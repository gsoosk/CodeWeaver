from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.disk.DiskFileItem import *
import os
import io
import pathlib

# Imports End


class DiskFileItemFactory:

    # Class Fields Begin
    DEFAULT_SIZE_THRESHOLD: int = 10240
    __repository: pathlib.Path = None
    __sizeThreshold: int = None
    __defaultCharset: str = None
    # Class Fields End

    # Class Methods Begin
    def setDefaultCharset(self, pCharset: str) -> None:
        self.__defaultCharset = pCharset

    def getDefaultCharset(self) -> str:
        return self.__defaultCharset

    def setSizeThreshold(self, sizeThreshold: int) -> None:
        self.__sizeThreshold = sizeThreshold

    def getSizeThreshold(self) -> int:
        return self.__sizeThreshold

    def setRepository(self, repository: pathlib.Path) -> None:
        self.__repository = repository

    def getRepository(self) -> pathlib.Path:
        return self.__repository

    @staticmethod
    def DiskFileItemFactory1() -> DiskFileItemFactory:
        return DiskFileItemFactory(DiskFileItemFactory.DEFAULT_SIZE_THRESHOLD, None)

    def __init__(self, sizeThreshold: int, repository: pathlib.Path) -> None:
        self.__sizeThreshold = sizeThreshold
        self.__repository = repository
        self.__defaultCharset = DiskFileItem.DEFAULT_CHARSET

    # Class Methods End
