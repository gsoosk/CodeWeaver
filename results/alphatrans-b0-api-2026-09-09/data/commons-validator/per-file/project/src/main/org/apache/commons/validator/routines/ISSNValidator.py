from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ISSNCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.EAN13CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
from src.main.org.apache.commons.validator.routines.CodeValidator import *
import typing
from typing import *
import io
import re

# Imports End


class ISSNValidator:

    # Class Fields Begin
    __serialVersionUID: int = 4319515687976420405
    __ISSN_REGEX: str = r"(?:ISSN )?(\d{4})-(\d{3}[0-9X])$"
    __ISSN_LEN: int = 8
    __ISSN_PREFIX: str = "977"
    __EAN_ISSN_REGEX: str = r"^(977)(?:(\d{10}))$"
    __EAN_ISSN_LEN: int = 13
    __VALIDATOR: CodeValidator = CodeValidator.CodeValidator4(
        __ISSN_REGEX, __ISSN_LEN, ISSNCheckDigit.ISSN_CHECK_DIGIT
    )
    __EAN_VALIDATOR: CodeValidator = CodeValidator.CodeValidator4(
        __EAN_ISSN_REGEX, __EAN_ISSN_LEN, EAN13CheckDigit.EAN13_CHECK_DIGIT
    )
    __ISSN_VALIDATOR: "ISSNValidator" = None
    # Class Fields End

    # Class Methods Begin
    def extractFromEAN13(self, ean13: str) -> str:
        input_ = ean13.strip()
        if len(input_) != ISSNValidator.__EAN_ISSN_LEN:
            raise ValueError(
                "Invalid length " + str(len(input_)) + " for '" + input_ + "'"
            )
        if not input_.startswith(ISSNValidator.__ISSN_PREFIX):
            raise ValueError(
                "Prefix must be "
                + ISSNValidator.__ISSN_PREFIX
                + " to contain an ISSN: '"
                + ean13
                + "'"
            )
        result = self.validateEan(input_)
        if result is None:
            return None
        input_ = str(result)
        try:
            issn_base = input_[3:10]
            check_digit = ISSNCheckDigit.ISSN_CHECK_DIGIT.calculate(issn_base)
            issn = issn_base + check_digit
            return issn
        except CheckDigitException as e:
            raise ValueError(
                "Check digit error for '" + ean13 + "' - " + str(e)
            )

    def convertToEAN13(self, issn: str, suffix: str) -> str:
        if suffix is None or not re.match(r"^\d\d$", suffix):
            raise ValueError("Suffix must be two digits: '" + str(suffix) + "'")

        result = self.validate(issn)
        if result is None:
            return None

        input_ = str(result)
        ean13 = ISSNValidator.__ISSN_PREFIX + input_[:-1] + suffix
        try:
            check_digit = EAN13CheckDigit.EAN13_CHECK_DIGIT.calculate(ean13)
            ean13 += check_digit
            return ean13
        except CheckDigitException as e:
            raise ValueError(
                "Check digit error for '" + ean13 + "' - " + str(e)
            )

    def validate(self, code: str) -> typing.Any:
        return ISSNValidator.__VALIDATOR.validate(code)

    def isValid(self, code: str) -> bool:
        return ISSNValidator.__VALIDATOR.isValid(code)

    def validateEan(self, code: str) -> typing.Any:
        return ISSNValidator.__EAN_VALIDATOR.validate(code)

    @staticmethod
    def getInstance() -> "ISSNValidator":
        return ISSNValidator.__ISSN_VALIDATOR

    # Class Methods End


ISSNValidator._ISSNValidator__ISSN_VALIDATOR = ISSNValidator()
