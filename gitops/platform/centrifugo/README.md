<div align="center">

# 📡 Centrifugo

**Minimal in-tree Helm chart for a scalable real-time messaging server (WebSocket / SSE / HTTP-stream).**

![Centrifugo](https://img.shields.io/badge/Centrifugo-v6-1A73E8?style=flat-square)
![Redis](https://img.shields.io/badge/Redis-engine-DC382D?style=flat-square&logo=redis&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-managed-EF7B4D?style=flat-square&logo=argo&logoColor=white)

</div>

---

A platform component that deploys [Centrifugo](https://centrifugal.dev/) with a Redis engine so it can scale horizontally.

## 🧱 What it deploys

- A Centrifugo `Deployment` (image `centrifugo/centrifugo:v6`).
- A `ConfigMap` with `config.json` — Redis engine, health check, and admin web UI.
- A `Service` (ClusterIP, port `8000`).

## ⚙️ Configuration

Set values in `values.yaml` (or via ArgoCD `$values`):

| Value | Default | Purpose |
|-------|---------|---------|
| `redis.host` / `redis.port` | `redis-master.redis.svc.cluster.local` / `6379` | Redis engine backend (for horizontal scaling). |
| `adminWeb.password` | `changeme` | Admin web UI password. |
| `service.port` | `8000` | Client-facing port. |

> [!WARNING]
> `adminWeb.password` ships as `changeme`. **Override it** per environment (or wire it from a `Secret`) before exposing the admin web UI.

## 🚀 Deploy

Managed by ArgoCD via `clusters/*/apps/platform/centrifugo.yaml`, or standalone:

```bash
helm upgrade --install centrifugo . -n centrifugo --create-namespace
```
