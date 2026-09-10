from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.BigDecimalValidator import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import decimal
import typing
from typing import *
import io

# Imports End


class PercentValidator(BigDecimalValidator):

    # Class Fields Begin
    __serialVersionUID: int = -3508241924961535772
    __VALIDATOR: 'PercentValidator' = None
    __PERCENT_SYMBOL: str = '%'
    __POINT_ZERO_ONE: decimal.Decimal = decimal.Decimal("0.01")
    # Class Fields End

    # Class Methods Begin
    def _parseFormatted(self, value: str, formatter: Format) -> typing.Any:
        parsedValue = super()._parseFormatted(value, formatter)
        if parsedValue is not None or not hasattr(formatter, "toPattern"):
            return parsedValue

        decimalFormat = formatter
        pattern = decimalFormat.toPattern()
        if pattern.find(PercentValidator.__PERCENT_SYMBOL) >= 0:
            buffer = io.StringIO()
            for ch in pattern:
                if ch != PercentValidator.__PERCENT_SYMBOL:
                    buffer.write(ch)
            decimalFormat.applyPattern(buffer.getvalue())
            parsedValue = super()._parseFormatted(value, decimalFormat)

            if parsedValue is not None:
                parsedValue = parsedValue * PercentValidator.__POINT_ZERO_ONE
        return parsedValue

    @staticmethod
    def PercentValidator1() -> 'PercentValidator':
        return PercentValidator(True)

    def __init__(self, strict: bool) -> None:
        super().__init__(strict, AbstractNumberValidator.PERCENT_FORMAT, True)

    @staticmethod
    def getInstance() -> BigDecimalValidator:
        return PercentValidator.__VALIDATOR

    # Class Methods End


PercentValidator._PercentValidator__VALIDATOR = PercentValidator.PercentValidator1()
