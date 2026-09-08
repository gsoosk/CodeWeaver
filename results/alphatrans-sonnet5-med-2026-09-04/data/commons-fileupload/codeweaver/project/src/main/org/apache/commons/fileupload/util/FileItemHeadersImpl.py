from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeaders import *
import typing
from typing import *
import io
from collections import OrderedDict

# Imports End


class FileItemHeadersImpl(FileItemHeaders):

    # Class Fields Begin
    __serialVersionUID: int = -4455695752627032559
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        # Map of str keys (lower-cased header name) to a list of str values,
        # mirroring the Java LinkedHashMap<String, List<String>> field.
        self.__headerNameToValueListMap: typing.Dict[str, typing.List[str]] = OrderedDict()

    def getHeaders(self, name: str) -> typing.Iterator[str]:
        nameLower = name.lower()
        headerValueList = self.__headerNameToValueListMap.get(nameLower)
        if headerValueList is None:
            headerValueList = []
        return iter(headerValueList)

    def getHeaderNames(self) -> typing.Iterator[str]:
        return iter(self.__headerNameToValueListMap.keys())

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
