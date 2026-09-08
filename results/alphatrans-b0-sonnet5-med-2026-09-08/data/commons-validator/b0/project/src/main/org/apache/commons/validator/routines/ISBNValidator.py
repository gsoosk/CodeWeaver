from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ISBN10CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.EAN13CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
from src.main.org.apache.commons.validator.routines.CodeValidator import *
import io

# Imports End


class ISBNValidator:

    # Class Fields Begin
    __ISBN_VALIDATOR: "ISBNValidator" = None
    __ISBN_VALIDATOR_NO_CONVERT: "ISBNValidator" = None
    __isbn10Validator: CodeValidator = None
    __isbn13Validator: CodeValidator = None
    __convert: bool = None
    __ISBN_10_LEN: int = 10
    __serialVersionUID: int = 4319515687976420405
    __SEP: str = r"(?:\-|\s)"
    __GROUP: str = r"(\d{1,5})"
    __PUBLISHER: str = r"(\d{1,7})"
    __TITLE: str = r"(\d{1,6})"
    ISBN10_REGEX: str = (
        r"^(?:(\d{9}[0-9X])|(?:" + __GROUP + __SEP + __PUBLISHER + __SEP + __TITLE + __SEP + "([0-9X])))$"
    )
    ISBN13_REGEX: str = (
        r"^(978|979)(?:(\d{10})|(?:"
        + __SEP
        + __GROUP
        + __SEP
        + __PUBLISHER
        + __SEP
        + __TITLE
        + __SEP
        + "([0-9])))$"
    )
    # Class Fields End

    # Class Methods Begin
    def convertToISBN13(self, isbn10: str) -> str:
        if isbn10 is None:
            return None
        input_ = isbn10.strip()
        if len(input_) != ISBNValidator.__ISBN_10_LEN:
            raise ValueError("Invalid length " + str(len(input_)) + " for '" + input_ + "'")
        isbn13 = "978" + input_[0 : ISBNValidator.__ISBN_10_LEN - 1]
        try:
            checkDigit = self.__isbn13Validator.getCheckDigit().calculate(isbn13)
            isbn13 += checkDigit
            return isbn13
        except CheckDigitException as e:
            raise ValueError("Check digit error for '" + input_ + "' - " + str(e))

    def validateISBN13(self, code: str) -> str:
        result = self.__isbn13Validator.validate(code)
        return None if result is None else str(result)

    def validateISBN10(self, code: str) -> str:
        result = self.__isbn10Validator.validate(code)
        return None if result is None else str(result)

    def validate(self, code: str) -> str:
        result = self.validateISBN13(code)
        if result is None:
            result = self.validateISBN10(code)
            if result is not None and self.__convert:
                result = self.convertToISBN13(result)
        return result

    def isValidISBN13(self, code: str) -> bool:
        return self.__isbn13Validator.isValid(code)

    def isValidISBN10(self, code: str) -> bool:
        return self.__isbn10Validator.isValid(code)

    def isValid(self, code: str) -> bool:
        return self.isValidISBN13(code) or self.isValidISBN10(code)

    @staticmethod
    def ISBNValidator1() -> "ISBNValidator":
        return ISBNValidator(True)

    def __init__(self, convert: bool) -> None:
        self.__convert = convert
        self.__isbn10Validator = CodeValidator.CodeValidator4(
            ISBNValidator.ISBN10_REGEX, 10, ISBN10CheckDigit.ISBN10_CHECK_DIGIT
        )
        self.__isbn13Validator = CodeValidator.CodeValidator4(
            ISBNValidator.ISBN13_REGEX, 13, EAN13CheckDigit.EAN13_CHECK_DIGIT
        )

    @staticmethod
    def getInstance1(convert: bool) -> "ISBNValidator":
        return ISBNValidator.__ISBN_VALIDATOR if convert else ISBNValidator.__ISBN_VALIDATOR_NO_CONVERT

    @staticmethod
    def getInstance0() -> "ISBNValidator":
        return ISBNValidator.__ISBN_VALIDATOR

    # Class Methods End


ISBNValidator._ISBNValidator__ISBN_VALIDATOR = ISBNValidator.ISBNValidator1()
ISBNValidator._ISBNValidator__ISBN_VALIDATOR_NO_CONVERT = ISBNValidator(False)
