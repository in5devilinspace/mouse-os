# Adversarial review → fixes (2026-07-08)

A 5-lens adversarial review workflow (correctness · pointer/uinput · voice/audio · accessibility contract · integration) with per-finding skeptic verification ran over mouseos v1. It confirmed several defects that broke the exact safety invariants the feature roundtable insisted on. All are now fixed under TDD — regression tests in `tests/test_review_fixes.py`, suite at 88 passing.

## Fixed

**Voice safety (the load-bearing ones)**
- **MuteGate was architecturally inert.** The pipeline is single-threaded, so `spd-say -w`'s pause→speak→resume ran entirely before the recognizer read again — the gate was never observed muted, and TTS audio buffered in the capture pipe was fed to Vosk. The system could hear itself say "stopped"/"held" and self-issue `stop`/`hold`. Fix: `MuteGate` now raises a `dirty` flag on each full unmute; the source consumes it, **resets the recognizer and drains the capture pipe** before reading fresh audio. (`voice.py`, `feedback.py`)
- **Noise → "pardon?" while ASLEEP.** A multi-`[unk]` final ("[unk] [unk]") slipped the exact-string guard, became `""`, and made the idle hot-mic device chatter. **Fix: any final containing an `[unk]` token is rejected wholesale** — which also closes the "mouse [unk] wake" fusion path that could wake the machine from noise. (`voice.py`)
- **`where am i` spoke command words.** It said "top left" / "center" — words in the movement grammar — which the mic could hear back and act on. **Fix: a disjoint compass lexicon** ("northwest", "north", "middle" …) for spoken orientation; the exact region + coordinates still print to the console. (`engine.py`)

**Engine safety**
- Unrecognized input while ASLEEP is now silent (console-only), never spoken.
- A bad `show my cameras` launch command, or any exception in a handler, no longer crashes the agent and strands the hands-free user — it's caught, spoken as "can't", and the loop keeps listening. (`engine.py`, `cli.py`)
- A clamped no-op `move` no longer clobbers the single undo slot.
- `never mind` now speaks a confirmation ("okay").

**Config actually wired**
- `[apps]` alias *values* now reach the window resolver ("point to files" → looks up `nautilus`, not "files").
- `[steps]` config now drives move distances (parser was ignoring it).

**CLI / platform robustness**
- `mouseos --input repl` (a flag with no explicit `run`) works — the default-subcommand handling was broken by any flag.
- A malformed `--screen` value fails with a clear message instead of a traceback.
- Voice mode with no capture tool, or whose mic/pipe dies mid-session, now reports it (spoken + console) instead of exiting silently with status 0.
- `doctor`'s microphone hint names real Ubuntu packages (`pipewire-bin` / `alsa-utils`), not a Fedora one.
- **Screen = the primary monitor, not the multi-monitor bounding box.** On the 3-monitor dev machine the box was 7280×1440 with dead zones between differently-sized monitors where grid cells could never land; v1 now targets the primary monitor (3440×1440 here). Multi-monitor targeting is a roadmap item.

## Deferred (documented, not fixed in this pass)
- **REL-backend pointer acceleration**: on the relative fallback, libinput pointer acceleration means corner-homing deltas aren't 1:1 pixels, so absolute positioning drifts. The `uinput-abs` tablet backend (preferred, and what this machine will use after setup) is exact; the rel backend is a degraded fallback. Tracked for v1.1.
- **GNOME hot-corner during corner-homing** (rel backend only): mitigated by a post-sweep dodge, not eliminated. Same v1.1 track.
