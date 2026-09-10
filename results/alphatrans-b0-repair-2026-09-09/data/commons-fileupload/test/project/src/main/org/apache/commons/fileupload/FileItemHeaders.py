from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from abc import ABC, abstractmethod

# Imports End


class FileItemHeaders(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def getHeaderNames(self) -> typing.Iterator[str]:
        pass

    @abstractmethod
    def getHeaders(self, name: str) -> typing.Iterator[str]:
        pass

    @abstractmethod
    def getHeader(self, name: str) -> str:
        pass

    # Class Methods End
