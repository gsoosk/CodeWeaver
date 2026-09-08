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
        self.__wrapped.close()

    def isClosed(self) -> bool:
        return self.__closed

    def read1(self, b: typing.List[int], off: int, len_: int) -> int:
        data = self.__wrapped.read(len_)
        if not data:
            res = -1
        else:
            res = len(data)
            for i, byteVal in enumerate(data):
                b[off + i] = byteVal
        if res > 0:
            self.__count += res
            self.__checkLimit()
        return res

    def read0(self) -> int:
        data = self.__wrapped.read(1)
        if not data:
            res = -1
        else:
            res = data[0]
        if res != -1:
            self.__count += 1
            self.__checkLimit()
        return res

    def __init__(
        self,
        inputStream: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        pSizeMax: int,
    ) -> None:
        self.__wrapped = inputStream
        self.__sizeMax = pSizeMax
        self.__count = 0
        self.__closed = False

    def __checkLimit(self) -> None:
        if self.__count > self.__sizeMax:
            self._raiseError(self.__sizeMax, self.__count)

    def _raiseError(self, pSizeMax: int, pCount: int) -> None:
        raise NotImplementedError

    # Class Methods End
