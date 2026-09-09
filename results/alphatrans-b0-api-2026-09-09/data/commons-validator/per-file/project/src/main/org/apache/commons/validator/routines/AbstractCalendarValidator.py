from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import *
import zoneinfo
import datetime
import typing
from typing import *
import io
from abc import ABC, abstractmethod
import re

# Imports End


# ---------------------------------------------------------------------------
# Internal helpers - a very small re-implementation of a subset of Java's
# SimpleDateFormat / DateFormat behaviour, sufficient to support the parsing
# and formatting requirements of the calendar/date/time validators.
# ---------------------------------------------------------------------------

# DateFormat style constants (mirrors java.text.DateFormat)
FULL = 0
LONG = 1
MEDIUM = 2
SHORT = 3

# java.util.Calendar field constants (only the ones used by this class)
YEAR = 1
MONTH = 2
WEEK_OF_YEAR = 3
WEEK_OF_MONTH = 4
DATE = 5
DAY_OF_MONTH = 5
DAY_OF_YEAR = 6
DAY_OF_WEEK = 7
DAY_OF_WEEK_IN_MONTH = 8
AM_PM = 9
HOUR = 10
HOUR_OF_DAY = 11
MINUTE = 12
SECOND = 13
MILLISECOND = 14


_PATTERN_MAP = {
    "y": "%Y",
    "M": "%m",
    "d": "%d",
    "H": "%H",
    "h": "%I",
    "m": "%M",
    "s": "%S",
    "S": "%f",
    "a": "%p",
    "E": "%a",
    "z": "%Z",
    "Z": "%z",
    "D": "%j",
    "w": "%W",
    "k": "%H",
    "K": "%I",
    "G": "",
    "u": "%u",
}


def _convert_pattern(pattern: str) -> str:
    """Convert a (subset of) Java SimpleDateFormat pattern to a Python
    strftime/strptime compatible pattern."""
    result: List[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "'":
            j = i + 1
            literal: List[str] = []
            while j < n and pattern[j] != "'":
                literal.append(pattern[j])
                j += 1
            if not literal:
                result.append("'")
            else:
                result.append("".join(literal))
            i = j + 1
            continue
        if c.isalpha():
            j = i
            while j < n and pattern[j] == c:
                j += 1
            length = j - i
            if c == "y" and length == 2:
                result.append("%y")
            elif c == "M" and length >= 4:
                result.append("%B")
            elif c == "M" and length == 3:
                result.append("%b")
            elif c == "E" and length >= 4:
                result.append("%A")
            elif c == "E" and length in (1, 2, 3):
                result.append("%a")
            elif c in _PATTERN_MAP:
                result.append(_PATTERN_MAP[c])
            else:
                result.append(pattern[i:j])
            i = j
        else:
            result.append(c)
            i += 1
    return "".join(result)


_DATE_STYLE_PATTERNS = {
    FULL: "EEEE, MMMM d, yyyy",
    LONG: "MMMM d, yyyy",
    MEDIUM: "MMM d, yyyy",
    SHORT: "M/d/yy",
}

_TIME_STYLE_PATTERNS = {
    FULL: "h:mm:ss a zzzz",
    LONG: "h:mm:ss a z",
    MEDIUM: "h:mm:ss a",
    SHORT: "h:mm a",
}


def _style_pattern(
    date_style: typing.Optional[int], time_style: typing.Optional[int]
) -> str:
    parts = []
    if date_style is not None:
        parts.append(_DATE_STYLE_PATTERNS.get(date_style, _DATE_STYLE_PATTERNS[SHORT]))
    if time_style is not None:
        parts.append(_TIME_STYLE_PATTERNS.get(time_style, _TIME_STYLE_PATTERNS[SHORT]))
    return " ".join(parts)


class _DateFormatter:
    """A minimal stand in for java.text.DateFormat / SimpleDateFormat."""

    def __init__(self, pattern: str, locale: typing.Any = None) -> None:
        self.pattern = pattern
        self.locale = locale
        self.lenient = False
        self.time_zone: typing.Any = None
        self._py_pattern = _convert_pattern(pattern)

    def set_time_zone(self, tz: typing.Any) -> None:
        self.time_zone = tz

    def set_lenient(self, lenient: bool) -> None:
        self.lenient = lenient

    def parse(self, text: str) -> typing.Optional[datetime.datetime]:
        try:
            dt = datetime.datetime.strptime(text, self._py_pattern)
        except (ValueError, TypeError):
            return None
        if self.time_zone is not None:
            try:
                dt = dt.replace(tzinfo=self.time_zone)
            except Exception:
                pass
        return dt

    def format(self, value: typing.Any) -> str:
        if isinstance(value, datetime.datetime):
            dt = value
        elif isinstance(value, datetime.date):
            dt = datetime.datetime.combine(value, datetime.time())
        else:
            dt = value
        if self.time_zone is not None and getattr(dt, "tzinfo", None) is None:
            try:
                dt = dt.replace(tzinfo=self.time_zone)
            except Exception:
                pass
        return dt.strftime(self._py_pattern)


class AbstractCalendarValidator(AbstractFormatValidator, ABC):

    # Class Fields Begin
    __serialVersionUID: int = -1410008585975827379
    __dateStyle: int = None
    __timeStyle: int = None
    # Class Fields End

    # Class Methods Begin
    def _getFormat(self, pattern: str, locale: typing.Any) -> Format:
        return self._getFormat0(pattern, locale)

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        parsedValue = self._parse(value, pattern, locale, None)
        return parsedValue is not None

    def _compareQuarters(
        self,
        value: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        compare: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        monthOfFirstQuarter: int,
    ) -> int:
        valueQuarter = self.__calculateQuarter(value, monthOfFirstQuarter)
        compareQuarter = self.__calculateQuarter(compare, monthOfFirstQuarter)
        if valueQuarter < compareQuarter:
            return -1
        elif valueQuarter > compareQuarter:
            return 1
        else:
            return 0

    def _compareTime(
        self,
        value: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        compare: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        field: int,
    ) -> int:
        result = self.__calculateCompareResult(value, compare, HOUR_OF_DAY)
        if result != 0 or (field == HOUR or field == HOUR_OF_DAY):
            return result

        result = self.__calculateCompareResult(value, compare, MINUTE)
        if result != 0 or field == MINUTE:
            return result

        result = self.__calculateCompareResult(value, compare, SECOND)
        if result != 0 or field == SECOND:
            return result

        if field == MILLISECOND:
            return self.__calculateCompareResult(value, compare, MILLISECOND)

        raise ValueError("Invalid field: " + str(field))

    def _compare(
        self,
        value: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        compare: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        field: int,
    ) -> int:
        result = self.__calculateCompareResult(value, compare, YEAR)
        if result != 0 or field == YEAR:
            return result

        if field == WEEK_OF_YEAR:
            return self.__calculateCompareResult(value, compare, WEEK_OF_YEAR)

        if field == DAY_OF_YEAR:
            return self.__calculateCompareResult(value, compare, DAY_OF_YEAR)

        result = self.__calculateCompareResult(value, compare, MONTH)
        if result != 0 or field == MONTH:
            return result

        if field == WEEK_OF_MONTH:
            return self.__calculateCompareResult(value, compare, WEEK_OF_MONTH)

        result = self.__calculateCompareResult(value, compare, DATE)
        if result != 0 or (
            field == DATE or field == DAY_OF_WEEK or field == DAY_OF_WEEK_IN_MONTH
        ):
            return result

        return self._compareTime(value, compare, field)

    def _getFormat1(self, locale: typing.Any) -> Format:
        dateStyle = self.__dateStyle
        timeStyle = self.__timeStyle

        if dateStyle >= 0 and timeStyle >= 0:
            pattern = _style_pattern(dateStyle, timeStyle)
        elif timeStyle >= 0:
            pattern = _style_pattern(None, timeStyle)
        else:
            useDateStyle = dateStyle if dateStyle >= 0 else SHORT
            pattern = _style_pattern(useDateStyle, None)

        formatter = _DateFormatter(pattern, locale)
        formatter.set_lenient(False)
        return formatter

    def _getFormat0(self, pattern: str, locale: typing.Any) -> Format:
        formatter = None
        usePattern = pattern is not None and len(pattern) > 0
        if not usePattern:
            formatter = self._getFormat1(locale)
        else:
            formatter = _DateFormatter(pattern, locale)
        formatter.set_lenient(False)
        return formatter

    def _parse(
        self,
        value: str,
        pattern: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Any:
        value = None if value is None else value.strip()
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        if timeZone is not None:
            formatter.set_time_zone(timeZone)
        return self.__parse_with_formatter(value, formatter)

    def _format5(self, value: typing.Any, formatter: Format) -> str:
        if value is None:
            return None
        return formatter.format(value)

    def format4(
        self,
        value: typing.Any,
        pattern: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> str:
        formatter = self._getFormat0(pattern, locale)
        if timeZone is not None:
            formatter.set_time_zone(timeZone)
        elif isinstance(value, datetime.datetime) and value.tzinfo is not None:
            formatter.set_time_zone(value.tzinfo)
        return self._format5(value, formatter)

    def format3(self, value: typing.Any, pattern: str, locale: typing.Any) -> str:
        return self.format4(value, pattern, locale, None)

    def format2(
        self,
        value: typing.Any,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> str:
        return self.format4(value, None, locale, timeZone)

    def format1(
        self,
        value: typing.Any,
        pattern: str,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> str:
        return self.format4(value, pattern, None, timeZone)

    def format0(
        self,
        value: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> str:
        return self.format4(value, None, None, timeZone)

    def __init__(self, strict: bool, dateStyle: int, timeStyle: int) -> None:
        super().__init__(strict)
        self.__dateStyle = dateStyle
        self.__timeStyle = timeStyle

    def __field_value(
        self,
        value: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        field: int,
    ) -> int:
        if field == YEAR:
            return value.year
        if field == MONTH:
            return value.month - 1
        if field == WEEK_OF_YEAR:
            return value.isocalendar()[1]
        if field == WEEK_OF_MONTH:
            return ((value.day - 1) // 7) + 1
        if field == DATE:
            return value.day
        if field == DAY_OF_YEAR:
            return value.timetuple().tm_yday
        if field == DAY_OF_WEEK:
            return (value.isoweekday() % 7) + 1
        if field == DAY_OF_WEEK_IN_MONTH:
            return ((value.day - 1) // 7) + 1
        if field == HOUR:
            return value.hour % 12
        if field == HOUR_OF_DAY:
            return value.hour
        if field == MINUTE:
            return value.minute
        if field == SECOND:
            return value.second
        if field == MILLISECOND:
            return value.microsecond // 1000
        raise ValueError("Invalid field: " + str(field))

    def __calculateCompareResult(
        self,
        value: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        compare: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        field: int,
    ) -> int:
        difference = self.__field_value(value, field) - self.__field_value(
            compare, field
        )
        if difference < 0:
            return -1
        elif difference > 0:
            return 1
        else:
            return 0

    def __calculateQuarter(
        self,
        calendar: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        monthOfFirstQuarter: int,
    ) -> int:
        year = calendar.year
        month = calendar.month
        if month >= monthOfFirstQuarter:
            relativeMonth = month - monthOfFirstQuarter
        else:
            relativeMonth = month + (12 - monthOfFirstQuarter)
        quarter = (relativeMonth // 3) + 1
        if month < monthOfFirstQuarter:
            year -= 1
        return (year * 10) + quarter

    def __parse_with_formatter(self, value: str, formatter: Format) -> typing.Any:
        parsed = formatter.parse(value)
        if parsed is None:
            return None
        return self._processParsedValue(parsed, formatter)

    @abstractmethod
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        pass

    # Class Methods End
