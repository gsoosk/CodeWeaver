from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
import copy

# Imports End


_MASK64 = 0xFFFFFFFFFFFFFFFF


class Flags:

    # Class Fields Begin
    __serialVersionUID: int = 8481587558770237995
    __flags: int = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        bin_str = bin(self.__flags & _MASK64)[2:]
        return bin_str.rjust(64, "0")

    def __str__(self) -> str:
        return self.toString()

    def hashCode(self) -> int:
        val = self.__flags & 0xFFFFFFFF
        if val >= 0x80000000:
            val -= 0x100000000
        return val

    def __hash__(self) -> int:
        return self.hashCode()

    def equals(self, obj: typing.Any) -> bool:
        if not isinstance(obj, Flags):
            return False

        if obj is self:
            return True

        return (self.__flags & _MASK64) == (obj.__flags & _MASK64)

    def __eq__(self, other: typing.Any) -> bool:
        return self.equals(other)

    def clone(self) -> typing.Any:
        return copy.copy(self)

    def __copy__(self) -> "Flags":
        new_obj = Flags(0, 0)
        new_obj.__flags = self.__flags
        return new_obj

    def turnOnAll(self) -> None:
        self.__flags = _MASK64

    def clear(self) -> None:
        self.__flags = 0

    def turnOffAll(self) -> None:
        self.__flags = 0

    def turnOff(self, flag: int) -> None:
        self.__flags = (self.__flags & ~flag) & _MASK64

    def turnOn(self, flag: int) -> None:
        self.__flags = (self.__flags | flag) & _MASK64

    def isOff(self, flag: int) -> bool:
        return (self.__flags & flag) == 0

    def isOn(self, flag: int) -> bool:
        return (self.__flags & flag) == flag

    def getFlags(self) -> int:
        return self.__flags

    def __init__(self, constructorId: int, flags: int) -> None:
        self.__flags = 0
        if constructorId == 1:
            self.__flags = flags & _MASK64

    # Class Methods End
