import pytest

from mouseos.parser import parse
from mouseos.intents import (
    Wake, Sleep, Quit, ConfirmQuit, NeverMind, Stop, Undo,
    Click, Hold, Release, Move, GoTo, Grid, PointTo, Focus,
    Scroll, ListWindows, WhereAmI, ShowCameras, MoveTo, Status, Help,
)


def test_state_commands():
    assert parse("mouse wake") == Wake()
    assert parse("mouse sleep") == Sleep()
    assert parse("mouse quit") == Quit()
    assert parse("confirm quit") == ConfirmQuit()
    assert parse("never mind") == NeverMind()


def test_interrupts():
    assert parse("stop") == Stop()
    assert parse("undo") == Undo()


def test_clicks():
    assert parse("click") == Click(button="left", double=False)
    assert parse("double click") == Click(button="left", double=True)
    assert parse("right click") == Click(button="right", double=False)
    assert parse("middle click") == Click(button="middle", double=False)


def test_hold_release():
    assert parse("hold") == Hold()
    assert parse("release") == Release()


def test_moves_default_and_magnitudes():
    assert parse("move up") == Move(dx=0, dy=-100)
    assert parse("move down a little") == Move(dx=0, dy=25)
    assert parse("move left a lot") == Move(dx=-300, dy=0)
    assert parse("move right") == Move(dx=100, dy=0)


def test_go_to_regions():
    assert parse("go to center") == GoTo(region="center")
    assert parse("go to top left") == GoTo(region="top left")
    assert parse("go to bottom right") == GoTo(region="bottom right")
    assert parse("go to left edge") == GoTo(region="left edge")
    assert parse("go to top") == GoTo(region="top")


def test_grid_cells():
    assert parse("grid one") == Grid(cell=1)
    assert parse("grid nine") == Grid(cell=9)
    assert parse("grid ten") is None


def test_point_and_focus_need_known_app():
    apps = ("firefox", "files")
    assert parse("point to firefox", apps=apps) == PointTo(app="firefox")
    assert parse("focus files", apps=apps) == Focus(app="files")
    assert parse("point to blender", apps=apps) is None


def test_scroll():
    assert parse("scroll up") == Scroll(amount=3)
    assert parse("scroll down") == Scroll(amount=-3)
    assert parse("scroll down a lot") == Scroll(amount=-10)


def test_info_and_cameras():
    assert parse("list windows") == ListWindows()
    assert parse("where am i") == WhereAmI()
    assert parse("show my cameras") == ShowCameras()
    assert parse("open my cameras") == ShowCameras()


def test_unknown_is_none():
    assert parse("make me a sandwich") is None
    assert parse("") is None
    assert parse("   ") is None


def test_case_and_whitespace_insensitive():
    assert parse("  Mouse   WAKE ") == Wake()


def test_repl_only_commands_gated():
    assert parse("move to 100 200", repl=True) == MoveTo(x=100, y=200, percent=False)
    assert parse("move to 50% 50%", repl=True) == MoveTo(x=50, y=50, percent=True)
    assert parse("status", repl=True) == Status()
    assert parse("help", repl=True) == Help()
    # not available to the voice path
    assert parse("move to 100 200") is None
    assert parse("status") is None
