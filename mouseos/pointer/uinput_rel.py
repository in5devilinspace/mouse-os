"""Relative uinput virtual mouse — proven fallback when the abs device is rejected.

Absolute moves are synthesized by corner-homing: sweep far past the top-left
corner (the compositor clamps at 0,0), nudge off the corner to dodge GNOME's
hot corner, then walk to the target. Every move_to therefore erases
dead-reckoning drift.
"""
from evdev import UInput, ecodes

_BUTTONS = {
    "left": ecodes.BTN_LEFT,
    "right": ecodes.BTN_RIGHT,
    "middle": ecodes.BTN_MIDDLE,
}

_CORNER_DODGE = 5


def _default_factory(caps, name):
    return UInput(caps, name=name)


class RelPointer:
    name = "uinput-rel"

    def __init__(self, screen, uinput_factory=None):
        self.screen = screen
        factory = uinput_factory or _default_factory
        caps = {
            ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL],
            ecodes.EV_KEY: list(_BUTTONS.values()),
        }
        self.dev = factory(caps, name="mouseos-pointer-rel")
        self._pos = (screen.width // 2, screen.height // 2)

    @property
    def position(self):
        return self._pos

    def _rel(self, dx, dy):
        if dx:
            self.dev.write(ecodes.EV_REL, ecodes.REL_X, dx)
        if dy:
            self.dev.write(ecodes.EV_REL, ecodes.REL_Y, dy)
        self.dev.syn()

    def move_to(self, x, y):
        x, y = self.screen.clamp(x, y)
        sweep = -(max(self.screen.width, self.screen.height) * 2)
        self._rel(sweep, sweep)              # slam into (0,0)
        self._rel(_CORNER_DODGE, _CORNER_DODGE)  # dodge the hot corner
        self._rel(x - _CORNER_DODGE, y - _CORNER_DODGE)
        self._pos = (x, y)

    def move_rel(self, dx, dy):
        self._rel(dx, dy)
        x, y = self._pos
        self._pos = self.screen.clamp(x + dx, y + dy)

    def press(self, button="left"):
        self.dev.write(ecodes.EV_KEY, _BUTTONS[button], 1)
        self.dev.syn()

    def release(self, button="left"):
        self.dev.write(ecodes.EV_KEY, _BUTTONS[button], 0)
        self.dev.syn()

    def click(self, button="left", double=False):
        for _ in range(2 if double else 1):
            self.press(button)
            self.release(button)

    def scroll(self, amount):
        step = 1 if amount > 0 else -1
        for _ in range(abs(amount)):
            self.dev.write(ecodes.EV_REL, ecodes.REL_WHEEL, step)
            self.dev.syn()
