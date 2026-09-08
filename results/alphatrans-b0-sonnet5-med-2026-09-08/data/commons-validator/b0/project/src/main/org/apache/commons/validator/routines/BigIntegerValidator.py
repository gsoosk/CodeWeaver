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
    __serialVersionUID: int = 6713144356347139988
    __VALIDATOR: "BigIntegerValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        return int(value)

    def maxValue(self, value: int, max_: int) -> bool:
        return value <= max_

    def minValue(self, value: int, min_: int) -> bool:
        return value >= min_

    def isInRange(self, value: int, min_: int, max_: int) -> bool:
        return value >= min_ and value <= max_

    def validate3(self, value: str, pattern: str, locale: typing.Any) -> int:
        return self._parse(value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> int:
        return self._parse(value, None, locale)

    def validate1(self, value: str, pattern: str) -> int:
        return self._parse(value, pattern, None)

    def validate0(self, value: str) -> int:
        return self._parse(value, None, None)

    @staticmethod
    def BigIntegerValidator1() -> "BigIntegerValidator":
        return BigIntegerValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        super().__init__(strict, formatType, False)

    @staticmethod
    def getInstance() -> "BigIntegerValidator":
        return BigIntegerValidator.__VALIDATOR

    # Class Methods End


BigIntegerValidator._BigIntegerValidator__VALIDATOR = BigIntegerValidator.BigIntegerValidator1()
