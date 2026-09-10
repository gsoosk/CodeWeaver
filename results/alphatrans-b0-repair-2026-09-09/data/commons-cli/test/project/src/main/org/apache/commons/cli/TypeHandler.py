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
    _JAVA_CLASS_ALIASES: typing.Dict[str, typing.Any] = {
        "java.lang.String": str,
        "java.lang.Object": object,
        "java.lang.Integer": int,
        "java.lang.Long": int,
        "java.lang.Short": int,
        "java.lang.Byte": int,
        "java.lang.Double": float,
        "java.lang.Float": float,
        "java.lang.Boolean": bool,
        "java.lang.Character": str,
        "java.lang.Void": type(None),
        "java.util.Date": datetime.datetime,
        "java.util.Calendar": datetime.datetime,
    }

    _KNOWN_URL_SCHEMES: typing.Set[str] = {
        "http",
        "https",
        "ftp",
        "file",
        "jar",
        "mailto",
        "gopher",
    }
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
            return io.FileIO(str_, "r")
        except (FileNotFoundError, OSError, ValueError):
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
            result = urllib.parse.urlparse(str_)
            if (
                not result.scheme
                or result.scheme.lower() not in TypeHandler._KNOWN_URL_SCHEMES
            ):
                raise ValueError("no scheme")
            return result
        except ValueError:
            raise ParseException("Unable to parse the URL: " + str_)

    @staticmethod
    def __resolveClass(classname: str) -> typing.Any:
        if classname is None or "." not in classname:
            raise ImportError("Unable to find the class: " + str(classname))

        if classname in TypeHandler._JAVA_CLASS_ALIASES:
            return TypeHandler._JAVA_CLASS_ALIASES[classname]

        parts = classname.split(".")

        # This translated project keeps Java's original fully qualified
        # package/class names in tests (e.g. "org.apache.commons.cli.X"),
        # but the actual Python module lives under "src.main.<same path>"
        # and the class shares the module's last path segment as its name.
        try:
            module = importlib.import_module("src.main." + classname)
            return getattr(module, parts[-1])
        except (ImportError, AttributeError, ModuleNotFoundError):
            pass

        module = None
        consumed = 0

        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            try:
                module = importlib.import_module(candidate)
                consumed = i
                break
            except ImportError:
                continue

        if module is None:
            raise ImportError("Unable to find the class: " + classname)

        obj = module
        for part in parts[consumed:]:
            obj = getattr(obj, part)

        return obj

    @staticmethod
    def createObject(classname: str) -> typing.Any:
        try:
            cl = TypeHandler.__resolveClass(classname)
        except (ImportError, AttributeError, ModuleNotFoundError):
            raise ParseException("Unable to find the class: " + classname)

        try:
            return cl()
        except Exception as e:
            raise ParseException(
                type(e).__module__
                + "."
                + type(e).__name__
                + "; Unable to create an instance of: "
                + classname
            )

    @staticmethod
    def createNumber(str_: str) -> typing.Union[int, float, numbers.Number]:
        try:
            if "." in str_:
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
            return TypeHandler.__resolveClass(classname)
        except (ImportError, AttributeError, ModuleNotFoundError):
            raise ParseException("Unable to find the class: " + classname)

    # Class Methods End
