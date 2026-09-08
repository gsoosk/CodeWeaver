from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from io import StringIO
import enum

# Imports End


class Type(enum.Enum):
    """Internal token type representation."""

    # Class Fields Begin
    INVALID = "INVALID"
    TOKEN = "TOKEN"
    EOF = "EOF"
    EORECORD = "EORECORD"
    COMMENT = "COMMENT"
    # Class Fields End

    # Class Methods Begin
    def __str__(self) -> str:
        return self.name

    # Class Methods End


class Token:
    """Internal token representation.

    It is used as contract between the lexer and the parser.
    """

    # Class Fields Begin
    __INITIAL_TOKEN_LENGTH: int = 50
    type: Type = None
    content: typing.Union[typing.List[str], io.StringIO] = None
    isReady: bool = None
    isQuoted: bool = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.type = Type.INVALID
        self.content = StringIO()
        self.isReady = False
        self.isQuoted = False

    def toString(self) -> str:
        return f"{self.type.name} [{self.content.getvalue()}]"

    def __str__(self) -> str:
        return self.toString()

    def reset(self) -> None:
        self.content.seek(0)
        self.content.truncate(0)
        self.type = Type.INVALID
        self.isReady = False
        self.isQuoted = False

    # Class Methods End
