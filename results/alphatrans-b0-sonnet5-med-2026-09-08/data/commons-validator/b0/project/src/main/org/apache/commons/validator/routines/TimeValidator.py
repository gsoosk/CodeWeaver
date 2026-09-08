from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
import zoneinfo
import datetime
import typing
from typing import *
import io

# Imports End


class TimeValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = 3494007492269691581
    __VALIDATOR: "TimeValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        return formatter.getCalendar()

    def compareHours(self, value, compare) -> int:
        return self._compareTime(value, compare, "hour")

    def compareMinutes(self, value, compare) -> int:
        return self._compareTime(value, compare, "minute")

    def compareSeconds(self, value, compare) -> int:
        return self._compareTime(value, compare, "second")

    def compareTime(self, value, compare) -> int:
        return self._compareTime(value, compare, "millisecond")

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
    def TimeValidator1() -> "TimeValidator":
        return TimeValidator(True, SHORT)

    def __init__(self, strict: bool, timeStyle: int) -> None:
        super().__init__(strict, -1, timeStyle)

    @staticmethod
    def getInstance() -> "TimeValidator":
        return TimeValidator.__VALIDATOR

    # Class Methods End


TimeValidator._TimeValidator__VALIDATOR = TimeValidator.TimeValidator1()
