---
title: Personal Feed (Homelab Feed)
scope: the homelab Feed backend: daily build engine, Nibble learn pipeline, the Miniflux-compatible API on :8077 used by Capy Reader, start_backend.sh, the compose file, out/ logs, trust scoring, the 05:00 and 06:00 crons, and its use of the AI brain on :8081
last_verified: 2026-10-29
sources: homelab/personal-feed/{README.md,run_daily.sh,run_learn.sh,start_backend.sh,serve_api.sh,install.sh,docker-compose.yml,Dockerfile,requirements.txt,.env.example,config.py,llm.py,engine.py,api.py,learn_api.py,retention.py,trust/cred1.py,trust/corroboration.py,rank.py,collab/STATUS.md}, out/*.log, homelab/control/services.yaml:116-124, crontab -l, ss -ltnp, ~/bin/llama-server-ctl
---

# Personal Feed (Homelab Feed)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Homelab Feed builds one personalised news and research deck per day. [V] (src: README.md:3-11)
It fetches arXiv, RSS, Hacker News and connected Substack, summarises items with the local AI, scores trust, ranks, and stores the deck in Postgres. [V] (src: README.md:12-27)
It serves a Miniflux-compatible API on port 8077. The Android app Capy Reader (and a Capy fork) is the UI. [V] (src: README.md:4-5,46-54)
A second daily job, "Nibble learn", builds short learning chapters and quizzes. [V] (src: run_learn.sh:2-3)

## How the owner refers to it
- "Personal Feed", "Homelab Feed", "the feed", "Android feed app backend". [V] (src: README.md:1; control/services.yaml:117-118)
- Homelab Control service id `personal_feed`. [V] (src: control/services.yaml:116)
- "Nibble", "learn pipeline", "Learn tab". [V] (src: crontab -l comment; collab/STATUS.md)
- "deck", "daily deck", "refresh". [V] (src: start_backend.sh:60-74; api.py:822-858)
- No `.bashrc` alias. [V] (cmd: grep feed ~/.bashrc → none)

## Components
- **Feed API (host process)** — `uvicorn api:app` from `.venv`, listening on `0.0.0.0:8077`, PID 18156 today, started 21:07. [V] (cmd: ss -ltnp; src: out/api.log)
- Started by `serve_api.sh`: kills any `uvicorn api:app`, then `nohup .venv/bin/uvicorn api:app --host ${FF_API_HOST:-0.0.0.0} --port ${FF_API_PORT:-8077} > out/api.log`. [V] (src: serve_api.sh:1-17)
- Registered in Homelab Control: `kind: host`, `start: ~/homelab/personal-feed/start_backend.sh`, `stop: pkill -f 'uvicorn api:app' || true`, `detect_port: 8077`, `gpu: false`, `default: true`. [V] (src: control/services.yaml:116-124)
- `personal_feed` is in the restored Default boot profile. [V] (src: DUM-E.md F5)
- **Compose alternative (not used now)** — `docker-compose.yml`: service `feed-api` (image `fortress-feed:latest`, container `fortress_feed_api`, `restart: unless-stopped`, port `8077:8077`, network `n8n_default`) and `feed-engine` (profile `engine`, container `fortress_feed_engine`, runs `python engine.py`). [V] (src: docker-compose.yml:1-40) Neither container is running. [V] (src: DUM-E.md section 10.3 container list) Starting `feed-api` while the host uvicorn holds 8077 would fail on the port. [I]
- `Dockerfile` — `python:3.12-slim`, installs requirements, `uvicorn` on 8077. [V]
- **Daily build** — `engine.py`, run by `run_daily.sh` (cron 06:00) or by the API refresh endpoint. [V] (src: run_daily.sh; api.py:822-858)
- **Learn pipeline** — `python -m learn.pipeline`, run by `run_learn.sh` (cron 05:00). [V] (src: run_learn.sh:19)
- Cron: `0 6 * * * cd ~/homelab/personal-feed && /bin/bash run_daily.sh >> out/cron.log 2>&1`. [V] (cmd: crontab -l)
- Cron: `0 5 * * * cd ~/homelab/personal-feed && /bin/bash run_learn.sh >> out/learn.log 2>&1`. [V] (cmd: crontab -l)
- Database: Postgres in the `n8n_postgres` container, DB `n8n`, tables prefixed `ff_` (feed) and `jd_` (detective). Schema in `schema.sql` plus `migrations/001…021`. [V] (src: README.md:26; install.sh:33-35; ls migrations)
- Ports: 8077 (API). Uses 8081 (llama) and n8n_postgres 5432 as a client. Optional 11434 if `FF_LLM_BASE_URL` points at Ollama. [V] (src: config.py:28; llm.py:27-28)
- Health route: `GET /healthz` → `{"status":"ok"}` (no auth). [V] (src: api.py:1117-1119)
- Auth for all other routes: header `X-Auth-Token: <FF_API_TOKEN>` or HTTP Basic whose password is the token. [V] (src: api.py:113-124)
- Main routes (Miniflux subset): `GET /v1/me`, `/v1/feeds`, `/v1/categories`, `/v1/entries`, `/v1/entries/{id}`, `/v1/feeds/{id}/entries`; `PUT /v1/entries`, `PUT /v1/entries/{id}/bookmark`. [V] (src: api.py:350-726)
- Homelab routes: `GET /v1/homelab/feed`, `/feed/deck`, `/feed/history`, `/feed/refresh/status`, `/feed/algorithm`, `/taste`, `/analytics`, `/detective/status`, `/entries/{id}/explain`, `/connect/status`, `/connect/oauth-config`, `/discover/substack`; `POST /feed/refresh`, `/entries/{id}/feedback`, `/connect/{google|reddit|substack}…`; `PUT /feed/algorithm`; `DELETE /v1/homelab/connect/{provider}`. [V] (src: api.py:575-1115)
- Learn routes under `/v1/homelab/learn`: `survey`, `mode`, `topics`, `today`, `upcoming`, `chapters/{id}`, `chapters/{id}/quiz`, `progress`, `graph`, `stats`. [V] (src: learn_api.py:17-668)
- **Trust scoring, step 1 (source trust, `trust/cred1.py`):** user blocklist → excluded (0.0). Trusted (user trustlist or built-in list) → 0.9. Unknown → 0.6. A CRED-1 hit lowers it to the dataset score. Every reason is stored. [V] (src: trust/cred1.py:56-79)
- **Trust scoring, step 2 (corroboration, `trust/corroboration.py`):** items are clustered by title keywords (≥3 shared). ≥2 independent source families → `VERIFIED_MULTI`, score `min(1.0, 0.5 + 0.15 × n)`. One item → `SINGLE_SOURCE` 0.3. Same family only → `SINGLE_SOURCE` 0.4. No cluster → `NOT_FOUND` 0.0. A web pass (Google News RSS) may upgrade single-source stories. Aggregators (news.google.com, hackernews, reddit.com, flipboard.com) do not count as independent. [V] (src: trust/corroboration.py:1-110)
- **Trust combined:** `trustified = source_trust × (0.4 + 0.6 × corroboration)`. [V] (src: engine.py:614; rank.py:83)
- **Ranking:** `final = w_rel·relevance + w_trust·trustified + w_fresh·freshness + …`; default weights include relevance 0.20, trust 0.25, freshness 0.15. Weights are visible via `/explain` and `GET /v1/homelab/feed/algorithm`. [V] (src: rank.py:3,17; README.md:18-19)
- Trust and rank results are stored in `ff_trust_scores` and `ff_rank_explain`. [V] (src: engine.py:627,653)

## Files and data
- `~/homelab/personal-feed/` — code, venv `.venv/`. [V]
- `.env` — SECRET. Not opened. Mode 664. [V] (cmd: stat)
- `.env` variable names (from `.env.example`): `FF_PG_DSN`, `FF_PI_BIN`, `FF_PI_PROVIDER`, `FF_PI_MODEL`, `FF_PI_THINKING`, `FF_PI_TIMEOUT_S`, `GEMINI_API_KEY`, `FF_GEMINI_MODEL`, `FF_TOKEN_KEY`, `FF_API_HOST`, `FF_API_PORT`, `FF_API_TOKEN`, `FF_NOTIFIER_URL`, `FF_NOTIFY`, `PUBLIC_BASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`. [V] (src: .env.example)
- More variables read by code: `FF_LLM_BASE_URL` (default `http://127.0.0.1:8081`), `FF_LLM_MODEL`, `FF_LLM_TIMEOUT_S` (90), `FF_LLM_THINKING`, `FF_OUT_DIR`, `FF_ROOT_PATH`, `FF_HTTP_TIMEOUT`. [V] (src: config.py:28-65)
- `docker-compose.yml` and `.env.example` contain a default Postgres DSN with a plaintext password (value not copied). [V] (src: docker-compose.yml:13; .env.example:5)
- OAuth tokens are stored in Postgres table `ff_oauth_tokens`, encrypted with `FF_TOKEN_KEY` (base64 only if the key is empty). SECRET. [V] (src: config.py:37-38; oauth.py:217)
- `data/` — empty. The CRED-1 dataset `data/cred1.compact.json` is not installed. [V] (cmd: ls -la data)
- `out/` — logs and snapshots: [V] (cmd: ls -la out)
  - `api.log` (API stdout, overwritten at each start), `cron.log` (934 KB, last 2026-10-19 06:00), `learn.log` (96 KB, last 2026-10-19 05:00), `manual_refresh.log` (660 KB, last 21:11 today), `llama-server.log` (launch messages), `latest.json`, `latest.txt` (today's deck, 21:11), `learn-manual-20260704-084650.log`.
  - `latest.json` / `latest.txt` — today's ranked deck. Contain article titles, not owner data. [V]
- `capy-fork/` — Android fork notes and Kotlin. `collab/` — Mac/server agent notes (`STATUS.md`). `docs/` — app/backend specs. [V] (cmd: ls)

## Commands
- `./run_daily.sh` — loads `.env`, adds nvm node to PATH so `pi` is found, then `exec .venv/bin/python engine.py "$@"`. Writes the deck to Postgres, swaps `ff_rank_explain`, purges old rows, writes `out/latest.*`. MUTATES and DELETES. [V] (src: run_daily.sh; engine.py:240-262,621-627)
- `./.venv/bin/python engine.py --dry` — fetch, trust, rank, write `out/latest.json` only. No DB writes, no GPU. MUTATES only `out/latest.*`. [V] (src: README.md:35-37; engine.py:578,797-801)
- `engine.py --notify` — also posts the deck to the notifier. [V] (src: engine.py:780-801)
- `./run_learn.sh` — loads `.env`, `exec .venv/bin/python -m learn.pipeline`. Rebalances topics and generates chapters with the LLM. MUTATES and DELETES (regenerating a chapter deletes its cards and quiz). [V] (src: run_learn.sh; learn/generate.py:235-236,277)
- `python -m learn.pipeline --topic <slug>` — force-generate one chapter. MUTATES. [V] (src: learn/pipeline.py:8)
- `./start_backend.sh` — in order: [V] (src: start_backend.sh:1-76)
  1. Reads `n8n_postgres`'s Docker IP. If it differs from the host in `FF_PG_DSN`, rewrites `.env` in place with `sed -i`. MUTATES (edits a secret file).
  2. If `:8081/v1/models` does not answer, launches `nohup ~/bin/llama-server-ctl >> out/llama-server.log &` (no argument = `start`) and waits up to 120 s. MUTATES (starts the GPU model, bypassing the homelab GPU guard). [V] (src: start_backend.sh:30-46; llama-server-ctl:159-161)
  3. Runs `serve_api.sh` (kills and restarts uvicorn). MUTATES.
  4. Health check `GET /v1/homelab/feed` with the token; exits 1 if it fails.
  5. If the newest `feed_date` in `ff_rank_explain` is not today (UTC), `POST /v1/homelab/feed/refresh`. MUTATES.
- `./serve_api.sh` — `pkill -f "uvicorn api:app"`, then starts uvicorn. MUTATES. [V]
- `fortress start personal_feed` / `fortress stop personal_feed` — Homelab Control start/stop (stop = `pkill -f 'uvicorn api:app'`). MUTATES. [V] (src: control/services.yaml:120-121)
- `POST /v1/homelab/feed/refresh` — spawns `run_daily.sh` in a new session, logs to `out/manual_refresh.log`. Refuses if an engine run is already active (checks `pgrep -f ".venv/bin/python engine.py"`). MUTATES. [V] (src: api.py:62-80,822-858)
- `GET /v1/homelab/feed/refresh/status` — READ. [V]
- `DELETE /v1/homelab/connect/{provider}` — deletes stored OAuth tokens and deactivates sources. DELETES. [V] (src: api.py:1106-1115; oauth.py:217)
- `PUT /v1/entries` (mark unread) and `PUT /v1/entries/{id}/bookmark` (unstar) delete `ff_feedback` rows. DELETES. [V] (src: api.py:711,722)
- `./install.sh` — creates venv, may create `.env` from the example with a new token and key, applies `schema.sql` with `docker exec -i n8n_postgres psql`. MUTATES. [V] (src: install.sh:1-48)
- `docker compose up -d feed-api` / `docker compose run --rm feed-engine` — alternative container path. MUTATES. [V] (src: docker-compose.yml:3-5)
- `./.venv/bin/python connect.py substack --private-rss <url>` — developer-only connect tool. MUTATES. [V] (src: install.sh:48; README.md:62)
- `npx -y @aloth/cred1 --export-compact data/cred1.compact.json` — downloads the trust dataset. MUTATES. [V] (src: README.md:72-74)
- `curl -s http://127.0.0.1:8077/healthz` — READ, no token needed. [V] (src: api.py:1117)

## Depends on
- **AI brain on :8081 (llama-server).** Summaries (`enrich/pi_summary.py` → `llm.chat`) and learn chapter generation (`learn/generate.py`) call `POST {FF_LLM_BASE_URL}/v1/chat/completions` with thinking disabled. [V] (src: llm.py:16-55; config.py:28; grep llm.chat)
- If :8081 is down, `llm.chat` returns None; the engine falls back to non-AI summaries. [V] (src: llm.py:53-55; README.md:35) Learn generation then produces nothing. [I]
- `run_daily.sh` and `run_learn.sh` do **not** start the model. Only `start_backend.sh` does. [V] (src: run_daily.sh; run_learn.sh; start_backend.sh:30-46)
- `start_backend.sh` launches the model directly, outside `fortress start ai_llama` and its GPU guard. [V] (src: DUM-E.md F7; start_backend.sh:36)
- GPU: indirectly, through :8081. The service itself is `gpu: false`. [V] (src: control/services.yaml:123)
- **Postgres `n8n_postgres`** (n8n stack). Required for the API, the engine, and learn. [V] (src: README.md:26; db.py traceback in out/cron.log)
- The Docker network `n8n_default` (compose path only). [V] (src: docker-compose.yml:37-40)
- Notifier :8001 — optional; `NOTIFY` is hard-set to `False` in config, but `--notify` forces it. [V] (src: config.py:49-51; engine.py:797-801)
- Gemini API — optional, for YouTube video enrichment; needs `GEMINI_API_KEY`. [V] (src: README.md:99; config.py:33-35)
- Mesh VPN (e.g. Tailscale) serve — for OAuth callbacks via `PUBLIC_BASE_URL` (`…ts.net/ff`). [V] (src: .env.example:30-31; config.py:53-56)
- Ollama :11434 — only if `FF_LLM_BASE_URL` contains `11434`. [V] (src: llm.py:27-28)
- `pi` CLI on PATH (nvm). `run_daily.sh` adds it, but current code calls llama over HTTP; whether `pi` is still used anywhere is [U]. [V] (src: run_daily.sh:20-26; config.py:19-24,26-27)

## How to check it (read-only)
- DUM-E tool `services` — `personal_feed` is "running" when port 8077 is open. [V] (src: control/services.yaml:122)
- DUM-E tool `ports` — `:8077` (uvicorn) and `:8081` (llama-server). [V]
- DUM-E tool `ai_brain` — is :8081 up; the feed needs it at 05:00 and 06:00. [I]
- DUM-E tool `schedules` — the 05:00 and 06:00 lines. [V]
- DUM-E tool `containers` — `n8n_postgres` must be running. [V]
- DUM-E tool `log_tail` on `personal-feed/out/cron.log`, `learn.log`, `api.log`, `llama-server.log` (registered logs). [V] (src: DUM-E.md:626)
- DUM-E tool `incidents` — "personal_feed not running (default service)" repeats in `incidents.log`. [V] (src: DUM-E.md F6)
- DUM-E tool `graph` — dependency edges feed → ai_llama, feed → n8n. [I]
- Owner, read-only: `curl -s http://127.0.0.1:8077/healthz`. [V] (src: api.py:1117)
- Owner, read-only: `ls -la ~/homelab/personal-feed/out/` — `latest.json` should be from today. [V]
- Owner, read-only: `tail -n 30 ~/homelab/personal-feed/out/cron.log`. [V]

## Known problems and fixes
- **Cron jobs fail when the Postgres container IP changes.** The DSN in `.env` holds a Docker IP. After a reboot the IP can change. Only `start_backend.sh` rewrites it. The last 05:00 and 06:00 runs (2026-10-19) ended with `psycopg2.OperationalError: connection to server at "172.21.0.2", port 5432 failed: No route to host`. 8 such failures in each log. [V] (src: out/cron.log tail; out/learn.log tail; start_backend.sh:15-28) Fix (owner): make the engine use a stable address (publish 5432 on 127.0.0.1, or run the engine via compose on the `n8n_default` network). Short-term: running `start_backend.sh` resyncs `.env`. DUM-E path: `service_start personal_feed` (approved) runs `start_backend.sh`, but see the next item.
- **Starting the feed can start the AI brain.** `start_backend.sh` launches `llama-server-ctl` if :8081 is down, bypassing the GPU guard and the VRAM watchdog's pause. [V] (src: start_backend.sh:30-46; DUM-E.md F7) Today's `out/llama-server.log` shows paired "Starting …" lines, consistent with two launchers racing at boot. [V] (src: out/llama-server.log) [I] race. Fix (owner): remove the launch from `start_backend.sh` or route it through `fortress start ai_llama`.
- **The cron comment is outdated.** It says "engine uses local GPU via Pi"; the code now calls llama-server over HTTP. [V] (src: crontab comment; llm.py:1-6)
- **Model id mismatch.** `.env.example` sets `FF_PI_MODEL=hauhaucs-qwen3.6-35b-iq3m`; `config.py` defaults to `…-q4km`; the server alias is always `…-q4km`. llama-server likely ignores the model name. [V] values (src: .env.example:10; config.py:22; DUM-E.md F8); effect [U].
- **No CRED-1 dataset.** `data/` is empty, so trust step 1 uses only the built-in trusted list (`thehackernews.com`, `bleepingcomputer.com`, `krebsonsecurity.com`, `arstechnica.com`, `arxiv.org`, `technologyreview.com`, `googleprojectzero.blogspot.com`, `cisa.gov`, `schneier.com` → 0.9) and 0.6 for everything else. [V] (src: trust/cred1.py:23-28,56-79; cmd: ls data)
- **API listens on all interfaces** (`0.0.0.0:8077`) with the firewall off. Token-protected. [V] (cmd: ss; src: DUM-E.md F9)
- **Health alert noise.** `personal_feed` "not running (default service)" × 735 in `incidents.log`. [V] (src: DUM-E.md F6)
- **Learn and feed share the GPU with Ollama.** Collab notes say chapters took ~3–4 min instead of ~33 s when both models were loaded. [V] (src: collab/STATUS.md, 2026-07-04 entry)
- **Gaps in runs.** No cron output after 2026-10-19; the host was likely off until 2026-10-29. [I] (src: out/ timestamps; DUM-E.md F6)

## Logs
- `out/cron.log` — 06:00 build. Look for Python tracebacks and `OperationalError … No route to host`. No timestamps. [V]
- `out/learn.log` — 05:00 learn run. Same failure pattern. [V]
- `out/manual_refresh.log` — refreshes started by the API (app button or `start_backend.sh`). Contains the printed deck. [V]
- `out/api.log` — uvicorn log; overwritten at each API start. Good: `Application startup complete`, `GET /v1/homelab/feed … 200 OK`. [V]
- `out/llama-server.log` — `start_backend.sh`'s model launches. Good: `Ready: http://0.0.0.0:8081/v1`. [V]
- `~/.local/state/llama-server-ctl.log` — the model server itself (31 MB). [V] (src: DUM-E.md F2)
- Engine prints `[retention] purged N articles, M remain` after a full build. [V] (src: engine.py:262-265)

## Rules for DUM-E here
- DUM-E must never run `run_daily.sh`, `run_learn.sh`, `start_backend.sh`, `serve_api.sh`, `install.sh`, `engine.py`, or `connect.py` directly. [V] (task rules)
- DUM-E must never POST to the feed API (refresh, feedback, connect, algorithm). [V] (task rules)
- DUM-E must never open `.env`. It may name its variables. [V]
- `service_start personal_feed` (approved action) runs `start_backend.sh`. Before asking, DUM-E must warn: it edits `.env`, may start the AI model on the GPU outside the guard, restarts uvicorn, and may trigger a feed rebuild that deletes old articles. [V] (src: start_backend.sh; retention.py)
- `service_stop personal_feed` runs `pkill -f 'uvicorn api:app'`. The Capy app loses its server until restart. [V] (src: control/services.yaml:121)
- If the AI brain is needed for the 05:00/06:00 jobs, use `llama_start` (approved), not the feed's launcher. [I]
- DUM-E has no action to run a build now; the owner runs: `cd ~/homelab/personal-feed && ./run_daily.sh`.
- DELETES operations that exist here:
  - `engine.py _persist`: `DELETE FROM ff_rank_explain` (whole table) before writing the new deck. [V] (src: engine.py:627)
  - `retention.purge_stale`: `DELETE FROM ff_articles` older than `retention_days` (default 7) unless starred, in today's deck, or agent-authored; then `DELETE FROM ff_seen` orphans. Runs after every full build. [V] (src: retention.py:41-71; engine.py:261)
  - `learn/generate.py`: deletes a chapter's cards and quiz, and can delete the chapter. [V] (src: learn/generate.py:235-236,277)
  - `oauth.disconnect` / `DELETE /v1/homelab/connect/{provider}`: deletes stored OAuth tokens. [V] (src: oauth.py:217; api.py:1106)
  - `oauth_flow.py`: deletes pending OAuth states older than 10 minutes. [V] (src: oauth_flow.py:58,78)
  - API mark-unread / unstar delete `ff_feedback` rows. [V] (src: api.py:711,722)
  - `start_backend.sh` rewrites `.env` with `sed -i`. [V] (src: start_backend.sh:21)
  - `serve_api.sh` overwrites `out/api.log`; the engine overwrites `out/latest.json` and `out/latest.txt`. [V]
  - Schema/migrations: `ON DELETE CASCADE` on many `ff_*`, `ff_learn_*` and `jd_*` foreign keys, so deleting an article removes its trust, rank and feedback rows. [V] (src: schema.sql:52-118; migrations/005, 018, 019)

## Open questions
- What is the current `FF_PG_DSN` host and does it match `n8n_postgres` now? Today's 21:11 refresh worked, so probably yes. [I] Settle: owner runs `docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' n8n_postgres` and compares with `.env` himself.
- Which `FF_LLM_MODEL` / `FF_LLM_BASE_URL` does `.env` set? [U] Settle: owner reads `.env`.
- Is `pi` still used by any enrichment path? [U] Settle: `grep -rn "PI_BIN\|subprocess" enrich/ learn/` (read-only).
- What is `retention_days` in `ff_config`? Default 7 if unset. [U] Settle: owner queries `SELECT value FROM ff_config WHERE key='retention_days'`.
- Is the Mesh VPN (e.g. Tailscale) serve path `/ff` configured? [U] Settle: owner runs `mesh-vpn serve status`.
