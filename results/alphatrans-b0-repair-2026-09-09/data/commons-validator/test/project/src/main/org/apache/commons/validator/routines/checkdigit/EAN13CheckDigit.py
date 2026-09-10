from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import os
import typing
from typing import *
import io

# Imports End


class EAN13CheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = 1726347093230424107
    EAN13_CHECK_DIGIT: CheckDigit = None
    __POSITION_WEIGHT: typing.List[int] = [3, 1]
    # Class Fields End

    # Class Methods Begin
    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        weight = EAN13CheckDigit.__POSITION_WEIGHT[rightPos % 2]
        return charValue * weight

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


EAN13CheckDigit.EAN13_CHECK_DIGIT = EAN13CheckDigit()
