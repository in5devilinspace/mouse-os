"""PointerBackend contract + Availability vocabulary for probes."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Availability:
    status: str          # "ok" | "needs_setup" | "unavailable"
    reason: str = ""
    hint: str = ""


@runtime_checkable
class PointerBackend(Protocol):
    name: str

    def move_to(self, x: int, y: int) -> None: ...
    def move_rel(self, dx: int, dy: int) -> None: ...
    def click(self, button: str = "left", double: bool = False) -> None: ...
    def press(self, button: str = "left") -> None: ...
    def release(self, button: str = "left") -> None: ...
    def scroll(self, amount: int) -> None: ...
