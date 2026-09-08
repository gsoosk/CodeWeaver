from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import (
    _DateFormat,
    _default_pattern,
    DATE_FORMAT_SHORT,
)
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import (
    ParsePosition,
)
import typing
from typing import *
import io

# Imports End


class DateValidator:

    # Class Fields Begin
    __DATE_VALIDATOR: DateValidator = None
    # Class Fields End

    # Class Methods Begin
    def isValid1(self, value: str, locale: typing.Any) -> bool:
        if value is None:
            return False

        pattern = _default_pattern(locale, DATE_FORMAT_SHORT, -1)
        formatter = _DateFormat(pattern, locale)

        pos = ParsePosition(0)
        result = formatter.parseObject(value, pos)
        if result is None:
            return False

        return True

    def isValid0(self, value: str, datePattern: str, strict: bool) -> bool:
        if value is None or datePattern is None or len(datePattern) <= 0:
            return False

        formatter = _DateFormat(datePattern)

        pos = ParsePosition(0)
        result = formatter.parseObject(value, pos)
        if result is None:
            return False

        if strict and (len(datePattern) != len(value)):
            return False

        return True

    def __init__(self) -> None:
        pass

    @staticmethod
    def getInstance() -> DateValidator:
        return DateValidator.__DATE_VALIDATOR

    # Class Methods End


DateValidator._DateValidator__DATE_VALIDATOR = DateValidator()
