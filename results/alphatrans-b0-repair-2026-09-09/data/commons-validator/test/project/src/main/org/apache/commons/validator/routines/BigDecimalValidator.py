from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import decimal
import typing
from typing import *
import numbers
import io

# Imports End


class BigDecimalValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = -670320911490506772
    __VALIDATOR: "BigDecimalValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        if isinstance(value, int) and not isinstance(value, bool):
            dec = decimal.Decimal(value)
        else:
            dec = decimal.Decimal(str(value))

        scale = self._determineScale(formatter)
        if scale >= 0:
            quantizer = decimal.Decimal(1).scaleb(-scale)
            dec = dec.quantize(quantizer, rounding=decimal.ROUND_DOWN)

        return dec

    def maxValue(self, value: decimal.Decimal, max_: float) -> bool:
        return float(value) <= max_

    def minValue(self, value: decimal.Decimal, min_: float) -> bool:
        return float(value) >= min_

    def isInRange(self, value: decimal.Decimal, min_: float, max_: float) -> bool:
        v = float(value)
        return v >= min_ and v <= max_

    def validate3(
        self, value: str, pattern: str, locale: typing.Any
    ) -> decimal.Decimal:
        return self._parse(value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> decimal.Decimal:
        return self._parse(value, None, locale)

    def validate1(self, value: str, pattern: str) -> decimal.Decimal:
        return self._parse(value, pattern, None)

    def validate0(self, value: str) -> decimal.Decimal:
        return self._parse(value, None, None)

    @staticmethod
    def BigDecimalValidator2() -> "BigDecimalValidator":
        return BigDecimalValidator.BigDecimalValidator1(True)

    @staticmethod
    def BigDecimalValidator1(strict: bool) -> "BigDecimalValidator":
        return BigDecimalValidator(strict, AbstractNumberValidator.STANDARD_FORMAT, True)

    def __init__(self, strict: bool, formatType: int, allowFractions: bool) -> None:
        super().__init__(strict, formatType, allowFractions)

    @staticmethod
    def getInstance() -> "BigDecimalValidator":
        return BigDecimalValidator.__VALIDATOR

    # Class Methods End


BigDecimalValidator._BigDecimalValidator__VALIDATOR = BigDecimalValidator.BigDecimalValidator2()
