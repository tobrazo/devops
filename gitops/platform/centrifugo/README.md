# Centrifugo

Minimal in-tree Helm chart for [Centrifugo](https://centrifugal.dev/) — a scalable real-time messaging server (WebSocket/SSE/HTTP-stream) used as a platform component.

## What it deploys
- A Centrifugo `Deployment` (image `centrifugo/centrifugo:v6`).
- A `ConfigMap` with `config.json` (Redis engine, admin web UI).
- A `Service` (ClusterIP, port 8000).

## Configuration
Set values in `values.yaml` (or via ArgoCD `$values`):

| Value | Purpose |
|-------|---------|
| `redis.host` / `redis.port` | Redis engine backend (for horizontal scaling). |
| `adminWeb.password` | Admin web UI password — **override this**, don't ship `changeme`. |
| `service.port` | Client-facing port (default 8000). |

## Deploy
Managed by ArgoCD via `clusters/*/apps/platform/centrifugo.yaml`, or standalone:

```bash
helm upgrade --install centrifugo . -n centrifugo --create-namespace
```
