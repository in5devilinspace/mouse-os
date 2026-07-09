# Dev Bridge — Onyx Self-Fix via Claude Code

When Matt tells Onyx to **fix something about itself**, Onyx diagnoses the issue and queues a repair. After Matt approves at the Telegram HITL gate, **dev-bridge** on his dev machine long-polls the VPS, launches **Claude Code** with skills/plugins/MCP, and posts the result back.

## Quick install (recommended)

From this repo root:

```bash
bash scripts/install-dev-bridge.sh
```

This will:

1. Create `~/.dev-bridge/` and copy `bridge.py` + `fix_prompt.md`
2. Seed `~/.dev-bridge/.env` (reuses `BRIDGE_BEARER` from `~/.assistant-bridge/.env` when present)
3. Install and start **systemd user service** `dev-bridge`

**Flags:**

| Flag | Effect |
|------|--------|
| `--tmux` | Also start a `dev-bridge` tmux session (debug) |
| `--no-start` | Install files only; don't enable systemd |
| `--force-env` | Fill in missing env keys (never overwrites non-empty values) |

**Debug in tmux:**

```bash
bash scripts/dev-bridge-tmux.sh
tmux attach -t dev-bridge
```

**Logs:**

```bash
journalctl --user -u dev-bridge -f
systemctl --user is-active dev-bridge
```

## Architecture

```
Matt: "fix email routing"  →  Orchestrator  →  dev_fix agent
       →  enqueue_dev_fix  →  pending_actions  →  Telegram approve
       →  Insert dev_commands  →  dev-bridge poll  →  claude -p ...
       →  POST /webhook/dev/result  →  Telegram notify
```

| Component | Where | Port |
|-----------|-------|------|
| `dev-bridge/control.py` | VPS (Postgres read) | 8622 |
| `dev-bridge/bridge.py` | Dev machine (Claude Code) | — |
| n8n webhooks | VPS | `/webhook/dev/poll`, `/webhook/dev/result` |

## VPS setup

1. Apply DDL: `dev_commands` in `build/schema.sql`
2. Env: `DEVBRIDGE_HMAC_SECRET` (same as dev machine)
3. Credential **DevBridge**: `Authorization: Bearer <DEV_CONTROL_TOKEN>`
4. Credential **HomeBridge**: reused for enqueue + dev poll webhooks
5. Run: `PORT=8622 DEV_CONTROL_TOKEN=... python3 dev-bridge/control.py`
6. Re-import workflow: `python3 scripts/gen-dev-fix.py` then import `build/Matts-Ultimate-Assistant.json`

## Manual dev machine setup (fallback)

```bash
mkdir -p ~/.dev-bridge
cat > ~/.dev-bridge/.env <<'EOF'
DEV_BRIDGE_BASE_URL=https://n8n.microtool.dev
DEV_BRIDGE_BEARER=<same as HomeBridge bearer>
DEV_BRIDGE_HMAC_SECRET=<same as DEVBRIDGE_HMAC_SECRET>
DEV_BRIDGE_REPO=/path/to/n8n-ultimate-assistant
DEV_BRIDGE_CLAUDE=claude
EOF

python3 ~/.dev-bridge/bridge.py
```

Or use the installer instead of copying by hand.

## Usage (Telegram)

- *"Onyx, when I ask about iCloud you only check Gmail — fix that"*
- *"Fix yourself: web agent times out on scroll"*
- *"Did the fix finish?"* → dev_fix checks status

Matt gets an approval card before Claude touches the repo.

## Safety

- HITL gate before any dev_command is inserted (same ACTION LANE as payments)
- HMAC on results (like home-bridge)
- Claude prompt forbids committing secrets or pushing without explicit ask
- Changes stay local until Matt reviews diff

See `dev-bridge/fix_prompt.md` for the Claude Code session brief.
