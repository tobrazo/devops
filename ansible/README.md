<div align="center">

# 🤖 Ansible Roles

**Standalone configuration-management roles & playbooks — bare-metal services, Prometheus exporters, and cluster ops.**

Each directory is self-contained: an example playbook at the root plus a `roles/` tree.

<br/>

![Ansible](https://img.shields.io/badge/Ansible-roles-EE0000?style=flat-square&logo=ansible&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-cluster%20%2B%20exporter-DC382D?style=flat-square&logo=redis&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-exporters-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![HAProxy](https://img.shields.io/badge/HAProxy-reverse%20proxy-106DA9?style=flat-square&logo=haproxy&logoColor=white)
![etcd](https://img.shields.io/badge/etcd-maintenance-419EDA?style=flat-square&logo=etcd&logoColor=white)

</div>

---

## 🗺️ At a glance

```mermaid
flowchart LR
  inv["📇 Your inventory<br/>(hosts + groups)"] --> ans["🤖 ansible-playbook"]
  ans --> svc["🔀 Services<br/>haproxy · redis + sentinel"]
  ans --> obs["📈 Exporters<br/>redis · zfs → Prometheus"]
  ans --> ops["🔧 Cluster ops<br/>etcd maintenance (RKE2)"]

  classDef src stroke:#64748b,stroke-width:2px,stroke-dasharray:4 3;
  classDef ctrl stroke:#6366f1,stroke-width:2px;
  classDef svc stroke:#10b981,stroke-width:2px;
  classDef obs stroke:#0ea5e9,stroke-width:2px;
  classDef ops stroke:#f59e0b,stroke-width:2px;
  class inv src; class ans ctrl; class svc svc; class obs obs; class ops ops;
```

---

## 🧱 Roles & playbooks

| Role / directory | What it does | Playbook |
|------------------|--------------|----------|
| 🔀 **[ansible-haproxy-reverse-proxy-role](ansible-haproxy-reverse-proxy-role%20)** | Installs and configures HAProxy as a reverse proxy for JSON-RPC and WebSocket backends (e.g. an Ethereum Geth + Lighthouse node). | `install_haproxy.yml` |
| 🧠 **[ansible-redis-cluster-role](ansible-redis-cluster-role)** | Deploys a Redis master/replica pair plus a Sentinel quorum with AUTH and automatic failover. | `redis.yml` |
| 📈 **[ansible-redis-exporter-role](ansible-redis-exporter-role)** | Installs the Redis Exporter as a systemd service, exposing Redis metrics to Prometheus on `:9121`. | `redis_exporter.yml` |
| 💾 **[ansible-zfs-exporter-role](ansible-zfs-exporter-role)** | Installs the ZFS Exporter as a systemd service, exposing ZFS filesystem metrics to Prometheus on `:9134`. | `zfs_exporter.yml` |
| 🔧 **[etcd-maintenance](etcd-maintenance)** | Safely compacts and defragments `etcd` on an RKE2 Kubernetes cluster. | `etcd-maintenance.yml` |
| 📊 **[prometheus-configs](prometheus-configs)** | Prometheus + Alertmanager configuration and per-exporter alert rules, with a GitLab CI pipeline that lints and deploys them. | _config bundle — no playbook_ |

---

## 🚀 How to run a role

Every role ships an example playbook at its root. Point Ansible at your own inventory and run it:

```bash
ansible-playbook -i inventory.ini <playbook>.yml
```

For example, to install the Redis Exporter:

```bash
cd ansible-redis-exporter-role
ansible-playbook -i inventory.ini redis_exporter.yml
```

> [!NOTE]
> These roles use `become: true` (they install packages and manage systemd units), so the SSH user needs sudo. Bring your own `inventory.ini` — the examples use RFC-1918 placeholder addresses (`10.0.0.x`, `192.168.x.x`).
