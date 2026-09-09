{{src/main/org/apache/commons/validator/FormSet.py}}
from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.Form import *

# from src.main.org.apache.commons.logging.LogFactory import *
# from src.main.org.apache.commons.logging.Log import *
import logging
import typing
from typing import *
import io

# Imports End


class FormSet:

    # Class Fields Begin
    __serialVersionUID: int = -8936513232763306055
    __log: logging.Logger = None
    __processed: bool = None
    __language: str = None
    __country: str = None
    __variant: str = None
    __forms: typing.Dict[str, Form] = None
    __constants: typing.Dict[str, str] = None
    _GLOBAL_FORMSET: int = 1
    _LANGUAGE_FORMSET: int = 2
    _COUNTRY_FORMSET: int = 3
    _VARIANT_FORMSET: int = 4
    __merged: bool = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.__log = logging.getLogger(
            "org.apache.commons.validator.FormSet"
        )
        self.__processed = False
        self.__language = None
        self.__country = None
        self.__variant = None
        self.__forms: typing.Dict[str, Form] = {}
        self.__constants: typing.Dict[str, str] = {}
        self.__merged = False

    def toString(self) -> str:
        results = io.StringIO()

        results.write("FormSet: language=")
        results.write(str(self.__language))
        results.write("  country=")
        results.write(str(self.__country))
        results.write("  variant=")
        results.write(str(self.__variant))
        results.write("\n")

        for form in self.getForms().values():
            results.write("   ")
            results.write(str(form))
            results.write("\n")

        return results.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def displayKey(self) -> str:
        results = io.StringIO()
        if self.__language is not None and len(self.__language) > 0:
            results.write("language=")
            results.write(self.__language)
        if self.__country is not None and len(self.__country) > 0:
            if results.tell() > 0:
                results.write(", ")
            results.write("country=")
            results.write(self.__country)
        if self.__variant is not None and len(self.__variant) > 0:
            if results.tell() > 0:
                results.write(", ")
            results.write("variant=")
            results.write(self.__variant)

        value = results.getvalue()
        if len(value) == 0:
            return "default"

        return value

    def getForms(self) -> typing.Dict[str, Form]:
        return dict(self.__forms)

    def getForm(self, formName: str) -> Form:
        return self.__forms.get(formName)

    def addForm(self, f: Form) -> None:
        formName = f.getName()
        if formName in self.__forms:
            self.__getLog().error(
                "Form '"
                + formName
                + "' already exists in FormSet["
                + self.displayKey()
                + "] - ignoring."
            )
        else:
            self.__forms[formName] = f

    def addConstant(self, name: str, value: str) -> None:
        if name in self.__constants:
            self.__getLog().error(
                "Constant '"
                + name
                + "' already exists in FormSet["
                + self.displayKey()
                + "] - ignoring."
            )
        else:
            self.__constants[name] = value

    def setVariant(self, variant: str) -> None:
        self.__variant = variant

    def getVariant(self) -> str:
        return self.__variant

    def setCountry(self, country: str) -> None:
        self.__country = country

    def getCountry(self) -> str:
        return self.__country

    def setLanguage(self, language: str) -> None:
        self.__language = language

    def getLanguage(self) -> str:
        return self.__language

    def isProcessed(self) -> bool:
        return self.__processed

    def _getType(self) -> int:
        if self.getVariant() is not None:
            if self.getLanguage() is None or self.getCountry() is None:
                raise ValueError(
                    "When variant is specified, country and language must be specified."
                )
            return FormSet._VARIANT_FORMSET
        elif self.getCountry() is not None:
            if self.getLanguage() is None:
                raise ValueError(
                    "When country is specified, language must be specified."
                )
            return FormSet._COUNTRY_FORMSET
        elif self.getLanguage() is not None:
            return FormSet._LANGUAGE_FORMSET
        else:
            return FormSet._GLOBAL_FORMSET

    def _isMerged(self) -> bool:
        return self.__merged

    def __getLog(self) -> logging.Logger:
        if self.__log is None:
            self.__log = logging.getLogger(
                "org.apache.commons.validator.FormSet"
            )
        return self.__log

    # Class Methods End
