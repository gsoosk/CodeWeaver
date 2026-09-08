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


class ISINCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = None
    __MAX_ALPHANUMERIC_VALUE: int = 35
    ISIN_CHECK_DIGIT: CheckDigit = None
    __POSITION_WEIGHT: typing.List[int] = [2, 1]
    # Class Fields End

    # Class Methods Begin
    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        weight = ISINCheckDigit.__POSITION_WEIGHT[rightPos % 2]
        weightedValue = charValue * weight
        return ModulusCheckDigit.sumDigits(weightedValue)

    def _calculateModulus(self, code: str, includesCheckDigit: bool) -> int:
        transformed = []
        if includesCheckDigit:
            checkDigit = code[-1]
            if not checkDigit.isdigit():
                raise CheckDigitException.CheckDigitException1(
                    "Invalid checkdigit[" + checkDigit + "] in " + code
                )
        for i in range(len(code)):
            try:
                charValue = int(code[i], 36)
            except ValueError:
                charValue = -1
            if charValue < 0 or charValue > ISINCheckDigit.__MAX_ALPHANUMERIC_VALUE:
                raise CheckDigitException.CheckDigitException1(
                    "Invalid Character[" + str(i + 1) + "] = '" + str(charValue) + "'"
                )
            transformed.append(str(charValue))
        return super()._calculateModulus("".join(transformed), includesCheckDigit)

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


ISINCheckDigit.ISIN_CHECK_DIGIT = ISINCheckDigit()
