from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeadersSupport import *
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO
from abc import ABC

# Imports End


class ItemSkippedException(IOError):

    # Class Fields Begin
    __serialVersionUID: int = -7280778431581963740
    # Class Fields End

    # Class Methods Begin
    # Class Methods End


class FileItemStream(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def isFormField(self) -> bool:
        raise NotImplementedError

    def getFieldName(self) -> str:
        raise NotImplementedError

    def getName(self) -> str:
        raise NotImplementedError

    def getContentType(self) -> str:
        raise NotImplementedError

    def openStream(self) -> typing.Union[io.BytesIO, io.StringIO, io.BufferedReader]:
        raise NotImplementedError

    # Class Methods End
