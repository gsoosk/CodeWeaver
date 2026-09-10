from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.csv.Token import *
from src.main.org.apache.commons.csv.ExtendedBufferedReader import *
from src.main.org.apache.commons.csv.Constants import *
from src.main.org.apache.commons.csv.CSVFormat import *
import os
import typing
from typing import *
import numbers
import io
from io import StringIO

# Imports End


def _to_char(ch: int) -> str:
    """Mimic Java's (char) cast of an int."""
    return chr(ch & 0xFFFF)


def _is_whitespace(ch: int) -> bool:
    """Mimic Java's Character.isWhitespace((char) ch)."""
    if ch is None:
        return False
    try:
        return _to_char(ch).isspace()
    except (TypeError, ValueError):
        return False


_CR_CODE = ord(CR)
_LF_CODE = ord(LF)
_FF_CODE = ord(FF)
_TAB_CODE = ord(TAB)
_BACKSPACE_CODE = ord(BACKSPACE)


class Lexer:

    # Class Fields Begin
    __CR_STRING: str = CR
    __LF_STRING: str = LF
    __DISABLED: str = '\ufffe'
    __delimiter: typing.List[str] = None
    __delimiterBuf: typing.List[str] = None
    __escapeDelimiterBuf: typing.List[str] = None
    __escape: str = None
    __quoteChar: str = None
    __commentStart: str = None
    __ignoreSurroundingSpaces: bool = None
    __ignoreEmptyLines: bool = None
    __reader: ExtendedBufferedReader = None
    __firstEol: str = None
    __isLastTokenDelimiter: bool = None
    # Class Fields End

    # Class Methods Begin
    def close(self) -> None:
        self.__reader.close()

    def __parseSimpleToken(self, token: Token, ch: int) -> Token:
        while True:
            if self.readEndOfLine(ch):
                token.type = Token.Type.EORECORD
                break
            if self.isEndOfFile(ch):
                token.type = Token.Type.EOF
                token.isReady = True
                break
            if self.isDelimiter(ch):
                token.type = Token.Type.TOKEN
                break
            if self.isEscape(ch):
                if self.isEscapeDelimiter():
                    token.content.append(''.join(self.__delimiter))
                else:
                    unescaped = self.readEscape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(_to_char(ch))
                        token.content.append(_to_char(self.__reader.getLastChar()))
                    else:
                        token.content.append(_to_char(unescaped))
            else:
                token.content.append(_to_char(ch))
            ch = self.__reader.read0()

        if self.__ignoreSurroundingSpaces:
            self.trimTrailingSpaces(token.content)

        return token

    def __parseEncapsulatedToken(self, token: Token) -> Token:
        token.isQuoted = True
        startLineNumber = self.getCurrentLineNumber()
        while True:
            c = self.__reader.read0()

            if self.isEscape(c):
                if self.isEscapeDelimiter():
                    token.content.append(''.join(self.__delimiter))
                else:
                    unescaped = self.readEscape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(_to_char(c))
                        token.content.append(_to_char(self.__reader.getLastChar()))
                    else:
                        token.content.append(_to_char(unescaped))
            elif self.isQuoteChar(c):
                if self.isQuoteChar(self.__reader.lookAhead0()):
                    c = self.__reader.read0()
                    token.content.append(_to_char(c))
                else:
                    while True:
                        c = self.__reader.read0()
                        if self.isDelimiter(c):
                            token.type = Token.Type.TOKEN
                            return token
                        if self.isEndOfFile(c):
                            token.type = Token.Type.EOF
                            token.isReady = True
                            return token
                        if self.readEndOfLine(c):
                            token.type = Token.Type.EORECORD
                            return token
                        if not _is_whitespace(c):
                            raise IOError(
                                "(line "
                                + str(self.getCurrentLineNumber())
                                + ") invalid char between encapsulated token and"
                                + " delimiter"
                            )
            elif self.isEndOfFile(c):
                raise IOError(
                    "(startline "
                    + str(startLineNumber)
                    + ") EOF reached before encapsulated token finished"
                )
            else:
                token.content.append(_to_char(c))

    def __mapNullToDisabled(self, c: str) -> str:
        return self.__DISABLED if c is None else c

    def __isMetaChar(self, ch: int) -> bool:
        return (
            ch == ord(self.__escape)
            or ch == ord(self.__quoteChar)
            or ch == ord(self.__commentStart)
        )

    def trimTrailingSpaces(
        self, buffer: typing.Union[typing.List[str], io.StringIO]
    ) -> None:
        if hasattr(buffer, "length") and hasattr(buffer, "setLength") and hasattr(
            buffer, "charAt"
        ):
            length = buffer.length()
            while length > 0 and str(buffer.charAt(length - 1)).isspace():
                length -= 1
            if length != buffer.length():
                buffer.setLength(length)
        elif hasattr(buffer, "getvalue"):
            s = buffer.getvalue()
            length = len(s)
            while length > 0 and s[length - 1].isspace():
                length -= 1
            if length != len(s):
                buffer.seek(0)
                buffer.truncate()
                buffer.write(s[:length])
        else:
            length = len(buffer)
            while length > 0 and str(buffer[length - 1]).isspace():
                length -= 1
            if length != len(buffer):
                del buffer[length:]

    def readEscape(self) -> int:
        ch = self.__reader.read0()
        if ch == ord('r'):
            return _CR_CODE
        if ch == ord('n'):
            return _LF_CODE
        if ch == ord('t'):
            return _TAB_CODE
        if ch == ord('b'):
            return _BACKSPACE_CODE
        if ch == ord('f'):
            return _FF_CODE
        if ch in (_CR_CODE, _LF_CODE, _FF_CODE, _TAB_CODE, _BACKSPACE_CODE):
            return ch
        if ch == END_OF_STREAM:
            raise IOError("EOF whilst processing escape sequence")
        if self.__isMetaChar(ch):
            return ch
        return END_OF_STREAM

    def readEndOfLine(self, ch: int) -> bool:
        if ch == _CR_CODE and self.__reader.lookAhead0() == _LF_CODE:
            ch = self.__reader.read0()
            if self.__firstEol is None:
                self.__firstEol = CRLF
        if self.__firstEol is None:
            if ch == _LF_CODE:
                self.__firstEol = self.__LF_STRING
            elif ch == _CR_CODE:
                self.__firstEol = self.__CR_STRING

        return ch == _LF_CODE or ch == _CR_CODE

    def nextToken(self, token: Token) -> Token:
        lastChar = self.__reader.getLastChar()

        c = self.__reader.read0()
        eol = self.readEndOfLine(c)

        if self.__ignoreEmptyLines:
            while eol and self.isStartOfLine(lastChar):
                lastChar = c
                c = self.__reader.read0()
                eol = self.readEndOfLine(c)
                if self.isEndOfFile(c):
                    token.type = Token.Type.EOF
                    return token

        if self.isEndOfFile(lastChar) or (
            not self.__isLastTokenDelimiter and self.isEndOfFile(c)
        ):
            token.type = Token.Type.EOF
            return token

        if self.isStartOfLine(lastChar) and self.isCommentStart(c):
            line = self.__reader.readLine()
            if line is None:
                token.type = Token.Type.EOF
                return token
            comment = line.strip()
            token.content.append(comment)
            token.type = Token.Type.COMMENT
            return token

        while token.type == Token.Type.INVALID:
            if self.__ignoreSurroundingSpaces:
                while _is_whitespace(c) and not self.isDelimiter(c) and not eol:
                    c = self.__reader.read0()
                    eol = self.readEndOfLine(c)

            if self.isDelimiter(c):
                token.type = Token.Type.TOKEN
            elif eol:
                token.type = Token.Type.EORECORD
            elif self.isQuoteChar(c):
                self.__parseEncapsulatedToken(token)
            elif self.isEndOfFile(c):
                token.type = Token.Type.EOF
                token.isReady = True
            else:
                self.__parseSimpleToken(token, c)
        return token

    def isStartOfLine(self, ch: int) -> bool:
        return ch == _LF_CODE or ch == _CR_CODE or ch == UNDEFINED

    def isQuoteChar(self, ch: int) -> bool:
        return ch == ord(self.__quoteChar)

    def isEscapeDelimiter(self) -> bool:
        self.__reader.lookAhead1(self.__escapeDelimiterBuf)
        if self.__escapeDelimiterBuf[0] != self.__delimiter[0]:
            return False
        for i in range(1, len(self.__delimiter)):
            if (
                self.__escapeDelimiterBuf[2 * i] != self.__delimiter[i]
                or self.__escapeDelimiterBuf[2 * i - 1] != self.__escape
            ):
                return False
        count = self.__reader.read1(
            self.__escapeDelimiterBuf, 0, len(self.__escapeDelimiterBuf)
        )
        return count != END_OF_STREAM

    def isEscape(self, ch: int) -> bool:
        return ch == ord(self.__escape)

    def isEndOfFile(self, ch: int) -> bool:
        return ch == END_OF_STREAM

    def isDelimiter(self, ch: int) -> bool:
        self.__isLastTokenDelimiter = False
        if ch != ord(self.__delimiter[0]):
            return False
        if len(self.__delimiter) == 1:
            self.__isLastTokenDelimiter = True
            return True
        self.__reader.lookAhead1(self.__delimiterBuf)
        for i in range(len(self.__delimiterBuf)):
            if self.__delimiterBuf[i] != self.__delimiter[i + 1]:
                return False
        count = self.__reader.read1(self.__delimiterBuf, 0, len(self.__delimiterBuf))
        self.__isLastTokenDelimiter = count != END_OF_STREAM
        return self.__isLastTokenDelimiter

    def isCommentStart(self, ch: int) -> bool:
        return ch == ord(self.__commentStart)

    def isClosed(self) -> bool:
        return self.__reader.isClosed()

    def getFirstEol(self) -> str:
        return self.__firstEol

    def getCurrentLineNumber(self) -> int:
        return self.__reader.getCurrentLineNumber()

    def getCharacterPosition(self) -> int:
        return self.__reader.getPosition()

    def __init__(self, format_: CSVFormat, reader: ExtendedBufferedReader) -> None:
        self.__reader = reader
        self.__delimiter = list(format_.getDelimiterString())
        self.__escape = self.__mapNullToDisabled(format_.getEscapeCharacter())
        self.__quoteChar = self.__mapNullToDisabled(format_.getQuoteCharacter())
        self.__commentStart = self.__mapNullToDisabled(format_.getCommentMarker())
        self.__ignoreSurroundingSpaces = format_.getIgnoreSurroundingSpaces()
        self.__ignoreEmptyLines = format_.getIgnoreEmptyLines()
        self.__delimiterBuf = [''] * (len(self.__delimiter) - 1)
        self.__escapeDelimiterBuf = [''] * (2 * len(self.__delimiter) - 1)
        self.__firstEol = None
        self.__isLastTokenDelimiter = False

    # Class Methods End
