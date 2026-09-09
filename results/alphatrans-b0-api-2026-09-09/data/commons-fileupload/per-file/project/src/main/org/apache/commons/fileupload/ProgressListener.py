from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from abc import ABC, abstractmethod

# Imports End


class ProgressListener(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def update(self, pBytesRead: int, pContentLength: int, pItems: int) -> None:
        raise NotImplementedError

    # Class Methods End
