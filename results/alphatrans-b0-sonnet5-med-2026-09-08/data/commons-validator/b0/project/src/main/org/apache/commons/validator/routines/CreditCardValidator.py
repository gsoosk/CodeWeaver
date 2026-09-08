from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.LuhnCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
from src.main.org.apache.commons.validator.routines.RegexValidator import *
from src.main.org.apache.commons.validator.routines.CodeValidator import *
from src.main.org.apache.commons.validator.util.Flags import *
import typing
from typing import *
import io

# Imports End


class CreditCardRange:

    # Class Fields Begin
    low: str = None
    high: str = None
    minLen: int = None
    maxLen: int = None
    lengths: typing.List[int] = None
    # Class Fields End

    # Class Methods Begin
    def __init__(
        self,
        constructorId: int,
        low: str,
        high: str,
        minLen: int,
        maxLen: int,
        lengths: typing.List[int],
    ) -> None:
        if constructorId == 0:
            self.low = low
            self.high = high
            self.minLen = minLen
            self.maxLen = maxLen
            self.lengths = None
        else:
            self.low = low
            self.high = high
            self.minLen = -1
            self.maxLen = -1
            self.lengths = list(lengths)

    # Class Methods End


_MIN_CC_LENGTH = 12
_MAX_CC_LENGTH = 19

_LUHN_VALIDATOR = LuhnCheckDigit.LUHN_CHECK_DIGIT

_AMEX_VALIDATOR = CodeValidator.CodeValidator5(r"^(3[47]\d{13})$", _LUHN_VALIDATOR)
_DINERS_VALIDATOR = CodeValidator.CodeValidator5(
    r"^(30[0-5]\d{11}|3095\d{10}|36\d{12}|3[8-9]\d{12})$", _LUHN_VALIDATOR
)
_DISCOVER_REGEX = RegexValidator.RegexValidator1(
    [r"^(6011\d{12,13})$", r"^(64[4-9]\d{13})$", r"^(65\d{14})$", r"^(62[2-8]\d{13})$"]
)
_DISCOVER_VALIDATOR = CodeValidator.CodeValidator2(_DISCOVER_REGEX, _LUHN_VALIDATOR)
_MASTERCARD_REGEX = RegexValidator.RegexValidator1(
    [
        r"^(5[1-5]\d{14})$",
        r"^(2221\d{12})$",
        r"^(222[2-9]\d{12})$",
        r"^(22[3-9]\d{13})$",
        r"^(2[3-6]\d{14})$",
        r"^(27[01]\d{13})$",
        r"^(2720\d{12})$",
    ]
)
_MASTERCARD_VALIDATOR = CodeValidator.CodeValidator2(_MASTERCARD_REGEX, _LUHN_VALIDATOR)
_MASTERCARD_VALIDATOR_PRE_OCT2016 = CodeValidator.CodeValidator5(r"^(5[1-5]\d{14})$", _LUHN_VALIDATOR)
_VISA_VALIDATOR = CodeValidator.CodeValidator5(r"^(4)(\d{12}|\d{15})$", _LUHN_VALIDATOR)
_VPAY_VALIDATOR = CodeValidator.CodeValidator5(r"^(4)(\d{12,18})$", _LUHN_VALIDATOR)


class CreditCardValidator:

    # Class Fields Begin
    NONE: int = 0
    AMEX: int = 1 << 0
    VISA: int = 1 << 1
    MASTERCARD: int = 1 << 2
    DISCOVER: int = 1 << 3
    DINERS: int = 1 << 4
    VPAY: int = 1 << 5
    MASTERCARD_PRE_OCT2016: int = 1 << 6
    __cardTypes: typing.List[CodeValidator] = None
    __LUHN_VALIDATOR: CheckDigit = _LUHN_VALIDATOR
    AMEX_VALIDATOR: CodeValidator = _AMEX_VALIDATOR
    DINERS_VALIDATOR: CodeValidator = _DINERS_VALIDATOR
    __DISCOVER_REGEX: RegexValidator = _DISCOVER_REGEX
    DISCOVER_VALIDATOR: CodeValidator = _DISCOVER_VALIDATOR
    __MASTERCARD_REGEX: RegexValidator = _MASTERCARD_REGEX
    MASTERCARD_VALIDATOR: CodeValidator = _MASTERCARD_VALIDATOR
    MASTERCARD_VALIDATOR_PRE_OCT2016: CodeValidator = _MASTERCARD_VALIDATOR_PRE_OCT2016
    VISA_VALIDATOR: CodeValidator = _VISA_VALIDATOR
    VPAY_VALIDATOR: CodeValidator = _VPAY_VALIDATOR
    __serialVersionUID: int = 5955978921148959496
    __MIN_CC_LENGTH: int = _MIN_CC_LENGTH
    __MAX_CC_LENGTH: int = _MAX_CC_LENGTH
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def createRangeValidator(
        creditCardRanges: typing.List[CreditCardRange], digitCheck: CheckDigit
    ) -> CodeValidator:
        class _RangeRegex(RegexValidator):
            def __init__(self):
                super().__init__([r"(\d+)"], True)
                self.ccr = list(creditCardRanges)

            def validate(self, value: str) -> str:
                if super().match(value) is not None:
                    length = len(value)
                    for range_ in self.ccr:
                        if CreditCardValidator.validLength(length, range_):
                            if range_.high is None:
                                if value.startswith(range_.low):
                                    return value
                            elif range_.low <= value and range_.high >= value[0:len(range_.high)]:
                                return value
                return None

            def isValid(self, value: str) -> bool:
                return self.validate(value) is not None

            def match(self, value: str) -> typing.List[str]:
                return [self.validate(value)]

        return CodeValidator.CodeValidator2(_RangeRegex(), digitCheck)

    @staticmethod
    def validLength(valueLength: int, range_: CreditCardRange) -> bool:
        if range_.lengths is not None:
            for length in range_.lengths:
                if valueLength == length:
                    return True
            return False
        return valueLength >= range_.minLen and valueLength <= range_.maxLen

    def validate(self, card: str) -> typing.Any:
        if card is None or len(card) == 0:
            return None
        for cardType in self.__cardTypes:
            result = cardType.validate(card)
            if result is not None:
                return result
        return None

    def isValid(self, card: str) -> bool:
        if card is None or len(card) == 0:
            return False
        for cardType in self.__cardTypes:
            if cardType.isValid(card):
                return True
        return False

    @staticmethod
    def genericCreditCardValidator2() -> "CreditCardValidator":
        return CreditCardValidator.genericCreditCardValidator0(
            CreditCardValidator.__MIN_CC_LENGTH, CreditCardValidator.__MAX_CC_LENGTH
        )

    @staticmethod
    def genericCreditCardValidator1(length: int) -> "CreditCardValidator":
        return CreditCardValidator.genericCreditCardValidator0(length, length)

    @staticmethod
    def genericCreditCardValidator0(minLen: int, maxLen: int) -> "CreditCardValidator":
        return CreditCardValidator(
            1,
            0,
            None,
            [CodeValidator(1, _LUHN_VALIDATOR, maxLen, None, minLen, r"(\d+)")],
        )

    def __init__(
        self,
        constructorId: int,
        options: int,
        creditCardRanges: typing.List[CreditCardRange],
        creditCardValidators: typing.List[CodeValidator],
    ) -> None:
        self.__cardTypes = []
        if constructorId == 0:
            if self.__isOn(options, CreditCardValidator.VISA):
                self.__cardTypes.append(CreditCardValidator.VISA_VALIDATOR)
            if self.__isOn(options, CreditCardValidator.VPAY):
                self.__cardTypes.append(CreditCardValidator.VPAY_VALIDATOR)
            if self.__isOn(options, CreditCardValidator.AMEX):
                self.__cardTypes.append(CreditCardValidator.AMEX_VALIDATOR)
            if self.__isOn(options, CreditCardValidator.MASTERCARD):
                self.__cardTypes.append(CreditCardValidator.MASTERCARD_VALIDATOR)
            if self.__isOn(options, CreditCardValidator.MASTERCARD_PRE_OCT2016):
                self.__cardTypes.append(CreditCardValidator.MASTERCARD_VALIDATOR_PRE_OCT2016)
            if self.__isOn(options, CreditCardValidator.DISCOVER):
                self.__cardTypes.append(CreditCardValidator.DISCOVER_VALIDATOR)
            if self.__isOn(options, CreditCardValidator.DINERS):
                self.__cardTypes.append(CreditCardValidator.DINERS_VALIDATOR)
        elif constructorId == 1:
            if creditCardValidators is None:
                raise ValueError("Card validators are missing")
            self.__cardTypes.extend(creditCardValidators)
        elif constructorId == 2:
            if creditCardRanges is None:
                raise ValueError("Card ranges are missing")
            self.__cardTypes.append(
                CreditCardValidator.createRangeValidator(creditCardRanges, _LUHN_VALIDATOR)
            )
        elif constructorId == 3:
            if creditCardValidators is None:
                raise ValueError("Card validators are missing")
            if creditCardRanges is None:
                raise ValueError("Card ranges are missing")
            self.__cardTypes.extend(creditCardValidators)
            self.__cardTypes.append(
                CreditCardValidator.createRangeValidator(creditCardRanges, _LUHN_VALIDATOR)
            )

    @staticmethod
    def CreditCardValidator0() -> "CreditCardValidator":
        return CreditCardValidator(
            0,
            CreditCardValidator.AMEX
            + CreditCardValidator.VISA
            + CreditCardValidator.MASTERCARD
            + CreditCardValidator.DISCOVER,
            None,
            None,
        )

    def __isOn(self, options: int, flag: int) -> bool:
        return (options & flag) > 0

    # Class Methods End
