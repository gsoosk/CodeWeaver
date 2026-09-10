from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
import zoneinfo
import datetime
import typing
from typing import *
import io

# Imports End


CalendarLike = typing.Union[
    datetime.datetime,
    datetime.date,
    datetime.time,
    datetime.timedelta,
    datetime.timezone,
]


class CalendarValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = 9109652318762134167

    # java.util.Calendar field constants
    YEAR: int = 1
    MONTH: int = 2
    WEEK_OF_YEAR: int = 3
    DATE: int = 5

    __VALIDATOR: "CalendarValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        return value

    def compareYears(
        self,
        value: CalendarLike,
        compare: CalendarLike,
    ) -> int:
        return self._compare(value, compare, CalendarValidator.YEAR)

    def compareQuarters1(
        self,
        value: CalendarLike,
        compare: CalendarLike,
        monthOfFirstQuarter: int,
    ) -> int:
        return super()._compareQuarters(value, compare, monthOfFirstQuarter)

    def compareQuarters0(
        self,
        value: CalendarLike,
        compare: CalendarLike,
    ) -> int:
        return self.compareQuarters1(value, compare, 1)

    def compareMonths(
        self,
        value: CalendarLike,
        compare: CalendarLike,
    ) -> int:
        return self._compare(value, compare, CalendarValidator.MONTH)

    def compareWeeks(
        self,
        value: CalendarLike,
        compare: CalendarLike,
    ) -> int:
        return self._compare(value, compare, CalendarValidator.WEEK_OF_YEAR)

    def compareDates(
        self,
        value: CalendarLike,
        compare: CalendarLike,
    ) -> int:
        return self._compare(value, compare, CalendarValidator.DATE)

    @staticmethod
    def adjustToTimeZone(
        value: CalendarLike,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> "CalendarLike":
        if not isinstance(value, datetime.datetime):
            return value
        current_tz = value.tzinfo
        if current_tz is not None and current_tz == timeZone:
            return value.replace(tzinfo=timeZone)
        # keep the same "wall clock" fields, just change the timezone
        return value.replace(tzinfo=timeZone)

    def validate7(
        self,
        value: str,
        pattern: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> CalendarLike:
        return self._parse(value, pattern, locale, timeZone)

    def validate6(self, value: str, pattern: str, locale: typing.Any) -> CalendarLike:
        return self._parse(value, pattern, locale, None)

    def validate5(
        self,
        value: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> CalendarLike:
        return self._parse(value, None, locale, timeZone)

    def validate4(self, value: str, locale: typing.Any) -> CalendarLike:
        return self._parse(value, None, locale, None)

    def validate3(
        self,
        value: str,
        pattern: str,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> CalendarLike:
        return self._parse(value, pattern, None, timeZone)

    def validate2(self, value: str, pattern: str) -> CalendarLike:
        return self._parse(value, pattern, None, None)

    def validate1(
        self, value: str, timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone]
    ) -> CalendarLike:
        return self._parse(value, None, None, timeZone)

    def validate0(self, value: str) -> CalendarLike:
        return self._parse(value, None, None, None)

    @staticmethod
    def CalendarValidator1() -> "CalendarValidator":
        return CalendarValidator(True, AbstractCalendarValidator.SHORT if hasattr(AbstractCalendarValidator, "SHORT") else 3)

    def __init__(self, strict: bool, dateStyle: int) -> None:
        super().__init__(strict, dateStyle, -1)

    @staticmethod
    def getInstance() -> "CalendarValidator":
        return CalendarValidator.__VALIDATOR

    # Class Methods End


CalendarValidator._CalendarValidator__VALIDATOR = CalendarValidator.CalendarValidator1()
