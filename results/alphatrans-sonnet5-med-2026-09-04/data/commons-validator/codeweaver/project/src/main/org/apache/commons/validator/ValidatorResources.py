from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.FormSet import *

# from src.main.org.apache.commons.logging.LogFactory import *
# from src.main.org.apache.commons.logging.Log import *
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
    __REGISTRATIONS: typing.List[typing.List[str]] = None
    __log: logging.Logger = None
    _defaultLocale: typing.Any = None
    # Class Fields End

    # Class Methods Begin
    def _buildKey(self, fs: FormSet) -> str:
        return self.__buildLocale(fs.getLanguage(), fs.getCountry(), fs.getVariant())

    def __init__(self) -> None:
        self._defaultFormSet = None
        self.__log = None
        if ValidatorResources.__REGISTRATIONS is None:
            ValidatorResources.__REGISTRATIONS = [
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.0//EN",
                    "/org/apache/commons/validator/resources/validator_1_0.dtd",
                ],
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.0.1//EN",
                    "/org/apache/commons/validator/resources/validator_1_0_1.dtd",
                ],
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.1//EN",
                    "/org/apache/commons/validator/resources/validator_1_1.dtd",
                ],
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.1.3//EN",
                    "/org/apache/commons/validator/resources/validator_1_1_3.dtd",
                ],
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.2.0//EN",
                    "/org/apache/commons/validator/resources/validator_1_2_0.dtd",
                ],
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.3.0//EN",
                    "/org/apache/commons/validator/resources/validator_1_3_0.dtd",
                ],
                [
                    "-//Apache Software Foundation//DTD Commons Validator Rules Configuration 1.4.0//EN",
                    "/org/apache/commons/validator/resources/validator_1_4_0.dtd",
                ],
            ]
        if ValidatorResources._defaultLocale is None:
            import locale as _locale_module

            try:
                default_locale = _locale_module.getlocale()[0]
            except Exception:
                default_locale = None
            ValidatorResources._defaultLocale = default_locale or "en_US"

    def __getLog(self) -> logging.Logger:
        if self.__log is None:
            self.__log = logging.getLogger(
                ValidatorResources.__module__ + ".ValidatorResources"
            )
        return self.__log

    def __buildLocale(self, lang: str, country: str, variant: str) -> str:
        key = lang if (lang is not None and len(lang) > 0) else ""
        key += ("_" + country) if (country is not None and len(country) > 0) else ""
        key += ("_" + variant) if (variant is not None and len(variant) > 0) else ""
        return key

    # Class Methods End
