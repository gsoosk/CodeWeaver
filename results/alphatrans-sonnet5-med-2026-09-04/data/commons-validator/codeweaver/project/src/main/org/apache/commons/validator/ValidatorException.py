from __future__ import annotations

# Imports Begin
import io

# Imports End


class ValidatorException(Exception):

    # Class Fields Begin
    __serialVersionUID: int = 1025759372615616964
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def ValidatorException1() -> ValidatorException:
        return ValidatorException(None)

    def __init__(self, message: str) -> None:
        super().__init__(message)

    def __str__(self) -> str:
        return str(self.args[0]) if self.args and self.args[0] is not None else ""

    # Class Methods End
