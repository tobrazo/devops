#!/usr/bin/env python3
"""
Pandora P-ON metrics exporter for Prometheus.

Logs into pro.p-on.ru (or p-on.ru), polls /api/updates,
exposes parsed telemetry as Prometheus metrics on /metrics.

Login flow verified against turbulator/pandora-cas reverse-engineering:
  POST /api/users/login form-encoded with {login, password, lang}
  Browser-like User-Agent (Pandora rejects default python-requests UA).
"""

import logging
import os
import sys
import time
from json import JSONDecodeError
from typing import Optional

import requests
from prometheus_client import Counter, Gauge, start_http_server

# ── Config (env vars) ───────────────────────────────────────────────
PANDORA_LOGIN = os.environ.get("PANDORA_LOGIN")
PANDORA_PASSWORD = os.environ.get("PANDORA_PASSWORD")
PANDORA_HOST = os.environ.get("PANDORA_HOST", "pro.p-on.ru")
# http only for the bundled mock cabinet — the real cabinet is https.
PANDORA_SCHEME = os.environ.get("PANDORA_SCHEME", "https")
PANDORA_LOGIN_PATH = os.environ.get("PANDORA_LOGIN_PATH", "/api/users/login")
PANDORA_LOGIN_FIELD = os.environ.get("PANDORA_LOGIN_FIELD", "login")
PANDORA_LOGIN_FORMAT = os.environ.get("PANDORA_LOGIN_FORMAT", "json")
DEVICE_FILTER = {
    d.strip() for d in os.environ.get("PANDORA_DEVICE_IDS", "").split(",") if d.strip()
}
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SEC", "10"))
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT", "9180"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

if not PANDORA_LOGIN or not PANDORA_PASSWORD:
    sys.stderr.write("ERROR: set PANDORA_LOGIN and PANDORA_PASSWORD env vars\n")
    sys.exit(2)

# CRITICAL: Pandora rejects default python-requests User-Agent with 200 + no cookies
BROWSER_UA = (
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0"
)

# ── Prometheus metrics ──────────────────────────────────────────────
LBL = ["device_id"]
TPMS_LBL = ["device_id", "wheel"]

m_online = Gauge("pandora_online", "Device online (1) or offline (0)", LBL)
m_move = Gauge("pandora_move", "Device moving (1) or stationary (0)", LBL)
m_speed = Gauge("pandora_speed_kmh", "Current speed, km/h", LBL)
m_rpm = Gauge("pandora_engine_rpm", "Engine RPM", LBL)
m_voltage = Gauge("pandora_voltage_v", "Battery voltage, V", LBL)
m_engine_temp = Gauge("pandora_engine_temp_c", "Engine coolant temperature, C", LBL)
m_out_temp = Gauge("pandora_outside_temp_c", "Outside temperature, C", LBL)
m_cabin_temp = Gauge("pandora_cabin_temp_c", "Cabin temperature, C", LBL)
m_fuel = Gauge("pandora_fuel_percent", "Fuel level, %", LBL)
m_mileage_pandora = Gauge("pandora_mileage_km", "Pandora-tracked mileage, km", LBL)
m_mileage_can = Gauge("pandora_mileage_can_km", "CAN-bus odometer, km", LBL)
m_gsm = Gauge("pandora_gsm_level", "GSM signal level (0-5)", LBL)
m_lat = Gauge("pandora_position_lat", "Latitude", LBL)
m_lon = Gauge("pandora_position_lon", "Longitude", LBL)
m_range_left = Gauge("pandora_range_to_empty_km", "Estimated range to empty, km", LBL)
m_tpms = Gauge("pandora_tpms_atm", "Tire pressure, atm", TPMS_LBL)
m_sim_balance = Gauge(
    "pandora_sim_balance", "SIM card balance", LBL + ["currency", "phone"]
)
m_last_seen = Gauge("pandora_last_seen_ts", "Last device-server contact, unix ts", LBL)
m_last_cmd = Gauge("pandora_last_command_ts", "Last command applied, unix ts", LBL)
m_last_setting = Gauge(
    "pandora_last_setting_ts", "Last settings change, unix ts", LBL
)

c_poll_total = Counter("pandora_poll_total", "Polls attempted")
c_poll_errors = Counter("pandora_poll_errors_total", "Polls failed", ["kind"])
c_relogin = Counter("pandora_relogin_total", "Re-login attempts")
m_last_poll = Gauge("pandora_exporter_last_poll_ts", "Last successful poll, unix ts")

log = logging.getLogger("pandora")


# ── HTTP client ─────────────────────────────────────────────────────
class AuthError(Exception):
    pass


class PandoraClient:
    def __init__(self, host: str, login: str, password: str):
        self.host = host
        self.login_value = login
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": BROWSER_UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def login(self) -> None:
        url = f"{PANDORA_SCHEME}://{self.host}{PANDORA_LOGIN_PATH}"
        payload = {
            PANDORA_LOGIN_FIELD: self.login_value,
            "password": self.password,
            "lang": "ru",
        }

        log.info(
            "POST %s (format=%s, field=%s, value=%s, UA=Firefox)",
            url, PANDORA_LOGIN_FORMAT, PANDORA_LOGIN_FIELD, self.login_value,
        )

        try:
            self.session.get(f"{PANDORA_SCHEME}://{self.host}/", timeout=10)
        except Exception as e:
            log.warning("Pre-login GET failed (continuing anyway): %s", e)

        if PANDORA_LOGIN_FORMAT == "json":
            r = self.session.post(url, json=payload, timeout=15)
        else:
            r = self.session.post(url, data=payload, timeout=15)

        log.info(
            "Login response: status=%s, content-type=%s, cookies=%s",
            r.status_code,
            r.headers.get("Content-Type", "?"),
            [c.name for c in self.session.cookies] or "<none>",
        )

        pandora_error = None
        try:
            body = r.json()
            if isinstance(body, dict) and body.get("status") == "fail":
                pandora_error = body.get("error_text", "(no error_text)")
        except (ValueError, JSONDecodeError):
            pass

        if r.status_code != 200 or not self.session.cookies or pandora_error:
            body_preview = r.text[:500] if r.text else "<empty>"
            body_preview = body_preview.replace(self.password, "***REDACTED***")
            log.error("Login response body (first 500 chars):\n%s", body_preview)

        r.raise_for_status()

        if pandora_error:
            raise RuntimeError(
                f"Login rejected by Pandora: {pandora_error}. "
                "PANDORA_LOGIN must be the email/username from website, "
                "NOT the device ID."
            )

        if not self.session.cookies:
            raise RuntimeError(
                f"Login failed: status={r.status_code}, no cookies. "
                "Try alternative PANDORA_LOGIN_FIELD ('email' or 'username') "
                "or PANDORA_HOST='p-on.ru'."
            )

        log.info("Login OK, cookies: %s", [c.name for c in self.session.cookies])

    def fetch_updates(self, since_ts: int = -1) -> dict:
        now = int(time.time())
        url = f"{PANDORA_SCHEME}://{self.host}/api/updates"
        params = {"ts": since_ts, "from": now - 86400, "to": now + 60}
        r = self.session.get(url, params=params, timeout=15)
        if r.status_code in (401, 403):
            raise AuthError(f"Auth required (status={r.status_code})")
        if r.status_code == 400:
            raise AuthError("Cabinet rejected request (400) — try re-login")
        r.raise_for_status()
        return r.json()


# ── Metric updaters ─────────────────────────────────────────────────
WHEEL_MAP = {
    "CAN_TMPS_back_left": "back_left",
    "CAN_TMPS_back_right": "back_right",
    "CAN_TMPS_forvard_left": "front_left",
    "CAN_TMPS_forvard_right": "front_right",
    "CAN_TMPS_reserve": "spare",
}


def _set(gauge: Gauge, value, **labels) -> None:
    if value is None:
        return
    try:
        gauge.labels(**labels).set(float(value))
    except (TypeError, ValueError):
        pass


def update_metrics(payload: dict) -> None:
    stats = payload.get("stats") or {}
    times = payload.get("time") or {}

    for device_id, d in stats.items():
        if DEVICE_FILTER and device_id not in DEVICE_FILTER:
            continue

        lbl = {"device_id": device_id}

        _set(m_online, d.get("online"), **lbl)
        _set(m_move, d.get("move"), **lbl)
        _set(m_speed, d.get("speed"), **lbl)
        _set(m_rpm, d.get("engine_rpm"), **lbl)
        _set(m_voltage, d.get("voltage"), **lbl)
        _set(m_engine_temp, d.get("engine_temp"), **lbl)
        _set(m_out_temp, d.get("out_temp"), **lbl)
        _set(m_cabin_temp, d.get("cabin_temp"), **lbl)
        _set(m_fuel, d.get("fuel"), **lbl)
        _set(m_mileage_pandora, d.get("mileage"), **lbl)
        _set(m_mileage_can, d.get("mileage_CAN"), **lbl)
        _set(m_gsm, d.get("gsm_level"), **lbl)
        _set(m_lat, d.get("x"), **lbl)
        _set(m_lon, d.get("y"), **lbl)

        can = d.get("can") or {}
        _set(m_range_left, can.get("CAN_mileage_to_empty"), **lbl)
        for api_key, wheel_label in WHEEL_MAP.items():
            v = can.get(api_key, 0)
            if v and v > 0:
                _set(m_tpms, v, device_id=device_id, wheel=wheel_label)

        for sim in d.get("sims") or []:
            bal = sim.get("balance") or {}
            _set(
                m_sim_balance,
                bal.get("value"),
                device_id=device_id,
                currency=bal.get("cur", "?"),
                phone=sim.get("phoneNumber", "?"),
            )

        t = times.get(device_id) or {}
        _set(m_last_seen, t.get("online"), **lbl)
        _set(m_last_cmd, t.get("command"), **lbl)
        _set(m_last_setting, t.get("setting"), **lbl)


# ── Main loop ───────────────────────────────────────────────────────
def run(client: PandoraClient) -> None:
    last_ts = -1
    backoff = 1

    while True:
        c_poll_total.inc()
        try:
            data = client.fetch_updates(since_ts=last_ts)
            update_metrics(data)
            last_ts = data.get("ts", last_ts)
            m_last_poll.set(time.time())
            backoff = 1
            log.debug(
                "Poll OK: ts=%s, devices=%d", last_ts, len(data.get("stats") or {})
            )

        except AuthError as e:
            c_relogin.inc()
            log.warning("Auth issue (%s), re-logging in", e)
            try:
                client.login()
            except Exception as login_err:
                c_poll_errors.labels(kind="login").inc()
                log.error("Re-login failed: %s — retry in %ds", login_err, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

        except requests.Timeout:
            c_poll_errors.labels(kind="timeout").inc()
            log.warning("Poll timeout")

        except requests.RequestException as e:
            c_poll_errors.labels(kind="network").inc()
            log.error("Network error: %s", e)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        except Exception:
            c_poll_errors.labels(kind="other").inc()
            log.exception("Unexpected error")

        time.sleep(POLL_INTERVAL)


def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    log.info(
        "Starting pandora-exporter: host=%s, devices=%s, interval=%ds, port=%d",
        PANDORA_HOST,
        DEVICE_FILTER or "<all>",
        POLL_INTERVAL,
        EXPORTER_PORT,
    )

    client = PandoraClient(PANDORA_HOST, PANDORA_LOGIN, PANDORA_PASSWORD)

    # Start HTTP server BEFORE login so /metrics is always reachable.
    # If login fails, the run() loop retries indefinitely.
    start_http_server(EXPORTER_PORT)
    log.info("Prometheus endpoint: http://0.0.0.0:%d/metrics", EXPORTER_PORT)

    try:
        client.login()
    except Exception as e:
        c_poll_errors.labels(kind="login").inc()
        log.error("Initial login failed: %s — will retry in polling loop", e)

    run(client)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Interrupted, exiting")
