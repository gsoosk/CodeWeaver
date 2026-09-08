from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import os
import typing
from typing import *
import numbers
import io

# Imports End


class ABANumberCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = None
    ABAN_CHECK_DIGIT: CheckDigit = None
    __POSITION_WEIGHT: typing.List[int] = [3, 1, 7]
    # Class Fields End

    # Class Methods Begin
    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        weight = ABANumberCheckDigit.__POSITION_WEIGHT[rightPos % 3]
        return charValue * weight

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


ABANumberCheckDigit.ABAN_CHECK_DIGIT = ABANumberCheckDigit()
