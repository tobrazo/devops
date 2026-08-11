<div align="center">

# 🐳 compose-stack

**The whole observability stack in one command — with or without a vehicle.**

![Docker Compose](https://img.shields.io/badge/Docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-v2.55.1-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![Alertmanager](https://img.shields.io/badge/Alertmanager-v0.27.0-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![Loki](https://img.shields.io/badge/Loki-2.9.8-F46800?style=flat-square&logo=grafana&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-11.2.2-F46800?style=flat-square&logo=grafana&logoColor=white)

</div>

---

Exporter + Prometheus + Alertmanager + Loki + Promtail + Grafana, with datasources,
dashboards and alert rules provisioned on first boot. Every image tag is pinned — nothing
moves until you run `docker compose pull`.

---

## 🎛️ Two profiles

| Profile | Adds | Why |
|---|---|---|
| `demo` | `mock-pandora` — a fake cabinet | Run the whole stack with no vehicle, no account, no credentials |
| `triage` | `alert-triage` — the [AI triage agent](../agent) | Firing alerts get diagnosed before they reach a human |

```bash
# Demo — nothing to configure, Grafana needs no login
docker compose --env-file .env.demo --profile demo up -d --build

# Real cabinet
cp .env.example .env && $EDITOR .env
docker compose up -d --build

# Demo + AI triage
export ANTHROPIC_API_KEY=sk-ant-...
docker compose --env-file .env.demo --profile demo --profile triage up -d --build
```

`.env.demo` is committed on purpose — nothing in it is a secret. `.env` is gitignored.
`GRAFANA_PASSWORD` has no default: compose refuses to start rather than silently booting
an `admin/admin` Grafana.

---

## 📂 Structure

```text
compose-stack/
├── docker-compose.yml
├── .env.demo                        → committed; drives the demo profile
├── .env.example                     → cp to .env for a real cabinet
├── prometheus/prometheus.yml        → scrape + rule_files
├── alertmanager/alertmanager.yml    → null · telegram · triage receivers
├── promtail/promtail.yml            → Docker log discovery → Loki
└── grafana/provisioning/
    ├── datasources/                 → Prometheus (default) + Loki
    └── dashboards/                  → auto-import provider
```

Alert rules come from `../alerts/` and the dashboard from `../dashboards/` — the same
files the Kubernetes deploy uses.

> [!NOTE]
> `rule_files` globs `*-rules.yml`, **not** `*.yml`: the alerts directory also holds
> `pandora-rules.test.yml`, a promtool unit-test file that the rule manager cannot parse.

---

## ✅ Verify

| URL | What you should see |
|---|---|
| `http://localhost:9180/metrics` | Raw `pandora_*` metrics |
| `http://localhost:9090/targets` | `pandora-exporter` **UP** |
| `http://localhost:9090/rules` | Group `pandora-vehicle.rules`, 10 rules |
| `http://localhost:9093` | Alertmanager, no config errors |
| `http://localhost:3000` | Grafana → folder **Pandora** → *Pandora Vehicle* |
| `http://localhost:3100` | Loki — vehicle events under `{job="pandora"}`, container logs under `{job="docker"}` |

In demo mode the mock runs a 30-minute drive cycle, so within a couple of minutes the
charts fill in and `PandoraSimLowBalance` / `PandoraTireLow` start firing on their own. The
mock's event feed covers the previous cycle too, so the **Vehicle events** panel has content
immediately rather than after the first ten minutes.

---

## 📣 Alert delivery

The default receiver is `null`, so the stack starts with no credentials configured.
Three ways out, all in [`alertmanager/alertmanager.yml`](alertmanager/alertmanager.yml):

- **`triage`** — already defined; point `route.receiver` at it and run `--profile triage`
  to get an AI diagnosis instead of a raw alert.
- **`telegram`** — raw alerts straight to a chat. Create the bot via
  [@BotFather](https://t.me/BotFather), then:

  ```bash
  printf '%s' '<token>' > secrets/telegram-token     # gitignored
  ```

  Uncomment the receiver, replace `REPLACE_WITH_CHAT_ID` (get it from
  `https://api.telegram.org/bot<TOKEN>/getUpdates` after messaging your bot), and point
  `route.receiver` at `telegram`.

  > [!WARNING]
  > **Alertmanager does not expand environment variables in its config.** A
  > `bot_token: '${TELEGRAM_BOT_TOKEN}'` is sent to Telegram as that literal string —
  > the outgoing request path becomes `/bot$%7BTELEGRAM_BOT_TOKEN%7D/sendMessage`. That
  > is why the token comes from `bot_token_file` and the chat id is written in plainly.
  > The triage agent is different: it reads its own env vars in Python, so `.env` works
  > there.
- **`null`** — keep discarding, and read alerts in the Alertmanager UI.

Restart Alertmanager after editing: `docker compose restart alertmanager`.

---

## 🔐 Security

- **All ports bind to `127.0.0.1`** — nothing is reachable off-host. For remote access put
  a reverse proxy (Caddy / Traefik / nginx) with TLS and auth in front.
- `pandora_position_lat/lon` is **the vehicle's live location**. Don't let it leave the host.
- **Anonymous Grafana access is off** unless `GRAFANA_ANONYMOUS=true`, which only
  `.env.demo` sets. Never enable it against a real cabinet — the dashboard shows the map.
- Promtail mounts `/var/run/docker.sock` read-only to discover and read container logs.
  That is still broad Docker API access; remove the `promtail` service if you'd rather not
  grant it.
- The triage agent's `ANTHROPIC_API_KEY` stays in that container — it is never sent to
  Prometheus, Loki, or Telegram.

---

## 🔧 Operating

```bash
docker compose pull            # newer Prometheus / Grafana / Loki / Alertmanager
docker compose up -d --build   # rebuild the exporter after a code change
docker compose down            # stop
docker compose down -v         # stop and delete volumes — wipes all metric history
```

The compose project name is pinned to `vehicle-telemetry`, so its volumes can't collide
with another stack that happens to live in a directory called `compose-stack`.

---

## 🩺 Troubleshooting

**`pandora-exporter` restart-loops** → `docker compose logs pandora-exporter`. Almost always
bad credentials or a changed Pandora login endpoint — see the [project README](../README.md).

**Prometheus restart-loops** → it failed to load a rule file. `docker compose logs prometheus`
and look for `loading groups failed`.

**Dashboard is empty** → check `http://localhost:9090/targets`; if `pandora-exporter` is
DOWN, the exporter isn't up, so read its logs.

**Logs panel is empty** → `docker compose logs promtail`; on hosts where the Docker socket
isn't at `/var/run/docker.sock`, fix the mount path in `docker-compose.yml`.

**Triage agent exits immediately** → it needs `ANTHROPIC_API_KEY`. Compose can't mark it
required (it interpolates services outside the active profile too), so the service checks
at startup instead.
