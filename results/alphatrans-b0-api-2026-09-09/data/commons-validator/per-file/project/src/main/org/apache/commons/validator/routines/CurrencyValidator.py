from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.BigDecimalValidator import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import typing
from typing import *
import io

# Imports End


class CurrencyValidator(BigDecimalValidator):

    # Class Fields Begin
    __serialVersionUID: int = -4201640771171486514
    __VALIDATOR: "CurrencyValidator" = None
    __CURRENCY_SYMBOL: str = '\u00A4'
    # Class Fields End

    # Class Methods Begin
    def _parse(self, value: str, formatter) -> typing.Any:
        parsedValue = super()._parse(value, formatter)
        if parsedValue is not None or not hasattr(formatter, "toPattern"):
            return parsedValue

        pattern = formatter.toPattern()
        if CurrencyValidator.__CURRENCY_SYMBOL in pattern:
            buffer = io.StringIO()
            for ch in pattern:
                if ch != CurrencyValidator.__CURRENCY_SYMBOL:
                    buffer.write(ch)
            formatter.applyPattern(buffer.getvalue())
            parsedValue = super()._parse(value, formatter)
        return parsedValue

    @staticmethod
    def CurrencyValidator1() -> "CurrencyValidator":
        return CurrencyValidator(True, True)

    def __init__(self, strict: bool, allowFractions: bool) -> None:
        super().__init__(strict, AbstractNumberValidator.CURRENCY_FORMAT, allowFractions)

    @staticmethod
    def getInstance() -> BigDecimalValidator:
        return CurrencyValidator.__VALIDATOR

    # Class Methods End


CurrencyValidator._CurrencyValidator__VALIDATOR = CurrencyValidator.CurrencyValidator1()
