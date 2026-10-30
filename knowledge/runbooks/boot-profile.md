---
title: Wrong things started after reboot
symptom: After a reboot the wrong services or the wrong AI model came up
last_verified: 2026-10-30
related: 04-fortress-control, 02-ai-brain
---

# Wrong things started after reboot

## Symptom
- After boot some services are off, or the AI brain is not the Q4 model. [V]

## Quick check
1. `services {}` - look for: the "in boot profile" column.
2. `ai_brain {}` - look for: "Default profile brain at boot" and the model file.
3. `log_tail {"log":"boot","lines":60}` - look for: "Starting:", "Already on:", "Done:", "Default profile applied."

## Diagnosis
1. Boot runs from cron `@reboot sleep 20 && fortress boot`. [V]
2. The profile is `~/.config/fortress-control/profiles/default.json`. On 2026-10-30 it lists: orchestration, n8n, monitoring, notifier, immich, plane, vault, personal_feed, ai_llama, modelq, agent_gateway, vram_watchdog, and the brain `hauhaucs_q4`. [V]
3. `modelq` and `agent_gateway` were added on 2026-10-30. Before that they only came up when the user systemd manager started them. [V]
4. User lingering is on (`Linger=yes`), so the user systemd manager and its units start at boot, not at desktop login. [V]
5. After the profile, `fortress boot` runs `agent-heal --fix --quiet` to catch anything missed (agent units, containers, ODA preview). [V]
6. `boot.log` has no timestamps and may show two runs. [I]
7. A service is missing -> compare `services {}` with the profile list above -> cause A: it is not in the profile.

## Fix
- The owner edits the JSON file, or runs `fortress save-default hauhaucs_q4` only when everything wanted is running. DUM-E never writes the profile.
- Backups of the profile: `default.json.bak-20261029-2215` and `default.json.bak-20261030`. [V]
- For one missing service now: `propose_action {"action":"service_start","args":{"service_id":"<id>"}}`. Tell the owner: dume approve <ID>.

## Verify
- `services {}` shows the wanted services ON.
- Owner runs `~/homelab/agents/scripts/agent-heal --check --quiet` - expected: no FAIL lines.

## Do not
- Do not run `fortress boot` while the brain is up and in use. It re-applies the AI brain and restarts it. [V]
- Do not use `save-default` while services are half-started: it saves only what is running at that moment.

## Sources
- `~/.config/fortress-control/profiles/default.json`
- `~/homelab/control/fortress` (boot), `control/lib/actions.sh` (fc_apply_profile)
- `loginctl show-user owner -p Linger`
- manual 04-fortress-control
