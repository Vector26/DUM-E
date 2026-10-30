#!/usr/bin/env bash
# Remove DUM-E's agent runtime. Run as the owner: bash ~/homelab/DUM-E/uninstall.sh
# Removes: /etc/sudoers.d/dume, /opt/dume, the ~/bin/dume symlink, and the `dume` user.
# Keeps:   ~/homelab/DUM-E (code, knowledge, audit log). /var/lib/dume (conversation history)
#          is removed only if you type DELETE-HISTORY when asked.
set -euo pipefail

[[ -z "${SUDO_USER:-}" ]] || { echo "run as the homelab owner without sudo" >&2; exit 1; }
[[ -t 0 ]] || { echo "needs an interactive terminal" >&2; exit 1; }

echo "This will remove: /etc/sudoers.d/dume, /opt/dume, ~/bin/dume (symlink), the user 'dume'."
read -r -p "Type y to continue: " ok
[[ "$ok" == y ]] || { echo "Cancelled."; exit 0; }

sudo rm -f /etc/sudoers.d/dume
sudo visudo -c >/dev/null
sudo rm -rf /opt/dume
[[ -L "$HOME/bin/dume" ]] && rm -f "$HOME/bin/dume"

read -r -p "Also delete DUM-E's conversation history in /var/lib/dume? Type DELETE-HISTORY to delete, anything else keeps it: " purge
if [[ "$purge" == DELETE-HISTORY ]]; then
  sudo userdel --remove dume 2>/dev/null || sudo userdel dume
else
  sudo userdel dume
  echo "Kept /var/lib/dume (now owned by a removed uid; delete it yourself later if wanted)."
fi
echo "DUM-E runtime removed. ~/homelab/DUM-E is untouched."
