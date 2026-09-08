from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import (
    AbstractFormatValidator,
    _ParsePosition,
)
import typing
from typing import *
import numbers
import io
from abc import ABC
import locale as _locale_module


class _DecimalFormat:
    def __init__(self, pattern: str = None):
        self.pattern = pattern
        self.parse_integer_only = False
        self.multiplier = 1
        self.min_fraction_digits = 0
        self.max_fraction_digits = 3

    def setParseIntegerOnly(self, b: bool) -> None:
        self.parse_integer_only = b

    def isParseIntegerOnly(self) -> bool:
        return self.parse_integer_only

    def getMinimumFractionDigits(self) -> int:
        return self.min_fraction_digits

    def getMaximumFractionDigits(self) -> int:
        return self.max_fraction_digits

    def getMultiplier(self) -> int:
        return self.multiplier

    def toPattern(self) -> str:
        return self.pattern or ""

    def applyPattern(self, pattern: str) -> None:
        self.pattern = pattern

    def parseObject(self, value: str, pos: "_ParsePosition"):
        s = value[pos.index:]
        s = s.strip()
        try:
            if self.parse_integer_only:
                num_str = ""
                idx = 0
                if idx < len(s) and s[idx] in "+-":
                    num_str += s[idx]
                    idx += 1
                while idx < len(s) and (s[idx].isdigit() or s[idx] == ","):
                    if s[idx] != ",":
                        num_str += s[idx]
                    idx += 1
                if num_str == "" or num_str == "+" or num_str == "-":
                    pos.error_index = pos.index
                    return None
                result = int(num_str)
                pos.index += idx
                return result
            else:
                num_str = ""
                idx = 0
                if idx < len(s) and s[idx] in "+-":
                    num_str += s[idx]
                    idx += 1
                while idx < len(s) and (s[idx].isdigit() or s[idx] in ".,"):
                    if s[idx] != ",":
                        num_str += s[idx]
                    idx += 1
                if num_str == "":
                    pos.error_index = pos.index
                    return None
                result = float(num_str)
                pos.index += idx
                return result
        except ValueError:
            pos.error_index = pos.index
            return None

    def format(self, value) -> str:
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
    def _getFormat(self, pattern: str, locale: typing.Any) -> typing.Any:
        return self._getFormat0(pattern, locale)

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        parsedValue = self._parse(value, pattern, locale)
        return parsedValue is not None

    def _getFormat1(self, locale: typing.Any) -> typing.Any:
        formatter = _DecimalFormat()
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
        if isinstance(format_, _DecimalFormat):
            multiplier = format_.getMultiplier()
            if multiplier == 100:
                scale += 2
            elif multiplier == 1000:
                scale += 3
        elif self.__formatType == AbstractNumberValidator.PERCENT_FORMAT:
            scale += 2
        return scale

    def _getFormat0(self, pattern: str, locale: typing.Any) -> typing.Any:
        usePattern = pattern is not None and len(pattern) > 0
        if not usePattern:
            formatter = self._getFormat1(locale)
        else:
            formatter = _DecimalFormat(pattern)
        if not self.isAllowFractions():
            formatter.setParseIntegerOnly(True)
        return formatter

    def _parse(self, value: str, pattern: str, locale: typing.Any) -> typing.Any:
        if value is not None:
            value = value.strip()
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        return AbstractFormatValidator._parse(self, value, formatter)

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

    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        raise NotImplementedError

    # Class Methods End
