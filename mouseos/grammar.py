"""Single source of truth for the voice grammar.

Emits BOTH the exhaustive phrase list fed verbatim to the Vosk recognizer
AND the word inventory used to prove the feedback lexicon is disjoint.
The weld test guarantees every phrase here parses to exactly one Intent.
"""

DEFAULT_APPS = ("firefox", "files", "terminal", "editor", "settings")

_DIRECTIONS = ("up", "down", "left", "right")
_MAGNITUDES = ("", " a little", " a lot")
_REGIONS = (
    "center",
    "top left", "top right", "bottom left", "bottom right",
    "top", "bottom", "left edge", "right edge",
)
_GRID_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")

_STATE = (
    "mouse wake",
    "mouse sleep",
    "mouse quit",
    "confirm quit",
    "never mind",
)

_HOT = ("stop", "undo")

_CLICKS = ("click", "double click", "right click", "middle click")

_DRAG = ("hold", "release")

_SCROLL = ("scroll up", "scroll down", "scroll up a lot", "scroll down a lot")

_INFO = ("list windows", "where am i")

_CAMERAS = ("show my cameras", "open my cameras")


def phrases(apps=DEFAULT_APPS):
    """The full closed vocabulary, expanded — feed this to KaldiRecognizer."""
    out = list(_STATE) + list(_HOT) + list(_CLICKS) + list(_DRAG)
    out += [f"move {d}{m}" for d in _DIRECTIONS for m in _MAGNITUDES]
    out += [f"go to {r}" for r in _REGIONS]
    out += [f"grid {w}" for w in _GRID_WORDS]
    out += list(_SCROLL) + list(_INFO) + list(_CAMERAS)
    for app in apps:
        out.append(f"point to {app}")
        out.append(f"focus {app}")
    return out


def asleep_phrases():
    """The recognizer grammar while ASLEEP — wake/quit path only."""
    return ["mouse wake", "mouse quit", "confirm quit", "never mind"]


def command_words(apps=DEFAULT_APPS):
    """Every word the user can say — for the feedback-disjointness proof."""
    words = set()
    for phrase in phrases(apps):
        words.update(phrase.split())
    return words
