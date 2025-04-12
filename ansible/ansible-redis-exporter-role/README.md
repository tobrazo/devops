# 📦 Ansible Role: Redis Exporter

This Ansible role installs and configures the [Redis Exporter](https://github.com/oliver006/redis_exporter) for Prometheus monitoring.

It exposes Redis metrics over HTTP, compatible with Prometheus scraping.

---

## 📁 Structure

```
.
├── redis_exporter.yml               # Example playbook
├── roles/
│   └── redis_exporter/
│       ├── tasks/
│       ├── templates/
│       ├── defaults/
│       ├── handlers/
```

---

## 🚀 Usage

```bash
ansible-playbook -i inventory.ini redis_exporter.yml
```

---

## ⚙️ Role Variables

Default variables are in `defaults/main.yml`:

```yaml
redis_exporter_version: "1.47.0"
redis_exporter_release: "linux-amd64"
redis_exporter:
  binary_install_dir: "/usr/local/bin"
redis_exporter_requirepass: ""  # Set if your Redis requires authentication
```

---

## 🔐 Service

Systemd service will be installed as `/etc/systemd/system/redis_exporter.service`

The service will connect to: `redis://localhost:6379`

Metrics exposed on: `http://localhost:9121/metrics`

---

## 📄 License

MIT