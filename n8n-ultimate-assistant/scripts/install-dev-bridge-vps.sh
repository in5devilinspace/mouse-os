#!/usr/bin/env bash
# install-dev-bridge-vps.sh — run ON THE VPS (as root) next to Onyx/n8n.
#
# Keeps dev-bridge polling 24/7 so Telegram-approved fixes fire without Matt's dev PC.
#
# Usage (on VPS):
#   cd /opt/n8n-ultimate-assistant   # or wherever the repo lives
#   sudo bash scripts/install-dev-bridge-vps.sh
#
# Optional env before running:
#   N8N_ENV=/opt/n8n/.env
#   REPO_ROOT=/opt/n8n-ultimate-assistant
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
INSTALL_DIR="/opt/dev-bridge"
N8N_ENV="${N8N_ENV:-/opt/n8n/.env}"
SERVICE="vps-dev-bridge"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root on the VPS: sudo bash $0" >&2
  exit 1
fi

read_env_value() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 0
  grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true
}

echo "==> VPS dev-bridge install"
echo "    Repo: ${REPO_ROOT}"
echo "    Install: ${INSTALL_DIR}"

mkdir -p "$INSTALL_DIR"
cp "$REPO_ROOT/dev-bridge/bridge.py" "$INSTALL_DIR/bridge.py"
cp "$REPO_ROOT/dev-bridge/fix_prompt.md" "$INSTALL_DIR/fix_prompt.md"
chmod +x "$INSTALL_DIR/bridge.py"

BEARER="$(read_env_value "$N8N_ENV" "HOME_BRIDGE_TOKEN")"
HMAC="$(read_env_value "$N8N_ENV" "DEVBRIDGE_HMAC_SECRET")"
CLIPROXY_KEY="$(read_env_value "$N8N_ENV" "CLIPROXY_API_KEY")"
if [[ -z "$CLIPROXY_KEY" ]]; then
  CLIPROXY_KEY="$(read_env_value /root/cliproxyapi/.env "API_KEY" 2>/dev/null || true)"
fi

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  cat > "$INSTALL_DIR/.env" <<EOF
# dev-bridge VPS — polls local n8n, fixes repo on this host
DEV_BRIDGE_BASE_URL=http://127.0.0.1:5678
DEV_BRIDGE_REPO=${REPO_ROOT}
DEV_BRIDGE_MODE=vps
DEV_BRIDGE_CLAUDE=claude
DEV_BRIDGE_GIT_BRANCH=main
POLL_INTERVAL=3
DEV_BRIDGE_TIMEOUT_SECS=2400
DEV_BRIDGE_BEARER=${BEARER}
DEV_BRIDGE_HMAC_SECRET=${HMAC}
CLIPROXY_BASE_URL=http://172.19.0.1:8317/v1
CLIPROXY_API_KEY=${CLIPROXY_KEY}
EOF
  echo "    Created ${INSTALL_DIR}/.env"
else
  echo "    Keeping existing ${INSTALL_DIR}/.env"
fi

if [[ -z "$(read_env_value "$INSTALL_DIR/.env" "DEV_BRIDGE_BEARER")" ]]; then
  echo "!! DEV_BRIDGE_BEARER empty — set HOME_BRIDGE_TOKEN in ${N8N_ENV}" >&2
  exit 1
fi

if [[ -z "$(read_env_value "$INSTALL_DIR/.env" "DEV_BRIDGE_HMAC_SECRET")" ]]; then
  echo "!! Warning: DEV_BRIDGE_HMAC_SECRET empty — add DEVBRIDGE_HMAC_SECRET to ${N8N_ENV}"
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "==> claude CLI not found — installing @anthropic-ai/claude-code globally"
  if command -v npm >/dev/null 2>&1; then
    npm install -g @anthropic-ai/claude-code || echo "!! npm install failed — install claude manually"
  else
    echo "!! Install Node/npm or place claude on PATH before fixes can run"
  fi
fi

cp "$REPO_ROOT/dev-bridge/vps-dev-bridge.service" "/etc/systemd/system/${SERVICE}.service"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo ""
echo "==> $(systemctl is-active "$SERVICE")"
echo "    Logs: journalctl -u ${SERVICE} -f"
echo "    Config: ${INSTALL_DIR}/.env"
echo ""
echo "Matt's dev PC no longer needs dev-bridge running."
