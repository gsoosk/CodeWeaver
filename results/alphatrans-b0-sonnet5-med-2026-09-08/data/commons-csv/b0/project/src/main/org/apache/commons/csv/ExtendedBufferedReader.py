from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.csv.Constants import *
import os
import typing
from typing import *
import numbers
import io
from io import IOBase

# Imports End


class ExtendedBufferedReader(io.BufferedReader):
    """A special buffered reader which supports sophisticated read access.

    In particular the reader supports a look-ahead option, which allows you
    to see the next char returned by read0(). This reader also tracks how
    many characters have been read via getPosition().
    """

    def __init__(
        self, reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase]
    ) -> None:
        self.__reader = reader
        self.__lastChar: int = UNDEFINED
        self.__eolCounter: int = 0
        self.__position: int = 0
        self.__closed: bool = False

    def close(self) -> None:
        self.__closed = True
        self.__lastChar = END_OF_STREAM
        self.__reader.close()

    def getCurrentLineNumber(self) -> int:
        if self.__lastChar in (CR, LF, UNDEFINED, END_OF_STREAM):
            return self.__eolCounter
        return self.__eolCounter + 1

    def getLastChar(self) -> int:
        return self.__lastChar

    def getPosition(self) -> int:
        return self.__position

    def isClosed(self) -> bool:
        return self.__closed

    def lookAhead0(self) -> int:
        pos = self.__reader.tell()
        c = self.__reader.read(1)
        self.__reader.seek(pos)
        return c if c else END_OF_STREAM

    def lookAhead1(self, buf: typing.List[str]) -> typing.List[str]:
        n = len(buf)
        pos = self.__reader.tell()
        s = self.__reader.read(n)
        self.__reader.seek(pos)
        for i in range(n):
            buf[i] = s[i] if i < len(s) else None
        return buf

    def lookAhead2(self, n: int) -> typing.List[str]:
        buf: typing.List[str] = [None] * n
        return self.lookAhead1(buf)

    def read0(self) -> int:
        c = self.__reader.read(1)
        current = c if c else END_OF_STREAM
        if (
            current == CR
            or (current == LF and self.__lastChar != CR)
            or (
                current == END_OF_STREAM
                and self.__lastChar != CR
                and self.__lastChar != LF
                and self.__lastChar != END_OF_STREAM
            )
        ):
            self.__eolCounter += 1
        self.__lastChar = current
        self.__position += 1
        return current

    def read1(self, buf: typing.List[str], offset: int, length: int) -> int:
        if length == 0:
            return 0
        s = self.__reader.read(length)
        ln = len(s)
        if ln > 0:
            for i in range(ln):
                buf[offset + i] = s[i]
            for i in range(offset, offset + ln):
                ch = buf[i]
                if ch == LF:
                    prev = buf[i - 1] if i > offset else self.__lastChar
                    if prev != CR:
                        self.__eolCounter += 1
                elif ch == CR:
                    self.__eolCounter += 1
            self.__lastChar = buf[offset + ln - 1]
        elif ln == 0:
            self.__lastChar = END_OF_STREAM
            self.__position += 0
            return -1
        self.__position += ln
        return ln

    def readLine(self) -> typing.Optional[str]:
        if self.lookAhead0() == END_OF_STREAM:
            return None
        chars: typing.List[str] = []
        while True:
            current = self.read0()
            if current == CR:
                nxt = self.lookAhead0()
                if nxt == LF:
                    self.read0()
            if current == END_OF_STREAM or current == LF or current == CR:
                break
            chars.append(current)
        return "".join(chars)
