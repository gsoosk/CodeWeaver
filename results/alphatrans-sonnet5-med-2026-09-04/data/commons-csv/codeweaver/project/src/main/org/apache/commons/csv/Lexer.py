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
import unicodedata

# `typing` exports its own `Type` alias which would otherwise shadow the
# `Token.Type` enum pulled in above via the wildcard import.
from src.main.org.apache.commons.csv.Token import Type as Type

# Imports End


def _java_is_whitespace(ch: int) -> bool:
    """Mirrors java.lang.Character#isWhitespace(char) for BMP code points."""
    if ch < 0:
        return False
    # Explicit control characters that Java treats as whitespace.
    if ch in (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x1C, 0x1D, 0x1E, 0x1F):
        return True
    c = chr(ch)
    category = unicodedata.category(c)
    if category in ("Zs", "Zl", "Zp"):
        # Java excludes non-breaking-style spaces from isWhitespace.
        if ch in (0x00A0, 0x2007, 0x202F):
            return False
        return True
    return False


class Lexer:

    # Class Fields Begin
    __CR_STRING: str = None
    __LF_STRING: str = None
    __DISABLED: str = None
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

    __CR_STRING = Constants.CR
    __LF_STRING = Constants.LF
    __DISABLED = '\ufffe'

    # Class Methods Begin
    def close(self) -> None:
        self.__reader.close()

    def __parseSimpleToken(self, token: Token, ch: int) -> Token:
        while True:
            if self.readEndOfLine(ch):
                token.type = Type.EORECORD
                break
            if self.isEndOfFile(ch):
                token.type = Type.EOF
                token.isReady = True  # there is data at EOF
                break
            if self.isDelimiter(ch):
                token.type = Type.TOKEN
                break
            if self.isEscape(ch):
                if self.isEscapeDelimiter():
                    token.content.write("".join(self.__delimiter))
                else:
                    unescaped = self.readEscape()
                    if unescaped == Constants.END_OF_STREAM:  # unexpected char after escape
                        token.content.write(chr(ch))
                        token.content.write(chr(self.__reader.getLastChar()))
                    else:
                        token.content.write(chr(unescaped))
            else:
                token.content.write(chr(ch))
            ch = self.__reader.read0()  # continue

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
                    token.content.write("".join(self.__delimiter))
                else:
                    unescaped = self.readEscape()
                    if unescaped == Constants.END_OF_STREAM:  # unexpected char after escape
                        token.content.write(chr(c))
                        token.content.write(chr(self.__reader.getLastChar()))
                    else:
                        token.content.write(chr(unescaped))
            elif self.isQuoteChar(c):
                if self.isQuoteChar(self.__reader.lookAhead0()):
                    c = self.__reader.read0()
                    token.content.write(chr(c))
                else:
                    while True:
                        c = self.__reader.read0()
                        if self.isDelimiter(c):
                            token.type = Type.TOKEN
                            return token
                        if self.isEndOfFile(c):
                            token.type = Type.EOF
                            token.isReady = True  # There is data at EOF
                            return token
                        if self.readEndOfLine(c):
                            token.type = Type.EORECORD
                            return token
                        if not _java_is_whitespace(c):
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
                token.content.write(chr(c))

    def __mapNullToDisabled(self, c: str) -> str:
        return Lexer.__DISABLED if c is None else c

    def __isMetaChar(self, ch: int) -> bool:
        return ch == ord(self.__escape) or ch == ord(self.__quoteChar) or ch == ord(self.__commentStart)

    def trimTrailingSpaces(
        self, buffer: typing.Union[typing.List[str], io.StringIO]
    ) -> None:
        value = buffer.getvalue()
        length = len(value)
        while length > 0 and _java_is_whitespace(ord(value[length - 1])):
            length -= 1
        if length != len(value):
            buffer.seek(0)
            buffer.truncate(0)
            buffer.write(value[:length])

    def readEscape(self) -> int:
        ch = self.__reader.read0()
        if ch == ord('r'):
            return ord(Constants.CR)
        if ch == ord('n'):
            return ord(Constants.LF)
        if ch == ord('t'):
            return ord(Constants.TAB)
        if ch == ord('b'):
            return ord(Constants.BACKSPACE)
        if ch == ord('f'):
            return ord(Constants.FF)
        if ch in (
            ord(Constants.CR),
            ord(Constants.LF),
            ord(Constants.FF),  # TODO is this correct?
            ord(Constants.TAB),  # TODO is this correct? Do tabs need to be escaped?
            ord(Constants.BACKSPACE),  # TODO is this correct?
        ):
            return ch
        if ch == Constants.END_OF_STREAM:
            raise IOError("EOF whilst processing escape sequence")
        if self.__isMetaChar(ch):
            return ch
        return Constants.END_OF_STREAM

    def readEndOfLine(self, ch: int) -> bool:
        if ch == ord(Constants.CR) and self.__reader.lookAhead0() == ord(Constants.LF):
            ch = self.__reader.read0()
            if self.__firstEol is None:
                self.__firstEol = Constants.CRLF
        if self.__firstEol is None:
            if ch == ord(Constants.LF):
                self.__firstEol = Lexer.__LF_STRING
            elif ch == ord(Constants.CR):
                self.__firstEol = Lexer.__CR_STRING

        return ch == ord(Constants.LF) or ch == ord(Constants.CR)

    def nextToken(self, token: Token) -> Token:
        lastChar = self.__reader.getLastChar()

        c = self.__reader.read0()
        # Note: The following call will swallow LF if c == CR. But we don't need to know if the
        # last char was CR or LF - they are equivalent here.
        eol = self.readEndOfLine(c)

        if self.__ignoreEmptyLines:
            while eol and self.isStartOfLine(lastChar):
                lastChar = c
                c = self.__reader.read0()
                eol = self.readEndOfLine(c)
                if self.isEndOfFile(c):
                    token.type = Type.EOF
                    return token

        if self.isEndOfFile(lastChar) or not self.__isLastTokenDelimiter and self.isEndOfFile(c):
            token.type = Type.EOF
            return token

        if self.isStartOfLine(lastChar) and self.isCommentStart(c):
            line = self.__reader.readLine()
            if line is None:
                token.type = Type.EOF
                return token
            comment = line.strip()
            token.content.write(comment)
            token.type = Type.COMMENT
            return token

        while token.type == Type.INVALID:
            if self.__ignoreSurroundingSpaces:
                while _java_is_whitespace(c) and not self.isDelimiter(c) and not eol:
                    c = self.__reader.read0()
                    eol = self.readEndOfLine(c)

            if self.isDelimiter(c):
                token.type = Type.TOKEN
            elif eol:
                token.type = Type.EORECORD
            elif self.isQuoteChar(c):
                self.__parseEncapsulatedToken(token)
            elif self.isEndOfFile(c):
                token.type = Type.EOF
                token.isReady = True  # there is data at EOF
            else:
                self.__parseSimpleToken(token, c)
        return token

    def isStartOfLine(self, ch: int) -> bool:
        return ch == ord(Constants.LF) or ch == ord(Constants.CR) or ch == Constants.UNDEFINED

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
        count = self.__reader.read1(self.__escapeDelimiterBuf, 0, len(self.__escapeDelimiterBuf))
        return count != Constants.END_OF_STREAM

    def isEscape(self, ch: int) -> bool:
        return ch == ord(self.__escape)

    def isEndOfFile(self, ch: int) -> bool:
        return ch == Constants.END_OF_STREAM

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
        self.__isLastTokenDelimiter = count != Constants.END_OF_STREAM
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
        self.__delimiterBuf = ['\0'] * (len(self.__delimiter) - 1)
        self.__escapeDelimiterBuf = ['\0'] * (2 * len(self.__delimiter) - 1)
        self.__firstEol = None
        self.__isLastTokenDelimiter = False

    # Class Methods End
