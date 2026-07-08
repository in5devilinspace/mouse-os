"""The weld: grammar and parser can never drift apart."""
import pytest

from mouseos import grammar, parser
from mouseos.intents import Intent


def test_every_grammar_phrase_parses_to_an_intent():
    apps = grammar.DEFAULT_APPS
    failures = []
    for phrase in grammar.phrases(apps):
        intent = parser.parse(phrase, apps=apps)
        if intent is None:
            failures.append(phrase)
    assert not failures, f"grammar phrases the parser rejects: {failures}"


def test_grammar_size_is_a_small_closed_vocabulary():
    n = len(grammar.phrases())
    assert 40 <= n <= 90, f"expected ~60 phrases, got {n}"


def test_asleep_phrases_are_a_subset_and_include_wake_and_quit():
    all_phrases = set(grammar.phrases())
    asleep = set(grammar.asleep_phrases())
    assert asleep <= all_phrases
    assert "mouse wake" in asleep
    assert "mouse quit" in asleep
    assert "confirm quit" in asleep


def test_hot_path_interrupts_are_in_the_grammar():
    ph = set(grammar.phrases())
    for hot in ("stop", "undo", "never mind"):
        assert hot in ph, f"roundtable amendment missing from grammar: {hot!r}"


def test_camera_launcher_utterances_present():
    ph = set(grammar.phrases())
    assert "show my cameras" in ph
    assert "open my cameras" in ph


def test_apps_expand_into_point_and_focus_phrases():
    ph = set(grammar.phrases(("firefox", "files")))
    assert "point to firefox" in ph
    assert "focus files" in ph
    assert "point to editor" not in ph


def test_command_words_cover_all_phrases():
    words = grammar.command_words()
    for phrase in grammar.phrases():
        for w in phrase.split():
            assert w in words, f"{w!r} from {phrase!r} missing in command_words()"
