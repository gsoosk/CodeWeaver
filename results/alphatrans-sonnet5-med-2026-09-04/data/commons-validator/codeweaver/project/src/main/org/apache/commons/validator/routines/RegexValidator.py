from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
import re

# Imports End


class RegexValidator:

    # Class Fields Begin
    __serialVersionUID: int = None
    __patterns: typing.List[re.Pattern] = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        buffer = "RegexValidator{"
        for i, pattern in enumerate(self.__patterns):
            if i > 0:
                buffer += ","
            buffer += pattern.pattern
        buffer += "}"
        return buffer

    def __str__(self) -> str:
        return self.toString()

    def validate(self, value: str) -> str:
        if value is None:
            return None
        for pattern in self.__patterns:
            matcher = pattern.fullmatch(value)
            if matcher is not None:
                count = matcher.re.groups
                if count == 1:
                    return matcher.group(1)
                buffer = ""
                for j in range(count):
                    component = matcher.group(j + 1)
                    if component is not None:
                        buffer += component
                return buffer
        return None

    def match(self, value: str) -> typing.List[typing.List[str]]:
        if value is None:
            return None
        for pattern in self.__patterns:
            matcher = pattern.fullmatch(value)
            if matcher is not None:
                count = matcher.re.groups
                groups = [matcher.group(j + 1) for j in range(count)]
                return groups
        return None

    def isValid(self, value: str) -> bool:
        if value is None:
            return False
        for pattern in self.__patterns:
            if pattern.fullmatch(value) is not None:
                return True
        return False

    @staticmethod
    def RegexValidator3(regex: str) -> RegexValidator:
        return RegexValidator.RegexValidator2(regex, True)

    @staticmethod
    def RegexValidator2(regex: str, caseSensitive: bool) -> RegexValidator:
        return RegexValidator([regex], caseSensitive)

    @staticmethod
    def RegexValidator1(regexs: typing.List[typing.List[str]]) -> RegexValidator:
        return RegexValidator(regexs, True)

    def __init__(
        self, regexs: typing.List[typing.List[str]], caseSensitive: bool
    ) -> None:
        if regexs is None or len(regexs) == 0:
            raise ValueError("Regular expressions are missing")
        flags = 0 if caseSensitive else re.IGNORECASE
        patterns = []
        for i, regex in enumerate(regexs):
            if regex is None or len(regex) == 0:
                raise ValueError("Regular expression[" + str(i) + "] is missing")
            patterns.append(re.compile(regex, flags))
        self.__patterns = patterns

    # Class Methods End
