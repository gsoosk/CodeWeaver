from __future__ import annotations

# Imports Begin
import os
import io
from abc import ABC, abstractmethod

# Imports End


class Closeable(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def isClosed(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    # Class Methods End
