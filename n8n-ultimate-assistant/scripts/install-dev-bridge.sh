#!/usr/bin/env bash
# install-dev-bridge.sh — one-command dev-bridge setup on Matt's dev machine.
#
# Usage (from n8n-ultimate-assistant repo root):
#   bash scripts/install-dev-bridge.sh
#   bash scripts/install-dev-bridge.sh --tmux
#   bash scripts/install-dev-bridge.sh --no-start
#   bash scripts/install-dev-bridge.sh --force-env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_SRC="$REPO_ROOT/dev-bridge"
INSTALL_DIR="${HOME}/.dev-bridge"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="dev-bridge"
ASSISTANT_ENV="${HOME}/.assistant-bridge/.env"

USE_TMUX=0
NO_START=0
FORCE_ENV=0

for arg in "$@"; do
  case "$arg" in
    --tmux) USE_TMUX=1 ;;
    --no-start) NO_START=1 ;;
    --force-env) FORCE_ENV=1 ;;
    -h|--help)
      echo "Usage: bash scripts/install-dev-bridge.sh [--tmux] [--no-start] [--force-env]"
      exit 0
      ;;
    *)
      echo "Unknown flag: $arg" >&2
      exit 1
      ;;
  esac
done

read_env_value() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 0
  grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true
}

set_env_if_missing() {
  local key="$1" value="$2"
  local file="$INSTALL_DIR/.env"
  if [[ -z "$value" ]]; then
    return 0
  fi
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    if [[ -z "$(read_env_value "$file" "$key")" ]]; then
      sed -i "/^${key}=/d" "$file"
    else
      return 0
    fi
  fi
  echo "${key}=${value}" >> "$file"
}

echo "==> Installing dev-bridge to ${INSTALL_DIR}"

mkdir -p "$INSTALL_DIR"
cp "$DEV_SRC/bridge.py" "$INSTALL_DIR/bridge.py"
cp "$DEV_SRC/fix_prompt.md" "$INSTALL_DIR/fix_prompt.md"
chmod +x "$INSTALL_DIR/bridge.py"

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  cat > "$INSTALL_DIR/.env" <<EOF
# dev-bridge — Onyx self-fix poller (see dev-bridge/README.md)
DEV_BRIDGE_BASE_URL=https://n8n.microtool.dev
DEV_BRIDGE_REPO=${REPO_ROOT}
DEV_BRIDGE_CLAUDE=claude
POLL_INTERVAL=3
DEV_BRIDGE_TIMEOUT_SECS=2400
DEV_BRIDGE_BEARER=
DEV_BRIDGE_HMAC_SECRET=
EOF
  echo "    Created ${INSTALL_DIR}/.env"
else
  echo "    Keeping existing ${INSTALL_DIR}/.env"
fi

set_env_if_missing "DEV_BRIDGE_BASE_URL" "https://n8n.microtool.dev"
set_env_if_missing "DEV_BRIDGE_REPO" "$REPO_ROOT"
set_env_if_missing "DEV_BRIDGE_CLAUDE" "claude"
set_env_if_missing "POLL_INTERVAL" "3"
set_env_if_missing "DEV_BRIDGE_TIMEOUT_SECS" "2400"

# Reuse home-bridge bearer when available.
if [[ -z "$(read_env_value "$INSTALL_DIR/.env" "DEV_BRIDGE_BEARER")" ]]; then
  HB_BEARER="$(read_env_value "$ASSISTANT_ENV" "BRIDGE_BEARER")"
  if [[ -n "$HB_BEARER" ]]; then
    set_env_if_missing "DEV_BRIDGE_BEARER" "$HB_BEARER"
    echo "    Copied DEV_BRIDGE_BEARER from ~/.assistant-bridge/.env"
  fi
fi

if [[ -z "$(read_env_value "$INSTALL_DIR/.env" "DEV_BRIDGE_BEARER")" ]]; then
  NEW_BEARER="$(openssl rand -hex 24 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(24))')"
  set_env_if_missing "DEV_BRIDGE_BEARER" "$NEW_BEARER"
  echo ""
  echo "!! DEV_BRIDGE_BEARER was empty — generated a new token."
  echo "   Add this to n8n HomeBridge credential: Bearer ${NEW_BEARER}"
  echo "   Or paste your existing HomeBridge bearer into ${INSTALL_DIR}/.env"
  echo ""
fi

if [[ -z "$(read_env_value "$INSTALL_DIR/.env" "DEV_BRIDGE_HMAC_SECRET")" ]]; then
  echo "!! DEV_BRIDGE_HMAC_SECRET is empty."
  echo "   Copy VPS env DEVBRIDGE_HMAC_SECRET into ${INSTALL_DIR}/.env"
  echo "   (Polling works; result posts fail HMAC verify until this matches.)"
  echo ""
fi

mkdir -p "$SYSTEMD_USER_DIR"
cp "$DEV_SRC/dev-bridge.service" "$SYSTEMD_USER_DIR/${SERVICE_NAME}.service"

if [[ "$NO_START" -eq 0 ]]; then
  if systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user restart "$SERVICE_NAME" || systemctl --user start "$SERVICE_NAME"
    echo ""
    echo "==> systemd: $(systemctl --user is-active "$SERVICE_NAME" 2>/dev/null || echo inactive)"
    echo "    Logs: journalctl --user -u ${SERVICE_NAME} -f"
  else
    echo ""
    echo "!! systemd user session not available (no D-Bus)."
    echo "   Files installed. On your dev PC run:"
    echo "     systemctl --user daemon-reload && systemctl --user enable --now ${SERVICE_NAME}"
    echo "   Or: bash scripts/dev-bridge-tmux.sh"
  fi
else
  echo "    Skipped systemd start (--no-start). Service unit copied to ${SYSTEMD_USER_DIR}/"
fi

if [[ "$USE_TMUX" -eq 1 ]]; then
  bash "$SCRIPT_DIR/dev-bridge-tmux.sh"
fi

echo ""
echo "Done. Config: ${INSTALL_DIR}/.env"
echo "Verify: systemctl --user is-active ${SERVICE_NAME}"
