from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeadersSupport import *
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO
from abc import ABC, abstractmethod

# Imports End


class ItemSkippedException(IOError):

    # Class Fields Begin
    __serialVersionUID: int = -7280778431581963740
    # Class Fields End

    # Class Methods Begin
    # Class Methods End


class FileItemStream(FileItemHeadersSupport, ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def isFormField(self) -> bool:
        pass

    @abstractmethod
    def getFieldName(self) -> str:
        pass

    @abstractmethod
    def getName(self) -> str:
        pass

    @abstractmethod
    def getContentType(self) -> str:
        pass

    @abstractmethod
    def openStream(self) -> typing.Union[io.BytesIO, io.StringIO, io.BufferedReader]:
        pass

    # Class Methods End
