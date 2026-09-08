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


class CUSIPCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = None
    CUSIP_CHECK_DIGIT: CheckDigit = None
    __POSITION_WEIGHT: typing.List[int] = [2, 1]
    # Class Fields End

    # Class Methods Begin
    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        weight = CUSIPCheckDigit.__POSITION_WEIGHT[rightPos % 2]
        weightedValue = charValue * weight
        return ModulusCheckDigit.sumDigits(weightedValue)

    def _toInt(self, character: str, leftPos: int, rightPos: int) -> int:
        try:
            charValue = int(character, 36)
        except ValueError:
            charValue = -1
        charMax = 9 if rightPos == 1 else 35
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

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


CUSIPCheckDigit.CUSIP_CHECK_DIGIT = CUSIPCheckDigit()
