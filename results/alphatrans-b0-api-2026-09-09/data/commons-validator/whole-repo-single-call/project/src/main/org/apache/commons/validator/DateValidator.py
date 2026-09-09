from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
import typing
from typing import *
import io
import datetime

# Imports End


class DateValidator:

    # Class Fields Begin
    __DATE_VALIDATOR: DateValidator = None
    # Class Fields End

    # Class Methods Begin
    def isValid1(self, value: str, locale: typing.Any) -> bool:
        if value is None:
            return False
        fmt = "%m/%d/%y"
        try:
            datetime.datetime.strptime(value, fmt)
            return True
        except ValueError:
            return False

    def isValid0(self, value: str, datePattern: str, strict: bool) -> bool:
        if value is None or datePattern is None or len(datePattern) <= 0:
            return False
        pyfmt = convert_java_pattern(datePattern)
        try:
            datetime.datetime.strptime(value, pyfmt)
        except ValueError:
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
