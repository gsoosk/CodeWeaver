from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.BigDecimalValidator import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import (
    _NumberFormat,
)
import locale
import typing
from typing import *
import io

# Imports End


class CurrencyValidator(BigDecimalValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: CurrencyValidator = None
    __CURRENCY_SYMBOL: str = "\u00A4"
    # Class Fields End

    # Class Methods Begin
    def _parse(self, value: str, formatter: Format) -> typing.Any:
        parsed_value = AbstractFormatValidator._parse(self, value, formatter)
        if parsed_value is not None or not isinstance(formatter, _NumberFormat):
            return parsed_value

        symbol = getattr(formatter, "currency_symbol_used", None)
        if not symbol:
            return parsed_value

        stripped = formatter.strip_affix_char(symbol)
        parsed_value = AbstractFormatValidator._parse(self, value, stripped)
        return parsed_value

    @staticmethod
    def CurrencyValidator1() -> CurrencyValidator:
        return CurrencyValidator(True, True)

    def __init__(self, strict: bool, allowFractions: bool) -> None:
        BigDecimalValidator.__init__(
            self, strict, AbstractNumberValidator.CURRENCY_FORMAT, allowFractions
        )

    @staticmethod
    def getInstance() -> BigDecimalValidator:
        return CurrencyValidator.__VALIDATOR

    # Class Methods End


CurrencyValidator._CurrencyValidator__VALIDATOR = CurrencyValidator.CurrencyValidator1()
