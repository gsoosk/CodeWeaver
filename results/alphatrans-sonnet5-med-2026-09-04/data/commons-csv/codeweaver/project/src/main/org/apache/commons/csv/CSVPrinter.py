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
    def flush(self) -> None:
        flush_method = getattr(self.__appendable, "flush", None)
        if callable(flush_method):
            flush_method()

    def close(self) -> None:
        self.close1(True)

    def printRecords1(self, values: typing.List[typing.Any]) -> None:
        self.printRecords0(list(values))

    def printRecords0(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.__printRecordObject(value)

    def printRecord2(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.print_(value)
        self.println()

    def printRecord1(self, values: typing.List[typing.Any]) -> None:
        self.printRecord0(list(values))

    def printRecord0(self, values: typing.Iterable[typing.Any]) -> None:
        for value in values:
            self.print_(value)
        self.println()

    def println(self) -> None:
        self.__format.println(self.__appendable)
        self.__newRecord = True

    def printComment(self, comment: str) -> None:
        if comment is None or not self.__format.isCommentMarkerSet():
            return
        if not self.__newRecord:
            self.println()
        commentMarker = self.__format.getCommentMarker()
        self.__appendable.write(commentMarker)
        self.__appendable.write(Constants.SP)
        i = 0
        length = len(comment)
        while i < length:
            c = comment[i]
            if c == Constants.CR:
                if i + 1 < length and comment[i + 1] == Constants.LF:
                    i += 1
                self.println()
                self.__appendable.write(commentMarker)
                self.__appendable.write(Constants.SP)
            elif c == Constants.LF:
                self.println()
                self.__appendable.write(commentMarker)
                self.__appendable.write(Constants.SP)
            else:
                self.__appendable.write(c)
            i += 1
        self.println()

    def print_(self, value: typing.Any) -> None:
        self.__format.print2(value, self.__appendable, self.__newRecord)
        self.__newRecord = False

    def getOut(self) -> typing.Union[typing.List, io.TextIOBase]:
        return self.__appendable

    def close1(self, flush: bool) -> None:
        if flush or self.__format.getAutoFlush():
            self.flush()
        close_method = getattr(self.__appendable, "close", None)
        if callable(close_method):
            close_method()

    def close0(self) -> None:
        self.close1(False)

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
        headerComments = self.__format.getHeaderComments()
        if headerComments is not None:
            for line in headerComments:
                self.printComment(line)
        if self.__format.getHeader() is not None and not self.__format.getSkipHeaderRecord():
            self.printRecord1(list(self.__format.getHeader()))

    def __printRecordObject(self, value: typing.Any) -> None:
        if isinstance(value, (list, tuple)):
            self.printRecord1(list(value))
        elif isinstance(value, typing.Iterable) and not isinstance(value, (str, bytes)):
            self.printRecord0(value)
        else:
            self.printRecord1([value])

    # Class Methods End
