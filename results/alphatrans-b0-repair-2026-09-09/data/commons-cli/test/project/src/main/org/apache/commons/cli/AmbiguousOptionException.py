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
        super().__init__(AmbiguousOptionException.__createMessage(option, matchingOptions), option)
        self.__matchingOptions = matchingOptions

    @staticmethod
    def __createMessage(option: str, matchingOptions: typing.Collection[str]) -> str:
        buf = io.StringIO()
        buf.write("Ambiguous option: '")
        buf.write(option)
        buf.write("'  (could be: ")

        it = iter(matchingOptions)
        try:
            current = next(it)
            has_next = True
        except StopIteration:
            has_next = False

        while has_next:
            buf.write("'")
            buf.write(current)
            buf.write("'")
            try:
                current = next(it)
                buf.write(", ")
            except StopIteration:
                has_next = False

        buf.write(")")

        return buf.getvalue()

    # Class Methods End
