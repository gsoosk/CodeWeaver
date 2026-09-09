from __future__ import annotations

# Imports Begin
import io

# Imports End


class QuoteMode:

    # Class Fields Begin
    ALL: QuoteMode = None
    ALL_NON_NULL: QuoteMode = None
    MINIMAL: QuoteMode = None
    NON_NUMERIC: QuoteMode = None
    NONE: QuoteMode = None
    # Class Fields End

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"QuoteMode.{self._name}"

    def __eq__(self, other) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(self._name)

    # Class Methods Begin
    @staticmethod
    def valueOf(name: str) -> QuoteMode:
        for member in QuoteMode.values():
            if member.name == name:
                return member
        raise ValueError(f"No enum constant QuoteMode.{name}")

    @staticmethod
    def values() -> list:
        return [
            QuoteMode.ALL,
            QuoteMode.ALL_NON_NULL,
            QuoteMode.MINIMAL,
            QuoteMode.NON_NUMERIC,
            QuoteMode.NONE,
        ]
    # Class Methods End


QuoteMode.ALL = QuoteMode("ALL")
QuoteMode.ALL_NON_NULL = QuoteMode("ALL_NON_NULL")
QuoteMode.MINIMAL = QuoteMode("MINIMAL")
QuoteMode.NON_NUMERIC = QuoteMode("NON_NUMERIC")
QuoteMode.NONE = QuoteMode("NONE")
