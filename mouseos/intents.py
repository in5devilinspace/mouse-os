"""Frozen intent dataclasses — the only contract between parser and engine."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    pass


# -- state --------------------------------------------------------------
@dataclass(frozen=True)
class Wake(Intent):
    pass


@dataclass(frozen=True)
class Sleep(Intent):
    pass


@dataclass(frozen=True)
class Quit(Intent):
    pass


@dataclass(frozen=True)
class ConfirmQuit(Intent):
    pass


@dataclass(frozen=True)
class NeverMind(Intent):
    pass


# -- always-hot recovery (roundtable amendment) --------------------------
@dataclass(frozen=True)
class Stop(Intent):
    pass


@dataclass(frozen=True)
class Undo(Intent):
    pass


# -- pointer actions ------------------------------------------------------
@dataclass(frozen=True)
class Click(Intent):
    button: str = "left"
    double: bool = False


@dataclass(frozen=True)
class Hold(Intent):
    pass


@dataclass(frozen=True)
class Release(Intent):
    pass


@dataclass(frozen=True)
class Move(Intent):
    dx: int = 0
    dy: int = 0


@dataclass(frozen=True)
class GoTo(Intent):
    region: str = "center"


@dataclass(frozen=True)
class Grid(Intent):
    cell: int = 5


@dataclass(frozen=True)
class PointTo(Intent):
    app: str = ""


@dataclass(frozen=True)
class Focus(Intent):
    app: str = ""


@dataclass(frozen=True)
class Scroll(Intent):
    amount: int = 3


# -- info & launchers ------------------------------------------------------
@dataclass(frozen=True)
class ListWindows(Intent):
    pass


@dataclass(frozen=True)
class WhereAmI(Intent):
    pass


@dataclass(frozen=True)
class ShowCameras(Intent):
    pass


# -- REPL-only --------------------------------------------------------------
@dataclass(frozen=True)
class MoveTo(Intent):
    x: int = 0
    y: int = 0
    percent: bool = False


@dataclass(frozen=True)
class Status(Intent):
    pass


@dataclass(frozen=True)
class Help(Intent):
    pass
