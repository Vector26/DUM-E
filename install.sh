#!/usr/bin/env bash
# Install DUM-E's agent runtime. Safe to re-run (it refreshes the runtime copy).
# Run as the homelab owner, without sudo:   bash ~/homelab/DUM-E/install.sh
#
# What it does (each step needs sudo; nothing outside these paths is touched):
#   1. system user `dume` (no login shell, home /var/lib/dume)
#   2. /opt/dume: root-owned copies of node, pi and the DUM-E extension (the agent cannot modify them)
#   3. pi config for `dume` (provider -> local model queue on :8181, telemetry off)
#   4. /etc/sudoers.d/dume: `dume` may run ONLY bin/dume-tool as the owner (validated with visudo first)
#   5. ~/bin/dume symlink, state folder permissions, knowledge graph
#   6. smoke tests (isolation + gateway)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OWNER="$(id -un)"
OPT=/opt/dume
AGENT_HOME=/var/lib/dume
MODEL="${DUME_MODEL:-your-local-model-id}"
FORTRESS_CTX="${DUME_CONTEXT:-262144}"
FORTRESS_MAXTOK="${DUME_MAXTOK:-16384}"

die() { echo "install: $*" >&2; exit 1; }
step() { echo; echo "== $*"; }

[[ -z "${SUDO_USER:-}" ]] || die "run without sudo; the script calls sudo itself"
sudo -n true 2>/dev/null || die "needs passwordless sudo for the install steps"

NODE_SRC="$(readlink -f "$(command -v node)")"
NODE_MAJOR="$("$NODE_SRC" -p 'process.versions.node.split(".")[0]')"
(( NODE_MAJOR >= 20 )) || die "node >= 20 needed (found $NODE_MAJOR at $NODE_SRC)"
PI_SRC="$(npm root -g)/@mariozechner/pi-coding-agent"
[[ -f "$PI_SRC/dist/cli.js" ]] || die "pi not found at $PI_SRC"
PI_VERSION="$("$NODE_SRC" -p "require('$PI_SRC/package.json').version")"

step "1/6 system user dume"
if ! getent passwd dume >/dev/null; then
  sudo useradd --system --user-group --home-dir "$AGENT_HOME" --create-home --shell /usr/sbin/nologin dume
  echo "created user dume"
else
  echo "user dume exists"
fi
sudo install -d -o dume -g dume -m 700 "$AGENT_HOME" "$AGENT_HOME/sessions" "$AGENT_HOME/.pi" "$AGENT_HOME/.pi/agent"

step "2/6 runtime in $OPT (root-owned, read-only for dume)"
sudo install -d -o root -g root -m 755 "$OPT" "$OPT/node" "$OPT/node/bin" "$OPT/ext"
sudo install -o root -g root -m 755 "$NODE_SRC" "$OPT/node/bin/node"
sudo rm -rf "$OPT/pi.new"
sudo cp -a "$PI_SRC" "$OPT/pi.new"
sudo chown -R root:root "$OPT/pi.new"
sudo chmod -R u+rwX,go+rX,go-w "$OPT/pi.new"
if [[ -d "$OPT/pi" ]]; then sudo rm -rf "$OPT/pi.old"; sudo mv "$OPT/pi" "$OPT/pi.old"; fi
sudo mv "$OPT/pi.new" "$OPT/pi"
sudo rm -rf "$OPT/pi.old"
sudo install -o root -g root -m 644 "$ROOT/ext/dume.ts" "$OPT/ext/dume.ts"
echo "node $("$OPT/node/bin/node" --version), pi $PI_VERSION"

step "3/6 pi configuration for dume (telemetry off, provider homelab -> model queue :8181)"
sudo -u dume tee "$AGENT_HOME/.pi/agent/settings.json" >/dev/null <<EOF
{
  "lastChangelogVersion": "$PI_VERSION",
  "defaultProvider": "homelab",
  "defaultModel": "$MODEL",
  "enableInstallTelemetry": false
}
EOF
sudo -u dume tee "$AGENT_HOME/.pi/agent/models.json" >/dev/null <<EOF
{
  "providers": {
    "homelab": {
      "baseUrl": "http://127.0.0.1:8181/v1",
      "api": "openai-completions",
      "apiKey": "local-no-key",
      "compat": { "supportsDeveloperRole": false, "supportsReasoningEffort": false },
      "models": [
        { "id": "$MODEL", "name": "Homelab local model", "reasoning": true,
          "input": ["text"], "contextWindow": $FORTRESS_CTX, "maxTokens": $FORTRESS_MAXTOK }
      ]
    }
  }
}
EOF
sudo chmod 600 "$AGENT_HOME/.pi/agent/settings.json" "$AGENT_HOME/.pi/agent/models.json"
sudo install -d -o dume -g dume -m 700 "$AGENT_HOME/.pi/agent/bin"
for tool in fd rg; do
  if [[ -x "$HOME/.pi/agent/bin/$tool" ]]; then
    sudo install -o dume -g dume -m 755 "$HOME/.pi/agent/bin/$tool" "$AGENT_HOME/.pi/agent/bin/$tool"
  fi
done

step "4/6 sudoers rule (validated before install)"
tmp="$(mktemp)"
printf '%s\n' "# DUM-E: the agent user may run only the DUM-E gateway, as the owner. Installed by $ROOT/install.sh" \
  "dume ALL=($OWNER) NOPASSWD: $ROOT/bin/dume-tool" > "$tmp"
sudo visudo -c -f "$tmp" >/dev/null || { rm -f "$tmp"; die "sudoers rule failed validation; nothing installed"; }
sudo install -o root -g root -m 440 "$tmp" /etc/sudoers.d/dume
rm -f "$tmp"
sudo visudo -c >/dev/null || die "sudo configuration invalid after install (check /etc/sudoers.d/dume)"
echo "installed /etc/sudoers.d/dume"

step "5/6 owner files"
chmod 755 "$ROOT/bin/dume" "$ROOT/bin/dume-tool"
mkdir -p "$ROOT/state/pending" "$ROOT/state/results" "$ROOT/state/cache" "$ROOT/knowledge/.history"
chmod 700 "$ROOT/state"
mkdir -p "$HOME/bin"
if [[ -e "$HOME/bin/dume" && ! -L "$HOME/bin/dume" ]]; then
  die "$HOME/bin/dume exists and is not a symlink; not replacing it"
fi
ln -sfn "$ROOT/bin/dume" "$HOME/bin/dume"
if [[ -x "$ROOT/bin/dume" ]]; then
  "$ROOT/bin/dume" rebuild-graph || echo "warn: rebuild-graph skipped (homelab control tree may not exist yet)"
fi

step "6/6 smoke tests"
if sudo -u dume test -r "$HOME/.bashrc"; then die "isolation broken: dume can read the owner's files"; fi
echo "ok: dume cannot read owner home"
if sudo -u dume sudo -n -u "$OWNER" /bin/true 2>/dev/null; then die "sudoers too wide: dume can run arbitrary commands as $OWNER"; fi
echo "ok: dume cannot run other commands as $OWNER"
out="$(echo '{}' | sudo -u dume sudo -n -H -u "$OWNER" -- "$ROOT/bin/dume-tool" ports | head -1)"
[[ "$out" == "port | bound to | known as" ]] || die "gateway call failed: $out"
echo "ok: gateway reachable from dume"
sudo -u dume -H "$OPT/node/bin/node" "$OPT/pi/dist/cli.js" --version >/dev/null && echo "ok: pi runs as dume"

echo
echo "DUM-E installed. Start a conversation with:  dume      (help: dume help)"
