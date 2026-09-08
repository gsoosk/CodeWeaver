from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io

# Imports End


class Var:

    # Class Fields Begin
    __serialVersionUID: int = -684185211548420224
    JSTYPE_INT: str = "int"
    JSTYPE_STRING: str = "string"
    JSTYPE_REGEXP: str = "regexp"
    __name: str = None
    __value: str = None
    __jsType: str = None
    __resource: bool = False
    __bundle: str = None
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        results = io.StringIO()
        results.write("Var: name=")
        results.write(str(self.__name))
        results.write("  value=")
        results.write(str(self.__value))
        results.write("  resource=")
        results.write(str(self.__resource))
        if self.__resource:
            results.write("  bundle=")
            results.write(str(self.__bundle))
        results.write("  jsType=")
        results.write(str(self.__jsType))
        results.write("\n")
        return results.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def clone(self) -> typing.Any:
        import copy
        return copy.copy(self)

    def setJsType(self, jsType: str) -> None:
        self.__jsType = jsType

    def getJsType(self) -> str:
        return self.__jsType

    def setBundle(self, bundle: str) -> None:
        self.__bundle = bundle

    def getBundle(self) -> str:
        return self.__bundle

    def setResource(self, resource: bool) -> None:
        self.__resource = resource

    def isResource(self) -> bool:
        return self.__resource

    def setValue(self, value: str) -> None:
        self.__value = value

    def getValue(self) -> str:
        return self.__value

    def setName(self, name: str) -> None:
        self.__name = name

    def getName(self) -> str:
        return self.__name

    def __init__(self, constructorId: int, name: str, value: str, jsType: str) -> None:
        if constructorId == 1:
            self.__name = name
            self.__value = value
            self.__jsType = jsType

    # Class Methods End
