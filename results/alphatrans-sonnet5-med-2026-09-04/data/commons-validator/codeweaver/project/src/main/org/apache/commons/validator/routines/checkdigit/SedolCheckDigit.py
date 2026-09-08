from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import os
import typing
from typing import *
import io

# Imports End


class SedolCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = None
    __MAX_ALPHANUMERIC_VALUE: int = 35
    SEDOL_CHECK_DIGIT: CheckDigit = None
    __POSITION_WEIGHT: typing.List[int] = [1, 3, 1, 7, 3, 9, 1]
    # Class Fields End

    # Class Methods Begin
    def _toInt(self, character: str, leftPos: int, rightPos: int) -> int:
        try:
            charValue = int(character, 36)
        except ValueError:
            charValue = -1
        charMax = 9 if rightPos == 1 else SedolCheckDigit.__MAX_ALPHANUMERIC_VALUE
        if charValue < 0 or charValue > charMax:
            raise CheckDigitException.CheckDigitException1(
                "Invalid Character["
                + str(leftPos)
                + ","
                + str(rightPos)
                + "] = '"
                + str(charValue)
                + "' out of range 0 to "
                + str(charMax)
            )
        return charValue

    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        return charValue * SedolCheckDigit.__POSITION_WEIGHT[leftPos - 1]

    def _calculateModulus(self, code: str, includesCheckDigit: bool) -> int:
        if len(code) > len(SedolCheckDigit.__POSITION_WEIGHT):
            raise CheckDigitException.CheckDigitException1(
                "Invalid Code Length = " + str(len(code))
            )
        return super()._calculateModulus(code, includesCheckDigit)

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


SedolCheckDigit.SEDOL_CHECK_DIGIT = SedolCheckDigit()
