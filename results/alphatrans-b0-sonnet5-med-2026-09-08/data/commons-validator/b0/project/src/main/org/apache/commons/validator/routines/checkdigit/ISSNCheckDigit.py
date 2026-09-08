from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import os
import io

# Imports End


class ISSNCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = 1
    ISSN_CHECK_DIGIT: CheckDigit = None
    # Class Fields End

    # Class Methods Begin
    def _toInt(self, character: str, leftPos: int, rightPos: int) -> int:
        if rightPos == 1 and character == "X":
            return 10
        return super()._toInt(character, leftPos, rightPos)

    def _toCheckDigit(self, charValue: int) -> str:
        if charValue == 10:
            return "X"
        return super()._toCheckDigit(charValue)

    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        return charValue * (9 - leftPos)

    def __init__(self) -> None:
        super().__init__(11)

    # Class Methods End


ISSNCheckDigit.ISSN_CHECK_DIGIT = ISSNCheckDigit()
