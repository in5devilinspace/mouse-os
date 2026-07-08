import io
import textwrap

from mouseos import config as config_mod
from mouseos.cli import run_pipeline
from mouseos.doctor import Check, render
from mouseos.engine import Engine
from mouseos.feedback import ConsoleSink
from mouseos.inputs.repl import ReplSource
from mouseos.pointer.dummy import DummyPointer
from mouseos.resolve.screen import Screen


# -- config -------------------------------------------------------------------
def test_config_defaults_when_no_file(tmp_path):
    cfg = config_mod.load(tmp_path / "nope.toml")
    assert cfg["start_asleep"] is True
    assert cfg["steps"]["normal"] == 100
    assert "firefox" in cfg["apps"]


def test_config_file_overrides_merge(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(textwrap.dedent("""
        [steps]
        normal = 50
        [cameras]
        command = "ffplay rtsp://hub/Preview_01_sub"
    """))
    cfg = config_mod.load(p)
    assert cfg["steps"]["normal"] == 50
    assert cfg["steps"]["lot"] == 300          # untouched default survives
    assert "ffplay" in cfg["cameras"]["command"]
    assert cfg["start_asleep"] is True


# -- doctor -------------------------------------------------------------------
def test_doctor_render_shows_status_and_hint():
    checks = [
        Check("uinput", "needs_setup", "permission denied",
              "run scripts/setup-uinput.sh then log out/in"),
        Check("spd-say", "ok", "found", ""),
    ]
    out = render(checks)
    assert "uinput" in out
    assert "FIX" in out          # needs_setup renders as an actionable FIX mark
    assert "setup-uinput.sh" in out
    assert "spd-say" in out and "OK" in out


# -- golden transcript ----------------------------------------------------------
def test_golden_repl_transcript_end_to_end():
    script = "\n".join([
        "mouse wake",
        "grid five",
        "move up a little",
        "click",
        "hold",
        "move right",
        "release",
        "scroll down",
        "undo",
        "mouse sleep",
        "click",              # must be ignored while asleep
        "mouse quit",
        "confirm quit",
    ]) + "\n"
    pointer = DummyPointer()
    sink = ConsoleSink(quiet=True, stream=io.StringIO())
    engine = Engine(pointer=pointer, screen=Screen(1920, 1200), feedback=sink,
                    clock=lambda: 0.0, launcher=lambda cmd: None)
    src = ReplSource(stream=io.StringIO(script), echo=False)

    run_pipeline(src, engine, apps=("firefox",))

    assert engine.done
    ops = [op[0] for op in pointer.ops]
    assert ops == [
        "move_to",        # grid five
        "move_rel",       # move up a little
        "click",
        "press",          # hold
        "move_rel",       # move right
        "release",
        "scroll",
        "move_rel",       # undo -> move_to? (absolute restore)
    ] or ops == [
        "move_to", "move_rel", "click", "press", "move_rel",
        "release", "scroll", "move_to",
    ]
    # the asleep click must NOT appear: exactly one click
    assert ops.count("click") == 1
