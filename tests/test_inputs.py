import io
import json

from mouseos.inputs.repl import ReplSource
from mouseos.inputs.voice import build_grammar_json, MuteGate


def test_repl_yields_normalized_utterances():
    stream = io.StringIO("Mouse Wake\n\n  CLICK  \nmouse quit\nconfirm quit\n")
    src = ReplSource(stream=stream, echo=False)
    assert list(src) == ["mouse wake", "click", "mouse quit", "confirm quit"]


def test_repl_is_marked_as_repl_for_parser_gating():
    assert ReplSource(stream=io.StringIO(""), echo=False).repl is True


def test_build_grammar_json_includes_unk_token():
    j = build_grammar_json(["mouse wake", "click"])
    data = json.loads(j)
    assert "mouse wake" in data
    assert "click" in data
    assert "[unk]" in data


def test_mute_gate_pause_resume():
    gate = MuteGate()
    assert not gate.muted
    gate.pause()
    assert gate.muted
    gate.resume()
    assert not gate.muted


def test_mute_gate_nested_pauses():
    gate = MuteGate()
    gate.pause()
    gate.pause()
    gate.resume()
    assert gate.muted          # still one pause outstanding
    gate.resume()
    assert not gate.muted
