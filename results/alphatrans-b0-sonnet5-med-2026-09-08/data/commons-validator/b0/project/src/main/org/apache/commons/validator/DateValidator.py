from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import (
    java_pattern_to_python,
)
import datetime
import typing
from typing import *
import io

# Imports End


class DateValidator:

    # Class Fields Begin
    __DATE_VALIDATOR: "DateValidator" = None
    # Class Fields End

    # Class Methods Begin
    def isValid1(self, value: str, locale: typing.Any) -> bool:
        if value is None:
            return False
        try:
            datetime.datetime.strptime(value, "%m/%d/%y")
        except ValueError:
            try:
                datetime.datetime.strptime(value, "%m/%d/%Y")
            except ValueError:
                return False
        return True

    def isValid0(self, value: str, datePattern: str, strict: bool) -> bool:
        if value is None or datePattern is None or len(datePattern) <= 0:
            return False
        py_pattern = java_pattern_to_python(datePattern)
        try:
            datetime.datetime.strptime(value, py_pattern)
        except ValueError:
            return False
        if strict and (len(datePattern) != len(value)):
            return False
        return True

    def __init__(self) -> None:
        pass

    @staticmethod
    def getInstance() -> "DateValidator":
        return DateValidator.__DATE_VALIDATOR

    # Class Methods End


DateValidator._DateValidator__DATE_VALIDATOR = DateValidator()
