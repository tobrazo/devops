# 🔧 etcd-maintenance (RKE2)

Ansible playbook to safely perform `etcd` maintenance operations such as compaction and defragmentation in an RKE2 Kubernetes cluster.

---

## 🛠️ What It Does

- Lists all Kubernetes nodes
- Finds the etcd pod using kubectl and label selector
- Retrieves current etcd revision
- Runs `etcdctl compact` with the retrieved revision
- Runs `etcdctl defrag` for the entire cluster

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