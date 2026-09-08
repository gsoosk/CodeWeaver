from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
import zoneinfo
import datetime
import typing
from typing import *
import io

# Imports End


class CalendarValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = 9109652318762134167
    __VALIDATOR: "CalendarValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        return formatter.getCalendar()

    def compareYears(self, value, compare) -> int:
        return self._compare(value, compare, "year")

    def compareQuarters1(self, value, compare, monthOfFirstQuarter: int) -> int:
        return super()._compareQuarters(value, compare, monthOfFirstQuarter)

    def compareQuarters0(self, value, compare) -> int:
        return self.compareQuarters1(value, compare, 1)

    def compareMonths(self, value, compare) -> int:
        return self._compare(value, compare, "month")

    def compareWeeks(self, value, compare) -> int:
        return self._compare(value, compare, "week")

    def compareDates(self, value, compare) -> int:
        return self._compare(value, compare, "day")

    @staticmethod
    def adjustToTimeZone(value, timeZone) -> None:
        pass

    def validate7(self, value: str, pattern: str, locale: typing.Any, timeZone):
        return self._parse(value, pattern, locale, timeZone)

    def validate6(self, value: str, pattern: str, locale: typing.Any):
        return self._parse(value, pattern, locale, None)

    def validate5(self, value: str, locale: typing.Any, timeZone):
        return self._parse(value, None, locale, timeZone)

    def validate4(self, value: str, locale: typing.Any):
        return self._parse(value, None, locale, None)

    def validate3(self, value: str, pattern: str, timeZone):
        return self._parse(value, pattern, None, timeZone)

    def validate2(self, value: str, pattern: str):
        return self._parse(value, pattern, None, None)

    def validate1(self, value: str, timeZone):
        return self._parse(value, None, None, timeZone)

    def validate0(self, value: str):
        return self._parse(value, None, None, None)

    @staticmethod
    def CalendarValidator1() -> "CalendarValidator":
        return CalendarValidator(True, SHORT)

    def __init__(self, strict: bool, dateStyle: int) -> None:
        super().__init__(strict, dateStyle, -1)

    @staticmethod
    def getInstance() -> "CalendarValidator":
        return CalendarValidator.__VALIDATOR

    # Class Methods End


CalendarValidator._CalendarValidator__VALIDATOR = CalendarValidator.CalendarValidator1()
