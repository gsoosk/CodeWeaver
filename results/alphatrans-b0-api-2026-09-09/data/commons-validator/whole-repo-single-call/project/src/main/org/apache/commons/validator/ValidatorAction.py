from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.ValidatorException import *
from src.main.org.apache.commons.validator.Validator import *
import logging
import typing
from typing import *
import io
import inspect

# Imports End


class ValidatorAction:

    # Class Fields Begin
    __jsFunction: str = None
    __javascript: str = None
    __instance: typing.Any = None
    __dependencyList: typing.List[str] = None
    __methodParameterList: typing.List[str] = None
    __serialVersionUID: int = 1339713700053204597
    __log: logging.Logger = None
    __name: str = None
    __classname: str = None
    __validationClass: typing.Type[typing.Any] = None
    __method: str = None
    __validationMethod: typing.Any = None
    __methodParams: str = "java.lang.Object,org.apache.commons.validator.ValidatorAction,org.apache.commons.validator.Field"
    __parameterClasses: typing.List[typing.Any] = None
    __depends: str = None
    __msg: str = None
    __jsFunctionName: str = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.__dependencyList = []
        self.__methodParameterList = []

    def toString(self) -> str:
        return "ValidatorAction: " + str(self.__name) + "\n"

    def __str__(self) -> str:
        return self.toString()

    def getDependencyList(self) -> typing.List[str]:
        return list(self.__dependencyList)

    def isDependency(self, validatorName: str) -> bool:
        return validatorName in self.__dependencyList

    def _loadJavascriptFunction(self) -> None:
        if self.__javascriptAlreadyLoaded():
            return

    def _init(self) -> None:
        self._loadJavascriptFunction()

    def setJavascript(self, javascript: str) -> None:
        if self.__jsFunction is not None:
            raise ValueError("Cannot call setJavascript() after calling setJsFunction()")
        self.__javascript = javascript

    def getJavascript(self) -> str:
        return self.__javascript

    def setJsFunction(self, jsFunction: str) -> None:
        if self.__javascript is not None:
            raise ValueError("Cannot call setJsFunction() after calling setJavascript()")
        self.__jsFunction = jsFunction

    def setJsFunctionName(self, jsFunctionName: str) -> None:
        self.__jsFunctionName = jsFunctionName

    def getJsFunctionName(self) -> str:
        return self.__jsFunctionName

    def setMsg(self, msg: str) -> None:
        self.__msg = msg

    def getMsg(self) -> str:
        return self.__msg

    def setDepends(self, depends: str) -> None:
        self.__depends = depends
        self.__dependencyList = []
        if depends:
            for token in depends.split(","):
                depend = token.strip()
                if depend:
                    self.__dependencyList.append(depend)

    def getDepends(self) -> str:
        return self.__depends

    def setMethodParams(self, methodParams: str) -> None:
        self.__methodParams = methodParams
        self.__methodParameterList = []
        if methodParams:
            for token in methodParams.split(","):
                value = token.strip()
                if value:
                    self.__methodParameterList.append(value)

    def getMethodParams(self) -> str:
        return self.__methodParams

    def setMethod(self, method: str) -> None:
        self.__method = method

    def getMethod(self) -> str:
        return self.__method

    def setClassname(self, classname: str) -> None:
        self.__classname = classname

    def getClassname(self) -> str:
        return self.__classname

    def setName(self, name: str) -> None:
        self.__name = name

    def getName(self) -> str:
        return self.__name

    def __getLog(self) -> logging.Logger:
        if self.__log is None:
            self.__log = logging.getLogger("ValidatorAction")
        return self.__log

    def __onlyReturnErrors(self, params: typing.Dict[str, typing.Any]) -> bool:
        v = params.get(Validator.VALIDATOR_PARAM)
        return v.getOnlyReturnErrors()

    def __getClassLoader(self, params: typing.Dict[str, typing.Any]) -> typing.Any:
        v = params.get(Validator.VALIDATOR_PARAM)
        return v.getClassLoader()

    def __isValid(self, result: typing.Any) -> bool:
        if isinstance(result, bool):
            return result
        return result is not None

    def __getValidationClassInstance(self) -> typing.Any:
        return self.__instance

    def __getParameterValues(self, params: typing.Dict[str, typing.Any]) -> typing.List[typing.Any]:
        return [params.get(name) for name in self.__methodParameterList]

    def __loadParameterClasses(self, loader: typing.Any) -> None:
        pass

    def __loadValidationClass(self, loader: typing.Any) -> None:
        pass

    def __loadValidationMethod(self) -> None:
        pass

    def __generateJsFunction(self) -> str:
        jsName = "org.apache.commons.validator.javascript.validate"
        if self.__name:
            jsName += self.__name[0:1].upper() + self.__name[1:]
        return jsName

    def __javascriptAlreadyLoaded(self) -> bool:
        return self.__javascript is not None

    def __formatJavascriptFileName(self) -> str:
        if self.__jsFunction is None:
            return None
        fname = self.__jsFunction[1:]
        if not self.__jsFunction.startswith("/"):
            fname = self.__jsFunction.replace(".", "/") + ".js"
        return fname

    def __readJavascriptFile(self, javascriptFileName: str) -> str:
        return None

    # Class Methods End
