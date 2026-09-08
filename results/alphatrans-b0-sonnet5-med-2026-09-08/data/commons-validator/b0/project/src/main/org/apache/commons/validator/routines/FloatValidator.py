from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import typing
from typing import *
import numbers
import io

# Imports End


_FLOAT_MAX = 3.4028235e38
_FLOAT_MIN = 1.4e-45


class FloatValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = -4513245432806414267
    __VALIDATOR: "FloatValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        doubleValue = float(value)
        if doubleValue > 0:
            if doubleValue < _FLOAT_MIN:
                return None
            if doubleValue > _FLOAT_MAX:
                return None
        elif doubleValue < 0:
            posDouble = doubleValue * -1
            if posDouble < _FLOAT_MIN:
                return None
            if posDouble > _FLOAT_MAX:
                return None
        return doubleValue

    def maxValue1(self, value: float, max_: float) -> bool:
        return self.maxValue0(value, max_)

    def maxValue0(self, value: float, max_: float) -> bool:
        return value <= max_

    def minValue1(self, value: float, min_: float) -> bool:
        return self.minValue0(value, min_)

    def minValue0(self, value: float, min_: float) -> bool:
        return value >= min_

    def isInRange1(self, value: float, min_: float, max_: float) -> bool:
        return self.isInRange0(value, min_, max_)

    def isInRange0(self, value: float, min_: float, max_: float) -> bool:
        return value >= min_ and value <= max_

    def validate3(self, value: str, pattern: str, locale: typing.Any) -> float:
        return self._parse(value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> float:
        return self._parse(value, None, locale)

    def validate1(self, value: str, pattern: str) -> float:
        return self._parse(value, pattern, None)

    def validate0(self, value: str) -> float:
        return self._parse(value, None, None)

    @staticmethod
    def FloatValidator1() -> "FloatValidator":
        return FloatValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        super().__init__(strict, formatType, True)

    @staticmethod
    def getInstance() -> "FloatValidator":
        return FloatValidator.__VALIDATOR

    # Class Methods End


FloatValidator._FloatValidator__VALIDATOR = FloatValidator.FloatValidator1()
