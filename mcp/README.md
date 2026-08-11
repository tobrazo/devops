<div align="center">

# 🤖 MCP

**Model Context Protocol servers — AI-assisted operations.**

![MCP](https://img.shields.io/badge/MCP-stdio_servers-000000?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)

</div>

---

Servers that hand an AI assistant a **typed, auditable interface to infrastructure** instead
of a raw shell. Each one is standalone, configured by environment variables, and ships an
example tree so it runs before you point it at anything real.

---

## 📂 Servers

| Server | What it exposes |
|--------|-----------------|
| 🤖 **[ansible-ops](ansible-ops)** | An Ansible control node: playbooks (with dry-run), inventory and vault, plus SSH, Docker, app-CLI and diagnostic tools across the fleet. Hosts resolve from your inventory — nothing is hardcoded. |

---

## 🔐 A note on blast radius

> [!IMPORTANT]
> These servers run real commands against real servers. They are a convenience layer with
> guardrails in their MCP `instructions` (dry-run first, confirm destructive operations) —
> **not** a sandbox. Read each server's Security section before connecting one to production.
