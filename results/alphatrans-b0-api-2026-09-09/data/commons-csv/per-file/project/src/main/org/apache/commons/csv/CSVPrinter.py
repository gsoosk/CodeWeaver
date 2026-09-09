from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.csv.IOUtils import *
from src.main.org.apache.commons.csv.Constants import *
from src.main.org.apache.commons.csv.CSVFormat import *
import os
import typing
from typing import *
import io
from io import IOBase

# Imports End


class CSVPrinter(io.BufferedIOBase):

    # Class Fields Begin
    __appendable: typing.Union[typing.List, io.TextIOBase] = None
    __format: CSVFormat = None
    __newRecord: bool = None
    # Class Fields End

    # Class Methods Begin

    def _append(self, text: typing.Any) -> None:
        appendable = self.__appendable
        if appendable is None:
            return
        if isinstance(appendable, list):
            if isinstance(text, str):
                appendable.extend(list(text))
            else:
                appendable.append(text)
        elif hasattr(appendable, "write"):
            appendable.write(str(text))
        elif hasattr(appendable, "append"):
            appendable.append(text)
        else:
            raise TypeError("Unsupported appendable type")

    def flush(self) -> None:
        appendable = self.__appendable
        if appendable is not None and hasattr(appendable, "flush"):
            appendable.flush()

    def close(self) -> None:
        self.close1(True)

    def close0(self) -> None:
        self.close1(False)

    def close1(self, flush: bool) -> None:
        if flush or self.__format.getAutoFlush():
            self.flush()
        appendable = self.__appendable
        if appendable is not None and hasattr(appendable, "close"):
            appendable.close()

    def getOut(self) -> typing.Union[typing.List, io.TextIOBase]:
        return self.__appendable

    def print_(self, value: typing.Any) -> None:
        self.__format.print2(value, self.__appendable, self.__newRecord)
        self.__newRecord = False

    def printComment(self, comment: str) -> None:
        if comment is None or not self.__format.isCommentMarkerSet():
            return
        if not self.__newRecord:
            self.println()
        self._append(self.__format.getCommentMarker())
        self._append(SP)
        i = 0
        length = len(comment)
        while i < length:
            c = comment[i]
            if c == CR:
                if i + 1 < length and comment[i + 1] == LF:
                    i += 1
                self.println()
                self._append(self.__format.getCommentMarker())
                self._append(SP)
            elif c == LF:
                self.println()
                self._append(self.__format.getCommentMarker())
                self._append(SP)
            else:
                self._append(c)
            i += 1
        self.println()

    def println(self) -> None:
        self.__format.println(self.__appendable)
        self.__newRecord = True

    def printRecord0(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.print_(value)
        self.println()

    def printRecord1(self, values: typing.List[typing.Any]) -> None:
        self.printRecord0(list(values))

    def printRecord2(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.print_(value)
        self.println()

    def __printRecordObject(self, value: typing.Any) -> None:
        if isinstance(value, (list, tuple)):
            self.printRecord1(list(value))
        elif isinstance(value, str):
            self.printRecord1([value])
        elif isinstance(value, typing.Iterable):
            self.printRecord0(value)
        else:
            self.printRecord1([value])

    def printRecords0(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.__printRecordObject(value)

    def printRecords1(self, values: typing.List[typing.Any]) -> None:
        self.printRecords0(list(values))

    def __init__(
        self, appendable: typing.Union[typing.List, io.TextIOBase], format_: CSVFormat
    ) -> None:
        if appendable is None:
            raise ValueError("appendable")
        if format_ is None:
            raise ValueError("format")

        self.__appendable = appendable
        self.__format = format_.copy()
        self.__newRecord = True

        header_comments = self.__format.getHeaderComments()
        if header_comments is not None:
            for line in header_comments:
                self.printComment(line)

        header = self.__format.getHeader()
        if header is not None and not self.__format.getSkipHeaderRecord():
            self.printRecord1(list(header))

    # Class Methods End
