"""TOML config with shipped defaults. ~/.config/mouseos/config.toml"""
import copy
import os
import tomllib
from pathlib import Path

DEFAULTS = {
    "start_asleep": True,
    "pointer": "auto",          # auto | abs | rel | dummy
    "screen": "auto",           # auto | "WIDTHxHEIGHT"
    "steps": {"little": 25, "normal": 100, "lot": 300},
    "apps": {
        "firefox": "firefox",
        "files": "nautilus",
        "terminal": "terminal",
        "editor": "editor",
        "settings": "settings",
    },
    "cameras": {
        # see docs/research/reolink-cameras-on-ubuntu.md — go2rtc 2x2 grid
        "command": ("xdg-open http://localhost:1984/stream.html"
                    "?src=cam1&src=cam2&src=cam3&src=cam4"),
    },
}


def default_path():
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(base) / "mouseos" / "config.toml"


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load(path=None):
    path = Path(path) if path is not None else default_path()
    if not path.exists():
        return copy.deepcopy(DEFAULTS)
    with open(path, "rb") as fh:
        return _merge(DEFAULTS, tomllib.load(fh))
