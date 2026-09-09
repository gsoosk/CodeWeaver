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

    # java.text.DateFormat.SHORT constant value
    _SHORT_STYLE: int = 3

    # java.util.Calendar field constants (values match java.util.Calendar)
    _HOUR_OF_DAY: int = 11
    _MINUTE: int = 12
    _SECOND: int = 13
    _MILLISECOND: int = 14
    # Class Fields End

    # Class Methods Begin
    def __init__(self, strict: bool, timeStyle: int) -> None:
        super().__init__(strict, -1, timeStyle)

    @staticmethod
    def TimeValidator1() -> "TimeValidator":
        return TimeValidator(True, TimeValidator._SHORT_STYLE)

    @staticmethod
    def getInstance() -> "TimeValidator":
        return TimeValidator.__VALIDATOR

    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        return value

    def _timeTuple(self, val: typing.Any, field: int) -> typing.Tuple:
        hour = getattr(val, "hour", 0)
        minute = getattr(val, "minute", 0)
        second = getattr(val, "second", 0)
        micro = getattr(val, "microsecond", 0)
        millis = micro // 1000

        if field == TimeValidator._HOUR_OF_DAY:
            return (hour,)
        elif field == TimeValidator._MINUTE:
            return (hour, minute)
        elif field == TimeValidator._SECOND:
            return (hour, minute, second)
        else:
            return (hour, minute, second, millis)

    def _compareTime(self, value: typing.Any, compare: typing.Any, field: int) -> int:
        v = self._timeTuple(value, field)
        c = self._timeTuple(compare, field)
        if v < c:
            return -1
        elif v > c:
            return 1
        return 0

    def compareTime(
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
        return self._compareTime(value, compare, TimeValidator._MILLISECOND)

    def compareSeconds(
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
        return self._compareTime(value, compare, TimeValidator._SECOND)

    def compareMinutes(
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
        return self._compareTime(value, compare, TimeValidator._MINUTE)

    def compareHours(
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
        return self._compareTime(value, compare, TimeValidator._HOUR_OF_DAY)

    def validate0(self, value: str) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self._parse(value, None, None, None)

    def validate1(
        self, value: str, timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone]
    ) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self._parse(value, None, None, timeZone)

    def validate2(self, value: str, pattern: str) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self._parse(value, pattern, None, None)

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
        return self._parse(value, pattern, None, timeZone)

    def validate4(self, value: str, locale: typing.Any) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self._parse(value, None, locale, None)

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
        return self._parse(value, None, locale, timeZone)

    def validate6(self, value: str, pattern: str, locale: typing.Any) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        return self._parse(value, pattern, locale, None)

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

    # Class Methods End


TimeValidator._TimeValidator__VALIDATOR = TimeValidator.TimeValidator1()
