# DevOps Lab

![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-326ce5?logo=kubernetes&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-3-0f1689?logo=helm&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-EF7B4D?logo=argo&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform&logoColor=white)
![Ansible](https://img.shields.io/badge/Ansible-Automation-EE0000?logo=ansible&logoColor=white)
![Prometheus](https://img.shields.io/badge/Observability-Prometheus%20%C2%B7%20Loki%20%C2%B7%20Tempo-E6522C?logo=prometheus&logoColor=white)

A hands-on collection of production-grade DevOps building blocks — Kubernetes Helm charts, a full GitOps platform, Terraform modules, Ansible roles, and monitoring configs. Everything here is self-contained, cloud-agnostic, and validated (`helm lint` clean).

---

## 🌟 Highlights

| Component | What it demonstrates |
|-----------|----------------------|
| **[helm-charts/redis-stack-cluster](helm-charts/redis-stack-cluster)** | A 6-node Redis Stack (RediSearch + RedisJSON) cluster on Kubernetes with a self-healing `nodes.conf` IP-reconciliation hook, cluster-bootstrap Job, PDB, and Prometheus exporter. |
| **[helm-charts/argo-rollouts-blue-green](helm-charts/argo-rollouts-blue-green)** | Progressive delivery with **Argo Rollouts blue/green** — active/preview services, pre-promotion k6 analysis gate, preview ingress, HPA & PDB, plus the matching ArgoCD Application. Toggles to a plain Deployment via one value. |
| **[gitops/](gitops)** | A complete **ArgoCD app-of-apps platform template**: metrics (kube-prometheus-stack), logs (Loki), tracing (Tempo + OpenTelemetry), TLS/DNS (cert-manager + external-dns), progressive delivery (Argo Rollouts), secrets (Vault), and a ready-to-copy nginx blue/green workload. |

---

## 📂 Repository Structure

```text
devops/
├── helm-charts/                     # Kubernetes Helm charts
│   ├── redis-stack-cluster/         # Redis Stack cluster (StatefulSet)
│   ├── argo-rollouts-blue-green/    # Blue/green delivery example
│   └── kubernetes-event-exporter/   # Cluster event → sink exporter
├── gitops/                          # ArgoCD app-of-apps platform template
│   ├── clusters/{dev,prod}/         # Per-cluster app-of-apps + AppProjects
│   ├── platform/                    # monitoring · logging · otel · cert-manager
│   │                                #   · argo-rollouts · vault · centrifugo
│   └── workloads/nginx/             # Example blue/green workload chart
├── terraform/                       # Infrastructure as Code
│   └── web-server/                  # Cloud web server module
├── ansible/                         # Configuration management roles
│   ├── ansible-redis-cluster-role/  # Redis + Sentinel
│   ├── ansible-haproxy-reverse-proxy-role/
│   ├── ansible-redis-exporter-role/
│   ├── ansible-zfs-exporter-role/
│   ├── etcd-maintenance/
│   └── prometheus-configs/          # Alert rules & exporters config
└── python/                          # Tooling & scripts
    └── evmpolls_scraper/
```

---

## 🚀 Quick Starts

**Redis Stack cluster**
```bash
helm upgrade --install redis ./helm-charts/redis-stack-cluster \
  -n redis --create-namespace -f ./helm-charts/redis-stack-cluster/values-production.yaml
```

**Blue/green app (Argo Rollouts)**
```bash
helm upgrade --install tobrazo-app ./helm-charts/argo-rollouts-blue-green \
  -n tobrazo-app --create-namespace
kubectl argo rollouts get rollout tobrazo-app -n tobrazo-app
```

**GitOps platform (app-of-apps)**
```bash
kubectl apply -f gitops/clusters/prod/project-platform.yaml
kubectl apply -f gitops/clusters/prod/project-tobrazo.yaml
kubectl apply -f gitops/clusters/prod/apps/platform-root.yaml
kubectl apply -f gitops/clusters/prod/apps/workloads-root.yaml
```

Each component ships its own README with architecture diagrams, a configuration reference, and validation steps.

---

## ✅ Validation

All Helm charts pass `helm lint` and render with `helm template`. The blue/green and nginx charts use Argo Rollouts CRDs (installed by the `gitops/` platform) — install those before applying to a live cluster.

```bash
helm lint ./helm-charts/redis-stack-cluster
helm lint ./helm-charts/argo-rollouts-blue-green
helm lint ./gitops/workloads/nginx
```

---

## 🔐 A note on secrets

This repo is a **template**: every credential is a placeholder (`REPLACE_WITH_*`, `changeme`) or referenced from a Kubernetes `Secret` / Vault that you provide. Nothing here is a live secret — create your own before deploying.
