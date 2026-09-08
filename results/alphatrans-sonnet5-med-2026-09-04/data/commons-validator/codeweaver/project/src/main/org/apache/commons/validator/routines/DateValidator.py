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


class DateValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: DateValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        # Mirrors Java's ``DateValidator.processParsedValue``, which simply
        # returns the parsed ``Calendar``'s ``getTime()`` value unchanged --
        # the resolved time zone (attached by ``AbstractCalendarValidator``)
        # is preserved rather than stripped.
        return value

    def compareYears(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendar_value = self.__getCalendar(value, timeZone)
        calendar_compare = self.__getCalendar(compare, timeZone)
        return self._compare(calendar_value, calendar_compare, _CAL_YEAR)

    def compareQuarters1(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
        monthOfFirstQuarter: int,
    ) -> int:
        calendar_value = self.__getCalendar(value, timeZone)
        calendar_compare = self.__getCalendar(compare, timeZone)
        return self._compareQuarters(calendar_value, calendar_compare, monthOfFirstQuarter)

    def compareQuarters0(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        return self.compareQuarters1(value, compare, timeZone, 1)

    def compareMonths(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendar_value = self.__getCalendar(value, timeZone)
        calendar_compare = self.__getCalendar(compare, timeZone)
        return self._compare(calendar_value, calendar_compare, _CAL_MONTH)

    def compareWeeks(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendar_value = self.__getCalendar(value, timeZone)
        calendar_compare = self.__getCalendar(compare, timeZone)
        return self._compare(calendar_value, calendar_compare, _CAL_WEEK_OF_YEAR)

    def compareDates(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendar_value = self.__getCalendar(value, timeZone)
        calendar_compare = self.__getCalendar(compare, timeZone)
        return self._compare(calendar_value, calendar_compare, _CAL_DATE)

    def validate7(
        self,
        value: str,
        pattern: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self._parse(value, pattern, locale, timeZone)

    def validate6(
        self, value: str, pattern: str, locale: typing.Any
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, pattern, locale, None)

    def validate5(
        self,
        value: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, None, locale, timeZone)

    def validate4(
        self, value: str, locale: typing.Any
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, None, locale, None)

    def validate3(
        self,
        value: str,
        pattern: str,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, pattern, None, timeZone)

    def validate2(
        self, value: str, pattern: str
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, pattern, None, None)

    def validate1(
        self, value: str, timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone]
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, None, None, timeZone)

    def validate0(self, value: str) -> typing.Union[datetime.datetime, datetime.date]:
        return self.validate7(value, None, None, None)

    @staticmethod
    def DateValidator1() -> DateValidator:
        return DateValidator(True, DATE_FORMAT_SHORT)

    def __init__(self, strict: bool, dateStyle: int) -> None:
        AbstractCalendarValidator.__init__(self, strict, dateStyle, -1)

    @staticmethod
    def getInstance() -> DateValidator:
        return DateValidator.__VALIDATOR

    def __getCalendar(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        datetime.timezone,
    ]:
        if isinstance(value, datetime.datetime):
            dt = value
        else:
            dt = datetime.datetime(value.year, value.month, value.day)
        if timeZone is not None:
            if dt.tzinfo is not None:
                dt = dt.astimezone(timeZone)
            else:
                dt = dt.replace(tzinfo=timeZone)
        return dt

    # Class Methods End


DateValidator._DateValidator__VALIDATOR = DateValidator.DateValidator1()
