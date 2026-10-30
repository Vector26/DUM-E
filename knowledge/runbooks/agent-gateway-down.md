---
title: Agent gateway down or an agent fails through it
symptom: The Android app or fortress-agent cannot reach an agent, or Dexter / flowsmith / Virtual Self fail through the gateway
last_verified: 2026-10-30
related: 40-agent-platform, 36-n8n-dexter-orchestration, 35-virtual-self
---

# Agent gateway down or an agent fails through it

## Symptom
- `curl http://127.0.0.1:8190/health` refuses the connection. [V]
- A gateway chat returns "Internal Server Error". [V]
- `fortress-agent job ...` prints `curl: (22) The requested URL returned error: 422`. [V]

## Quick check
1. `ports {}` - look for: 8190 LISTEN.
2. Owner runs `~/homelab/agents/scripts/agent-heal --check` - look for: `gateway`, `gateway_path`, `vself_api`, `flowsmith`.

## Diagnosis
1. :8190 refused -> cause A: the unit stopped. `fortress-agent-gateway.service` has `Restart=always`; agent-heal restarts it within 2 minutes. [V]
2. Health ok but `GET /agents` with the token is not 200 -> cause B: token mismatch or registry error. Read `journalctl --user -u fortress-agent-gateway -n 50`. [I]
3. Dexter chat returns Internal Server Error and the journal says `FileNotFoundError: [Errno 2] No such file or directory: 'bun'` -> cause C. The systemd user unit has a short PATH. Fixed with `Environment=PATH=...` including `~/.bun/bin` in the unit. agent-heal reports it as `gateway_path`. [V]
4. Dexter reply starts with "Error: [Ollama API] model 'qwen3.6:27b' not found" -> cause D: Dexter used its `.env` Ollama model, not the queue. The gateway now sets `FORTRESS_CHAT_MODEL` so Dexter uses the brain through :8181. [V]
5. Dexter prints Python code errors from `ssrf-guard.ts` -> cause E: that file was Python by mistake. It was rewritten in TypeScript on 2026-10-30. [V]
6. Virtual Self chat fails -> cause F. Docker does not publish :8090 for the internal network, and the API needs the bootstrap token. The adapter finds the container IP and reads the token at call time. If `virtual_self_api` is down -> runbook:agent-container-down. [V]
7. `fortress-agent job ... 422` -> cause G: the old `fortress-agent` script added a stray `}` to the JSON. Fixed. [V]
8. `flowsmith list` returns `[]` although workflows exist -> cause H: the old code mishandled n8n's `{"data": [...]}` answer. Fixed. [V]

## Fix
- A: wait for restart, or owner runs `systemctl --user restart fortress-agent-gateway`.
- B, C, D, E, F, G, H: already fixed in the code. If they come back, report the exact journal line to the owner.

## Verify
- `~/homelab/agents/scripts/agent-heal --check` shows `OK gateway` and `OK gateway_path`.
- `~/homelab/agents/scripts/agent-heal --e2e` shows OK for Dexter, Detective, Virtual Self and the flowsmith job (it makes a few small AI calls).

## Do not
- Do not print or copy the token in `~/.config/homelab/agent-gateway.token`.
- Do not start `agent-gateway/start.sh` by hand.
- Do not point Dexter at Ollama. One GPU job at a time. [V]

## Sources
- `~/.config/systemd/user/fortress-agent-gateway.service`
- `~/homelab/agent-gateway/agent_gateway/adapters/__init__.py`
- `~/homelab/dexter/src/cli/fortress_chat.ts`, `src/tools/fetch/ssrf-guard.ts`
- `~/homelab/agents/bin/fortress-agent`, `~/homelab/flowsmith/flowsmith/n8n_client.py`
