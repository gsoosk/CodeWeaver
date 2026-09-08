from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.PatternOptionBuilder import *
from src.main.org.apache.commons.cli.ParseException import *
import urllib
import datetime
import typing
from typing import *
import numbers
import io
import pathlib
import builtins
import importlib
import inspect
import sys

# Imports End

# Schemes recognized out-of-the-box by java.net.URL's default
# protocol handlers (http, https, ftp, file, jar, mailto). Anything
# else mirrors a MalformedURLException ("unknown protocol").
_KNOWN_URL_SCHEMES = frozenset({"http", "https", "ftp", "file", "jar", "mailto"})

# Restrict wildcard imports (`from ... import *`) to the public class only,
# so that helper module imports like `datetime` are not re-exported and do
# not shadow same-named symbols (e.g. `datetime.datetime`) in importers.
__all__ = ["TypeHandler", "ParseException"]


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
    def openFile(str_: str) -> typing.Union[io.FileIO, io.BufferedReader, io.TextIOWrapper]:
        try:
            return open(str_, "r")
        except OSError as e:
            raise ParseException("Unable to find file: " + str_) from e

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
        parsed = urllib.parse.urlparse(str_)
        # Mirror java.net.URL: only known/registered protocol handlers are
        # accepted, everything else raises MalformedURLException -> ParseException.
        if not parsed.scheme or parsed.scheme.lower() not in _KNOWN_URL_SCHEMES:
            raise ParseException("Unable to parse the URL: " + str_)
        return parsed

    @staticmethod
    def createObject(classname: str) -> typing.Any:
        cl = TypeHandler.createClass(classname)

        try:
            return cl()
        except Exception as e:
            raise ParseException(
                type(e).__name__ + "; Unable to create an instance of: " + classname
            ) from e

    @staticmethod
    def createNumber(str_: str) -> typing.Union[int, float, numbers.Number]:
        try:
            if "." in str_:
                return float(str_)
            return int(str_)
        except ValueError as e:
            raise ParseException(str(e)) from e

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
        module_name, _, class_name = classname.rpartition(".")

        if module_name:
            try:
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
            except (ImportError, AttributeError, ValueError) as e:
                raise ParseException("Unable to find the class: " + classname) from e

        # Unqualified name: mirror Java's Class.forName lookup, which
        # searches the whole classpath rather than a single namespace.
        if hasattr(builtins, class_name):
            return getattr(builtins, class_name)

        # Treat the whole name as an importable top-level module (e.g. "datetime").
        try:
            module = importlib.import_module(class_name)
            # Some modules expose a class of the same name as the module
            # itself (e.g. the "datetime" module's "datetime" class). Prefer
            # that same-named class attribute over the bare module, mirroring
            # how a fully-qualified Java classname always resolves to a class.
            same_named = getattr(module, class_name, None)
            if isinstance(same_named, type):
                return same_named
            return module
        except ImportError:
            pass

        # Search frames on the call stack for a class defined in the
        # caller's scope (covers classes declared alongside the caller,
        # analogous to Java classes visible on the classpath).
        for frame_info in inspect.stack():
            frame = frame_info.frame
            candidate = frame.f_locals.get(class_name, frame.f_globals.get(class_name))
            if isinstance(candidate, type):
                return candidate

        # Finally, look through already-imported modules for a matching class.
        for module in list(sys.modules.values()):
            if module is None:
                continue
            candidate = getattr(module, class_name, None)
            if isinstance(candidate, type):
                return candidate

        raise ParseException("Unable to find the class: " + classname)

    # Class Methods End
