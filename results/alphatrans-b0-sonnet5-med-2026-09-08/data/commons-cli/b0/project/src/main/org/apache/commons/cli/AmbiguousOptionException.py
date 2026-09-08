from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.UnrecognizedOptionException import *
import typing
import io

# Imports End


class AmbiguousOptionException(UnrecognizedOptionException):

    # Class Fields Begin
    __serialVersionUID: int = 5829816121277947229
    __matchingOptions: typing.Collection[str] = None
    # Class Fields End

    # Class Methods Begin
    def getMatchingOptions(self) -> typing.Collection[str]:
        return self.__matchingOptions

    def __init__(self, option: str, matchingOptions: typing.Collection[str]) -> None:
        super().__init__(
            AmbiguousOptionException.__createMessage(option, matchingOptions), option
        )
        self.__matchingOptions = matchingOptions

    @staticmethod
    def __createMessage(option: str, matchingOptions: typing.Collection[str]) -> str:
        buf = io.StringIO()
        buf.write("Ambiguous option: '")
        buf.write(option)
        buf.write("'  (could be: ")

        items = list(matchingOptions)
        n = len(items)
        for i, item in enumerate(items):
            buf.write("'")
            buf.write(item)
            buf.write("'")
            if i != n - 1:
                buf.write(", ")
        buf.write(")")

        return buf.getvalue()

    # Class Methods End
