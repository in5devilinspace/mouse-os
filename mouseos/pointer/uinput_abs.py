"""Absolute (tablet-style) uinput virtual pointer — the preferred backend.

Mimics the QEMU USB tablet profile that GNOME/libinput accept unconditionally:
an ABS_X/ABS_Y device with button keys. Absolute positioning means no drift
and no corner tricks.
"""
from evdev import AbsInfo, UInput, ecodes

_BUTTONS = {
    "left": ecodes.BTN_LEFT,
    "right": ecodes.BTN_RIGHT,
    "middle": ecodes.BTN_MIDDLE,
}


def _default_factory(caps, name):
    return UInput(caps, name=name)


class AbsPointer:
    name = "uinput-abs"

    def __init__(self, screen, uinput_factory=None):
        self.screen = screen
        factory = uinput_factory or _default_factory
        caps = {
            ecodes.EV_ABS: [
                (ecodes.ABS_X, AbsInfo(value=0, min=0, max=screen.width - 1,
                                       fuzz=0, flat=0, resolution=0)),
                (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=screen.height - 1,
                                       fuzz=0, flat=0, resolution=0)),
            ],
            ecodes.EV_KEY: list(_BUTTONS.values()),
            ecodes.EV_REL: [ecodes.REL_WHEEL],
        }
        self.dev = factory(caps, name="mouseos-pointer-abs")
        self._pos = (screen.width // 2, screen.height // 2)

    @property
    def position(self):
        return self._pos

    def move_to(self, x, y):
        x, y = self.screen.clamp(x, y)
        self.dev.write(ecodes.EV_ABS, ecodes.ABS_X, x)
        self.dev.write(ecodes.EV_ABS, ecodes.ABS_Y, y)
        self.dev.syn()
        self._pos = (x, y)

    def move_rel(self, dx, dy):
        x, y = self._pos
        self.move_to(x + dx, y + dy)

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
