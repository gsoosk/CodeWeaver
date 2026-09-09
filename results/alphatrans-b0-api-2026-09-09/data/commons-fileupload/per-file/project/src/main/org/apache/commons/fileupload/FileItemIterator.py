from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileUploadException import *
from src.main.org.apache.commons.fileupload.FileItemStream import *
import typing
from typing import *
import io
from abc import ABC, abstractmethod

# Imports End


class FileItemIterator(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def next_(self) -> FileItemStream:
        """
        Returns the next available FileItemStream.

        Raises NoSuchElementException (via StopIteration semantics not used here;
        Java throws java.util.NoSuchElementException) if no more items are available.
        """
        raise NotImplementedError

    @abstractmethod
    def hasNext(self) -> bool:
        raise NotImplementedError

    # Class Methods End
