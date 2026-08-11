#!/usr/bin/env python3
"""
Mock Pandora P-ON cabinet — lets the whole stack run without a car.

Serves the two endpoints the exporter talks to:

  POST /api/users/login   → sets a session cookie
  GET  /api/updates       → simulated telemetry for one or more devices

The simulation is a pure function of wall-clock time, so every panel on the
dashboard fills in within a minute and the alert rules have something to fire
on: a 30-minute drive cycle (park → drive → park), a fuel level that falls
while the engine runs, an odometer that only goes up, and one slowly
deflating tire that eventually trips PandoraTireLow.

Standard library only — no dependencies, no network calls.
"""

import json
import math
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("MOCK_PORT", "8080"))
DEVICE_IDS = [
    d.strip()
    for d in os.environ.get("MOCK_DEVICE_IDS", "1234567890").split(",")
    if d.strip()
]
# Centre of the simulated GPS loop. Deliberately a neutral, non-specific point.
BASE_LAT = float(os.environ.get("MOCK_LAT", "50.0"))
BASE_LON = float(os.environ.get("MOCK_LON", "10.0"))

CYCLE = 1800.0        # one park → drive → park cycle, seconds
DRIVE_START = 600.0   # engine starts 10 min into the cycle
DRIVE_END = 1500.0    # engine stops 25 min in
TPMS_CYCLE = 21600.0  # a tire deflates over 6 h, then is "re-inflated"

SESSION_COOKIE = "mock_pandora_sid"


def _drive_phase(now: float) -> tuple[bool, float]:
    """Return (engine_running, seconds_into_the_drive)."""
    t = now % CYCLE
    if DRIVE_START <= t < DRIVE_END:
        return True, t - DRIVE_START
    return False, 0.0


def _speed(driving: bool, elapsed: float) -> float:
    """City-driving speed profile: pulls away, cruises, stops at lights."""
    if not driving:
        return 0.0
    base = 45 + 25 * math.sin(elapsed / 90.0)
    stops = max(0.0, math.sin(elapsed / 240.0))  # periodic slow-downs
    return round(max(0.0, base * stops), 1)


def _device_state(device_id: str, now: float, index: int) -> dict:
    driving, elapsed = _drive_phase(now + index * 300)  # stagger multiple cars
    speed = _speed(driving, elapsed)

    # Odometer only ever grows; derived from total elapsed time, not the cycle.
    mileage = round(12000 + (now % 31_536_000) / 3600.0 * 8.0, 1)

    # Fuel drains during the drive phase and is "refuelled" each cycle.
    fuel = round(70 - (elapsed / (DRIVE_END - DRIVE_START)) * 62, 1) if driving else 70.0

    # Coolant warms up over the first ~8 minutes of driving, then cools off.
    if driving:
        engine_temp = round(min(92.0, 20 + elapsed * 0.15), 1)
    else:
        engine_temp = round(max(18.0, 92 - (now % CYCLE) * 0.05), 1)

    out_temp = round(12 + 6 * math.sin(now / 86400.0 * 2 * math.pi), 1)
    cabin_temp = round(out_temp + (8 if driving else 2), 1)
    voltage = round(14.2 if driving else 12.6 - (now % CYCLE) / CYCLE * 0.5, 2)
    rpm = int(900 + speed * 42) if driving else 0

    # One tire loses pressure slowly, so PandoraTireLow has something to catch.
    leak = 2.3 - (now % TPMS_CYCLE) / TPMS_CYCLE * 0.8

    angle = (now % 900) / 900.0 * 2 * math.pi
    lat = round(BASE_LAT + 0.01 * math.sin(angle), 6)
    lon = round(BASE_LON + 0.01 * math.cos(angle), 6)

    return {
        "online": 1,
        "move": 1 if speed > 0 else 0,
        "speed": speed,
        "engine_rpm": rpm,
        "voltage": voltage,
        "engine_temp": engine_temp,
        "out_temp": out_temp,
        "cabin_temp": cabin_temp,
        "fuel": fuel,
        "mileage": mileage,
        "mileage_CAN": round(mileage + 240.0, 1),
        "gsm_level": 4,
        "x": lat,
        "y": lon,
        "can": {
            "CAN_mileage_to_empty": round(fuel * 9.5, 1),
            "CAN_TMPS_forvard_left": round(leak, 2),
            "CAN_TMPS_forvard_right": 2.3,
            "CAN_TMPS_back_left": 2.2,
            "CAN_TMPS_back_right": 2.2,
            "CAN_TMPS_reserve": 0,
        },
        "sims": [
            {
                "phoneNumber": "+10000000000",
                "balance": {
                    "value": round(120 - (now % 604800) / 604800 * 100, 2),
                    "cur": "EUR",
                },
            }
        ],
    }


def build_payload() -> dict:
    now = time.time()
    ts = int(now)
    stats, times = {}, {}
    for index, device_id in enumerate(DEVICE_IDS):
        stats[device_id] = _device_state(device_id, now, index)
        times[device_id] = {"online": ts, "command": ts - 3600, "setting": ts - 86400}
    return {"ts": ts, "stats": stats, "time": times}


class Handler(BaseHTTPRequestHandler):
    server_version = "MockPandora/1.0"

    def _json(self, payload: dict, status: int = 200, cookie: bool = False) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=mock-session; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def _authenticated(self) -> bool:
        return SESSION_COOKIE in (self.headers.get("Cookie") or "")

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/api/updates":
            # Mirror the real cabinet: no session cookie means 401, which
            # exercises the exporter's re-login path.
            if not self._authenticated():
                self._json({"status": "fail", "error_text": "auth required"}, 401)
                return
            self._json(build_payload())
        elif path in ("/", "/healthz"):
            self._json({"status": "ok", "devices": DEVICE_IDS})
        else:
            self._json({"status": "fail", "error_text": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else ""

        if path != "/api/users/login":
            self._json({"status": "fail", "error_text": "not found"}, 404)
            return

        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {k: v[0] for k, v in parse_qs(raw).items()}

        login = payload.get("login") or payload.get("email") or payload.get("username")
        if not login or not payload.get("password"):
            self._json({"status": "fail", "error_text": "login/password required"}, 200)
            return

        self._json({"status": "success", "lang": payload.get("lang", "ru")}, cookie=True)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[mock-pandora] {fmt % args}", flush=True)


def main() -> None:
    print(
        f"[mock-pandora] listening on :{PORT}, devices={DEVICE_IDS}",
        flush=True,
    )
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
