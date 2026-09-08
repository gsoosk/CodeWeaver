from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.GenericValidator import *
import logging
import datetime
import typing
from typing import *
import io

# Imports End


class GenericTypeValidator:

    # Class Fields Begin
    __serialVersionUID: int = 5487162314134261703
    __LOG: logging.Logger = logging.getLogger("GenericTypeValidator")
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def formatCreditCard(value: str) -> int:
        return int(value) if GenericValidator.isCreditCard(value) else None

    @staticmethod
    def formatDate1(value: str, datePattern: str, strict: bool):
        from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import (
            java_pattern_to_python,
        )
        if value is None or datePattern is None or len(datePattern) == 0:
            return None
        try:
            py_pattern = java_pattern_to_python(datePattern)
            date = datetime.datetime.strptime(value, py_pattern)
            if strict and len(datePattern) != len(value):
                return None
            return date
        except ValueError:
            return None

    @staticmethod
    def formatDate0(value: str, locale: typing.Any):
        if value is None:
            return None
        for fmt in ("%m/%d/%y", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def formatDouble1(value: str, locale: typing.Any) -> float:
        return GenericTypeValidator.formatDouble0(value)

    @staticmethod
    def formatDouble0(value: str) -> float:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def formatFloat1(value: str, locale: typing.Any) -> float:
        return GenericTypeValidator.formatFloat0(value)

    @staticmethod
    def formatFloat0(value: str) -> float:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def formatLong1(value: str, locale: typing.Any) -> int:
        return GenericTypeValidator.formatLong0(value)

    @staticmethod
    def formatLong0(value: str) -> int:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def formatInt1(value: str, locale: typing.Any) -> int:
        return GenericTypeValidator.formatInt0(value)

    @staticmethod
    def formatInt0(value: str) -> int:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def formatShort1(value: str, locale: typing.Any) -> int:
        return GenericTypeValidator.formatShort0(value)

    @staticmethod
    def formatShort0(value: str) -> int:
        if value is None:
            return None
        try:
            v = int(value)
            if v < -32768 or v > 32767:
                return None
            return v
        except ValueError:
            return None

    @staticmethod
    def formatByte1(value: str, locale: typing.Any) -> int:
        return GenericTypeValidator.formatByte0(value)

    @staticmethod
    def formatByte0(value: str) -> int:
        if value is None:
            return None
        try:
            v = int(value)
            if v < -128 or v > 127:
                return None
            return v
        except ValueError:
            return None

    # Class Methods End
