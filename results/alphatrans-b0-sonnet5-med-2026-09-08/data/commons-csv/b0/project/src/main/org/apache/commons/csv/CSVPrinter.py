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


class CSVPrinter:
    """Prints values in a CSV format."""

    def __init__(
        self, appendable: typing.Union[typing.List, io.TextIOBase], format_: "CSVFormat"
    ) -> None:
        if appendable is None:
            raise ValueError("appendable")
        if format_ is None:
            raise ValueError("format")

        self.__appendable = appendable
        self.__format = format_.copy()
        self.__newRecord = True

        headerComments = self.__format.getHeaderComments()
        if headerComments is not None:
            for line in headerComments:
                self.printComment(line)

        if self.__format.getHeader() is not None and not self.__format.getSkipHeaderRecord():
            self.printRecord1(list(self.__format.getHeader()))

    def close(self) -> None:
        self.close1(True)

    def close0(self) -> None:
        self.close1(False)

    def close1(self, flush: bool) -> None:
        if flush or self.__format.getAutoFlush():
            self.flush()
        if hasattr(self.__appendable, "close"):
            self.__appendable.close()

    def flush(self) -> None:
        if hasattr(self.__appendable, "flush"):
            self.__appendable.flush()

    def getOut(self) -> typing.Union[typing.List, io.TextIOBase]:
        return self.__appendable

    def print_(self, value: typing.Any) -> None:
        self.__format.print2(value, self.__appendable, self.__newRecord)
        self.__newRecord = False

    def printComment(self, comment: typing.Optional[str]) -> None:
        if comment is None or not self.__format.isCommentMarkerSet():
            return
        if not self.__newRecord:
            self.println()
        marker = self.__format.getCommentMarker()
        self.__write(marker)
        self.__write(SP)
        i = 0
        n = len(comment)
        while i < n:
            c = comment[i]
            if c == CR:
                if i + 1 < n and comment[i + 1] == LF:
                    i += 1
                self.println()
                self.__write(marker)
                self.__write(SP)
            elif c == LF:
                self.println()
                self.__write(marker)
                self.__write(SP)
            else:
                self.__write(c)
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
        elif hasattr(value, "__iter__"):
            self.printRecord0(value)
        else:
            self.printRecord1([value])

    def printRecords0(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.__printRecordObject(value)

    def printRecords1(self, values: typing.List[typing.Any]) -> None:
        self.printRecords0(list(values))

    def __write(self, s: str) -> None:
        if hasattr(self.__appendable, "write"):
            self.__appendable.write(s)
        else:
            self.__appendable.append(s)
