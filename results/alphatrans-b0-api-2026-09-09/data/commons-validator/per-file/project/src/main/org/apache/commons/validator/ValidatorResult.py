from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.Field import *
import typing
from typing import *
import io

# Imports End


class ResultStatus:

    # Class Fields Begin
    __serialVersionUID: int = 4076665918535320007
    __valid: bool = None
    __result: typing.Any = None
    # Class Fields End

    # Class Methods Begin
    def isValid(self) -> bool:
        return self.__valid

    def setResult(self, result: typing.Any) -> None:
        self.__result = result

    def getResult(self) -> typing.Any:
        return self.__result

    def setValid(self, valid: bool) -> None:
        self.__valid = valid

    @staticmethod
    def ResultStatus0(
        ignored: ValidatorResult, valid: bool, result: typing.Any
    ) -> ResultStatus:
        return ResultStatus(1, result, None, valid)

    def __init__(
        self,
        constructorId: int,
        result: typing.Any,
        ignored: ValidatorResult,
        valid: bool,
    ) -> None:
        if constructorId == 1:
            self.__valid = valid
            self.__result = result
        else:
            self.__valid = valid
            self.__result = result

    # Class Methods End


class ValidatorResult:

    # Class Fields Begin
    __serialVersionUID: int = -3713364681647250531
    _hAction: typing.Dict[str, ResultStatus] = None
    _field: typing.Any = None
    # Class Fields End

    # Class Methods Begin
    def getActionMap(self) -> typing.Dict[str, ResultStatus]:
        return dict(self._hAction)

    def getField(self) -> typing.Any:
        return self._field

    def getActions(self) -> typing.Iterator[str]:
        return iter(list(self._hAction.keys()))

    def getResult(self, validatorName: str) -> typing.Any:
        status = self._hAction.get(validatorName)
        return None if status is None else status.getResult()

    def isValid(self, validatorName: str) -> bool:
        status = self._hAction.get(validatorName)
        return False if status is None else status.isValid()

    def containsAction(self, validatorName: str) -> bool:
        return validatorName in self._hAction

    def add1(self, validatorName: str, result: bool, value: typing.Any) -> None:
        self._hAction[validatorName] = ResultStatus(1, value, None, result)

    def add0(self, validatorName: str, result: bool) -> None:
        self.add1(validatorName, result, None)

    def __init__(self, field: typing.Any) -> None:
        self._hAction = {}
        self._field = field

    # Class Methods End
