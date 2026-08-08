---
name: new-workload
description: Scaffold a new GitOps workload (a blue/green Rollout app) into the ArgoCD app-of-apps. Use when asked to "add a workload", "add an app to gitops", "deploy X via ArgoCD", or "create a new service in the platform".
---

# Add a new GitOps workload

Workloads are wired by the recursing `workloads-root` — you only create (1) a chart under `gitops/workloads/<name>/` and (2) an `Application` under `gitops/clusters/prod/apps/workloads/<name>-prod.yaml`. Ask the user for the app **name**, container **image**, and container **port** if not given.

## 1. Copy the nginx chart as the starting point

```bash
NAME="<name>"                                   # e.g. api, web, worker
cp -r gitops/workloads/nginx "gitops/workloads/$NAME"
```

Then edit `gitops/workloads/$NAME/`:
- `Chart.yaml` — set `name: $NAME`, description, `appVersion`, `icon`.
- `values.yaml` — set `image.repository`/`tag`/`pullPolicy`, `service.activeName: $NAME-active`, `service.previewName: $NAME-preview`, `service.targetPort`, probe path/port. Keep `rollout.autoPromotionEnabled: false` for manual promotion.
- Templates already use `{{ .Release.Namespace }}` and `{{ include "nginx.fullname" . }}` — rename the helper define in `templates/_helpers.tpl` to `$NAME.fullname` and update the includes, **or** leave the `nginx.*` helper name (it's internal and harmless). Prefer renaming for a clean chart.

## 2. Create the ArgoCD Application

Copy `gitops/clusters/prod/apps/workloads/nginx-prod.yaml` to `<name>-prod.yaml` and set:
- `metadata.name: $NAME-prod`, a sensible `sync-wave`.
- `spec.project: tobrazo`
- `spec.source.path: gitops/workloads/$NAME`
- `spec.destination.namespace: $NAME` (or a chosen namespace)
- `ignoreDifferences`: the active/preview Service names + namespace (Rollout injects `/spec/selector`).

Nothing else to register — `workloads-root` recurses `apps/workloads/` and picks it up.

## 3. Validate

Run the `validate-charts` skill (which lints/renders the new chart and checks refs), then `sanitize-check`. Confirm:

```bash
helm template $NAME gitops/workloads/$NAME -n $NAME | grep -E '^kind:'
```
renders `Rollout` + two `Service`s (and a `PodDisruptionBudget` if `pdb.enabled`).
