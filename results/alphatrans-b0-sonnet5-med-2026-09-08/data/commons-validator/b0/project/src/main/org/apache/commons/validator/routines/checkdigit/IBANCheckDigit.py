from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import io


def _numeric_value(character: str) -> int:
    if character.isdigit():
        return int(character)
    if character.isalpha():
        return ord(character.upper()) - ord("A") + 10
    return -1

# Imports End


class IBANCheckDigit(CheckDigit):

    # Class Fields Begin
    __MIN_CODE_LEN: int = 5
    __serialVersionUID: int = -3600191725934382801
    __MAX_ALPHANUMERIC_VALUE: int = 35
    IBAN_CHECK_DIGIT: CheckDigit = None
    __MAX: int = 999999999
    __MODULUS: int = 97
    # Class Fields End

    # Class Methods Begin
    def calculate(self, code: str) -> str:
        if code is None or len(code) < IBANCheckDigit.__MIN_CODE_LEN:
            raise CheckDigitException.CheckDigitException1(
                "Invalid Code length=" + str(0 if code is None else len(code))
            )
        code = code[0:2] + "00" + code[4:]
        modulusResult = self.__calculateModulus(code)
        charValue = 98 - modulusResult
        checkDigit = str(charValue)
        return checkDigit if charValue > 9 else "0" + checkDigit

    def isValid(self, code: str) -> bool:
        if code is None or len(code) < IBANCheckDigit.__MIN_CODE_LEN:
            return False
        check = code[2:4]
        if check in ("00", "01", "99"):
            return False
        try:
            modulusResult = self.__calculateModulus(code)
            return modulusResult == 1
        except CheckDigitException:
            return False

    def __init__(self) -> None:
        pass

    def __calculateModulus(self, code: str) -> int:
        reformattedCode = code[4:] + code[0:4]
        total = 0
        for i in range(len(reformattedCode)):
            charValue = _numeric_value(reformattedCode[i])
            if charValue < 0 or charValue > IBANCheckDigit.__MAX_ALPHANUMERIC_VALUE:
                raise CheckDigitException.CheckDigitException1(
                    "Invalid Character[" + str(i) + "] = '" + str(charValue) + "'"
                )
            total = (total * 100 if charValue > 9 else total * 10) + charValue
            if total > IBANCheckDigit.__MAX:
                total = total % IBANCheckDigit.__MODULUS
        return total % IBANCheckDigit.__MODULUS

    # Class Methods End


IBANCheckDigit.IBAN_CHECK_DIGIT = IBANCheckDigit()
