<div align="center">

# 📦 Kubernetes Event Exporter

**A thin wrapper around the upstream event-exporter chart — install, upgrade, delete or dry-run with one `start.sh` helper.**

![Helm](https://img.shields.io/badge/Helm-3-0F1689?style=flat-square&logo=helm&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-events-326CE5?style=flat-square&logo=kubernetes&logoColor=white)

</div>

---

This wrapper drives the official [Bitnami Helm chart for kubernetes-event-exporter](https://github.com/bitnami/charts/tree/main/bitnami/kubernetes-event-exporter), giving you quick deploy, upgrade, and delete flows through the `start.sh` script.

## 📁 Structure

```text
.
├── additional-configmap.yaml      # Example ConfigMap with CA certificate
├── start.sh                       # Install, upgrade, delete or dry-run the chart
└── test-env/
    └── replace.yaml               # Example values.yaml
```

## 🚀 Quick start

```bash
chmod +x start.sh
./start.sh install     # Install the chart
./start.sh upgrade     # Upgrade the release
./start.sh delete      # Delete the release
./start.sh debug       # Dry-run and render templates
```

## ⚙️ Configuration

### `test-env/replace.yaml`

Configuration for `kubernetes-event-exporter`, including logging setup and an Elasticsearch receiver:

```yaml
config:
  receivers:
    - elasticsearch:
        hosts:
          - https://elasticsearch.example.internal:9200
        username: REPLACE_WITH_ES_USERNAME
        password: REPLACE_WITH_ES_PASSWORD
```

> [!WARNING]
> Replace the endpoint and credentials with your own before deploying. Never commit real hosts or passwords — source them from a Kubernetes `Secret` or your secret store.

### `additional-configmap.yaml`

Provides a public CA certificate (e.g. an Elasticsearch HTTP CA) to the exporter.

## 🛠 Requirements

- [Helm](https://helm.sh/) 3.x
- `kubectl` configured with access to your Kubernetes cluster

## 📝 License

[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
