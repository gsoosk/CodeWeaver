from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import typing
from typing import *
import io

# Imports End


class DoubleValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: DoubleValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        return float(value)

    def isInRange1(self, value: float, min_: float, max_: float) -> bool:
        return self.isInRange0(float(value), min_, max_)

    def isInRange0(self, value: float, min_: float, max_: float) -> bool:
        return min_ <= value <= max_

    def minValue1(self, value: float, min_: float) -> bool:
        return self.minValue0(float(value), min_)

    def minValue0(self, value: float, min_: float) -> bool:
        return value >= min_

    def maxValue1(self, value: float, max_: float) -> bool:
        return self.maxValue0(float(value), max_)

    def maxValue0(self, value: float, max_: float) -> bool:
        return value <= max_

    def validate3(self, value: str, pattern: str, locale: typing.Any) -> float:
        return AbstractNumberValidator._parse(self, value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> float:
        return self.validate3(value, None, locale)

    def validate1(self, value: str, pattern: str) -> float:
        return self.validate3(value, pattern, None)

    def validate0(self, value: str) -> float:
        return self.validate3(value, None, None)

    @staticmethod
    def DoubleValidator1() -> DoubleValidator:
        return DoubleValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        AbstractNumberValidator.__init__(self, strict, formatType, True)

    @staticmethod
    def getInstance() -> DoubleValidator:
        return DoubleValidator.__VALIDATOR

    # Class Methods End


DoubleValidator._DoubleValidator__VALIDATOR = DoubleValidator.DoubleValidator1()
