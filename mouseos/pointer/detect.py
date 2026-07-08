"""Probe ladder: uinput-abs → uinput-rel → dummy. Degrades loudly, never silently."""
from .base import Availability
from .dummy import DummyPointer
from .uinput_abs import AbsPointer
from .uinput_rel import RelPointer

_SETUP_HINT = ("run ./scripts/setup-uinput.sh (one-time, needs sudo), "
               "then log out and back in")


def pick_backend(prefer="auto", screen=None, uinput_factory=None):
    """Returns (backend, Availability). Never raises: worst case is dummy."""
    if prefer == "dummy":
        return DummyPointer(echo=True), Availability("ok", "forced dummy", "")

    ladder = []
    if prefer in ("auto", "abs"):
        ladder.append(("uinput-abs", AbsPointer))
    if prefer in ("auto", "rel"):
        ladder.append(("uinput-rel", RelPointer))

    try:
        from evdev import UInputError
    except ImportError:  # pragma: no cover
        UInputError = OSError

    last_error = None
    for name, cls in ladder:
        try:
            backend = cls(screen, uinput_factory=uinput_factory)
            return backend, Availability("ok", f"{name} created", "")
        except PermissionError as e:
            last_error = f"{name}: permission denied ({e})"
        except FileNotFoundError as e:
            last_error = f"{name}: /dev/uinput missing ({e})"
        # evdev's UInputError subclasses Exception, not OSError
        except (OSError, UInputError) as e:
            last_error = f"{name}: {e}"

    return (DummyPointer(echo=True),
            Availability("needs_setup",
                         last_error or "no uinput backend requested",
                         _SETUP_HINT))
