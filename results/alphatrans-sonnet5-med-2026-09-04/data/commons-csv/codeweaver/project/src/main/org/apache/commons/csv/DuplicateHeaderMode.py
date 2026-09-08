from __future__ import annotations

# Imports Begin
import io
import enum

# Imports End


class DuplicateHeaderMode(enum.Enum):
    """Determines how duplicate header fields should be handled."""

    # Class Fields Begin
    ALLOW_ALL = "ALLOW_ALL"
    ALLOW_EMPTY = "ALLOW_EMPTY"
    DISALLOW = "DISALLOW"
    # Class Fields End

    # Class Methods Begin
    def __str__(self) -> str:
        return self.name

    # Class Methods End
