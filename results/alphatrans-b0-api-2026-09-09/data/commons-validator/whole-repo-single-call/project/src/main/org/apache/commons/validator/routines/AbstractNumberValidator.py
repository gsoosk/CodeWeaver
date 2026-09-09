from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import *
import typing
from typing import *
import numbers
import io
import re as _re
from abc import ABC


class NumberFormat:
    def __init__(self, pattern=None, locale=None, format_type=0, allow_fractions=True):
        self.pattern = pattern
        self.locale = locale
        self.format_type = format_type
        self.parse_integer_only = not allow_fractions
        self.min_fraction_digits = 0
        self.max_fraction_digits = 3
        self.multiplier = 1
        if pattern:
            self._analyze_pattern(pattern)
        else:
            if format_type == 1:
                self.min_fraction_digits = 2
                self.max_fraction_digits = 2
            elif format_type == 2:
                self.min_fraction_digits = 0
                self.max_fraction_digits = 0
                self.multiplier = 100
        if not allow_fractions:
            self.parse_integer_only = True

    def _analyze_pattern(self, pattern):
        p = pattern
        if "%" in p:
            self.multiplier = 100
        if "\u2030" in p:
            self.multiplier = 1000
        if "." in p:
            frac = p.split(".", 1)[1]
            m = _re.match(r"[0#]*", frac)
            fracchars = m.group(0) if m else ""
            self.max_fraction_digits = len(fracchars)
            self.min_fraction_digits = len(fracchars.rstrip("#"))
        else:
            self.max_fraction_digits = 0
            self.min_fraction_digits = 0

    def setParseIntegerOnly(self, v):
        self.parse_integer_only = v

    def isParseIntegerOnly(self):
        return self.parse_integer_only

    def getMinimumFractionDigits(self):
        return self.min_fraction_digits

    def getMaximumFractionDigits(self):
        return self.max_fraction_digits

    def getMultiplier(self):
        return self.multiplier

    def toPattern(self):
        return self.pattern or ""

    def applyPattern(self, pattern):
        self.pattern = pattern
        self._analyze_pattern(pattern)

    def parseObject(self, value):
        s = value
        m = _re.match(r"^\s*([+-])?\s*[\$\u00A4]?\s*([0-9][0-9,]*)(\.[0-9]+)?\s*%?\s*\u2030?", s)
        if not m or m.group(2) is None:
            return None, 0, True
        sign = m.group(1) or ""
        intpart = m.group(2).replace(",", "")
        fracpart = m.group(3)
        end = m.end()
        if self.parse_integer_only:
            if fracpart:
                end = m.start(3)
            numeric_str = sign + intpart
            try:
                num = int(numeric_str)
            except ValueError:
                return None, 0, True
            return num, end, False
        else:
            numeric_str = sign + intpart + (fracpart or "")
            try:
                num = float(numeric_str)
            except ValueError:
                return None, 0, True
            if self.multiplier != 1:
                num = num / self.multiplier
            return num, end, False

    def format(self, value):
        if self.parse_integer_only:
            return str(int(value))
        return str(value)


# Imports End


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
    def _getFormat(self, pattern: str, locale: typing.Any):
        return self._getFormat0(pattern, locale)

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        parsedValue = self._parse(value, pattern, locale)
        return parsedValue is not None

    def _getFormat1(self, locale: typing.Any):
        return NumberFormat(
            pattern=None,
            locale=locale,
            format_type=self.__formatType,
            allow_fractions=self.isAllowFractions(),
        )

    def _determineScale(self, format_: typing.Any) -> int:
        if not self.isStrict():
            return -1
        if not self.isAllowFractions() or format_.isParseIntegerOnly():
            return 0
        minFrac = format_.getMinimumFractionDigits()
        maxFrac = format_.getMaximumFractionDigits()
        if minFrac != maxFrac:
            return -1
        scale = minFrac
        multiplier = format_.getMultiplier() if hasattr(format_, "getMultiplier") else 1
        if multiplier == 100:
            scale += 2
        elif multiplier == 1000:
            scale += 3
        return scale

    def _getFormat0(self, pattern: str, locale: typing.Any):
        usePattern = pattern is not None and len(pattern) > 0
        if not usePattern:
            formatter = self._getFormat1(locale)
        else:
            formatter = NumberFormat(
                pattern=pattern,
                locale=locale,
                format_type=self.__formatType,
                allow_fractions=self.isAllowFractions(),
            )
        if not self.isAllowFractions():
            formatter.setParseIntegerOnly(True)
        return formatter

    def _parse(self, value: str, pattern: str, locale: typing.Any) -> typing.Any:
        value = value.strip() if value is not None else None
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        parsedValue, endIndex, error = formatter.parseObject(value)
        if error:
            return None
        if self.isStrict() and endIndex < len(value):
            return None
        if parsedValue is not None:
            parsedValue = self._processParsedValue(parsedValue, formatter)
        return parsedValue

    def maxValue(self, value, max_) -> bool:
        if self.isAllowFractions():
            return float(value) <= float(max_)
        return int(value) <= int(max_)

    def minValue(self, value, min_) -> bool:
        if self.isAllowFractions():
            return float(value) >= float(min_)
        return int(value) >= int(min_)

    def isInRange(self, value, min_, max_) -> bool:
        return self.minValue(value, min_) and self.maxValue(value, max_)

    def getFormatType(self) -> int:
        return self.__formatType

    def isAllowFractions(self) -> bool:
        return self.__allowFractions

    def __init__(self, strict: bool, formatType: int, allowFractions: bool) -> None:
        super().__init__(strict)
        self.__allowFractions = allowFractions
        self.__formatType = formatType

    def _processParsedValue(self, value: typing.Any, formatter) -> typing.Any:
        raise NotImplementedError

    # Class Methods End
