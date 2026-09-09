from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import *
import zoneinfo
import datetime
import typing
from typing import *
import io
import re as _re
from abc import ABC

# Imports End


SHORT = 3
MEDIUM = 2
LONG = 1
FULL = 0
DEFAULT = 2


def convert_java_pattern(pattern: str) -> str:
    if pattern is None:
        return None
    mapping = {
        "yyyy": "%Y", "yy": "%y", "y": "%Y",
        "MMMM": "%B", "MMM": "%b", "MM": "%m", "M": "%m",
        "dd": "%d", "d": "%d",
        "EEEE": "%A", "EEE": "%a", "E": "%a",
        "HH": "%H", "H": "%H",
        "hh": "%I", "h": "%I",
        "mm": "%M", "m": "%M",
        "ss": "%S", "s": "%S",
        "SSS": "%f", "S": "%f",
        "a": "%p",
        "z": "", "Z": "",
    }
    result = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "'":
            j = i + 1
            lit = ""
            while j < n and pattern[j] != "'":
                lit += pattern[j]
                j += 1
            if lit == "":
                lit = "'"
            result.append(lit)
            i = j + 1
            continue
        if c.isalpha():
            j = i
            while j < n and pattern[j] == c:
                j += 1
            run = pattern[i:j]
            token = None
            for length in range(min(len(run), 4), 0, -1):
                key = c * length
                if key in mapping:
                    token = mapping[key]
                    break
            if token is None:
                token = ""
            result.append(token)
            i = j
            continue
        result.append(c)
        i += 1
    return "".join(result)


class _CalendarFormat:
    def __init__(self, pattern, locale, dateStyle, timeStyle):
        self.pattern = pattern
        self.locale = locale
        self.dateStyle = dateStyle
        self.timeStyle = timeStyle
        self.timezone = None

    def _default_pattern(self):
        date_patterns = {3: "%m/%d/%y", 2: "%b %d, %Y", 1: "%B %d, %Y", 0: "%A, %B %d, %Y"}
        time_patterns = {3: "%H:%M", 2: "%H:%M:%S", 1: "%H:%M:%S", 0: "%H:%M:%S"}
        if self.dateStyle is not None and self.dateStyle >= 0 and self.timeStyle is not None and self.timeStyle >= 0:
            return date_patterns.get(self.dateStyle, "%m/%d/%y") + " " + time_patterns.get(self.timeStyle, "%H:%M:%S")
        elif self.timeStyle is not None and self.timeStyle >= 0:
            return time_patterns.get(self.timeStyle, "%H:%M:%S")
        else:
            useStyle = self.dateStyle if (self.dateStyle is not None and self.dateStyle >= 0) else 3
            return date_patterns.get(useStyle, "%m/%d/%y")

    def parseObject(self, value: str):
        fmt = self.pattern if self.pattern else self._default_pattern()
        try:
            dt = datetime.datetime.strptime(value, fmt)
            if self.timezone is not None:
                dt = dt.replace(tzinfo=self.timezone)
            return dt, len(value), False
        except ValueError:
            pass
        for cut in range(len(value) - 1, 0, -1):
            prefix = value[:cut]
            try:
                dt = datetime.datetime.strptime(prefix, fmt)
                if self.timezone is not None:
                    dt = dt.replace(tzinfo=self.timezone)
                return dt, cut, False
            except ValueError:
                continue
        return None, 0, True

    def format(self, value):
        if value is None:
            return None
        fmt = self.pattern if self.pattern else self._default_pattern()
        return value.strftime(fmt)

    def setLenient(self, lenient):
        pass

    def getCalendar(self):
        return getattr(self, "_last_parsed", None)


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
        if result != 0 or field in ("HOUR", "HOUR_OF_DAY"):
            return result
        result = self.__calculateCompareResult(value, compare, "minute")
        if result != 0 or field == "MINUTE":
            return result
        result = self.__calculateCompareResult(value, compare, "second")
        if result != 0 or field == "SECOND":
            return result
        if field == "MILLISECOND":
            return self.__calculateCompareResult(value, compare, "microsecond")
        raise ValueError("Invalid field: " + str(field))

    def _compare(self, value, compare, field: int) -> int:
        result = self.__calculateCompareResult(value, compare, "year")
        if result != 0 or field == "YEAR":
            return result
        if field == "WEEK_OF_YEAR":
            return self.__calculateCompareResult(value, compare, "isocalendar_week")
        if field == "DAY_OF_YEAR":
            return self.__calculateCompareResult(value, compare, "yday")
        result = self.__calculateCompareResult(value, compare, "month")
        if result != 0 or field == "MONTH":
            return result
        result = self.__calculateCompareResult(value, compare, "day")
        if result != 0 or field in ("DATE", "DAY_OF_WEEK", "DAY_OF_WEEK_IN_MONTH"):
            return result
        return self._compareTime(value, compare, field)

    def _getFormat1(self, locale: typing.Any):
        return _CalendarFormat(None, locale, self.__dateStyle, self.__timeStyle)

    def _getFormat0(self, pattern: str, locale: typing.Any):
        usePattern = pattern is not None and len(pattern) > 0
        if not usePattern:
            formatter = self._getFormat1(locale)
        else:
            formatter = _CalendarFormat(convert_java_pattern(pattern), locale, self.__dateStyle, self.__timeStyle)
        return formatter

    def _parse(self, value: str, pattern: str, locale: typing.Any, timeZone):
        value = value.strip() if value is not None else None
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        if timeZone is not None:
            formatter.timezone = timeZone
        parsedValue, endIndex, error = formatter.parseObject(value)
        if error:
            return None
        if self.isStrict() and endIndex < len(value):
            return None
        if parsedValue is not None:
            parsedValue = self._processParsedValue(parsedValue, formatter)
        return parsedValue

    def _format5(self, value: typing.Any, formatter) -> str:
        if value is None:
            return None
        return formatter.format(value)

    def format4(self, value: typing.Any, pattern: str, locale: typing.Any, timeZone) -> str:
        formatter = self._getFormat0(pattern, locale)
        if timeZone is not None:
            formatter.timezone = timeZone
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
        v = getattr(value, field, None)
        c = getattr(compare, field, None)
        if field == "isocalendar_week":
            v = value.isocalendar()[1]
            c = compare.isocalendar()[1]
        if field == "yday":
            v = value.timetuple().tm_yday
            c = compare.timetuple().tm_yday
        diff = v - c
        if diff < 0:
            return -1
        elif diff > 0:
            return 1
        return 0

    def __calculateQuarter(self, calendar, monthOfFirstQuarter: int) -> int:
        year = calendar.year
        month = calendar.month
        relativeMonth = (month - monthOfFirstQuarter) if month >= monthOfFirstQuarter else (month + (12 - monthOfFirstQuarter))
        quarter = (relativeMonth // 3) + 1
        if month < monthOfFirstQuarter:
            year -= 1
        return (year * 10) + quarter

    def _processParsedValue(self, value: typing.Any, formatter) -> typing.Any:
        raise NotImplementedError

    # Class Methods End
