---
title: Research Digest
scope: the Research News Digest: the rdigest CLI, the n8n workflow that runs it, the node pipeline that scores news and arXiv items with pi on the local AI brain, its Postgres tables, and the runtime copy inside n8n_files
last_verified: 2026-10-29
sources: homelab/research-digest/{research-digest-cli.sh,install.sh,push_research_digest_to_n8n.sh,run_digest.sh,run_digest.mjs,pipeline_lib.mjs,schema.sql,research_digest.import.json,verify_scopes.sh,pi/agent/{models.json,models.host.json,settings.json,curator_system.md}}, homelab/n8n/docker-compose.yml, homelab/n8n/n8n_files/research-digest/, ~/.bashrc:540-542
---

# Research Digest

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
The Research Digest is a small news and paper curator for cybersecurity and AI topics. [V] (src: schema.sql:57-63; pi/agent/curator_system.md)
An n8n workflow runs it on a schedule. It fetches RSS feeds and arXiv categories, asks the local AI (through the `pi` CLI) to score and summarise items, and writes a digest file. [V] (src: research_digest.import.json nodes; run_digest.mjs:46-88)
It can also send the digest to the homelab notifier (Telegram), but by default it only writes a file. [V] (src: schema.sql:49 `delivery_mode = file`; run_digest.mjs:39-42,90-97)
The owner configures topics, feeds and schedules with the menu tool `rdigest`. [V] (src: research-digest-cli.sh:2)

## How the owner refers to it
- `rdigest` — alias: `bash "~/homelab/research-digest/research-digest-cli.sh"`, inside the `# >>> research-digest >>>` block. [V] (src: ~/.bashrc:540-542)
- `rdigest run-news`, `rdigest run-papers`, `rdigest status`, `rdigest deploy`. [V] (src: research-digest-cli.sh:298-310)
- n8n workflow name "Research News Digest". [V] (src: research_digest.import.json name; push_research_digest_to_n8n.sh:9)
- "news digest" (daily) and "papers digest" (weekly). [V] (src: schema.sql:38-39)

## Components
- **n8n workflow "Research News Digest"** — nodes: `Schedule News Daily` (cron `0 8 * * *`), `Schedule Papers Weekly` (cron `0 8 * * 1`), `Webhook Run` (POST path `research-digest-run`), `Manual Run`, four `Init …` code nodes, `Load Config` (Postgres query), `Prepare Run` (code), `Run Digest Pipeline` (Execute Command `sh /files/research-digest/run_digest.sh`), `Parse Result` (code), `Record Seen` (Postgres insert into `rd_seen`). [V] (src: research_digest.import.json, parsed)
- Workflow id used by the checker: `kFC1Ow112M8FgTr4` (default in `verify_scopes.sh`). Whether it is the live id is [U]. (src: verify_scopes.sh:9)
- n8n runs in container `n8n_server` on port 5678. It mounts `~/homelab/n8n/n8n_files` at `/files` and the host's nvm node `~/.nvm/versions/node/v20.20.0` read-only at `/host-node`. [V] (src: homelab/n8n/docker-compose.yml:5,14,38,40)
- **Pipeline** — `run_digest.sh` (sh) → `node run_digest.mjs` with `pipeline_lib.mjs`. Inside n8n the runtime root is `/files/research-digest`. [V] (src: run_digest.sh:5-33)
- **pi** — the pi coding agent CLI from the host's nvm (`/host-node/lib/node_modules/@mariozechner/pi-coding-agent/dist/cli.js`), run with `--provider llama-hauhaucs --model hauhaucs-qwen3.6-35b-iq3m --no-session --no-tools --thinking minimal --mode text --system-prompt <curator_system.md> -p <prompt>`, timeout 240 s. [V] (src: pipeline_lib.mjs:115-175; cmd: ls cli.js on host)
- pi provider config (container): `baseUrl http://host.docker.internal:8081/v1`, `api openai-completions`, one model `hauhaucs-qwen3.6-35b-iq3m` (context 262144, max tokens 4096). The `apiKey` field exists (value not copied). [V] (src: pi/agent/models.json)
- pi provider config (host run): same but `baseUrl http://127.0.0.1:8081/v1`. Used only when `/host-node/bin/pi` does not exist. [V] (src: pi/agent/models.host.json:4; run_digest.sh:13-17)
- pi settings: default provider `llama-hauhaucs`, default model `…-iq3m`, thinking `minimal`. No telemetry setting. [V] (src: pi/agent/settings.json)
- **Postgres** — tables `rd_config`, `rd_topics`, `rd_feeds`, `rd_seen` in the `n8n` DB of container `n8n_postgres`. [V] (src: schema.sql:4-32)
- n8n credential "Research Digest Postgres" (host `postgres`, DB `n8n`, user `n8n`, password from `POSTGRES_PASSWORD`). [V] (src: push_research_digest_to_n8n.sh:10,80-106)
- No cron line and no systemd unit. Scheduling lives inside n8n. [V] (cmd: crontab -l)
- No port of its own. Uses n8n :5678 (webhook and API), :8081 (AI), :8001 (notifier, optional). [V] (src: research-digest-cli.sh:6-8)

## Files and data
- `~/homelab/research-digest/` — source. [V]
- `~/homelab/n8n/n8n_files/research-digest/` — runtime copy (seen as `/files/research-digest` in n8n). Its scripts and pi config are byte-identical to the source today. [V] (cmd: cmp each file)
  - `latest.json`, `latest.txt` — last digest output. Last written 2026-10-06 08:01 (news mode, ok, 24 collected, 16 after dedupe, 4 ranked; the Krebs feed failed with "fetch failed"). [V] (cmd: ls -la; parsed latest.json)
  - `.run-input.json` — config, topics, feeds and seen-URLs written by n8n for each run (2026-10-06 08:00). [V] (cmd: ls -la; src: run_digest.mjs:17,30)
  - `pi-runtime/.pi/agent/` — HOME used for pi during a run. Holds `auth.json` (SECRET), `models.json`, `settings.json`, `curator_system.md`. [V] (cmd: ls)
- `pi/agent/auth.json` — SECRET (mode 600). Not opened. [V] (cmd: ls -la)
- `pi/agent/models.json`, `models.host.json` — contain an `apiKey` field. Treat as SECRET; value not copied. [V]
- `pi/agent/curator_system.md` — the scoring prompt: score 1–10, 1–2 sentence summary, JSON array only. [V]
- `docs/PERSONAL_FEED_RESEARCH.md` — 700-line design doc for the Personal Feed (manual 31). [V] (cmd: wc -l)
- `research_digest.import.json` — the n8n workflow definition. [V]
- `homelab/n8n/.env` — SECRET. `install.sh` sources it for `N8N_API_KEY` and `POSTGRES_PASSWORD`. Not opened. [V] (src: install.sh:6,54-57)
- `rd_config` keys and schema defaults: `cron_news '0 8 * * *'`, `cron_papers '0 8 * * 1'`, `relevance_threshold 6`, `max_items 8`, `lookback_days 7`, `model_override ''`, `autoload false`, `ollama_priority`, `llama_base_url`, `ollama_base_url`, `notifier_url http://host.docker.internal:8001/notify`, `delivery_mode file`, `ai_backend pi`, `pi_provider llama-hauhaucs`, `pi_model hauhaucs-qwen3.6-35b-iq3m`, `pi_thinking minimal`. Live values may differ. [V] defaults (src: schema.sql:37-54); live [U]
- `rd_seen` — URL, title, source, mode, score, first_seen, sent_at. Used to avoid repeats. [V] (src: schema.sql:24-32)

## Commands
- `rdigest` (no argument) — interactive menu (whiptail or `select`). Needs `n8n_postgres` running; checks with `docker ps`. [V] (src: research-digest-cli.sh:293-309)
- Menu reads (READ): list topics (1), list news feeds (4), list arXiv categories (7), show recent history (i), show status (j). They run `docker exec -i n8n_postgres psql …` SELECT queries. READ, but via `docker exec`, which DUM-E may not use. [V] (src: research-digest-cli.sh:10-16,42-89,164-185)
- Menu writes (MUTATES): add topic (2), deactivate topic (3), add news feed (5), deactivate feed (6), add arXiv category (8), deactivate arXiv category (9), set news cron (a), set papers cron (b), set threshold and max items (c), set model override (d), toggle Ollama autoload (e). All write `rd_*` tables with `docker exec … psql`. "Remove" is a soft delete (`active=false`). [V] (src: research-digest-cli.sh:47-148)
- `rdigest run-news` / menu f — `POST http://127.0.0.1:5678/webhook/research-digest-run?mode=news`. Starts a run. MUTATES. [V] (src: research-digest-cli.sh:150-155,299)
- `rdigest run-papers` / menu g — same with `mode=papers`. MUTATES. [V]
- Menu h "Send test Telegram" — `POST http://127.0.0.1:8001/notify` with a test message. MUTATES (sends a message). [V] (src: research-digest-cli.sh:157-162)
- `rdigest status` — prints the cron, threshold, model override, autoload and webhook values. READ (via `docker exec`). [V] (src: research-digest-cli.sh:178-185,301)
- `rdigest deploy` / menu k — runs `install.sh --push-only`: sources `homelab/n8n/.env`, copies `pipeline_lib.mjs`, `run_digest.mjs`, `run_digest.sh` and the whole `pi/` folder into the runtime dir, then pushes the workflow. MUTATES and overwrites. [V] (src: research-digest-cli.sh:169-176; install.sh:49-68)
- `bash install.sh` (full) — also applies `schema.sql` with `docker exec`, appends the `rdigest` alias block to `~/.bashrc`, prints a ufw hint. MUTATES. [V] (src: install.sh:16-47)
- `push_research_digest_to_n8n.sh` — via the n8n API (`X-N8N-API-KEY`): creates or PATCHes the "Research Digest Postgres" credential, PUTs (or POSTs) the workflow from the import file, keeps live `staticData`, then activates it. MUTATES and overwrites the live workflow. [V] (src: push_research_digest_to_n8n.sh:1-155)
- `verify_scopes.sh [news|papers]` — checks config rows, model reachability, then **triggers a real run** through the webhook and polls n8n executions. MUTATES. [V] (src: verify_scopes.sh:17-60)
- `sh run_digest.sh` (by hand on the host) — copies pi config into `pi-runtime` (overwrite), runs the pipeline, overwrites `latest.json`/`latest.txt`. MUTATES. [V] (src: run_digest.sh:10-33)
- Read-only for the owner: `cat ~/homelab/n8n/n8n_files/research-digest/latest.txt` and `ls -la ~/homelab/n8n/n8n_files/research-digest/`. READ. [V]

## Depends on
- **The AI brain on :8081.** pi talks to `host.docker.internal:8081/v1` from inside n8n. [V] (src: pi/agent/models.json)
- If :8081 is down, `scoreWithPi` throws; the run still finishes with score 5 and the feed's own summary text (cut to 200 characters). `ai_debug.error` records why. [V] (src: run_digest.mjs:53-65; pipeline_lib.mjs:175-180)
- `resolveModel` always returns `ai_ok: true` (pi backend). It does not check :8081 first. [V] (src: pipeline_lib.mjs:103-113,198-200)
- GPU: indirectly, through :8081. [I]
- Ollama :11434: listed in `rd_config` (`ollama_priority`, `autoload`), but the current code path is pi only; `resolveModel` ignores them. [V] (src: pipeline_lib.mjs:197-200) The menu text about Ollama autoload is therefore stale. [I]
- **n8n** (`n8n_server`, :5678) and **Postgres** (`n8n_postgres`). [V]
- The host nvm node v20.20.0 tree (mounted into n8n). Removing or upgrading that node version breaks the pipeline. [I] (src: n8n docker-compose.yml:40)
- The notifier :8001 — only if `delivery_mode` contains `notify`, or for the menu's test message. [V]
- Internet access to the RSS feeds and `export.arxiv.org`. [V] (src: pipeline_lib.mjs:246-275)

## How to check it (read-only)
- DUM-E tool `containers` — `n8n_server` and `n8n_postgres` must be running. [V]
- DUM-E tool `ai_brain` — :8081 must be up at 08:00 for AI scoring. [I]
- DUM-E tool `ports` — :5678 (n8n). [V]
- DUM-E tool `schedules` — will not show it; the schedule is inside n8n. [V]
- DUM-E tool `graph` — digest → n8n, digest → ai_llama. [I]
- DUM-E tool `manual` — this file. [I]
- Owner, read-only: `ls -la ~/homelab/n8n/n8n_files/research-digest/latest.json` — the time shows the last run. [V]
- Owner, read-only: `head -c 400 ~/homelab/n8n/n8n_files/research-digest/latest.json` — `"ok": true` means the last run finished. [V]
- Owner, in n8n UI (`http://<host>:5678`): workflow "Research News Digest" → Executions. Read-only if he only looks. [I]

## Known problems and fixes
- **No runs since 2026-10-06.** `latest.json` is from 2026-10-06 08:01. Daily 08:00 runs should have updated it. [V] (cmd: ls -la) The host was likely off from 2026-10-20; the gap 2026-10-07 → 2026-10-19 is unexplained. [I] Possible causes: workflow deactivated, n8n down (n8n "not running" × 402 in incidents), or runs failing before the write. [U] Settle: owner opens n8n Executions for the workflow.
- **At most 4 items per digest.** When AI is on, only the first 4 deduped items are kept and scored; the rest are dropped, even though `max_items` is 8. Last run: 16 deduped, 4 ranked. [V] (src: run_digest.mjs:53-58; latest.json stats) Fix (owner): change `deduped.slice(0, 4)` in `run_digest.mjs` and redeploy. DUM-E has no action for this.
- **Changing the schedule in `rdigest` does nothing.** The menu says "re-run: rdigest deploy to sync n8n schedule", but the push script uploads the import file with fixed crons (`0 8 * * *`, `0 8 * * 1`) and never reads `rd_config`. [V] (src: research-digest-cli.sh:110,117; push_research_digest_to_n8n.sh:21-155; research_digest.import.json) Fix (owner): edit the schedule nodes in n8n or in the import JSON.
- **Model id mismatch.** The digest asks for `hauhaucs-qwen3.6-35b-iq3m`; the server alias is `…-q4km`. Works only if llama-server ignores the model name. [V] values (src: pi/agent/models.json; DUM-E.md F8); effect [U].
- **pi telemetry is on.** The run sets `HOME` to `pi-runtime` with a `settings.json` that does not disable install telemetry, and `PI_TELEMETRY` is not set. [I] (src: run_digest.sh:18-22; pi/agent/settings.json; DUM-E.md F14)
- **`install.sh` copies `auth.json` into the n8n files tree** (`cp -a "$RD_DIR/pi"`). `n8n_files` is mounted into the n8n container. [V] (src: install.sh:65) The runtime `pi/agent/` currently has no `auth.json` (copied before it existed), but `pi-runtime/.pi/agent/auth.json` exists. [V] (cmd: ls) Risk: secret exposure to the container. [I]
- **SQL built by string concatenation in the CLI.** IDs for "remove" are not quoted or checked (`… WHERE id=${id}`). A typo like `1 or true` would deactivate every row. Owner-only tool, but fragile. [V] (src: research-digest-cli.sh:60,82,103)
- **Krebs feed failed in the last run** ("fetch failed"). [V] (src: latest.json feeds) Transient or blocked is [U].
- **Feeds changed from the schema defaults.** The last run used `arstechnica …/technology-lab` instead of the schema's `…/security`. [V] (src: latest.json; schema.sql:70) Changed via the CLI. [I]

## Logs
- No log file of its own. Each run's result is in `latest.json` (`ok`, `stats`, `ai_debug`, `items`, `digest_text`). On failure it holds `{"ok": false, "error": "…"}`. [V] (src: run_digest.mjs:71-109)
- n8n keeps execution history for the workflow (in the n8n DB/UI). [I]
- The AI side: `~/.local/state/llama-server-ctl.log`. [V] (src: DUM-E.md F2)

## Rules for DUM-E here
- DUM-E must never run `rdigest` (any mode or menu item), `install.sh`, `push_research_digest_to_n8n.sh`, `verify_scopes.sh`, or `run_digest.sh`. [V] (task rules)
- DUM-E must never use `docker exec` (the CLI's only DB path). [V] (task rules)
- DUM-E must never POST to the n8n webhook or the n8n API. [V] (task rules)
- DUM-E must never open `pi/agent/auth.json`, `pi-runtime/.pi/agent/auth.json`, `homelab/n8n/.env`, or print `apiKey` values from `models*.json`. [V]
- DUM-E may read `latest.json` / `latest.txt` (news headlines, not personal) and file times. [I]
- DUM-E has no action to run a digest; the owner runs: `rdigest run-news` (or `rdigest run-papers`).
- If the AI brain is down before 08:00, DUM-E can propose `llama_start` (approved action). [I]
- DELETES operations that exist here:
  - `cfg_set` overwrites `rd_config` values (`ON CONFLICT DO UPDATE`). [V] (src: research-digest-cli.sh:22-26)
  - "Remove topic / feed / arXiv category" sets `active=false` (soft delete). [V] (src: research-digest-cli.sh:60,82,103)
  - `push_research_digest_to_n8n.sh` overwrites the live workflow nodes and connections (PUT) and the credential (PATCH). [V] (src: push_research_digest_to_n8n.sh:98-142)
  - `install.sh` overwrites the runtime copies (`cp -f`, `cp -a`). [V] (src: install.sh:63-65)
  - `run_digest.sh` overwrites `pi-runtime/.pi/agent/{models.json,settings.json,curator_system.md}` each run. [V] (src: run_digest.sh:13-19)
  - Each run overwrites `latest.json` and `latest.txt`. [V] (src: run_digest.mjs:87-88)

## Open questions
- Is the workflow active in n8n, and what is its live id? [U] Settle: owner checks n8n UI → Workflows.
- What are the live `rd_config`, `rd_topics` and `rd_feeds` values? [U] Settle: owner runs `rdigest status` and the list menus.
- Why no runs between 2026-10-07 and 2026-10-19? [U] Settle: n8n Executions list.
- Which n8n timezone applies to `0 8 * * *`? [U] Settle: `GENERIC_TIMEZONE` in the n8n compose/.env (owner).
- Does the `Prepare Run` node write `.run-input.json` itself? Likely, since the file is dated one minute before `latest.json`. [I] Settle: read the node code in `research_digest.import.json`.
