"""Regression tests built from the REAL Mutter reply shape on the target machine."""
import evdev
import pytest

from mouseos.resolve.windows import detect_screen_size, WindowCallsResolver
from mouseos.resolve.screen import Screen
from mouseos.pointer.detect import pick_backend


def _mode(w, h, current):
    props = {"is-current": {"type": "b", "data": True}} if current else {}
    return [f"{w}x{h}@60", w, h, 60.0, 1.0, [1.0, 1.5, 2.0], props]


# Shaped exactly like busctl --json=short GetCurrentState on the dev machine:
# three monitors — laptop 2880x1800@1.5 at x=3440, ultrawide 3440x1440 at 0,
# side panel 1920x1080 at x=5360. Bounding box: 7280 x 1440.
_STATE = {
    "type": "(ua((ssss)a(siiddada{sv})a{sv})a(iiduba(ssss)a{sv})a{sv})",
    "data": [
        7,
        [
            [["eDP-1", "SDC", "ATNA40HQ01-0 ", "0x0"],
             [_mode(2880, 1800, True), _mode(1920, 1200, False)], {}],
            [["DP-2", "GSM", "LG ULTRAGEAR+", "602I"],
             [_mode(3440, 1440, True)], {}],
            [["DP-1", "ACR", "PM161Q C", "2530"],
             [_mode(1920, 1080, True)], {}],
        ],
        [
            [3440, 0, 1.5, 0, False, [["eDP-1", "SDC", "ATNA40HQ01-0 ", "0x0"]], {}],
            [0, 0, 1.0, 0, True, [["DP-2", "GSM", "LG ULTRAGEAR+", "602I"]], {}],
            [5360, 0, 1.0, 0, False, [["DP-1", "ACR", "PM161Q C", "2530"]], {}],
        ],
        {},
    ],
}


def test_detect_screen_size_bounding_box_of_all_logical_monitors():
    assert detect_screen_size(fetch=lambda: _STATE) == (7280, 1440)


def test_detect_screen_size_none_on_dbus_failure():
    assert detect_screen_size(fetch=lambda: None) is None


def test_window_calls_resolver_matches_wm_class_substring():
    windows = ('[{"wm_class": "firefox", "title": "Mozilla Firefox", '
               '"x": 100, "y": 50, "width": 800, "height": 600, "id": 1}]')
    r = WindowCallsResolver(runner=lambda: {"data": [windows]})
    assert r("firefox") == (100, 50, 800, 600)
    assert r("blender") is None
    assert r.list_names() == ["firefox"]


def test_pick_backend_degrades_on_evdev_uinput_error():
    def denied(caps, name):
        raise evdev.UInputError('"/dev/uinput" cannot be opened for writing')

    backend, availability = pick_backend(screen=Screen(100, 100),
                                         uinput_factory=denied)
    assert backend.name == "dummy"
    assert availability.status == "needs_setup"
    assert "setup-uinput.sh" in availability.hint
