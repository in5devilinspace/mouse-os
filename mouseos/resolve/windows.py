"""GNOME Wayland integration over D-Bus via busctl --json (no GVariant parsing).

- detect_screen_size(): monitor geometry from Mutter DisplayConfig.
- try_windows_resolver(): window-by-name lookup IF the 'Window Calls'
  GNOME Shell extension is installed (org.gnome.Shell.Extensions.Windows).
  Returns None when unavailable — the engine degrades to grid targeting.
"""
import json
import shutil
import subprocess


def _busctl(args, timeout=3):
    if not shutil.which("busctl"):
        return None
    try:
        out = subprocess.run(
            ["busctl", "--user", "--json=short", "call"] + args,
            capture_output=True, text=True, timeout=timeout)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _current_mode_by_connector(monitors):
    """connector -> (width, height) of its is-current mode."""
    out = {}
    for mon in monitors:
        connector = mon[0][0]
        for mode in mon[1]:
            props = mode[6] if len(mode) > 6 else {}
            if isinstance(props, dict) and props.get(
                    "is-current", {}).get("data") is True:
                out[connector] = (mode[1], mode[2])
                break
    return out


def detect_screen_size(fetch=None):
    """Effective size of the PRIMARY logical monitor (Mutter DisplayConfig).

    v1 operates on one monitor: grid cells and named regions must always land
    on real pixels, so we use the primary monitor rather than the desktop
    bounding box (which spans gaps between monitors of different heights —
    dead zones where the cursor can never go). Multi-monitor targeting is a
    roadmap item. Each monitor's pixel size is its own current mode / scale.
    """
    fetch = fetch or (lambda: _busctl([
        "org.gnome.Mutter.DisplayConfig",
        "/org/gnome/Mutter/DisplayConfig",
        "org.gnome.Mutter.DisplayConfig", "GetCurrentState", "",
    ]))
    reply = fetch()
    if not reply:
        return None
    try:
        # GetCurrentState -> (serial, monitors, logical_monitors, properties)
        # logical monitor: (x, y, scale, transform, primary, [monitors], props)
        monitors, logical = reply["data"][1], reply["data"][2]
        modes = _current_mode_by_connector(monitors)

        def size_of(lm):
            scale = lm[2] or 1.0
            for spec in (lm[5] if len(lm) > 5 else []):
                mode = modes.get(spec[0])
                if mode:
                    return (int(mode[0] / scale), int(mode[1] / scale))
            return None

        primary = next((lm for lm in logical if len(lm) > 4 and lm[4]), None)
        for lm in ([primary] if primary else logical):
            size = size_of(lm)
            if size and size[0] and size[1]:
                return size
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        pass
    return None


class WindowCallsResolver:
    """Backed by the 'Window Calls' extension: List returns JSON windows."""

    def __init__(self, runner=None):
        self._run = runner or (lambda: _busctl([
            "org.gnome.Shell",
            "/org/gnome/Shell/Extensions/Windows",
            "org.gnome.Shell.Extensions.Windows", "List", "",
        ]))

    def _windows(self):
        reply = self._run()
        if not reply:
            return []
        try:
            payload = reply["data"][0] if isinstance(reply, dict) else reply
            return json.loads(payload) if isinstance(payload, str) else payload
        except (KeyError, IndexError, json.JSONDecodeError, TypeError):
            return []

    def list_names(self):
        names = []
        for w in self._windows():
            name = (w.get("wm_class") or w.get("title") or "").lower()
            if name:
                names.append(name)
        return names

    def __call__(self, name):
        """name -> (x, y, width, height) of the best-matching window, or None."""
        name = name.lower()
        for w in self._windows():
            hay = f"{w.get('wm_class', '')} {w.get('title', '')}".lower()
            if name in hay:
                try:
                    return (int(w["x"]), int(w["y"]),
                            int(w["width"]), int(w["height"]))
                except (KeyError, TypeError, ValueError):
                    continue
        return None


def try_windows_resolver():
    resolver = WindowCallsResolver()
    reply = resolver._run()
    return resolver if reply else None
