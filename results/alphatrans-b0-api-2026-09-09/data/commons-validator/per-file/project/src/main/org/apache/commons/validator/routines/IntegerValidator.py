from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import typing
from typing import *
import numbers
import io

# Imports End


class IntegerValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = 422081746310306596
    __VALIDATOR: IntegerValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        if isinstance(value, numbers.Integral) or isinstance(value, float):
            long_value = int(value)
            if -2147483648 <= long_value <= 2147483647:
                return long_value
        return None

    def maxValue1(self, value: int, max_: int) -> bool:
        return self.maxValue0(int(value), max_)

    def maxValue0(self, value: int, max_: int) -> bool:
        return value <= max_

    def minValue1(self, value: int, min_: int) -> bool:
        return self.minValue0(int(value), min_)

    def minValue0(self, value: int, min_: int) -> bool:
        return value >= min_

    def isInRange1(self, value: int, min_: int, max_: int) -> bool:
        return self.isInRange0(int(value), min_, max_)

    def isInRange0(self, value: int, min_: int, max_: int) -> bool:
        return min_ <= value <= max_

    def validate3(self, value: str, pattern: str, locale: typing.Any) -> int:
        return self._parse(value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> int:
        return self._parse(value, None, locale)

    def validate1(self, value: str, pattern: str) -> int:
        return self._parse(value, pattern, None)

    def validate0(self, value: str) -> int:
        return self._parse(value, None, None)

    @staticmethod
    def IntegerValidator1() -> IntegerValidator:
        return IntegerValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        super().__init__(strict, formatType, False)

    @staticmethod
    def getInstance() -> IntegerValidator:
        return IntegerValidator.__VALIDATOR

    # Class Methods End


IntegerValidator._IntegerValidator__VALIDATOR = IntegerValidator.IntegerValidator1()
