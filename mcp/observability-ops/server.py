#!/usr/bin/env python3
"""
MCP server for a Prometheus / Loki / Alertmanager stack.

Exposes a running observability stack as tools an MCP client (e.g. Claude Code)
can call directly from the conversation: run PromQL and LogQL, inspect firing
alerts, scrape targets and loaded rules, and manage silences.

Nothing about the target stack is hardcoded — every endpoint comes from an
environment variable and defaults to a local stack. The server is read-only by
default; the two mutating tools (creating and expiring silences) only register
when OBS_MCP_ALLOW_WRITE is set.

See README.md for configuration and installation.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

try:  # MCP Python SDK >= 2.0
    from mcp.server.mcpserver import MCPServer
except ImportError:  # SDK 1.x — same API under the old name
    from mcp.server.fastmcp import FastMCP as MCPServer

# -------------------------------------------------------
# Configuration — every value is an env var with a safe default
# -------------------------------------------------------

PROMETHEUS_URL = os.environ.get("OBS_MCP_PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
LOKI_URL = os.environ.get("OBS_MCP_LOKI_URL", "http://localhost:3100").rstrip("/")
ALERTMANAGER_URL = os.environ.get("OBS_MCP_ALERTMANAGER_URL", "http://localhost:9093").rstrip("/")

TIMEOUT = int(os.environ.get("OBS_MCP_TIMEOUT", "20"))
MAX_CHARS = int(os.environ.get("OBS_MCP_MAX_CHARS", "12000"))

# Silences change what humans get paged about, so they are opt-in.
ALLOW_WRITE = os.environ.get("OBS_MCP_ALLOW_WRITE", "").lower() in ("1", "true", "yes")

# -------------------------------------------------------
# MCP server
# -------------------------------------------------------

mcp = MCPServer(
    "observability-ops",
    instructions=f"""
You investigate a Prometheus / Loki / Alertmanager stack.

Prometheus:   {PROMETHEUS_URL}
Loki:         {LOKI_URL}
Alertmanager: {ALERTMANAGER_URL}
Silences:     {"enabled" if ALLOW_WRITE else "read-only (OBS_MCP_ALLOW_WRITE is unset)"}

DISCOVERY — do this before guessing metric or label names:
  prom_metrics       — metric names, optionally filtered by substring
  prom_label_values  — values of a label, optionally scoped to one metric
  loki_labels        — log stream labels available in Loki

INVESTIGATION:
  prom_alerts / am_alerts — what is firing right now
  prom_query_range        — how a metric behaved over time (prefer over
                            repeated instant queries)
  loki_query              — what the services logged around that moment
  prom_targets            — whether a scrape target is actually up

Correlate before concluding: a firing alert plus a flat metric plus quiet logs
usually means a broken exporter, not a broken service. Report the numbers you
saw, not just the verdict.
""",
)


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _truncate(text: str) -> str:
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n… (truncated)"


def _get(url: str, params: dict[str, Any] | None = None) -> Any:
    r = requests.get(url, params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _prom(path: str, params: dict[str, Any] | None = None) -> Any:
    body = _get(f"{PROMETHEUS_URL}/api/v1/{path}", params)
    if body.get("status") != "success":
        raise RuntimeError(body.get("error", "Prometheus returned an error"))
    return body.get("data")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_samples(result: list[dict], limit: int = 50) -> str:
    if not result:
        return "No series matched."
    lines = []
    for item in result[:limit]:
        metric = item.get("metric", {})
        name = metric.pop("__name__", "")
        labels = ", ".join(f'{k}="{v}"' for k, v in sorted(metric.items()))
        value = item.get("value", ["", "?"])[1]
        lines.append(f"{name}{{{labels}}} = {value}")
    if len(result) > limit:
        lines.append(f"… {len(result) - limit} more series")
    return _truncate("\n".join(lines))


# -------------------------------------------------------
# Prometheus — query
# -------------------------------------------------------

@mcp.tool()
def prom_query(query: str) -> str:
    """Run an instant PromQL query and return the current value of each matching series.

    Use for point-in-time questions: what a metric reads now, whether a series
    exists, how many series match a selector.
    """
    data = _prom("query", {"query": query})
    if data.get("resultType") == "scalar":
        return str(data.get("result", ["", "?"])[1])
    return _fmt_samples(data.get("result", []))


@mcp.tool()
def prom_query_range(query: str, minutes: int = 60, step_seconds: int = 60) -> str:
    """Run a range PromQL query and return a downsampled series per match.

    Use to see how a metric behaved over time — trending, oscillating, or a step
    change. Prefer this over repeatedly calling prom_query.
    """
    end = _now()
    start = end - timedelta(minutes=max(1, minutes))
    data = _prom(
        "query_range",
        {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": max(15, step_seconds),
        },
    )
    result = data.get("result", [])
    if not result:
        return "No series matched."

    chunks = []
    for item in result[:10]:
        values = item.get("values", [])
        sampled = values[:: max(1, len(values) // 24)] if values else []
        points = ", ".join(f"{v[1]}@{int(float(v[0]))}" for v in sampled)
        chunks.append(f"{item.get('metric', {})}\n  {points}")
    if len(result) > 10:
        chunks.append(f"… {len(result) - 10} more series")
    return _truncate("\n".join(chunks))


# -------------------------------------------------------
# Prometheus — discovery and health
# -------------------------------------------------------

@mcp.tool()
def prom_metrics(contains: str = "") -> str:
    """List metric names known to Prometheus, optionally filtered by substring.

    Start here when you don't know what is being collected.
    """
    names = _prom("label/__name__/values") or []
    if contains:
        names = [n for n in names if contains.lower() in n.lower()]
    if not names:
        return "No metric names matched."
    return _truncate(f"{len(names)} metrics:\n" + "\n".join(sorted(names)))


@mcp.tool()
def prom_label_values(label: str, metric: str = "") -> str:
    """List the values a label takes, optionally scoped to one metric.

    Use to enumerate instances, jobs, devices, or any other dimension before
    writing a query that filters on it.
    """
    params = {"match[]": metric} if metric else None
    values = _prom(f"label/{label}/values", params) or []
    if not values:
        return f"No values found for label '{label}'."
    return _truncate(f"{len(values)} values:\n" + "\n".join(sorted(values)))


@mcp.tool()
def prom_targets(state: str = "active") -> str:
    """List Prometheus scrape targets and their health ('active', 'dropped', 'any').

    A metric that has gone flat is often a target that stopped being scraped —
    check here before assuming the underlying system changed.
    """
    data = _prom("targets", {"state": state})
    targets = data.get("activeTargets", []) + data.get("droppedTargets", [])
    if not targets:
        return "No targets."
    lines = []
    for t in targets:
        labels = t.get("labels", {})
        health = t.get("health", "unknown")
        marker = "UP  " if health == "up" else "DOWN"
        err = f"  ← {t['lastError']}" if t.get("lastError") else ""
        lines.append(
            f"{marker} {labels.get('job', '?')} {t.get('scrapeUrl', '?')}{err}"
        )
    return _truncate("\n".join(lines))


@mcp.tool()
def prom_rules(only_firing: bool = False) -> str:
    """List alerting and recording rule groups loaded by Prometheus.

    Use to confirm a rule file was actually picked up, or to read the exact
    expression behind an alert before interpreting it.
    """
    data = _prom("rules")
    lines = []
    for group in data.get("groups", []):
        lines.append(f"[{group.get('file', '?')}] {group.get('name', '?')}")
        for rule in group.get("rules", []):
            state = rule.get("state", "")
            if only_firing and state != "firing":
                continue
            kind = rule.get("type", "?")
            name = rule.get("name", "?")
            suffix = f"  ({state})" if state else ""
            lines.append(f"  {kind:9s} {name}{suffix}")
            lines.append(f"            expr: {rule.get('query', '')}")
    return _truncate("\n".join(lines) or "No rules loaded.")


@mcp.tool()
def prom_alerts() -> str:
    """List alerts Prometheus currently considers pending or firing.

    This is Prometheus' own view — use am_alerts for what Alertmanager has
    after grouping, inhibition and silencing.
    """
    data = _prom("alerts")
    alerts = data.get("alerts", [])
    if not alerts:
        return "No pending or firing alerts."
    lines = []
    for a in alerts:
        labels = a.get("labels", {})
        lines.append(
            f"{a.get('state', '?').upper():8s} {labels.get('alertname', '?')} "
            f"{ {k: v for k, v in labels.items() if k != 'alertname'} } "
            f"since {a.get('activeAt', '?')}"
        )
        summary = a.get("annotations", {}).get("summary")
        if summary:
            lines.append(f"         {summary}")
    return _truncate("\n".join(lines))


# -------------------------------------------------------
# Loki
# -------------------------------------------------------

@mcp.tool()
def loki_query(query: str, minutes: int = 30, limit: int = 100) -> str:
    """Run a LogQL query and return matching log lines, newest first.

    Example selectors: {job="docker"} — everything;
    {container="prometheus"} |= "error" — one container, filtered.
    """
    end = _now()
    start = end - timedelta(minutes=max(1, minutes))
    body = _get(
        f"{LOKI_URL}/loki/api/v1/query_range",
        {
            "query": query,
            "start": int(start.timestamp() * 1e9),
            "end": int(end.timestamp() * 1e9),
            "limit": min(max(1, limit), 1000),
            "direction": "backward",
        },
    )
    result = body.get("data", {}).get("result", [])
    if not result:
        return "No log lines matched."

    lines = []
    for stream in result:
        labels = stream.get("stream", {})
        tag = labels.get("container") or labels.get("job") or "?"
        for ts, line in stream.get("values", []):
            when = datetime.fromtimestamp(int(ts) / 1e9, timezone.utc).strftime("%H:%M:%S")
            lines.append(f"{when} [{tag}] {line.rstrip()}")
    return _truncate("\n".join(lines[:limit]))


@mcp.tool()
def loki_labels(label: str = "") -> str:
    """List Loki stream labels, or the values of one label if `label` is given.

    Run this before writing a LogQL selector so the stream matcher is real.
    """
    path = f"{LOKI_URL}/loki/api/v1/label/{label}/values" if label else f"{LOKI_URL}/loki/api/v1/labels"
    values = _get(path).get("data", []) or []
    if not values:
        return "Nothing found — is anything shipping logs to Loki?"
    return _truncate("\n".join(sorted(values)))


# -------------------------------------------------------
# Alertmanager
# -------------------------------------------------------

@mcp.tool()
def am_alerts(active: bool = True, silenced: bool = False, inhibited: bool = False) -> str:
    """List alerts currently held by Alertmanager, after grouping and silencing.

    Compare with prom_alerts: an alert firing in Prometheus but absent here has
    been silenced or inhibited.
    """
    body = _get(
        f"{ALERTMANAGER_URL}/api/v2/alerts",
        {
            "active": str(active).lower(),
            "silenced": str(silenced).lower(),
            "inhibited": str(inhibited).lower(),
        },
    )
    if not body:
        return "No alerts."
    lines = []
    for a in body:
        labels = a.get("labels", {})
        status = a.get("status", {}).get("state", "?")
        lines.append(
            f"{status:9s} {labels.get('alertname', '?')} "
            f"{ {k: v for k, v in labels.items() if k != 'alertname'} }"
        )
        summary = a.get("annotations", {}).get("summary")
        if summary:
            lines.append(f"          {summary}")
    return _truncate("\n".join(lines))


@mcp.tool()
def am_silences(active_only: bool = True) -> str:
    """List Alertmanager silences with their matchers, author and expiry."""
    body = _get(f"{ALERTMANAGER_URL}/api/v2/silences")
    lines = []
    for s in body:
        state = s.get("status", {}).get("state", "?")
        if active_only and state != "active":
            continue
        matchers = ", ".join(
            f"{m.get('name')}{'=~' if m.get('isRegex') else '='}{m.get('value')}"
            for m in s.get("matchers", [])
        )
        lines.append(
            f"{s.get('id', '?')}  [{state}]  {matchers}\n"
            f"    by {s.get('createdBy', '?')} until {s.get('endsAt', '?')}: "
            f"{s.get('comment', '')}"
        )
    return _truncate("\n".join(lines) or "No silences.")


if ALLOW_WRITE:

    @mcp.tool()
    def am_silence_create(
        matchers: str, hours: float = 1.0, comment: str = "", created_by: str = "observability-ops"
    ) -> str:
        """Silence alerts matching a label set for a number of hours.

        `matchers` is a JSON list of {"name","value","isRegex"} objects, e.g.
        [{"name":"alertname","value":"PandoraDeviceOffline","isRegex":false}].

        This suppresses paging — confirm the matchers and duration with the user
        before calling, and prefer the narrowest matcher that covers the noise.
        Only available when OBS_MCP_ALLOW_WRITE is set.
        """
        try:
            parsed = json.loads(matchers)
        except ValueError as exc:
            return f"matchers must be valid JSON: {exc}"
        if not isinstance(parsed, list) or not parsed:
            return "matchers must be a non-empty JSON list of matcher objects."

        start = _now()
        payload = {
            "matchers": [
                {
                    "name": m["name"],
                    "value": m["value"],
                    "isRegex": bool(m.get("isRegex", False)),
                    "isEqual": bool(m.get("isEqual", True)),
                }
                for m in parsed
            ],
            "startsAt": start.isoformat(),
            "endsAt": (start + timedelta(hours=max(0.1, hours))).isoformat(),
            "createdBy": created_by,
            "comment": comment or "created via observability-ops MCP",
        }
        r = requests.post(
            f"{ALERTMANAGER_URL}/api/v2/silences", json=payload, timeout=TIMEOUT
        )
        r.raise_for_status()
        return f"Silence created: {r.json().get('silenceID', '?')} (expires in {hours}h)"

    @mcp.tool()
    def am_silence_expire(silence_id: str) -> str:
        """Expire an Alertmanager silence immediately, so its alerts can page again.

        Only available when OBS_MCP_ALLOW_WRITE is set.
        """
        r = requests.delete(
            f"{ALERTMANAGER_URL}/api/v2/silence/{silence_id}", timeout=TIMEOUT
        )
        r.raise_for_status()
        return f"Silence {silence_id} expired."


# -------------------------------------------------------
# Resources
# -------------------------------------------------------

@mcp.resource("observability://config")
def config_resource() -> str:
    """Effective endpoints and mode of this MCP server."""
    return json.dumps(
        {
            "prometheus_url": PROMETHEUS_URL,
            "loki_url": LOKI_URL,
            "alertmanager_url": ALERTMANAGER_URL,
            "timeout_seconds": TIMEOUT,
            "write_enabled": ALLOW_WRITE,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
