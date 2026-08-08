## HashiCorp Vault (HA, Raft) via ArgoCD

**Install is GitOps; init / unseal / configure is a manual runbook** — Vault's
unseal keys and root token must never live in Git, so those steps are done by
hand (below), not by an ArgoCD Job.

### Runbook
1. Vault is installed by the platform root — `clusters/prod/apps/platform/vault.yaml`
   (chart `hashicorp/vault`, HA + Raft). No manual apply needed.

2. Waiting for pods to become ready
```bash
kubectl get pods -n vault -w
```

3. Initializing and Unsealing Vault
Initialization (only on vault-0):

```bash
kubectl exec -n vault vault-0 -- vault operator init
```

#### SAVE THE OUTPUT! It contains 5 unseal keys and the root token.

##### Unseal vault-0 (use any 3 of the 5 keys):

```bash
kubectl exec -n vault vault-0 -- vault operator unseal [KEY1]
kubectl exec -n vault vault-0 -- vault operator unseal [KEY2]
kubectl exec -n vault vault-0 -- vault operator unseal [KEY3]
```

##### Check the status of vault-0:

```bash
kubectl exec -n vault vault-0 -- vault status
```
It should show Sealed: false and HA Mode: active.

4. Joining and Unsealing the Remaining Nodes
Join vault-1 and vault-2 to the cluster:

```bash
kubectl exec -n vault vault-1 -- sh -c 'VAULT_TOKEN=[ROOT_TOKEN] vault operator raft join http://vault-active.vault.svc.cluster.local:8200'
kubectl exec -n vault vault-2 -- sh -c 'VAULT_TOKEN=[ROOT_TOKEN] vault operator raft join http://vault-active.vault.svc.cluster.local:8200'
```

Unseal vault-1 and vault-2 using the same 3 keys:

```bash
kubectl exec -n vault vault-1 -- vault operator unseal [KEY1]
kubectl exec -n vault vault-1 -- vault operator unseal [KEY2]
kubectl exec -n vault vault-1 -- vault operator unseal [KEY3]

kubectl exec -n vault vault-2 -- vault operator unseal [KEY1]
kubectl exec -n vault vault-2 -- vault operator unseal [KEY2]
kubectl exec -n vault vault-2 -- vault operator unseal [KEY3]
```

5. Cluster verification
```bash
kubectl exec -n vault vault-0 -- vault status
kubectl exec -n vault vault-1 -- vault status
kubectl exec -n vault vault-2 -- vault status
```
All nodes should show Sealed: false.

6. Configure Vault (with your root token from step 3)
Enable the KV engine + Kubernetes auth and write a policy/role, e.g.:

```bash
export VAULT_TOKEN=<root-token>
kubectl exec -n vault vault-0 -- sh -c '
  vault secrets enable -path=secret kv-v2
  vault auth enable kubernetes
  vault write auth/kubernetes/config \
    kubernetes_host=https://kubernetes.default.svc
  vault policy write myapp-reader - <<EOF
path "secret/data/myapp/*" { capabilities = ["read"] }
EOF
  vault write auth/kubernetes/role/myapp-role \
    bound_service_account_names=default \
    bound_service_account_namespaces=default \
    policies=myapp-reader ttl=24h
'
```
See `08-vault-rbac.yaml` / `ClusterRoleTokenReview.yaml` for the token-review RBAC the Kubernetes auth method needs, and `test-app.yaml` for an agent-injection example.

7. Configuration check

```bash
# Check secrets
kubectl exec -n vault vault-0 -- sh -c 'VAULT_TOKEN=[ROOT_TOKEN] vault kv get secret/myapp/database'

# Check policies
kubectl exec -n vault vault-0 -- sh -c 'VAULT_TOKEN=[ROOT_TOKEN] vault policy list'

# Check auth methods

kubectl exec -n vault vault-0 -- sh -c 'VAULT_TOKEN=[ROOT_TOKEN] vault auth list'
```
### Example usage in applications
#### Deployment with secret injection
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "myapp-role"
        vault.hashicorp.com/agent-inject-secret-db-credentials: "secret/data/myapp/database"
        vault.hashicorp.com/agent-inject-template-db-credentials: |
          {{- with secret "secret/data/myapp/database" -}}
          DB_USERNAME={{ .Data.data.username }}
          DB_PASSWORD={{ .Data.data.password }}
          {{- end }}
    spec:
      containers:
      - name: app
        image: my-app:latest
        command: ["/bin/sh"]
        args: ["-c", "set -a && . /vault/secrets/db-credentials && set +a && ./start-my-app"]
```


### Important notes
- **Unseal keys and the root token are printed once** during `vault operator init` — store them in a real secret manager, never in Git.
- Vault runs HA with Raft; init on `vault-0`, then `raft join` + unseal `vault-1`/`vault-2`.
- For production, prefer **auto-unseal** (a cloud KMS / transit seal) so pods recover without manual unsealing.