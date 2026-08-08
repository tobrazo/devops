---
name: sanitize-check
description: The repo's #1 invariant — scan for live secrets, real IPs, personal emails, and stray real identifiers. Use before any commit or push, when asked "is this safe to publish/push", "check for secrets/leaks", "sanitization", or after copying content in from a private source.
---

# Sanitize check

This repo is a **public** template. Nothing traceable to a real company, and no live secret, may land in it. Run the grep below over the publishable content and report each hit with file:line; the result must be **CLEAN** before committing.

> Scope excludes `.claude/` and `CLAUDE.md` on purpose — those tooling files legitimately contain the search patterns themselves.

```bash
grep -rniE 'dop_v1|GOCSPX|AKIA[0-9A-Z]{16}|ghp_[0-9A-Za-z]{20}|xox[baprs]-|hvs\.[A-Za-z0-9]{6}|discord\.com/api/webhooks/[0-9]|BEGIN (RSA|EC|OPENSSH|PRIVATE)|[0-9]{1,3}(\.[0-9]{1,3}){3}|@(gmail|yahoo|outlook|proton|icloud)\.com' \
  helm-charts gitops ansible terraform python README.md \
  --include='*.yaml' --include='*.yml' --include='*.tpl' --include='*.js' --include='*.json' --include='*.md' --include='*.sh' --include='*.tf' --include='*.py' \
  2>/dev/null | grep -vE '0\.0\.0\.0|127\.0\.0\.1|10\.[0-9]|172\.1[6-9]|172\.2[0-9]|172\.3[01]|192\.168|example\.(com|org|net|internal)|kubernetes\.default' \
  || echo "CLEAN"
```

Then **eyeball** for things a regex won't reliably catch:
- Real **company / org / product names** — replace with the neutral token **`tobrazo`** (or a generic word like `app`/`demo`).
- Real **domains** — replace with `example.com` (`.org`/`.net`/`.internal` for extras).

## How to fix a hit
- **Secret / token / password / private key** → a placeholder (`REPLACE_WITH_<THING>`, `changeme`) or a reference to a `Secret`/Vault the user provides. Never keep the real value.
- **Real public IP** → a placeholder hostname (`node-exporter.example.internal`) or an RFC-1918 example.
- **Personal email** → `admin@example.com`.

A hit inside a Kubernetes API **field name** (e.g. the giant `crd/crds.yaml` mentioning cloud SD-config fields) is upstream schema, not a leak — note it and move on.
