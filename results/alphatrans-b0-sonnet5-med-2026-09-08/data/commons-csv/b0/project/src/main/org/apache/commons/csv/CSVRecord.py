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
    """A CSV record parsed from a CSV file."""

    __serialVersionUID: int = 1

    def __init__(
        self,
        parser: typing.Optional["CSVParser"],
        values: typing.Optional[typing.List[str]],
        comment: typing.Optional[str],
        recordNumber: int,
        characterPosition: int,
    ) -> None:
        self.__recordNumber = recordNumber
        self.__values = values if values is not None else list(EMPTY_STRING_ARRAY)
        self.__parser = parser
        self.__comment = comment
        self.__characterPosition = characterPosition

    def get0(self, e: typing.Optional[enum.Enum]) -> str:
        return self.get2(None if e is None else e.name)

    def get1(self, i: int) -> str:
        return self.__values[i]

    def get2(self, name: str) -> str:
        headerMap = self.__getHeaderMapRaw()
        if headerMap is None:
            raise ValueError(
                "No header mapping was specified, the record values can't be accessed by name"
            )
        index = headerMap.get(name)
        if index is None:
            raise ValueError(
                f"Mapping for {name} not found, expected one of {list(headerMap.keys())}"
            )
        try:
            return self.__values[index]
        except IndexError:
            raise ValueError(
                f"Index for header '{name}' is {index} but CSVRecord only has "
                f"{len(self.__values)} values!"
            )

    def getCharacterPosition(self) -> int:
        return self.__characterPosition

    def getComment(self) -> typing.Optional[str]:
        return self.__comment

    def __getHeaderMapRaw(self) -> typing.Optional[typing.Dict[str, int]]:
        return None if self.__parser is None else self.__parser.getHeaderMapRaw()

    def getParser(self) -> typing.Optional["CSVParser"]:
        return self.__parser

    def getRecordNumber(self) -> int:
        return self.__recordNumber

    def hasComment(self) -> bool:
        return self.__comment is not None

    def isConsistent(self) -> bool:
        headerMap = self.__getHeaderMapRaw()
        return headerMap is None or len(headerMap) == len(self.__values)

    def isMapped(self, name: str) -> bool:
        headerMap = self.__getHeaderMapRaw()
        return headerMap is not None and name in headerMap

    def isSet0(self, index: int) -> bool:
        return 0 <= index < len(self.__values)

    def isSet1(self, name: str) -> bool:
        return self.isMapped(name) and self.__getHeaderMapRaw()[name] < len(self.__values)

    def iterator(self) -> typing.Iterator[str]:
        return iter(self.toList())

    def __iter__(self) -> typing.Iterator[str]:
        return self.iterator()

    def putIn(self, map_: typing.Any) -> typing.Any:
        headerMap = self.__getHeaderMapRaw()
        if headerMap is None:
            return map_
        for key, value in headerMap.items():
            if value < len(self.__values):
                map_[key] = self.__values[value]
        return map_

    def size(self) -> int:
        return len(self.__values)

    def stream(self) -> typing.Iterable[str]:
        return iter(self.__values)

    def toList(self) -> typing.List[str]:
        return list(self.__values)

    def toMap(self) -> typing.Dict[str, str]:
        return self.putIn({})

    def toString(self) -> str:
        return (
            "CSVRecord [comment='"
            + str(self.__comment)
            + "', recordNumber="
            + str(self.__recordNumber)
            + ", values="
            + str(list(self.__values))
            + "]"
        )

    def __str__(self) -> str:
        return self.toString()

    def __repr__(self) -> str:
        return self.toString()

    def __len__(self) -> int:
        return self.size()

    def __getitem__(self, item: typing.Union[int, str]) -> str:
        if isinstance(item, int):
            return self.get1(item)
        return self.get2(item)

    def values(self) -> typing.List[str]:
        return self.__values
