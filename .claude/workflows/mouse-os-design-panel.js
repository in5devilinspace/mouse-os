export const meta = {
  name: 'mouse-os-design-panel',
  description: 'Judge panel: 3 independent architectures for a voice-controlled cursor agent on GNOME Wayland',
  phases: [
    { title: 'Design', detail: '3 architects, different priorities' },
    { title: 'Judge', detail: 'score and synthesize winning design' },
  ],
}

const CONTEXT = `
PRODUCT: "Mouse OS" — a voice-controlled mouse-cursor agent. The user speaks ("point to Firefox",
"click", "scroll down") and the real on-screen pointer obeys. Accessibility-first: built for people
who cannot use their hands. Future modes: eye-tracking (gaze = cursor), a second "agent ghost cursor"
overlay you can command independently of the physical mouse.

HARD ENVIRONMENT CONSTRAINTS (verified on the target machine):
- Ubuntu, GNOME on **Wayland** (XDG_CURRENT_DESKTOP=ubuntu:GNOME). xdotool/wmctrl/pyautogui CANNOT move the cursor here.
- /dev/uinput exists but is root-only (crw------- root). The user CAN run a one-time sudo setup script
  (udev rule / group access), but the agent building this cannot sudo. So: uinput virtual-input backend
  is viable AFTER a documented one-time setup.
- No swaymsg/hyprctl/ydotool/wtype installed. gdbus and busctl ARE available.
- GNOME Wayland window enumeration options: (a) "Window Calls" GNOME Shell extension exposing List/Activate
  over D-Bus, (b) org.gnome.Shell.Introspect (restricted), (c) org.gnome.Mutter.DisplayConfig for monitor
  geometry, (d) fallback: percent/relative movement without window lookup.
- Python 3.14 available; vosk 0.3.45 on PyPI (offline STT, supports grammar-constrained recognition);
  working microphones (DMIC + USB).
- The build machine is headless for testing purposes: no real mic/cursor can be exercised in CI, so the
  design MUST include a text-command REPL input mode and a dummy/logging pointer backend, with the core
  (parser, intent model, resolver) fully unit-testable with pytest.
- Must ship TODAY as a working v1 (pip-installable Python package + CLI), with a clean roadmap for
  eye-tracking and overlay cursor. Git repo + GitHub + Linear issues are part of the deliverable.

DESIGN QUESTIONS TO ANSWER:
1. Package/module architecture (isolation: STT input, intent parsing, target resolution, pointer backends).
2. Pointer backend strategy (uinput absolute vs relative, X11 portability, dummy for tests, auto-detection).
3. Window/target resolution strategy on GNOME Wayland with graceful degradation.
4. Voice pipeline (vosk grammar mode? wake word? always-listening safety — "mouse sleep/wake"?).
5. Command grammar (the exact v1 utterance set).
6. Error handling & user feedback (spoken? printed? notification?).
7. Testing strategy.
8. v1 scope vs roadmap (YAGNI ruthlessly — v1 must be finishable today).
`

const DESIGN_SCHEMA = {
  type: 'object',
  required: ['approach_name', 'philosophy', 'architecture', 'components', 'pointer_backends', 'window_resolution', 'voice_pipeline', 'command_grammar', 'error_feedback', 'testing', 'v1_scope', 'roadmap', 'risks'],
  properties: {
    approach_name: { type: 'string' },
    philosophy: { type: 'string' },
    architecture: { type: 'string', description: 'prose overview of module layout and data flow' },
    components: { type: 'array', items: { type: 'object', required: ['name', 'purpose', 'interface'], properties: { name: { type: 'string' }, purpose: { type: 'string' }, interface: { type: 'string' } } } },
    pointer_backends: { type: 'string' },
    window_resolution: { type: 'string' },
    voice_pipeline: { type: 'string' },
    command_grammar: { type: 'array', items: { type: 'string' } },
    error_feedback: { type: 'string' },
    testing: { type: 'string' },
    v1_scope: { type: 'array', items: { type: 'string' } },
    roadmap: { type: 'array', items: { type: 'string' } },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

const ANGLES = [
  { key: 'accessibility-first', prompt: 'You are an accessibility engineer who has shipped assistive tech (think Talon, Dragon, GNOME accessibility stack). Design for a user who CANNOT use their hands at all: zero-hands bootstrapping, always-listening safety, misrecognition recovery, fatigue. Favor reliability of a small command set over breadth.' },
  { key: 'minimal-pragmatist', prompt: 'You are a pragmatic senior engineer who ships v1s in a day. Ruthless YAGNI: the smallest architecture that genuinely works on GNOME Wayland today, is honest about what cannot work without the sudo setup, and leaves clean seams for later. Kill every speculative abstraction.' },
  { key: 'platform-architect', prompt: 'You are a platform architect designing input systems (think libinput/compositor experience). Design the backend/resolver abstraction so uinput-absolute, uinput-relative, X11, dummy, and future eye-tracking/overlay modes are all first-class drivers behind one interface. Get the interfaces right; keep v1 implementation thin.' },
]

phase('Design')
const designs = (await parallel(ANGLES.map(a => () =>
  agent(`${a.prompt}\n\n${CONTEXT}\n\nProduce a complete design answering all 8 design questions. Be concrete: real module names, real D-Bus interface names, real vosk API usage, exact utterance grammar. Return via the structured schema.`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA })
))).filter(Boolean)

phase('Judge')
const JUDGE_SCHEMA = {
  type: 'object',
  required: ['winner', 'scores', 'rationale', 'synthesis'],
  properties: {
    winner: { type: 'string' },
    scores: { type: 'array', items: { type: 'object', required: ['approach', 'score', 'strengths', 'weaknesses'], properties: { approach: { type: 'string' }, score: { type: 'number' }, strengths: { type: 'string' }, weaknesses: { type: 'string' } } } },
    rationale: { type: 'string' },
    synthesis: DESIGN_SCHEMA,
  },
}
const judged = await agent(`You are the chief architect making the final call on a design for this product:\n${CONTEXT}\n\nHere are ${designs.length} competing designs:\n\n${designs.map((d, i) => `=== DESIGN ${i + 1}: ${d.approach_name} ===\n${JSON.stringify(d, null, 1)}`).join('\n\n')}\n\nScore each 1-10 on: works-today-on-GNOME-Wayland, accessibility soundness, testability, YAGNI discipline, clean seams for eye-tracking/overlay roadmap. Pick a winner, then produce a SYNTHESIZED final design: the winner's skeleton, grafting in the best specific ideas from the others (name which idea came from which design in the architecture prose). The synthesis must be finishable in one day by one engineer and every v1_scope item must be concretely implementable with the stated constraints (no sudo during build, headless tests).`,
  { label: 'judge:synthesize', phase: 'Judge', schema: JUDGE_SCHEMA, effort: 'high' })

return { designs_considered: designs.map(d => d.approach_name), judged }
