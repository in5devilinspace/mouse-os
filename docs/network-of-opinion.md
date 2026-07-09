# Network of Opinion

Onyx's **11am showcase**: a swarm of opinion lenses turns your last 48h Telegram transcript into a **7-day forecast** you can see — glass orb, Doppler sweep, scrollable segments.

## Your choices (locked in)

| Setting | Value |
|---------|-------|
| Delivery | Telegram digest **+** live web UI |
| Inputs | Transcript only (tasks/activity) |
| DB | Supabase |
| Hype | Hyperframes MP4 + interactive page |
| Auth | `?token=` in URL |
| Schedule | **11:00 AM Pacific** |

## Links

- **App repo:** `n8n-ultimate-assistant/network-of-opinion/`
- **Web (VPS):** `https://opinion.microtool.dev/?token=YOUR_TOKEN`
- **Hype reel:** `/hype/` on same host

## Local preview

```bash
cd ~/claude-recovery/wsl-the9nine/n8n-ultimate-assistant/network-of-opinion
export NOO_VIEWER_TOKEN=dev
python3 api/server.py
# open http://127.0.0.1:8765/?token=dev
```

Sample data ships in `data/latest.json` until Supabase is wired.

## Onyx wiring

```bash
python3 scripts/gen-network-of-opinion.py
# re-import build/Matts-Ultimate-Assistant.json into n8n
```

Cron node: **Schedule Network of Opinion** → Opinion Swarm → `save_noo_forecast` webhook → Telegram.

Orchestrator routes: "7-day forecast", "Network of Opinion", "show me my week".

## VPS deploy checklist

1. Create Supabase project → run `supabase/schema.sql`
2. Set env on VPS: `NOO_VIEWER_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
3. `cd network-of-opinion/deploy && docker compose up -d --build`
4. Add Caddy block for `opinion.microtool.dev` → `127.0.0.1:8765`
5. Create n8n webhook `noo-save` (POST) → writes Supabase + `data/latest.json`

## Related

- [web-agent shopping](web-agent-shopping.md)
- [Telegram self-diagnosis](onyx-telegram-self-diagnosis.md)
