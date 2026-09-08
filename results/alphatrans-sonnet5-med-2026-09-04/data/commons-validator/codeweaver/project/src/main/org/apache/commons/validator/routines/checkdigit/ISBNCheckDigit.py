from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ISBN10CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.EAN13CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
import io

# Imports End


class ISBNCheckDigit(CheckDigit):

    # Class Fields Begin
    __serialVersionUID: int = None
    ISBN10_CHECK_DIGIT: CheckDigit = None
    ISBN13_CHECK_DIGIT: CheckDigit = None
    ISBN_CHECK_DIGIT: CheckDigit = None
    # Class Fields End

    # Class Methods Begin
    def isValid(self, code: str) -> bool:
        if code is None:
            return False
        elif len(code) == 10:
            return ISBNCheckDigit.ISBN10_CHECK_DIGIT.isValid(code)
        elif len(code) == 13:
            return ISBNCheckDigit.ISBN13_CHECK_DIGIT.isValid(code)
        else:
            return False

    def calculate(self, code: str) -> str:
        if code is None or len(code) == 0:
            raise CheckDigitException.CheckDigitException1("ISBN Code is missing")
        elif len(code) == 9:
            return ISBNCheckDigit.ISBN10_CHECK_DIGIT.calculate(code)
        elif len(code) == 12:
            return ISBNCheckDigit.ISBN13_CHECK_DIGIT.calculate(code)
        else:
            raise CheckDigitException.CheckDigitException1(
                "Invalid ISBN Length = " + str(len(code))
            )

    # Class Methods End


ISBNCheckDigit.ISBN10_CHECK_DIGIT = ISBN10CheckDigit.ISBN10_CHECK_DIGIT
ISBNCheckDigit.ISBN13_CHECK_DIGIT = EAN13CheckDigit.EAN13_CHECK_DIGIT
ISBNCheckDigit.ISBN_CHECK_DIGIT = ISBNCheckDigit()
