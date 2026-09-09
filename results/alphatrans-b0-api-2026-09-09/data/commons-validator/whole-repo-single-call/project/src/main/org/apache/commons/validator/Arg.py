from __future__ import annotations

# Imports Begin
import os
import typing
from typing import *
import io
import copy

# Imports End


class Arg:

    # Class Fields Begin
    __serialVersionUID: int = -8922606779669839294
    _bundle: str = None
    _key: str = None
    _name: str = None
    _position: int = -1
    _resource: bool = True
    # Class Fields End

    # Class Methods Begin
    def toString(self) -> str:
        results = io.StringIO()
        results.write("Arg: name=")
        results.write(str(self._name))
        results.write("  key=")
        results.write(str(self._key))
        results.write("  position=")
        results.write(str(self._position))
        results.write("  bundle=")
        results.write(str(self._bundle))
        results.write("  resource=")
        results.write(str(self._resource))
        results.write("\n")
        return results.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def clone(self) -> typing.Any:
        return copy.copy(self)

    def setResource(self, resource: bool) -> None:
        self._resource = resource

    def setPosition(self, position: int) -> None:
        self._position = position

    def setName(self, name: str) -> None:
        self._name = name

    def setKey(self, key: str) -> None:
        self._key = key

    def setBundle(self, bundle: str) -> None:
        self._bundle = bundle

    def isResource(self) -> bool:
        return self._resource

    def getPosition(self) -> int:
        return self._position

    def getName(self) -> str:
        return self._name

    def getKey(self) -> str:
        return self._key

    def getBundle(self) -> str:
        return self._bundle

    # Class Methods End
