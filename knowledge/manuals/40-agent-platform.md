---
title: Homelab agent platform (model queue + gateway)
scope: modelq :8181, agent gateway :8190, registry v5, CLIs, flowsmith (sole n8n), repoints
last_verified: 2026-10-30
sources: homelab/docs/AGENT_PLATFORM_STATUS.md, homelab/AGENT_PLATFORM.md, control/services.yaml, agents/registry.yaml
---

# Homelab agent platform

## What it is

One **brain** (llama-server `:8081`), one **queue** (`modelq` `:8181`), one **HTTP gateway** (`agent_gateway` `:8190`). Agents (Dexter, Detective, flowsmith, ODA, DUM-E, Virtual Self) are roles with sandboxes; Android and CLIs call the gateway. **Only flowsmith** talks to n8n; NFA CLI is deprecated.

Full status (breaking issues, leftovers): [AGENT_PLATFORM_STATUS.md](../../docs/AGENT_PLATFORM_STATUS.md).

## Start (owner)

```bash
~/bin/llama-server-ctl start
fortress start modelq agent_gateway
openssl rand -hex 32 > ~/.config/homelab/agent-gateway.token   # once
```

## DUM-E notes

- **Chat** uses pi → `models.json` → **:8181** (queue), not direct `:8081`.
- **Health** tools (`ai_brain`, `ensure_ai`) still check **:8081** — that is intentional (brain process up).
- **Graph**: includes `service:modelq` and `service:agent_gateway` after `dume rebuild-graph`.
- DUM-E must **not** call n8n or push workflows; enqueue **flowsmith** jobs via gateway when automation is needed.
- DUM-E itself never starts or schedules anything. The shared infrastructure (modelq, gateway, ODA preview, agent containers) is supervised by systemd and by `agents/scripts/agent-heal` (see below), not by DUM-E.
- `dume` and `oda` start the queue at launch if :8181 is down (audit event `owner_started_modelq`). [V]

## Ports

| Port | Service |
|------|---------|
| 8081 | Brain (llama-server) |
| 8181 | Model queue |
| 8190 | Agent gateway |
| 7460 | ODA preview server |

## Which endpoint each agent uses [V]

| Agent | Endpoint it calls |
|-------|-------------------|
| DUM-E, ODA (pi, user `dume` / `oda`) | `http://127.0.0.1:8181/v1` (models.json under /var/lib/dume, /var/lib/oda) |
| pi-cyber, owner pi | `~/.pi/agent/models.json` provider llama-hauhaucs -> :8181 |
| Dexter, Detective, flowsmith (gateway adapters, host processes) | `FORTRESS_MODELQ_BASE` / `OPENAI_BASE_URL` = :8181 |
| Virtual Self containers | `host.docker.internal:8181` (172.28.0.1 on its network); modelq must listen on 0.0.0.0 |
| Jarvis, research-digest, personal feed | direct to :8081 (not through the queue; they work, but are not ordered by it) |

## Self-heal (agent-heal)

- Script: `~/homelab/agents/scripts/agent-heal` (`--check`, `--fix`, `--e2e`, `--json`, `--quiet`). Timer: `fortress-agent-heal.timer` every 2 minutes. Also runs at the end of `fortress boot`; `fortress heal` is the same script. [V]
- Log: `~/.local/state/homelab/agent-heal.log` (DUM-E: `log_tail {"log":"agent_heal"}`). Exit 0 healthy, 1 failing, 2 internal error, 3 warnings only. [V]
- Runbooks: runbook:agent-heal, runbook:model-queue-down, runbook:agent-gateway-down, runbook:oda-preview-down, runbook:agent-container-down. [V]

## CLI examples

```bash
~/homelab/agents/bin/fortress-agent health
~/homelab/agents/bin/fortress-agent chat dexter "Question"
~/homelab/hierarchial-agent/bin/detective ask "Thread?"
~/homelab/agents/bin/fortress-agent chat oda "Landing page for ..."
~/homelab/agents/bin/fortress-agent workflow "Build webhook for ..."
python -m flowsmith migrate-pipeline   # Homelab research pipeline (owner)
```

Streaming (Detective / flowsmith only): `POST /agents/detective/chat` with `"options": {"stream": true}` or `Accept: text/event-stream`.
