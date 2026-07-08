"""The only stateful object: ASLEEP/AWAKE(+QUIT_PENDING) FSM + believed position.

Safety invariants:
- starts ASLEEP; while asleep only Wake / Quit / ConfirmQuit / NeverMind act
- quit is two-step and the confirmation expires after 10 s
- going to sleep releases any held button (never strand a drag)
- stop is always honored: releases holds and cancels a pending quit
"""
import time

from .intents import (
    Wake, Sleep, Quit, ConfirmQuit, NeverMind, Stop, Undo,
    Click, Hold, Release, Move, GoTo, Grid, PointTo, Focus,
    Scroll, ListWindows, WhereAmI, ShowCameras, MoveTo, Status, Help,
)

_QUIT_WINDOW_S = 10.0
_DEFAULT_CAMERA_CMD = (
    "xdg-open http://localhost:1984/stream.html"
    "?src=cam1&src=cam2&src=cam3&src=cam4"
)


class Engine:
    def __init__(self, pointer, screen, feedback, windows=None, config=None,
                 clock=None, launcher=None):
        self.pointer = pointer
        self.screen = screen
        self.feedback = feedback
        self.windows = windows
        self.config = config or {}
        self.clock = clock or time.monotonic
        self.launcher = launcher
        self.awake = False
        self.done = False
        self.holding = False
        self.position = screen.clamp(screen.width // 2, screen.height // 2)
        self._quit_pending_until = None
        self._undo_position = None

    # -- helpers -----------------------------------------------------------
    def _say(self, key):
        self.feedback.say(key)

    def _quit_pending(self):
        return (self._quit_pending_until is not None
                and self.clock() <= self._quit_pending_until)

    def _release_if_holding(self):
        if self.holding:
            self.pointer.release("left")
            self.holding = False
            self._say("dropped")

    def _move_abs(self, x, y, remember=True):
        x, y = self.screen.clamp(x, y)
        if remember:
            self._undo_position = self.position
        self.pointer.move_to(x, y)
        self.position = (x, y)

    # -- the one entry point -------------------------------------------------
    def handle(self, intent):
        if intent is None:
            self._say("pardon")
            return

        # state & safety commands work regardless of sleep state
        if isinstance(intent, Quit):
            self._quit_pending_until = self.clock() + _QUIT_WINDOW_S
            self._say("sure")
            self.feedback.event('say "confirm quit" within 10 seconds')
            return
        if isinstance(intent, ConfirmQuit):
            if self._quit_pending():
                self._release_if_holding()
                self.done = True
                self._say("goodbye")
            else:
                self._quit_pending_until = None
                self._say("cant")
            return
        if isinstance(intent, NeverMind):
            self._quit_pending_until = None
            return
        if isinstance(intent, Wake):
            self.awake = True
            self._say("ready")
            return
        if isinstance(intent, Sleep):
            self._release_if_holding()
            self.awake = False
            self._say("resting")
            return
        if isinstance(intent, Stop):
            had_hold = self.holding
            self._release_if_holding()
            self._quit_pending_until = None
            if not had_hold:
                self._say("stopped")
            return

        if not self.awake:
            self.feedback.event(f"asleep — ignored {type(intent).__name__}")
            return

        # -- awake-only actions ---------------------------------------------
        if isinstance(intent, Undo):
            if self._undo_position is None:
                self._say("cant")
                return
            target, self._undo_position = self._undo_position, None
            self.pointer.move_to(*target)
            self.position = target
            self._say("reverted")
            return

        if isinstance(intent, Click):
            self.pointer.click(button=intent.button, double=intent.double)
            self._say("done")
            return

        if isinstance(intent, Hold):
            self.pointer.press("left")
            self.holding = True
            self._say("held")
            return

        if isinstance(intent, Release):
            if not self.holding:
                self._say("cant")
                return
            self.pointer.release("left")
            self.holding = False
            self._say("dropped")
            return

        if isinstance(intent, Move):
            x, y = self.position
            nx, ny = self.screen.clamp(x + intent.dx, y + intent.dy)
            dx, dy = nx - x, ny - y
            self._undo_position = self.position
            if dx or dy:
                self.pointer.move_rel(dx, dy)
            self.position = (nx, ny)
            return

        if isinstance(intent, GoTo):
            self._move_abs(*self.screen.region(intent.region))
            return

        if isinstance(intent, Grid):
            self._move_abs(*self.screen.grid_cell(intent.cell))
            return

        if isinstance(intent, MoveTo):
            if intent.percent:
                self._move_abs(*self.screen.percent(intent.x, intent.y))
            else:
                self._move_abs(intent.x, intent.y)
            return

        if isinstance(intent, (PointTo, Focus)):
            if self.windows is None:
                self._say("cant")
                self.feedback.event(
                    "window lookup unavailable — use grid one..nine "
                    "(GNOME 'Window Calls' extension enables point to <app>)")
                return
            rect = self.windows(intent.app)
            if rect is None:
                self._say("cant")
                self.feedback.event(f"no window matching {intent.app!r}")
                return
            x, y, w, h = rect
            self._move_abs(x + w // 2, y + h // 2)
            return

        if isinstance(intent, Scroll):
            self.pointer.scroll(intent.amount)
            return

        if isinstance(intent, WhereAmI):
            x, y = self.position
            region = self.screen.nearest_region(x, y)
            self.feedback.event(f"at ({x}, {y}) — near {region}")
            self.feedback.say(region)
            return

        if isinstance(intent, ListWindows):
            lister = getattr(self.windows, "list_names", None) if self.windows else None
            names = lister() if callable(lister) else None
            if not names:
                self._say("cant")
                return
            self.feedback.event("windows: " + ", ".join(names))
            return

        if isinstance(intent, ShowCameras):
            cmd = (self.config.get("cameras", {}) or {}).get(
                "command", _DEFAULT_CAMERA_CMD)
            if self.launcher is None:
                self._say("cant")
                return
            self.launcher(cmd)
            self._say("opening")
            return

        if isinstance(intent, Status):
            state = "awake" if self.awake else "asleep"
            self.feedback.event(
                f"{state} · position {self.position} · holding={self.holding}")
            return

        if isinstance(intent, Help):
            self.feedback.event("say 'mouse wake' then e.g. 'grid five', "
                                "'click', 'move up a little', 'mouse quit'")
            return

        self._say("pardon")
