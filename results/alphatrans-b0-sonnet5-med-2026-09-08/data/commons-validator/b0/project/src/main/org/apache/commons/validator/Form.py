from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.Field import *
import typing
from typing import *
import io

# Imports End


class Form:

    # Class Fields Begin
    __serialVersionUID: int = 6445211789563796371
    _name: str = None
    _lFields: typing.List[Field] = None
    _inherit: str = None
    __processed: bool = False
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self._lFields = []

    def toString(self) -> str:
        results = io.StringIO()
        results.write("Form: ")
        results.write(str(self._name))
        results.write("\n")
        for f in self._lFields:
            results.write("\tField: \n")
            results.write(str(f))
            results.write("\n")
        return results.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def isExtending(self) -> bool:
        return self._inherit is not None

    def setExtends(self, inherit: str) -> None:
        self._inherit = inherit

    def getExtends(self) -> str:
        return self._inherit

    def isProcessed(self) -> bool:
        return self.__processed

    def getFields(self) -> typing.List[Field]:
        return list(self._lFields)

    def setName(self, name: str) -> None:
        self._name = name

    def getName(self) -> str:
        return self._name

    # Class Methods End
