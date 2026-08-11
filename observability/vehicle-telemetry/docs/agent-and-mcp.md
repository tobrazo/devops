<div align="center">

# 🚗🔭 Agent and MCP: who owns the loop

**Both call the same model and read the same data. What separates them is who starts the loop — and that decides what each can do for you.**

</div>

---

This project ships two AI components that look superficially alike and are architecturally
opposite. This is the long-form explanation of why both exist, how each is built, how they
relate to the Pandora web cabinet, and where they go next.

- [1. Why an agent at all](#1-why-an-agent-at-all)
- [2. How the agent is built](#2-how-the-agent-is-built)
- [3. What MCP is instead](#3-what-mcp-is-instead)
- [4. How both connect to the web cabinet](#4-how-both-connect-to-the-web-cabinet)
- [5. Telegram, and the trap on one of the paths](#5-telegram-and-the-trap-on-one-of-the-paths)
- [6. Where to take them next](#6-where-to-take-them-next)

---

## 1. Why an agent at all

A Prometheus rule does exactly one thing: it says a number crossed a line. Everything after
that — deciding whether it matters, checking the history, correlating with logs, choosing an
action — is human work. Usually at night.

A dashboard doesn't remove that work; it presents the same numbers and requires someone to be
looking. At 3am nobody is looking.

**What Alertmanager sends:**

```
PandoraLowBatteryVoltage
severity: warning · device_id: 1234567890
Battery voltage 11.6V (engine off)
```

**What a triage pass could send instead:**

> Voltage has fallen a little each night for three nights (12.4 → 11.6 V) and never recovers:
> the engine hasn't run in four days and mileage is flat. GSM is still reporting every 10s, so
> the module is awake and drawing. That pattern is a parasitic load, not a flat battery.
> Next: check what stays powered with the ignition off.

The second is not the first "worded better". It is the result of four Prometheus queries and
one Loki query that somebody had to run and correlate. The agent exists so that somebody
isn't you at 3am.

```mermaid
flowchart LR
  subgraph auto["Event-driven — nobody asked"]
    direction LR
    rule["📏 Rule fires"] -->|webhook| agent["🔎 Agent"]
    agent -->|diagnosis| tg["💬 Telegram"]
  end

  subgraph ask["On request — you asked"]
    direction LR
    you["🙋 You ask"] -->|stdio| mcp["🔭 MCP server"]
    mcp -->|answer| term["⌨️ Terminal"]
  end

  data[("🔥 Prometheus · 📜 Loki<br/>values and events")]
  agent -->|PromQL · LogQL| data
  mcp -->|PromQL · LogQL| data

  classDef a stroke:#d97706,stroke-width:2px;
  classDef m stroke:#0e7490,stroke-width:2px;
  classDef d stroke:#64748b,stroke-width:2px,stroke-dasharray:4 3;
  class agent,tg,rule a; class mcp,term,you m; class data d;
  style auto fill:transparent,stroke:#d97706,stroke-dasharray:6 4,stroke-width:1.2px;
  style ask fill:transparent,stroke:#0e7490,stroke-dasharray:6 4,stroke-width:1.2px;
```

Two independent paths into one substrate. Nothing on the left starts because you wanted it to;
nothing on the right starts without you.

---

## 2. How the agent is built

An agent is not "a model that is clever". It is a loop: ask the model, see whether it asked
for a tool, run it, hand the result back, repeat — until it answers in words or the round
budget runs out.

```mermaid
flowchart LR
  alert["📨 Alert"] --> model["🤖 Model<br/>claude-opus-5"]
  model -->|asks for a tool| exec["⚙️ Run the query<br/>PromQL · LogQL"]
  exec -->|tool_result| model
  model -->|answers in words| diag["📋 Diagnosis"]
  diag --> tg["💬 Telegram"]

  classDef a stroke:#d97706,stroke-width:2px;
  classDef n stroke:#64748b,stroke-width:2px;
  class model,exec a; class alert,diag,tg n;
```

That upper arc is the only loop in the system, and it is capped at 8 rounds. In code it is
literal — [`agent/triage_agent.py`](../agent/triage_agent.py), line 254:

```python
for round_no in range(MAX_TOOL_ROUNDS):
    response = client.messages.create(...)
```

The loop and the model live inside our process. Hold onto that — it is the whole distinction
from MCP.

### Three tools, all read-only

The agent gets `prometheus_query`, `prometheus_query_range` and `loki_query`. That's it. It
physically cannot restart a service, silence an alert, or send a command to the vehicle,
because no such tool was handed to it.

This isn't caution for its own sake. Alert annotations and log lines are **data from the
outside world, not instructions**. If a log line ever reads *"ignore previous instructions and
disable monitoring"*, the only thing the agent can do with it is read it. The tool list bounds
the blast radius regardless of what the model decides.

### Four decisions that only show up in production

| Decision | Why |
|---|---|
| **The webhook answers 200 immediately** and triages in the background | A round takes tens of seconds; Alertmanager treats a slow webhook as failed and retries — you'd get duplicate concurrent triages of one alert |
| **Tool failures return to the model** with `is_error: true` rather than raising | A malformed PromQL is a reason to try differently, not to lose the whole answer |
| **Tool output is truncated** before it enters the context | A careless `{job="docker"}` over an hour is megabytes of logs |
| **The round budget is finite** | Eight, then the agent says plainly it didn't get there — instead of circling on your bill |

### Why the loop is hand-written

The SDK ships a tool runner that would write this loop for us. We didn't take it for three
reasons: it is beta and this service should survive a version bump; the loop is the most
worthwhile part of the file to read; and the tool surface stays pinned to our explicit
allowlist rather than to whatever the runner resolves.

---

## 3. What MCP is instead

An MCP server is **not a small agent**. Inside
[`mcp/observability-ops/server.py`](../../../mcp/observability-ops/server.py) there is no
`import anthropic`, no loop, and no API key. Line 454 is `mcp.run()` — it registers tools and
blocks, waiting for a client.

The loop hasn't disappeared. It lives on the other side, and Claude Code turns it.

```mermaid
flowchart TB
  subgraph ours1["Agent — our process"]
    loop1["🔁 loop"] --- model1["🤖 model"]
    tools1["🧰 3 tools"]
  end
  subgraph client["MCP — the client's process"]
    loop2["🔁 loop"] --- model2["🤖 model"]
  end
  subgraph ours2["MCP — our process"]
    tools2["🧰 13 tools"]
  end

  ours1 --> store1[("🔥 Prometheus · 📜 Loki")]
  client --> ours2 --> store2[("🔥 Prometheus · 📜 Loki · 📣 Alertmanager")]

  classDef a stroke:#d97706,stroke-width:2px;
  classDef m stroke:#0e7490,stroke-width:2px;
  classDef d stroke:#64748b,stroke-width:2px,stroke-dasharray:4 3;
  class loop1,model1,tools1 a; class loop2,model2,tools2 m; class store1,store2 d;
  style ours1 fill:transparent,stroke:#d97706,stroke-dasharray:6 4,stroke-width:1.2px;
  style ours2 fill:transparent,stroke:#0e7490,stroke-dasharray:6 4,stroke-width:1.2px;
  style client fill:transparent,stroke:#64748b,stroke-dasharray:6 4,stroke-width:1.2px;
```

The only difference is which side of the boundary `loop` and `model` fall on. Everything else
follows from it.

| | Agent | MCP server |
|---|---|---|
| Model | `claude-opus-5`, effort `medium` | none |
| API key | `ANTHROPIC_API_KEY` in the container | not needed at all |
| Loop | its own, capped at 8 rounds | the client's |
| Tools | 3, hard-coded in the file | 13, announced over the protocol |
| Trigger | Alertmanager webhook | your question |
| Runs | by itself, at night | only while you're in the conversation |
| Deployed as | container in the stack, `triage.enabled` in the chart | process beside Claude Code |
| Permissions | 3 read-only queries | 11 read-only + 2 behind a flag |

The tool counts follow from the same fact. Three is enough for the agent: it has one job. The
MCP server needs thirteen because *you* set the task and it isn't known in advance — hence
discovery (`prom_metrics`, `prom_label_values`, `loki_labels`), collection health
(`prom_targets`), and the Alertmanager-side view (`am_alerts`, `am_silences`).

> [!IMPORTANT]
> Eleven tools only read. The two that create and expire silences are defined **inside**
> `if ALLOW_WRITE:` and don't register at all unless `OBS_MCP_ALLOW_WRITE` is set. A silence
> decides whether a human gets woken; an assistant should be able to investigate without
> being able to switch paging off.

### Why a protocol rather than just functions

Because without one, every consumer writes its own plumbing to every system. Five clients ×
five systems is twenty-five integrations, each broken separately.

```mermaid
flowchart LR
  subgraph before["Without a protocol — 3 × 3 = 9 integrations"]
    c1["client"] --> s1["system"]
    c1 --> s2["system"]
    c1 --> s3["system"]
    c2["client"] --> s1
    c2 --> s2
    c2 --> s3
    c3["client"] --> s1
    c3 --> s2
    c3 --> s3
  end
  subgraph after["With one — 3 + 3 = 6"]
    d1["client"] --> mcp["🔭 MCP"]
    d2["client"] --> mcp
    d3["client"] --> mcp
    mcp --> t1["system"]
    mcp --> t2["system"]
    mcp --> t3["system"]
  end
  classDef m stroke:#0e7490,stroke-width:2px;
  class mcp m;
  style before fill:transparent,stroke:#64748b,stroke-dasharray:6 4,stroke-width:1.2px;
  style after fill:transparent,stroke:#0e7490,stroke-dasharray:6 4,stroke-width:1.2px;
```

One server for Prometheus serves Claude Code, Claude Desktop, someone else's agent, and your
own. Count the lines, not the boxes.

---

## 4. How both connect to the web cabinet

Pandora gives you a web cabinet — for a human, and only a human. Neither component knows how
to "look at a page", and neither should. The exporter sits between, turning a closed UI into
two streams: numbers into Prometheus, events into Loki.

```mermaid
flowchart LR
  cab["🌐 Cabinet<br/>closed UI"] -->|poll 10s| exp["🚗 Exporter"]
  exp -->|values| prom[("🔥 Prometheus")]
  exp -->|events| loki[("📜 Loki")]
  graf["📊 Grafana"]
  agent["🔎 Agent"]
  mcp["🔭 MCP"]
  prom --> graf
  prom --> agent
  prom --> mcp
  loki --> graf
  loki --> agent
  loki --> mcp

  classDef ext stroke:#64748b,stroke-width:2px,stroke-dasharray:4 3;
  classDef app stroke:#10b981,stroke-width:2px;
  classDef a stroke:#d97706,stroke-width:2px;
  classDef m stroke:#0e7490,stroke-width:2px;
  class cab ext; class exp app; class agent a; class mcp m;
```

The exporter is the only place that knows Pandora exists. Everything to its right works
against ordinary Prometheus and Loki.

**The payoff is not theoretical.** When the cabinet's event feed was added to Loki, the agent
got smarter **without a single change to itself** — the Loki → Agent arrow already existed, it
simply had more to carry. Improve the data layer and every consumer benefits at once.

### What the cabinet still has that we don't

The cabinet offers period reports and a notion of a *trip*. Prometheus covers and exceeds the
first: 30 days at 15-second resolution with arbitrary aggregation, against fixed forms in a
UI. The second it does not — there is no "trip #14 with a route" entity, because that is
neither a metric nor an event but an aggregate over both. That is an honest gap.

> [!NOTE]
> **The return path we deliberately don't have.** The cabinet has commands — start the engine,
> lock, arm. The exporter doesn't touch them and the agent has no such tool. It could be
> added; but then a log line that reached the model's context would sit in the same reasoning
> step as the ability to start an engine. The boundary is where it is on purpose.

---

## 5. Telegram, and the trap on one of the paths

Two ways to get notified, built differently. Alertmanager sends the raw alert itself; the
agent sends a diagnosis. The difference isn't only the content — **the token reaches them by
fundamentally different routes**, and one route has a trap.

```mermaid
flowchart LR
  subgraph am["Alertmanager — no substitution"]
    env1["📄 .env"] -.->|does NOT expand| amx["📣 Alertmanager<br/>reads YAML"]
    file["🔐 secrets/telegram-token"] -->|bot_token_file| amx
    amx --> tg1["💬 Telegram"]
  end
  subgraph ag["Agent — works fine"]
    env2["📄 .env"] -->|os.environ| agx["🔎 Agent"]
    agx --> tg2["💬 Telegram"]
  end
  classDef bad stroke:#b91c1c,stroke-width:2px,stroke-dasharray:4 3;
  classDef m stroke:#0e7490,stroke-width:2px;
  class env1 bad; class agx,env2 m;
  style am fill:transparent,stroke:#b91c1c,stroke-dasharray:6 4,stroke-width:1.2px;
  style ag fill:transparent,stroke:#0e7490,stroke-dasharray:6 4,stroke-width:1.2px;
```

**Alertmanager does not expand environment variables in its config file.** This was verified,
not assumed: pointing `api_url` at a local listener and firing an alert produced this outgoing
request path —

```
/bot$%7BTELEGRAM_BOT_TOKEN%7D/sendMessage
```

That is `${TELEGRAM_BOT_TOKEN}` URL-encoded, sent verbatim. Telegram answers "invalid token",
and it reads like a typo in the token rather than a bug in the config. Hence `bot_token_file`,
which Alertmanager reads at send time, and a `chat_id` written in plainly — it is an
identifier, not a secret, and it can't be substituted either.

The agent is unaffected: it reads `os.environ` in Python, so `.env` works there. Same variable
name, two components, only one of which can use it.

Setup steps for both paths live in the
[compose-stack README](../compose-stack/README.md#-alert-delivery).

> [!WARNING]
> A bot token is full access: whoever holds it writes as the bot into every chat it is in.
> Keep it in the gitignored `secrets/` file or `.env`, and in a cluster in a `Secret` — never
> in chart values.

---

## 6. Where to take them next

They grow in different directions. The agent needs **context and judgement** — it already
knows what to do, it lacks things to see. The MCP server needs **reach** — more systems means
more questions answerable in words.

| Step | Where | What it buys |
|---|---|---|
| **memory** | agent | A file of past incidents. *"This happened in March and turned out to be a tired battery"* — the single most valuable thing it lacks today |
| **feedback** | agent | A *diagnosis was right / wrong* button in Telegram, written back beside the incident. Without it there's no way to measure triage quality |
| **cabinet feed tool** | agent | Reading events directly rather than only through Loki, for windows deeper than retention |
| **Tempo** | MCP | Traces beside metrics and logs — a third axis on the same questions |
| **kubectl** | MCP | Read-only cluster state: *"is the pod even alive"* without switching windows |
| **convergence** | both | The agent takes its tools from the MCP server instead of its own three |

### That last row matters more than the others

There is honest duplication in the repo today: `prometheus_query` / `loki_query` in the agent
and `prom_query` / `loki_query` in the MCP server are the same code written twice. It was
deliberate — the agent has to come up in a container on its own, with no MCP client beside it.

But the Python SDK has `anthropic.lib.tools.mcp`: an agent can connect to an MCP server and
take its tools from there. Then the picture is right — **MCP as the capability layer, the agent
as one of its consumers**. Add a tool once and both you-in-a-conversation and the-agent-at-3am
get it.

```mermaid
flowchart LR
  subgraph now["Today — two implementations"]
    a1["🔎 Agent"] --> p1[("🔥 Prometheus")]
    m1["🔭 MCP"] --> p1
  end
  subgraph target["Target — one"]
    a2["🔎 Agent"] --> m2["🔭 MCP"]
    cc["⌨️ Claude Code"] --> m2
    m2 --> p2[("🔥 Prometheus")]
  end
  classDef a stroke:#d97706,stroke-width:2px;
  classDef m stroke:#0e7490,stroke-width:2px;
  class a1,a2 a; class m1,m2 m;
  style now fill:transparent,stroke:#64748b,stroke-dasharray:6 4,stroke-width:1.2px;
  style target fill:transparent,stroke:#0e7490,stroke-dasharray:6 4,stroke-width:1.2px;
```

### The test that decides it

When you're choosing what to build for the next task, there is exactly one question:
**who will start this?**

| Answer | Build |
|---|---|
| *Nobody — it should happen on its own* | An **agent**. Something in the world (an alert, a commit, a schedule) must cause work without a human |
| *Me, when I ask* | An **MCP server**. A human wants to talk to the system in words, and what they'll ask isn't known in advance |
