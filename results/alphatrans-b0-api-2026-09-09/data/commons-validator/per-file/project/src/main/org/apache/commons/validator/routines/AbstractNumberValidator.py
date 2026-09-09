from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import *
import typing
from typing import *
import numbers
import io
import re
import locale as _locale_module
from abc import ABC

# Imports End


class _NumFmt:
    """
    A lightweight stand-in for java.text.NumberFormat / DecimalFormat used
    internally by AbstractNumberValidator. It supports enough of the
    NumberFormat/DecimalFormat contract (parse, isParseIntegerOnly,
    setParseIntegerOnly, getMinimumFractionDigits, getMaximumFractionDigits,
    getMultiplier) to allow AbstractNumberValidator to operate.
    """

    def __init__(
        self,
        formatType: int,
        pattern: typing.Optional[str] = None,
        locale: typing.Any = None,
    ) -> None:
        self.formatType = formatType
        self.pattern = pattern
        self.locale = locale
        self._parse_integer_only = False
        self._is_decimal_format = pattern is not None

        if formatType == AbstractNumberValidator.PERCENT_FORMAT:
            self.multiplier = 100
            self.minimum_fraction_digits = 0
            self.maximum_fraction_digits = 0
        elif formatType == AbstractNumberValidator.CURRENCY_FORMAT:
            self.multiplier = 1
            self.minimum_fraction_digits = 2
            self.maximum_fraction_digits = 2
        else:
            self.multiplier = 1
            self.minimum_fraction_digits = 0
            self.maximum_fraction_digits = 3

        if pattern:
            self._parse_pattern(pattern)

    def _parse_pattern(self, pattern: str) -> None:
        if "%" in pattern:
            self.multiplier = 100
        # Only consider the positive sub-pattern
        sub_pattern = pattern.split(";")[0]
        if "." in sub_pattern:
            frac_part = sub_pattern.split(".", 1)[1]
            # Strip anything that isn't part of the fraction digit spec
            frac_chars = [c for c in frac_part if c in "0#"]
            self.minimum_fraction_digits = sum(1 for c in frac_part if c == "0")
            self.maximum_fraction_digits = len(frac_chars)
        else:
            self.minimum_fraction_digits = 0
            self.maximum_fraction_digits = 0

    def isParseIntegerOnly(self) -> bool:
        return self._parse_integer_only

    def setParseIntegerOnly(self, value: bool) -> None:
        self._parse_integer_only = value

    def getMinimumFractionDigits(self) -> int:
        return self.minimum_fraction_digits

    def getMaximumFractionDigits(self) -> int:
        return self.maximum_fraction_digits

    def getMultiplier(self) -> int:
        return self.multiplier

    def isDecimalFormat(self) -> bool:
        return self._is_decimal_format

    def _get_locale_symbols(self) -> typing.Tuple[str, str, str]:
        decimal_point = "."
        thousands_sep = ","
        currency_symbol = ""
        if self.locale is not None:
            saved = None
            try:
                saved = _locale_module.setlocale(_locale_module.LC_ALL)
                _locale_module.setlocale(_locale_module.LC_ALL, str(self.locale))
            except Exception:
                saved = None
            try:
                conv = _locale_module.localeconv()
                decimal_point = conv.get("decimal_point") or decimal_point
                thousands_sep = conv.get("thousands_sep") or thousands_sep
                currency_symbol = (
                    conv.get("currency_symbol")
                    or conv.get("int_curr_symbol")
                    or currency_symbol
                )
            finally:
                if saved is not None:
                    try:
                        _locale_module.setlocale(_locale_module.LC_ALL, saved)
                    except Exception:
                        pass
        return decimal_point, thousands_sep, currency_symbol

    def parse(self, value: str) -> typing.Union[int, float]:
        decimal_point, thousands_sep, currency_symbol = self._get_locale_symbols()

        s = value.strip()

        if currency_symbol:
            s = s.replace(currency_symbol, "")

        is_percent = "%" in s
        s = s.replace("%", "").strip()

        if thousands_sep and thousands_sep != decimal_point:
            s = s.replace(thousands_sep, "")

        if decimal_point and decimal_point != ".":
            s = s.replace(decimal_point, ".")

        s = s.strip()

        if self._parse_integer_only:
            match = re.match(r"^[+-]?\d+", s)
            if not match:
                raise ValueError("Invalid number: %s" % value)
            return int(match.group(0))

        try:
            num = float(s)
        except ValueError:
            raise ValueError("Invalid number: %s" % value)

        if (
            self.formatType == AbstractNumberValidator.PERCENT_FORMAT
            and (is_percent or self.multiplier == 100)
        ):
            num = num / 100.0

        return num


class AbstractNumberValidator(AbstractFormatValidator, ABC):

    # Class Fields Begin
    __serialVersionUID: int = -3088817875906765463
    STANDARD_FORMAT: int = 0
    CURRENCY_FORMAT: int = 1
    PERCENT_FORMAT: int = 2
    __allowFractions: bool = None
    __formatType: int = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self, strict: bool, formatType: int, allowFractions: bool) -> None:
        super().__init__(strict)
        self.__allowFractions = allowFractions
        self.__formatType = formatType

    def isAllowFractions(self) -> bool:
        return self.__allowFractions

    def getFormatType(self) -> int:
        return self.__formatType

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        parsedValue = self._parse(value, pattern, locale)
        return parsedValue is not None

    def isInRange(
        self,
        value: typing.Union[int, float, numbers.Number],
        min_: typing.Union[int, float, numbers.Number],
        max_: typing.Union[int, float, numbers.Number],
    ) -> bool:
        return self.minValue(value, min_) and self.maxValue(value, max_)

    def minValue(
        self,
        value: typing.Union[int, float, numbers.Number],
        min_: typing.Union[int, float, numbers.Number],
    ) -> bool:
        if self.isAllowFractions():
            return float(value) >= float(min_)
        return int(value) >= int(min_)

    def maxValue(
        self,
        value: typing.Union[int, float, numbers.Number],
        max_: typing.Union[int, float, numbers.Number],
    ) -> bool:
        if self.isAllowFractions():
            return float(value) <= float(max_)
        return int(value) <= int(max_)

    def _parse(self, value: str, pattern: str, locale: typing.Any) -> typing.Any:
        value = None if value is None else value.strip()
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        try:
            parsed_value = formatter.parse(value)
        except Exception:
            return None
        return self._processParsedValue(parsed_value, formatter)

    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        raise NotImplementedError

    def _getFormat(self, pattern: str, locale: typing.Any) -> Format:
        return self._getFormat0(pattern, locale)

    def _getFormat0(self, pattern: str, locale: typing.Any) -> Format:
        usePattern = pattern is not None and len(pattern) > 0
        if not usePattern:
            formatter = self._getFormat1(locale)
        else:
            formatter = _NumFmt(self.getFormatType(), pattern, locale)

        if not self.isAllowFractions():
            formatter.setParseIntegerOnly(True)
        return formatter

    def _determineScale(self, format_: typing.Any) -> int:
        if not self.isStrict():
            return -1
        if not self.isAllowFractions() or format_.isParseIntegerOnly():
            return 0
        minimumFraction = format_.getMinimumFractionDigits()
        maximumFraction = format_.getMaximumFractionDigits()
        if minimumFraction != maximumFraction:
            return -1
        scale = minimumFraction
        if hasattr(format_, "isDecimalFormat") and format_.isDecimalFormat():
            multiplier = format_.getMultiplier()
            if multiplier == 100:
                scale += 2
            elif multiplier == 1000:
                scale += 3
        elif self.__formatType == AbstractNumberValidator.PERCENT_FORMAT:
            scale += 2
        return scale

    def _getFormat1(self, locale: typing.Any) -> Format:
        formatType = self.getFormatType()
        formatter = _NumFmt(formatType, None, locale)
        if formatType == AbstractNumberValidator.STANDARD_FORMAT:
            if not self.isAllowFractions():
                formatter.setParseIntegerOnly(True)
        return formatter

    # Class Methods End
