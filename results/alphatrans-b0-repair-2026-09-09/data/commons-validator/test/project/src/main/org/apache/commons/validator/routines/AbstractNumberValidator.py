from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import *
import typing
from typing import *
import numbers
import io
import re
import decimal
from abc import ABC

# Imports End


_LOCALE_NUMBER_SYMBOLS = {
    'en': ('.', ',', '$'),
    'en_US': ('.', ',', '$'),
    'en_GB': ('.', ',', '\u00a3'),
    'en_CA': ('.', ',', '$'),
    'de': (',', '.', '\u20ac'),
    'de_DE': (',', '.', '\u20ac'),
    'fr': (',', '\u00a0', '\u20ac'),
    'fr_FR': (',', '\u00a0', '\u20ac'),
}

_DEFAULT_SYMBOLS = ('.', ',', '$')


def _locale_key(locale: typing.Any) -> typing.Optional[str]:
    if locale is None:
        return None
    language = getattr(locale, 'language', None)
    country = getattr(locale, 'country', None)
    if language is None and hasattr(locale, 'getLanguage'):
        try:
            language = locale.getLanguage()
        except Exception:
            language = None
    if country is None and hasattr(locale, 'getCountry'):
        try:
            country = locale.getCountry()
        except Exception:
            country = None
    if language is None and isinstance(locale, str):
        parts = locale.replace('-', '_').split('_')
        language = parts[0] if len(parts) > 0 else None
        country = parts[1] if len(parts) > 1 else None

    if language and country:
        return f"{language}_{country}"
    if language:
        return language
    return None


class _NumFmt:
    """
    A lightweight stand-in for java.text.NumberFormat / DecimalFormat used
    internally by AbstractNumberValidator. It supports enough of the
    NumberFormat/DecimalFormat contract (parse, isParseIntegerOnly,
    setParseIntegerOnly, getMinimumFractionDigits, getMaximumFractionDigits,
    getMultiplier, format) to allow AbstractNumberValidator to operate.
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
        key = _locale_key(self.locale)
        if key is not None:
            symbols = _LOCALE_NUMBER_SYMBOLS.get(key)
            if symbols is None and '_' in key:
                symbols = _LOCALE_NUMBER_SYMBOLS.get(key.split('_')[0])
            if symbols is not None:
                return symbols
        return _DEFAULT_SYMBOLS

    def _match_number(
        self, value: str
    ) -> typing.Optional[typing.Tuple[str, int, bool]]:
        decimal_point, thousands_sep, currency_symbol = self._get_locale_symbols()
        n = len(value)
        i = 0
        while i < n and value[i].isspace():
            i += 1

        if currency_symbol and value[i:i + len(currency_symbol)] == currency_symbol:
            i += len(currency_symbol)
            while i < n and value[i].isspace():
                i += 1

        sign_start = i
        if i < n and value[i] in '+-':
            i += 1

        digits_start = i
        while i < n:
            if value[i].isdigit():
                i += 1
            elif (
                thousands_sep
                and value[i:i + len(thousands_sep)] == thousands_sep
                and i > digits_start
            ):
                i += len(thousands_sep)
            else:
                break

        if i == digits_start:
            return None

        frac_end = i
        if (
            not self._parse_integer_only
            and decimal_point
            and value[i:i + len(decimal_point)] == decimal_point
        ):
            j = i + len(decimal_point)
            k = j
            while k < n and value[k].isdigit():
                k += 1
            if k > j:
                frac_end = k

        end = frac_end
        is_percent = False
        if self.formatType == AbstractNumberValidator.PERCENT_FORMAT:
            m = end
            while m < n and value[m].isspace():
                m += 1
            if m < n and value[m] == '%':
                end = m + 1
                is_percent = True

        num_str = value[sign_start:frac_end]
        if thousands_sep:
            num_str = num_str.replace(thousands_sep, '')
        if decimal_point and decimal_point != '.':
            num_str = num_str.replace(decimal_point, '.')

        return num_str, end, is_percent

    def parse_with_position(self, value: str) -> typing.Tuple[typing.Any, int]:
        result = self._match_number(value)
        if result is None:
            raise ValueError("Invalid number: %s" % value)
        num_str, end, is_percent = result

        if self._parse_integer_only:
            try:
                num: typing.Any = int(num_str)
            except ValueError:
                raise ValueError("Invalid number: %s" % value)
        else:
            try:
                num = float(num_str)
            except ValueError:
                raise ValueError("Invalid number: %s" % value)
            if self.formatType == AbstractNumberValidator.PERCENT_FORMAT and (
                is_percent or self.multiplier == 100
            ):
                num = num / 100.0

        return num, end

    def parse(self, value: str) -> typing.Union[int, float]:
        num, _ = self.parse_with_position(value)
        return num

    def format(self, value: typing.Any) -> str:
        decimal_point, thousands_sep, currency_symbol = self._get_locale_symbols()

        if isinstance(value, bool):
            working: typing.Any = int(value)
        else:
            working = value

        is_percent = self.formatType == AbstractNumberValidator.PERCENT_FORMAT
        if is_percent:
            try:
                working = working * 100
            except Exception:
                pass

        if self.pattern:
            min_frac = self.minimum_fraction_digits
            max_frac = self.maximum_fraction_digits
        elif self.formatType == AbstractNumberValidator.CURRENCY_FORMAT:
            min_frac = 2
            max_frac = 2
        elif is_percent:
            min_frac = 0
            max_frac = 0
        else:
            min_frac = self.minimum_fraction_digits
            max_frac = self.maximum_fraction_digits

        if isinstance(working, decimal.Decimal):
            dec = working
        elif isinstance(working, float):
            dec = decimal.Decimal(str(working))
        else:
            try:
                dec = decimal.Decimal(int(working))
            except Exception:
                dec = decimal.Decimal(str(working))

        if max_frac > 0:
            quantizer = decimal.Decimal(1).scaleb(-max_frac)
        else:
            quantizer = decimal.Decimal(1)
        dec = dec.quantize(quantizer, rounding=decimal.ROUND_HALF_UP)

        s = format(dec, "f")

        neg = s.startswith("-")
        if neg:
            s = s[1:]

        if "." in s:
            int_part, frac_part = s.split(".", 1)
        else:
            int_part, frac_part = s, ""

        while len(frac_part) > min_frac and frac_part.endswith("0"):
            frac_part = frac_part[:-1]
        while len(frac_part) < min_frac:
            frac_part += "0"

        if thousands_sep:
            groups = []
            remaining = int_part
            while len(remaining) > 3:
                groups.insert(0, remaining[-3:])
                remaining = remaining[:-3]
            groups.insert(0, remaining)
            int_part = thousands_sep.join(groups)

        if frac_part:
            result = int_part + decimal_point + frac_part
        else:
            result = int_part

        if neg:
            result = "-" + result

        if self.formatType == AbstractNumberValidator.CURRENCY_FORMAT and currency_symbol:
            result = currency_symbol + result
        if is_percent:
            result = result + "%"

        return result


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
        return self._parseFormatted(value, formatter)

    def _parseFormatted(self, value: str, formatter: Format) -> typing.Any:
        try:
            if hasattr(formatter, "parse_with_position"):
                parsed_value, end = formatter.parse_with_position(value)
                if self.isStrict() and end < len(value):
                    return None
            else:
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
