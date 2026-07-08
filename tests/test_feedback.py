"""Defense-in-depth: nothing the system says can be heard as a command."""
from mouseos import grammar, feedback


def test_feedback_lexicon_disjoint_from_command_words():
    command_words = set(grammar.command_words())
    spoken_words = set()
    for utterance in feedback.PHRASES.values():
        spoken_words.update(utterance.lower().replace("?", "").replace(".", "").split())
    overlap = spoken_words & command_words
    assert not overlap, f"feedback words that are also command words: {overlap}"


def test_feedback_phrases_are_at_most_two_words():
    # Sally's contract: <=2 words per spoken confirmation.
    long = {k: v for k, v in feedback.PHRASES.items() if len(v.split()) > 2}
    assert not long, f"feedback phrases exceeding two words: {long}"


def test_console_sink_records_lines():
    sink = feedback.ConsoleSink(quiet=True)
    sink.event("wake")
    sink.error("parse", "make me a sandwich")
    assert any("wake" in line for line in sink.lines)
    assert any("sandwich" in line for line in sink.lines)
