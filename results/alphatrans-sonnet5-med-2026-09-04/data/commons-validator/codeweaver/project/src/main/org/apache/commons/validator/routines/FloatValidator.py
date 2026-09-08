from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
import sys
import struct
import typing
from typing import *
import io

# Imports End

# java.lang.Float.MIN_VALUE / Float.MAX_VALUE -- the smallest positive
# (denormalized) and largest finite values representable by Java's 32-bit
# ``float``. Python has no distinct 32-bit float type, but ``struct`` lets
# us compute the exact IEEE-754 single-precision boundary values so the
# range checks below reject values that would overflow/underflow a real
# Java ``float`` (unlike ``sys.float_info.min``/``.max``, which are the
# *double*-precision boundaries and are many orders of magnitude off).
_FLOAT_MIN_VALUE = struct.unpack("<f", struct.pack("<i", 1))[0]
_FLOAT_MAX_VALUE = struct.unpack("<f", struct.pack("<I", 0x7F7FFFFF))[0]


class FloatValidator(AbstractNumberValidator):

    # Class Fields Begin
    __serialVersionUID: int = None
    __VALIDATOR: FloatValidator = None
    # Class Fields End

    # Class Methods Begin
    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        double_value = float(value)

        if double_value > 0:
            if double_value < _FLOAT_MIN_VALUE:
                return None
            if double_value > _FLOAT_MAX_VALUE:
                return None
        elif double_value < 0:
            pos_double = double_value * -1
            if pos_double < _FLOAT_MIN_VALUE:
                return None
            if pos_double > _FLOAT_MAX_VALUE:
                return None

        # Mirrors Java's ``Float.valueOf((float) doubleValue)`` -- narrow
        # the double-precision parsed value down to genuine IEEE-754
        # single-precision (32-bit) representation, then widen it back to
        # a Python ``float`` for storage/comparison. Without this
        # round-trip, values like ``Float.MIN_VALUE`` parsed back from a
        # formatted string would retain double precision and fail to
        # compare equal to a true (narrowed) Java ``float``.
        return struct.unpack("<f", struct.pack("<f", double_value))[0]


    def isInRange1(self, value: float, min_: float, max_: float) -> bool:
        return self.isInRange0(float(value), min_, max_)

    def isInRange0(self, value: float, min_: float, max_: float) -> bool:
        return min_ <= value <= max_

    def minValue1(self, value: float, min_: float) -> bool:
        return self.minValue0(float(value), min_)

    def minValue0(self, value: float, min_: float) -> bool:
        return value >= min_

    def maxValue1(self, value: float, max_: float) -> bool:
        return self.maxValue0(float(value), max_)

    def maxValue0(self, value: float, max_: float) -> bool:
        return value <= max_

    def validate3(self, value: str, pattern: str, locale: typing.Any) -> float:
        return AbstractNumberValidator._parse(self, value, pattern, locale)

    def validate2(self, value: str, locale: typing.Any) -> float:
        return self.validate3(value, None, locale)

    def validate1(self, value: str, pattern: str) -> float:
        return self.validate3(value, pattern, None)

    def validate0(self, value: str) -> float:
        return self.validate3(value, None, None)

    @staticmethod
    def FloatValidator1() -> FloatValidator:
        return FloatValidator(True, AbstractNumberValidator.STANDARD_FORMAT)

    def __init__(self, strict: bool, formatType: int) -> None:
        AbstractNumberValidator.__init__(self, strict, formatType, True)

    @staticmethod
    def getInstance() -> FloatValidator:
        return FloatValidator.__VALIDATOR

    # Class Methods End


FloatValidator._FloatValidator__VALIDATOR = FloatValidator.FloatValidator1()
