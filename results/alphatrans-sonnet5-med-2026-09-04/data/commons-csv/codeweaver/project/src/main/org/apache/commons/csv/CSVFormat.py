from __future__ import annotations

# Imports Begin
import pathlib
from pathlib import Path
from src.main.org.apache.commons.csv.QuoteMode import *
from src.main.org.apache.commons.csv.IOUtils import *
from src.main.org.apache.commons.csv.ExtendedBufferedReader import *
from src.main.org.apache.commons.csv.DuplicateHeaderMode import *
from src.main.org.apache.commons.csv.Constants import *
from src.main.org.apache.commons.csv.CSVPrinter import *
from src.main.org.apache.commons.csv.CSVParser import *
import os
import sys
import typing
from typing import *
import io
from io import IOBase

# Imports End


# Module-level helpers.
#
# These exist so that Builder and CSVFormat -- two separate top-level Python
# classes translating what was, in Java, an outer class (CSVFormat) and a
# nested inner class (CSVFormat.Builder) with implicit access to each
# other's private members -- can share logic without falling into Python's
# name-mangling trap (writing `CSVFormat.__foo` inside Builder's method
# bodies would mangle to `CSVFormat._Builder__foo`, not
# `CSVFormat._CSVFormat__foo`). Keeping the shared logic here, and reading
# private fields across classes with `getattr`/an explicit mangled name
# string, sidesteps that pitfall entirely.
def _is_line_break0(c: typing.Optional[str]) -> bool:
    return c is not None and (c == Constants.LF or c == Constants.CR)


def _is_line_break1(c: typing.Optional[str]) -> bool:
    return c is not None and _is_line_break0(c)


def _contains(source: typing.Optional[str], search_ch: str) -> bool:
    if source is None:
        raise ValueError("source")
    return search_ch in source


def _contains_line_break(source: str) -> bool:
    return _contains(source, Constants.CR) or _contains(source, Constants.LF)


def _is_trim_char0(ch: str) -> bool:
    return ch <= Constants.SP


def _is_trim_char1(char_sequence: str, pos: int) -> bool:
    return _is_trim_char0(char_sequence[pos])


def _to_string_array(
    values: typing.Optional[typing.List[typing.Any]],
) -> typing.Optional[typing.List[str]]:
    if values is None:
        return None
    return [None if v is None else str(v) for v in values]


def _clone(values: typing.Optional[typing.List[typing.Any]]) -> typing.Optional[typing.List[typing.Any]]:
    return None if values is None else list(values)


def _trim0(char_sequence: typing.Optional[str]) -> typing.Optional[str]:
    if char_sequence is None:
        return char_sequence
    length = len(char_sequence)
    start = 0
    end = length
    while start < end and _is_trim_char1(char_sequence, start):
        start += 1
    while start < end and _is_trim_char1(char_sequence, end - 1):
        end -= 1
    return char_sequence[start:end]


def _is_blank(value: typing.Optional[str]) -> bool:
    return value is None or _trim0(value) == ""


def _java_concat3(a: typing.Any, b: typing.Any, c: typing.Any) -> str:
    # Mirrors Java string concatenation of possibly-null values, where a
    # null operand contributes the four literal characters "null" (per
    # StringBuilder.append(String)/append(Object) semantics) rather than
    # being skipped, as an empty Python string would be.
    def part(x: typing.Any) -> str:
        return "null" if x is None else str(x)

    return part(a) + part(b) + part(c)


def _java_bool(v: bool) -> str:
    return "true" if v else "false"


def _java_array_to_string(arr: typing.Optional[typing.List[typing.Any]]) -> str:
    if arr is None:
        return "null"
    return "[" + ", ".join("null" if e is None else str(e) for e in arr) + "]"


def _is_number(v: typing.Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Builder:

    # Class Fields Begin
    __allowMissingColumnNames: bool = None
    __autoFlush: bool = None
    __commentMarker: str = None
    __delimiter: str = None
    __duplicateHeaderMode: DuplicateHeaderMode = None
    __escapeCharacter: str = None
    __headerComments: typing.List[typing.List[str]] = None
    __headers: typing.List[typing.List[str]] = None
    __ignoreEmptyLines: bool = None
    __ignoreHeaderCase: bool = None
    __ignoreSurroundingSpaces: bool = None
    __nullString: str = None
    __quoteCharacter: str = None
    __quotedNullString: str = None
    __quoteMode: QuoteMode = None
    __recordSeparator: str = None
    __skipHeaderRecord: bool = None
    __trailingDelimiter: bool = None
    __trim: bool = None
    # Class Fields End

    # Class Methods Begin
    def setAllowDuplicateHeaderNames(self, allowDuplicateHeaderNames: bool) -> Builder:
        self.setDuplicateHeaderMode(
            DuplicateHeaderMode.ALLOW_ALL
            if allowDuplicateHeaderNames
            else DuplicateHeaderMode.ALLOW_EMPTY
        )
        return self

    def setTrim(self, trim: bool) -> Builder:
        self.__trim = trim
        return self

    def setTrailingDelimiter(self, trailingDelimiter: bool) -> Builder:
        self.__trailingDelimiter = trailingDelimiter
        return self

    def setSkipHeaderRecord(self, skipHeaderRecord: bool) -> Builder:
        self.__skipHeaderRecord = skipHeaderRecord
        return self

    def setRecordSeparator1(self, recordSeparator: str) -> Builder:
        self.__recordSeparator = recordSeparator
        return self

    def setRecordSeparator0(self, recordSeparator: str) -> Builder:
        self.__recordSeparator = str(recordSeparator)
        return self

    def setQuoteMode(self, quoteMode: QuoteMode) -> Builder:
        self.__quoteMode = quoteMode
        return self

    def setQuote1(self, quoteCharacter: str) -> Builder:
        if _is_line_break1(quoteCharacter):
            raise ValueError("The quoteChar cannot be a line break")
        self.__quoteCharacter = quoteCharacter
        return self

    def setQuote0(self, quoteCharacter: str) -> Builder:
        self.setQuote1(quoteCharacter)
        return self

    def setNullString(self, nullString: str) -> Builder:
        self.__nullString = nullString
        self.__quotedNullString = _java_concat3(
            self.__quoteCharacter, nullString, self.__quoteCharacter
        )
        return self

    def setIgnoreSurroundingSpaces(self, ignoreSurroundingSpaces: bool) -> Builder:
        self.__ignoreSurroundingSpaces = ignoreSurroundingSpaces
        return self

    def setIgnoreHeaderCase(self, ignoreHeaderCase: bool) -> Builder:
        self.__ignoreHeaderCase = ignoreHeaderCase
        return self

    def setIgnoreEmptyLines(self, ignoreEmptyLines: bool) -> Builder:
        self.__ignoreEmptyLines = ignoreEmptyLines
        return self

    def setHeaderComments1(
        self, headerComments: typing.List[typing.List[str]]
    ) -> Builder:
        self.__headerComments = _clone(headerComments)
        return self

    def setHeaderComments0(self, headerComments: typing.List[typing.Any]) -> Builder:
        self.__headerComments = _clone(_to_string_array(headerComments))
        return self

    def setEscape1(self, escapeCharacter: str) -> Builder:
        if _is_line_break1(escapeCharacter):
            raise ValueError("The escape character cannot be a line break")
        self.__escapeCharacter = escapeCharacter
        return self

    def setEscape0(self, escapeCharacter: str) -> Builder:
        self.setEscape1(escapeCharacter)
        return self

    def setDuplicateHeaderMode(
        self, duplicateHeaderMode: DuplicateHeaderMode
    ) -> Builder:
        if duplicateHeaderMode is None:
            raise ValueError("duplicateHeaderMode")
        self.__duplicateHeaderMode = duplicateHeaderMode
        return self

    def setDelimiter1(self, delimiter: str) -> Builder:
        if _contains_line_break(delimiter):
            raise ValueError("The delimiter cannot be a line break")
        if delimiter == "":
            raise ValueError("The delimiter cannot be empty")
        self.__delimiter = delimiter
        return self

    def setDelimiter0(self, delimiter: str) -> Builder:
        return self.setDelimiter1(str(delimiter))

    def setCommentMarker1(self, commentMarker: str) -> Builder:
        if _is_line_break1(commentMarker):
            raise ValueError("The comment start marker character cannot be a line break")
        self.__commentMarker = commentMarker
        return self

    def setCommentMarker0(self, commentMarker: str) -> Builder:
        self.setCommentMarker1(commentMarker)
        return self

    def setAutoFlush(self, autoFlush: bool) -> Builder:
        self.__autoFlush = autoFlush
        return self

    def setAllowMissingColumnNames(self, allowMissingColumnNames: bool) -> Builder:
        self.__allowMissingColumnNames = allowMissingColumnNames
        return self

    def build(self) -> CSVFormat:
        return CSVFormat(
            1, False, False, None, None, None, False, False, self, None, False,
            None, None, False, None, None, False, False, None, None,
        )

    @staticmethod
    def create1(csvFormat: CSVFormat) -> Builder:
        return Builder(csvFormat)

    @staticmethod
    def create0() -> Builder:
        return Builder(CSVFormat.DEFAULT)

    def __init__(self, csvFormat: CSVFormat) -> None:
        self.__delimiter = getattr(csvFormat, "_CSVFormat__delimiter")
        self.__quoteCharacter = getattr(csvFormat, "_CSVFormat__quoteCharacter")
        self.__quoteMode = getattr(csvFormat, "_CSVFormat__quoteMode")
        self.__commentMarker = getattr(csvFormat, "_CSVFormat__commentMarker")
        self.__escapeCharacter = getattr(csvFormat, "_CSVFormat__escapeCharacter")
        self.__ignoreSurroundingSpaces = getattr(
            csvFormat, "_CSVFormat__ignoreSurroundingSpaces"
        )
        self.__allowMissingColumnNames = getattr(
            csvFormat, "_CSVFormat__allowMissingColumnNames"
        )
        self.__ignoreEmptyLines = getattr(csvFormat, "_CSVFormat__ignoreEmptyLines")
        self.__recordSeparator = getattr(csvFormat, "_CSVFormat__recordSeparator")
        self.__nullString = getattr(csvFormat, "_CSVFormat__nullString")
        self.__headerComments = getattr(csvFormat, "_CSVFormat__headerComments")
        self.__headers = getattr(csvFormat, "_CSVFormat__headers")
        self.__skipHeaderRecord = getattr(csvFormat, "_CSVFormat__skipHeaderRecord")
        self.__ignoreHeaderCase = getattr(csvFormat, "_CSVFormat__ignoreHeaderCase")
        self.__trailingDelimiter = getattr(csvFormat, "_CSVFormat__trailingDelimiter")
        self.__trim = getattr(csvFormat, "_CSVFormat__trim")
        self.__autoFlush = getattr(csvFormat, "_CSVFormat__autoFlush")
        self.__quotedNullString = getattr(csvFormat, "_CSVFormat__quotedNullString")
        self.__duplicateHeaderMode = getattr(
            csvFormat, "_CSVFormat__duplicateHeaderMode"
        )

    # Class Methods End


class Predefined:

    # Class Fields Begin
    Default: Predefined = None
    Excel: Predefined = None
    InformixUnload: Predefined = None
    InformixUnloadCsv: Predefined = None
    MongoDBCsv: Predefined = None
    MongoDBTsv: Predefined = None
    MySQL: Predefined = None
    Oracle: Predefined = None
    PostgreSQLCsv: Predefined = None
    PostgreSQLText: Predefined = None
    RFC4180: Predefined = None
    TDF: Predefined = None
    __format: CSVFormat = None
    # Class Fields End

    # Class Methods Begin
    def getFormat(self) -> CSVFormat:
        return self.__format

    def __init__(self, format_: CSVFormat) -> None:
        self.__format = format_

    # Class Methods End


class CSVFormat:

    # Class Fields Begin
    ORACLE: CSVFormat = None
    POSTGRESQL_CSV: CSVFormat = None
    POSTGRESQL_TEXT: CSVFormat = None
    RFC4180: CSVFormat = None
    __serialVersionUID: int = None
    TDF: CSVFormat = None
    __duplicateHeaderMode: DuplicateHeaderMode = None
    __allowMissingColumnNames: bool = None
    __autoFlush: bool = None
    __commentMarker: str = None
    __delimiter: str = None
    __escapeCharacter: str = None
    __headers: typing.List[typing.List[str]] = None
    __headerComments: typing.List[typing.List[str]] = None
    __ignoreEmptyLines: bool = None
    __ignoreHeaderCase: bool = None
    __ignoreSurroundingSpaces: bool = None
    __nullString: str = None
    __quoteCharacter: str = None
    __quotedNullString: str = None
    __quoteMode: QuoteMode = None
    __recordSeparator: str = None
    __skipHeaderRecord: bool = None
    __trailingDelimiter: bool = None
    __trim: bool = None
    DEFAULT: CSVFormat = None
    EXCEL: CSVFormat = None
    INFORMIX_UNLOAD: CSVFormat = None
    INFORMIX_UNLOAD_CSV: CSVFormat = None
    MONGODB_CSV: CSVFormat = None
    MONGODB_TSV: CSVFormat = None
    MYSQL: CSVFormat = None
    # Class Fields End

    # Class Methods Begin
    def withTrim1(self, trim: bool) -> CSVFormat:
        return self.builder().setTrim(trim).build()

    def withTrim0(self) -> CSVFormat:
        return self.builder().setTrim(True).build()

    def withTrailingDelimiter1(self, trailingDelimiter: bool) -> CSVFormat:
        return self.builder().setTrailingDelimiter(trailingDelimiter).build()

    def withTrailingDelimiter0(self) -> CSVFormat:
        return self.builder().setTrailingDelimiter(True).build()

    def withSystemRecordSeparator(self) -> CSVFormat:
        return self.builder().setRecordSeparator1(os.linesep).build()

    def withSkipHeaderRecord1(self, skipHeaderRecord: bool) -> CSVFormat:
        return self.builder().setSkipHeaderRecord(skipHeaderRecord).build()

    def withSkipHeaderRecord0(self) -> CSVFormat:
        return self.builder().setSkipHeaderRecord(True).build()

    def withRecordSeparator1(self, recordSeparator: str) -> CSVFormat:
        return self.builder().setRecordSeparator1(recordSeparator).build()

    def withRecordSeparator0(self, recordSeparator: str) -> CSVFormat:
        return self.builder().setRecordSeparator0(recordSeparator).build()

    def withQuoteMode(self, quoteMode: QuoteMode) -> CSVFormat:
        return self.builder().setQuoteMode(quoteMode).build()

    def withQuote1(self, quoteChar: str) -> CSVFormat:
        return self.builder().setQuote1(quoteChar).build()

    def withQuote0(self, quoteChar: str) -> CSVFormat:
        return self.builder().setQuote0(quoteChar).build()

    def withNullString(self, nullString: str) -> CSVFormat:
        return self.builder().setNullString(nullString).build()

    def withIgnoreSurroundingSpaces1(self, ignoreSurroundingSpaces: bool) -> CSVFormat:
        return self.builder().setIgnoreSurroundingSpaces(ignoreSurroundingSpaces).build()

    def withIgnoreSurroundingSpaces0(self) -> CSVFormat:
        return self.builder().setIgnoreSurroundingSpaces(True).build()

    def withIgnoreHeaderCase1(self, ignoreHeaderCase: bool) -> CSVFormat:
        return self.builder().setIgnoreHeaderCase(ignoreHeaderCase).build()

    def withIgnoreHeaderCase0(self) -> CSVFormat:
        return self.builder().setIgnoreHeaderCase(True).build()

    def withIgnoreEmptyLines1(self, ignoreEmptyLines: bool) -> CSVFormat:
        return self.builder().setIgnoreEmptyLines(ignoreEmptyLines).build()

    def withIgnoreEmptyLines0(self) -> CSVFormat:
        return self.builder().setIgnoreEmptyLines(True).build()

    def withHeaderComments(self, headerComments: typing.List[typing.Any]) -> CSVFormat:
        return self.builder().setHeaderComments0(headerComments).build()

    def withEscape1(self, escape: str) -> CSVFormat:
        return self.builder().setEscape1(escape).build()

    def withEscape0(self, escape: str) -> CSVFormat:
        return self.builder().setEscape0(escape).build()

    def withDelimiter(self, delimiter: str) -> CSVFormat:
        return self.builder().setDelimiter0(delimiter).build()

    def withCommentMarker1(self, commentMarker: str) -> CSVFormat:
        return self.builder().setCommentMarker1(commentMarker).build()

    def withCommentMarker0(self, commentMarker: str) -> CSVFormat:
        return self.builder().setCommentMarker0(commentMarker).build()

    def withAutoFlush(self, autoFlush: bool) -> CSVFormat:
        return self.builder().setAutoFlush(autoFlush).build()

    def withAllowMissingColumnNames1(self, allowMissingColumnNames: bool) -> CSVFormat:
        return self.builder().setAllowMissingColumnNames(allowMissingColumnNames).build()

    def withAllowMissingColumnNames0(self) -> CSVFormat:
        return self.builder().setAllowMissingColumnNames(True).build()

    def withAllowDuplicateHeaderNames1(
        self, allowDuplicateHeaderNames: bool
    ) -> CSVFormat:
        mode = (
            DuplicateHeaderMode.ALLOW_ALL
            if allowDuplicateHeaderNames
            else DuplicateHeaderMode.ALLOW_EMPTY
        )
        return self.builder().setDuplicateHeaderMode(mode).build()

    def withAllowDuplicateHeaderNames0(self) -> CSVFormat:
        return self.builder().setDuplicateHeaderMode(DuplicateHeaderMode.ALLOW_ALL).build()

    def toString(self) -> str:
        sb = f"Delimiter=<{self.__delimiter}>"
        if self.isEscapeCharacterSet():
            sb += f" Escape=<{self.__escapeCharacter}>"
        if self.isQuoteCharacterSet():
            sb += f" QuoteChar=<{self.__quoteCharacter}>"
        if self.__quoteMode is not None:
            sb += f" QuoteMode=<{self.__quoteMode}>"
        if self.isCommentMarkerSet():
            sb += f" CommentStart=<{self.__commentMarker}>"
        if self.isNullStringSet():
            sb += f" NullString=<{self.__nullString}>"
        if self.__recordSeparator is not None:
            sb += f" RecordSeparator=<{self.__recordSeparator}>"
        if self.getIgnoreEmptyLines():
            sb += " EmptyLines:ignored"
        if self.getIgnoreSurroundingSpaces():
            sb += " SurroundingSpaces:ignored"
        if self.getIgnoreHeaderCase():
            sb += " IgnoreHeaderCase:ignored"
        sb += f" SkipHeaderRecord:{_java_bool(self.__skipHeaderRecord)}"
        if self.__headerComments is not None:
            sb += f" HeaderComments:{_java_array_to_string(self.__headerComments)}"
        if self.__headers is not None:
            sb += f" Header:{_java_array_to_string(self.__headers)}"
        return sb

    __str__ = toString

    def print4(self, out: Path, charset: str) -> CSVPrinter:
        writer = open(str(out), mode="w", encoding=charset, newline="")
        return self.print0(writer)

    def print1(self, out: pathlib.Path, charset: str) -> CSVPrinter:
        from src.main.org.apache.commons.csv.CSVPrinter import CSVPrinter
        writer = open(str(out), mode="w", encoding=charset, newline="")
        return CSVPrinter(writer, self)

    def hashCode(self) -> int:
        headers_t = tuple(self.__headers) if self.__headers is not None else None
        comments_t = (
            tuple(self.__headerComments) if self.__headerComments is not None else None
        )
        return hash(
            (
                headers_t,
                comments_t,
                self.__duplicateHeaderMode,
                self.__allowMissingColumnNames,
                self.__autoFlush,
                self.__commentMarker,
                self.__delimiter,
                self.__escapeCharacter,
                self.__ignoreEmptyLines,
                self.__ignoreHeaderCase,
                self.__ignoreSurroundingSpaces,
                self.__nullString,
                self.__quoteCharacter,
                self.__quoteMode,
                self.__quotedNullString,
                self.__recordSeparator,
                self.__skipHeaderRecord,
                self.__trailingDelimiter,
                self.__trim,
            )
        )

    __hash__ = hashCode

    def getDelimiter(self) -> str:
        return self.__delimiter[0]

    def getAllowDuplicateHeaderNames(self) -> bool:
        return self.__duplicateHeaderMode == DuplicateHeaderMode.ALLOW_ALL

    def equals(self, obj: typing.Any) -> bool:
        if self is obj:
            return True
        if obj is None or type(self) is not type(obj):
            return False
        other = obj
        return (
            self.__duplicateHeaderMode == other.__duplicateHeaderMode
            and self.__allowMissingColumnNames == other.__allowMissingColumnNames
            and self.__autoFlush == other.__autoFlush
            and self.__commentMarker == other.__commentMarker
            and self.__delimiter == other.__delimiter
            and self.__escapeCharacter == other.__escapeCharacter
            and self.__headers == other.__headers
            and self.__headerComments == other.__headerComments
            and self.__ignoreEmptyLines == other.__ignoreEmptyLines
            and self.__ignoreHeaderCase == other.__ignoreHeaderCase
            and self.__ignoreSurroundingSpaces == other.__ignoreSurroundingSpaces
            and self.__nullString == other.__nullString
            and self.__quoteCharacter == other.__quoteCharacter
            and self.__quoteMode == other.__quoteMode
            and self.__quotedNullString == other.__quotedNullString
            and self.__recordSeparator == other.__recordSeparator
            and self.__skipHeaderRecord == other.__skipHeaderRecord
            and self.__trailingDelimiter == other.__trailingDelimiter
            and self.__trim == other.__trim
        )

    __eq__ = equals

    @staticmethod
    def clone(values: typing.List[typing.Any]) -> typing.List[typing.Any]:
        return _clone(values)

    def printRecord(
        self,
        appendable: typing.Union[typing.List, io.TextIOBase],
        values: typing.List[typing.Any],
    ) -> None:
        for i, value in enumerate(values):
            self.print2(value, appendable, i == 0)
        self.println(appendable)

    def println(self, appendable: typing.Union[typing.List, io.TextIOBase]) -> None:
        if self.getTrailingDelimiter():
            self.__append1(self.getDelimiterString(), appendable)
        if self.__recordSeparator is not None:
            self.__append1(self.__recordSeparator, appendable)

    def printer(self) -> CSVPrinter:
        from src.main.org.apache.commons.csv.CSVPrinter import CSVPrinter
        return CSVPrinter(sys.stdout, self)

    def print2(
        self,
        value: typing.Any,
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        if value is None:
            if self.__nullString is None:
                charSequence = Constants.EMPTY
            elif self.__quoteMode == QuoteMode.ALL:
                charSequence = self.__quotedNullString
            else:
                charSequence = self.__nullString
        elif isinstance(value, str):
            charSequence = value
        elif hasattr(value, "read") and callable(getattr(value, "read", None)):
            self.__print5(value, out, newRecord)
            return
        else:
            charSequence = str(value)
        charSequence = _trim0(charSequence) if self.getTrim() else charSequence
        self.__print3(value, charSequence, out, newRecord)

    def print0(self, out: typing.Union[typing.List, io.TextIOBase]) -> CSVPrinter:
        from src.main.org.apache.commons.csv.CSVPrinter import CSVPrinter
        return CSVPrinter(out, self)

    def parse(
        self, reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase]
    ) -> CSVParser:
        return CSVParser.CSVParser1(reader, self)

    def isQuoteCharacterSet(self) -> bool:
        return self.__quoteCharacter is not None

    def isNullStringSet(self) -> bool:
        return self.__nullString is not None

    def isEscapeCharacterSet(self) -> bool:
        return self.__escapeCharacter is not None

    def isCommentMarkerSet(self) -> bool:
        return self.__commentMarker is not None

    def getTrim(self) -> bool:
        return self.__trim

    def getTrailingDelimiter(self) -> bool:
        return self.__trailingDelimiter

    def getSkipHeaderRecord(self) -> bool:
        return self.__skipHeaderRecord

    def getRecordSeparator(self) -> str:
        return self.__recordSeparator

    def getQuoteMode(self) -> QuoteMode:
        return self.__quoteMode

    def getQuoteCharacter(self) -> str:
        return self.__quoteCharacter

    def getNullString(self) -> str:
        return self.__nullString

    def getIgnoreSurroundingSpaces(self) -> bool:
        return self.__ignoreSurroundingSpaces

    def getIgnoreHeaderCase(self) -> bool:
        return self.__ignoreHeaderCase

    def getIgnoreEmptyLines(self) -> bool:
        return self.__ignoreEmptyLines

    def getHeaderComments(self) -> typing.List[typing.List[str]]:
        return list(self.__headerComments) if self.__headerComments is not None else None

    def getHeader(self) -> typing.List[typing.List[str]]:
        return list(self.__headers) if self.__headers is not None else None

    def getEscapeCharacter(self) -> str:
        return self.__escapeCharacter

    def getDuplicateHeaderMode(self) -> DuplicateHeaderMode:
        return self.__duplicateHeaderMode

    def getDelimiterString(self) -> str:
        return self.__delimiter

    def getCommentMarker(self) -> str:
        return self.__commentMarker

    def getAutoFlush(self) -> bool:
        return self.__autoFlush

    def getAllowMissingColumnNames(self) -> bool:
        return self.__allowMissingColumnNames

    def format_(self, values: typing.List[typing.Any]) -> str:
        out = io.StringIO()
        self.printRecord(out, values)
        res = out.getvalue()
        length = (
            len(res) - len(self.__recordSeparator)
            if self.__recordSeparator is not None
            else len(res)
        )
        return res[:length]

    def builder(self) -> Builder:
        return Builder.create1(self)

    def __init__(
        self,
        constructorId: int,
        autoFlush: bool,
        skipHeaderRecord: bool,
        delimiter: str,
        nullString: str,
        escape: str,
        ignoreSurroundingSpaces: bool,
        trim: bool,
        builder: Builder,
        commentStart: str,
        ignoreHeaderCase: bool,
        quoteChar: str,
        quoteMode: QuoteMode,
        ignoreEmptyLines: bool,
        duplicateHeaderMode: DuplicateHeaderMode,
        header: typing.List[typing.List[str]],
        allowMissingColumnNames: bool,
        trailingDelimiter: bool,
        headerComments: typing.List[typing.Any],
        recordSeparator: str,
    ) -> None:
        if constructorId == 0:
            self.__delimiter = delimiter
            self.__quoteCharacter = quoteChar
            self.__quoteMode = quoteMode
            self.__commentMarker = commentStart
            self.__escapeCharacter = escape
            self.__ignoreSurroundingSpaces = ignoreSurroundingSpaces
            self.__allowMissingColumnNames = allowMissingColumnNames
            self.__ignoreEmptyLines = ignoreEmptyLines
            self.__recordSeparator = recordSeparator
            self.__nullString = nullString
            self.__headerComments = _to_string_array(headerComments)
            self.__headers = _clone(header)
            self.__skipHeaderRecord = skipHeaderRecord
            self.__ignoreHeaderCase = ignoreHeaderCase
            self.__trailingDelimiter = trailingDelimiter
            self.__trim = trim
            self.__autoFlush = autoFlush
            self.__quotedNullString = _java_concat3(quoteChar, nullString, quoteChar)
            self.__duplicateHeaderMode = duplicateHeaderMode
            self.__validate()
        else:
            self.__delimiter = getattr(builder, "_Builder__delimiter")
            self.__quoteCharacter = getattr(builder, "_Builder__quoteCharacter")
            self.__quoteMode = getattr(builder, "_Builder__quoteMode")
            self.__commentMarker = getattr(builder, "_Builder__commentMarker")
            self.__escapeCharacter = getattr(builder, "_Builder__escapeCharacter")
            self.__ignoreSurroundingSpaces = getattr(
                builder, "_Builder__ignoreSurroundingSpaces"
            )
            self.__allowMissingColumnNames = getattr(
                builder, "_Builder__allowMissingColumnNames"
            )
            self.__ignoreEmptyLines = getattr(builder, "_Builder__ignoreEmptyLines")
            self.__recordSeparator = getattr(builder, "_Builder__recordSeparator")
            self.__nullString = getattr(builder, "_Builder__nullString")
            self.__headerComments = getattr(builder, "_Builder__headerComments")
            self.__headers = getattr(builder, "_Builder__headers")
            self.__skipHeaderRecord = getattr(builder, "_Builder__skipHeaderRecord")
            self.__ignoreHeaderCase = getattr(builder, "_Builder__ignoreHeaderCase")
            self.__trailingDelimiter = getattr(builder, "_Builder__trailingDelimiter")
            self.__trim = getattr(builder, "_Builder__trim")
            self.__autoFlush = getattr(builder, "_Builder__autoFlush")
            self.__quotedNullString = getattr(builder, "_Builder__quotedNullString")
            self.__duplicateHeaderMode = getattr(
                builder, "_Builder__duplicateHeaderMode"
            )
            self.__validate()

    @staticmethod
    def valueOf(format_: str) -> CSVFormat:
        predefined = getattr(Predefined, format_, None)
        if predefined is None or not isinstance(predefined, Predefined):
            raise ValueError(
                f"No enum constant org.apache.commons.csv.CSVFormat.Predefined.{format_}"
            )
        return predefined.getFormat()

    @staticmethod
    def trim0(charSequence: str) -> str:
        return _trim0(charSequence)

    @staticmethod
    def toStringArray(values: typing.List[typing.Any]) -> typing.List[typing.List[str]]:
        return _to_string_array(values)

    @staticmethod
    def newFormat(delimiter: str) -> CSVFormat:
        return CSVFormat(
            0, False, False, str(delimiter), None, None, False, False, None, None,
            False, None, None, False, DuplicateHeaderMode.ALLOW_ALL, None, False,
            False, None, None,
        )

    @staticmethod
    def isBlank(value: str) -> bool:
        return _is_blank(value)

    def __validate(self) -> None:
        if _contains_line_break(self.__delimiter):
            raise ValueError("The delimiter cannot be a line break")

        if self.__quoteCharacter is not None and _contains(
            self.__delimiter, self.__quoteCharacter
        ):
            raise ValueError(
                "The quoteChar character and the delimiter cannot be the same "
                f"('{self.__quoteCharacter}')"
            )

        if self.__escapeCharacter is not None and _contains(
            self.__delimiter, self.__escapeCharacter
        ):
            raise ValueError(
                "The escape character and the delimiter cannot be the same "
                f"('{self.__escapeCharacter}')"
            )

        if self.__commentMarker is not None and _contains(
            self.__delimiter, self.__commentMarker
        ):
            raise ValueError(
                "The comment start character and the delimiter cannot be the same "
                f"('{self.__commentMarker}')"
            )

        if self.__quoteCharacter is not None and self.__quoteCharacter == self.__commentMarker:
            raise ValueError(
                "The comment start character and the quoteChar cannot be the same "
                f"('{self.__commentMarker}')"
            )

        if self.__escapeCharacter is not None and self.__escapeCharacter == self.__commentMarker:
            raise ValueError(
                "The comment start and the escape character cannot be the same "
                f"('{self.__commentMarker}')"
            )

        if self.__escapeCharacter is None and self.__quoteMode == QuoteMode.NONE:
            raise ValueError("No quotes mode set but no escape character is set")

        if self.__headers is not None and self.__duplicateHeaderMode != DuplicateHeaderMode.ALLOW_ALL:
            dup_check_set: typing.Set[str] = set()
            empty_duplicates_allowed = (
                self.__duplicateHeaderMode == DuplicateHeaderMode.ALLOW_EMPTY
            )
            for header in self.__headers:
                blank = CSVFormat.isBlank(header)
                key = "" if blank else header
                contains_header = key in dup_check_set
                dup_check_set.add(key)
                if contains_header and not (blank and empty_duplicates_allowed):
                    raise ValueError(
                        f'The header contains a duplicate name: "{header}" in '
                        f"{_java_array_to_string(self.__headers)}. If this is valid "
                        "then use CSVFormat.Builder.setDuplicateHeaderMode()."
                    )

    def __printWithQuotes1(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        appendable: typing.Union[typing.List, io.TextIOBase],
    ) -> None:
        if self.getQuoteMode() == QuoteMode.NONE:
            self.__printWithEscapes1(reader, appendable)
            return

        pos = 0
        quote = self.__quoteCharacter
        builder: typing.List[str] = []

        self.__append0(quote, appendable)

        c = reader.read(1)
        while c != "":
            builder.append(c)
            if c == quote:
                if pos > 0:
                    self.__append1("".join(builder[0:pos]), appendable)
                    self.__append0(quote, appendable)
                    builder = []
                    pos = -1
                self.__append0(c, appendable)
            pos += 1
            c = reader.read(1)

        if pos > 0:
            self.__append1("".join(builder[0:pos]), appendable)

        self.__append0(quote, appendable)

    def __printWithQuotes0(
        self,
        object_: typing.Any,
        charSeq: str,
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        quote = False
        start = 0
        pos = 0
        length = len(charSeq)

        delim = list(self.getDelimiterString())
        delimLength = len(delim)
        quoteChar = self.__quoteCharacter
        escapeChar = (
            self.__escapeCharacter if self.isEscapeCharacterSet() else quoteChar
        )

        quoteModePolicy = self.getQuoteMode()
        if quoteModePolicy is None:
            quoteModePolicy = QuoteMode.MINIMAL

        if quoteModePolicy in (QuoteMode.ALL, QuoteMode.ALL_NON_NULL):
            quote = True
        elif quoteModePolicy == QuoteMode.NON_NUMERIC:
            quote = not _is_number(object_)
        elif quoteModePolicy == QuoteMode.NONE:
            self.__printWithEscapes0(charSeq, out)
            return
        elif quoteModePolicy == QuoteMode.MINIMAL:
            if length <= 0:
                if newRecord:
                    quote = True
            else:
                c = charSeq[pos]
                if c <= Constants.COMMENT:
                    quote = True
                else:
                    while pos < length:
                        c = charSeq[pos]
                        if (
                            c == Constants.LF
                            or c == Constants.CR
                            or c == quoteChar
                            or c == escapeChar
                            or self.__isDelimiter(c, charSeq, pos, delim, delimLength)
                        ):
                            quote = True
                            break
                        pos += 1

                    if not quote:
                        pos = length - 1
                        c = charSeq[pos]
                        if CSVFormat.__isTrimChar0(c):
                            quote = True

            if not quote:
                self.__append1(charSeq[start:length], out)
                return
        else:
            raise RuntimeError(f"Unexpected Quote value: {quoteModePolicy}")

        if not quote:
            self.__append1(charSeq[start:length], out)
            return

        self.__append0(quoteChar, out)

        while pos < length:
            c = charSeq[pos]
            if c == quoteChar or c == escapeChar:
                self.__append1(charSeq[start:pos], out)
                self.__append0(escapeChar, out)
                start = pos
            pos += 1

        self.__append1(charSeq[start:pos], out)
        self.__append0(quoteChar, out)

    def __printWithEscapes1(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        appendable: typing.Union[typing.List, io.TextIOBase],
    ) -> None:
        start = 0
        pos = 0

        bufferedReader = ExtendedBufferedReader(reader)
        delim = list(self.getDelimiterString())
        delimLength = len(delim)
        escape = self.__escapeCharacter
        builder: typing.List[str] = []

        c = bufferedReader.read0()
        while c != Constants.END_OF_STREAM:
            builder.append(chr(c))
            lookahead = bufferedReader.lookAhead2(delimLength - 1)
            combined = "".join(builder) + "".join(lookahead)
            isDelimiterStart = self.__isDelimiter(
                chr(c), combined, pos, delim, delimLength
            )
            if c == ord(Constants.CR) or c == ord(Constants.LF) or chr(c) == escape or isDelimiterStart:
                if pos > start:
                    self.__append1("".join(builder[start:pos]), appendable)
                    builder = []
                    pos = -1
                if c == ord(Constants.LF):
                    outChar = "n"
                elif c == ord(Constants.CR):
                    outChar = "r"
                else:
                    outChar = chr(c)

                self.__append0(escape, appendable)
                self.__append0(outChar, appendable)

                if isDelimiterStart:
                    for _ in range(1, delimLength):
                        c = bufferedReader.read0()
                        self.__append0(escape, appendable)
                        self.__append0(chr(c), appendable)

                start = pos + 1
            pos += 1
            c = bufferedReader.read0()

        if pos > start:
            self.__append1("".join(builder[start:pos]), appendable)

    def __printWithEscapes0(
        self, charSeq: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        start = 0
        pos = 0
        end = len(charSeq)

        delim = list(self.getDelimiterString())
        delimLength = len(delim)
        escape = self.__escapeCharacter

        while pos < end:
            c = charSeq[pos]
            isDelimiterStart = self.__isDelimiter(c, charSeq, pos, delim, delimLength)
            if c == Constants.CR or c == Constants.LF or c == escape or isDelimiterStart:
                if pos > start:
                    self.__append1(charSeq[start:pos], appendable)
                if c == Constants.LF:
                    c = "n"
                elif c == Constants.CR:
                    c = "r"

                self.__append0(escape, appendable)
                self.__append0(c, appendable)

                if isDelimiterStart:
                    for _ in range(1, delimLength):
                        pos += 1
                        c = charSeq[pos]
                        self.__append0(escape, appendable)
                        self.__append0(c, appendable)

                start = pos + 1
            pos += 1

        if pos > start:
            self.__append1(charSeq[start:pos], appendable)

    def __print5(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        if not newRecord:
            self.__append1(self.getDelimiterString(), out)
        if self.isQuoteCharacterSet():
            self.__printWithQuotes1(reader, out)
        elif self.isEscapeCharacterSet():
            self.__printWithEscapes1(reader, out)
        elif hasattr(out, "write"):
            IOUtils.copyLarge0(reader, out)
        else:
            IOUtils.copy0(reader, out)

    def __print3(
        self,
        object_: typing.Any,
        value: str,
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        offset = 0
        length = len(value)
        if not newRecord:
            self.__append1(self.getDelimiterString(), out)
        if object_ is None:
            self.__append1(value, out)
        elif self.isQuoteCharacterSet():
            self.__printWithQuotes0(object_, value, out, newRecord)
        elif self.isEscapeCharacterSet():
            self.__printWithEscapes0(value, out)
        else:
            self.__append1(value[offset:offset + length], out)

    def __isDelimiter(
        self,
        ch: str,
        charSeq: str,
        startIndex: int,
        delimiter: typing.List[str],
        delimiterLength: int,
    ) -> bool:
        if ch != delimiter[0]:
            return False
        length = len(charSeq)
        if startIndex + delimiterLength > length:
            return False
        for i in range(1, delimiterLength):
            if charSeq[startIndex + i] != delimiter[i]:
                return False
        return True

    def __append1(
        self, csq: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        if isinstance(appendable, list):
            appendable.append(csq)
        else:
            appendable.write(csq)

    def __append0(
        self, c: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        if isinstance(appendable, list):
            appendable.append(c)
        else:
            appendable.write(c)

    @staticmethod
    def __isTrimChar1(charSequence: str, pos: int) -> bool:
        return _is_trim_char1(charSequence, pos)

    @staticmethod
    def __isTrimChar0(ch: str) -> bool:
        return _is_trim_char0(ch)

    @staticmethod
    def __isLineBreak1(c: str) -> bool:
        return _is_line_break1(c)

    @staticmethod
    def __isLineBreak0(c: str) -> bool:
        return _is_line_break0(c)

    @staticmethod
    def __containsLineBreak(source: str) -> bool:
        return _contains_line_break(source)

    @staticmethod
    def __contains(source: str, searchCh: str) -> bool:
        return _contains(source, searchCh)

    def trim1(self, value: str) -> str:
        return _trim0(value) if self.getTrim() else value

    def copy(self) -> CSVFormat:
        return self.builder().build()

    # Class Methods End



# Predefined CSVFormat constants.
#
# These must be assigned after the CSVFormat class body (the Builder-based
# presets call CSVFormat.DEFAULT.builder()...build(), which requires a fully
# defined CSVFormat class and an already-assigned DEFAULT constant) and
# before the Predefined instances below (each of which wraps one of these
# constants).
CSVFormat.DEFAULT = CSVFormat(
    0, False, False, Constants.COMMA, None, None, False, False, None, None,
    False, Constants.DOUBLE_QUOTE_CHAR, None, True, DuplicateHeaderMode.ALLOW_ALL,
    None, False, False, None, Constants.CRLF,
)

CSVFormat.EXCEL = (
    CSVFormat.DEFAULT.builder()
    .setIgnoreEmptyLines(False)
    .setAllowMissingColumnNames(True)
    .build()
)

CSVFormat.INFORMIX_UNLOAD = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(Constants.PIPE)
    .setEscape0(Constants.BACKSLASH)
    .setQuote1(Constants.DOUBLE_QUOTE_CHAR)
    .setRecordSeparator0(Constants.LF)
    .build()
)

CSVFormat.INFORMIX_UNLOAD_CSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(Constants.COMMA)
    .setQuote1(Constants.DOUBLE_QUOTE_CHAR)
    .setRecordSeparator0(Constants.LF)
    .build()
)

CSVFormat.MONGODB_CSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(Constants.COMMA)
    .setEscape1(Constants.DOUBLE_QUOTE_CHAR)
    .setQuote1(Constants.DOUBLE_QUOTE_CHAR)
    .setQuoteMode(QuoteMode.MINIMAL)
    .setSkipHeaderRecord(False)
    .build()
)

CSVFormat.MONGODB_TSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(Constants.TAB)
    .setEscape1(Constants.DOUBLE_QUOTE_CHAR)
    .setQuote1(Constants.DOUBLE_QUOTE_CHAR)
    .setQuoteMode(QuoteMode.MINIMAL)
    .setSkipHeaderRecord(False)
    .build()
)

CSVFormat.MYSQL = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(Constants.TAB)
    .setEscape0(Constants.BACKSLASH)
    .setIgnoreEmptyLines(False)
    .setQuote1(None)
    .setRecordSeparator0(Constants.LF)
    .setNullString(Constants.SQL_NULL_STRING)
    .setQuoteMode(QuoteMode.ALL_NON_NULL)
    .build()
)

CSVFormat.ORACLE = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(Constants.COMMA)
    .setEscape0(Constants.BACKSLASH)
    .setIgnoreEmptyLines(False)
    .setQuote1(Constants.DOUBLE_QUOTE_CHAR)
    .setNullString(Constants.SQL_NULL_STRING)
    .setTrim(True)
    .setRecordSeparator1(os.linesep)
    .setQuoteMode(QuoteMode.MINIMAL)
    .build()
)

CSVFormat.POSTGRESQL_CSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(Constants.COMMA)
    .setEscape1(None)
    .setIgnoreEmptyLines(False)
    .setQuote1(Constants.DOUBLE_QUOTE_CHAR)
    .setRecordSeparator0(Constants.LF)
    .setNullString(Constants.EMPTY)
    .setQuoteMode(QuoteMode.ALL_NON_NULL)
    .build()
)

CSVFormat.POSTGRESQL_TEXT = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(Constants.TAB)
    .setEscape0(Constants.BACKSLASH)
    .setIgnoreEmptyLines(False)
    .setQuote1(None)
    .setRecordSeparator0(Constants.LF)
    .setNullString(Constants.SQL_NULL_STRING)
    .setQuoteMode(QuoteMode.ALL_NON_NULL)
    .build()
)

CSVFormat.RFC4180 = CSVFormat.DEFAULT.builder().setIgnoreEmptyLines(False).build()

CSVFormat.TDF = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(Constants.TAB)
    .setIgnoreSurroundingSpaces(True)
    .build()
)


# Predefined instances, wired up strictly after the CSVFormat presets above.
Predefined.Default = Predefined(CSVFormat.DEFAULT)
Predefined.Excel = Predefined(CSVFormat.EXCEL)
Predefined.InformixUnload = Predefined(CSVFormat.INFORMIX_UNLOAD)
Predefined.InformixUnloadCsv = Predefined(CSVFormat.INFORMIX_UNLOAD_CSV)
Predefined.MongoDBCsv = Predefined(CSVFormat.MONGODB_CSV)
Predefined.MongoDBTsv = Predefined(CSVFormat.MONGODB_TSV)
Predefined.MySQL = Predefined(CSVFormat.MYSQL)
Predefined.Oracle = Predefined(CSVFormat.ORACLE)
Predefined.PostgreSQLCsv = Predefined(CSVFormat.POSTGRESQL_CSV)
Predefined.PostgreSQLText = Predefined(CSVFormat.POSTGRESQL_TEXT)
Predefined.RFC4180 = Predefined(CSVFormat.RFC4180)
Predefined.TDF = Predefined(CSVFormat.TDF)
