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


class TimeValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: TimeValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        return value

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
        return self._compareTime(value, compare, _CAL_HOUR_OF_DAY)

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
        return self._compareTime(value, compare, _CAL_MINUTE)

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
        return self._compareTime(value, compare, _CAL_SECOND)

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
        return self._compareTime(value, compare, _CAL_MILLISECOND)

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
    def TimeValidator1() -> TimeValidator:
        return TimeValidator(True, DATE_FORMAT_SHORT)

    def __init__(self, strict: bool, timeStyle: int) -> None:
        AbstractCalendarValidator.__init__(self, strict, -1, timeStyle)

    @staticmethod
    def getInstance() -> TimeValidator:
        return TimeValidator.__VALIDATOR

    # Class Methods End


TimeValidator._TimeValidator__VALIDATOR = TimeValidator.TimeValidator1()
