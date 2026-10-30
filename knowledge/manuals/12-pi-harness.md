---
title: pi, the coding agent harness
scope: What pi is, how the owner uses it, how DUM-E uses it, settings, telemetry, extensions, safety notes
last_verified: 2026-10-29
sources: pi README and docs (npm package @mariozechner/pi-coding-agent 0.67.1), ~/.pi/agent/{settings,models}.json, ~/.bashrc pi function, homelab/pi-cyber/bin/pi-cyber-run
---

# pi, the coding agent harness

## What it is
pi (`@mariozechner/pi-coding-agent`) is a minimal terminal agent: a chat loop that lets a model call tools. By default it gives the model four tools: read, write, edit, bash [V]. The owner uses it as a coding assistant on the local AI brain. DUM-E runs on a separate copy of pi with all four tools switched off.

## How the owner refers to it
"pi", "pih", "pi-cyber", "the coding agent".

## Components
- Installed: version 0.67.1 (changelog dated 2026-04-13), binary `~/.nvm/versions/node/v20.20.0/bin/pi` [V]. Newer versions exist (a 0.73.1 README was seen in a web search) [V-web].
- Owner settings `~/.pi/agent/settings.json`: defaultProvider `llama-hauhaucs`, defaultModel `your-local-model-id`, defaultThinkingLevel `high` [V]. `enableInstallTelemetry` is not set, so pi sends an anonymous version ping to pi.dev after updates [V]; opt out with `"enableInstallTelemetry": false` or `PI_TELEMETRY=0` (src: pi docs/settings.md) [V].
- Owner providers `~/.pi/agent/models.json`: `llama-hauhaucs` (http://127.0.0.1:8081/v1) and `ollama` (http://localhost:11434/v1) [V].
- Owner skills: `~/.pi/agent/skills/osint-decision` (link to pi-cyber) [V]; sessions in `~/.pi/agent/sessions/` [V].
- DUM-E's copy: `/opt/dume/pi`, run as user `dume` with `PI_TELEMETRY=0`, flags `--no-tools --no-extensions --no-skills -e /opt/dume/ext/dume.ts --system-prompt ...`, provider `fortress` (http://127.0.0.1:8081/v1) defined in `/var/lib/dume/.pi/agent/models.json` [V after install].

Key pi features (src: pi README/docs) [V]:
- Modes: interactive, print (`-p`), JSON, RPC (`--mode rpc`), SDK.
- `--no-tools` disables built-in tools; extension tools still work. `--tools <list>` picks built-ins.
- Extensions (TypeScript) can register tools and block any tool call (`tool_call` event).
- No MCP, no sub-agents, no permission pop-ups by design.
- Security note from pi itself: extensions and packages run with full system access.

## Files and data
- Owner: `~/.pi/agent/` (auth.json is SECRET). DUM-E: `/var/lib/dume/.pi/agent/`.

## Commands
- `pi` - owner's agent (starts the AI brain if needed). `pi -c` continue, `pi -r` resume picker.
- `pih` - pi with the HauhauCS provider; defaults to model id `hauhaucs-qwen3.6-35b-iq3m`, which is not defined in models.json [V] (may fail; untested).
- `pi-cyber`, `pi-case <name>` - separate security workspace (out of DUM-E's scope).
- `dume` - DUM-E's pi (manual 11).

## Depends on
The AI brain on :8081 (or Ollama for the `ollama` provider).

## How to check it (read-only)
- `ai_brain` (is :8081 up), `shell_index query=pi`.

## Known problems and fixes
- Telemetry on for the owner's pi (privacy). Fix (owner): add `"enableInstallTelemetry": false` to `~/.pi/agent/settings.json`.
- `pih` model id mismatch (above).

## Logs
pi sessions are JSONL files in the session folders.

## Rules for DUM-E here
- DUM-E does not change pi settings, versions or packages.

## Open questions
- Changes between 0.67.1 and newer pi versions [U]: read the changelog before upgrading `/opt/dume/pi`.
