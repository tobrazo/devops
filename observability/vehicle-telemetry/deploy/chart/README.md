<div align="center">

# ☸️ vehicle-telemetry Helm chart

**The whole slice on a cluster: exporter, alert rules, dashboard, mock, triage agent.**

![Helm](https://img.shields.io/badge/Helm-3-0F1689?style=flat-square&logo=helm&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![Prometheus Operator](https://img.shields.io/badge/Prometheus_Operator-ServiceMonitor_+_PrometheusRule-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-ready-EF7B4D?style=flat-square&logo=argo&logoColor=white)

</div>

---

The Compose stack runs the slice on one host. This chart runs the same slice on a cluster —
and it ships more than the exporter, because the exporter alone is not the interesting part:

| Object | What it is | Toggle |
|---|---|---|
| `Deployment` + `Service` | The exporter, singleton, non-root, read-only rootfs | always |
| `Secret` | Cabinet credentials — or bring your own | `pandora.existingSecret` |
| `ServiceMonitor` | Prometheus Operator scrape target | `serviceMonitor.enabled` |
| `PrometheusRule` | All 10 alert rules, from the same file the Compose stack and the promtool tests use | `prometheusRule.enabled` |
| `ConfigMap` | The 14-panel dashboard, labelled for the Grafana sidecar | `dashboard.enabled` |
| Mock `Deployment` + `Service` | In-cluster fake cabinet — the `--profile demo` equivalent | `mock.enabled` |
| Triage `Deployment` + `Service` + `Secret` | The AI alert-triage agent | `triage.enabled` |

---

## 🚀 Install

**Demo — a scratch cluster, no vehicle, no credentials:**

```bash
helm upgrade --install vt ./observability/vehicle-telemetry/deploy/chart \
  -n vehicle-telemetry --create-namespace \
  -f ./observability/vehicle-telemetry/deploy/chart/values-demo.yaml
```

The mock runs in-cluster and the exporter points at it automatically — `PANDORA_HOST` and
`PANDORA_SCHEME` are derived, not configured. Operator CRDs and the Grafana sidecar are
assumed absent in demo mode, so those objects are off.

**Real cabinet:**

```bash
kubectl -n vehicle-telemetry create secret generic pandora-credentials \
  --from-literal=PANDORA_LOGIN='you@example.com' \
  --from-literal=PANDORA_PASSWORD='...'

helm upgrade --install vt ./observability/vehicle-telemetry/deploy/chart \
  -n vehicle-telemetry --create-namespace \
  --set pandora.existingSecret=pandora-credentials \
  --set pandora.deviceIds=1234567890 \
  --set loki.url=http://loki.monitoring.svc:3100
```

**Not using Helm?** Render plain manifests and apply them:

```bash
helm template vt ./observability/vehicle-telemetry/deploy/chart \
  -n vehicle-telemetry > manifests.yaml
```

---

## 🐙 ArgoCD

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: vehicle-telemetry
  namespace: argocd
spec:
  project: tobrazo
  source:
    repoURL: https://github.com/tobrazo/devops
    targetRevision: main
    path: observability/vehicle-telemetry/deploy/chart
    helm:
      valueFiles:
        - values.yaml
      parameters:
        - name: pandora.existingSecret
          value: pandora-credentials
  destination:
    server: https://kubernetes.default.svc
    namespace: vehicle-telemetry
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions: [CreateNamespace=true]
```

Namespace comes from `destination.namespace` — the chart has no `namespace` value, by repo
convention.

---

## ⚙️ Values worth knowing

| Value | Default | Notes |
|---|---|---|
| `pandora.existingSecret` | `""` | **Set this for anything real.** Empty renders a Secret from `pandora.login`/`.password`, which are placeholders. |
| `pandora.host` / `.scheme` | `pro.p-on.ru` / `https` | Ignored when `mock.enabled` — the mock Service wins. |
| `pandora.loginPath` / `.loginField` / `.loginFormat` | `/api/users/login` / `login` / `json` | The cabinet has no public API; these absorb a UI change without a code change. |
| `loki.url` | `""` | Empty disables event shipping entirely. Set it and the cabinet's event feed lands in Loki as `{job="pandora"}`. |
| `loki.eventsKey` | `lenta` | An educated guess, not a verified contract. The exporter logs the payload keys it actually received on its first poll. |
| `serviceMonitor.labels` | `release: prometheus` | Must match what your Prometheus selects on, or the target never appears. |
| `dashboard.label` | `grafana_dashboard` | What the Grafana sidecar watches for. |
| `triage.existingSecret` | `""` | Same story as the cabinet Secret, for `ANTHROPIC_API_KEY`. |

Full list with comments in [`values.yaml`](values.yaml); `values.schema.json` type-checks them
on `helm lint`/`template` — a bad `pandora.scheme` fails before anything reaches the cluster.

---

## 🔁 The two synced files

`files/pandora-rules.yml` and `files/pandora-vehicle.json` are copies of the canonical
`alerts/` and `dashboards/` files one level up. Helm cannot read outside the chart directory,
so a copy is unavoidable — but **CI diffs them and fails on drift**, which makes the
duplication mechanical rather than a promise. After editing either source:

```bash
cp ../../alerts/pandora-rules.yml ../../dashboards/pandora-vehicle.json files/
```

---

## ✅ Validate

```bash
helm lint .
helm lint . -f values-demo.yaml
helm template vt . -n vehicle-telemetry > /dev/null
helm template vt . -n vehicle-telemetry -f values-demo.yaml > /dev/null
helm template vt . -n vehicle-telemetry --set triage.enabled=true --set loki.url=http://loki:3100 > /dev/null
```

---

## 🔐 Notes

- **The exporter is a singleton**: `replicas: 1` with `strategy: Recreate`, because Pandora
  session cookies aren't shareable and two pods would fight over the session. Don't scale it.
- **`/metrics` carries `pandora_position_lat/lon`** — the vehicle's live location. The Service
  is `ClusterIP` and the chart deliberately renders no Ingress.
- All three workloads run **non-root with a read-only root filesystem**, no privilege
  escalation, all capabilities dropped.
- Credentials in `values.yaml` are placeholders and must stay that way — the chart is in a
  public repo. Use `existingSecret` with Vault, sealed-secrets or SOPS.
