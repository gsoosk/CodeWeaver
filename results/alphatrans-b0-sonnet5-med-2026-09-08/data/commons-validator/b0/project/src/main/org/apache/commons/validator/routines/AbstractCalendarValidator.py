from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import (
    AbstractFormatValidator,
    _ParsePosition,
)
import zoneinfo
import datetime
import typing
from typing import *
import io
from abc import ABC

# Imports End


_JAVA_TO_PY = [
    ("yyyy", "%Y"),
    ("yy", "%y"),
    ("MMMM", "%B"),
    ("MMM", "%b"),
    ("MM", "%m"),
    ("M", "%m"),
    ("dd", "%d"),
    ("d", "%d"),
    ("HH", "%H"),
    ("H", "%H"),
    ("hh", "%I"),
    ("h", "%I"),
    ("mm", "%M"),
    ("m", "%M"),
    ("ss", "%S"),
    ("s", "%S"),
    ("SSS", "%f"),
    ("EEEE", "%A"),
    ("EEE", "%a"),
    ("a", "%p"),
    ("zzz", "%Z"),
    ("z", "%Z"),
]


def java_pattern_to_python(pattern: str) -> str:
    if pattern is None:
        return pattern
    result = []
    i = 0
    n = len(pattern)
    while i < n:
        matched = False
        for jtoken, ptoken in _JAVA_TO_PY:
            if pattern.startswith(jtoken, i):
                result.append(ptoken)
                i += len(jtoken)
                matched = True
                break
        if not matched:
            result.append(pattern[i])
            i += 1
    return "".join(result)


# Java DateFormat style constants
FULL = 0
LONG = 1
MEDIUM = 2
SHORT = 3
DEFAULT = 2

_DATE_STYLE_PATTERNS = {
    FULL: "EEEE, MMMM d, yyyy",
    LONG: "MMMM d, yyyy",
    MEDIUM: "MMM d, yyyy",
    SHORT: "M/d/yy",
}

_TIME_STYLE_PATTERNS = {
    FULL: "h:mm:ss a zzz",
    LONG: "h:mm:ss a",
    MEDIUM: "h:mm:ss a",
    SHORT: "h:mm a",
}


class _DateTimeFormat:
    def __init__(self, java_pattern: str):
        self.java_pattern = java_pattern
        self.py_pattern = java_pattern_to_python(java_pattern)
        self.lenient = False
        self.timezone = None
        self._calendar = None

    def setLenient(self, b: bool) -> None:
        self.lenient = b

    def setTimeZone(self, tz) -> None:
        self.timezone = tz

    def getTimeZone(self):
        return self.timezone

    def toPattern(self) -> str:
        return self.java_pattern

    def parseObject(self, value: str, pos: "_ParsePosition"):
        s = value[pos.index:]
        try:
            dt = datetime.datetime.strptime(s, self.py_pattern)
        except ValueError:
            pos.error_index = pos.index
            return None
        if self.timezone is not None:
            try:
                dt = dt.replace(tzinfo=self.timezone)
            except Exception:
                pass
        self._calendar = dt
        pos.index = len(value)
        return dt

    def getCalendar(self):
        return self._calendar if self._calendar is not None else None

    def format(self, value) -> str:
        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            value = datetime.datetime.combine(value, datetime.time())
        return value.strftime(self.py_pattern)


class AbstractCalendarValidator(AbstractFormatValidator, ABC):

    # Class Fields Begin
    __serialVersionUID: int = -1410008585975827379
    __dateStyle: int = None
    __timeStyle: int = None
    # Class Fields End

    # Class Methods Begin
    def _getFormat(self, pattern: str, locale: typing.Any):
        return self._getFormat0(pattern, locale)

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        parsedValue = self._parse(value, pattern, locale, None)
        return parsedValue is not None

    def _compareQuarters(self, value, compare, monthOfFirstQuarter: int) -> int:
        valueQuarter = self.__calculateQuarter(value, monthOfFirstQuarter)
        compareQuarter = self.__calculateQuarter(compare, monthOfFirstQuarter)
        if valueQuarter < compareQuarter:
            return -1
        elif valueQuarter > compareQuarter:
            return 1
        return 0

    def _compareTime(self, value, compare, field: int) -> int:
        result = self.__calculateCompareResult(value, compare, "hour")
        if result != 0 or field in ("hour",):
            return result
        result = self.__calculateCompareResult(value, compare, "minute")
        if result != 0 or field == "minute":
            return result
        result = self.__calculateCompareResult(value, compare, "second")
        if result != 0 or field == "second":
            return result
        if field == "millisecond":
            return self.__calculateCompareResult(value, compare, "microsecond")
        raise ValueError("Invalid field: " + str(field))

    def _compare(self, value, compare, field: int) -> int:
        result = self.__calculateCompareResult(value, compare, "year")
        if result != 0 or field == "year":
            return result
        if field == "week":
            return self.__calculateCompareResult(value, compare, "week")
        if field == "dayofyear":
            return self.__calculateCompareResult(value, compare, "dayofyear")
        result = self.__calculateCompareResult(value, compare, "month")
        if result != 0 or field == "month":
            return result
        if field == "weekofmonth":
            return self.__calculateCompareResult(value, compare, "weekofmonth")
        result = self.__calculateCompareResult(value, compare, "day")
        if result != 0 or field in ("day", "dayofweek", "dayofweekinmonth"):
            return result
        return self._compareTime(value, compare, field)

    def _getFormat1(self, locale: typing.Any):
        if self.__dateStyle is not None and self.__dateStyle >= 0 and self.__timeStyle is not None and self.__timeStyle >= 0:
            pattern = _DATE_STYLE_PATTERNS.get(self.__dateStyle, "M/d/yy") + " " + _TIME_STYLE_PATTERNS.get(self.__timeStyle, "h:mm a")
        elif self.__timeStyle is not None and self.__timeStyle >= 0:
            pattern = _TIME_STYLE_PATTERNS.get(self.__timeStyle, "h:mm a")
        else:
            useDateStyle = self.__dateStyle if (self.__dateStyle is not None and self.__dateStyle >= 0) else SHORT
            pattern = _DATE_STYLE_PATTERNS.get(useDateStyle, "M/d/yy")
        formatter = _DateTimeFormat(pattern)
        formatter.setLenient(False)
        return formatter

    def _getFormat0(self, pattern: str, locale: typing.Any):
        usePattern = pattern is not None and len(pattern) > 0
        if not usePattern:
            formatter = self._getFormat1(locale)
        else:
            formatter = _DateTimeFormat(pattern)
        formatter.setLenient(False)
        return formatter

    def _parse(self, value: str, pattern: str, locale: typing.Any, timeZone):
        if value is not None:
            value = value.strip()
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        if timeZone is not None:
            formatter.setTimeZone(timeZone)
        return AbstractFormatValidator._parse(self, value, formatter)

    def _format5(self, value: typing.Any, formatter: typing.Any) -> str:
        if value is None:
            return None
        return formatter.format(value)

    def format4(self, value: typing.Any, pattern: str, locale: typing.Any, timeZone) -> str:
        formatter = self._getFormat0(pattern, locale)
        if timeZone is not None:
            formatter.setTimeZone(timeZone)
        return self._format5(value, formatter)

    def format3(self, value: typing.Any, pattern: str, locale: typing.Any) -> str:
        return self.format4(value, pattern, locale, None)

    def format2(self, value: typing.Any, locale: typing.Any, timeZone) -> str:
        return self.format4(value, None, locale, timeZone)

    def format1(self, value: typing.Any, pattern: str, timeZone) -> str:
        return self.format4(value, pattern, None, timeZone)

    def format0(self, value: typing.Any, timeZone) -> str:
        return self.format4(value, None, None, timeZone)

    def __init__(self, strict: bool, dateStyle: int, timeStyle: int) -> None:
        super().__init__(strict)
        self.__dateStyle = dateStyle
        self.__timeStyle = timeStyle

    def __calculateCompareResult(self, value, compare, field: str) -> int:
        v1 = getattr(value, field, None)
        v2 = getattr(compare, field, None)
        if field == "week":
            v1 = value.isocalendar()[1]
            v2 = compare.isocalendar()[1]
        elif field == "dayofyear":
            v1 = value.timetuple().tm_yday
            v2 = compare.timetuple().tm_yday
        elif field == "weekofmonth":
            v1 = (value.day - 1) // 7
            v2 = (compare.day - 1) // 7
        elif field == "dayofweekinmonth":
            v1 = (value.day - 1) // 7
            v2 = (compare.day - 1) // 7
        elif field == "hour":
            v1 = value.hour if hasattr(value, "hour") else 0
            v2 = compare.hour if hasattr(compare, "hour") else 0
        elif field == "minute":
            v1 = value.minute if hasattr(value, "minute") else 0
            v2 = compare.minute if hasattr(compare, "minute") else 0
        elif field == "second":
            v1 = value.second if hasattr(value, "second") else 0
            v2 = compare.second if hasattr(compare, "second") else 0
        elif field == "microsecond":
            v1 = value.microsecond if hasattr(value, "microsecond") else 0
            v2 = compare.microsecond if hasattr(compare, "microsecond") else 0
        difference = v1 - v2
        if difference < 0:
            return -1
        elif difference > 0:
            return 1
        return 0

    def __calculateQuarter(self, calendar, monthOfFirstQuarter: int) -> int:
        year = calendar.year
        month = calendar.month
        relativeMonth = (month - monthOfFirstQuarter) if (month >= monthOfFirstQuarter) else (month + (12 - monthOfFirstQuarter))
        quarter = (relativeMonth // 3) + 1
        if month < monthOfFirstQuarter:
            year -= 1
        return (year * 10) + quarter

    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        raise NotImplementedError

    # Class Methods End
