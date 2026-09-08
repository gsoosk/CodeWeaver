from __future__ import annotations

# Imports Begin
import typing
from typing import *
import enum
import io
from io import StringIO

# Imports End


class Type(enum.Enum):
    """Token type."""

    INVALID = "INVALID"
    TOKEN = "TOKEN"
    EOF = "EOF"
    EORECORD = "EORECORD"
    COMMENT = "COMMENT"

    def __str__(self) -> str:
        return self.name


class _StringBuilder:
    """A small mutable string buffer mimicking java.lang.StringBuilder enough
    for the needs of the Lexer/Token/CSVFormat translation."""

    def __init__(self, initial: typing.Optional[str] = None) -> None:
        self._chars: typing.List[str] = list(initial) if initial else []

    def append(self, value: typing.Any) -> "_StringBuilder":
        if value is None:
            return self
        if isinstance(value, _StringBuilder):
            self._chars.extend(value._chars)
        elif isinstance(value, (list, tuple)):
            for v in value:
                self._chars.extend(str(v))
        else:
            self._chars.extend(str(value))
        return self

    def setLength(self, length: int) -> None:
        if length < len(self._chars):
            del self._chars[length:]
        elif length > len(self._chars):
            self._chars.extend([" "] * (length - len(self._chars)))

    def charAt(self, index: int) -> str:
        return self._chars[index]

    def substring(self, start: int, end: typing.Optional[int] = None) -> str:
        if end is None:
            return "".join(self._chars[start:])
        return "".join(self._chars[start:end])

    def toString(self) -> str:
        return "".join(self._chars)

    def __len__(self) -> int:
        return len(self._chars)

    def __str__(self) -> str:
        return self.toString()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, _StringBuilder):
            return self.toString() == other.toString()
        if isinstance(other, str):
            return self.toString() == other
        return NotImplemented


class Token:
    """Internal token representation used as contract between the lexer and
    the parser."""

    __INITIAL_TOKEN_LENGTH: int = 50

    def __init__(self) -> None:
        self.type: Type = Type.INVALID
        self.content: _StringBuilder = _StringBuilder()
        self.isReady: bool = False
        self.isQuoted: bool = False

    def reset(self) -> None:
        self.content.setLength(0)
        self.type = Type.INVALID
        self.isReady = False
        self.isQuoted = False

    def toString(self) -> str:
        return f"{self.type.name} [{self.content.toString()}]"

    def __str__(self) -> str:
        return self.toString()
