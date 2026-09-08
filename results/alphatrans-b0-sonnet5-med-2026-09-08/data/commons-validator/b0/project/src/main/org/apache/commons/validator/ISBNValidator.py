from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ISBN10CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.EAN13CheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigitException import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
from src.main.org.apache.commons.validator.routines.CodeValidator import *
import src.main.org.apache.commons.validator.routines.ISBNValidator as _routines_isbn
import io

# Imports End


class ISBNValidator:

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def isValid(self, isbn: str) -> bool:
        return _routines_isbn.ISBNValidator.getInstance0().isValidISBN10(isbn)

    def __init__(self) -> None:
        pass

    # Class Methods End
