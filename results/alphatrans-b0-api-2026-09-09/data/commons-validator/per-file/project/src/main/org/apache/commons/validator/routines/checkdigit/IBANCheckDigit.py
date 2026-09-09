from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import io

# Imports End


def _get_numeric_value(ch: str) -> int:
    if ch.isdigit():
        return int(ch)
    if ch.isalpha():
        upper = ch.upper()
        if 'A' <= upper <= 'Z':
            return ord(upper) - ord('A') + 10
    return -1


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
        modulus_result = self.__calculateModulus(code)
        char_value = 98 - modulus_result
        check_digit = str(char_value)
        return check_digit if char_value > 9 else "0" + check_digit

    def isValid(self, code: str) -> bool:
        if code is None or len(code) < IBANCheckDigit.__MIN_CODE_LEN:
            return False
        check = code[2:4]
        if check in ("00", "01", "99"):
            return False
        try:
            modulus_result = self.__calculateModulus(code)
            return modulus_result == 1
        except CheckDigitException:
            return False

    def __init__(self) -> None:
        pass

    def __calculateModulus(self, code: str) -> int:
        reformatted_code = code[4:] + code[0:4]
        total = 0
        for i, ch in enumerate(reformatted_code):
            char_value = _get_numeric_value(ch)
            if char_value < 0 or char_value > IBANCheckDigit.__MAX_ALPHANUMERIC_VALUE:
                raise CheckDigitException.CheckDigitException1(
                    "Invalid Character[" + str(i) + "] = '" + str(char_value) + "'"
                )
            total = (total * 100 if char_value > 9 else total * 10) + char_value
            if total > IBANCheckDigit.__MAX:
                total = total % IBANCheckDigit.__MODULUS
        return int(total % IBANCheckDigit.__MODULUS)

    # Class Methods End


IBANCheckDigit.IBAN_CHECK_DIGIT = IBANCheckDigit()
