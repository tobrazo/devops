# 📦 Ansible Role: Redis Cluster with Sentinel

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

---

## 🛠 Features

- Secure Redis with AUTH
- Sentinel monitors master and performs automatic failover
- Configurable via inventory group names

---

## 📄 License

MIT