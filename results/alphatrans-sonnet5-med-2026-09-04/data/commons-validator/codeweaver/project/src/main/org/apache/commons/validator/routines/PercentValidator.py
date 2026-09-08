from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.BigDecimalValidator import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import (
    _NumberFormat,
)
import decimal
import typing
from typing import *
import io

# Imports End


class PercentValidator(BigDecimalValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: PercentValidator = None
    __PERCENT_SYMBOL: str = "%"
    __POINT_ZERO_ONE: decimal.Decimal = decimal.Decimal("0.01")
    # Class Fields End

    # Class Methods Begin
    def _parse(self, value: str, formatter: Format) -> typing.Any:
        parsed_value = AbstractFormatValidator._parse(self, value, formatter)
        if parsed_value is not None or not isinstance(formatter, _NumberFormat):
            return parsed_value

        symbol = getattr(formatter, "percent_symbol_used", None)
        if not symbol:
            return parsed_value

        stripped = formatter.strip_affix_char(
            symbol, reset_multiplier_if=PercentValidator.__PERCENT_SYMBOL
        )
        parsed_value = AbstractFormatValidator._parse(self, value, stripped)
        if parsed_value is not None:
            parsed_value = parsed_value * PercentValidator.__POINT_ZERO_ONE
        return parsed_value

    @staticmethod
    def PercentValidator1() -> PercentValidator:
        return PercentValidator(True)

    def __init__(self, strict: bool) -> None:
        BigDecimalValidator.__init__(
            self, strict, AbstractNumberValidator.PERCENT_FORMAT, True
        )

    @staticmethod
    def getInstance() -> BigDecimalValidator:
        return PercentValidator.__VALIDATOR

    # Class Methods End


PercentValidator._PercentValidator__VALIDATOR = PercentValidator.PercentValidator1()
