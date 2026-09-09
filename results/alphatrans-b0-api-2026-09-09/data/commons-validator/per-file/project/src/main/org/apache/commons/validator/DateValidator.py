from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
import typing
from typing import *
import io
import re
from datetime import datetime

# Imports End


def _convert_pattern(pattern: str) -> str:
    """
    Convert a subset of a Java SimpleDateFormat pattern into a Python
    strftime/strptime compatible format string.
    """
    result = []
    i = 0
    length = len(pattern)
    while i < length:
        ch = pattern[i]
        if ch.isalpha():
            j = i
            while j < length and pattern[j] == ch:
                j += 1
            run_len = j - i
            token = _map_token(ch, run_len)
            result.append(token)
            i = j
        else:
            # escape literal percent signs
            if ch == '%':
                result.append('%%')
            else:
                result.append(ch)
            i += 1
    return ''.join(result)


def _map_token(ch: str, run_len: int) -> str:
    if ch == 'y':
        return '%Y' if run_len >= 4 else '%y'
    if ch == 'M':
        if run_len >= 4:
            return '%B'
        if run_len == 3:
            return '%b'
        return '%m'
    if ch == 'd':
        return '%d'
    if ch == 'H':
        return '%H'
    if ch == 'h':
        return '%I'
    if ch == 'm':
        return '%M'
    if ch == 's':
        return '%S'
    if ch == 'E':
        return '%A' if run_len >= 4 else '%a'
    if ch == 'a':
        return '%p'
    if ch == 'z' or ch == 'Z':
        return '%Z'
    # Unknown letter run - treat as literal characters (best effort)
    return ch * run_len


_LOCALE_SHORT_PATTERNS = {
    'en_US': 'M/d/yy',
    'en_GB': 'dd/MM/yy',
    'en_CA': 'dd/MM/yy',
    'de_DE': 'dd.MM.yy',
    'de': 'dd.MM.yy',
    'fr_FR': 'dd/MM/yy',
    'fr': 'dd/MM/yy',
    'en': 'M/d/yy',
}

_DEFAULT_SHORT_PATTERN = 'M/d/yy'


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


class DateValidator:

    # Class Fields Begin
    __DATE_VALIDATOR: DateValidator = None
    # Class Fields End

    # Class Methods Begin
    def isValid1(self, value: str, locale: typing.Any) -> bool:
        if value is None:
            return False

        key = _locale_key(locale)
        if key is not None:
            pattern = _LOCALE_SHORT_PATTERNS.get(key)
            if pattern is None and '_' in key:
                lang = key.split('_')[0]
                pattern = _LOCALE_SHORT_PATTERNS.get(lang)
        else:
            pattern = None

        if pattern is None:
            pattern = _DEFAULT_SHORT_PATTERN

        python_pattern = _convert_pattern(pattern)

        try:
            datetime.strptime(value, python_pattern)
        except ValueError:
            return False

        return True

    def isValid0(self, value: str, datePattern: str, strict: bool) -> bool:
        if value is None or datePattern is None or len(datePattern) <= 0:
            return False

        python_pattern = _convert_pattern(datePattern)

        try:
            datetime.strptime(value, python_pattern)
        except ValueError:
            return False

        if strict and (len(datePattern) != len(value)):
            return False

        return True

    def __init__(self) -> None:
        pass

    @staticmethod
    def getInstance() -> DateValidator:
        if DateValidator.__DATE_VALIDATOR is None:
            DateValidator.__DATE_VALIDATOR = DateValidator()
        return DateValidator.__DATE_VALIDATOR

    # Class Methods End
