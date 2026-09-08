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
    __serialVersionUID: int = None
    __VALIDATOR: BigDecimalValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        if isinstance(value, bool):
            dec = decimal.Decimal(int(value))
        elif isinstance(value, int):
            dec = decimal.Decimal(value)
        elif isinstance(value, decimal.Decimal):
            dec = value
        else:
            dec = decimal.Decimal(str(value))

        scale = self._determineScale(formatter)
        if scale >= 0:
            quant = decimal.Decimal(1).scaleb(-scale) if scale > 0 else decimal.Decimal(1)
            # As with _NumberFormat.format(), the default (28-digit) decimal
            # context is too narrow for values with a large number of
            # significant digits and would raise InvalidOperation instead of
            # quantizing them; size the context to fit every digit of ``dec``
            # plus the requested scale.
            digit_count = len(dec.as_tuple().digits)
            integer_digits = (dec.adjusted() + 1) if dec != 0 else 1
            needed_prec = max(digit_count, integer_digits) + scale + 10
            ctx = decimal.Context(prec=max(needed_prec, decimal.getcontext().prec))
            dec = dec.quantize(quant, rounding=decimal.ROUND_DOWN, context=ctx)
        return dec

    def maxValue(self, value: decimal.Decimal, max_: float) -> bool:
        return float(value) <= max_

    def minValue(self, value: decimal.Decimal, min_: float) -> bool:
        return float(value) >= min_

    def isInRange(self, value: decimal.Decimal, min_: float, max_: float) -> bool:
        return self.minValue(value, min_) and self.maxValue(value, max_)

    def validate3(
        self, value: str, pattern: str, locale: typing.Any
    ) -> decimal.Decimal:
        return AbstractNumberValidator._parse(self, value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> decimal.Decimal:
        return self.validate3(value, None, locale)

    def validate1(self, value: str, pattern: str) -> decimal.Decimal:
        return self.validate3(value, pattern, None)

    def validate0(self, value: str) -> decimal.Decimal:
        return self.validate3(value, None, None)

    @staticmethod
    def BigDecimalValidator2() -> BigDecimalValidator:
        return BigDecimalValidator.BigDecimalValidator1(True)

    @staticmethod
    def BigDecimalValidator1(strict: bool) -> BigDecimalValidator:
        return BigDecimalValidator(strict, AbstractNumberValidator.STANDARD_FORMAT, True)

    def __init__(self, strict: bool, formatType: int, allowFractions: bool) -> None:
        AbstractNumberValidator.__init__(self, strict, formatType, allowFractions)

    @staticmethod
    def getInstance() -> BigDecimalValidator:
        return BigDecimalValidator.__VALIDATOR

    # Class Methods End


BigDecimalValidator._BigDecimalValidator__VALIDATOR = BigDecimalValidator.BigDecimalValidator2()
