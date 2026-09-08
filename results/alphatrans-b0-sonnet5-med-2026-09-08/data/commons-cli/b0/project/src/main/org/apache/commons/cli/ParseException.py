from __future__ import annotations

# Imports Begin
import io

# Imports End


class ParseException(Exception):

    # Class Fields Begin
    __serialVersionUID: int = 9112808380089253192
    # Class Fields End

    # Class Methods Begin
    def __init__(self, message: str) -> None:
        super().__init__(message)

    # Class Methods End
