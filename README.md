# Mouse OS 🖱️🗣️

**Your voice is the pointer.** Mouse OS is a voice-controlled cursor agent for Ubuntu — say *"point to firefox"*, *"click"*, *"scroll down"*, and the real on-screen pointer obeys, then confirms out loud. Built accessibility-first for people who can't use their hands. Wayland-native, fully offline.

> Landing page & live demo: see `docs/index.html` (GitHub Pages). Feature roadmap decided by an AI roundtable: `docs/roadmap/2026-07-07-feature-roundtable.md`.

> ▶ **Prefer watching?** [The 2-minute tutorial film](https://in5devilinspace.github.io/mouse-os/mouse-os-tutorial.mp4) — install to "goodbye", narrated by the cursor itself (its real offline voice), captions included. Pipeline: `tools/video/tutorial/`.

## How it works

```
mic (pw-record) → Vosk (grammar-locked, ~60 phrases, offline) → Intent → Engine (FSM)
                                                                    ├─ pointer: uinput virtual mouse (abs → rel → dummy ladder)
                                                                    ├─ resolve: screen regions, 3×3 grid, optional window lookup
                                                                    └─ feedback: spd-say (≤2 words) + console
```

- **A real cursor, not a widget** — a kernel-level virtual input device moves *the* pointer in every app, on Wayland.
- **It talks back** — every consequential action gets a spoken confirmation ("done", "held", "pardon?"). The feedback lexicon shares no word with the command grammar, so the system can never command itself.
- **Safe by default** — starts asleep; `mouse quit` needs `confirm quit` within 10 s; `stop` / `undo` / `never mind` are always in the grammar.
- **Honest degradation** — before the one-time permission setup, it runs in practice (dummy) mode and *says so*.

## Quick start

```bash
# 1. Install (uv recommended)
uv venv .venv && VIRTUAL_ENV=$PWD/.venv uv pip install -e '.[voice,test]'

# 2. One-time: allow virtual input devices (prints what it does; needs sudo)
./scripts/setup-uinput.sh        # then log out & back in

# 3. Health check — tells you exactly what works and how to fix what doesn't
./.venv/bin/mouseos doctor

# 4. Try it without a microphone (text REPL, real cursor if step 2 done)
./.venv/bin/mouseos run --input repl

# 5. Voice: download the offline model (~40 MB) and go
./.venv/bin/mouseos setup-model
./.venv/bin/mouseos run --input voice
```

## Say this

| You say | It does |
|---|---|
| `mouse wake` / `mouse sleep` | arm / disarm listening (starts asleep) |
| `point to firefox` · `focus files` | cursor to that window (aliases configurable) |
| `click` · `double click` · `right click` · `middle click` | clicks at the cursor |
| `hold` … `release` | drag |
| `move up` · `move left a little` · `move right a lot` | nudge 100 / 25 / 300 px |
| `go to center` · `go to top left` · `go to right edge` | named regions |
| `grid one` … `grid nine` | 3×3 grid jump, then nudge to refine |
| `scroll up` · `scroll down a lot` | wheel |
| `stop` · `undo` · `never mind` | always-hot recovery |
| `where am i` · `list windows` | orientation |
| `show my cameras` | launches your camera wall (configurable command) |
| `mouse quit` → `confirm quit` | exit (two-step, expires in 10 s) |

Text-REPL extras: `move to 960 600`, `move to 50% 50%`, `status`, `help`.

## Configuration

`~/.config/mouseos/config.toml`:

```toml
start_asleep = true
[steps]
little = 25
normal = 100
lot = 300
[apps]           # window aliases for "point to <app>" / "focus <app>"
firefox = "firefox"
files = "nautilus"
[cameras]        # what "show my cameras" launches — see docs/research/reolink-cameras-on-ubuntu.md
command = "xdg-open http://localhost:1984/stream.html?src=cam1&src=cam2&src=cam3&src=cam4"
```

## Docs

- `docs/superpowers/specs/2026-07-08-mouse-os-v1-design.md` — the v1 design (judge-panel synthesis + roundtable amendments)
- `docs/roadmap/2026-07-07-feature-roundtable.md` — the four-persona roadmap debate, with dissents
- `docs/research/reolink-cameras-on-ubuntu.md` — verified: view 4 Reolink cams (Home Hub) on Ubuntu; VLC test + go2rtc grid
- `docs/research/speech-to-speech.md` — the talking-cursor upgrade path (Piper → conversational)
- `docs/research/web-agent-integration.md` — hand-off design for "have the web agent do it"

## Roadmap

**v1.1** ① hot interrupt grammar during TTS ② taskbar indicator with hard mute + "heard you" light ③ GNOME window-lookup extension + "which one?" disambiguation. **v2** speech-to-speech persona · eye-tracking (gaze moves, voice clicks) · web-agent errands · ghost cursor.

## Development

```bash
./.venv/bin/pytest        # fully headless — no mic, no display, no uinput needed
```

MIT license. Built with voice. Literally.
