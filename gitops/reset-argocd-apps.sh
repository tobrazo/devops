#!/bin/bash
set -euo pipefail

# Wipes ArgoCD Application state and re-applies the two roots from Git.
# Destructive — it deletes every Application in the argocd namespace.

ARGO_NS="argocd"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Resetting ArgoCD state in namespace: $ARGO_NS"

echo "🧹 Terminating any running sync operations..."
for app in $(argocd app list -o name 2>/dev/null || true); do
  argocd app terminate-op "$app" || true
done

echo "🔥 Deleting all ArgoCD Applications..."
kubectl -n "$ARGO_NS" delete applications --all --ignore-not-found

echo "🧠 Clearing ArgoCD repo-server cache..."
kubectl -n "$ARGO_NS" delete pods -l app.kubernetes.io/name=argocd-repo-server --ignore-not-found

echo "📦 Re-applying AppProjects and roots..."
kubectl apply -f "$REPO_ROOT/clusters/prod/project-platform.yaml"
kubectl apply -f "$REPO_ROOT/clusters/prod/project-tobrazo.yaml"
kubectl apply -f "$REPO_ROOT/clusters/prod/apps/platform-root.yaml"
kubectl apply -f "$REPO_ROOT/clusters/prod/apps/workloads-root.yaml"

echo "✅ Reset complete. ArgoCD will redeploy everything from Git."
