import pytest
from evdev import ecodes

from mouseos.resolve.screen import Screen
from mouseos.pointer.dummy import DummyPointer
from mouseos.pointer.uinput_abs import AbsPointer
from mouseos.pointer.uinput_rel import RelPointer
from mouseos.pointer.detect import pick_backend


class FakeUInput:
    """Captures the evdev event stream a real UInput would emit."""

    def __init__(self):
        self.events = []
        self.synced = 0

    def write(self, etype, code, value):
        self.events.append((etype, code, value))

    def syn(self):
        self.synced += 1
        self.events.append(("SYN",))


@pytest.fixture
def screen():
    return Screen(1920, 1200)


# -- dummy -----------------------------------------------------------------
def test_dummy_records_everything(screen):
    d = DummyPointer()
    d.move_to(10, 20)
    d.move_rel(5, -5)
    d.click(button="right", double=False)
    d.press("left")
    d.release("left")
    d.scroll(-3)
    kinds = [op[0] for op in d.ops]
    assert kinds == ["move_to", "move_rel", "click", "press", "release", "scroll"]
    assert d.name == "dummy"


# -- absolute (tablet-style) --------------------------------------------------
def test_abs_move_to_writes_abs_events(screen):
    fake = FakeUInput()
    p = AbsPointer(screen, uinput_factory=lambda caps, name: fake)
    p.move_to(100, 200)
    assert (ecodes.EV_ABS, ecodes.ABS_X, 100) in fake.events
    assert (ecodes.EV_ABS, ecodes.ABS_Y, 200) in fake.events
    assert fake.synced >= 1


def test_abs_click_press_release_sequence(screen):
    fake = FakeUInput()
    p = AbsPointer(screen, uinput_factory=lambda caps, name: fake)
    p.click(button="left", double=False)
    presses = [e for e in fake.events if e[:2] == (ecodes.EV_KEY, ecodes.BTN_LEFT)]
    assert [v for *_, v in presses] == [1, 0]


def test_abs_double_click_emits_two_pairs(screen):
    fake = FakeUInput()
    p = AbsPointer(screen, uinput_factory=lambda caps, name: fake)
    p.click(button="left", double=True)
    presses = [e for e in fake.events if e[:2] == (ecodes.EV_KEY, ecodes.BTN_LEFT)]
    assert [v for *_, v in presses] == [1, 0, 1, 0]


def test_abs_move_rel_is_emulated_from_tracked_position(screen):
    fake = FakeUInput()
    p = AbsPointer(screen, uinput_factory=lambda caps, name: fake)
    p.move_to(100, 100)
    p.move_rel(50, -20)
    assert (ecodes.EV_ABS, ecodes.ABS_X, 150) in fake.events
    assert (ecodes.EV_ABS, ecodes.ABS_Y, 80) in fake.events


def test_abs_scroll_emits_wheel_detents(screen):
    fake = FakeUInput()
    p = AbsPointer(screen, uinput_factory=lambda caps, name: fake)
    p.scroll(-3)
    wheel = [e for e in fake.events if e[:2] == (ecodes.EV_REL, ecodes.REL_WHEEL)]
    assert [v for *_, v in wheel] == [-1, -1, -1]


# -- relative with corner homing ------------------------------------------------
def test_rel_move_to_homes_to_corner_then_walks(screen):
    fake = FakeUInput()
    p = RelPointer(screen, uinput_factory=lambda caps, name: fake)
    p.move_to(105, 205)
    rel_x = [v for t, c, *rest in
             [(e[0], e[1], *e[2:]) for e in fake.events if e[0] != "SYN"]
             if t == ecodes.EV_REL and c == ecodes.REL_X
             for v in rest]
    # first a huge negative homing sweep (compositor clamps it at 0),
    # then the walk from the corner must land exactly on x
    assert rel_x[0] <= -screen.width
    assert sum(rel_x[1:]) == 105
    assert p.position == (105, 205)


def test_rel_move_rel_tracks_position(screen):
    fake = FakeUInput()
    p = RelPointer(screen, uinput_factory=lambda caps, name: fake)
    p.move_to(100, 100)
    p.move_rel(10, 15)
    assert p.position == (110, 115)
    assert (ecodes.EV_REL, ecodes.REL_X, 10) in fake.events
    assert (ecodes.EV_REL, ecodes.REL_Y, 15) in fake.events


# -- the ladder --------------------------------------------------------------
def test_pick_backend_falls_to_dummy_when_uinput_denied(screen):
    def denied(caps, name):
        raise PermissionError("/dev/uinput")

    backend, availability = pick_backend(screen=screen, uinput_factory=denied)
    assert backend.name == "dummy"
    assert availability.status == "needs_setup"
    assert "setup-uinput.sh" in availability.hint


def test_pick_backend_prefers_abs_when_available(screen):
    fakes = []

    def ok(caps, name):
        fake = FakeUInput()
        fakes.append(fake)
        return fake

    backend, availability = pick_backend(screen=screen, uinput_factory=ok)
    assert backend.name == "uinput-abs"
    assert availability.status == "ok"


def test_pick_backend_forced_dummy(screen):
    backend, availability = pick_backend(prefer="dummy", screen=screen)
    assert backend.name == "dummy"
    assert availability.status == "ok"
