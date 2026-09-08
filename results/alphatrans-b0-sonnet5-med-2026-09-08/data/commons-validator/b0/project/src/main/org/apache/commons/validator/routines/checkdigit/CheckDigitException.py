from __future__ import annotations

# Imports Begin
import io

# Imports End


class CheckDigitException(Exception):

    # Class Fields Begin
    __serialVersionUID: int = -3519894732624685477
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def CheckDigitException1(msg: str) -> "CheckDigitException":
        return CheckDigitException(msg, None)

    @staticmethod
    def CheckDigitException2() -> "CheckDigitException":
        return CheckDigitException(None, None)

    def __init__(self, msg: str, cause: BaseException) -> None:
        super().__init__(msg)
        self.__cause__ = cause

    # Class Methods End
