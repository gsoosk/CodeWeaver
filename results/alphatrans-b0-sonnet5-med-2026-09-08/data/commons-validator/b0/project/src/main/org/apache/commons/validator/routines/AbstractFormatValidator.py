from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from abc import ABC, abstractmethod

# Imports End


class _ParsePosition:
    def __init__(self, index: int = 0):
        self.index = index
        self.error_index = -1


class AbstractFormatValidator(ABC):

    # Class Fields Begin
    __serialVersionUID: int = -4690687565200568258
    __strict: bool = None
    # Class Fields End

    # Class Methods Begin
    def _parse(self, value: str, formatter: typing.Any) -> typing.Any:
        pos = _ParsePosition(0)
        parsedValue = formatter.parseObject(value, pos)
        if pos.error_index > -1:
            return None
        if self.isStrict() and pos.index < len(value):
            return None
        if parsedValue is not None:
            parsedValue = self._processParsedValue(parsedValue, formatter)
        return parsedValue

    def _format4(self, value: typing.Any, formatter: typing.Any) -> str:
        return formatter.format(value)

    def format3(self, value: typing.Any, pattern: str, locale: typing.Any) -> str:
        formatter = self._getFormat(pattern, locale)
        return self._format4(value, formatter)

    def format2(self, value: typing.Any, locale: typing.Any) -> str:
        return self.format3(value, None, locale)

    def format1(self, value: typing.Any, pattern: str) -> str:
        return self.format3(value, pattern, None)

    def format0(self, value: typing.Any) -> str:
        return self.format3(value, None, None)

    def isValid2(self, value: str, locale: typing.Any) -> bool:
        return self.isValid3(value, None, locale)

    def isValid1(self, value: str, pattern: str) -> bool:
        return self.isValid3(value, pattern, None)

    def isValid0(self, value: str) -> bool:
        return self.isValid3(value, None, None)

    def isStrict(self) -> bool:
        return self.__strict

    def __init__(self, strict: bool) -> None:
        self.__strict = strict

    @abstractmethod
    def _getFormat(self, pattern: str, locale: typing.Any) -> typing.Any:
        raise NotImplementedError

    @abstractmethod
    def _processParsedValue(self, value: typing.Any, formatter: typing.Any) -> typing.Any:
        raise NotImplementedError

    @abstractmethod
    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        raise NotImplementedError

    # Class Methods End
