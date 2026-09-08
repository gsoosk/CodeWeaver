from __future__ import annotations

# Imports Begin
import io
import enum

# Imports End


class QuoteMode(enum.Enum):
    """Defines quoting behavior."""

    # Class Fields Begin
    ALL = "ALL"
    ALL_NON_NULL = "ALL_NON_NULL"
    MINIMAL = "MINIMAL"
    NON_NUMERIC = "NON_NUMERIC"
    NONE = "NONE"
    # Class Fields End

    # Class Methods Begin
    def __str__(self) -> str:
        return self.name

    # Class Methods End
