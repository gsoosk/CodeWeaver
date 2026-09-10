from __future__ import annotations

# Imports Begin
import io
from enum import Enum, auto

# Imports End


class DuplicateHeaderMode(Enum):

    # Class Fields Begin
    ALLOW_ALL = auto()
    ALLOW_EMPTY = auto()
    DISALLOW = auto()
    # Class Fields End

    # Class Methods Begin
    # Class Methods End
