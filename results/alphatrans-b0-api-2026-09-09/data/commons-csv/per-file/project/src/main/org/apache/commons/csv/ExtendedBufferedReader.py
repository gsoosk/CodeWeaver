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

    # Class Fields Begin
    __lastChar: int = None
    __eolCounter: int = None
    __position: int = None
    __closed: bool = None
    # Class Fields End

    # Class Methods Begin
    def __init__(
        self, reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase]
    ) -> None:
        # NOTE: We do not delegate to io.BufferedReader's binary implementation
        # since the underlying reader here is expected to be a text-mode
        # file-like object (like java.io.Reader). Instead we manage our own
        # internal state and a small look-ahead buffer.
        self.__reader = reader
        self.__lastChar = UNDEFINED
        self.__eolCounter = 0
        self.__position = 0
        self.__closed = False
        # Buffer of look-ahead characters (as ints, matching Java char/int
        # semantics) that have been peeked but not yet consumed.
        self.__pushback: typing.List[int] = []

    def _read_raw(self) -> int:
        ch = self.__reader.read(1)
        if ch == "" or ch is None:
            return END_OF_STREAM
        return ord(ch)

    def _next_char(self) -> int:
        if self.__pushback:
            return self.__pushback.pop(0)
        return self._read_raw()

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
        if not self.__pushback:
            c = self._read_raw()
            self.__pushback.append(c)
        return self.__pushback[0]

    def lookAhead1(self, buf: typing.List[str]) -> typing.List[str]:
        n = len(buf)
        while len(self.__pushback) < n:
            c = self._read_raw()
            self.__pushback.append(c)
            if c == END_OF_STREAM:
                break
        for i in range(n):
            if i < len(self.__pushback) and self.__pushback[i] != END_OF_STREAM:
                buf[i] = chr(self.__pushback[i])
            else:
                buf[i] = "\x00"
        return buf

    def lookAhead2(self, n: int) -> typing.List[str]:
        buf: typing.List[str] = [None] * n
        return self.lookAhead1(buf)

    def read0(self) -> int:
        current = self._next_char()
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
        return self.__lastChar

    def read1(self, buf: typing.List[str], offset: int, length: int) -> int:
        if length == 0:
            return 0

        codes: typing.List[int] = []
        for _ in range(length):
            c = self._next_char()
            if c == END_OF_STREAM:
                break
            codes.append(c)

        length_read = len(codes)

        if length_read > 0:
            for i in range(length_read):
                buf[offset + i] = chr(codes[i])

            for i in range(length_read):
                ch = codes[i]
                if ch == LF:
                    prev = codes[i - 1] if i > 0 else self.__lastChar
                    if prev != CR:
                        self.__eolCounter += 1
                elif ch == CR:
                    self.__eolCounter += 1

            self.__lastChar = codes[length_read - 1]
            self.__position += length_read
            return length_read
        else:
            self.__lastChar = END_OF_STREAM
            self.__position += -1
            return -1

    def readLine(self) -> str:
        if self.lookAhead0() == END_OF_STREAM:
            return None
        buffer: typing.List[str] = []
        while True:
            current = self.read0()
            if current == CR:
                next_char = self.lookAhead0()
                if next_char == LF:
                    self.read0()
            if current == END_OF_STREAM or current == LF or current == CR:
                break
            buffer.append(chr(current))
        return "".join(buffer)

    # Class Methods End
