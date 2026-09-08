from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeadersSupport import *
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO
import pathlib
from abc import ABC

# Imports End


class FileItem(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def getOutputStream(
        self,
    ) -> typing.Union[io.BytesIO, io.StringIO, io.BufferedWriter]:
        raise NotImplementedError

    def setFormField(self, state: bool) -> None:
        raise NotImplementedError

    def isFormField(self) -> bool:
        raise NotImplementedError

    def setFieldName(self, name: str) -> None:
        raise NotImplementedError

    def getFieldName(self) -> str:
        raise NotImplementedError

    def delete(self) -> None:
        raise NotImplementedError

    def write(self, file: pathlib.Path) -> None:
        raise NotImplementedError

    def getString1(self) -> str:
        raise NotImplementedError

    def getString0(self, encoding: str) -> str:
        raise NotImplementedError

    def get(self) -> typing.List[int]:
        raise NotImplementedError

    def getSize(self) -> int:
        raise NotImplementedError

    def isInMemory(self) -> bool:
        raise NotImplementedError

    def getName(self) -> str:
        raise NotImplementedError

    def getContentType(self) -> str:
        raise NotImplementedError

    def getInputStream(
        self,
    ) -> typing.Union[io.BytesIO, io.StringIO, io.BufferedReader]:
        raise NotImplementedError

    # Class Methods End
