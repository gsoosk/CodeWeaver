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
        bin_str = bin(self.__flags & 0xFFFFFFFFFFFFFFFF)[2:]
        bin_str = bin_str.rjust(64, "0")
        return bin_str

    def __str__(self) -> str:
        return self.toString()

    def hashCode(self) -> int:
        return self.__flags & 0xFFFFFFFF

    def __hash__(self) -> int:
        return self.hashCode()

    def equals(self, obj: typing.Any) -> bool:
        if not isinstance(obj, Flags):
            return False
        if obj is self:
            return True
        return self.__flags == obj._Flags__flags

    def __eq__(self, other) -> bool:
        return self.equals(other)

    def clone(self) -> typing.Any:
        import copy
        return copy.copy(self)

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
        if constructorId == 1:
            self.__flags = flags

    # Class Methods End
