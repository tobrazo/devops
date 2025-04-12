# 📦 Kubernetes Event Exporter Helm Wrapper

This repository provides a convenient wrapper around the official [Bitnami Helm chart for kubernetes-event-exporter](https://github.com/bitnami/charts/tree/main/bitnami/kubernetes-event-exporter), allowing quick deployment, upgrades, and deletion using the `start.sh` script.

---

## 📁 Structure

```
.
├── additional-configmap.yaml      # Example ConfigMap with CA certificate
├── start.sh                       # Script to install, upgrade, delete or dry-run the chart
└── test-env/
    └── replace.yaml               # Example values.yaml
```

---

## 🚀 Quick Start

```bash
chmod +x start.sh
./start.sh install     # Install the chart
./start.sh upgrade     # Upgrade the release
./start.sh delete      # Delete the release
./start.sh debug       # Dry-run and render templates
```

---

## ⚙️ Configuration

### `test-env/replace.yaml`

This file contains configuration for `kubernetes-event-exporter`, including logging setup and Elasticsearch receiver. **Make sure to replace** the credentials and endpoint with your own:

```yaml
config:
  receivers:
    - elasticsearch:
        hosts:
          - https://your-elasticsearch-url:9200
        username: your-username
        password: your-password
```

---

### `additional-configmap.yaml`

Used to provide a public CA certificate (e.g., Elasticsearch HTTP CA).

---

## 🛠 Requirements

- [Helm](https://helm.sh/) 3.x
- `kubectl` configured with access to your Kubernetes cluster

---

## 📝 License

[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
