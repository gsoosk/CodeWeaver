from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from io import StringIO

# Imports End


class Type:

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name

    # Class Fields Begin
    INVALID: typing.Type = None
    TOKEN: typing.Type = None
    EOF: typing.Type = None
    EORECORD: typing.Type = None
    COMMENT: typing.Type = None
    # Class Fields End

    # Class Methods Begin
    # Class Methods End


Type.INVALID = Type("INVALID")
Type.TOKEN = Type("TOKEN")
Type.EOF = Type("EOF")
Type.EORECORD = Type("EORECORD")
Type.COMMENT = Type("COMMENT")


class Token:

    # Class Fields Begin
    __INITIAL_TOKEN_LENGTH: int = 50
    # Class Fields End

    def __init__(self) -> None:
        self.type: typing.Type = Type.INVALID
        self.content: io.StringIO = io.StringIO()
        self.isReady: bool = False
        self.isQuoted: bool = False

    # Class Methods Begin
    def toString(self) -> str:
        return f"{self.type.name} [{self.content.getvalue()}]"

    def __str__(self) -> str:
        return self.toString()

    def reset(self) -> None:
        self.content = io.StringIO()
        self.type = Type.INVALID
        self.isReady = False
        self.isQuoted = False

    # Class Methods End
