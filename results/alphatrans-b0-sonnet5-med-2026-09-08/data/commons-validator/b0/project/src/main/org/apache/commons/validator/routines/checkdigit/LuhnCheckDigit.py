from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import os
import typing
from typing import *
import io

# Imports End


class LuhnCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = -2976900113942875999
    LUHN_CHECK_DIGIT: CheckDigit = None
    __POSITION_WEIGHT: typing.List[int] = [2, 1]
    # Class Fields End

    # Class Methods Begin
    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        weight = LuhnCheckDigit.__POSITION_WEIGHT[rightPos % 2]
        weightedValue = charValue * weight
        return weightedValue - 9 if weightedValue > 9 else weightedValue

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


LuhnCheckDigit.LUHN_CHECK_DIGIT = LuhnCheckDigit()
