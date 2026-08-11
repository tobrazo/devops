#!/usr/bin/env python3
"""
Alert-triage agent — turns a raw Alertmanager webhook into a diagnosis.

Alertmanager POSTs a firing alert here; the agent hands it to Claude together
with three read-only tools (instant PromQL, range PromQL, LogQL) and lets the
model decide what to correlate. The answer — a short, human-readable diagnosis
with the evidence it actually pulled — goes to Telegram, or to stdout when no
bot token is configured.

Nothing about this is vehicle-specific: point PROMETHEUS_URL / LOKI_URL at any
Prometheus and Loki and it triages whatever alerts you send it.

The agent loop is written out by hand rather than using the SDK's (beta) tool
runner: it is the part worth reading, it pins the tool surface to a read-only
allowlist, and it keeps this file on the stable, non-beta Messages API.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import anthropic
import requests

# ── Config (env vars) ───────────────────────────────────────────────
PORT = int(os.environ.get("TRIAGE_PORT", "9099"))
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
LOKI_URL = os.environ.get("LOKI_URL", "http://loki:3100")
MODEL = os.environ.get("TRIAGE_MODEL", "claude-opus-5")
EFFORT = os.environ.get("TRIAGE_EFFORT", "medium")
MAX_TOOL_ROUNDS = int(os.environ.get("TRIAGE_MAX_TOOL_ROUNDS", "8"))
HTTP_TIMEOUT = int(os.environ.get("TRIAGE_HTTP_TIMEOUT", "15"))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("triage")

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.stderr.write("ERROR: set ANTHROPIC_API_KEY\n")
    sys.exit(2)

client = anthropic.Anthropic()

SYSTEM_PROMPT = """\
You are an on-call engineer triaging a single Prometheus alert.

You have read-only access to the Prometheus and Loki instances that produced it.
Use the tools to gather evidence before drawing a conclusion — the alert label
set alone is rarely enough to tell a real incident from a benign blip. Typical
moves: chart the alerting metric over a longer window to see whether this is a
trend or a spike, check whether related metrics moved at the same moment, and
read the logs around the alert's start time.

Then answer with, in this order:
1. One sentence stating what is actually happening.
2. The evidence you gathered, with the concrete numbers you saw.
3. The most likely cause, and how confident you are.
4. The single next action for the on-call engineer.

Ground every claim in a tool result. If the data does not support a conclusion,
say what is missing rather than guessing. Keep the whole answer under 200 words —
it is going to a phone at 3am. No headers, no bullet-point walls, plain prose.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "prometheus_query",
        "description": (
            "Run an instant PromQL query against Prometheus and return the "
            "current value(s). Use for point-in-time facts: the current value of "
            "a metric, whether a series exists, how many series match a selector."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "PromQL expression, e.g. pandora_voltage_v",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "prometheus_query_range",
        "description": (
            "Run a range PromQL query and return a downsampled series. Use to see "
            "how a metric behaved over time — whether it is trending, oscillating, "
            "or changed abruptly. Prefer this over repeated instant queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "PromQL expression"},
                "minutes": {
                    "type": "integer",
                    "description": "How far back to look, in minutes (default 60)",
                },
                "step_seconds": {
                    "type": "integer",
                    "description": "Resolution in seconds (default 60)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "loki_query",
        "description": (
            "Run a LogQL query against Loki and return matching log lines, newest "
            "first. Use to read what the services were logging around the alert. "
            'Example selector: {job="docker"} |= "error"'
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "LogQL expression"},
                "minutes": {
                    "type": "integer",
                    "description": "How far back to look, in minutes (default 30)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum lines to return (default 50, max 200)",
                },
            },
            "required": ["query"],
        },
    },
]


# ── Tool implementations ────────────────────────────────────────────
def _truncate(text: str, limit: int = 6000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n… (truncated)"


def prometheus_query(query: str) -> str:
    r = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    result = r.json().get("data", {}).get("result", [])
    if not result:
        return "No series matched."
    lines = [
        f"{item.get('metric', {})} = {item.get('value', ['', ''])[1]}"
        for item in result[:50]
    ]
    return _truncate("\n".join(lines))


def prometheus_query_range(query: str, minutes: int = 60, step_seconds: int = 60) -> str:
    now = int(time.time())
    r = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query_range",
        params={
            "query": query,
            "start": now - max(1, minutes) * 60,
            "end": now,
            "step": max(15, step_seconds),
        },
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    result = r.json().get("data", {}).get("result", [])
    if not result:
        return "No series matched."

    chunks = []
    for item in result[:10]:
        values = item.get("values", [])
        # Keep the shape of the series without flooding the context window.
        sampled = values[:: max(1, len(values) // 20)] if values else []
        points = ", ".join(f"{v[1]}@{int(v[0])}" for v in sampled)
        chunks.append(f"{item.get('metric', {})}\n  {points}")
    return _truncate("\n".join(chunks))


def loki_query(query: str, minutes: int = 30, limit: int = 50) -> str:
    now_ns = int(time.time() * 1e9)
    r = requests.get(
        f"{LOKI_URL}/loki/api/v1/query_range",
        params={
            "query": query,
            "start": now_ns - max(1, minutes) * 60 * 10**9,
            "end": now_ns,
            "limit": min(max(1, limit), 200),
            "direction": "backward",
        },
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    result = r.json().get("data", {}).get("result", [])
    if not result:
        return "No log lines matched."

    lines = []
    for stream in result:
        label = stream.get("stream", {}).get("container", "?")
        for ts, line in stream.get("values", []):
            lines.append(f"[{label}] {line.rstrip()}")
    return _truncate("\n".join(lines[:limit]))


DISPATCH = {
    "prometheus_query": prometheus_query,
    "prometheus_query_range": prometheus_query_range,
    "loki_query": loki_query,
}


# ── Agent loop ──────────────────────────────────────────────────────
def describe_alert(alert: dict[str, Any]) -> str:
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    return json.dumps(
        {
            "status": alert.get("status"),
            "startsAt": alert.get("startsAt"),
            "labels": labels,
            "annotations": annotations,
        },
        indent=2,
        ensure_ascii=False,
    )


def triage(alert: dict[str, Any]) -> str:
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                "This alert just fired. Investigate it and report back.\n\n"
                f"{describe_alert(alert)}"
            ),
        }
    ]

    for round_no in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "refusal":
            return "Model declined to answer this alert."

        if response.stop_reason != "tool_use":
            return "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            handler = DISPATCH.get(block.name)
            log.info("round %d: %s(%s)", round_no + 1, block.name, block.input)
            try:
                if handler is None:
                    raise ValueError(f"unknown tool {block.name}")
                output = handler(**block.input)
                is_error = False
            except Exception as exc:  # surfaced to the model so it can adapt
                output, is_error = f"{type(exc).__name__}: {exc}", True
                log.warning("tool %s failed: %s", block.name, exc)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                }
            )

        messages.append({"role": "user", "content": results})

    return "Gave up after the tool-call budget was exhausted without a conclusion."


# ── Delivery ────────────────────────────────────────────────────────
def deliver(alert: dict[str, Any], diagnosis: str) -> None:
    name = alert.get("labels", {}).get("alertname", "alert")
    severity = alert.get("labels", {}).get("severity", "?")
    text = f"🔎 {name} ({severity})\n\n{diagnosis}"

    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        log.info("no Telegram configured — diagnosis below\n%s", text)
        return

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        log.info("delivered diagnosis for %s to Telegram", name)
    except Exception as exc:
        log.error("Telegram delivery failed: %s — diagnosis below\n%s", exc, text)


# ── Webhook server ──────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    server_version = "AlertTriage/1.0"

    def _respond(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        if self.path in ("/", "/healthz"):
            self._respond(200, {"status": "ok", "model": MODEL})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        if self.path.rstrip("/") not in ("", "/alerts"):
            self._respond(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._respond(400, {"error": "invalid JSON"})
            return

        alerts = [a for a in payload.get("alerts", []) if a.get("status") == "firing"]
        # Acknowledge immediately — Alertmanager retries on a slow webhook, and
        # a triage round takes far longer than its timeout.
        self._respond(200, {"accepted": len(alerts)})

        for alert in alerts:
            name = alert.get("labels", {}).get("alertname", "?")
            log.info("triaging %s", name)
            try:
                deliver(alert, triage(alert))
            except Exception as exc:
                log.exception("triage failed for %s: %s", name, exc)

    def log_message(self, fmt: str, *args) -> None:
        log.debug("%s", fmt % args)


def main() -> None:
    log.info(
        "alert-triage listening on :%d (model=%s, effort=%s, prometheus=%s, loki=%s)",
        PORT, MODEL, EFFORT, PROMETHEUS_URL, LOKI_URL,
    )
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("interrupted, exiting")
