<div align="center">

# 🔀 Ansible Role: HAProxy Reverse Proxy

**Installs and configures HAProxy as a reverse proxy for JSON-RPC and WebSocket backends.**

![Ansible](https://img.shields.io/badge/Ansible-role-EE0000?style=flat-square&logo=ansible&logoColor=white)
![HAProxy](https://img.shields.io/badge/HAProxy-reverse%20proxy-106DA9?style=flat-square&logo=haproxy&logoColor=white)

</div>

---

This role installs and configures HAProxy as a reverse proxy for JSON-RPC and WebSocket connections,
commonly used in Ethereum node setups like Geth and Lighthouse.

## 📁 Structure

```
ansible-haproxy-reverse-proxy-role/
├── install_haproxy.yml          # Example playbook
├── roles/
│   └── haproxy/
│       ├── tasks/
│       │   └── main.yml
│       └── templates/
│           └── haproxy.cfg.j2
└── README.md
```

## ▶️ Usage

```bash
ansible-playbook -i inventory install_haproxy.yml
```

> [!NOTE]
> The role targets Debian/Ubuntu (installs via `apt`) and uses `become: true` to write `/etc/haproxy/haproxy.cfg` and manage the `haproxy` systemd unit. Adjust the frontend/backend addresses in `haproxy.cfg.j2` to match your own upstreams.
