from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import typing
from typing import *
import numbers
import io

# Imports End


SHORT_MIN_VALUE = -32768
SHORT_MAX_VALUE = 32767


class ShortValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = -5227510699747787066
    __VALIDATOR: 'ShortValidator' = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        long_value = int(value)

        if long_value < SHORT_MIN_VALUE or long_value > SHORT_MAX_VALUE:
            return None
        return long_value

    def maxValue1(self, value: int, max_: int) -> bool:
        return self.maxValue0(value, max_)

    def maxValue0(self, value: int, max_: int) -> bool:
        return value <= max_

    def minValue1(self, value: int, min_: int) -> bool:
        return self.minValue0(value, min_)

    def minValue0(self, value: int, min_: int) -> bool:
        return value >= min_

    def isInRange1(self, value: int, min_: int, max_: int) -> bool:
        return self.isInRange0(value, min_, max_)

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
    def ShortValidator1() -> 'ShortValidator':
        return ShortValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        super().__init__(strict, formatType, False)

    @staticmethod
    def getInstance() -> 'ShortValidator':
        return ShortValidator.__VALIDATOR

    # Class Methods End


ShortValidator._ShortValidator__VALIDATOR = ShortValidator.ShortValidator1()
