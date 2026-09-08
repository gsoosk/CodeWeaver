from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io

# Imports End


class Constants:
    """Constants for this package."""

    # Class Fields Begin
    BACKSLASH: str = '\\'
    BACKSPACE: str = '\b'
    COMMA: str = ','
    COMMENT: str = '#'
    CR: str = '\r'
    CRLF: str = '\r\n'
    DOUBLE_QUOTE_CHAR: str = '"'
    EMPTY: str = ''
    EMPTY_STRING_ARRAY: typing.List[typing.List[str]] = []
    END_OF_STREAM: int = -1
    FF: str = '\f'
    LF: str = '\n'
    LINE_SEPARATOR: str = '\u2028'
    NEXT_LINE: str = '\u0085'
    PARAGRAPH_SEPARATOR: str = '\u2029'
    PIPE: str = '|'
    RS: str = chr(30)
    SP: str = ' '
    SQL_NULL_STRING: str = '\\N'
    TAB: str = '\t'
    UNDEFINED: int = -2
    US: str = chr(31)
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        raise TypeError("No instances of Constants are permitted")

    # Class Methods End
