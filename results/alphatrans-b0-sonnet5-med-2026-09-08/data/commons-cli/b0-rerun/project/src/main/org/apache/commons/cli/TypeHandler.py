from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.PatternOptionBuilder import *
from src.main.org.apache.commons.cli.ParseException import *
import urllib
import urllib.parse
import datetime
import typing
from typing import *
import numbers
import io
import pathlib
import importlib

# Imports End


class TypeHandler:

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def createValue0(str_: str, clazz: typing.Type[typing.Any]) -> typing.Any:
        if PatternOptionBuilder.STRING_VALUE == clazz:
            return str_
        if PatternOptionBuilder.OBJECT_VALUE == clazz:
            return TypeHandler.createObject(str_)
        if PatternOptionBuilder.NUMBER_VALUE == clazz:
            return TypeHandler.createNumber(str_)
        if PatternOptionBuilder.DATE_VALUE == clazz:
            return TypeHandler.createDate(str_)
        if PatternOptionBuilder.CLASS_VALUE == clazz:
            return TypeHandler.createClass(str_)
        if PatternOptionBuilder.FILE_VALUE == clazz:
            return TypeHandler.createFile(str_)
        if PatternOptionBuilder.EXISTING_FILE_VALUE == clazz:
            return TypeHandler.openFile(str_)
        if PatternOptionBuilder.FILES_VALUE == clazz:
            return TypeHandler.createFiles(str_)
        if PatternOptionBuilder.URL_VALUE == clazz:
            return TypeHandler.createURL(str_)
        raise ParseException("Unable to handle the class: " + str(clazz))

    @staticmethod
    def openFile(str_: str) -> typing.Union[io.FileIO, io.BufferedReader]:
        try:
            return open(str_, "rb")
        except FileNotFoundError:
            raise ParseException("Unable to find file: " + str_)

    @staticmethod
    def createValue1(str_: str, obj: typing.Any) -> typing.Any:
        return TypeHandler.createValue0(str_, obj)

    @staticmethod
    def createURL(
        str_: str,
    ) -> typing.Union[
        urllib.parse.ParseResult,
        urllib.parse.SplitResult,
        urllib.parse.DefragResult,
        str,
    ]:
        try:
            parsed = urllib.parse.urlparse(str_)
            if not parsed.scheme:
                raise ValueError("Malformed URL")
            return parsed
        except Exception:
            raise ParseException("Unable to parse the URL: " + str_)

    @staticmethod
    def createObject(classname: str) -> typing.Any:
        try:
            cl = TypeHandler.createClass(classname)
        except ParseException:
            raise ParseException("Unable to find the class: " + classname)

        try:
            return cl()
        except Exception as e:
            raise ParseException(
                type(e).__name__ + "; Unable to create an instance of: " + classname
            )

    @staticmethod
    def createNumber(str_: str) -> typing.Union[int, float, numbers.Number]:
        try:
            if str_.find(".") != -1:
                return float(str_)
            return int(str_)
        except ValueError as e:
            raise ParseException(str(e))

    @staticmethod
    def createFiles(str_: str) -> typing.List[pathlib.Path]:
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def createFile(str_: str) -> pathlib.Path:
        return pathlib.Path(str_)

    @staticmethod
    def createDate(str_: str) -> typing.Union[datetime.datetime, datetime.date]:
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def createClass(classname: str) -> typing.Type[typing.Any]:
        try:
            module_name, _, cls_name = classname.rpartition(".")
            if module_name:
                mod = importlib.import_module(module_name)
                return getattr(mod, cls_name)
            return eval(classname)
        except Exception:
            raise ParseException("Unable to find the class: " + classname)

    # Class Methods End
