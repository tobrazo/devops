<div align="center">

# 🔧 etcd-maintenance (RKE2)

**Safely compacts and defragments `etcd` on an RKE2 Kubernetes cluster.**

![Ansible](https://img.shields.io/badge/Ansible-playbook-EE0000?style=flat-square&logo=ansible&logoColor=white)
![etcd](https://img.shields.io/badge/etcd-compact%20%2B%20defrag-419EDA?style=flat-square&logo=etcd&logoColor=white)
![RKE2](https://img.shields.io/badge/RKE2-Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white)

</div>

---

Ansible playbook to safely perform `etcd` maintenance operations such as compaction and defragmentation in an RKE2 Kubernetes cluster.

---

## 🛠️ What It Does

- Lists all Kubernetes nodes
- Finds the etcd pod using kubectl and label selector
- Retrieves current etcd revision
- Runs `etcdctl compact` with the retrieved revision
- Runs `etcdctl defrag` for the entire cluster

> [!WARNING]
> `etcdctl defrag` briefly blocks writes on each member while it runs. Take an etcd snapshot first and run maintenance during a low-traffic window.

---

## ▶️ Example Usage

```bash
ansible-playbook -i inventory_example.ini etcd-maintenance.yml -l your-etcd-host
```

Replace `your-etcd-host` with your actual host or group.

---

## 📂 Inventory Example (inventory_example.ini)

```ini
[etcd]
your-etcd-node-name ansible_host=192.168.1.10
```

---

## ⚙️ Requirements

- Ansible 2.9+
- RKE2 with access to:
  - `/etc/rancher/rke2/rke2.yaml`
  - `/var/lib/rancher/rke2/bin/kubectl`

---

## 📄 License

MIT
