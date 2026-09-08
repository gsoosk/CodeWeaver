from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.ValidatorException import *
from src.main.org.apache.commons.validator.Validator import *

# from src.main.org.apache.commons.logging.LogFactory import *
# from src.main.org.apache.commons.logging.Log import *
import logging
import inspect
import typing
from typing import *
import io

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
    __validationMethod: typing.Union[inspect.Signature, typing.Callable] = None
    __methodParams: str = None
    __parameterClasses: typing.List[typing.Type[typing.Any]] = None
    __depends: str = None
    __msg: str = None
    __jsFunctionName: str = None
    # Class Fields End

    def __init__(self) -> None:
        self.__jsFunction = None
        self.__javascript = None
        self.__instance = None
        self.__dependencyList = []
        self.__methodParameterList = []
        self.__log = None
        self.__name = None
        self.__classname = None
        self.__validationClass = None
        self.__method = None
        self.__validationMethod = None
        self.__methodParams = (
            str(Validator.BEAN_PARAM)
            + ","
            + str(Validator.VALIDATOR_ACTION_PARAM)
            + ","
            + str(Validator.FIELD_PARAM)
        )
        self.__parameterClasses = None
        self.__depends = None
        self.__msg = None
        self.__jsFunctionName = None

    # Class Methods Begin
    def toString(self) -> str:
        results = io.StringIO()
        results.write("ValidatorAction: ")
        results.write(str(self.__name))
        results.write("\n")

        return results.getvalue()

    def __str__(self) -> str:
        return self.toString()

    def getDependencyList(self) -> typing.List[str]:
        return list(self.__dependencyList)

    def isDependency(self, validatorName: str) -> bool:
        return validatorName in self.__dependencyList

    def _loadJavascriptFunction(self) -> None:
        if self.__javascriptAlreadyLoaded():
            return

        if self.__getLog().isEnabledFor(logging.DEBUG):
            self.__getLog().debug("  Loading function begun")

        if self.__jsFunction is None:
            self.__jsFunction = self.__generateJsFunction()

        javascriptFileName = self.__formatJavascriptFileName()

        if self.__getLog().isEnabledFor(logging.DEBUG):
            self.__getLog().debug("  Loading js function '" + javascriptFileName + "'")

        self.__javascript = self.__readJavascriptFile(javascriptFileName)

        if self.__getLog().isEnabledFor(logging.DEBUG):
            self.__getLog().debug("  Loading javascript function completed")

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

        self.__dependencyList.clear()

        for depend in depends.split(","):
            depend = depend.strip()
            if depend is not None and len(depend) > 0:
                self.__dependencyList.append(depend)

    def getDepends(self) -> str:
        return self.__depends

    def setMethodParams(self, methodParams: str) -> None:
        self.__methodParams = methodParams

        self.__methodParameterList.clear()

        for value in methodParams.split(","):
            value = value.strip()
            if value is not None and len(value) > 0:
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
            self.__log = logging.getLogger(ValidatorAction.__module__ + ".ValidatorAction")
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
        is_static = isinstance(self.__validationMethod, staticmethod) or (
            inspect.isfunction(self.__validationMethod)
            and not inspect.signature(self.__validationMethod).parameters.get("self")
        )

        if is_static:
            self.__instance = None
        else:
            if self.__instance is None:
                try:
                    self.__instance = self.__validationClass()
                except Exception as e:
                    msg1 = "Couldn't create instance of " + str(self.__classname) + ".  " + str(e)
                    raise ValidatorException(msg1)

        return self.__instance

    def __getParameterValues(
        self, params: typing.Dict[str, typing.Any]
    ) -> typing.List[typing.Any]:
        paramValue: typing.List[typing.Any] = [None] * len(self.__methodParameterList)

        for i in range(len(self.__methodParameterList)):
            paramClassName = self.__methodParameterList[i]
            paramValue[i] = params.get(paramClassName)

        return paramValue

    def __loadParameterClasses(self, loader: typing.Any) -> None:
        if self.__parameterClasses is not None:
            return

        parameterClasses: typing.List[typing.Type[typing.Any]] = [None] * len(
            self.__methodParameterList
        )

        for i in range(len(self.__methodParameterList)):
            paramClassName = self.__methodParameterList[i]

            try:
                parameterClasses[i] = loader.loadClass(paramClassName)
            except Exception as e:
                raise ValidatorException(str(e))

        self.__parameterClasses = parameterClasses

    def __loadValidationClass(self, loader: typing.Any) -> None:
        if self.__validationClass is not None:
            return

        try:
            self.__validationClass = loader.loadClass(self.__classname)
        except Exception as e:
            raise ValidatorException(str(e))

    def __loadValidationMethod(self) -> None:
        if self.__validationMethod is not None:
            return

        try:
            self.__validationMethod = getattr(self.__validationClass, self.__method)
        except AttributeError as e:
            raise ValidatorException("No such validation method: " + str(e))

    def __generateJsFunction(self) -> str:
        jsName = io.StringIO()
        jsName.write("org.apache.commons.validator.javascript")

        jsName.write(".validate")
        jsName.write(self.__name[0:1].upper())
        jsName.write(self.__name[1:len(self.__name)])

        return jsName.getvalue()

    def __javascriptAlreadyLoaded(self) -> bool:
        return self.__javascript is not None

    def __formatJavascriptFileName(self) -> str:
        fname = self.__jsFunction[1:]

        if not self.__jsFunction.startswith("/"):
            fname = self.__jsFunction.replace(".", "/") + ".js"

        return fname

    def __readJavascriptFile(self, javascriptFileName: str) -> str:
        try:
            with open(javascriptFileName, "r") as f:
                function = f.read()
        except OSError:
            self.__getLog().debug("  Unable to read javascript name " + javascriptFileName)
            return None

        return None if function == "" else function

    # Class Methods End
