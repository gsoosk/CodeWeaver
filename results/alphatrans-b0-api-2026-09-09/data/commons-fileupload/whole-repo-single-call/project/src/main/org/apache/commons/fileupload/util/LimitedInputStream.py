from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.util.Closeable import *
import os
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO
from abc import ABC

# Imports End


class LimitedInputStream(ABC):

    # Class Fields Begin
    __sizeMax: int = None
    __count: int = None
    __closed: bool = None
    # Class Fields End

    # Class Methods Begin
    def close(self) -> None:
        self.__closed = True
        self.__inputStream.close()

    def isClosed(self) -> bool:
        return self.__closed

    def read1(self, b: typing.List[int], off: int, len_: int) -> int:
        data = self.__inputStream.read(len_)
        if not data:
            return -1
        n = len(data)
        b[off : off + n] = data
        self.__count += n
        self.__checkLimit()
        return n

    def read0(self) -> int:
        res = self.__inputStream.read(1)
        if not res:
            return -1
        b = res[0]
        self.__count += 1
        self.__checkLimit()
        return b

    def __init__(
        self,
        inputStream: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        pSizeMax: int,
    ) -> None:
        self.__inputStream = inputStream
        self.__sizeMax = pSizeMax
        self.__count = 0
        self.__closed = False

    def __checkLimit(self) -> None:
        if self.__count > self.__sizeMax:
            self._raiseError(self.__sizeMax, self.__count)

    def _raiseError(self, pSizeMax: int, pCount: int) -> None:
        pass

    # Class Methods End
