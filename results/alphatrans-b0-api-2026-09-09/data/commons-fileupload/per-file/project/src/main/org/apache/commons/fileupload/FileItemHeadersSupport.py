from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileItemHeaders import *
import io
from abc import ABC, abstractmethod

# Imports End


class FileItemHeadersSupport(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def setHeaders(self, headers: FileItemHeaders) -> None:
        pass

    @abstractmethod
    def getHeaders(self) -> FileItemHeaders:
        pass

    # Class Methods End
