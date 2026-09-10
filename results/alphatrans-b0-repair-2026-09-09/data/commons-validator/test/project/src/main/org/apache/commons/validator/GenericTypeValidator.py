from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.GenericValidator import *

# from src.main.org.apache.commons.logging.LogFactory import *
# from src.main.org.apache.commons.logging.Log import *
import logging
import datetime
import typing
import re
from typing import *
import io

# Imports End


class GenericTypeValidator:

    # Class Fields Begin
    __serialVersionUID: int = 5487162314134261703
    __LOG: logging.Logger = logging.getLogger(
        "org.apache.commons.validator.GenericTypeValidator"
    )
    # Class Fields End

    # ---- Internal helpers -------------------------------------------------

    @staticmethod
    def __parse_number(value: typing.Optional[str], integer_only: bool) -> typing.Optional[float]:
        if value is None:
            return None

        if integer_only:
            pattern = r'^[+-]?(\d{1,3}(,\d{3})*|\d+)$'
        else:
            pattern = r'^[+-]?(\d{1,3}(,\d{3})*|\d+)(\.\d+)?$'

        if not re.match(pattern, value):
            return None

        cleaned = value.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def __convert_date_pattern(pattern: str) -> str:
        mapping = [
            ("yyyy", "%Y"),
            ("yy", "%y"),
            ("MMMM", "%B"),
            ("MMM", "%b"),
            ("MM", "%m"),
            ("M", "%m"),
            ("dd", "%d"),
            ("d", "%d"),
            ("EEEE", "%A"),
            ("EEE", "%a"),
            ("HH", "%H"),
            ("H", "%H"),
            ("hh", "%I"),
            ("h", "%I"),
            ("mm", "%M"),
            ("ss", "%S"),
            ("a", "%p"),
        ]

        result = ""
        i = 0
        length = len(pattern)
        while i < length:
            matched = False
            for token, repl in mapping:
                token_len = len(token)
                if pattern[i:i + token_len] == token:
                    result += repl
                    i += token_len
                    matched = True
                    break
            if not matched:
                result += pattern[i]
                i += 1
        return result

    # Class Methods Begin
    @staticmethod
    def formatCreditCard(value: str) -> int:
        if value is None:
            return None
        try:
            if GenericValidator.isCreditCard(value):
                return int(value)
        except Exception:
            return None
        return None

    @staticmethod
    def formatDate1(
        value: str, datePattern: str, strict: bool
    ) -> typing.Union[datetime.datetime, datetime.date]:
        if value is None or datePattern is None or len(datePattern) == 0:
            return None

        py_pattern = GenericTypeValidator.__convert_date_pattern(datePattern)

        try:
            date = datetime.datetime.strptime(value, py_pattern)
        except ValueError as e:
            if GenericTypeValidator.__LOG.isEnabledFor(logging.DEBUG):
                GenericTypeValidator.__LOG.debug(
                    "Date parse failed value=[%s], pattern=[%s], strict=[%s] %s"
                    % (value, datePattern, strict, e)
                )
            return None

        if strict and len(datePattern) != len(value):
            return None

        return date

    @staticmethod
    def formatDate0(
        value: str, locale: typing.Any
    ) -> typing.Union[datetime.datetime, datetime.date]:
        if value is None:
            return None

        short_patterns = ["%m/%d/%y"]
        default_patterns = ["%b %d, %Y"]

        date = None
        for pattern in short_patterns:
            try:
                date = datetime.datetime.strptime(value, pattern)
                break
            except ValueError:
                date = None

        if date is None:
            for pattern in default_patterns:
                try:
                    date = datetime.datetime.strptime(value, pattern)
                    break
                except ValueError:
                    date = None

        if date is None:
            if GenericTypeValidator.__LOG.isEnabledFor(logging.DEBUG):
                GenericTypeValidator.__LOG.debug(
                    "Date parse failed value=[%s], locale=[%s]" % (value, locale)
                )

        return date

    @staticmethod
    def formatDouble1(value: str, locale: typing.Any) -> float:
        num = GenericTypeValidator.__parse_number(value, False)
        if num is None:
            return None

        max_double = 1.7976931348623157e308
        if -max_double <= num <= max_double:
            return float(num)
        return None

    @staticmethod
    def formatDouble0(value: str) -> float:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def formatFloat1(value: str, locale: typing.Any) -> float:
        num = GenericTypeValidator.__parse_number(value, False)
        if num is None:
            return None

        max_float = 3.4028235e38
        if -max_float <= num <= max_float:
            return float(num)
        return None

    @staticmethod
    def formatFloat0(value: str) -> float:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def formatLong1(value: str, locale: typing.Any) -> int:
        num = GenericTypeValidator.__parse_number(value, True)
        if num is None:
            return None

        min_long = -9223372036854775808
        max_long = 9223372036854775807
        if min_long <= num <= max_long:
            return int(num)
        return None

    @staticmethod
    def formatLong0(value: str) -> int:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def formatInt1(value: str, locale: typing.Any) -> int:
        num = GenericTypeValidator.__parse_number(value, True)
        if num is None:
            return None

        min_int = -2147483648
        max_int = 2147483647
        if min_int <= num <= max_int:
            return int(num)
        return None

    @staticmethod
    def formatInt0(value: str) -> int:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def formatShort1(value: str, locale: typing.Any) -> int:
        num = GenericTypeValidator.__parse_number(value, True)
        if num is None:
            return None

        min_short = -32768
        max_short = 32767
        if min_short <= num <= max_short:
            return int(num)
        return None

    @staticmethod
    def formatShort0(value: str) -> int:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def formatByte1(value: str, locale: typing.Any) -> int:
        num = GenericTypeValidator.__parse_number(value, True)
        if num is None:
            return None

        min_byte = -128
        max_byte = 127
        if min_byte <= num <= max_byte:
            return int(num)
        return None

    @staticmethod
    def formatByte0(value: str) -> int:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    # Class Methods End
