from __future__ import annotations

# Imports Begin
import src.main.org.apache.commons.validator.GenericValidator as _generic_validator_module
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import (
    _DateFormat,
    _default_pattern,
    DATE_FORMAT_SHORT,
    DATE_FORMAT_MEDIUM,
)
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import (
    ParsePosition,
    _normalize_locale,
)

# from src.main.org.apache.commons.logging.LogFactory import *
# from src.main.org.apache.commons.logging.Log import *
import re
import logging
import datetime
import typing
from typing import *
import io

# Imports End


# Locale-sensitive decimal/grouping separators used by ``NumberFormat``-style
# parsing (mirrors the small set of locales supported elsewhere in this
# port -- see ``AbstractCalendarValidator``/``AbstractFormatValidator``).
_LOCALE_NUMBER_SEPARATORS = {
    "en_US": {"decimal": ".", "grouping": ","},
    "en_GB": {"decimal": ".", "grouping": ","},
    "de_DE": {"decimal": ",", "grouping": "."},
}


def _number_separators(locale: typing.Any) -> typing.Dict[str, str]:
    tag = _normalize_locale(locale)
    return _LOCALE_NUMBER_SEPARATORS.get(tag, _LOCALE_NUMBER_SEPARATORS["en_US"])


def _match_number(
    value: str, locale: typing.Any, integer_only: bool
) -> typing.Tuple[typing.Optional[str], int]:
    """Analogue of ``NumberFormat.parse(value, ParsePosition)`` (optionally
    with ``setParseIntegerOnly(true)``): matches a leading, locale-formatted
    number (honoring the locale's grouping/decimal separators) and returns
    ``(normalized_text, charsConsumed)`` -- or ``(None, 0)`` if nothing
    could be parsed from the start of ``value``."""
    seps = _number_separators(locale)
    dec_re = re.escape(seps["decimal"])
    grp_re = re.escape(seps["grouping"])
    int_part = rf"\d{{1,3}}(?:{grp_re}\d{{3}})+|\d+"
    if integer_only:
        pattern = re.compile(rf"^[+-]?(?:{int_part})")
    else:
        pattern = re.compile(rf"^[+-]?(?:{int_part})(?:{dec_re}\d+)?")
    match = pattern.match(value)
    if not match:
        return None, 0
    text = match.group(0)
    normalized = text.replace(seps["grouping"], "")
    if not integer_only:
        normalized = normalized.replace(seps["decimal"], ".")
    return normalized, match.end()


def _parse_integer(value: str, locale: typing.Any) -> typing.Tuple[typing.Optional[int], int]:
    normalized, consumed = _match_number(value, locale, integer_only=True)
    if normalized is None:
        return None, 0
    try:
        return int(normalized), consumed
    except ValueError:
        return None, 0


def _parse_number(value: str, locale: typing.Any) -> typing.Optional[float]:
    normalized, consumed = _match_number(value, locale, integer_only=False)
    if normalized is None or consumed != len(value):
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


_STRICT_INT_RE = re.compile(r"^[+-]?\d+$")


def _parse_strict_bounded_int(value: str, min_value: int, max_value: int) -> int:
    """Analogue of ``Byte``/``Short``/``Integer``/``Long``'s ``valueOf(String)``:
    strict all-digits (plus optional sign) parsing with a range check,
    raising ``ValueError`` (the Python analogue of ``NumberFormatException``)
    on anything else."""
    if not _STRICT_INT_RE.match(value):
        raise ValueError(f"For input string: \"{value}\"")
    num = int(value)
    if num < min_value or num > max_value:
        raise ValueError(f"Value out of range. Value:\"{value}\"")
    return num


_JAVA_FLOAT_SUFFIXES = "fFdD"


def _parse_strict_float(value: str) -> float:
    """Analogue of ``Float``/``Double.valueOf(String)``: like Python's
    ``float()`` but rejecting Python-only extensions (e.g. ``_`` digit
    separators) that Java would not accept, and tolerating a trailing
    ``f``/``F``/``d``/``D`` type suffix."""
    text = value.strip()
    if "_" in text:
        raise ValueError(f"For input string: \"{value}\"")
    if text and text[-1] in _JAVA_FLOAT_SUFFIXES:
        text = text[:-1]
    return float(text)


class GenericTypeValidator:

    # Class Fields Begin
    __serialVersionUID: int = None
    __LOG: logging.Logger = logging.getLogger(
        "org.apache.commons.validator.GenericTypeValidator"
    )
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def formatCreditCard(value: str) -> int:
        return (
            int(value)
            if _generic_validator_module.GenericValidator.isCreditCard(value)
            else None
        )

    @staticmethod
    def formatDate1(
        value: str, datePattern: str, strict: bool
    ) -> typing.Union[datetime.datetime, datetime.date]:
        if value is None or datePattern is None or len(datePattern) == 0:
            return None

        date = None

        formatter = _DateFormat(datePattern)
        pos = ParsePosition(0)
        parsed = formatter.parseObject(value, pos)

        if pos.error_index == -1:
            date = parsed
            if strict and len(datePattern) != len(value):
                date = None
        else:
            if GenericTypeValidator.__LOG.isEnabledFor(logging.DEBUG):
                GenericTypeValidator.__LOG.debug(
                    "Date parse failed value=[%s], pattern=[%s], strict=[%s]"
                    % (value, datePattern, strict)
                )

        return date

    @staticmethod
    def formatDate0(
        value: str, locale: typing.Any
    ) -> typing.Union[datetime.datetime, datetime.date]:
        if value is None:
            return None

        date = None

        short_pattern = _default_pattern(locale, DATE_FORMAT_SHORT, -1)
        formatter_short = _DateFormat(short_pattern, locale)
        pos_short = ParsePosition(0)
        parsed = formatter_short.parseObject(value, pos_short)
        if pos_short.error_index == -1:
            date = parsed

        if date is None:
            default_pattern = _default_pattern(locale, DATE_FORMAT_MEDIUM, -1)
            formatter_default = _DateFormat(default_pattern, locale)
            pos_default = ParsePosition(0)
            parsed = formatter_default.parseObject(value, pos_default)
            if pos_default.error_index == -1:
                date = parsed

        if date is None:
            if GenericTypeValidator.__LOG.isEnabledFor(logging.DEBUG):
                GenericTypeValidator.__LOG.debug(
                    "Date parse failed value=[%s], locale=[%s]" % (value, locale)
                )

        return date

    @staticmethod
    def formatDouble1(value: str, locale: typing.Any) -> float:
        result = None

        if value is not None:
            num = _parse_number(value, locale)
            if num is not None and abs(num) <= 1.7976931348623157e308:
                result = float(num)

        return result

    @staticmethod
    def formatDouble0(value: str) -> float:
        if value is None:
            return None

        try:
            return _parse_strict_float(value)
        except ValueError:
            return None

    @staticmethod
    def formatFloat1(value: str, locale: typing.Any) -> float:
        result = None

        if value is not None:
            num = _parse_number(value, locale)
            if num is not None and abs(num) <= 3.4028235e38:
                result = float(num)

        return result

    @staticmethod
    def formatFloat0(value: str) -> float:
        if value is None:
            return None

        try:
            return _parse_strict_float(value)
        except ValueError:
            return None

    @staticmethod
    def formatLong1(value: str, locale: typing.Any) -> int:
        result = None

        if value is not None:
            num, matched_len = _parse_integer(value, locale)
            if (
                num is not None
                and matched_len == len(value)
                and -(2**63) <= num <= (2**63 - 1)
            ):
                result = int(num)

        return result

    @staticmethod
    def formatLong0(value: str) -> int:
        if value is None:
            return None

        try:
            return _parse_strict_bounded_int(value, -(2**63), 2**63 - 1)
        except ValueError:
            return None

    @staticmethod
    def formatInt1(value: str, locale: typing.Any) -> int:
        result = None

        if value is not None:
            num, matched_len = _parse_integer(value, locale)
            if (
                num is not None
                and matched_len == len(value)
                and -(2**31) <= num <= (2**31 - 1)
            ):
                result = int(num)

        return result

    @staticmethod
    def formatInt0(value: str) -> int:
        if value is None:
            return None

        try:
            return _parse_strict_bounded_int(value, -(2**31), 2**31 - 1)
        except ValueError:
            return None

    @staticmethod
    def formatShort1(value: str, locale: typing.Any) -> int:
        result = None

        if value is not None:
            num, matched_len = _parse_integer(value, locale)
            if num is not None and matched_len == len(value) and -32768 <= num <= 32767:
                result = int(num)

        return result

    @staticmethod
    def formatShort0(value: str) -> int:
        if value is None:
            return None

        try:
            return _parse_strict_bounded_int(value, -32768, 32767)
        except ValueError:
            return None

    @staticmethod
    def formatByte1(value: str, locale: typing.Any) -> int:
        result = None

        if value is not None:
            num, matched_len = _parse_integer(value, locale)
            if num is not None and matched_len == len(value) and -128 <= num <= 127:
                result = int(num)

        return result

    @staticmethod
    def formatByte0(value: str) -> int:
        if value is None:
            return None

        try:
            return _parse_strict_bounded_int(value, -128, 127)
        except ValueError:
            return None

    # Class Methods End
