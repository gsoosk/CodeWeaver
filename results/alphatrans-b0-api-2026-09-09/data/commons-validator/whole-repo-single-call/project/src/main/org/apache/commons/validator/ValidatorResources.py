from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.FormSet import *
import logging
import typing
from typing import *
import io

# Imports End


class ValidatorResources:

    # Class Fields Begin
    _defaultFormSet: FormSet = None
    __ARGS_PATTERN: str = "form-validation/formset/form/field/arg"
    __serialVersionUID: int = -8203745881446239554
    __VALIDATOR_RULES: str = "digester-rules.xml"
    __REGISTRATIONS: typing.List[str] = []
    __log: logging.Logger = None
    _defaultLocale: typing.Any = None
    # Class Fields End

    # Class Methods Begin
    def _buildKey(self, fs: FormSet) -> str:
        return self.__buildLocale(fs.getLanguage(), fs.getCountry(), fs.getVariant())

    def __init__(self) -> None:
        pass

    def __getLog(self) -> logging.Logger:
        if self.__log is None:
            self.__log = logging.getLogger("ValidatorResources")
        return self.__log

    def __buildLocale(self, lang: str, country: str, variant: str) -> str:
        key = lang if lang else ""
        key += ("_" + country) if country else ""
        key += ("_" + variant) if variant else ""
        return key

    # Class Methods End
