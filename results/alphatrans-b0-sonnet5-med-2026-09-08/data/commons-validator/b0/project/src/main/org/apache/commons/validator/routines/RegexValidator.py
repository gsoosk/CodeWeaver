from __future__ import annotations

# Imports Begin
import re
import typing
from typing import *
import io

# Imports End


class RegexValidator:

    # Class Fields Begin
    __serialVersionUID: int = -8832409930574867162
    __patterns: typing.List[typing.Any] = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        buffer = io.StringIO()
        buffer.write("RegexValidator{")
        for i, p in enumerate(self.__patterns):
            if i > 0:
                buffer.write(",")
            buffer.write(p.pattern)
        buffer.write("}")
        return buffer.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def validate(self, value: str) -> str:
        if value is None:
            return None
        for pattern in self.__patterns:
            m = pattern.fullmatch(value)
            if m:
                count = len(m.groups())
                if count == 1:
                    return m.group(1)
                buffer = io.StringIO()
                for j in range(count):
                    component = m.group(j + 1)
                    if component is not None:
                        buffer.write(component)
                return buffer.getvalue()
        return None

    def match(self, value: str) -> typing.List[str]:
        if value is None:
            return None
        for pattern in self.__patterns:
            m = pattern.fullmatch(value)
            if m:
                count = len(m.groups())
                groups = [None] * count
                for j in range(count):
                    groups[j] = m.group(j + 1)
                return groups
        return None

    def isValid(self, value: str) -> bool:
        if value is None:
            return False
        for pattern in self.__patterns:
            if pattern.fullmatch(value):
                return True
        return False

    @staticmethod
    def RegexValidator3(regex: str) -> "RegexValidator":
        return RegexValidator.RegexValidator2(regex, True)

    @staticmethod
    def RegexValidator2(regex: str, caseSensitive: bool) -> "RegexValidator":
        return RegexValidator([regex], caseSensitive)

    @staticmethod
    def RegexValidator1(regexs: typing.List[str]) -> "RegexValidator":
        return RegexValidator(regexs, True)

    def __init__(self, regexs: typing.List[str], caseSensitive: bool) -> None:
        if regexs is None or len(regexs) == 0:
            raise ValueError("Regular expressions are missing")
        self.__patterns = []
        flags = 0 if caseSensitive else re.IGNORECASE
        for i in range(len(regexs)):
            if regexs[i] is None or len(regexs[i]) == 0:
                raise ValueError("Regular expression[" + str(i) + "] is missing")
            self.__patterns.append(re.compile(regexs[i], flags))

    # Class Methods End
