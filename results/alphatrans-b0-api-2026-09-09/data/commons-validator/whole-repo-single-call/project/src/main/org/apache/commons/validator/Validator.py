from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.ValidatorResources import *
import typing
from typing import *
import io

# Imports End


class Validator:

    # Class Fields Begin
    _classLoader: typing.Any = None
    _useContextClassLoader: bool = False
    _onlyReturnErrors: bool = False
    __serialVersionUID: int = -7119418755208731611
    BEAN_PARAM: str = "java.lang.Object"
    VALIDATOR_ACTION_PARAM: str = "org.apache.commons.validator.ValidatorAction"
    VALIDATOR_RESULTS_PARAM: str = "org.apache.commons.validator.ValidatorResults"
    FORM_PARAM: str = "org.apache.commons.validator.Form"
    FIELD_PARAM: str = "org.apache.commons.validator.Field"
    VALIDATOR_PARAM: str = "org.apache.commons.validator.Validator"
    LOCALE_PARAM: str = "java.util.Locale"
    _resources: ValidatorResources = None
    _formName: str = None
    _fieldName: str = None
    _parameters: typing.Dict[str, typing.Any] = None
    _page: int = 0
    # Class Fields End

    # Class Methods Begin
    def setOnlyReturnErrors(self, onlyReturnErrors: bool) -> None:
        self._onlyReturnErrors = onlyReturnErrors

    def getOnlyReturnErrors(self) -> bool:
        return self._onlyReturnErrors

    def setClassLoader(self, classLoader: typing.Any) -> None:
        self._classLoader = classLoader

    def getClassLoader(self) -> typing.Any:
        return self._classLoader

    def setUseContextClassLoader(self, use: bool) -> None:
        self._useContextClassLoader = use

    def getUseContextClassLoader(self) -> bool:
        return self._useContextClassLoader

    def clear(self) -> None:
        self._formName = None
        self._fieldName = None
        self._parameters = {}
        self._page = 0

    def setPage(self, page: int) -> None:
        self._page = page

    def getPage(self) -> int:
        return self._page

    def setFieldName(self, fieldName: str) -> None:
        self._fieldName = fieldName

    def setFormName(self, formName: str) -> None:
        self._formName = formName

    def getFormName(self) -> str:
        return self._formName

    def getParameterValue(self, parameterClassName: str) -> typing.Any:
        return self._parameters.get(parameterClassName)

    def setParameter(self, parameterClassName: str, parameterValue: typing.Any) -> None:
        self._parameters[parameterClassName] = parameterValue

    @staticmethod
    def Validator2(resources: ValidatorResources) -> Validator:
        return Validator(1, resources, None, None)

    def __init__(
        self,
        constructorId: int,
        resources: ValidatorResources,
        formName: str,
        fieldName: str,
    ) -> None:
        self._parameters = {}
        if resources is None:
            raise ValueError("Resources cannot be null.")
        self._resources = resources
        self._formName = formName
        if constructorId == 0:
            self._fieldName = fieldName

    # Class Methods End
