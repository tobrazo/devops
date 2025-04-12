# Ansible Role: HAProxy Reverse Proxy

This role installs and configures HAProxy as a reverse proxy for JSON-RPC and WebSocket connections,
commonly used in Ethereum node setups like Geth and Lighthouse.

## Structure
```
ansible-haproxy-reverse-proxy-role/
├── roles/
│   └── haproxy/
│       ├── tasks/
│       │   └── main.yml
│       └── templates/
│           └── haproxy.cfg.j2
└── README.md
```

## Usage
```bash
ansible-playbook -i inventory install_haproxy.yml
```
