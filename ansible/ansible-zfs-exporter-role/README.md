# 📦 Ansible Role: ZFS Exporter

This Ansible role installs and configures the [ZFS Exporter](https://github.com/pdf/zfs_exporter) for Prometheus monitoring.

The exporter collects metrics related to ZFS file systems and exposes them via HTTP for scraping by Prometheus.

---

## 📁 Role Structure

```
.
├── zfs_exporter.yml               # Example playbook
├── roles/
│   └── zfs_exporter/
│       ├── tasks/
│       ├── templates/
│       ├── vars/
│       └── README.md
```

---

## 🚀 Quick Start

```bash
ansible-playbook -i inventory.ini zfs_exporter.yml
```

You can also include the role in your playbook:

```yaml
- hosts: all
  become: yes
  roles:
    - zfs_exporter
```

---

## 🔧 Role Variables

Available variables and defaults (see `vars/main.yml`):

```yaml
exporter_version: "2.3.4"
```

---

## 🔐 Service

After installation, the role will:

- Download and install the exporter
- Create a systemd service
- Enable and start the service

Service endpoint will be exposed on: `http://<host>:9134/metrics` (default port)

---

## 📄 License

MIT