# Mouse OS v1 — Design

Date: 2026-07-08. Status: approved for build (founder directive "create that for me" + judge-panel synthesis + roundtable amendments).

## What it is

A voice-controlled cursor agent for Ubuntu (GNOME Wayland). The user speaks — "point to firefox", "click", "scroll down" — and the real on-screen pointer obeys, then confirms out loud. Accessibility-first: built for people who cannot use their hands. Fully offline.

## How this design was made

1. A three-architect judge panel produced and scored competing designs; the winner (grammar-locked pipeline, corner-homing uinput) was synthesized with the runner-ups' best parts (spoken feedback + safety layer; Availability probes + abs-tablet device). Full record: workflow `mouse-os-design-panel`.
2. A BMad-persona roundtable (Mary/John/Winston/Sally) amended the plan — see `docs/roadmap/2026-07-07-feature-roundtable.md`.
3. Environment facts were verified on the target machine (GNOME Shell 50.1, Wayland, `/dev/uinput` root-only until setup, `spd-say` present, `pw-record`/`arecord` present, `uv` present, vosk+evdev install cleanly in a uv venv; PortAudio absent so sounddevice is OUT — mic capture is a `pw-record`/`arecord` subprocess).

## Architecture

One straight, synchronous pipeline; every seam is a small Protocol with one real and one test implementation:

```
InputSource (repl | vosk)  →  parser (utterance → frozen Intent)  →  Engine (FSM)
                                                                        │
                                    ┌───────────────┬──────────────────┤
                                    ▼               ▼                  ▼
                                resolve/        pointer/           feedback/
                             screen regions   uinput ladder     spd-say + console
                             grid, windows    abs → rel → dummy  (disjoint lexicon)
```

- `grammar.py` is the single source of truth: it emits BOTH the exhaustive vosk phrase list (~60 phrases, everything else absorbed by `[unk]`) AND the token tables the parser uses. A round-trip test welds them: every grammar phrase must parse to an Intent.
- `engine.py` is the only stateful object: ASLEEP / AWAKE / QUIT_PENDING states + `holding` flag + believed cursor position (clamped to screen). Starts ASLEEP (hot-mic safety). `mouse quit` requires `confirm quit` within 10 s.
- Pointer ladder probed at startup (`detect.py`): `uinput_abs` (tablet-style absolute device, QEMU-tablet recipe) → `uinput_rel` (relative device with corner-homing to erase drift) → `dummy` (records + prints `[DUMMY]`). Degradation is LOUD: spoken + printed, with the exact fix (`mouseos setup`).
- `resolve/screen.py`: monitor geometry via `busctl --json=short call org.gnome.Mutter.DisplayConfig ...` (JSON, not GVariant text); fallback `--screen WxH` flag/config. Provides named regions (center, corners, edges) and the 3×3 grid.
- `resolve/windows.py`: optional window-by-name via the "Window Calls" GNOME extension D-Bus if present; absent → spoken hint, grid still covers every pixel.
- `feedback.py`: SpeechSink shells `spd-say`; ConsoleSink always logs. Error taxonomy: ParseError ("pardon?"), ResolveError, BackendError — every failure has a spoken word and a printed line.

## Roundtable amendments (binding)

1. **`stop`, `undo`, `never mind` are in the v1 grammar.** `stop` releases any held button and clears pending state; `undo` restores the believed position from before the last movement (single slot — a full undo stack stays out); `never mind` cancels QUIT_PENDING / acknowledges quietly.
2. **Sally's TTS contract:** spoken feedback ≤2 words wherever possible; the mic is paused only while TTS actually plays and re-arms ≤200 ms after; listening/deaf state always visible (REPL prompt/status line in v1, tray light in v1.1). Long sentences don't ship until interruptible (v1.1 hot interrupt grammar).
3. **`show my cameras` / `open my cameras`** is one grammar utterance that launches the user's Reolink view via a configurable command (default: browser to go2rtc grid URL; see `docs/research/reolink-cameras-on-ubuntu.md`). Zero camera code inside the shell.

## v1 grammar (families)

`mouse wake` · `mouse sleep` · `mouse quit`/`confirm quit` · `point to <app>` / `focus <app>` (config aliases) · `click`/`double click`/`right click`/`middle click` · `hold`/`release` · `move up|down|left|right [a little|a lot]` · `go to center|top left|top right|bottom left|bottom right|top|bottom|left edge|right edge` · `grid one…nine` · `scroll up|down [a lot]` · `stop` · `undo` · `never mind` · `list windows` · `where am i` · `show my cameras`/`open my cameras`. REPL-only: `move to <x> <y>`, `move to <x>% <y>%`, `status`, `help`.

Design rules: hot-path commands are prefix-free 1–2 words; only state commands carry the `mouse` prefix; all slots finite; every word exists in the vosk small-model vocabulary; ASLEEP tightens the recognizer grammar to wake/quit only. The feedback lexicon shares no word with any command phrase (defense-in-depth against self-triggering), enforced by test.

## Packaging & ops

- `pyproject.toml`: package `mouseos`, `requires-python >=3.11`; core dep `evdev` only; extra `[voice]` = `vosk`; extra `[test]` = `pytest`. Managed with `uv`.
- CLI: `mouseos run [--input auto|repl|voice] [--pointer auto|abs|rel|dummy] [--quiet]`, `mouseos doctor` (Availability table, one-line fixes, exit 0 iff cursor can move), `mouseos setup` (prints `scripts/setup-uinput.sh` instructions — NEVER auto-runs sudo), `mouseos setup-model` (downloads vosk small-en model to `~/.cache/mouseos`), `mouseos say "<utterance>"` (one-shot inject), `mouseos grammar` (prints phrases).
- Config: `~/.config/mouseos/config.toml` — app aliases, step sizes, camera command, screen fallback, start_asleep.
- Tests: grammar↔parser weld (property: every phrase parses), engine FSM transitions, believed-position clamping, hold/release pairing, undo, feedback-lexicon disjointness, grid math, golden REPL transcript through dummy backend. All headless.

## Explicitly OUT of v1 (roadmap)

Hot interrupt grammar during TTS (v1.1 #1) · tray AppIndicator with hard mute + heard-light (v1.1 #2) · GNOME window-lookup extension + disambiguation dialogue (v1.1 #3) · eye tracking, ghost cursor, glide, speech-to-speech persona (Piper/ElevenLabs — see `docs/research/speech-to-speech.md`), web-agent hand-off (browser-use — see `docs/research/web-agent-integration.md`), X11 backend, systemd unit, dynamic window vocabulary.

## Risks

- uinput permissions: until the user runs `scripts/setup-uinput.sh` (sudo), only dummy mode works — mitigated by honest doctor + spoken notice.
- Vosk model download (~40 MB) needed once for voice mode; text REPL works without it.
- GNOME hot-corner can trip during corner-homing (rel backend) — home to top-left with a post-home nudge; abs backend avoids it entirely.
- Believed-position drift if the human moves the physical mouse — any absolute command (grid/region/point) re-grounds it.
