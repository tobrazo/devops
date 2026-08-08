<div align="center">

# ⎈ Helm Charts

**Standalone, cloud-agnostic Helm charts — validated, secret-free, ready to `helm install`.**

![Helm](https://img.shields.io/badge/Helm-3-0F1689?style=flat-square&logo=helm&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![helm lint](https://img.shields.io/badge/helm_lint-passing-3FB950?style=flat-square)

</div>

---

Each chart here stands on its own, ships sane defaults plus a production overlay where relevant, and passes `helm lint` / `helm template`. For the GitOps app-of-apps platform that deploys workloads via ArgoCD, see [`../gitops`](../gitops).

## 🧱 What's inside

| Chart | What it demonstrates |
|-------|----------------------|
| 🧠 **[redis-stack-cluster](redis-stack-cluster)** | A 6-node Redis Stack cluster (RediSearch + RedisJSON) with self-healing `nodes.conf` IP reconciliation, a bootstrap Job, Prometheus exporter, non-root securityContext, and an opt-in NetworkPolicy. |
| 🔀 **[argo-rollouts-blue-green](argo-rollouts-blue-green)** | Progressive delivery with **Argo Rollouts** — active/preview services, a real k6 pre-promotion gate, preview ingress, HPA/PDB, and a matching ArgoCD Application. Toggles to a plain Deployment. |
| 📦 **[kubernetes-event-exporter](kubernetes-event-exporter)** | A thin wrapper around the upstream event-exporter chart — a `start.sh` helper for install/upgrade/delete/debug and example receiver config. |

## ✅ Lint them all

```bash
for chart in redis-stack-cluster argo-rollouts-blue-green; do
  helm lint "./$chart"
done
```

> [!NOTE]
> `argo-rollouts-blue-green` renders Argo Rollouts CRDs (`Rollout`, `AnalysisTemplate`); install the CRDs before applying it to a live cluster. `kubernetes-event-exporter` is a script-driven wrapper rather than a standalone chart — see its README for the `start.sh` workflow.
