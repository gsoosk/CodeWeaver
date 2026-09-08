from __future__ import annotations

# Imports Begin
import enum
import io

# Imports End


class QuoteMode(enum.Enum):
    """Defines quoting behavior."""

    ALL = "ALL"
    ALL_NON_NULL = "ALL_NON_NULL"
    MINIMAL = "MINIMAL"
    NON_NUMERIC = "NON_NUMERIC"
    NONE = "NONE"

    def __str__(self) -> str:
        return self.name
