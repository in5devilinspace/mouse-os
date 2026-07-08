#!/usr/bin/env bash
# Mouse OS one-time setup: let this user create virtual input devices (uinput).
# Run: sudo bash scripts/setup-uinput.sh   — then LOG OUT and back in.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "This needs root. Run: sudo bash $0" >&2
    exit 1
fi

TARGET_USER="${SUDO_USER:-$USER}"

echo "→ loading the uinput kernel module (now and at every boot)"
modprobe uinput || true
echo uinput > /etc/modules-load.d/mouseos-uinput.conf

echo "→ udev rule: /dev/uinput owned by group 'input', mode 0660"
cat > /etc/udev/rules.d/99-mouseos-uinput.rules <<'RULE'
KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
RULE
udevadm control --reload-rules
udevadm trigger --name-match=uinput || true

echo "→ adding $TARGET_USER to the 'input' group"
usermod -aG input "$TARGET_USER"

echo
echo "Done. Log out and back in (group membership needs a fresh session),"
echo "then verify with: mouseos doctor"
