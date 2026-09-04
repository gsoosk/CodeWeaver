from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.Option import *
from src.main.org.apache.commons.cli.AlreadySelectedException import *
import typing
from typing import *
import io

# Imports End


class OptionGroup:

    # Class Fields Begin
    __serialVersionUID: int = 1
    __optionMap: typing.Dict[str, Option] = None
    __selected: str = None
    __required: bool = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.__optionMap = {}
        self.__selected = None
        self.__required = False

    def toString(self) -> str:
        buff = ""

        options = list(self.getOptions())

        buff += "["

        for i, option in enumerate(options):
            if option.getOpt() is not None:
                buff += "-"
                buff += option.getOpt()
            else:
                buff += "--"
                buff += option.getLongOpt()

            if option.getDescription() is not None:
                buff += " "
                buff += option.getDescription()

            if i < len(options) - 1:
                buff += ", "

        buff += "]"

        return buff

    def setSelected(self, option: Option) -> None:
        if option is None:
            self.__selected = None
            return

        from src.main.org.apache.commons.cli.AlreadySelectedException import (
            AlreadySelectedException,
        )

        if self.__selected is not None and self.__selected != option.getKey():
            raise AlreadySelectedException.AlreadySelectedException1(self, option)
        self.__selected = option.getKey()

    def setRequired(self, required: bool) -> None:
        self.__required = required

    def isRequired(self) -> bool:
        return self.__required

    def getSelected(self) -> str:
        return self.__selected

    def getOptions(self) -> typing.Collection[Option]:
        return self.__optionMap.values()

    def getNames(self) -> typing.Collection[str]:
        return self.__optionMap.keys()

    def addOption(self, option: Option) -> OptionGroup:
        self.__optionMap[option.getKey()] = option

        return self

    def __str__(self) -> str:
        return self.toString()

    # Class Methods End
