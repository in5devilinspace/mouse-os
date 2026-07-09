#!/usr/bin/env bash
# dev-bridge-tmux.sh — debug helper: run dev-bridge in a tmux session.
#
# Usage:
#   bash scripts/dev-bridge-tmux.sh
#   tmux attach -t dev-bridge
set -euo pipefail

SESSION="dev-bridge"
INSTALL_DIR="${HOME}/.dev-bridge"
BRIDGE="${INSTALL_DIR}/bridge.py"
TMUX_CONF="/exec-daemon/tmux.portal.conf"

if [[ ! -f "$BRIDGE" ]]; then
  echo "dev-bridge not installed. Run: bash scripts/install-dev-bridge.sh" >&2
  exit 1
fi

tmux_cmd() {
  if [[ -f "$TMUX_CONF" ]]; then
    tmux -f "$TMUX_CONF" "$@"
  else
    tmux "$@"
  fi
}

if tmux_cmd has-session -t "$SESSION" 2>/dev/null; then
  echo "Session '$SESSION' already running."
else
  tmux_cmd new-session -d -s "$SESSION" "python3 ${BRIDGE}"
  echo "Started dev-bridge in tmux session '$SESSION'."
fi

echo "Attach: tmux attach -t ${SESSION}"
