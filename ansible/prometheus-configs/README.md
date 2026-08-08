<div align="center">

# 📊 Prometheus Monitoring Configuration

**Prometheus + Alertmanager configuration and per-exporter alert rules, deployed via GitLab CI.**

![Prometheus](https://img.shields.io/badge/Prometheus-config-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![Alertmanager](https://img.shields.io/badge/Alertmanager-alerts-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![GitLab CI](https://img.shields.io/badge/GitLab_CI-lint%20%2B%20deploy-FC6D26?style=flat-square&logo=gitlab&logoColor=white)

</div>

---

This directory contains configuration files and alert rules for Prometheus and Alertmanager, designed for a modular monitoring setup.

---

## 📁 Contents

- `prometheus.yml` — Prometheus configuration file
- `alertmanager.yml` — Alertmanager configuration
- `*.rules.*` — Prometheus alert rules (per exporter)
- `*.service` — Example systemd unit files
- `.gitlab-ci.yml` — GitLab CI pipeline to test and deploy configurations
- `ssl/` — Directory placeholder for TLS certificates (not included)

---

## 🚀 GitLab CI/CD Pipeline

The `.gitlab-ci.yml` pipeline is set up to:

- Lint Prometheus and Alertmanager configs using `promtool` and `amtool`
- Detect config changes
- Automatically deploy updated configs to `/etc/prometheus` or `/etc/alertmanager`
- Restart services when needed

---

## ⚙️ Setup

Ensure the following:

- Prometheus installed
- Alertmanager installed
- `promtool` and `amtool` available in the runner environment

---

## 🛡 Security Note

> [!IMPORTANT]
> SSL files are **not** included in this repository. Place your own `*.crt` and `*.key` files under `ssl/`. Slack webhook URLs and other credentials in the sample configs are placeholders (`xxxxx`, `<password>`) — replace them with values from your secret store.

---

## 📄 License

MIT
