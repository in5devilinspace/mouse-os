# Mouse OS — Linear issues (ready to sync)

Project: **Mouse OS** · source of truth for priorities: `docs/roadmap/2026-07-07-feature-roundtable.md`
Status: prepared 2026-07-08; sync to Linear via MCP once authorized (or import manually).

---

## 1. Hot interrupt grammar during TTS — kill the deaf window · `v1.1` `priority:urgent`
The v1 mic pauses during spd-say playback, so "stop" cannot be heard while the system talks — Sally ruled this an accessibility bug accepted only for v1. Winston's fix (from the roundtable): because the feedback lexicon is disjoint from the command lexicon, keep the mic hot during TTS on a tiny interrupt-only grammar ("stop", "undo", "never mind") — no echo cancellation needed. Acceptance: "stop" spoken mid-TTS halts speech and any in-flight action within 200 ms; regression test with a fake recognizer.

## 2. Taskbar AppIndicator: hard mute, "heard you" light, settings · `v1.1` `priority:high`
AyatanaAppIndicator3 tray icon (verified available on the target Ubuntu): listening/deaf/asleep state at a glance, a hard mute toggle the user can trust, and a settings entry (pointer speed, steps, apps, camera command). John: "a user who can't verify the mic is dead won't keep the product installed." Runs as a separate process on system python3 (gi), talks to the daemon over a local socket.

## 3. Window-by-name + "which one?" disambiguation dialogue · `v1.1` `priority:high`
Ship/require the GNOME "Window Calls" extension path (already integrated in `resolve/windows.py`), add a yes/no + ordinal follow-up grammar so "point to firefox" with two Firefox windows becomes a spoken dialogue. Mary: this dialogue loop is the wedge Talon structurally can't copy. Depends on #1 (long sentences must be interruptible before they ship — Sally's contract).

## 4. Pointer speed profiles, glide, and pointer lock · `v1.1` `priority:medium`
Founder asks: adjustable cursor speed, "slowly go over to it" (glide — animated movement instead of teleport), and "lock the mouse pointer" (ignore physical mouse / freeze position until unlocked). Glide must be preemptible by "stop" mid-flight (intent bus priority — Winston's design).

## 5. Camera wall one-command setup (Reolink via go2rtc) · `v1.x` `priority:medium`
`mouseos setup-cameras`: guide through Reolink Home Hub RTSP enablement, map channels via GetChannelStatus, install go2rtc to ~/.local/bin, write the 4-stream YAML, systemd --user unit, and point the existing "show my cameras" launcher at the grid URL. Everything verified in `docs/research/reolink-cameras-on-ubuntu.md` (hub firmware ≥ Sept 2025 required for stable sub-stream RTSP).

## 6. Speech-to-speech cursor persona · `v2` `priority:low` `parked`
ElevenLabs-style live conversation with the pointer. Parked by unanimous roundtable ruling until barge-in is real (#1 first). Upgrade path researched and verified: Piper TTS (pip-installable, tested on the target machine) → conversational stack; see `docs/research/speech-to-speech.md`. Sally's veto: no uninterruptible speech, ever.

## 7. Eye-tracking mode: gaze moves, voice clicks · `v2` `priority:low` `parked`
Webcam gaze estimation as a position source publishing to the same intent bus (Winston: eye-tracking is a position source, not a backend). Hands stay behind your back.

## 8. Web-agent hand-off · `v2` `priority:low` `parked`
"Have the web agent order it" → delegate to a browser-use task, narrate progress via TTS. NOTE from adversarial fact-check: browser-use's install is NOT purely user-space and the API surface claim was refuted — re-verify current API before building. See `docs/research/web-agent-integration.md`.

## 9. Ghost cursor (second, agent-owned pointer) · `v2` `priority:low` `parked`
A visually distinct overlay cursor the agent moves while the physical mouse stays free — "you have a mouse, and then you have another one." Needs a GNOME Shell extension for the overlay; named-cursor design kept additive in the pointer plane.

## 10. Landing-page expectations pass · `v1` `priority:medium`
Mary: "correct the overpromise in writing now, before user zero becomes churn zero." Sally: "our first users will find it from a hospital bed — we do not get to overpromise." Review docs/index.html copy: keep the hype, mark v2 items clearly as roadmap, add an honest "what works today" section.

## 11. Promo video (Fal AI / HyperFrames) · `ops` `blocked`
Founder wants a hype/YouTube video. Blocked: waiting on the Fal AI API key (founder to provide) or HyperFrames MCP authorization.
