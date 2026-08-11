#!/usr/bin/env python3
"""
MCP server for Ansible-managed infrastructure.

Exposes Ansible playbooks, SSH server access, Docker operations and app CLIs as
tools an MCP client (e.g. Claude Code) can call directly from the conversation.

Nothing about the target infrastructure is hardcoded: hosts are resolved from
the Ansible inventory, and paths/credentials come from environment variables.
See README.md for configuration and installation.
"""

from __future__ import annotations

import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Optional

import paramiko

try:  # MCP Python SDK >= 2.0
    from mcp.server.mcpserver import MCPServer
except ImportError:  # SDK 1.x — same API under the old name
    from mcp.server.fastmcp import FastMCP as MCPServer

# -------------------------------------------------------
# Configuration — every value is an env var with a safe default
# -------------------------------------------------------

def _env_path(name: str, default: str | Path) -> Path:
    return Path(os.environ.get(name) or default).expanduser()


# Root of the Ansible tree (expects playbooks/, inventory/, roles/).
# Defaults to the bundled example skeleton so the server runs out of the box.
ANSIBLE_DIR = _env_path("ANSIBLE_MCP_DIR", Path(__file__).parent / "example").resolve()

# Inventory path, relative to ANSIBLE_DIR (or absolute).
INVENTORY = os.environ.get("ANSIBLE_MCP_INVENTORY") or "inventory/hosts.yml"

# Vault password file. Optional — vault flags are omitted when it is absent.
VAULT_PASS = _env_path("ANSIBLE_MCP_VAULT_PASS", ANSIBLE_DIR / ".vault_pass")

# SSH defaults. Per-host `ansible_user` / `ansible_ssh_private_key_file`
# from the inventory take precedence over these.
SSH_USER = os.environ.get("ANSIBLE_MCP_SSH_USER") or "deploy"
SSH_KEY = _env_path("ANSIBLE_MCP_SSH_KEY", "~/.ssh/id_ed25519")

SSH_TIMEOUT = 30    # seconds for normal commands
LONG_TIMEOUT = 300  # seconds for slow commands (composer install, reindex, ...)
PLAY_TIMEOUT = 1800 # seconds for a full playbook run

# -------------------------------------------------------
# MCP server
# -------------------------------------------------------

mcp = MCPServer(
    "ansible-ops",
    instructions=f"""
You manage infrastructure through an Ansible control node.

Ansible root: {ANSIBLE_DIR}
Inventory:    {INVENTORY}

DISCOVERY — do this before assuming anything about the environment:
  ansible_list_hosts      — inventory hosts, their groups and addresses
  ansible_list_playbooks  — available playbooks with a one-line description
  ansible_list_inventories — inventory files

Pass inventory host or group names (not IP addresses) to every tool.

WORKFLOW RULES:
  1. Run ansible_run with check_mode=True first for any change to a
     provisioning playbook, and show the user the diff before applying.
  2. Never drop databases, delete volumes, or run FLUSHALL without explicit
     user confirmation in the conversation.
  3. For credentials, use vault_view — never print raw vault ciphertext, and
     never echo a decrypted secret into a command line that gets logged.
  4. Prefer a dedicated tool over server_ssh; reach for server_ssh only for
     one-off diagnostics nothing else covers.
""",
)

# -------------------------------------------------------
# Internal helpers
# -------------------------------------------------------

def _vault_args() -> list[str]:
    """Vault flags, only when a password file is actually configured."""
    return ["--vault-password-file", str(VAULT_PASS)] if VAULT_PASS.exists() else []


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run a command in ANSIBLE_DIR."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(ANSIBLE_DIR),
        timeout=timeout,
        env=os.environ.copy(),
    )


def _ansible_cmd(args: list[str], timeout: int = 120) -> str:
    """Run an ansible command and format stdout/stderr/exit code for display."""
    try:
        result = _run(args, timeout)
    except FileNotFoundError:
        return f"Command not found: {args[0]} — is Ansible installed and on PATH?"
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s: {' '.join(args)}"

    output = result.stdout
    if result.stderr.strip():
        output += f"\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        output += f"\n[exit {result.returncode}]"
    return output.strip()


@lru_cache(maxsize=1)
def _hosts() -> dict[str, dict[str, str]]:
    """
    Resolve hosts from the Ansible inventory: alias -> {addr, user, key, groups}.

    This is the single source of truth for connection details — there is no
    hardcoded host list. Cached for the lifetime of the process.
    """
    try:
        result = _run(
            ["ansible-inventory", "-i", INVENTORY, "--list", *_vault_args()],
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    groups = {
        name: set(body.get("hosts", []))
        for name, body in data.items()
        if name != "_meta" and isinstance(body, dict)
    }

    hosts: dict[str, dict[str, str]] = {}
    for name, hostvars in data.get("_meta", {}).get("hostvars", {}).items():
        member_of = sorted(g for g, members in groups.items() if name in members and g != "all")
        hosts[name] = {
            "addr": str(hostvars.get("ansible_host") or name),
            "user": str(hostvars.get("ansible_user") or SSH_USER),
            "key": str(hostvars.get("ansible_ssh_private_key_file") or SSH_KEY),
            "groups": ", ".join(member_of),
        }
    return hosts


def _ssh(host: str, command: str, timeout: int = SSH_TIMEOUT) -> str:
    """SSH to an inventory host and run a shell command. Returns stdout + stderr."""
    target = _hosts().get(host)
    if not target:
        known = ", ".join(sorted(_hosts())) or "none — check the inventory path"
        return f"Unknown host '{host}'. Inventory hosts: {known}"

    addr, user = target["addr"], target["user"]
    key = Path(target["key"]).expanduser()

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            addr,
            username=user,
            key_filename=str(key),
            timeout=10,
            look_for_keys=False,
        )
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        exit_code = stdout.channel.recv_exit_status()

        result = out
        if err.strip():
            result += f"\n[stderr]\n{err}"
        if exit_code != 0:
            result += f"\n[exit {exit_code}]"
        return result.strip()
    except paramiko.AuthenticationException:
        return f"SSH auth failed for {user}@{addr} — check the key at {key}"
    except Exception as exc:
        return f"SSH error ({user}@{addr}): {exc}"
    finally:
        client.close()


# -------------------------------------------------------
# Tools: Ansible
# -------------------------------------------------------

@mcp.tool()
def ansible_run(
    playbook: str,
    limit: str,
    extra_vars: Optional[str] = None,
    tags: Optional[str] = None,
    check_mode: bool = False,
) -> str:
    """
    Run an Ansible playbook against the inventory.

    Args:
        playbook:   Playbook name without extension (e.g. 'site', 'deploy-app').
        limit:      Host or group to target (see ansible_list_hosts); 'all' for
                    every host, 'web:db' for several.
        extra_vars: Space-separated key=value pairs (e.g. 'app_git_branch=main').
        tags:       Comma-separated tags to run (e.g. 'nginx,firewall').
        check_mode: True = dry-run (--check), no changes made. Use this first
                    for any change to a provisioning playbook.
    """
    cmd = [
        "ansible-playbook",
        f"playbooks/{playbook}.yml",
        "-i", INVENTORY,
        *_vault_args(),
        "--limit", limit,
    ]
    if check_mode:
        cmd.append("--check")
    if extra_vars:
        cmd += ["-e", extra_vars]
    if tags:
        cmd += ["--tags", tags]

    return _ansible_cmd(cmd, timeout=PLAY_TIMEOUT)


@mcp.tool()
def ansible_list_hosts() -> str:
    """List inventory hosts with their groups and connection address."""
    hosts = _hosts()
    if not hosts:
        return (
            f"No hosts resolved from {ANSIBLE_DIR / INVENTORY}.\n"
            "Check ANSIBLE_MCP_DIR / ANSIBLE_MCP_INVENTORY, and that "
            "`ansible-inventory --list` works in that directory."
        )
    lines = [f"{'HOST':<20} {'GROUPS':<28} ADDRESS"]
    for name, info in sorted(hosts.items()):
        lines.append(f"{name:<20} {info['groups']:<28} {info['addr']}")
    return "\n".join(lines)


@mcp.tool()
def ansible_get_vars(limit: str = "all") -> str:
    """
    Show effective Ansible variables for hosts (vault values decrypted).

    Args:
        limit: Host or group filter (see ansible_list_hosts), or 'all'.
    """
    cmd = [
        "ansible", limit,
        "-i", INVENTORY,
        *_vault_args(),
        "-m", "debug",
        "-a", "var=hostvars[inventory_hostname]",
    ]
    return _ansible_cmd(cmd, timeout=60)


@mcp.tool()
def ansible_list_playbooks() -> str:
    """List available playbooks with a one-line description from their header comment."""
    playbooks_dir = ANSIBLE_DIR / "playbooks"
    if not playbooks_dir.is_dir():
        return f"No playbooks directory at {playbooks_dir}"

    results = []
    for path in sorted(playbooks_dir.glob("*.yml")):
        desc = ""
        for line in path.read_text().splitlines()[1:6]:
            if line.startswith("#"):
                desc = line.lstrip("# ").strip()
                break
        results.append(f"{path.name:<35} {desc}")
    return "\n".join(results) or f"No playbooks found in {playbooks_dir}"


@mcp.tool()
def ansible_list_inventories() -> str:
    """List available inventory files."""
    inv_dir = ANSIBLE_DIR / "inventory"
    if not inv_dir.is_dir():
        return f"No inventory directory at {inv_dir}"
    names = sorted(f.name for f in inv_dir.iterdir() if f.is_file())
    return "\n".join(names) or f"No inventory files in {inv_dir}"


@mcp.tool()
def vault_view(file_path: str) -> str:
    """
    View the decrypted contents of a vault-encrypted file.

    Args:
        file_path: Path relative to the Ansible root
                   (e.g. 'inventory/group_vars/web.yml').
    """
    full = (ANSIBLE_DIR / file_path).resolve()
    if not full.is_relative_to(ANSIBLE_DIR):
        return f"Refusing to read outside the Ansible root: {file_path}"
    if not full.exists():
        return f"File not found: {file_path}"
    if not VAULT_PASS.exists():
        return f"No vault password file at {VAULT_PASS} — set ANSIBLE_MCP_VAULT_PASS."
    return _ansible_cmd(["ansible-vault", "view", str(full), *_vault_args()], timeout=30)


@mcp.tool()
def vault_encrypt_string(value: str, var_name: str) -> str:
    """
    Encrypt a string value with ansible-vault (ready to paste into group_vars).

    Args:
        value:    The plaintext string to encrypt.
        var_name: Variable name for the output header (e.g. 'db_root_password').
    """
    if not VAULT_PASS.exists():
        return f"No vault password file at {VAULT_PASS} — set ANSIBLE_MCP_VAULT_PASS."
    cmd = ["ansible-vault", "encrypt_string", *_vault_args(), "--name", var_name, value]
    return _ansible_cmd(cmd, timeout=30)


# -------------------------------------------------------
# Tools: Docker
# -------------------------------------------------------

@mcp.tool()
def docker_status(host: str) -> str:
    """
    Show running Docker containers and their resource usage on a host.

    Args:
        host: Inventory host alias (see ansible_list_hosts).
    """
    cmd = (
        "echo '=== CONTAINERS ===' && "
        "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.RunningFor}}' && "
        "echo '' && echo '=== RESOURCE USAGE ===' && "
        "docker stats --no-stream "
        "--format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.NetIO}}'"
    )
    return _ssh(host, cmd, timeout=20)


@mcp.tool()
def docker_logs(
    host: str,
    container: str,
    lines: int = 200,
    since: Optional[str] = None,
) -> str:
    """
    Fetch recent logs from a Docker container.

    Args:
        host:      Inventory host alias (see ansible_list_hosts).
        container: Container name (see docker_status).
        lines:     Number of log lines (default 200).
        since:     Show logs since this time: '1h', '30m', '2024-01-01T00:00:00'.
    """
    flags = f"--tail {lines}"
    if since:
        flags += f" --since {since}"
    return _ssh(host, f"docker logs {container} {flags} 2>&1", timeout=20)


@mcp.tool()
def docker_exec(
    host: str,
    container: str,
    command: str,
    user: str = "app",
) -> str:
    """
    Execute a command inside a running Docker container.

    Args:
        host:      Inventory host alias (see ansible_list_hosts).
        container: Container name (see docker_status).
        command:   Command to run inside the container.
        user:      User to run as (default: 'app'). Use 'root' for system operations.
    """
    return _ssh(host, f"docker exec --user {user} {container} {command}", timeout=LONG_TIMEOUT)


@mcp.tool()
def docker_restart(host: str, container: str) -> str:
    """
    Restart a Docker container.

    Args:
        host:      Inventory host alias (see ansible_list_hosts).
        container: Container name (see docker_status).
    """
    return _ssh(host, f"docker restart {container}", timeout=30)


# -------------------------------------------------------
# Tools: application (Magento / Redis / MariaDB)
# -------------------------------------------------------

@mcp.tool()
def magento_cli(host: str, container: str, magento_command: str) -> str:
    """
    Run a Magento CLI command inside the PHP container.

    Args:
        host:             Inventory host alias (see ansible_list_hosts).
        container:        PHP container name (see docker_status).
        magento_command:  Command without the 'bin/magento' prefix
                          (e.g. 'cache:flush', 'indexer:status', 'setup:upgrade').
    """
    return _ssh(
        host,
        f"docker exec --user app {container} bin/magento {magento_command}",
        timeout=LONG_TIMEOUT,
    )


@mcp.tool()
def redis_cli(host: str, container: str, command: str = "INFO") -> str:
    """
    Run a redis-cli command inside the Redis container.

    Args:
        host:      Inventory host alias (see ansible_list_hosts).
        container: Redis container name (see docker_status).
        command:   redis-cli command (e.g. 'INFO', 'DBSIZE', 'MEMORY USAGE key').
                   FLUSHALL and other destructive commands need user confirmation.
    """
    return _ssh(host, f"docker exec {container} redis-cli {command}", timeout=15)


@mcp.tool()
def mariadb_query(host: str, container: str, query: str, database: str = "app") -> str:
    """
    Run a SQL query inside the MariaDB container.

    The password is read from MYSQL_ROOT_PASSWORD inside the container, so no
    credential is ever passed through this tool or written to a log.

    Args:
        host:      Inventory host alias (see ansible_list_hosts).
        container: DB container name (see docker_status).
        query:     SQL query (e.g. 'SHOW TABLES', 'SELECT * FROM users LIMIT 10').
        database:  Database name (default: 'app').
    """
    safe_query = query.replace("'", "'\\''")
    cmd = f"docker exec {container} mariadb -uroot -p\"$MYSQL_ROOT_PASSWORD\" {database} -e '{safe_query}'"
    return _ssh(host, cmd, timeout=30)


# -------------------------------------------------------
# Tools: server diagnostics
# -------------------------------------------------------

@mcp.tool()
def server_resources(host: str) -> str:
    """
    Show system resource usage: memory, CPU load, disk, top processes.

    Args:
        host: Inventory host alias (see ansible_list_hosts).
    """
    cmd = (
        "echo '=== MEMORY ===' && free -h && "
        "echo '' && echo '=== CPU / LOAD ===' && uptime && "
        "echo '' && vmstat 1 3 && "
        "echo '' && echo '=== DISK ===' && "
        "df -h --output=source,size,used,avail,pcent,target | grep -v tmpfs | grep -v udev && "
        "echo '' && echo '=== TOP 10 PROCESSES BY MEMORY ===' && "
        "ps aux --sort=-%mem | head -11"
    )
    return _ssh(host, cmd, timeout=20)


@mcp.tool()
def server_tail_nginx(host: str, lines: int = 100, error: bool = False) -> str:
    """
    Tail the nginx access or error log on the host (not inside Docker).

    Args:
        host:  Inventory host alias (see ansible_list_hosts).
        lines: Number of lines (default 100).
        error: True = error log, False = access log (default).
    """
    log = "/var/log/nginx/error.log" if error else "/var/log/nginx/access.log"
    return _ssh(host, f"sudo tail -n {lines} {log}", timeout=15)


@mcp.tool()
def server_ssh(host: str, command: str, timeout: int = 60) -> str:
    """
    Run an arbitrary shell command on a host via SSH.
    Use for one-off diagnostics not covered by the other tools.

    Args:
        host:    Inventory host alias (see ansible_list_hosts).
        command: Shell command to execute.
        timeout: Seconds to wait (default 60).
    """
    return _ssh(host, command, timeout=timeout)


# -------------------------------------------------------
# Resources — read Ansible files
# -------------------------------------------------------

@mcp.resource("ansible://playbooks/{name}")
def get_playbook(name: str) -> str:
    """Read a playbook file."""
    path = ANSIBLE_DIR / "playbooks" / name
    return path.read_text() if path.exists() else f"Not found: playbooks/{name}"


@mcp.resource("ansible://inventory/{name}")
def get_inventory(name: str) -> str:
    """Read an inventory file (vault values remain encrypted)."""
    path = ANSIBLE_DIR / "inventory" / name
    return path.read_text() if path.exists() else f"Not found: inventory/{name}"


@mcp.resource("ansible://group_vars/{name}")
def get_group_vars(name: str) -> str:
    """Read a group_vars file (vault values remain encrypted)."""
    path = ANSIBLE_DIR / "inventory" / "group_vars" / name
    return path.read_text() if path.exists() else f"Not found: inventory/group_vars/{name}"


@mcp.resource("ansible://roles/{role}/defaults")
def get_role_defaults(role: str) -> str:
    """Read default variables for a role."""
    path = ANSIBLE_DIR / "roles" / role / "defaults" / "main.yml"
    return path.read_text() if path.exists() else f"Not found: roles/{role}/defaults/main.yml"


@mcp.resource("ansible://roles/{role}/tasks")
def get_role_tasks(role: str) -> str:
    """Read the task list for a role."""
    path = ANSIBLE_DIR / "roles" / role / "tasks" / "main.yml"
    return path.read_text() if path.exists() else f"Not found: roles/{role}/tasks/main.yml"


@mcp.resource("ansible://roles/list")
def list_roles() -> str:
    """List all available roles."""
    roles_dir = ANSIBLE_DIR / "roles"
    if not roles_dir.is_dir():
        return f"No roles directory at {roles_dir}"
    return "\n".join(sorted(d.name for d in roles_dir.iterdir() if d.is_dir()))


# -------------------------------------------------------
# Entry point
# -------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
