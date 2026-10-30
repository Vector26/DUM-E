---
title: Knowledge index - start here
scope: How DUM-E's knowledge is organised and which file answers which kind of question
last_verified: 2026-10-29
sources: knowledge/ (this tree), homelab/library/
---

# Knowledge index - start here

Evidence tags used in every manual: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified. Sources are given as (src: path:line) or (cmd: command).

## What it is
This is DUM-E's own knowledge about the homelab (the owner's home server, host name homelab-host).
It has four parts:
- Manuals: how each part of the system works (this folder, `knowledge/manuals/`).
- Runbooks: symptom -> checks -> fix, step by step (`knowledge/runbooks/`, read as `runbook:<name>`).
- Glossary: what the owner means by their words (`knowledge/glossary.md`).
- Graph: how things connect (tool `graph`, built from files by `dume rebuild-graph`).
The homelab also has its own documentation library at `homelab/library/` (409 markdown files). The `manual` tool searches it too, with lower priority than DUM-E's own manuals.

## How the owner refers to it
"the manual", "your notes", "what you know", "teach you", "remember this". When the owner says "remember" or "learn", use `propose_knowledge_edit` (owner approves with `dume approve <ID>`).

## Components
Manuals by number:
- 00-index (this file)
- 01-machine: hardware, disks, partitions, swap, network, users, time zone
- 02-ai-brain: the local LLM server on :8081, model files, settings, clients
- 03-gpu-vram-watchdog: GPU memory, who uses it, the VRAM watchdog, the GPU guard
- 04-fortress-control: the `fortress` command, boot profile, health checks, incidents
- 05-services-catalog: all 22 Homelab services, one by one
- 06-schedules: cron jobs, systemd units and timers
- 07-ollama-and-models: Ollama, model files, cold storage
- 08-network-and-ports: every listening port, exposure, Mesh VPN (e.g. Tailscale)
- 09-security-and-boundaries: protected paths, secrets, the Deletion Mandate, what DUM-E may not do
- 10-shell-reference: the owner's bashrc aliases and functions, grouped
- 11-dume: DUM-E itself: tools, approvals, learning, files, install
- 12-pi-harness: the pi coding agent that DUM-E runs on
- 13-logs-and-incidents: every log, the incident log, alert de-duplication
- 14-known-issues: the register of every known problem (KI-01 ...), severity, evidence, who must act
- 20-cine-immich, 21-immich, 22-media-and-music
- 23-backups, 24-vault-storage, 25-monitoring, 26-notifier, 27-portainer-and-stacks
- 28-system-monitor-and-power, 29-wifi-and-network-guard, 30-kindle-dash, 31-personal-feed, 32-research-digest, 33-memory-swap-oom
- 34-jarvis, 35-virtual-self, 36-n8n-dexter-orchestration, 37-moltbot-vitalis-rag, 38-productivity-apps, 39-other-projects, 40-agent-platform (model queue :8181, gateway :8190)

Runbooks: ai-down, gpu-vram, watchdog, service-not-running, health-alerts, backup-failing, disk-full, container-unhealthy, boot-profile, notifier, feed-stale, slow-ai, after-reboot, dume-trouble, ollama, wifi-guard.

## Files and data
- Manuals, runbooks and glossary live in `~/homelab/DUM-E/knowledge/` [V].
- Old versions of edited files are kept in `knowledge/.history/` [V].
- The graph is `knowledge/graph.json` [V].

## Commands
- `manual` action=list | read | search (DUM-E tool) - READ.
- Owner: `dume manual [name [section]]`, `dume search <words>` - READ.
- Owner: `dume rebuild-graph` - rewrites `knowledge/graph.json` (DUM-E's own file).

## Depends on
Nothing running. Knowledge works even when the AI brain is down (the owner can read it with `dume manual`).

## How to check it (read-only)
1. Owner's words unclear -> glossary.
2. A problem -> search runbooks by symptom words, then follow the runbook.
3. "How does X work" -> the manual for X.
4. "What is happening now" -> live tools (snapshot, ai_brain, gpu, services, ...). Manuals describe; tools tell the truth now.

## Known problems and fixes
- A manual can be out of date. If a live tool disagrees with a manual, trust the tool, tell the owner, and offer to propose a correction (only if the owner asks for it).

## Logs
DUM-E's own audit log: `~/homelab/DUM-E/state/audit.log` (log_tail log=dume_audit).

## Rules for DUM-E here
- Never edit knowledge without the owner asking and approving.
- Never copy secrets or private content into knowledge.

## Open questions
None.
