from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeaders import *
import typing
from typing import *
import io

# Imports End


class FileItemHeadersImpl(FileItemHeaders):

    # Class Fields Begin
    __serialVersionUID: int = -4455695752627032559
    __headerNameToValueListMap: typing.Dict[str, typing.List[str]] = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.__headerNameToValueListMap = {}

    def getHeaders(self, name: str) -> typing.Iterator[str]:
        nameLower = name.lower()
        lst = self.__headerNameToValueListMap.get(nameLower, [])
        return iter(list(lst))

    def getHeaderNames(self) -> typing.Iterator[str]:
        return iter(list(self.__headerNameToValueListMap.keys()))

    def getHeader(self, name: str) -> str:
        nameLower = name.lower()
        lst = self.__headerNameToValueListMap.get(nameLower)
        if lst is None:
            return None
        return lst[0]

    def addHeader(self, name: str, value: str) -> None:
        nameLower = name.lower()
        lst = self.__headerNameToValueListMap.get(nameLower)
        if lst is None:
            lst = []
            self.__headerNameToValueListMap[nameLower] = lst
        lst.append(value)

    # Class Methods End
