---
title: Agent self-heal system
symptom: An agent health or heal finding appears, or the owner asks how the agent platform heals itself
last_verified: 2026-10-30
related: 40-agent-platform, 11-dume
---

# Agent self-heal system

## Symptom
- `dume doctor` lists "agent-heal <check>: ...". [V]
- The owner asks "did it fix itself?" or gets an "Agent platform: <check> keeps failing" message. [V]

## Quick check
1. `log_tail {"log":"agent_heal","lines":40}` - look for: DETECT, FIX, RECOVERED, "gave up".
2. Owner runs `~/homelab/agents/scripts/agent-heal --check` - look for: FAIL and WARN lines.

## Diagnosis
1. What it is: `~/homelab/agents/scripts/agent-heal`, run every 2 minutes by `fortress-agent-heal.timer` (user systemd), and at the end of `fortress boot`. It is not DUM-E and DUM-E never runs it on a schedule. [V]
2. What it probes: brain `/health`; a tiny plain and stream completion through :8181; gateway health and authenticated `/agents`; the gateway's PATH; ODA preview page; Virtual Self and n8n containers; n8n `healthz`; `flowsmith list`; the pi endpoints of DUM-E, ODA and pi-cyber; DUM-E install drift; lingering and unit enablement. [V]
3. What it fixes: restarts a failed user unit; restarts `oda-preview.service` (sudo -n); `docker start` or `docker restart` on the listed agent containers; starts the brain only through its script when no pause flag, no other GPU job and at least 10240 MiB free. [V]
4. Limits: at most 3 fix attempts per check per 30 minutes with growing waits; one run at a time; it never prunes or deletes. [V]
5. WARN lines have no automatic fix. Examples: `endpoint:*` (a pi config points at the wrong URL), `dume_install` (installed extension differs), `boot:linger`, `gateway_path`. [V]
6. A check keeps failing after fixes -> the cause is not a crash. Read the detail text, then the matching runbook: runbook:model-queue-down, runbook:agent-gateway-down, runbook:oda-preview-down, runbook:agent-container-down. [V]

## Fix
- Owner runs `~/homelab/agents/scripts/agent-heal --fix` to retry now, or `--e2e` for real chats with every agent.
- To pause the self-heal: `systemctl --user stop fortress-agent-heal.timer`. To turn it off for good: `systemctl --user disable --now fortress-agent-heal.timer`. [V]
- WARN `boot:linger`: owner runs `sudo loginctl enable-linger owner`.

## Verify
- `agent-heal --check --quiet` prints nothing and exits 0. Exit 1 means something still fails, 3 means only warnings. [V]
- `systemctl --user list-timers fortress-agent-heal.timer` shows a next run. [V]

## Do not
- Do not add `agent-heal` to DUM-E's own scheduler or give DUM-E a daemon.
- Do not raise the retry limits to "make it stick". A cause that survives 3 fixes needs a person.
- Do not add Immich, Plane or backup containers to its list.

## Sources
- `~/homelab/agents/scripts/agent-heal`
- `~/.config/systemd/user/fortress-agent-heal.service`, `fortress-agent-heal.timer`
- `~/.local/state/homelab/agent-heal.log`, `incidents.log`
- `~/homelab/docs/AGENT_PLATFORM_STATUS.md`
