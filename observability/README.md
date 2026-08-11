<div align="center">

# 📈 Observability

**Instrumenting a data source end to end — collection, alerting, dashboards, and the AI layer on top.**

![Prometheus](https://img.shields.io/badge/Prometheus-exporters_+_rules-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-dashboards-F46800?style=flat-square&logo=grafana&logoColor=white)
![Loki](https://img.shields.io/badge/Loki-logs-F46800?style=flat-square&logo=grafana&logoColor=white)

</div>

---

Where `helm-charts/`, `terraform/` and `ansible/` hold reusable building blocks, this
directory holds **vertical slices**: one data source taken all the way through, from the
thing that produces the numbers to the human who gets paged about them.

---

## 📂 Projects

| Project | What it is |
|---------|------------|
| 🚗 **[vehicle-telemetry](vehicle-telemetry)** | Pandora car telematics → 24 Prometheus metric families → 9 alert rules (with promtool unit tests) → a 13-panel Grafana dashboard → Compose **and** Kubernetes deploys → an AI agent that triages firing alerts. Ships a mock cabinet, so `docker compose --profile demo up` gives you the whole stack with live data and no hardware. |

Related: **[mcp/observability-ops](../mcp/observability-ops)** exposes a running
Prometheus / Loki / Alertmanager stack as MCP tools, so an assistant can query it from a
conversation. It is generic — it works against these projects or against your own cluster.
