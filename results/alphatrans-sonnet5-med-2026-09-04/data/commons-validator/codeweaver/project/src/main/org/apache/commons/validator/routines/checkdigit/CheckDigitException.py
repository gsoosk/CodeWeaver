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
    def CheckDigitException2() -> CheckDigitException:
        return CheckDigitException(None, None)

    @staticmethod
    def CheckDigitException1(msg: str) -> CheckDigitException:
        return CheckDigitException(msg, None)

    def __init__(self, msg: str, cause: BaseException) -> None:
        super().__init__(msg)
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return str(self.args[0]) if self.args and self.args[0] is not None else ""

    # Class Methods End
