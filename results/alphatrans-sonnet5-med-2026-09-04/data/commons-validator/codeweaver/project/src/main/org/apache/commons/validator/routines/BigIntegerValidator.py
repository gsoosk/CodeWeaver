from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import typing
from typing import *
import numbers
import io

# Imports End


class BigIntegerValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: BigIntegerValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        return int(value)

    def maxValue(self, value: int, max_: int) -> bool:
        return int(value) <= max_

    def minValue(self, value: int, min_: int) -> bool:
        return int(value) >= min_

    def isInRange(self, value: int, min_: int, max_: int) -> bool:
        return self.minValue(value, min_) and self.maxValue(value, max_)

    def validate3(self, value: str, pattern: str, locale: typing.Any) -> int:
        return AbstractNumberValidator._parse(self, value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> int:
        return self.validate3(value, None, locale)

    def validate1(self, value: str, pattern: str) -> int:
        return self.validate3(value, pattern, None)

    def validate0(self, value: str) -> int:
        return self.validate3(value, None, None)

    @staticmethod
    def BigIntegerValidator1() -> BigIntegerValidator:
        return BigIntegerValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        AbstractNumberValidator.__init__(self, strict, formatType, False)

    @staticmethod
    def getInstance() -> BigIntegerValidator:
        return BigIntegerValidator.__VALIDATOR

    # Class Methods End


BigIntegerValidator._BigIntegerValidator__VALIDATOR = BigIntegerValidator.BigIntegerValidator1()
