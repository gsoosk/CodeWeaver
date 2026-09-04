from __future__ import annotations

# Imports Begin
import io
import unicodedata

# Imports End


class OptionValidator:

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def validate(option: str) -> str:
        if option is None:
            return None

        if len(option) == 1:
            ch = option[0]

            if not OptionValidator.__isValidOpt(ch):
                raise ValueError("Illegal option name '" + ch + "'")
        else:
            for ch in option:
                if not OptionValidator.__isValidChar(ch):
                    raise ValueError(
                        "The option '"
                        + option
                        + "' contains an illegal "
                        + "character : '"
                        + ch
                        + "'"
                    )
        return option

    @staticmethod
    def __isValidOpt(c: str) -> bool:
        return OptionValidator.__isValidChar(c) or c == '?' or c == '@'

    @staticmethod
    def __isValidChar(c: str) -> bool:
        if not c:
            return False
        category = unicodedata.category(c)
        if category in (
            "Lu", "Ll", "Lt", "Lm", "Lo",  # letter
            "Nd",                          # digit
            "Nl",                          # numeric letter
            "Mc", "Mn",                    # combining / non-spacing mark
            "Pc",                          # connecting punctuation
            "Sc",                          # currency symbol
        ):
            return True
        # Character.isIdentifierIgnorable: format chars (Cf) and certain ISO
        # control characters that are not whitespace.
        if category == "Cf":
            return True
        cp = ord(c)
        if (0x0000 <= cp <= 0x0008) or (0x000E <= cp <= 0x001B) or (0x007F <= cp <= 0x009F):
            return True
        return False

    # Class Methods End
