from __future__ import annotations

# Imports Begin
import typing
import re
from typing import *
import io

# Imports End


class RegexValidator:

    # Class Fields Begin
    __serialVersionUID: int = -8832409930574867162
    __patterns: typing.List[re.Pattern] = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        buffer = io.StringIO()
        buffer.write("RegexValidator{")
        for i, pattern in enumerate(self.__patterns):
            if i > 0:
                buffer.write(",")
            buffer.write(pattern.pattern)
        buffer.write("}")
        return buffer.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def validate(self, value: str) -> str:
        if value is None:
            return None
        for pattern in self.__patterns:
            matcher = pattern.match(value)
            if matcher is not None and matcher.group(0) == value:
                count = matcher.re.groups
                if count == 1:
                    return matcher.group(1)
                buffer = io.StringIO()
                for j in range(count):
                    component = matcher.group(j + 1)
                    if component is not None:
                        buffer.write(component)
                return buffer.getvalue()
        return None

    def match(self, value: str) -> typing.List[str]:
        if value is None:
            return None
        for pattern in self.__patterns:
            matcher = pattern.match(value)
            if matcher is not None and matcher.group(0) == value:
                count = matcher.re.groups
                groups = []
                for j in range(count):
                    groups.append(matcher.group(j + 1))
                return groups
        return None

    def isValid(self, value: str) -> bool:
        if value is None:
            return False
        for pattern in self.__patterns:
            matcher = pattern.match(value)
            if matcher is not None and matcher.group(0) == value:
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

    def __init__(
        self, regexs: typing.List[str], caseSensitive: bool
    ) -> None:
        if regexs is None or len(regexs) == 0:
            raise ValueError("Regular expressions are missing")
        patterns = []
        flags = 0 if caseSensitive else re.IGNORECASE
        for i, regex in enumerate(regexs):
            if regex is None or len(regex) == 0:
                raise ValueError(f"Regular expression[{i}] is missing")
            patterns.append(re.compile(regex, flags))
        self.__patterns = patterns

    # Class Methods End
