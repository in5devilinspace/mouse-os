# Onyx Telegram self-diagnosis

Matt wants Onyx to read its own Telegram transcript, find problems, and fix them — **without opening Cursor**. This doc explains what was wired.

## Daily 10am review (automatic)

Every day at **10:00 AM Pacific**, Onyx runs **Daily Reviewer**:

1. Loads last ~150 Telegram messages from `n8n_chat_histories`
2. Loads open HITL actions + yesterday's audit log
3. Sends a **morning digest** to your Telegram
4. If it finds real bugs, queues **one** `dev_fix` job (you approve on Telegram)

**Workflow nodes:** `Schedule Daily Review` → `Load Daily Transcript` → `Daily Reviewer` → `Send Daily Digest`

**Re-apply after edits:** `python3 scripts/gen-daily-review.py` then re-import `build/Matts-Ultimate-Assistant.json` into n8n.

## Fix anytime from Telegram (manual)

Tell Onyx:

- *"Diagnose what went wrong with the Amazon fan search"*
- *"Fix yourself — you gave me the wrong viewer link"*
- *"Read the transcript and patch the workflow"*

→ Routes to **dev_fix** → Telegram approval → **dev-bridge** on VPS runs Claude Code on the repo.

## What you still need running

| Daemon | Where | Purpose |
|--------|-------|---------|
| **dev-bridge** | **VPS** (recommended) | Executes repo fixes after Telegram approve — 24/7 |
| **home-bridge** | Dev PC | Spins up web-agent SSH tunnel (`web_agent_tunnel`) |

### Install dev-bridge on VPS (no dev PC required)

SSH to your VPS, then:

```bash
cd /opt/n8n-ultimate-assistant
sudo bash scripts/install-dev-bridge-vps.sh
journalctl -u vps-dev-bridge -f
```

Requires `HOME_BRIDGE_TOKEN` and `DEVBRIDGE_HMAC_SECRET` in `/opt/n8n/.env`.

### Dev PC install (optional fallback)

Only if you want fixes on a **local** repo clone instead of VPS:

```bash
bash scripts/install-dev-bridge.sh
```

Full details: `n8n-ultimate-assistant/dev-bridge/README.md`

## Cash App card / physical mail

There is **no Cash App API**. Ask Onyx:

> *"Search my iCloud mail for Cash App card delivery"*

→ **email** agent (iCloud IMAP) → **packages** if there's a tracking number.

Zip **90210** / **93021** — tell Onyx once via **profile** agent so it remembers for Amazon checkout.

## Security note

If you spoke passwords aloud near the mic (Amazon login, etc.), they may be in the Telegram transcript or voice STT. **Rotate those passwords** and use the web-agent portal for login instead of dictating credentials to Onyx.
