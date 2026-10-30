---
title: Model queue or agent gateway down
symptom: DUM-E, ODA, Dexter, Detective, flowsmith, Virtual Self or the Android app says "connection refused" or gets an empty reply, but the AI brain (:8081) is fine
last_verified: 2026-10-30
related: 02-ai-brain, 11-dume, 40-agent-platform
---

# Model queue or agent gateway down

## Symptom
- `dume` starts, then the chat fails with a connection error, or ends with "terminated". [V]
- Dexter, Detective, ODA or `fortress-agent` calls fail. [V]
- `dume doctor` lists "Model queue not answering on :8181" or "Agent gateway not answering on :8190". [V]

## Quick check
1. `ai_brain {}` - look for: "/health: 200" for the brain on :8081. If not 200, use runbook:ai-down first.
2. `ports {}` - look for: 8181 (model queue) and 8190 (agent gateway) as LISTEN.
3. Owner runs `curl -s http://127.0.0.1:8181/health` - expected: `"status":"ok","upstream_ok":true`. [V]

## Diagnosis
1. Brain :8081 answers, :8181 does not -> cause A: model queue stopped. The pi provider of DUM-E, ODA and pi-cyber points at :8181. [V]
2. :8181 answers `/health`, but a chat returns nothing or "terminated" -> cause B: the queue's streaming path is broken. On 2026-10-30 it returned an empty stream and logged `RuntimeError: Cannot send a request, as the client has been closed.` It was fixed in `modelq/modelq/app.py`. agent-heal catches it with its `completion` probe (plain and stream). [V]
3. :8181 answers but `upstream_ok` is false -> the brain is down or paused -> runbook:ai-down. [V]
4. `:8181` works on the host but a container cannot reach `host.docker.internal:8181` -> cause C: modelq must listen on 0.0.0.0 (`Environment=MODELQ_BIND=0.0.0.0` in the unit). agent-heal reports it as `container_to_queue`. [V]
5. :8190 does not answer, :8181 does -> runbook:agent-gateway-down.
6. Both keep dying -> read `journalctl --user -u fortress-modelq -n 50` and report the exact error. [U]

## Fix
- Both services are systemd user units with `Restart=always` (3 s). A crash heals itself. [V]
- A hung process (port open, no answer) is restarted by agent-heal within 2 minutes (`systemctl --user restart fortress-modelq`). [V]
- `dume` and `oda` also start the queue at launch if :8181 is down (audit event `owner_started_modelq`). [V]
- Owner runs: `systemctl --user restart fortress-modelq` (DUM-E has no action for this). Same through Homelab Control: `fortress start modelq`. [V]
- C: owner checks the unit has `MODELQ_BIND=0.0.0.0`, then `systemctl --user daemon-reload && systemctl --user restart fortress-modelq`. [V]

## Verify
- Owner runs `~/homelab/agents/scripts/agent-heal --check` - expected: `OK modelq`, `OK completion`, `OK container_to_queue`.
- `dume ask "pong"` answers.

## Do not
- Do not start `modelq/start.sh` by hand. It runs in the foreground and a second copy fights for the port. [V]
- Do not set `MODELQ_BYPASS=1` as a fix. It hides the problem and removes ordering. [I]
- Do not restart the AI brain to fix this. The brain is not the cause in A, B or C.

## Sources
- `~/.config/systemd/user/fortress-modelq.service`
- `~/homelab/modelq/modelq/app.py`
- `~/homelab/control/services.yaml` (id modelq)
- `~/homelab/agents/scripts/agent-heal`
- `~/homelab/docs/AGENT_PLATFORM_STATUS.md`
