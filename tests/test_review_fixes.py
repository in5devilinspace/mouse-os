"""Regression tests for the adversarial-review findings (2026-07-08).

Each test encodes a concrete failure scenario the review confirmed. They must
fail against the pre-fix code and pass after the fix.
"""
import io

import pytest

from mouseos import grammar, parser
from mouseos.engine import Engine
from mouseos.feedback import ConsoleSink
from mouseos.inputs.voice import MuteGate, VoskSource
from mouseos.pointer.dummy import DummyPointer
from mouseos.resolve.screen import Screen
from mouseos.resolve.windows import detect_screen_size
from mouseos.intents import (
    Wake, NeverMind, Quit, ConfirmQuit, Move, MoveTo, GoTo, Undo,
    WhereAmI, PointTo, ShowCameras,
)
from mouseos import cli


# ---- shared fakes ---------------------------------------------------------
class TogglingFeedback:
    """Mimics SpeechSink: speaking pauses+resumes the mute gate synchronously."""

    def __init__(self, gate):
        self.gate = gate
        self.spoken = []
        self.errors = []
        self.lines = []

    def say(self, key, **kw):
        self.spoken.append(key)
        self.gate.pause()
        self.gate.resume()

    def event(self, msg):
        self.lines.append(msg)

    def error(self, kind, detail=""):
        self.errors.append((kind, detail))


class FakeRec:
    def __init__(self, finals):
        self.finals = finals            # chunk bytes -> recognized text
        self.reset_count = 0
        self._last = ""

    def AcceptWaveform(self, chunk):
        if chunk in self.finals:
            self._last = self.finals[chunk]
            return True
        return False

    def Result(self):
        import json
        return json.dumps({"text": self._last})

    def Reset(self):
        self.reset_count += 1


# ---- 1. MuteGate: dirty + drain ------------------------------------------
def test_mutegate_marks_dirty_after_a_pause_resume_cycle():
    g = MuteGate()
    assert g.consume_dirty() is False
    g.pause()
    g.resume()
    assert g.consume_dirty() is True
    assert g.consume_dirty() is False        # consumed exactly once


def test_mutegate_dirty_only_after_full_unmute():
    g = MuteGate()
    g.pause()
    g.pause()
    g.resume()
    assert g.consume_dirty() is False        # still muted
    g.resume()
    assert g.consume_dirty() is True


def test_voice_pipeline_discards_tts_echo_buffered_during_speech():
    """The core safety invariant: the system must never act on its own voice."""
    gate = MuteGate()
    chunks = [b"c1", b"c2_echo", b"c3"]
    rec = FakeRec({b"c1": "mouse wake", b"c2_echo": "ready", b"c3": "click"})
    pointer = DummyPointer()
    fb = TogglingFeedback(gate)
    engine = Engine(pointer=pointer, screen=Screen(1920, 1200), feedback=fb,
                    clock=lambda: 0.0, launcher=lambda c: None)
    source = VoskSource("model", grammar.phrases(), mute_gate=gate,
                        recognizer=rec, chunks=chunks)

    cli.run_pipeline(source, engine, apps=("firefox",))

    # the echo chunk (captured while "ready" was spoken) must be dropped
    assert rec.reset_count >= 1
    assert "pardon" not in fb.spoken          # echo never became a bad utterance
    assert [op[0] for op in pointer.ops] == ["click"]


# ---- 2. [unk] handling ----------------------------------------------------
def test_voice_rejects_any_final_containing_unk():
    gate = MuteGate()
    chunks = [b"noise1", b"noise2", b"fused", b"clean"]
    rec = FakeRec({
        b"noise1": "[unk]",
        b"noise2": "[unk] [unk]",
        b"fused": "mouse [unk] wake",   # must NOT become "mouse wake"
        b"clean": "mouse wake",
    })
    source = VoskSource("model", grammar.phrases(), mute_gate=gate,
                        recognizer=rec, chunks=chunks)
    assert list(source) == ["mouse wake"]


# ---- 3. asleep is silent on unrecognized input ---------------------------
def test_asleep_engine_is_silent_on_none_intent():
    fb = ConsoleSink(quiet=True, stream=io.StringIO())
    eng = Engine(pointer=DummyPointer(), screen=Screen(800, 600), feedback=fb,
                 clock=lambda: 0.0, launcher=lambda c: None)
    eng.handle(None)                         # asleep + garbage
    assert not any("pardon" in l for l in fb.lines)


def test_awake_engine_says_pardon_on_none_intent():
    fb = ConsoleSink(quiet=True, stream=io.StringIO())
    eng = Engine(pointer=DummyPointer(), screen=Screen(800, 600), feedback=fb,
                 clock=lambda: 0.0, launcher=lambda c: None)
    eng.handle(Wake())
    eng.handle(None)
    assert any("pardon" in l for l in fb.lines)


# ---- 4. where-am-i uses a disjoint lexicon -------------------------------
def test_where_am_i_never_speaks_a_command_word():
    spoken = []

    class FB(ConsoleSink):
        def say(self, key, **kw):
            spoken.append(key)

    fb = FB(quiet=True, stream=io.StringIO())
    eng = Engine(pointer=DummyPointer(), screen=Screen(1920, 1200), feedback=fb,
                 clock=lambda: 0.0, launcher=lambda c: None)
    eng.handle(Wake())
    eng.handle(GoTo(region="top left"))
    spoken.clear()
    eng.handle(WhereAmI())
    command_words = grammar.command_words()
    for phrase in spoken:
        for word in phrase.split():
            assert word not in command_words, f"{word!r} is a command word"


# ---- 5. handler / launcher exceptions never strand the user --------------
def test_run_pipeline_survives_a_handler_exception():
    class BoomEngine:
        done = False

        def __init__(self):
            self.seen = []

        def handle(self, intent):
            self.seen.append(intent)
            if len(self.seen) == 1:
                raise RuntimeError("boom")

    class Src:
        repl = True

        def __iter__(self):
            yield "click"
            yield "mouse wake"

    fb_errors = []
    eng = BoomEngine()
    cli.run_pipeline(Src(), eng, apps=("firefox",),
                     on_error=lambda e: fb_errors.append(e))
    assert len(eng.seen) == 2                 # kept going after the boom
    assert fb_errors                          # and reported it


def test_show_cameras_survives_a_bad_launch_command():
    def boom(cmd):
        raise FileNotFoundError(cmd)

    spoken = []

    class FB(ConsoleSink):
        def say(self, key, **kw):
            spoken.append(key)

    fb = FB(quiet=True, stream=io.StringIO())
    eng = Engine(pointer=DummyPointer(), screen=Screen(800, 600), feedback=fb,
                 clock=lambda: 0.0, launcher=boom)
    eng.handle(Wake())
    eng.handle(ShowCameras())                 # must not raise
    assert "cant" in spoken


# ---- 6. no-op move preserves the undo slot -------------------------------
def test_clamped_noop_move_does_not_clobber_undo():
    pointer = DummyPointer()
    eng = Engine(pointer=pointer, screen=Screen(1920, 1200), feedback=ConsoleSink(
        quiet=True, stream=io.StringIO()), clock=lambda: 0.0,
        launcher=lambda c: None)
    eng.handle(Wake())
    eng.handle(GoTo(region="center"))         # undo slot -> initial center
    eng.handle(MoveTo(x=0, y=0))              # undo slot -> center(960,600); pos (0,0)
    eng.handle(Move(dx=-100, dy=0))           # clamped no-op at x=0
    eng.handle(Undo())                        # must restore (960,600), not (0,0)
    assert eng.position == (960, 600)


# ---- 7. never mind confirms ----------------------------------------------
def test_never_mind_speaks_a_confirmation():
    spoken = []

    class FB(ConsoleSink):
        def say(self, key, **kw):
            spoken.append(key)

    fb = FB(quiet=True, stream=io.StringIO())
    eng = Engine(pointer=DummyPointer(), screen=Screen(800, 600), feedback=fb,
                 clock=lambda: 0.0, launcher=lambda c: None)
    eng.handle(Quit())
    spoken.clear()
    eng.handle(NeverMind())
    assert spoken, "never mind gave no feedback"


# ---- 8. config app aliases reach the resolver ----------------------------
def test_point_to_resolves_config_alias_value():
    asked = []
    eng = Engine(pointer=DummyPointer(), screen=Screen(1920, 1200),
                 feedback=ConsoleSink(quiet=True, stream=io.StringIO()),
                 windows=lambda name: (asked.append(name) or (0, 0, 100, 100)),
                 config={"apps": {"files": "nautilus"}},
                 clock=lambda: 0.0, launcher=lambda c: None)
    eng.handle(Wake())
    eng.handle(PointTo(app="files"))
    assert asked == ["nautilus"]              # not the spoken alias "files"


# ---- 9. config steps drive move distances --------------------------------
def test_parser_uses_supplied_step_sizes():
    steps = {"": 50, "a little": 10, "a lot": 200}
    assert parser.parse("move up", steps=steps) == Move(dx=0, dy=-50)
    assert parser.parse("move down a lot", steps=steps) == Move(dx=0, dy=200)
    assert parser.parse("move left a little", steps=steps) == Move(dx=-10, dy=0)


# ---- 10. CLI default subcommand tolerates flags --------------------------
def test_normalize_argv_prepends_run_for_bare_flags():
    assert cli._normalize_argv([]) == ["run"]
    assert cli._normalize_argv(["--input", "repl"]) == ["run", "--input", "repl"]
    assert cli._normalize_argv(["doctor"]) == ["doctor"]
    assert cli._normalize_argv(["run", "--quiet"]) == ["run", "--quiet"]
    assert cli._normalize_argv(["--quiet"]) == ["run", "--quiet"]


# ---- 11. malformed --screen fails cleanly --------------------------------
def test_resolve_screen_rejects_garbage_cleanly():
    with pytest.raises(SystemExit):
        cli._resolve_screen({"screen": "auto"}, override="wide")


# ---- 12. doctor names a real Ubuntu package ------------------------------
def test_doctor_capture_hint_is_ubuntu_correct():
    import mouseos.doctor as d
    orig = d.shutil.which
    d.shutil.which = lambda name: None
    try:
        check = d.probe_capture()
    finally:
        d.shutil.which = orig
    assert "pipewire-utils" not in check.hint
    assert "pipewire-bin" in check.hint or "alsa-utils" in check.hint


# ---- 13. screen = primary monitor, no dead zones -------------------------
def _mode(w, h, current):
    props = {"is-current": {"type": "b", "data": True}} if current else {}
    return [f"{w}x{h}@60", w, h, 60.0, 1.0, [1.0], props]


_STATE = {
    "data": [
        7,
        [
            [["eDP-1", "SDC", "x", "0"], [_mode(2880, 1800, True)], {}],
            [["DP-2", "GSM", "ULTRAGEAR", "1"], [_mode(3440, 1440, True)], {}],
            [["DP-1", "ACR", "y", "2"], [_mode(1920, 1080, True)], {}],
        ],
        [
            [3440, 0, 1.5, 0, False, [["eDP-1", "SDC", "x", "0"]], {}],
            [0, 0, 1.0, 0, True, [["DP-2", "GSM", "ULTRAGEAR", "1"]], {}],
            [5360, 0, 1.0, 0, False, [["DP-1", "ACR", "y", "2"]], {}],
        ],
        {},
    ],
}


def test_detect_screen_size_returns_primary_monitor_not_bounding_box():
    # primary is DP-2 (index-4 flag True), 3440x1440 @ scale 1.0
    assert detect_screen_size(fetch=lambda: _STATE) == (3440, 1440)
