from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.util.ValidatorUtils import *
from src.main.org.apache.commons.validator.ValidatorException import *
from src.main.org.apache.commons.validator.Arg import *
import os
import typing
from typing import *
import io

# Imports End


class Field:

    # Class Fields Begin
    __serialVersionUID: int = -8502647722530192185
    __DEFAULT_ARG: str = "org.apache.commons.validator.Field.DEFAULT"
    TOKEN_INDEXED: str = "[]"
    _TOKEN_START: str = "${"
    _TOKEN_END: str = "}"
    _TOKEN_VAR: str = "var:"
    # Class Fields End

    def __init__(self):
        self._property: str = None
        self._indexedProperty: str = None
        self._indexedListProperty: str = None
        self._key: str = None
        self._depends: str = None
        self._page: int = 0
        self._clientValidation: bool = True
        self._fieldOrder: int = 0
        self.__dependencyList: typing.List[str] = []
        self._args: typing.List[typing.Dict[str, Arg]] = []

    # Class Methods Begin
    def getDependencyList(self) -> typing.List[str]:
        return list(self.__dependencyList)

    def isDependency(self, validatorName: str) -> bool:
        return validatorName in self.__dependencyList

    def generateKey(self) -> None:
        if self.isIndexed():
            self._key = self._indexedListProperty + self.TOKEN_INDEXED + "." + self._property
        else:
            self._key = self._property

    def isIndexed(self) -> bool:
        return self._indexedListProperty is not None and len(self._indexedListProperty) > 0

    def setKey(self, key: str) -> None:
        self._key = key

    def getKey(self) -> str:
        if self._key is None:
            self.generateKey()
        return self._key

    def getArgs(self, key: str) -> typing.List[Arg]:
        argList: typing.List[Arg] = []
        for i in range(len(self._args)):
            argList.append(self.getArg1(key, i))
        return argList

    def getArg1(self, key: str, position: int) -> Arg:
        if position >= len(self._args) or self._args[position] is None:
            return None

        arg = self._args[position].get(key)

        if arg is None and key == self.__DEFAULT_ARG:
            return None

        return self.getArg0(position) if arg is None else arg

    def getArg0(self, position: int) -> Arg:
        return self.getArg1(self.__DEFAULT_ARG, position)

    def addArg(self, arg: Arg) -> None:
        if arg is None or arg.getKey() is None or len(arg.getKey()) == 0:
            return

        self.__determineArgPosition(arg)
        self.__ensureArgsCapacity(arg)

        argMap = self._args[arg.getPosition()]
        if argMap is None:
            argMap = {}
            self._args[arg.getPosition()] = argMap

        if arg.getName() is None:
            argMap[self.__DEFAULT_ARG] = arg
        else:
            argMap[arg.getName()] = arg

    def setClientValidation(self, clientValidation: bool) -> None:
        self._clientValidation = clientValidation

    def isClientValidation(self) -> bool:
        return self._clientValidation

    def setDepends(self, depends: str) -> None:
        self._depends = depends

        self.__dependencyList.clear()

        tokens = [t.strip() for t in depends.split(",")]
        for depend in tokens:
            if depend is not None and len(depend) > 0:
                self.__dependencyList.append(depend)

    def getDepends(self) -> str:
        return self._depends

    def setIndexedListProperty(self, indexedListProperty: str) -> None:
        self._indexedListProperty = indexedListProperty

    def getIndexedListProperty(self) -> str:
        return self._indexedListProperty

    def setIndexedProperty(self, indexedProperty: str) -> None:
        self._indexedProperty = indexedProperty

    def getIndexedProperty(self) -> str:
        return self._indexedProperty

    def setProperty(self, property_: str) -> None:
        self._property = property_

    def getProperty(self) -> str:
        return self._property

    def setFieldOrder(self, fieldOrder: int) -> None:
        self._fieldOrder = fieldOrder

    def getFieldOrder(self) -> int:
        return self._fieldOrder

    def setPage(self, page: int) -> None:
        self._page = page

    def getPage(self) -> int:
        return self._page

    def __handleMissingAction(self, name: str) -> None:
        raise ValidatorException(
            "No ValidatorAction named " + name + " found for field " + self.getProperty()
        )

    def __processArg(self, key: str, replaceValue: str) -> None:
        for i in range(len(self._args)):
            argMap = self._args[i]
            if argMap is None:
                continue

            for arg in list(argMap.values()):
                if arg is not None:
                    arg.setKey(ValidatorUtils.replace(arg.getKey(), key, replaceValue))

    def __ensureArgsCapacity(self, arg: Arg) -> None:
        if arg.getPosition() >= len(self._args):
            newSize = arg.getPosition() + 1
            self._args.extend([None] * (newSize - len(self._args)))

    def __determineArgPosition(self, arg: Arg) -> None:
        position = arg.getPosition()

        if position >= 0:
            return

        if self._args is None or len(self._args) == 0:
            arg.setPosition(0)
            return

        keyName = self.__DEFAULT_ARG if arg.getName() is None else arg.getName()
        lastPosition = -1
        lastDefault = -1
        for i in range(len(self._args)):
            if self._args[i] is not None and keyName in self._args[i]:
                lastPosition = i
            if self._args[i] is not None and self.__DEFAULT_ARG in self._args[i]:
                lastDefault = i

        if lastPosition < 0:
            lastPosition = lastDefault

        lastPosition += 1
        arg.setPosition(lastPosition)

    def __str__(self) -> str:
        results = "Field: \n"
        results += "\tproperty=  " + str(self._property) + "\n"
        results += "\tindexedProperty=  " + str(self._indexedProperty) + "\n"
        results += "\tindexedListProperty=  " + str(self._indexedListProperty) + "\n"
        results += "\tdepends=  " + str(self._depends) + "\n"
        results += "\tpage=  " + str(self._page) + "\n"
        results += "\tfieldOrder=  " + str(self._fieldOrder) + "\n"
        return results

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Field):
            return False
        return (
            self._property == other._property
            and self._indexedProperty == other._indexedProperty
            and self._indexedListProperty == other._indexedListProperty
            and self._key == other._key
            and self._depends == other._depends
            and self._page == other._page
            and self._clientValidation == other._clientValidation
            and self._fieldOrder == other._fieldOrder
        )

    def __hash__(self):
        return hash(
            (
                self._property,
                self._indexedProperty,
                self._indexedListProperty,
                self._key,
                self._depends,
                self._page,
                self._clientValidation,
                self._fieldOrder,
            )
        )

    # Class Methods End
