# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **public** DevOps portfolio: reusable, cloud-agnostic Kubernetes/Helm charts, a full ArgoCD GitOps platform, plus Terraform/Ansible/Python samples. Everything is a **template** — no real infrastructure, no live credentials.

### The #1 invariant: it stays company-neutral and secret-free

This content was sanitized from private work. Before adding or editing anything, keep it that way:

- **No company/PII identifiers.** The neutral brand token is **`tobrazo`**; example domains are **`example.com`** (`.org`/`.net`/`.internal` for extras). Never introduce real company names, real domains, real IPs, or personal emails.
- **No live secrets.** Only placeholders: `REPLACE_WITH_*`, `changeme`, or references to a Kubernetes `Secret`/Vault the user provides. Never commit a real token/password/key.
- Run the sanitization check before committing (see Validation).

## Common commands

```bash
# Lint + render every in-tree Helm chart (what CI runs)
for c in helm-charts/redis-stack-cluster helm-charts/argo-rollouts-blue-green \
         gitops/workloads/nginx gitops/platform/centrifugo; do
  helm lint "$c"
done

# Render a chart (proves it obeys -n and both modes)
helm template redis helm-charts/redis-stack-cluster -n redis -f helm-charts/redis-stack-cluster/values-production.yaml
helm template app  helm-charts/argo-rollouts-blue-green -n demo                              # blue/green Rollout
helm template app  helm-charts/argo-rollouts-blue-green -n demo -f helm-charts/argo-rollouts-blue-green/values-deployment.yaml   # plain Deployment
helm template nginx gitops/workloads/nginx -n nginx-demo

# Build the kustomize manifest dirs
kubectl kustomize gitops/platform/monitoring/manifests
kubectl kustomize gitops/platform/otel/additional-resources
```

CI: `.github/workflows/helm-ci.yaml` runs `helm lint` + `helm template` (blocking) and `kube-linter` (informational) on pushes/PRs touching `helm-charts/**` or `gitops/**`. Helm 3 is required (`helm version` → v3.x).

## Helm chart conventions (apply to every chart here)

- **Namespace comes from the release, never a value.** Templates use `{{ .Release.Namespace }}` — there is **no** `.Values.namespace` key. This is deliberate: it makes `helm install -n <ns>` and ArgoCD `destination.namespace` the single source of truth. Do not reintroduce a `namespace` value.
- **`fullname` helpers** are `{{ .Release.Name | trunc 63 | trimSuffix "-" }}` (DNS-label safe). Reuse the pattern in new charts.
- **`values.schema.json`** validates each chart's values on `helm lint`/`template` — update it when you add required/typed values.
- Charts ship `NOTES.txt`, an `icon`, and full `Chart.yaml` metadata (maintainers/keywords/sources).

### Blue/green charts (`argo-rollouts-blue-green`, `gitops/workloads/nginx`)
- One chart renders **either** an Argo `Rollout` (blue/green) **or** a plain `Deployment`, switched by `controller.type`. Rollout-only resources (preview Service/ingress, AnalysisTemplate, k6 ConfigMap) are gated on `eq .Values.controller.type "rollout"`.
- Active/preview Services carry **only** an `app: <fullname>` selector — the Rollout controller injects `rollouts-pod-template-hash`. The ArgoCD `Application` must `ignoreDifferences` on those Services' `/spec/selector` and the Rollout's `/spec/replicas` (HPA-owned), or ArgoCD fights the controller.
- The k6 pre-promotion gate targets the **in-cluster preview Service** via `PREVIEW_URL` env (not a public URL) and uses `failureLimit: 0` so it can actually fail a bad build.

### `redis-stack-cluster`
- A StatefulSet Redis Cluster. Pod IPs change on reschedule, so a `postStart` hook runs `fix-ip.sh` (embedded in a ConfigMap) to reconcile the `myself` line of `nodes.conf`. The `sed` is intentionally scoped to the `myself` line with escaped metacharacters — do not broaden it to a global replace.
- Security posture is NetworkPolicy (opt-in) + non-root `securityContext` + `protected-mode no` for in-cluster clustering; auth is bring-your-own-Secret (never put a password in the ConfigMap).

## GitOps platform (`gitops/`)

App-of-apps on a **single cluster, namespace-per-component**.

- **Entry points:** `clusters/prod/apps/platform-root.yaml` and `workloads-root.yaml` are two ArgoCD `Application`s with `directory.recurse: true`. They discover every child `Application` under `apps/platform/` and `apps/workloads/` — so **adding a workload = dropping one `Application` YAML** into `apps/workloads/` (copy `workloads/nginx` + `clusters/prod/apps/workloads/nginx-prod.yaml` as the pattern).
- **AppProjects** are defined in `clusters/prod/project-{platform,tobrazo}.yaml`. Roots and every child app reference one of these two projects; `tobrazo` (workloads) is least-privilege (namespaced resources + own Namespace only).
- **Multi-source values pattern:** external-chart apps use two sources — the upstream chart repo + a `ref: values` source pointing at this repo — and load values via `$values/gitops/platform/<component>/values.yaml`. When you change a component's values path, update the `$values/...` reference; it must resolve from the **repo root**.
- **Sync-waves** order the graph: `argo-rollouts` at wave `-5` installs its CRDs before any workload `Rollout` (wave `1`) syncs; cert-manager (8) before its ClusterIssuer (15); etc.
- **Bootstrap / reset:** apply the two projects + two roots (see `gitops/README.md`), or `gitops/reset-argocd-apps.sh`.
- Some components need secrets you provide before they go healthy: cert-manager/external-dns (Cloudflare token), Grafana/Alertmanager/Centrifugo (placeholder passwords). Vault install is GitOps; **init/unseal/configure is a manual runbook** (`gitops/platform/vault/README.md`) — unseal keys must never be in Git.

## Other trees

- `ansible/` — standalone roles (haproxy, redis+sentinel, redis/zfs exporters, etcd maintenance) and a Prometheus/alerting config set. Each has its own README and playbook (`*.yml`).
- `terraform/web-server/` — a single cloud web-server module (`WebServer.tf` + `userdata.tpl`).
- `python/evmpolls_scraper/` — a standalone scraper (`requirements.txt`).

## Validation before committing

```bash
# 1) charts must lint clean and render  (run the lint loop above)
# 2) sanitization gate — must return CLEAN (generic leak signatures; see the
#    sanitize-check skill for the full scan + how-to-fix)
grep -rniE 'dop_v1|GOCSPX|AKIA[0-9A-Z]{16}|hvs\.[A-Za-z0-9]{6}|discord\.com/api/webhooks/[0-9]|BEGIN (RSA|EC|OPENSSH|PRIVATE)|[0-9]{1,3}(\.[0-9]{1,3}){3}|@(gmail|yahoo|outlook)\.com' \
  helm-charts gitops --include='*.yaml' --include='*.yml' --include='*.tpl' --include='*.js' \
  | grep -vE '0\.0\.0\.0|127\.0\.0\.1|10\.[0-9]|192\.168|example\.(com|org|net|internal)|kubernetes\.default' || echo CLEAN
```

Also eyeball for real company/product names (→ `tobrazo`) and real domains (→ `example.com`); a regex won't reliably catch those.

Commit/push only when the user asks. Repo default branch is `main`; work on a feature branch and open a PR.
