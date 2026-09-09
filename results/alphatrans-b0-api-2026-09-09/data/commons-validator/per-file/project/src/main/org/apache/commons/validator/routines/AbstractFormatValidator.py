from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from abc import ABC, abstractmethod

# Imports End

Format = typing.Any


class AbstractFormatValidator(ABC):

    # Class Fields Begin
    __serialVersionUID: int = -4690687565200568258
    __strict: bool = None
    # Class Fields End

    # Class Methods Begin
    def _parse(self, value: str, formatter: Format) -> typing.Any:
        pos_error_index = -1
        pos_index = 0

        parsed_value = None
        try:
            # Try to emulate java.text.Format.parseObject with ParsePosition
            if hasattr(formatter, "parseObject"):
                class _Pos:
                    def __init__(self):
                        self.index = 0
                        self.errorIndex = -1

                    def getIndex(self):
                        return self.index

                    def getErrorIndex(self):
                        return self.errorIndex

                pos = _Pos()
                parsed_value = formatter.parseObject(value, pos)
                pos_error_index = pos.getErrorIndex()
                pos_index = pos.getIndex()
            else:
                parsed_value = formatter.parse(value)
                pos_index = len(value)
        except Exception:
            return None

        if pos_error_index > -1:
            return None

        if self.isStrict() and pos_index < len(value):
            return None

        if parsed_value is not None:
            parsed_value = self._processParsedValue(parsed_value, formatter)

        return parsed_value

    def _format4(self, value: typing.Any, formatter: Format) -> str:
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
    def _getFormat(self, pattern: str, locale: typing.Any) -> Format:
        pass

    @abstractmethod
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        pass

    @abstractmethod
    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        pass

    # Class Methods End
