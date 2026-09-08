from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ModulusCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
import os
import typing
from typing import *
import io

# Imports End


class ModulusTenCheckDigit(ModulusCheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = -3752929983453368497
    __postitionWeight: typing.List[int] = None
    __useRightPos: bool = None
    __sumWeightedDigits: bool = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        return (
            type(self).__name__
            + "[postitionWeight="
            + str(self.__postitionWeight)
            + ", useRightPos="
            + str(self.__useRightPos)
            + ", sumWeightedDigits="
            + str(self.__sumWeightedDigits)
            + "]"
        )

    def __str__(self) -> str:
        return self.toString()

    def _weightedValue(self, charValue: int, leftPos: int, rightPos: int) -> int:
        pos = rightPos if self.__useRightPos else leftPos
        weight = self.__postitionWeight[(pos - 1) % len(self.__postitionWeight)]
        weightedValue = charValue * weight
        if self.__sumWeightedDigits:
            weightedValue = ModulusCheckDigit.sumDigits(weightedValue)
        return weightedValue

    def _toInt(self, character: str, leftPos: int, rightPos: int) -> int:
        num = int(character) if character.isdigit() else -1
        if num < 0:
            raise CheckDigitException.CheckDigitException1(
                "Invalid Character[" + str(leftPos) + "] = '" + character + "'"
            )
        return num

    def isValid(self, code: str) -> bool:
        if code is None or len(code) == 0:
            return False
        if not code[len(code) - 1].isdigit():
            return False
        return super().isValid(code)

    @staticmethod
    def ModulusTenCheckDigit2(postitionWeight: typing.List[int]) -> "ModulusTenCheckDigit":
        return ModulusTenCheckDigit(postitionWeight, False, False)

    @staticmethod
    def ModulusTenCheckDigit1(
        postitionWeight: typing.List[int], useRightPos: bool
    ) -> "ModulusTenCheckDigit":
        return ModulusTenCheckDigit(postitionWeight, useRightPos, False)

    def __init__(
        self,
        postitionWeight: typing.List[int],
        useRightPos: bool,
        sumWeightedDigits: bool,
    ) -> None:
        super().__init__(10)
        self.__postitionWeight = list(postitionWeight)
        self.__useRightPos = useRightPos
        self.__sumWeightedDigits = sumWeightedDigits

    # Class Methods End
