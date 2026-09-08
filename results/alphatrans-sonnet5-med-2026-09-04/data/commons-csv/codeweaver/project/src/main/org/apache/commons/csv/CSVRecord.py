from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.csv.Constants import *
from src.main.org.apache.commons.csv.CSVParser import *
import os
import typing
from typing import *
import enum
import numbers
import io

# Imports End


class CSVRecord:

    # Class Fields Begin
    __serialVersionUID: int = None
    __characterPosition: int = None
    __comment: str = None
    __recordNumber: int = None
    __values: typing.List[typing.List[str]] = None
    __parser: CSVParser = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        return (
            "CSVRecord [comment='"
            + str(self.__comment)
            + "', recordNumber="
            + str(self.__recordNumber)
            + ", values="
            + "[" + ", ".join(str(v) for v in self.__values) + "]"
            + "]"
        )

    def __str__(self) -> str:
        return self.toString()

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.toList())

    def iterator(self) -> typing.Iterator[str]:
        return iter(self.toList())

    def values(self) -> typing.List[typing.List[str]]:
        return self.__values

    def toMap(self) -> typing.Dict[str, str]:
        from collections import OrderedDict

        return self.putIn(OrderedDict())

    def toList(self) -> typing.List[str]:
        return list(self.__values)

    def stream(self) -> typing.Iterable[str]:
        return iter(self.__values)

    def size(self) -> int:
        return len(self.__values)

    def putIn(self, map_: typing.Any) -> typing.Any:
        header_map = self.__getHeaderMapRaw()
        if header_map is None:
            return map_
        for key, value in header_map.items():
            if value < len(self.__values):
                map_[key] = self.__values[value]
        return map_

    def isSet1(self, name: str) -> bool:
        header_map = self.__getHeaderMapRaw()
        return self.isMapped(name) and header_map.get(name) < len(self.__values)

    def isSet0(self, index: int) -> bool:
        return 0 <= index < len(self.__values)

    def isMapped(self, name: str) -> bool:
        header_map = self.__getHeaderMapRaw()
        return header_map is not None and name in header_map

    def isConsistent(self) -> bool:
        header_map = self.__getHeaderMapRaw()
        return header_map is None or len(header_map) == len(self.__values)

    def hasComment(self) -> bool:
        return self.__comment is not None

    def getRecordNumber(self) -> int:
        return self.__recordNumber

    def getParser(self) -> CSVParser:
        return self.__parser

    def getComment(self) -> str:
        return self.__comment

    def getCharacterPosition(self) -> int:
        return self.__characterPosition

    def get2(self, name: str) -> str:
        header_map = self.__getHeaderMapRaw()
        if header_map is None:
            raise ValueError(
                "No header mapping was specified, the record values can't be accessed by name"
            )
        index = header_map.get(name)
        if index is None:
            raise ValueError(
                "Mapping for %s not found, expected one of %s" % (name, list(header_map.keys()))
            )
        try:
            return self.__values[index]
        except IndexError:
            raise ValueError(
                "Index for header '%s' is %d but CSVRecord only has %d values!"
                % (name, index, len(self.__values))
            )

    def get1(self, i: int) -> str:
        return self.__values[i]

    def get0(self, e: enum.Enum) -> str:
        return self.get2(e.name if e is not None else None)

    def __getHeaderMapRaw(self) -> typing.Dict[str, int]:
        return None if self.__parser is None else self.__parser.getHeaderMapRaw()

    def __init__(
        self,
        parser: CSVParser,
        values: typing.List[typing.List[str]],
        comment: str,
        recordNumber: int,
        characterPosition: int,
    ) -> None:
        self.__recordNumber = recordNumber
        self.__values = values if values is not None else Constants.EMPTY_STRING_ARRAY
        self.__parser = parser
        self.__comment = comment
        self.__characterPosition = characterPosition

    # Class Methods End
