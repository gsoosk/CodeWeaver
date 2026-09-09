from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeadersSupport import *
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO
import pathlib
from abc import ABC, abstractmethod

# Imports End


class FileItem(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def getOutputStream(
        self,
    ) -> typing.Union[io.BytesIO, io.StringIO, io.BufferedWriter]:
        raise NotImplementedError

    @abstractmethod
    def setFormField(self, state: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def isFormField(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def setFieldName(self, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def getFieldName(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def write(self, file: pathlib.Path) -> None:
        raise NotImplementedError

    @abstractmethod
    def getString1(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def getString0(self, encoding: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get(self) -> typing.List[int]:
        raise NotImplementedError

    @abstractmethod
    def getSize(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def isInMemory(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def getName(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def getContentType(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def getInputStream(
        self,
    ) -> typing.Union[io.BytesIO, io.StringIO, io.BufferedReader]:
        raise NotImplementedError

    # Class Methods End
