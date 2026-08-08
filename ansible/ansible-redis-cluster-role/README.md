<div align="center">

# 🧠 Ansible Role: Redis Cluster with Sentinel

**Deploys a Redis master/replica pair plus a Sentinel quorum with AUTH and automatic failover.**

![Ansible](https://img.shields.io/badge/Ansible-role-EE0000?style=flat-square&logo=ansible&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-master%2Freplica-DC382D?style=flat-square&logo=redis&logoColor=white)
![Sentinel](https://img.shields.io/badge/Sentinel-failover-DC382D?style=flat-square&logo=redis&logoColor=white)

</div>

---

This role deploys a full Redis cluster including:
- Redis master
- Redis slave
- Sentinel cluster with automatic failover

---

## 📁 Structure

```
.
├── redis.yml                       # Example playbook
├── roles/
│   └── redis/
│       ├── tasks/
│       ├── templates/
│       ├── files/
│       └── defaults/
```

---

## ▶️ Usage

```bash
ansible-playbook -i inventory.ini redis.yml
```

Groups expected in inventory:

```ini
[master]
redis-master-1 ansible_host=10.0.0.1

[slave]
redis-slave-1 ansible_host=10.0.0.2

[sentinels]
sentinel-1 ansible_host=10.0.0.3
sentinel-2 ansible_host=10.0.0.4
sentinel-3 ansible_host=10.0.0.5
```

---

## ⚙️ Variables

Defined in `defaults/main.yml`:

```yaml
redis_password: ""      # Password for Redis AUTH
requirepass: ""         # Sentinel requirepass
cluster_name: "my-cluster"
```

> [!TIP]
> Keep `redis_password` and `requirepass` out of the repo — supply them from Ansible Vault or `--extra-vars` at run time rather than committing real secrets.

---

## 🛠 Features

- Secure Redis with AUTH
- Sentinel monitors master and performs automatic failover
- Configurable via inventory group names

---

## 📄 License

MIT
