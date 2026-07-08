import pytest

from mouseos.engine import Engine
from mouseos.resolve.screen import Screen
from mouseos.intents import (
    Wake, Sleep, Quit, ConfirmQuit, NeverMind, Stop, Undo,
    Click, Hold, Release, Move, GoTo, Grid, PointTo,
    Scroll, WhereAmI, ShowCameras, MoveTo,
)


class FakePointer:
    def __init__(self):
        self.ops = []

    def move_to(self, x, y):
        self.ops.append(("move_to", x, y))

    def move_rel(self, dx, dy):
        self.ops.append(("move_rel", dx, dy))

    def click(self, button="left", double=False):
        self.ops.append(("click", button, double))

    def press(self, button="left"):
        self.ops.append(("press", button))

    def release(self, button="left"):
        self.ops.append(("release", button))

    def scroll(self, amount):
        self.ops.append(("scroll", amount))


class FakeFeedback:
    def __init__(self):
        self.spoken = []
        self.lines = []

    def say(self, key, **kw):
        self.spoken.append(key)

    def event(self, msg):
        self.lines.append(msg)

    def error(self, kind, detail=""):
        self.lines.append(f"{kind}:{detail}")


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def rig():
    pointer, fb, clock = FakePointer(), FakeFeedback(), FakeClock()
    launched = []
    eng = Engine(
        pointer=pointer,
        screen=Screen(1920, 1200),
        feedback=fb,
        clock=clock,
        launcher=lambda cmd: launched.append(cmd),
    )
    return eng, pointer, fb, clock, launched


def test_starts_asleep_and_ignores_actions(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Click())
    eng.handle(Move(dx=0, dy=-100))
    assert pointer.ops == []
    assert not eng.done


def test_wake_then_click(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    assert eng.awake
    assert "ready" in fb.spoken
    eng.handle(Click())
    assert ("click", "left", False) in pointer.ops


def test_sleep_reenters_asleep_and_releases_held_button(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(Hold())
    eng.handle(Sleep())
    assert ("release", "left") in pointer.ops
    eng.handle(Click())
    assert not any(op[0] == "click" for op in pointer.ops)


def test_quit_requires_confirmation_within_10s(rig):
    eng, pointer, fb, clock, _ = rig
    eng.handle(Wake())
    eng.handle(Quit())
    assert not eng.done
    clock.t += 11
    eng.handle(ConfirmQuit())     # expired — must NOT quit
    assert not eng.done
    eng.handle(Quit())
    clock.t += 3
    eng.handle(ConfirmQuit())
    assert eng.done


def test_never_mind_cancels_pending_quit(rig):
    eng, pointer, fb, clock, _ = rig
    eng.handle(Wake())
    eng.handle(Quit())
    eng.handle(NeverMind())
    eng.handle(ConfirmQuit())
    assert not eng.done


def test_quit_confirmable_while_asleep(rig):
    # safety: user must be able to quit without waking the pointer
    eng, pointer, fb, clock, _ = rig
    eng.handle(Quit())
    eng.handle(ConfirmQuit())
    assert eng.done


def test_move_updates_believed_position_with_clamp(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(GoTo(region="top left"))          # (5,5)
    eng.handle(Move(dx=-300, dy=0))              # clamped to x=0
    assert eng.position == (0, 5)
    # the relative move sent to the pointer is the clamped delta
    assert pointer.ops[-1] == ("move_rel", -5, 0)


def test_goto_and_grid_use_absolute_moves(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(GoTo(region="center"))
    assert ("move_to", 960, 600) in pointer.ops
    eng.handle(Grid(cell=1))
    assert ("move_to", 320, 200) in pointer.ops
    assert eng.position == (320, 200)


def test_undo_restores_previous_position(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(GoTo(region="center"))     # (960,600)
    eng.handle(Grid(cell=9))              # (1600,1000)
    eng.handle(Undo())
    assert eng.position == (960, 600)
    assert pointer.ops[-1] == ("move_to", 960, 600)


def test_undo_with_nothing_to_undo_says_cant(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(Undo())
    assert "cant" in fb.spoken


def test_stop_releases_hold_and_clears_pending_quit(rig):
    eng, pointer, fb, clock, _ = rig
    eng.handle(Wake())
    eng.handle(Hold())
    eng.handle(Quit())
    eng.handle(Stop())
    assert ("release", "left") in pointer.ops
    eng.handle(ConfirmQuit())
    assert not eng.done


def test_release_without_hold_warns(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(Release())
    assert "cant" in fb.spoken
    assert not any(op[0] == "release" for op in pointer.ops)


def test_scroll(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(Scroll(amount=-3))
    assert ("scroll", -3) in pointer.ops


def test_point_to_without_resolver_says_cant(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(PointTo(app="firefox"))
    assert "cant" in fb.spoken


def test_point_to_with_resolver_moves_to_window_center():
    pointer, fb = FakePointer(), FakeFeedback()
    eng = Engine(
        pointer=pointer, screen=Screen(1920, 1200), feedback=fb,
        windows=lambda name: (100, 100, 600, 400),  # x, y, w, h
        clock=lambda: 0.0, launcher=lambda cmd: None,
    )
    eng.handle(Wake())
    eng.handle(PointTo(app="firefox"))
    assert ("move_to", 400, 300) in pointer.ops


def test_show_cameras_launches_configured_command(rig):
    eng, pointer, fb, clock, launched = rig
    eng.handle(Wake())
    eng.handle(ShowCameras())
    assert launched, "camera command was not launched"


def test_where_am_i_speaks_nearest_region(rig):
    # Speaks a disjoint COMPASS word (not the command-grammar region name),
    # so the mic hearing the answer can't self-issue a movement command.
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(GoTo(region="top left"))
    eng.handle(WhereAmI())
    assert "northwest" in fb.spoken
    assert "top left" not in fb.spoken


def test_move_to_absolute_and_percent(rig):
    eng, pointer, fb, *_ = rig
    eng.handle(Wake())
    eng.handle(MoveTo(x=100, y=200, percent=False))
    assert eng.position == (100, 200)
    eng.handle(MoveTo(x=50, y=50, percent=True))
    assert eng.position == (960, 600)
