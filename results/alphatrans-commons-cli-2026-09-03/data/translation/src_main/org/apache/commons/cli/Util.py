from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io

# Imports End


class Util:

    # Class Fields Begin
    EMPTY_STRING_ARRAY: typing.List[typing.List[str]] = []
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def stripLeadingHyphens(str_: str) -> str:
        if str_ is None:
            return None
        if str_.startswith("--"):
            return str_[2:]
        if str_.startswith("-"):
            return str_[1:]
        return str_

    @staticmethod
    def stripLeadingAndTrailingQuotes(str_: str) -> str:
        length = len(str_)
        if (
            length > 1
            and str_.startswith('"')
            and str_.endswith('"')
            and str_[1:length - 1].find('"') == -1
        ):
            str_ = str_[1:length - 1]
        return str_

    # Class Methods End
