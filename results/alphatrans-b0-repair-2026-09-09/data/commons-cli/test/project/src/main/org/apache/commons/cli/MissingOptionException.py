from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.ParseException import *
import typing
from typing import *
import io

# Imports End


class MissingOptionException(ParseException):

    # Class Fields Begin
    __serialVersionUID: int = 8161889051578563249
    __missingOptions: typing.List[typing.Any] = None
    # Class Fields End

    # Class Methods Begin
    def getMissingOptions(self) -> typing.List[typing.Any]:
        return self.missingOptions

    @staticmethod
    def MissingOptionException1(
        constructorId: int, missingOptions: typing.List[typing.Any], message: str
    ) -> "MissingOptionException":
        if constructorId == 1:
            return MissingOptionException(
                constructorId,
                missingOptions,
                MissingOptionException._MissingOptionException__createMessage(missingOptions),
            )
        return MissingOptionException(constructorId, missingOptions, message)

    def __init__(
        self, constructorId: int, missingOptions: typing.List[typing.Any], message: str
    ) -> None:
        super().__init__(message)
        self.missingOptions = None
        if constructorId == 1:
            self.missingOptions = missingOptions

    @staticmethod
    def __createMessage(missingOptions: typing.List[typing.Any]) -> str:
        buf = io.StringIO()
        buf.write("Missing required option")
        buf.write("" if len(missingOptions) == 1 else "s")
        buf.write(": ")

        it = iter(missingOptions)
        try:
            item = next(it)
            while True:
                buf.write(str(item))
                item = next(it)
                buf.write(", ")
        except StopIteration:
            pass

        return buf.getvalue()

    # Class Methods End
