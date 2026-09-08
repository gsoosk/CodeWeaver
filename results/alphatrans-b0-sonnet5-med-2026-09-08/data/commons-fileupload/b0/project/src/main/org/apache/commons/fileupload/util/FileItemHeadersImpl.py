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
        self.__headerNameToValueListMap: typing.Dict[str, typing.List[str]] = {}

    def getHeaders(self, name: str) -> typing.Iterator[str]:
        nameLower = name.lower()
        headerValueList = self.__headerNameToValueListMap.get(nameLower)
        if headerValueList is None:
            headerValueList = []
        return iter(list(headerValueList))

    def getHeaderNames(self) -> typing.Iterator[str]:
        return iter(list(self.__headerNameToValueListMap.keys()))

    def getHeader(self, name: str) -> str:
        nameLower = name.lower()
        headerValueList = self.__headerNameToValueListMap.get(nameLower)
        if headerValueList is None:
            return None
        return headerValueList[0]

    def addHeader(self, name: str, value: str) -> None:
        nameLower = name.lower()
        headerValueList = self.__headerNameToValueListMap.get(nameLower)
        if headerValueList is None:
            headerValueList = []
            self.__headerNameToValueListMap[nameLower] = headerValueList
        headerValueList.append(value)

    # Class Methods End
