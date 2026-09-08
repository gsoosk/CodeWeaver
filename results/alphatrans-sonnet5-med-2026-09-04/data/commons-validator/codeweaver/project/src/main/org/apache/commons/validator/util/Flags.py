from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io

# Imports End


class Flags:

    # Class Fields Begin
    __serialVersionUID: int = 8481587558770237995
    __flags: int = 0
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        # 64-bit binary string, unsigned, first flag on the right / 64th on the left
        mask = (1 << 64) - 1
        bin_str = format(self.__flags & mask, "b")
        return bin_str.zfill(64)

    def hashCode(self) -> int:
        mask = (1 << 32) - 1
        value = self.__flags & mask
        if value & (1 << 31):
            value -= (1 << 32)
        return value

    def __hash__(self) -> int:
        return self.hashCode()

    def equals(self, obj: typing.Any) -> bool:
        if not isinstance(obj, Flags):
            return False
        if obj is self:
            return True
        return self.__flags == obj.__flags

    def __eq__(self, obj: typing.Any) -> bool:
        return self.equals(obj)

    def __str__(self) -> str:
        return self.toString()

    def clone(self) -> typing.Any:
        new_flags = Flags(1, self.__flags)
        return new_flags

    def turnOnAll(self) -> None:
        self.__flags = 0xFFFFFFFFFFFFFFFF

    def clear(self) -> None:
        self.__flags = 0

    def turnOffAll(self) -> None:
        self.__flags = 0

    def turnOff(self, flag: int) -> None:
        self.__flags &= ~flag

    def turnOn(self, flag: int) -> None:
        self.__flags |= flag

    def isOff(self, flag: int) -> bool:
        return (self.__flags & flag) == 0

    def isOn(self, flag: int) -> bool:
        return (self.__flags & flag) == flag

    def getFlags(self) -> int:
        return self.__flags

    def __init__(self, constructorId: int, flags: int) -> None:
        self.__flags = 0
        if constructorId == 1:
            self.__flags = flags

    # Class Methods End
