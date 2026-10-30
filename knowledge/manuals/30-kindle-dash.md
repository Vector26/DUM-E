---
title: Kindle Dashboard
scope: the Kindle wall dashboard: PNG renderer (cron every 15 min), the token-gated PNG server (user unit kindle-dash.service on :18765), the two source folders, and the habits/news input files
last_verified: 2026-10-29
sources: ~/kindle-dash/{render_dash.py,serve_dash.py,render.log,dash.png}, homelab/kindle-dash/{README.md,CLIENT_SETUP_PROMPT.md,.env.example,kindle-dash.service,render_dash.py,serve_dash.py}, systemctl --user cat/status kindle-dash.service, crontab -l, ss -ltnp
---

# Kindle Dashboard

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
A jailbroken Kindle Basic 11th gen (KT5) shows a grayscale "Home Dashboard" picture on the wall. [V] (src: homelab/kindle-dash/README.md:3)
The homelab draws that picture as `~/kindle-dash/dash.png` every 15 minutes. It shows the date and time, a habit checklist, and up to 5 news or note lines. [V] (src: crontab -l; ~/kindle-dash/render_dash.py:51-88)
A tiny Python web server hands the PNG to the Kindle over the home LAN when the request carries the right token. [V] (src: serve_dash.py:16-38)
There is no write API. Other tools change the dashboard by overwriting two input files. [V] (src: README.md:16-37)

## How the owner refers to it
- "kindle-dash", "Kindle dashboard", "Home Dashboard", "wall dashboard". [V] (src: README.md:1; render_dash.py:60; CLIENT_SETUP_PROMPT.md:9)
- Cron tag `kindle-dash-render`. [V] (cmd: crontab -l)
- Unit `kindle-dash.service` ("Kindle Dashboard PNG server"). [V] (cmd: systemctl --user cat kindle-dash.service)
- No alias in `.bashrc`. [V] (cmd: grep kindle ~/.bashrc → none)

## Components
- **Which folder is canonical:** the README says canonical source is `~/homelab/kindle-dash`; the deployment (run) directory is `~/kindle-dash`. [V] (src: homelab/kindle-dash/README.md:5-6)
- **What actually runs:** cron and the unit both use `~/kindle-dash` (`~/kindle-dash`). [V] (cmd: crontab -l; systemctl --user cat)
- The two folders are separate real directories, not symlinks. [V] (cmd: readlink -f)
- `serve_dash.py` is identical in both folders. [V] (cmd: diff → no difference)
- `render_dash.py` differs. The running copy (`~/kindle-dash`, edited 2026-08-22 21:10) renders 1072×1448. The canonical copy renders 600×800. [V] (cmd: diff; file ~/kindle-dash/dash.png → "1072 x 1448, 8-bit grayscale")
- `kindle-dash.service` (user unit) — `WorkingDirectory=%h/kindle-dash`, `EnvironmentFile=%h/kindle-dash/.env`, `ExecStart=/usr/bin/python3 %h/kindle-dash/serve_dash.py`, `Restart=always`, `WantedBy=default.target`. Identical to the repo copy. [V] (cmd: systemctl --user cat; diff)
- Unit state: enabled, active (running) since 2026-10-29 21:06:14, PID 8846. [V] (cmd: systemctl --user status kindle-dash.service)
- Port **18765**, bound on `0.0.0.0` (all interfaces), process `python3` PID 8846. [V] (cmd: ss -ltnp)
- This explains the "unidentified 18765 (python3)" port in DUM-E.md. [I] (src: DUM-E.md:428)
- Routes: `GET /kindle/dash.png?token=…` and also `GET /dash.png?token=…`. Anything else returns 404. Wrong or missing token returns 403. No PNG yet returns 503. [V] (src: serve_dash.py:20-31)
- Response headers on 200: `Content-Type: image/png`, `Cache-Control: no-store, no-cache, must-revalidate`, `Content-Length`. [V] (src: serve_dash.py:33-37)
- The server logs nothing per request (`log_message` is a no-op). [V] (src: serve_dash.py:17-18)
- Cron, every 15 minutes: `cd ~/kindle-dash && . ./.env && HABITS_FILE=~/kindle-dash/habits.json NEWS_FILE=~/kindle-dash/news.txt python3 render_dash.py >> ~/kindle-dash/render.log 2>&1 # kindle-dash-render`. [V] (cmd: crontab -l)
- The renderer uses system `python3` with Pillow (`/usr/lib/python3/dist-packages/PIL`). Fonts: DejaVu Sans, then Liberation Sans, then the PIL default. [V] (src: render_dash.py:10,41-48; cmd: ls PIL)
- Client side (on the Kindle, not on the homelab): planned `/mnt/us/kindle-dash/update.sh`, KUAL extension, `dash.conf` with the full URL, refresh every 15 min with `rtcwake`. Whether this was built is [U]. (src: CLIENT_SETUP_PROMPT.md:47-61)

## Files and data
- `~/kindle-dash/` — the running deployment. [V]
  - `render_dash.py`, `serve_dash.py` — code. [V]
  - `.env` — SECRET. Holds `DASH_TOKEN` (and per `.env.example` also `DASH_OUT`, `DASH_PORT`). Not opened. Mode 664. [V] name, mode (cmd: stat); variables from `homelab/kindle-dash/.env.example:1-3`
  - `PUBLIC_URL.txt` — SECRET. Full Kindle URL including the token. Mode 600. Not opened. [V] (cmd: ls -la; README.md:73)
  - `habits.json` — PRIVATE. Format: a JSON array of `{"name": string, "done": bool}`. Every row is drawn as `[x] name` or `[ ] name`. 160 bytes. [V] (src: README.md:12; render_dash.py:17-26,69-72; cmd: ls -la)
  - `news.txt` — PRIVATE. Format: plain text, one item per line, blank lines dropped, first 5 lines shown, each cut to 75 characters (42 in the canonical copy). 140 bytes. [V] (src: README.md:13; render_dash.py:29-38,79-81)
  - `dash.png` — output, ~29 KB, rewritten every 15 min (last 22:30). [V] (cmd: ls -la)
  - `render.log` — 153 KB, only "Wrote …" lines, no errors. Never rotated. [V] (cmd: grep -vc '^Wrote' → 0)
- `~/homelab/kindle-dash/` — canonical source. [V]
  - `README.md` — data, render and HTTP contracts, deploy steps, ops. [V]
  - `CLIENT_SETUP_PROMPT.md` — SECRET. A prompt for an agent setting up the Kindle. It contains plaintext Wi-Fi passwords (lines 30–31; values not copied here). [V]
  - `.env.example` — variable names `DASH_TOKEN`, `DASH_OUT`, `DASH_PORT` with placeholder values. [V]
  - `kindle-dash.service` — unit file source. [V]
  - `habits.json`, `news.txt` — PRIVATE sample or older copies (2026-08-22). Same sizes as the deployed ones. [V] (cmd: ls -la)
- Optional future input `stats.json` (`{"key": value}`) is mentioned but not used by the code. [V] (src: README.md:14; render_dash.py has no stats)
- Habit and news defaults are built in if the files are missing. [V] (src: render_dash.py:21-26,33-38)

## Commands
- Manual render: `cd ~/kindle-dash && . ./.env && python3 render_dash.py` — overwrites `dash.png`. MUTATES (DELETES the previous PNG by overwrite). [V] (src: README.md:44-46; render_dash.py:86-88)
- Update inputs: `printf '[{"name":"…","done":true}]\n' > ~/kindle-dash/habits.json`, `printf 'Line one\n' > ~/kindle-dash/news.txt` — DELETES (overwrites) the previous content. [V] (src: README.md:22-25)
- Remote update from the tailnet: `ssh owner@100.x.x.x 'cat > ~/kindle-dash/news.txt' < news.txt` — DELETES (overwrite). [V] (src: README.md:31-33)
- Deploy from canonical: `scp … render_dash.py serve_dash.py habits.json news.txt owner@100.x.x.x:~/kindle-dash/` and the unit file to `~/.config/systemd/user/`. MUTATES and DELETES (overwrites the running copies and the live habits/news). [V] (src: README.md:79-85)
- Health check from the README: `curl -fsSL "http://127.0.0.1:18765/kindle/dash.png?token=$(grep ^DASH_TOKEN= ~/kindle-dash/.env | cut -d= -f2)" | file -` — READ, but it reads the secret token. DUM-E must not run it. [V] (src: README.md:94-97)
- `systemctl --user status kindle-dash.service` — READ. [V]
- `journalctl --user -u kindle-dash.service -f` — READ. [V] (src: README.md:90)
- `systemctl --user restart kindle-dash.service` — MUTATES (needed after a token change). [V] (src: README.md:101-102)
- Token rotation: `openssl rand -hex 24`, edit `.env`, restart the service, update the Kindle's `dash.conf`. MUTATES. [V] (src: README.md:101-102)
- `file ~/kindle-dash/dash.png` — READ; should print "PNG image data … grayscale". [V]

## Depends on
- GPU: no. AI brain :8081: no. Ollama: no. Notifier :8001: no. [V] (src: render_dash.py, serve_dash.py)
- System `python3` and Pillow. [V]
- The user systemd manager (user unit runs at boot only if lingering is on or the user logs in). [I] Lingering status [U].
- The LAN: the Kindle and the homelab must share Wi-Fi; the Kindle uses `http://192.168.1.41:18765/…`. The homelab LAN IP is DHCP. [V] (src: README.md:61-75; cmd: ip -4 addr → 192.168.1.41/24)
- The Wi-Fi guard (manual 29) can move the homelab to another Wi-Fi network. Then the Kindle can no longer reach it. [I] (src: wifi-safe-switch.sh:265-286)

## How to check it (read-only)
- DUM-E tool `services` — state of `kindle-dash.service` (if in the unit allowlist). [I]
- DUM-E tool `ports` — `:18765` must be listening. [V] (cmd: ss -ltnp)
- DUM-E tool `schedules` — the `*/15` line tagged `kindle-dash-render`. [V]
- DUM-E tool `log_tail` on `kindle-dash/render.log` (registered log). Healthy = recent "Wrote ~/kindle-dash/dash.png (N bytes)" lines. [V] (src: DUM-E.md:626)
- DUM-E tool `disk_memory` — not relevant (tiny files).
- Owner, read-only: `ls -la ~/kindle-dash/dash.png` — the time should be within the last 15 minutes. [V]
- Owner, read-only: `file ~/kindle-dash/dash.png`. [V]
- Owner, read-only: `systemctl --user status kindle-dash.service`. [V]

## Known problems and fixes
- **Source drift between the two folders.** Running renderer = 1072×1448; canonical = 600×800; README says 600×800. A deploy from the canonical folder would shrink the picture. [V] (cmd: diff; file dash.png) Which size the Kindle wants is [U] (the KT5 screen is 600×800 per README:3; the running copy was changed later the same evening). Fix (owner): decide the size and copy the chosen file to the other folder. DUM-E has no action for this.
- **The README lists one route; the code accepts two** (`/kindle/dash.png` and `/dash.png`). Harmless. [V] (src: serve_dash.py:22)
- **Weak default token.** If `.env` is missing, both scripts fall back to `change-me-kindle-dash-token`. The unit loads `.env`, so this only bites if `.env` is lost. [V] (src: serve_dash.py:12; render_dash.py:14)
- **Token travels in clear text on the LAN and the server listens on all interfaces** (also on Docker bridges and `mesh-vpn0`). [V] (src: README.md:74-75,104; cmd: ss → 0.0.0.0:18765) Accepted by design for home Wi-Fi. [V]
- **Token compare is not constant-time.** Low risk on a home LAN. [V] (src: serve_dash.py:26)
- **DHCP address.** If the router gives the homelab a new IP, the Kindle breaks. README asks for a DHCP reservation; whether it exists is [U]. [V] (src: README.md:70-71)
- **Plaintext Wi-Fi passwords in `CLIENT_SETUP_PROMPT.md`.** [V] (src: CLIENT_SETUP_PROMPT.md:30-31) Fix (owner): remove them from the file; rotate if the file was shared. DUM-E has no action for this.
- **Secret files are group-readable.** `~/kindle-dash/.env` mode 664. [V] (cmd: stat) Fix (owner): `chmod 600 ~/kindle-dash/.env`. DUM-E has no action for this.
- **The cron line sources `.env` into the renderer**, but the renderer only uses `DASH_OUT` (and an unused `TOKEN`). Harmless. [V] (src: render_dash.py:12-14)
- **`render.log` grows forever** (~150 KB so far). Low risk. [V]

## Logs
- `~/kindle-dash/render.log` — one "Wrote … (N bytes)" line per render. Anything else (a Python traceback) means the render failed. [V]
- `kindle-dash.service` — user journal. Startup only; no request logging. [V] (src: serve_dash.py:17-18,43)
- The Kindle side logs on the Kindle (planned). [U]

## Rules for DUM-E here
- DUM-E must never open `~/kindle-dash/.env`, `~/kindle-dash/PUBLIC_URL.txt`, or `homelab/kindle-dash/CLIENT_SETUP_PROMPT.md` (SECRET). [V] (task rules)
- DUM-E must never print `habits.json` or `news.txt` contents (PRIVATE). It may say the format and the file times. [V]
- DUM-E must never call the README health-check `curl`, because it reads the token from `.env`. [V] (src: README.md:95)
- DUM-E may restart the server only if `kindle-dash` is registered as a service id and the owner approves `service_start`/`service_stop`. It is not in `services.yaml` today. [V] (cmd: grep kindle control/services.yaml → none) Otherwise DUM-E has no action for this; the owner runs: `systemctl --user restart kindle-dash.service`.
- DUM-E has no action to render; the owner runs: `cd ~/kindle-dash && . ./.env && python3 render_dash.py`.
- DELETES operations that exist here:
  - Every render overwrites `~/kindle-dash/dash.png`. [V]
  - Writers overwrite `habits.json` and `news.txt` (`>`). [V] (src: README.md:22-25,31)
  - The deploy `scp` overwrites the running scripts, the live habits/news, and the user unit file. [V] (src: README.md:79-85)
  - Token rotation overwrites `DASH_TOKEN` in `.env`. [V] (src: README.md:101-102)

## Open questions
- Was the Kindle-side client (update.sh, KUAL extension, dash.conf) ever installed? [U] Settle: check the Kindle, or look for regular requests (not logged today; would need request logging).
- Is user lingering enabled so the unit starts without a login? [U] Settle: `loginctl show-user owner -p Linger` (owner, read-only).
- Which resolution is correct, 600×800 or 1072×1448? [U] Settle: owner checks the Kindle model's screen and what looks right.
- Does anything other than manual edits write `habits.json` / `news.txt`? No writer was found in cron. [V] (cmd: crontab -l) Other writers (n8n, scripts on the Mac) are [U]. Settle: owner.
