from __future__ import annotations

# Imports Begin
import copy
import typing
from typing import *
import io

# Imports End


class Msg:

    # Class Fields Begin
    __serialVersionUID: int = 5690015734364127124
    _bundle: str = None
    _key: str = None
    _name: str = None
    _resource: bool = True
    # Class Fields End

    def __init__(self) -> None:
        self._bundle: str = None
        self._key: str = None
        self._name: str = None
        self._resource: bool = True

    # Class Methods Begin
    def toString(self) -> str:
        results = io.StringIO()

        results.write("Msg: name=")
        results.write(str(self._name))
        results.write("  key=")
        results.write(str(self._key))
        results.write("  resource=")
        results.write(str(self._resource))
        results.write("  bundle=")
        results.write(str(self._bundle))
        results.write("\n")

        return results.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def clone(self) -> typing.Any:
        return copy.copy(self)

    def setResource(self, resource: bool) -> None:
        self._resource = resource

    def isResource(self) -> bool:
        return self._resource

    def setKey(self, key: str) -> None:
        self._key = key

    def getKey(self) -> str:
        return self._key

    def setName(self, name: str) -> None:
        self._name = name

    def getName(self) -> str:
        return self._name

    def setBundle(self, bundle: str) -> None:
        self._bundle = bundle

    def getBundle(self) -> str:
        return self._bundle

    # Class Methods End
