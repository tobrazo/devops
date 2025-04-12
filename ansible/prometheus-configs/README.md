# 📊 Prometheus Monitoring Configuration

This repository contains configuration files and alert rules for Prometheus and Alertmanager, designed for a modular monitoring setup.

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

This repository includes `.gitlab-ci.yml` to:

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

> SSL files are not included in this repository. Place your `*.crt` and `*.key` files under `ssl/`.

---

## 📄 License

MIT