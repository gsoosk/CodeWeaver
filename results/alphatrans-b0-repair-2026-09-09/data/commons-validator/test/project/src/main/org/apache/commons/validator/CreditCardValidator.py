from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.LuhnCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
from src.main.org.apache.commons.validator.routines.RegexValidator import *
from src.main.org.apache.commons.validator.routines.CodeValidator import *
from src.main.org.apache.commons.validator.util.Flags import *
import typing
from typing import *
import numbers
import io
from abc import ABC

# Imports End


class CreditCardType(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def matches(self, card: str) -> bool:
        pass

    # Class Methods End


class Amex(CreditCardType):

    # Class Fields Begin
    __PREFIX: str = "34,37,"
    # Class Fields End

    # Class Methods Begin
    def matches(self, card: str) -> bool:
        prefix2 = card[0:2] + ","
        return (prefix2 in Amex.__PREFIX) and (len(card) == 15)

    # Class Methods End


class Discover(CreditCardType):

    # Class Fields Begin
    __PREFIX: str = "6011"
    # Class Fields End

    # Class Methods Begin
    def matches(self, card: str) -> bool:
        return card[0:4] == Discover.__PREFIX and (len(card) == 16)

    # Class Methods End


class Mastercard(CreditCardType):

    # Class Fields Begin
    __PREFIX: str = "51,52,53,54,55,"
    # Class Fields End

    # Class Methods Begin
    def matches(self, card: str) -> bool:
        prefix2 = card[0:2] + ","
        return (prefix2 in Mastercard.__PREFIX) and (len(card) == 16)

    # Class Methods End


class Visa(CreditCardType):

    # Class Fields Begin
    __PREFIX: str = "4"
    # Class Fields End

    # Class Methods Begin
    def matches(self, card: str) -> bool:
        return card[0:1] == Visa.__PREFIX and (len(card) == 13 or len(card) == 16)

    # Class Methods End


class CreditCardValidator:

    # Class Fields Begin
    NONE: int = 0
    AMEX: int = 1 << 0
    VISA: int = 1 << 1
    MASTERCARD: int = 1 << 2
    DISCOVER: int = 1 << 3
    __cardTypes: typing.Collection[CreditCardType] = None
    # Class Fields End

    # Class Methods Begin
    def _luhnCheck(self, cardNumber: str) -> bool:
        digits = len(cardNumber)
        odd_or_even = digits & 1
        total = 0
        for count in range(digits):
            ch = cardNumber[count]
            if not ch.isdigit():
                return False
            digit = int(ch)

            if ((count & 1) ^ odd_or_even) == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit

        return False if total == 0 else (total % 10 == 0)

    def addAllowedCardType(self, type_: CreditCardType) -> None:
        self.__cardTypes.append(type_)

    def isValid(self, card: str) -> bool:
        if card is None or len(card) < 13 or len(card) > 19:
            return False

        if not self._luhnCheck(card):
            return False

        for card_type in self.__cardTypes:
            if card_type.matches(card):
                return True

        return False

    @staticmethod
    def CreditCardValidator1() -> "CreditCardValidator":
        return CreditCardValidator(
            CreditCardValidator.AMEX
            + CreditCardValidator.VISA
            + CreditCardValidator.MASTERCARD
            + CreditCardValidator.DISCOVER
        )

    def __init__(self, options: int) -> None:
        self.__cardTypes = []

        f = Flags(1, options)
        if f.isOn(CreditCardValidator.VISA):
            self.__cardTypes.append(Visa())

        if f.isOn(CreditCardValidator.AMEX):
            self.__cardTypes.append(Amex())

        if f.isOn(CreditCardValidator.MASTERCARD):
            self.__cardTypes.append(Mastercard())

        if f.isOn(CreditCardValidator.DISCOVER):
            self.__cardTypes.append(Discover())

    # Class Methods End
