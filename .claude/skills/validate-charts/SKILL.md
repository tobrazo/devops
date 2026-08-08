---
name: validate-charts
description: Validate every Helm chart and kustomize dir in this repo — lint, render in all modes, and build kustomize. Use before committing chart/gitops changes, or when asked to "validate", "check the charts", "does it still render", or "is this safe to push".
---

# Validate charts

Run this from the repo root. Report a concise pass/fail table; if anything fails, show the error and stop.

## 1. Lint + render every in-tree Helm chart

```bash
set -e
for c in helm-charts/redis-stack-cluster helm-charts/argo-rollouts-blue-green \
         gitops/workloads/nginx gitops/platform/centrifugo; do
  echo "== $c =="
  helm lint "$c"
done
```

## 2. Render each chart in every mode (proves templates + values.schema.json)

```bash
helm template redis helm-charts/redis-stack-cluster -n redis \
  -f helm-charts/redis-stack-cluster/values-production.yaml > /dev/null
helm template redis helm-charts/redis-stack-cluster -n redis > /dev/null
helm template app  helm-charts/argo-rollouts-blue-green -n demo > /dev/null
helm template app  helm-charts/argo-rollouts-blue-green -n demo \
  -f helm-charts/argo-rollouts-blue-green/values-deployment.yaml > /dev/null
helm template nginx gitops/workloads/nginx -n nginx-demo > /dev/null
helm template centrifugo gitops/platform/centrifugo -n centrifugo > /dev/null
```

## 3. Build the kustomize dirs

```bash
for d in gitops/platform/monitoring/manifests \
         gitops/platform/otel/additional-resources \
         gitops/platform/monitoring/kube-prometheus/crd; do
  kubectl kustomize "$d" > /dev/null && echo "OK $d"
done
```

## 4. Verify ArgoCD refs resolve (no dangling `$values`/`path`)

```bash
# $values/... must resolve from the repo root
grep -rhoE '\$values/[^ ]+' gitops/clusters --include='*.yaml' | sort -u | while IFS= read -r r; do
  rel="${r#\$values/}"; [ -e "$rel" ] && echo "OK  $r" || echo "MISSING $r"
done
```

## 5. Finish with the sanitization gate

Invoke the `sanitize-check` skill (or its grep) — a chart is not "ready" until it is both valid **and** company/secret-free.
