from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractCalendarValidator import *
import zoneinfo
import datetime
import typing
from typing import *
import io

# Imports End


class DateValidator(AbstractCalendarValidator):

    # Class Fields Begin
    __serialVersionUID: int = -3966328400469953190
    __VALIDATOR: "DateValidator" = None

    # java.text.DateFormat.SHORT
    __DATE_FORMAT_SHORT: int = 3

    # java.util.Calendar field constants used for comparisons
    __CAL_YEAR: int = 1
    __CAL_MONTH: int = 2
    __CAL_WEEK_OF_YEAR: int = 3
    __CAL_DATE: int = 5
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        return value

    def compareYears(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendarValue = self.__getCalendar(value, timeZone)
        calendarCompare = self.__getCalendar(compare, timeZone)
        return self.compare(calendarValue, calendarCompare, self.__CAL_YEAR)

    def compareQuarters1(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
        monthOfFirstQuarter: int,
    ) -> int:
        calendarValue = self.__getCalendar(value, timeZone)
        calendarCompare = self.__getCalendar(compare, timeZone)
        return super().compareQuarters(calendarValue, calendarCompare, monthOfFirstQuarter)

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
        calendarValue = self.__getCalendar(value, timeZone)
        calendarCompare = self.__getCalendar(compare, timeZone)
        return self.compare(calendarValue, calendarCompare, self.__CAL_MONTH)

    def compareWeeks(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendarValue = self.__getCalendar(value, timeZone)
        calendarCompare = self.__getCalendar(compare, timeZone)
        return self.compare(calendarValue, calendarCompare, self.__CAL_WEEK_OF_YEAR)

    def compareDates(
        self,
        value: typing.Union[datetime.datetime, datetime.date],
        compare: typing.Union[datetime.datetime, datetime.date],
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> int:
        calendarValue = self.__getCalendar(value, timeZone)
        calendarCompare = self.__getCalendar(compare, timeZone)
        return self.compare(calendarValue, calendarCompare, self.__CAL_DATE)

    def validate7(
        self,
        value: str,
        pattern: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, pattern, locale, timeZone)

    def validate6(
        self, value: str, pattern: str, locale: typing.Any
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, pattern, locale, None)

    def validate5(
        self,
        value: str,
        locale: typing.Any,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, None, locale, timeZone)

    def validate4(
        self, value: str, locale: typing.Any
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, None, locale, None)

    def validate3(
        self,
        value: str,
        pattern: str,
        timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone],
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, pattern, None, timeZone)

    def validate2(
        self, value: str, pattern: str
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, pattern, None, None)

    def validate1(
        self, value: str, timeZone: typing.Union[zoneinfo.ZoneInfo, datetime.timezone]
    ) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, None, None, timeZone)

    def validate0(self, value: str) -> typing.Union[datetime.datetime, datetime.date]:
        return self.parse(value, None, None, None)

    @staticmethod
    def DateValidator1() -> "DateValidator":
        return DateValidator(True, DateValidator.__DATE_FORMAT_SHORT)

    def __init__(self, strict: bool, dateStyle: int) -> None:
        super().__init__(strict, dateStyle, -1)

    @staticmethod
    def getInstance() -> "DateValidator":
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
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = datetime.datetime.combine(value, datetime.time.min, tzinfo=datetime.timezone.utc)

        if timeZone is not None:
            return dt.astimezone(timeZone)
        return dt.astimezone()

    # Class Methods End


DateValidator._DateValidator__VALIDATOR = DateValidator.DateValidator1()
