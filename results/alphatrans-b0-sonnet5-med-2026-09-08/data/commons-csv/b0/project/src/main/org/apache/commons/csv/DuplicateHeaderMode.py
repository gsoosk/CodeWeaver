from __future__ import annotations

# Imports Begin
import enum
import io

# Imports End


class DuplicateHeaderMode(enum.Enum):
    """Determines how duplicate header fields should be handled."""

    ALLOW_ALL = "ALLOW_ALL"
    ALLOW_EMPTY = "ALLOW_EMPTY"
    DISALLOW = "DISALLOW"

    def __str__(self) -> str:
        return self.name
