# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **public** DevOps portfolio: reusable, cloud-agnostic Kubernetes/Helm charts, a full ArgoCD GitOps platform, plus Terraform/Ansible/Python samples. Everything is a **template** — no real infrastructure, no live credentials.

### The #1 invariant: it stays company-neutral and secret-free

This content was sanitized from private work. Before adding or editing anything, keep it that way:

- **No company/PII identifiers.** The neutral brand token is **`tobrazo`**; example domains are **`example.com`** (`.org`/`.net`/`.internal` for extras). Never introduce real company names, real domains, real IPs, or personal emails.
- **No live secrets.** Only placeholders: `REPLACE_WITH_*`, `changeme`, or references to a Kubernetes `Secret`/Vault the user provides. Never commit a real token/password/key.
- Run the sanitization check before committing (see Validation).

## Common commands

```bash
# Lint + render every in-tree Helm chart (what CI runs)
for c in helm-charts/redis-stack-cluster helm-charts/argo-rollouts-blue-green \
         gitops/workloads/nginx gitops/platform/centrifugo; do
  helm lint "$c"
done

# Render a chart (proves it obeys -n and both modes)
helm template redis helm-charts/redis-stack-cluster -n redis -f helm-charts/redis-stack-cluster/values-production.yaml
helm template app  helm-charts/argo-rollouts-blue-green -n demo                              # blue/green Rollout
helm template app  helm-charts/argo-rollouts-blue-green -n demo -f helm-charts/argo-rollouts-blue-green/values-deployment.yaml   # plain Deployment
helm template nginx gitops/workloads/nginx -n nginx-demo

# Build the kustomize manifest dirs
kubectl kustomize gitops/platform/monitoring/manifests
kubectl kustomize gitops/platform/otel/additional-resources
```

CI: `.github/workflows/helm-ci.yaml` runs `helm lint` + `helm template` (blocking) and `kube-linter` (informational) on pushes/PRs touching `helm-charts/**` or `gitops/**`. Helm 3 is required (`helm version` → v3.x).

`.github/workflows/observability-ci.yaml` covers `observability/**` and `mcp/**`: `promtool check rules` + `promtool test rules`, `compileall` over every Python tree, and a live run of the demo stack that asserts the exporter reports, Prometheus scrapes it, all 10 rules load, and Grafana serves the provisioned dashboard.

## Helm chart conventions (apply to every chart here)

- **Namespace comes from the release, never a value.** Templates use `{{ .Release.Namespace }}` — there is **no** `.Values.namespace` key. This is deliberate: it makes `helm install -n <ns>` and ArgoCD `destination.namespace` the single source of truth. Do not reintroduce a `namespace` value.
- **`fullname` helpers** are `{{ .Release.Name | trunc 63 | trimSuffix "-" }}` (DNS-label safe). Reuse the pattern in new charts.
- **`values.schema.json`** validates each chart's values on `helm lint`/`template` — update it when you add required/typed values.
- Charts ship `NOTES.txt`, an `icon`, and full `Chart.yaml` metadata (maintainers/keywords/sources).

### Blue/green charts (`argo-rollouts-blue-green`, `gitops/workloads/nginx`)
- One chart renders **either** an Argo `Rollout` (blue/green) **or** a plain `Deployment`, switched by `controller.type`. Rollout-only resources (preview Service/ingress, AnalysisTemplate, k6 ConfigMap) are gated on `eq .Values.controller.type "rollout"`.
- Active/preview Services carry **only** an `app: <fullname>` selector — the Rollout controller injects `rollouts-pod-template-hash`. The ArgoCD `Application` must `ignoreDifferences` on those Services' `/spec/selector` and the Rollout's `/spec/replicas` (HPA-owned), or ArgoCD fights the controller.
- The k6 pre-promotion gate targets the **in-cluster preview Service** via `PREVIEW_URL` env (not a public URL) and uses `failureLimit: 0` so it can actually fail a bad build.

### `redis-stack-cluster`
- A StatefulSet Redis Cluster. Pod IPs change on reschedule, so a `postStart` hook runs `fix-ip.sh` (embedded in a ConfigMap) to reconcile the `myself` line of `nodes.conf`. The `sed` is intentionally scoped to the `myself` line with escaped metacharacters — do not broaden it to a global replace.
- Security posture is NetworkPolicy (opt-in) + non-root `securityContext` + `protected-mode no` for in-cluster clustering; auth is bring-your-own-Secret (never put a password in the ConfigMap).

## GitOps platform (`gitops/`)

App-of-apps on a **single cluster, namespace-per-component**.

- **Entry points:** `clusters/prod/apps/platform-root.yaml` and `workloads-root.yaml` are two ArgoCD `Application`s with `directory.recurse: true`. They discover every child `Application` under `apps/platform/` and `apps/workloads/` — so **adding a workload = dropping one `Application` YAML** into `apps/workloads/` (copy `workloads/nginx` + `clusters/prod/apps/workloads/nginx-prod.yaml` as the pattern).
- **AppProjects** are defined in `clusters/prod/project-{platform,tobrazo}.yaml`. Roots and every child app reference one of these two projects; `tobrazo` (workloads) is least-privilege (namespaced resources + own Namespace only).
- **Multi-source values pattern:** external-chart apps use two sources — the upstream chart repo + a `ref: values` source pointing at this repo — and load values via `$values/gitops/platform/<component>/values.yaml`. When you change a component's values path, update the `$values/...` reference; it must resolve from the **repo root**.
- **Sync-waves** order the graph: `argo-rollouts` at wave `-5` installs its CRDs before any workload `Rollout` (wave `1`) syncs; cert-manager (8) before its ClusterIssuer (15); etc.
- **Bootstrap / reset:** apply the two projects + two roots (see `gitops/README.md`), or `gitops/reset-argocd-apps.sh`.
- Some components need secrets you provide before they go healthy: cert-manager/external-dns (Cloudflare token), Grafana/Alertmanager/Centrifugo (placeholder passwords). Vault install is GitOps; **init/unseal/configure is a manual runbook** (`gitops/platform/vault/README.md`) — unseal keys must never be in Git.

## Other trees

- `ansible/` — standalone roles (haproxy, redis+sentinel, redis/zfs exporters, etcd maintenance) and a Prometheus/alerting config set. Each has its own README and playbook (`*.yml`).
- `terraform/web-server/` — a single cloud web-server module (`WebServer.tf` + `userdata.tpl`).
- `python/evmpolls_scraper/` — a standalone scraper (`requirements.txt`).
- `observability/vehicle-telemetry/` — an end-to-end monitoring slice: exporter, mock data source, alert rules + unit tests, dashboard, Compose stack, k8s deploy and an AI triage agent. See below.
- `mcp/ansible-ops/` — a stdio MCP server (`server.py`) exposing an Ansible control node as tools/resources. See below.
- `mcp/observability-ops/` — a stdio MCP server over Prometheus / Loki / Alertmanager. See below.

### `mcp/ansible-ops`

- **Zero hardcoded infrastructure — keep it that way.** Hosts, users and SSH keys are resolved at runtime from the Ansible inventory via `ansible-inventory --list` (`_hosts()`); paths and fallbacks come from `ANSIBLE_MCP_*` env vars. Never reintroduce a literal host/IP/user dict — that is exactly what was scrubbed out of this code.
- `ANSIBLE_MCP_DIR` defaults to the bundled `example/` tree, so the server runs with no configuration. Keep `example/` valid: `ansible-playbook --syntax-check` must pass and every address stays under `example.com`.
- `ansible_list_playbooks` reports each playbook's **first comment line** as its description — new example playbooks need a `# one-liner` under the `---`.
- The MCP SDK renamed `FastMCP` → `MCPServer` in 2.0; the import is a `try/except` shim supporting both. Don't collapse it to one branch.
- Vault flags are added only when the password file exists (`_vault_args()`), so the server works without a vault. `vault_view` rejects paths resolving outside `ANSIBLE_MCP_DIR` — keep that guard.
- Validate with:
  ```bash
  python3 -m py_compile mcp/ansible-ops/server.py
  (cd mcp/ansible-ops/example && ansible-playbook --syntax-check -i inventory/hosts.yml playbooks/*.yml)
  ```

### `observability/vehicle-telemetry`

A vertical slice: exporter → alert rules → dashboard → Compose/k8s deploys → AI triage.

- **Single source of truth for rules and dashboards.** `alerts/pandora-rules.yml` and `dashboards/pandora-vehicle.json` are consumed by *both* the Compose stack (bind-mounted `../alerts`, `../dashboards`) and the Helm chart. Don't fork a second copy under `compose-stack/`.
- **The chart's `files/` copies are the one sanctioned duplication.** Helm cannot read outside the chart directory, so `deploy/chart/files/` holds copies of the two canonical files and CI diffs them. After editing either source, re-copy — `cp alerts/pandora-rules.yml dashboards/pandora-vehicle.json deploy/chart/files/` — or the chart job fails.
- **The chart follows the repo Helm conventions:** namespace from the release (no `namespace` value), `fullname` from `.Release.Name`, `values.schema.json` type-checks values, `NOTES.txt` ships. Credentials are bring-your-own via `pandora.existingSecret` / `triage.existingSecret`; the inline values are placeholders and must stay that way. Demo mode (`mock.enabled`) derives `PANDORA_HOST`/`PANDORA_SCHEME` from the mock Service — don't make them configurable in that path.
- **`rule_files` globs `*-rules.yml`, not `*.yml`.** `alerts/` also holds `pandora-rules.test.yml`, a promtool unit-test file; the rule manager cannot parse it and Prometheus restart-loops if the glob widens. Any new rule file must end in `-rules.yml`.
- **Alert rules have unit tests — keep them passing and extend them with every new rule.** `promtool test rules` asserts exact labels *and* rendered annotations, so editing an annotation string means editing the test too.
- **The mock cabinet is what makes this repo verifiable.** `mock/mock_pandora.py` must keep serving the same contract as the real cabinet (`POST /api/users/login` setting a cookie, `GET /api/updates` returning `{ts, stats, time}`, 401 without the cookie). If the exporter's parsing changes, change the mock in the same commit or the demo and CI silently stop proving anything.
- **Two stores, on purpose.** Values go to Prometheus; the cabinet's discrete events (door opened, engine stopped) go to Loki as log lines labelled `{job="pandora", device_id, event_type}`. Don't turn events into metrics — the cardinality explodes and the payload is lost either way.
- **Nothing depends on the event feed's schema.** It is undocumented, so `LokiShipper` ships each record verbatim as the line and resolves only two label values, each against a candidate-field list with an `unknown` fallback; it handles a flat list and a dict-keyed-by-device alike. `PANDORA_EVENTS_KEY` (default `lenta`) is a guess — the exporter logs the real payload keys on the first poll and warns when the configured key is absent. If you touch this, keep it shape-agnostic and keep the de-duplication (a content hash in a bounded `OrderedDict`); the cabinet re-sends recent events on every poll.
- **Event shipping must never take metrics down.** The `shipper.ship()` call is wrapped in its own try/except that only increments `pandora_events_errors_total`. Unset `LOKI_URL` disables the path entirely.
- **Read-only exporter, singleton by design.** Pandora session cookies aren't shareable, so the Deployment is `replicas: 1` + `strategy: Recreate`. `start_http_server()` runs *before* login on purpose, so `/metrics` answers while credentials retry.
- **The browser User-Agent is load-bearing** — Pandora answers the default `python-requests` UA with `200` and no cookies. Keep `BROWSER_UA`.
- **The login contract is reverse-engineered**, so it lives in env vars (`PANDORA_LOGIN_PATH` / `_FIELD` / `_FORMAT`, plus `PANDORA_SCHEME` for the mock). A Pandora UI change is a config change; don't hardcode a new path.
- **`/metrics` exposes vehicle GPS.** Every Compose port binds to `127.0.0.1`, and `GF_AUTH_ANONYMOUS_ENABLED` is off unless `.env.demo` turns it on. Never publish an example that binds `0.0.0.0` or enables anonymous Grafana outside the demo.
- **Compose specifics:** the project name is pinned (`name: vehicle-telemetry`) so volumes can't collide with another `compose-stack` directory, and services deliberately have no `container_name`. `ANTHROPIC_API_KEY` is *not* marked required with `:?` — compose interpolates services outside the active profile, so that would break the demo; the agent checks at startup instead.
- **`.env.demo` is committed and must stay secret-free.** `.env` is gitignored. No real credentials or device IDs anywhere: docs use `1234567890`, manifests use `REPLACE_WITH_*`.
- **The triage agent is read-only by construction** — three query tools, a bounded loop, and no ability to restart or silence anything. Don't add a mutating tool to it.
- **The design rationale for the agent and the MCP server lives in `observability/vehicle-telemetry/docs/agent-and-mcp.md`.** Read it before changing either one — it records why the loop is hand-written rather than the SDK tool runner, why the tool surfaces differ in size, and why the cabinet's command endpoints are deliberately unreachable from the model.
- Validate with:
  ```bash
  python3 -m compileall -q observability/vehicle-telemetry
  (cd observability/vehicle-telemetry/alerts && docker run --rm --entrypoint promtool \
     -v "$PWD":/w -w /w prom/prometheus:v2.55.1 test rules pandora-rules.test.yml)
  (cd observability/vehicle-telemetry/compose-stack && \
     docker compose --env-file .env.demo --profile demo config -q)
  ```

### `mcp/observability-ops`

- **Zero hardcoded infrastructure** — Prometheus / Loki / Alertmanager URLs come from `OBS_MCP_*` env vars and default to localhost. Same rule as `ansible-ops`: never reintroduce a literal endpoint.
- **Read-only by default.** The two silence tools are defined *inside* `if ALLOW_WRITE:` so they don't even register unless `OBS_MCP_ALLOW_WRITE` is set. Keep that gate — silences decide whether humans get paged.
- Results are truncated at `OBS_MCP_MAX_CHARS` and range queries are downsampled before returning; a wide query would otherwise flood the client's context window.
- Same `FastMCP` → `MCPServer` import shim as `ansible-ops` — don't collapse it to one branch.

## Validation before committing

```bash
# 1) charts must lint clean and render  (run the lint loop above)
# 2) sanitization gate — must return CLEAN (generic leak signatures; see the
#    sanitize-check skill for the full scan + how-to-fix)
grep -rniE 'dop_v1|GOCSPX|AKIA[0-9A-Z]{16}|hvs\.[A-Za-z0-9]{6}|discord\.com/api/webhooks/[0-9]|BEGIN (RSA|EC|OPENSSH|PRIVATE)|[0-9]{1,3}(\.[0-9]{1,3}){3}|@(gmail|yahoo|outlook)\.com' \
  helm-charts gitops terraform ansible python mcp observability \
  --include='*.yaml' --include='*.yml' --include='*.tpl' --include='*.js' \
  --include='*.py' --include='*.md' --include='*.json' --include='*.tf' \
  | grep -vE '0\.0\.0\.0|127\.0\.0\.1|10\.[0-9]|192\.168|172\.(1[6-9]|2[0-9]|3[01])\.|example\.(com|org|net|internal)|kubernetes\.default' || echo CLEAN
```

Also eyeball for real company/product names (→ `tobrazo`) and real domains (→ `example.com`); a regex won't reliably catch those.

Commit/push only when the user asks. Repo default branch is `main`; work on a feature branch and open a PR.
