"""InputSource contract: iterable of lowercase utterance strings.

Sources set .repl = True when typed commands (move to x y, status, help)
should be allowed by the parser.
"""
from typing import Iterator, Protocol, runtime_checkable


@runtime_checkable
class InputSource(Protocol):
    repl: bool

    def __iter__(self) -> Iterator[str]: ...
