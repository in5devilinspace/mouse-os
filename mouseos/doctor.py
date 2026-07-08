"""mouseos doctor — Availability table with one-line fixes.

Exit code 0 iff the cursor can actually move (a uinput backend opened).
"""
import os
import shutil
import subprocess
from dataclasses import dataclass

_STATUS_MARK = {"ok": "  OK  ", "needs_setup": " FIX  ", "unavailable": " MISS "}


@dataclass(frozen=True)
class Check:
    name: str
    status: str          # ok | needs_setup | unavailable
    detail: str = ""
    hint: str = ""


def render(checks):
    lines = ["mouseos doctor", "=" * 64]
    for c in checks:
        mark = _STATUS_MARK.get(c.status, c.status)
        lines.append(f"[{mark}] {c.name:<14} {c.detail}")
        if c.hint:
            lines.append(f"         fix → {c.hint}")
    return "\n".join(lines)


# -- real probes ------------------------------------------------------------
def probe_uinput():
    try:
        from evdev import UInput, ecodes
        dev = UInput({ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y]},
                     name="mouseos-doctor-probe")
        dev.close()
        return Check("uinput", "ok", "virtual input devices allowed")
    except PermissionError:
        return Check("uinput", "needs_setup", "permission denied on /dev/uinput",
                     "run ./scripts/setup-uinput.sh then log out and back in")
    except FileNotFoundError:
        return Check("uinput", "needs_setup", "/dev/uinput missing",
                     "run ./scripts/setup-uinput.sh (loads the uinput module)")
    except Exception as e:
        # evdev raises UInputError (a bare Exception) for open failures —
        # on this platform that's almost always the permission problem.
        if "cannot be opened" in str(e) or "/dev/uinput" in str(e):
            return Check("uinput", "needs_setup", str(e),
                         "run ./scripts/setup-uinput.sh then log out and back in")
        return Check("uinput", "unavailable", str(e))


def probe_tts():
    if shutil.which("spd-say"):
        return Check("spd-say", "ok", "spoken feedback available")
    return Check("spd-say", "unavailable", "spd-say not found",
                 "sudo apt install speech-dispatcher (feedback stays on screen)")


def probe_capture():
    for tool in ("pw-record", "arecord"):
        if shutil.which(tool):
            return Check("microphone", "ok", f"capture via {tool}")
    return Check("microphone", "unavailable", "no pw-record/arecord",
                 "sudo apt install pipewire-utils or alsa-utils")


def probe_vosk(model_dir=None):
    try:
        import vosk  # noqa: F401
    except ImportError:
        return Check("vosk", "needs_setup", "voice extra not installed",
                     "uv pip install -e '.[voice]' (text REPL works without it)")
    model_dir = model_dir or os.path.expanduser(
        "~/.cache/mouseos/vosk-model-small-en-us-0.15")
    if os.path.isdir(model_dir):
        return Check("vosk", "ok", f"model at {model_dir}")
    return Check("vosk", "needs_setup", "model not downloaded",
                 "mouseos setup-model (~40 MB, one time)")


def probe_screen():
    from .resolve.windows import detect_screen_size
    size = detect_screen_size()
    if size:
        return Check("screen", "ok", f"{size[0]}x{size[1]} (Mutter D-Bus)")
    return Check("screen", "needs_setup", "could not read monitor geometry",
                 "pass --screen WIDTHxHEIGHT or set screen in config.toml")


def probe_windows():
    from .resolve.windows import try_windows_resolver
    if try_windows_resolver() is not None:
        return Check("windows", "ok", "'point to <app>' available")
    return Check("windows", "needs_setup",
                 "GNOME 'Window Calls' extension not detected",
                 "grid one..nine reaches every pixel meanwhile")


def run_checks():
    return [probe_uinput(), probe_tts(), probe_capture(),
            probe_vosk(), probe_screen(), probe_windows()]


def exit_code(checks):
    by_name = {c.name: c for c in checks}
    return 0 if by_name.get("uinput") and by_name["uinput"].status == "ok" else 1
