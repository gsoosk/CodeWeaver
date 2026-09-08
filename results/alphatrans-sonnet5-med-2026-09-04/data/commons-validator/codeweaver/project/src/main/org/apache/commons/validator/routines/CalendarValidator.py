from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import (
    _CAL_YEAR,
    _CAL_MONTH,
    _CAL_WEEK_OF_YEAR,
    _CAL_WEEK_OF_MONTH,
    _CAL_DATE,
    _CAL_DAY_OF_YEAR,
    _CAL_DAY_OF_WEEK,
    _CAL_DAY_OF_WEEK_IN_MONTH,
    _CAL_HOUR,
    _CAL_HOUR_OF_DAY,
    _CAL_MINUTE,
    _CAL_SECOND,
    _CAL_MILLISECOND,
)
import zoneinfo
import datetime
import typing
from typing import *
import io

# Imports End


class CalendarValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: CalendarValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        # Java's ``CalendarValidator.processParsedValue`` returns
        # ``((DateFormat) formatter).getCalendar()`` verbatim -- the
        # underlying ``Calendar`` including whatever concrete ``TimeZone``
        # was attached during parsing. ``Calendar#equals`` compares that
        # zone too, so the zone must be preserved here, not stripped.
        return value

    def _defaultTimeZone(self) -> typing.Optional[typing.Any]:
        # Mirrors java.util.TimeZone.getDefault() semantics via the shared
        # AbstractCalendarValidator._defaultTimeZone() implementation.
        # Declared explicitly here (rather than relying purely on
        # inheritance) to make CalendarValidator's contract clear.
        return AbstractCalendarValidator._defaultTimeZone(self)

    def compareYears(
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
    ) -> int:
        return self._compare(value, compare, _CAL_YEAR)

    def compareQuarters1(
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
        return self._compareQuarters(value, compare, monthOfFirstQuarter)

    def compareQuarters0(
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
    ) -> int:
        return self.compareQuarters1(value, compare, 1)

    def compareMonths(
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
    ) -> int:
        return self._compare(value, compare, _CAL_MONTH)

    def compareWeeks(
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
    ) -> int:
        return self._compare(value, compare, _CAL_WEEK_OF_YEAR)

    def compareDates(
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
    ) -> int:
        return self._compare(value, compare, _CAL_DATE)

    @staticmethod
    def adjustToTimeZone(
        value: typing.Union[
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
            datetime.timezone,
        ],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> None:
        # NOTE: java.util.Calendar objects are mutable, so the original
        # ``adjustToTimeZone`` mutates ``value`` in place, re-pointing it at
        # ``timeZone`` while leaving its wall-clock fields (year/month/day/
        # hour/minute[/second/millisecond]) untouched -- i.e. it changes
        # *which instant* the Calendar represents without changing how the
        # fields read. Python's ``datetime`` is immutable, so there is no
        # way to mutate the caller's object in place; callers must instead
        # rebind the result, e.g. ``value = CalendarValidator.adjustToTimeZone(value, tz)``.
        if value is None or timeZone is None:
            return value
        return value.replace(tzinfo=timeZone)

    def validate7(
        self,
        value: str,
        pattern: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self._parse(value, pattern, locale, timeZone)

    def validate6(self, value: str, pattern: str, locale: typing.Any) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, pattern, locale, None)

    def validate5(
        self,
        value: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, None, locale, timeZone)

    def validate4(self, value: str, locale: typing.Any) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, None, locale, None)

    def validate3(
        self,
        value: str,
        pattern: str,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, pattern, None, timeZone)

    def validate2(self, value: str, pattern: str) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, pattern, None, None)

    def validate1(
        self, value: str, timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone]
    ) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, None, None, timeZone)

    def validate0(self, value: str) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self.validate7(value, None, None, None)

    @staticmethod
    def CalendarValidator1() -> CalendarValidator:
        return CalendarValidator(True, DATE_FORMAT_SHORT)

    def __init__(self, strict: bool, dateStyle: int) -> None:
        AbstractCalendarValidator.__init__(self, strict, dateStyle, -1)

    @staticmethod
    def getInstance() -> CalendarValidator:
        return CalendarValidator.__VALIDATOR

    # Class Methods End


CalendarValidator._CalendarValidator__VALIDATOR = CalendarValidator.CalendarValidator1()
