from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.ParseException import *
import io

# Imports End


class UnrecognizedOptionException(ParseException):

    # Class Fields Begin
    __serialVersionUID: int = -252504690284625623
    __option: str = None
    # Class Fields End

    # Class Methods Begin
    def getOption(self) -> str:
        return self.__option

    @staticmethod
    def UnrecognizedOptionException1(message: str) -> UnrecognizedOptionException:
        return UnrecognizedOptionException(message, None)

    def __init__(self, message: str, option: str) -> None:
        super().__init__(message)
        self.__option = option

    # Class Methods End
