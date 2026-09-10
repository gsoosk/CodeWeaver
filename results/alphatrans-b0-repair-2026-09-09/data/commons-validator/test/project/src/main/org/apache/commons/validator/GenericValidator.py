from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.UrlValidator import *
from src.main.org.apache.commons.validator.routines.EmailValidator import *
from src.main.org.apache.commons.validator.routines.DateValidator import *
from src.main.org.apache.commons.validator.routines.CreditCardValidator import *
from src.main.org.apache.commons.validator.GenericTypeValidator import *
from src.main.org.apache.commons.validator.DateValidator import *
import typing
from typing import *
import io

# Imports End

import re
from src.main.org.apache.commons.validator.routines.DateValidator import DateValidator as _RoutinesDateValidator


class GenericValidator:

    # Class Fields Begin
    __serialVersionUID: int = -7212095066891517618
    __URL_VALIDATOR: UrlValidator = None
    __CREDIT_CARD_VALIDATOR: CreditCardValidator = None
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def maxValue3(value: float, max_: float) -> bool:
        return value <= max_

    @staticmethod
    def maxValue2(value: float, max_: float) -> bool:
        return value <= max_

    @staticmethod
    def maxValue1(value: int, max_: int) -> bool:
        return value <= max_

    @staticmethod
    def maxValue0(value: int, max_: int) -> bool:
        return value <= max_

    @staticmethod
    def minValue3(value: float, min_: float) -> bool:
        return value >= min_

    @staticmethod
    def minValue2(value: float, min_: float) -> bool:
        return value >= min_

    @staticmethod
    def minValue1(value: int, min_: int) -> bool:
        return value >= min_

    @staticmethod
    def minValue0(value: int, min_: int) -> bool:
        return value >= min_

    @staticmethod
    def minLength1(value: str, min_: int, lineEndLength: int) -> bool:
        adjustAmount = GenericValidator._GenericValidator__adjustForLineEnding(value, lineEndLength)
        return (len(value) + adjustAmount) >= min_

    @staticmethod
    def minLength0(value: str, min_: int) -> bool:
        return len(value) >= min_

    @staticmethod
    def maxLength1(value: str, max_: int, lineEndLength: int) -> bool:
        adjustAmount = GenericValidator._GenericValidator__adjustForLineEnding(value, lineEndLength)
        return (len(value) + adjustAmount) <= max_

    @staticmethod
    def maxLength0(value: str, max_: int) -> bool:
        return len(value) <= max_

    @staticmethod
    def isUrl(value: str) -> bool:
        if GenericValidator.__URL_VALIDATOR is None:
            GenericValidator.__URL_VALIDATOR = UrlValidator.UrlValidator6()
        return GenericValidator.__URL_VALIDATOR.isValid(value)

    @staticmethod
    def isEmail(value: str) -> bool:
        return EmailValidator.getInstance0().isValid(value)

    @staticmethod
    def isCreditCard(value: str) -> bool:
        if GenericValidator.__CREDIT_CARD_VALIDATOR is None:
            GenericValidator.__CREDIT_CARD_VALIDATOR = CreditCardValidator.CreditCardValidator0()
        return GenericValidator.__CREDIT_CARD_VALIDATOR.isValid(value)

    @staticmethod
    def isInRange5(value: float, min_: float, max_: float) -> bool:
        return (value >= min_) and (value <= max_)

    @staticmethod
    def isInRange4(value: int, min_: int, max_: int) -> bool:
        return (value >= min_) and (value <= max_)

    @staticmethod
    def isInRange3(value: int, min_: int, max_: int) -> bool:
        return (value >= min_) and (value <= max_)

    @staticmethod
    def isInRange2(value: float, min_: float, max_: float) -> bool:
        return (value >= min_) and (value <= max_)

    @staticmethod
    def isInRange1(value: int, min_: int, max_: int) -> bool:
        return (value >= min_) and (value <= max_)

    @staticmethod
    def isInRange0(value: int, min_: int, max_: int) -> bool:
        return (value >= min_) and (value <= max_)

    @staticmethod
    def isDate1(value: str, datePattern: str, strict: bool) -> bool:
        return DateValidator.getInstance().isValid0(value, datePattern, strict)

    @staticmethod
    def isDate0(value: str, locale: typing.Any) -> bool:
        return _RoutinesDateValidator.getInstance().isValid2(value, locale)

    @staticmethod
    def isDouble(value: str) -> bool:
        return GenericTypeValidator.formatDouble0(value) is not None

    @staticmethod
    def isFloat(value: str) -> bool:
        return GenericTypeValidator.formatFloat0(value) is not None

    @staticmethod
    def isLong(value: str) -> bool:
        return GenericTypeValidator.formatLong0(value) is not None

    @staticmethod
    def isInt(value: str) -> bool:
        return GenericTypeValidator.formatInt0(value) is not None

    @staticmethod
    def isShort(value: str) -> bool:
        return GenericTypeValidator.formatShort0(value) is not None

    @staticmethod
    def isByte(value: str) -> bool:
        return GenericTypeValidator.formatByte0(value) is not None

    @staticmethod
    def matchRegexp(value: str, regexp: str) -> bool:
        if regexp is None or len(regexp) <= 0:
            return False
        if value is None:
            return False
        return re.fullmatch(regexp, value) is not None

    @staticmethod
    def isBlankOrNull(value: str) -> bool:
        return (value is None) or (len(value.strip()) == 0)

    @staticmethod
    def __adjustForLineEnding(value: str, lineEndLength: int) -> int:
        nCount = 0
        rCount = 0
        for ch in value:
            if ch == '\n':
                nCount += 1
            if ch == '\r':
                rCount += 1
        return (nCount * lineEndLength) - (rCount + nCount)

    # Class Methods End
