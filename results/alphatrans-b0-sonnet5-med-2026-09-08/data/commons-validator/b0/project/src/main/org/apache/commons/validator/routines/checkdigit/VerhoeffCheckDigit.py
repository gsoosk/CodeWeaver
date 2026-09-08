from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import typing
from typing import *
import io

# Imports End


class VerhoeffCheckDigit(CheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = 4138993995483695178
    VERHOEFF_CHECK_DIGIT: CheckDigit = None
    __D_TABLE: typing.List[typing.List[int]] = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
    ]
    __P_TABLE: typing.List[typing.List[int]] = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
    ]
    __INV_TABLE: typing.List[int] = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
    # Class Fields End

    # Class Methods Begin
    def calculate(self, code: str) -> str:
        if code is None or len(code) == 0:
            raise CheckDigitException.CheckDigitException1("Code is missing")
        checksum = self.__calculateChecksum(code, False)
        return str(VerhoeffCheckDigit.__INV_TABLE[checksum])

    def isValid(self, code: str) -> bool:
        if code is None or len(code) == 0:
            return False
        try:
            return self.__calculateChecksum(code, True) == 0
        except CheckDigitException:
            return False

    def __calculateChecksum(self, code: str, includesCheckDigit: bool) -> int:
        checksum = 0
        for i in range(len(code)):
            idx = len(code) - (i + 1)
            ch = code[idx]
            if not ch.isdigit():
                raise CheckDigitException.CheckDigitException1(
                    "Invalid Character[" + str(i) + "] = '" + str(ord(ch)) + "'"
                )
            num = int(ch)
            pos = i if includesCheckDigit else i + 1
            checksum = VerhoeffCheckDigit.__D_TABLE[checksum][VerhoeffCheckDigit.__P_TABLE[pos % 8][num]]
        return checksum

    # Class Methods End


VerhoeffCheckDigit.VERHOEFF_CHECK_DIGIT = VerhoeffCheckDigit()
