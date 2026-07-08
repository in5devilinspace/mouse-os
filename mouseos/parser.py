"""utterance string -> frozen Intent (or None). No state, no side effects."""
import re

from . import grammar
from .intents import (
    Wake, Sleep, Quit, ConfirmQuit, NeverMind, Stop, Undo,
    Click, Hold, Release, Move, GoTo, Grid, PointTo, Focus,
    Scroll, ListWindows, WhereAmI, ShowCameras, MoveTo, Status, Help,
)

_STEPS = {"": 100, "a little": 25, "a lot": 300}
_DIR_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
_GRID_CELLS = {w: i + 1 for i, w in enumerate(
    ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine"))}
_REGIONS = {
    "center", "top left", "top right", "bottom left", "bottom right",
    "top", "bottom", "left edge", "right edge",
}

_FIXED = {
    "mouse wake": Wake(),
    "mouse sleep": Sleep(),
    "mouse quit": Quit(),
    "confirm quit": ConfirmQuit(),
    "never mind": NeverMind(),
    "stop": Stop(),
    "undo": Undo(),
    "click": Click(button="left", double=False),
    "double click": Click(button="left", double=True),
    "right click": Click(button="right", double=False),
    "middle click": Click(button="middle", double=False),
    "hold": Hold(),
    "release": Release(),
    "scroll up": Scroll(amount=3),
    "scroll down": Scroll(amount=-3),
    "scroll up a lot": Scroll(amount=10),
    "scroll down a lot": Scroll(amount=-10),
    "list windows": ListWindows(),
    "where am i": WhereAmI(),
    "show my cameras": ShowCameras(),
    "open my cameras": ShowCameras(),
}

_MOVE_TO_RE = re.compile(r"^move to (\d+)(%?) (\d+)(%?)$")


def parse(utterance, apps=None, repl=False, steps=None):
    text = " ".join((utterance or "").lower().split())
    if not text:
        return None
    apps = tuple(apps) if apps is not None else grammar.DEFAULT_APPS
    steps = steps if steps is not None else _STEPS

    if text in _FIXED:
        return _FIXED[text]

    if text.startswith("move "):
        rest = text[len("move "):]
        for direction, (vx, vy) in _DIR_VECTORS.items():
            if rest == direction or rest.startswith(direction + " "):
                magnitude = rest[len(direction):].strip()
                if magnitude in steps:
                    step = steps[magnitude]
                    return Move(dx=vx * step, dy=vy * step)
        if repl:
            m = _MOVE_TO_RE.match(text)
            if m and m.group(2) == m.group(4):
                return MoveTo(x=int(m.group(1)), y=int(m.group(3)),
                              percent=m.group(2) == "%")
        return None

    if text.startswith("go to "):
        region = text[len("go to "):]
        if region in _REGIONS:
            return GoTo(region=region)
        return None

    if text.startswith("grid "):
        cell = _GRID_CELLS.get(text[len("grid "):])
        return Grid(cell=cell) if cell else None

    if text.startswith("point to "):
        app = text[len("point to "):]
        return PointTo(app=app) if app in apps else None

    if text.startswith("focus "):
        app = text[len("focus "):]
        return Focus(app=app) if app in apps else None

    if repl:
        if text == "status":
            return Status()
        if text == "help":
            return Help()

    return None
