from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
import io
from abc import ABC

# Imports End


class CheckDigit(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def isValid(self, code: str) -> bool:
        raise NotImplementedError

    def calculate(self, code: str) -> str:
        raise NotImplementedError

    # Class Methods End
