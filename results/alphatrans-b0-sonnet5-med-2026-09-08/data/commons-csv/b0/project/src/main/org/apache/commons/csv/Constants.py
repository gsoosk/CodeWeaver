from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io

# Imports End


class Constants:

    BACKSLASH: str = '\\'
    BACKSPACE: str = '\b'
    COMMA: str = ','
    COMMENT: str = '#'
    CR: str = '\r'
    CRLF: str = '\r\n'
    DOUBLE_QUOTE_CHAR: str = '"'
    EMPTY: str = ''
    EMPTY_STRING_ARRAY: typing.List[str] = []
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

    def __init__(self) -> None:
        raise TypeError("No instances.")


# Bare module-level aliases so `from Constants import *` exposes the constants
# directly, matching how the Java code used static imports.
BACKSLASH = Constants.BACKSLASH
BACKSPACE = Constants.BACKSPACE
COMMA = Constants.COMMA
COMMENT = Constants.COMMENT
CR = Constants.CR
CRLF = Constants.CRLF
DOUBLE_QUOTE_CHAR = Constants.DOUBLE_QUOTE_CHAR
EMPTY = Constants.EMPTY
EMPTY_STRING_ARRAY = Constants.EMPTY_STRING_ARRAY
END_OF_STREAM = Constants.END_OF_STREAM
FF = Constants.FF
LF = Constants.LF
LINE_SEPARATOR = Constants.LINE_SEPARATOR
NEXT_LINE = Constants.NEXT_LINE
PARAGRAPH_SEPARATOR = Constants.PARAGRAPH_SEPARATOR
PIPE = Constants.PIPE
RS = Constants.RS
SP = Constants.SP
SQL_NULL_STRING = Constants.SQL_NULL_STRING
TAB = Constants.TAB
UNDEFINED = Constants.UNDEFINED
US = Constants.US
