from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.PatternOptionBuilder import *
from src.main.org.apache.commons.cli.ParseException import *
import urllib
import urllib.parse
from datetime import datetime, date
import typing
from typing import *
import numbers
import io
import pathlib
import pydoc
import inspect
import sys

# Imports End


class TypeHandler:

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def createValue0(str_: str, clazz: typing.Type[typing.Any]) -> typing.Any:
        if PatternOptionBuilder.STRING_VALUE is clazz:
            return str_
        if PatternOptionBuilder.OBJECT_VALUE is clazz:
            return TypeHandler.createObject(str_)
        if PatternOptionBuilder.NUMBER_VALUE is clazz:
            return TypeHandler.createNumber(str_)
        if PatternOptionBuilder.DATE_VALUE is clazz:
            return TypeHandler.createDate(str_)
        if PatternOptionBuilder.CLASS_VALUE is clazz:
            return TypeHandler.createClass(str_)
        if PatternOptionBuilder.FILE_VALUE is clazz:
            return TypeHandler.createFile(str_)
        if PatternOptionBuilder.EXISTING_FILE_VALUE is clazz:
            return TypeHandler.openFile(str_)
        if PatternOptionBuilder.FILES_VALUE is clazz:
            return TypeHandler.createFiles(str_)
        if PatternOptionBuilder.URL_VALUE is clazz:
            return TypeHandler.createURL(str_)
        raise ParseException("Unable to handle the class: " + str(clazz))

    @staticmethod
    def openFile(str_: str) -> typing.Union[io.FileIO, io.BufferedReader]:
        try:
            return open(str_, "r")
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
        known_protocols = (
            "http",
            "https",
            "ftp",
            "file",
            "jar",
            "mailto",
            "netdoc",
        )

        try:
            result = urllib.parse.urlparse(str_)
        except ValueError:
            raise ParseException("Unable to parse the URL: " + str_)

        if (
            not result.scheme
            or result.scheme.lower() not in known_protocols
            or result.geturl() != str_
        ):
            raise ParseException("Unable to parse the URL: " + str_)

        return result

    @staticmethod
    def createObject(classname: str) -> typing.Any:
        cl = TypeHandler.createClass(classname)

        try:
            return cl()
        except Exception as e:
            raise ParseException(
                type(e).__name__ + "; Unable to create an instance of: " + classname
            )

    @staticmethod
    def createNumber(str_: str) -> typing.Union[int, float, numbers.Number]:
        try:
            if '.' in str_:
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
        simple = classname.rsplit(".", 1)[-1]

        located = None
        try:
            located = pydoc.locate(classname)
        except Exception:
            located = None

        # Java's Class.forName resolves a name to a class, never to a
        # package/module. pydoc.locate may return a module (e.g. "datetime"
        # yields the datetime module), so only accept a class result; when a
        # module is returned, prefer the attribute matching the simple name.
        cl: typing.Optional[type] = None
        if isinstance(located, type):
            cl = located
        elif located is not None:
            attr = getattr(located, simple, None)
            if isinstance(attr, type):
                cl = attr

        if cl is None:

            def _match(candidate: typing.Any) -> typing.Optional[type]:
                if isinstance(candidate, type) and candidate.__name__ == simple:
                    return candidate
                return None

            def _search(namespace: typing.Mapping[str, typing.Any]) -> typing.Optional[type]:
                found = _match(namespace.get(classname))
                if found is None:
                    found = _match(namespace.get(simple))
                if found is not None:
                    return found
                for value in list(namespace.values()):
                    if isinstance(value, type):
                        try:
                            nested = getattr(value, simple, None)
                        except Exception:
                            nested = None
                        found = _match(nested)
                        if found is not None:
                            return found
                return None

            frame = inspect.currentframe()
            try:
                if frame is not None:
                    frame = frame.f_back
                while frame is not None and cl is None:
                    cl = _search(frame.f_globals)
                    if cl is None:
                        cl = _search(frame.f_locals)
                    frame = frame.f_back
            finally:
                del frame

            if cl is None:
                for module in list(sys.modules.values()):
                    if module is None:
                        continue
                    try:
                        namespace = vars(module)
                    except TypeError:
                        continue
                    found = _match(namespace.get(classname))
                    if found is None:
                        found = _match(namespace.get(simple))
                    if found is not None:
                        cl = found
                        break

        if cl is None:
            raise ParseException("Unable to find the class: " + classname)

        return cl

    # Class Methods End
