from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
import io
from abc import ABC, abstractmethod

# Imports End


class CheckDigit(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def isValid(self, code: str) -> bool:
        pass

    @abstractmethod
    def calculate(self, code: str) -> str:
        pass

    # Class Methods End
