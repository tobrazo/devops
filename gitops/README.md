<div align="center">

# 🐙 GitOps Platform

**A reusable ArgoCD app-of-apps — metrics, logs, tracing, TLS/DNS, progressive delivery, and secrets on day one.**

![ArgoCD](https://img.shields.io/badge/ArgoCD-app--of--apps-EF7B4D?style=flat-square&logo=argo&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![GitOps](https://img.shields.io/badge/GitOps-declarative-1A73E8?style=flat-square&logo=git&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?style=flat-square&logo=prometheus&logoColor=white)

</div>

---

Everything a new project needs on its first sync — observability, TLS/DNS automation, progressive delivery, secrets, and real-time messaging — plus a ready-to-copy **nginx** workload wired as an Argo Rollouts blue/green deployment.

Drop a new `Application` into `clusters/<env>/apps/workloads/` and the recursing root picks it up automatically.

---

## 🏗️ Architecture

Single cluster, app-of-apps. Two root Applications fan out to the platform and the workloads.

```mermaid
flowchart TD

subgraph git["Git Repository"]
  repo["tobrazo/devops<br/>main · gitops/"]
end

subgraph argocd["ArgoCD"]
  platform_root["platform-root"]
  workloads_root["workloads-root"]
  image_updater["Image Updater"]
end

subgraph platform["Platform Apps"]
  observ["Prometheus · Grafana<br/>Loki · Tempo · OTel"]
  netsec["cert-manager · external-dns<br/>Vault"]
  rollouts["Argo Rollouts"]
  redis[("Redis")]
end

subgraph workloads["Workload Apps"]
  nginx["nginx-prod<br/>blue/green Rollout"]
end

repo -->|sync| platform_root
repo -->|sync| workloads_root
platform_root --> observ
platform_root --> netsec
platform_root --> rollouts
platform_root --> redis
workloads_root --> nginx
image_updater -.->|update tags| workloads_root

classDef edge stroke:#64748b,stroke-width:2px,stroke-dasharray:4 3;
classDef ctrl stroke:#6366f1,stroke-width:2px;
classDef obs stroke:#0ea5e9,stroke-width:2px;
classDef warn stroke:#ef4444,stroke-width:2px;
classDef deliver stroke:#10b981,stroke-width:2px;
classDef data stroke:#f59e0b,stroke-width:2px;

class repo edge;
class platform_root,workloads_root,image_updater ctrl;
class observ obs;
class netsec warn;
class rollouts,nginx deliver;
class redis data;

style git fill:transparent,stroke:#94a3b8,stroke-width:1px
style argocd fill:transparent,stroke:#94a3b8,stroke-width:1px
style platform fill:transparent,stroke:#94a3b8,stroke-width:1px
style workloads fill:transparent,stroke:#94a3b8,stroke-width:1px
```

---

## 🔀 CI/CD Flow

```mermaid
flowchart LR

code["Code Push"] -->|trigger| build["Build Image"]
build --> push["Push to GHCR"]
push --> image["ghcr.io/tobrazo/*"]
image -.->|watch| updater["Image Updater<br/>newest-build"]
updater -->|write-back| sync["ArgoCD Sync"]
sync --> deploy["Rollout / Deploy"]
deploy --> pods["New Pods"]

classDef edge stroke:#64748b,stroke-width:2px,stroke-dasharray:4 3;
classDef data stroke:#f59e0b,stroke-width:2px;
classDef ctrl stroke:#6366f1,stroke-width:2px;
classDef deliver stroke:#10b981,stroke-width:2px;

class code edge;
class build,push,image data;
class updater,sync ctrl;
class deploy,pods deliver;
```

---

## 📂 Directory Structure

```text
gitops/
├── clusters/
│   └── prod/                         # Single-cluster app-of-apps
│       ├── project-platform.yaml     # AppProject: platform
│       ├── project-tobrazo.yaml      # AppProject: tobrazo (workloads)
│       └── apps/
│           ├── platform-root.yaml    # app-of-apps root (platform)
│           ├── workloads-root.yaml   # app-of-apps root (workloads)
│           ├── platform/             # 15 platform Applications
│           └── workloads/            # Workload Applications (nginx-prod)
├── platform/                         # Shared platform manifests / charts
│   ├── cert-manager-external-dns/    # ClusterIssuer + DNS token secret
│   ├── monitoring/                   # Prometheus, Grafana, dashboards
│   ├── logging/                      # Loki, event-exporter
│   ├── otel/                         # OpenTelemetry operator, Tempo
│   ├── vault/                        # HashiCorp Vault runbook + RBAC
│   ├── argo-rollouts/                # Progressive delivery values
│   ├── image-updater/                # argocd-image-updater values
│   ├── redis/                        # bitnami redis values
│   └── centrifugo/                   # Real-time messaging chart
├── workloads/
│   └── nginx/                        # Example nginx blue/green Rollout chart
└── reset-argocd-apps.sh              # Recovery script
```

> [!NOTE]
> Single cluster, namespace-per-component. Argo Rollouts CRDs are installed by the `argo-rollouts` platform app (sync-wave `-5`, chart-managed), so the nginx workload's `Rollout` resolves on first sync.

---

## 🧱 Root Applications

Two root ArgoCD Applications manage everything (app-of-apps):

| Application | Path | Project | Purpose |
|-------------|------|---------|---------|
| `platform-root` | `gitops/clusters/prod/apps/platform/` | `platform` | Infrastructure components |
| `workloads-root` | `gitops/clusters/prod/apps/workloads/` | `tobrazo` | Application deployments |

Both use `directory.recurse: true` — child Applications are discovered automatically, so adding a workload is just dropping a YAML file into the `workloads/` folder.

---

## 🚀 Bootstrap

<details open>
<summary><b>Apply the AppProjects and roots, then watch it converge</b></summary>

```bash
# 1) AppProjects
kubectl apply -f clusters/prod/project-platform.yaml
kubectl apply -f clusters/prod/project-tobrazo.yaml

# 2) Root applications (app-of-apps)
kubectl apply -f clusters/prod/apps/platform-root.yaml
kubectl apply -f clusters/prod/apps/workloads-root.yaml

# 3) Watch it converge
argocd app list
argocd app get platform-root
```
</details>

> [!IMPORTANT]
> Some components need secrets you provide — they are **not** committed. Before syncing, create: the cert-manager/external-dns Cloudflare API token (`platform/cert-manager-external-dns/secrets.yaml` ships placeholders), the Grafana admin password, and the Alertmanager Discord webhook. See the `REPLACE_WITH_*` / `changeme` placeholders in `platform/monitoring/kube-prometheus/values*.yaml`.

> [!WARNING]
> Vault installs via GitOps but **init / unseal / configure is a manual runbook** — unseal keys and the root token must never live in Git. Follow `platform/vault/README.md` after the `vault` app is synced.

---

## 🕒 Workloads Sync Order

Applications deploy in order using `sync-wave` annotations. This template ships a single demo workload:

| Wave | Application | Namespace |
|------|-------------|-----------|
| 1 | nginx-prod | nginx-demo |

Add more workloads at higher waves as needed (backend → frontend → …).

---

## 🧱 Platform Stack

```mermaid
flowchart TB

subgraph observability["Observability"]
  prometheus["Prometheus<br/>Metrics"]
  grafana["Grafana<br/>Dashboards"]
  loki["Loki<br/>Logs"]
  tempo["Tempo<br/>Traces"]
  otel["OTel Collector"]
end

subgraph networking["Networking & Security"]
  certmgr["cert-manager<br/>TLS Certificates"]
  extdns["external-dns<br/>DNS Automation"]
  ingress["NGINX Ingress"]
  vault["Vault<br/>Secrets"]
end

subgraph delivery["Delivery"]
  rollouts["Argo Rollouts<br/>Blue/Green · Canary"]
end

subgraph data["Data"]
  redis[("Redis<br/>Cache")]
end

subgraph apps["Applications"]
  workload["Workload Pods"]
end

workload -->|metrics| prometheus
workload -->|logs| loki
workload -->|traces| otel
otel --> tempo
prometheus --> grafana
loki --> grafana
tempo --> grafana
certmgr -->|TLS| ingress
extdns -->|DNS| ingress
rollouts -->|manages| workload
vault -.->|secrets| workload
workload --> redis

classDef obs stroke:#0ea5e9,stroke-width:2px;
classDef ctrl stroke:#6366f1,stroke-width:2px;
classDef warn stroke:#ef4444,stroke-width:2px;
classDef deliver stroke:#10b981,stroke-width:2px;
classDef data stroke:#f59e0b,stroke-width:2px;

class prometheus,grafana,loki,tempo,otel obs;
class certmgr,extdns,ingress ctrl;
class vault warn;
class rollouts deliver;
class redis data;
class workload deliver;

style observability fill:transparent,stroke:#94a3b8,stroke-width:1px
style networking fill:transparent,stroke:#94a3b8,stroke-width:1px
style delivery fill:transparent,stroke:#94a3b8,stroke-width:1px
style data fill:transparent,stroke:#94a3b8,stroke-width:1px
style apps fill:transparent,stroke:#94a3b8,stroke-width:1px
```

---

## 🧩 Platform Components

15 ArgoCD Applications, ordered by `sync-wave`:

| Wave | Application | Chart / Source | Namespace | Purpose |
|------|-------------|----------------|-----------|---------|
| -5 | `argo-rollouts` | argoproj | argo-rollouts | Progressive delivery + CRDs |
| 0 | `prometheus-crds` | prometheus-community | argocd | Prometheus operator CRDs |
| 3 | `redis` | bitnami | redis | In-memory cache |
| 5 | `prometheus-stack` | prometheus-community | monitoring | Metrics & Grafana |
| 5 | `loki-stack` | grafana | logs | Log aggregation |
| 5 | `opentelemetry-operator` | open-telemetry | monitoring | Auto-instrumentation |
| 5 | `centrifugo` | in-tree chart | centrifugo | Real-time messaging |
| 5 | `vault` | hashicorp | vault | Secrets management |
| 8 | `cert-manager` | jetstack | cert-manager | TLS certificates |
| 10 | `tempo` | grafana | monitoring | Distributed tracing |
| 15 | `cert-manager-issuer` | in-tree | cert-manager | ClusterIssuer (ACME) |
| 15 | `monitoring-custom` | in-tree | monitoring | Dashboards & alert rules |
| 15 | `otel-additional-resources` | in-tree | monitoring | Collector / instrumentation |
| 20 | `external-dns` | kubernetes-sigs | kube-system | DNS automation |
| 20 | `argocd-image-updater` | argoproj | argocd | Image auto-updates |

---

## 🔄 Image Updater

Workload Applications can carry ArgoCD Image Updater annotations:

```yaml
annotations:
  argocd-image-updater.argoproj.io/image-list: app=ghcr.io/tobrazo/app
  argocd-image-updater.argoproj.io/app.update-strategy: newest-build
  argocd-image-updater.argoproj.io/app.pull-secret: pullsecret:argocd/ghcr-creds
  argocd-image-updater.argoproj.io/write-back-method: argocd
```

New images are detected and the tag is written back into the Application automatically.

---

## ➕ Adding a New Workload

<details>
<summary><b>Copy the nginx chart, add an Application, commit</b></summary>

1. Add a Helm chart under `workloads/<app-name>/` (copy `workloads/nginx/` as a starting point).

2. Add an ArgoCD Application in `clusters/prod/apps/workloads/<app-name>-prod.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: <app-name>-prod
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "<priority>"
spec:
  project: tobrazo
  source:
    repoURL: https://github.com/tobrazo/devops
    path: gitops/workloads/<app-name>
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: <namespace>
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

3. Commit and push — the recursing `workloads-root` picks it up and ArgoCD syncs.
</details>

---

## 🧪 Roadmap / TODOs

- Store webhook URLs and API tokens in Vault (out of Git).
- Add NetworkPolicies for workload isolation.
- Add a canary example alongside the blue/green nginx workload.
