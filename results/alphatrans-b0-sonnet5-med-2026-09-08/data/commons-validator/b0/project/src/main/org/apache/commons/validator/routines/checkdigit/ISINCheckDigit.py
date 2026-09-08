from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import os
import typing
from typing import *
import io


def _numeric_value(character: str) -> int:
    if character.isdigit():
        return int(character)
    if character.isalpha():
        return ord(character.upper()) - ord("A") + 10
    return -1

# Imports End


class ISINCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = -1239211208101323599
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
        transformed = io.StringIO()
        if includesCheckDigit:
            checkDigit = code[len(code) - 1]
            if not checkDigit.isdigit():
                raise CheckDigitException.CheckDigitException1(
                    "Invalid checkdigit[" + checkDigit + "] in " + code
                )
        for i in range(len(code)):
            charValue = _numeric_value(code[i])
            if charValue < 0 or charValue > ISINCheckDigit.__MAX_ALPHANUMERIC_VALUE:
                raise CheckDigitException.CheckDigitException1(
                    "Invalid Character[" + str(i + 1) + "] = '" + str(charValue) + "'"
                )
            transformed.write(str(charValue))
        return super()._calculateModulus(transformed.getvalue(), includesCheckDigit)

    def __init__(self) -> None:
        super().__init__(10)

    # Class Methods End


ISINCheckDigit.ISIN_CHECK_DIGIT = ISINCheckDigit()
