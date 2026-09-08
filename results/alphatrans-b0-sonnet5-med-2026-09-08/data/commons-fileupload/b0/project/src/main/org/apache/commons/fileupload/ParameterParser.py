from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.util.mime.MimeUtility import *
import os
import typing
from typing import *
import io

# Imports End


class ParameterParser:

    # Class Fields Begin
    __chars: typing.List[str] = None
    __pos: int = None
    __len: int = None
    __i1: int = None
    __i2: int = None
    __lowerCaseNames: bool = None
    # Class Fields End

    # Class Methods Begin
    def parse3(
        self, charArray: typing.List[str], offset: int, length: int, separator: str
    ) -> typing.Dict[str, str]:
        if charArray is None:
            return {}

        params: typing.Dict[str, str] = {}
        self.__chars = charArray
        self.__pos = offset
        self.__len = length

        while self.__hasChar():
            paramName = self.__parseToken(["=", separator])
            paramValue = None
            if self.__hasChar() and (charArray[self.__pos] == "="):
                self.__pos += 1  # skip '='
                paramValue = self.__parseQuotedToken([separator])

                if paramValue is not None:
                    try:
                        paramValue = MimeUtility.decodeText(paramValue)
                    except Exception:
                        pass

            if self.__hasChar() and (charArray[self.__pos] == separator):
                self.__pos += 1  # skip separator

            if (paramName is not None) and (len(paramName) > 0):
                if self.__lowerCaseNames:
                    paramName = paramName.lower()

                params[paramName] = paramValue
        return params

    def parse2(
        self, charArray: typing.List[str], separator: str
    ) -> typing.Dict[str, str]:
        if charArray is None:
            return {}
        return self.parse3(charArray, 0, len(charArray), separator)

    def parse1(self, str_: str, separator: str) -> typing.Dict[str, str]:
        if str_ is None:
            return {}
        return self.parse2(list(str_), separator)

    def parse0(self, str_: str, separators: typing.List[str]) -> typing.Dict[str, str]:
        if separators is None or len(separators) == 0:
            return {}
        separator = separators[0]
        if str_ is not None:
            idx = len(str_)
            for separator2 in separators:
                tmp = str_.find(separator2)
                if tmp != -1 and tmp < idx:
                    idx = tmp
                    separator = separator2
        return self.parse1(str_, separator)

    def setLowerCaseNames(self, b: bool) -> None:
        self.__lowerCaseNames = b

    def isLowerCaseNames(self) -> bool:
        return self.__lowerCaseNames

    def __init__(self) -> None:
        self.__chars = None
        self.__pos = 0
        self.__len = 0
        self.__i1 = 0
        self.__i2 = 0
        self.__lowerCaseNames = False

    def __parseQuotedToken(self, terminators: typing.List[str]) -> str:
        self.__i1 = self.__pos
        self.__i2 = self.__pos
        quoted = False
        charEscaped = False
        while self.__hasChar():
            ch = self.__chars[self.__pos]
            if (not quoted) and self.__isOneOf(ch, terminators):
                break
            if (not charEscaped) and ch == '"':
                quoted = not quoted
            charEscaped = (not charEscaped) and ch == "\\"
            self.__i2 += 1
            self.__pos += 1
        return self.__getToken(True)

    def __parseToken(self, terminators: typing.List[str]) -> str:
        self.__i1 = self.__pos
        self.__i2 = self.__pos
        while self.__hasChar():
            ch = self.__chars[self.__pos]
            if self.__isOneOf(ch, terminators):
                break
            self.__i2 += 1
            self.__pos += 1
        return self.__getToken(False)

    def __isOneOf(self, ch: str, charray: typing.List[str]) -> bool:
        for element in charray:
            if ch == element:
                return True
        return False

    def __getToken(self, quoted: bool) -> str:
        i1 = self.__i1
        i2 = self.__i2
        chars = self.__chars
        while (i1 < i2) and (chars[i1].isspace()):
            i1 += 1
        while (i2 > i1) and (chars[i2 - 1].isspace()):
            i2 -= 1
        if quoted and ((i2 - i1) >= 2) and (chars[i1] == '"') and (chars[i2 - 1] == '"'):
            i1 += 1
            i2 -= 1
        result = None
        if i2 > i1:
            result = "".join(chars[i1:i2])
        return result

    def __hasChar(self) -> bool:
        return self.__pos < self.__len

    # Class Methods End
