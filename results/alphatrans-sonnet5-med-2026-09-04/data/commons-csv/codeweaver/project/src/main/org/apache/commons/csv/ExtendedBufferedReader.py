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
    to see the next char returned by ``read0()``. This reader also tracks
    how many characters have been read with ``getPosition()``.

    Note: this does not call ``io.BufferedReader.__init__`` because the
    wrapped ``reader`` is a text-based object (e.g. ``io.StringIO`` or any
    object exposing ``read``/``close``), not the raw binary stream that
    ``io.BufferedReader`` expects. All buffering/look-ahead state is tracked
    manually with a small pushback queue, and all inherited I/O behavior
    (context manager, close, etc.) is implemented explicitly below.
    """

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
        self.__reader = reader
        self.__lastChar = Constants.UNDEFINED
        self.__eolCounter = 0
        self.__position = 0
        self.__closed = False
        # One-slot-or-more pushback queue used to implement lookAhead*
        # without relying on BufferedReader.mark()/reset().
        self.__pushback: typing.List[str] = []

    def __enter__(self) -> "ExtendedBufferedReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False

    @property
    def closed(self) -> bool:
        return self.__closed

    def __fillPushback(self, n: int) -> None:
        while len(self.__pushback) < n:
            ch = self.__reader.read(1)
            if ch == "":
                break
            self.__pushback.append(ch)

    def getCurrentLineNumber(self) -> int:
        if self.__lastChar in (ord(Constants.CR), ord(Constants.LF), Constants.UNDEFINED, Constants.END_OF_STREAM):
            return self.__eolCounter  # counter is accurate
        return self.__eolCounter + 1  # Allow for counter being incremented only at EOL

    def getLastChar(self) -> int:
        return self.__lastChar

    def getPosition(self) -> int:
        return self.__position

    def isClosed(self) -> bool:
        return self.__closed

    def lookAhead0(self) -> int:
        self.__fillPushback(1)
        if not self.__pushback:
            return Constants.END_OF_STREAM
        return ord(self.__pushback[0])

    def lookAhead1(self, buf: typing.List[str]) -> typing.List[str]:
        n = len(buf)
        self.__fillPushback(n)
        for i in range(min(n, len(self.__pushback))):
            buf[i] = self.__pushback[i]
        return buf

    def lookAhead2(self, n: int) -> typing.List[str]:
        buf = ["\0"] * n
        return self.lookAhead1(buf)

    def read0(self) -> int:
        if self.__pushback:
            ch = self.__pushback.pop(0)
        else:
            ch = self.__reader.read(1)
        current = Constants.END_OF_STREAM if ch == "" else ord(ch)
        if (
            current == ord(Constants.CR)
            or (current == ord(Constants.LF) and self.__lastChar != ord(Constants.CR))
            or (
                current == Constants.END_OF_STREAM
                and self.__lastChar != ord(Constants.CR)
                and self.__lastChar != ord(Constants.LF)
                and self.__lastChar != Constants.END_OF_STREAM
            )
        ):
            self.__eolCounter += 1
        self.__lastChar = current
        self.__position += 1
        return self.__lastChar

    def read1(self, buf: typing.List[str], offset: int, length: int) -> int:
        if length == 0:
            return 0

        chars: typing.List[str] = []
        while len(chars) < length and self.__pushback:
            chars.append(self.__pushback.pop(0))
        if len(chars) < length:
            remaining = length - len(chars)
            s = self.__reader.read(remaining)
            if s:
                chars.extend(s)

        length_read = len(chars)

        if length_read > 0:
            for i, ch in enumerate(chars):
                idx = offset + i
                if idx < len(buf):
                    buf[idx] = ch
                else:
                    buf.append(ch)

            for i in range(offset, offset + length_read):
                ch = ord(buf[i])
                if ch == ord(Constants.LF):
                    prev = ord(buf[i - 1]) if i > offset else self.__lastChar
                    if ord(Constants.CR) != prev:
                        self.__eolCounter += 1
                elif ch == ord(Constants.CR):
                    self.__eolCounter += 1

            self.__lastChar = ord(buf[offset + length_read - 1])
            self.__position += length_read
            return length_read

        # len == -1 in the Java sense: nothing could be read (EOF).
        self.__lastChar = Constants.END_OF_STREAM
        self.__position += -1
        return -1

    def readLine(self) -> typing.Optional[str]:
        if self.lookAhead0() == Constants.END_OF_STREAM:
            return None
        buffer: typing.List[str] = []
        while True:
            current = self.read0()
            if current == ord(Constants.CR):
                next_ = self.lookAhead0()
                if next_ == ord(Constants.LF):
                    self.read0()
            if current == Constants.END_OF_STREAM or current == ord(Constants.LF) or current == ord(Constants.CR):
                break
            buffer.append(chr(current))
        return "".join(buffer)

    def close(self) -> None:
        self.__closed = True
        self.__lastChar = Constants.END_OF_STREAM
        self.__reader.close()

    # Class Methods End
