# ZFS Exporter Role

This role installs and configures the ZFS Exporter for Prometheus monitoring. The ZFS Exporter collects metrics related to ZFS file systems.

## Role Variables

- `exporter_version`: The version of ZFS Exporter to install (default: `2.3.4`). You can change this variable as needed in the `vars/main.yml` file or pass it directly via the command line or inventory.

## Run role 
```
ansible-playbook -i <path to inventory> zfs_exporter.yml

```