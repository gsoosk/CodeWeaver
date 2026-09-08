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


def _is_whitespace(ch: typing.Any) -> bool:
    return isinstance(ch, str) and ch.isspace()


class Lexer:
    """Lexical analyzer."""

    __CR_STRING: str = CR
    __LF_STRING: str = LF

    # Constant used for disabling comments, escapes and encapsulation.
    __DISABLED: str = "\ufffe"

    def __init__(self, format_: "CSVFormat", reader: ExtendedBufferedReader) -> None:
        self.__reader = reader
        self.__delimiter: typing.List[str] = list(format_.getDelimiterString())
        self.__escape: str = self.__mapNullToDisabled(format_.getEscapeCharacter())
        self.__quoteChar: str = self.__mapNullToDisabled(format_.getQuoteCharacter())
        self.__commentStart: str = self.__mapNullToDisabled(format_.getCommentMarker())
        self.__ignoreSurroundingSpaces: bool = format_.getIgnoreSurroundingSpaces()
        self.__ignoreEmptyLines: bool = format_.getIgnoreEmptyLines()
        self.__delimiterBuf: typing.List[str] = [None] * (len(self.__delimiter) - 1)
        self.__escapeDelimiterBuf: typing.List[str] = [None] * (
            2 * len(self.__delimiter) - 1
        )
        self.__firstEol: typing.Optional[str] = None
        self.__isLastTokenDelimiter: bool = False

    def close(self) -> None:
        self.__reader.close()

    def getCharacterPosition(self) -> int:
        return self.__reader.getPosition()

    def getCurrentLineNumber(self) -> int:
        return self.__reader.getCurrentLineNumber()

    def getFirstEol(self) -> str:
        return self.__firstEol

    def isClosed(self) -> bool:
        return self.__reader.isClosed()

    def isCommentStart(self, ch: int) -> bool:
        return ch == self.__commentStart

    def isDelimiter(self, ch: int) -> bool:
        self.__isLastTokenDelimiter = False
        if ch != self.__delimiter[0]:
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

    def isEndOfFile(self, ch: int) -> bool:
        return ch == END_OF_STREAM

    def isEscape(self, ch: int) -> bool:
        return ch == self.__escape

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

    def __isMetaChar(self, ch: int) -> bool:
        return ch == self.__escape or ch == self.__quoteChar or ch == self.__commentStart

    def isQuoteChar(self, ch: int) -> bool:
        return ch == self.__quoteChar

    def isStartOfLine(self, ch: int) -> bool:
        return ch == LF or ch == CR or ch == UNDEFINED

    def __mapNullToDisabled(self, c: typing.Optional[str]) -> str:
        return Lexer.__DISABLED if c is None else c

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
                    token.type = Type.EOF
                    return token

        if self.isEndOfFile(lastChar) or (
            not self.__isLastTokenDelimiter and self.isEndOfFile(c)
        ):
            token.type = Type.EOF
            return token

        if self.isStartOfLine(lastChar) and self.isCommentStart(c):
            line = self.__reader.readLine()
            if line is None:
                token.type = Type.EOF
                return token
            comment = line.strip()
            token.content.append(comment)
            token.type = Type.COMMENT
            return token

        while token.type == Type.INVALID:
            if self.__ignoreSurroundingSpaces:
                while _is_whitespace(c) and not self.isDelimiter(c) and not eol:
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
                token.isReady = True
            else:
                self.__parseSimpleToken(token, c)
        return token

    def __parseEncapsulatedToken(self, token: Token) -> Token:
        token.isQuoted = True
        startLineNumber = self.getCurrentLineNumber()
        while True:
            c = self.__reader.read0()

            if self.isEscape(c):
                if self.isEscapeDelimiter():
                    token.content.append(self.__delimiter)
                else:
                    unescaped = self.readEscape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(c)
                        token.content.append(self.__reader.getLastChar())
                    else:
                        token.content.append(unescaped)
            elif self.isQuoteChar(c):
                if self.isQuoteChar(self.__reader.lookAhead0()):
                    c = self.__reader.read0()
                    token.content.append(c)
                else:
                    while True:
                        c = self.__reader.read0()
                        if self.isDelimiter(c):
                            token.type = Type.TOKEN
                            return token
                        if self.isEndOfFile(c):
                            token.type = Type.EOF
                            token.isReady = True
                            return token
                        if self.readEndOfLine(c):
                            token.type = Type.EORECORD
                            return token
                        if not _is_whitespace(c):
                            raise IOError(
                                "(line "
                                + str(self.getCurrentLineNumber())
                                + ") invalid char between encapsulated token and delimiter"
                            )
            elif self.isEndOfFile(c):
                raise IOError(
                    "(startline "
                    + str(startLineNumber)
                    + ") EOF reached before encapsulated token finished"
                )
            else:
                token.content.append(c)

    def __parseSimpleToken(self, token: Token, ch: int) -> Token:
        while True:
            if self.readEndOfLine(ch):
                token.type = Type.EORECORD
                break
            if self.isEndOfFile(ch):
                token.type = Type.EOF
                token.isReady = True
                break
            if self.isDelimiter(ch):
                token.type = Type.TOKEN
                break
            if self.isEscape(ch):
                if self.isEscapeDelimiter():
                    token.content.append(self.__delimiter)
                else:
                    unescaped = self.readEscape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(ch)
                        token.content.append(self.__reader.getLastChar())
                    else:
                        token.content.append(unescaped)
            else:
                token.content.append(ch)
            ch = self.__reader.read0()

        if self.__ignoreSurroundingSpaces:
            self.trimTrailingSpaces(token.content)

        return token

    def readEndOfLine(self, ch: int) -> bool:
        if ch == CR and self.__reader.lookAhead0() == LF:
            ch = self.__reader.read0()
            if self.__firstEol is None:
                self.__firstEol = CRLF
        if self.__firstEol is None:
            if ch == LF:
                self.__firstEol = Lexer.__LF_STRING
            elif ch == CR:
                self.__firstEol = Lexer.__CR_STRING
        return ch == LF or ch == CR

    def readEscape(self) -> int:
        ch = self.__reader.read0()
        if ch == "r":
            return CR
        if ch == "n":
            return LF
        if ch == "t":
            return TAB
        if ch == "b":
            return BACKSPACE
        if ch == "f":
            return FF
        if ch == CR or ch == LF or ch == FF or ch == TAB or ch == BACKSPACE:
            return ch
        if ch == END_OF_STREAM:
            raise IOError("EOF whilst processing escape sequence")
        if self.__isMetaChar(ch):
            return ch
        return END_OF_STREAM

    def trimTrailingSpaces(
        self, buffer: typing.Union[typing.List[str], io.StringIO]
    ) -> None:
        length = len(buffer)
        while length > 0 and _is_whitespace(buffer.charAt(length - 1)):
            length -= 1
        if length != len(buffer):
            buffer.setLength(length)
