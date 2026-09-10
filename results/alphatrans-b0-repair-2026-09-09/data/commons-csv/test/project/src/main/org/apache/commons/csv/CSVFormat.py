from __future__ import annotations

# Imports Begin
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
import pathlib

# Imports End


def _java_str(value: Any) -> str:
    """Mimic Java's String concatenation null handling."""
    return "null" if value is None else str(value)


def _java_bool(value: Any) -> str:
    """Mimic Java's Boolean.toString()."""
    return "true" if value else "false"


def _arrays_to_string(values: Optional[typing.List[typing.Any]]) -> str:
    """Mimic Java's Arrays.toString()."""
    if values is None:
        return "null"
    return "[" + ", ".join(_java_str(v) for v in values) + "]"


def _appendable_append(appendable: Any, s: str) -> None:
    """Write/append a string chunk to either a file-like object or a list-like buffer."""
    if hasattr(appendable, "write"):
        appendable.write(s)
    else:
        appendable.append(s)


def _to_char(value: Any) -> Any:
    if isinstance(value, int):
        return chr(value)
    return value


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
    def setAllowDuplicateHeaderNames(self, allowDuplicateHeaderNames: bool) -> "Builder":
        self.setDuplicateHeaderMode(
            DuplicateHeaderMode.ALLOW_ALL
            if allowDuplicateHeaderNames
            else DuplicateHeaderMode.ALLOW_EMPTY
        )
        return self

    def setTrim(self, trim: bool) -> "Builder":
        self.__trim = trim
        return self

    def setTrailingDelimiter(self, trailingDelimiter: bool) -> "Builder":
        self.__trailingDelimiter = trailingDelimiter
        return self

    def setSkipHeaderRecord(self, skipHeaderRecord: bool) -> "Builder":
        self.__skipHeaderRecord = skipHeaderRecord
        return self

    def setRecordSeparator1(self, recordSeparator: str) -> "Builder":
        self.__recordSeparator = recordSeparator
        return self

    def setRecordSeparator0(self, recordSeparator: str) -> "Builder":
        self.__recordSeparator = str(recordSeparator)
        return self

    def setQuoteMode(self, quoteMode: QuoteMode) -> "Builder":
        self.__quoteMode = quoteMode
        return self

    def setQuote1(self, quoteCharacter: Optional[str]) -> "Builder":
        if CSVFormat._CSVFormat__isLineBreak1(quoteCharacter):
            raise ValueError("The quoteChar cannot be a line break")
        self.__quoteCharacter = quoteCharacter
        return self

    def setQuote0(self, quoteCharacter: str) -> "Builder":
        self.setQuote1(quoteCharacter)
        return self

    def setNullString(self, nullString: str) -> "Builder":
        self.__nullString = nullString
        self.__quotedNullString = (
            _java_str(self.__quoteCharacter) + _java_str(nullString) + _java_str(self.__quoteCharacter)
        )
        return self

    def setIgnoreSurroundingSpaces(self, ignoreSurroundingSpaces: bool) -> "Builder":
        self.__ignoreSurroundingSpaces = ignoreSurroundingSpaces
        return self

    def setIgnoreHeaderCase(self, ignoreHeaderCase: bool) -> "Builder":
        self.__ignoreHeaderCase = ignoreHeaderCase
        return self

    def setIgnoreEmptyLines(self, ignoreEmptyLines: bool) -> "Builder":
        self.__ignoreEmptyLines = ignoreEmptyLines
        return self

    def setHeaderComments1(
        self, headerComments: typing.List[typing.List[str]]
    ) -> "Builder":
        self.__headerComments = CSVFormat.clone(headerComments)
        return self

    def setHeaderComments0(self, headerComments: typing.List[typing.Any]) -> "Builder":
        self.__headerComments = CSVFormat.clone(CSVFormat.toStringArray(headerComments))
        return self

    def setEscape1(self, escapeCharacter: Optional[str]) -> "Builder":
        if CSVFormat._CSVFormat__isLineBreak1(escapeCharacter):
            raise ValueError("The escape character cannot be a line break")
        self.__escapeCharacter = escapeCharacter
        return self

    def setEscape0(self, escapeCharacter: str) -> "Builder":
        self.setEscape1(escapeCharacter)
        return self

    def setDuplicateHeaderMode(
        self, duplicateHeaderMode: DuplicateHeaderMode
    ) -> "Builder":
        if duplicateHeaderMode is None:
            raise ValueError("duplicateHeaderMode")
        self.__duplicateHeaderMode = duplicateHeaderMode
        return self

    def setDelimiter1(self, delimiter: str) -> "Builder":
        if CSVFormat._CSVFormat__containsLineBreak(delimiter):
            raise ValueError("The delimiter cannot be a line break")
        if delimiter == "":
            raise ValueError("The delimiter cannot be empty")
        self.__delimiter = delimiter
        return self

    def setDelimiter0(self, delimiter: str) -> "Builder":
        return self.setDelimiter1(str(delimiter))

    def setCommentMarker1(self, commentMarker: Optional[str]) -> "Builder":
        if CSVFormat._CSVFormat__isLineBreak1(commentMarker):
            raise ValueError("The comment start marker character cannot be a line break")
        self.__commentMarker = commentMarker
        return self

    def setCommentMarker0(self, commentMarker: str) -> "Builder":
        self.setCommentMarker1(commentMarker)
        return self

    def setAutoFlush(self, autoFlush: bool) -> "Builder":
        self.__autoFlush = autoFlush
        return self

    def setAllowMissingColumnNames(self, allowMissingColumnNames: bool) -> "Builder":
        self.__allowMissingColumnNames = allowMissingColumnNames
        return self

    def build(self) -> "CSVFormat":
        return CSVFormat(
            1, False, False, None, None, None, False, False, self, None, False, None,
            None, False, None, None, False, False, None, None,
        )

    @staticmethod
    def create1(csvFormat: "CSVFormat") -> "Builder":
        return Builder(csvFormat)

    @staticmethod
    def create0() -> "Builder":
        return Builder(CSVFormat.DEFAULT)

    def __init__(self, csvFormat: "CSVFormat") -> None:
        self.__delimiter = csvFormat._CSVFormat__delimiter
        self.__quoteCharacter = csvFormat._CSVFormat__quoteCharacter
        self.__quoteMode = csvFormat._CSVFormat__quoteMode
        self.__commentMarker = csvFormat._CSVFormat__commentMarker
        self.__escapeCharacter = csvFormat._CSVFormat__escapeCharacter
        self.__ignoreSurroundingSpaces = csvFormat._CSVFormat__ignoreSurroundingSpaces
        self.__allowMissingColumnNames = csvFormat._CSVFormat__allowMissingColumnNames
        self.__ignoreEmptyLines = csvFormat._CSVFormat__ignoreEmptyLines
        self.__recordSeparator = csvFormat._CSVFormat__recordSeparator
        self.__nullString = csvFormat._CSVFormat__nullString
        self.__headerComments = csvFormat._CSVFormat__headerComments
        self.__headers = csvFormat._CSVFormat__headers
        self.__skipHeaderRecord = csvFormat._CSVFormat__skipHeaderRecord
        self.__ignoreHeaderCase = csvFormat._CSVFormat__ignoreHeaderCase
        self.__trailingDelimiter = csvFormat._CSVFormat__trailingDelimiter
        self.__trim = csvFormat._CSVFormat__trim
        self.__autoFlush = csvFormat._CSVFormat__autoFlush
        self.__quotedNullString = csvFormat._CSVFormat__quotedNullString
        self.__duplicateHeaderMode = csvFormat._CSVFormat__duplicateHeaderMode

    # Class Methods End


class Predefined:

    # Class Fields Begin
    Default: "Predefined" = None
    Excel: "Predefined" = None
    InformixUnload: "Predefined" = None
    InformixUnloadCsv: "Predefined" = None
    MongoDBCsv: "Predefined" = None
    MongoDBTsv: "Predefined" = None
    MySQL: "Predefined" = None
    Oracle: "Predefined" = None
    PostgreSQLCsv: "Predefined" = None
    PostgreSQLText: "Predefined" = None
    RFC4180: "Predefined" = None
    TDF: "Predefined" = None
    __format: "CSVFormat" = None
    # Class Fields End

    # Class Methods Begin
    def getFormat(self) -> "CSVFormat":
        return self.__format

    def __init__(self, format_: "CSVFormat") -> None:
        self.__format = format_

    # Class Methods End


class CSVFormat:

    # Class Fields Begin
    ORACLE: "CSVFormat" = None
    POSTGRESQL_CSV: "CSVFormat" = None
    POSTGRESQL_TEXT: "CSVFormat" = None
    RFC4180: "CSVFormat" = None
    __serialVersionUID: int = 2
    TDF: "CSVFormat" = None
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
    DEFAULT: "CSVFormat" = None
    EXCEL: "CSVFormat" = None
    INFORMIX_UNLOAD: "CSVFormat" = None
    INFORMIX_UNLOAD_CSV: "CSVFormat" = None
    MONGODB_CSV: "CSVFormat" = None
    MONGODB_TSV: "CSVFormat" = None
    MYSQL: "CSVFormat" = None
    # Class Fields End

    # Class Methods Begin
    def withTrim1(self, trim: bool) -> "CSVFormat":
        return self.builder().setTrim(trim).build()

    def withTrim0(self) -> "CSVFormat":
        return self.builder().setTrim(True).build()

    def withTrailingDelimiter1(self, trailingDelimiter: bool) -> "CSVFormat":
        return self.builder().setTrailingDelimiter(trailingDelimiter).build()

    def withTrailingDelimiter0(self) -> "CSVFormat":
        return self.builder().setTrailingDelimiter(True).build()

    def withSystemRecordSeparator(self) -> "CSVFormat":
        return self.builder().setRecordSeparator1(os.linesep).build()

    def withSkipHeaderRecord1(self, skipHeaderRecord: bool) -> "CSVFormat":
        return self.builder().setSkipHeaderRecord(skipHeaderRecord).build()

    def withSkipHeaderRecord0(self) -> "CSVFormat":
        return self.builder().setSkipHeaderRecord(True).build()

    def withRecordSeparator1(self, recordSeparator: str) -> "CSVFormat":
        return self.builder().setRecordSeparator1(recordSeparator).build()

    def withRecordSeparator0(self, recordSeparator: str) -> "CSVFormat":
        return self.builder().setRecordSeparator0(recordSeparator).build()

    def withQuoteMode(self, quoteMode: QuoteMode) -> "CSVFormat":
        return self.builder().setQuoteMode(quoteMode).build()

    def withQuote1(self, quoteChar: Optional[str]) -> "CSVFormat":
        return self.builder().setQuote1(quoteChar).build()

    def withQuote0(self, quoteChar: str) -> "CSVFormat":
        return self.builder().setQuote0(quoteChar).build()

    def withNullString(self, nullString: str) -> "CSVFormat":
        return self.builder().setNullString(nullString).build()

    def withIgnoreSurroundingSpaces1(self, ignoreSurroundingSpaces: bool) -> "CSVFormat":
        return self.builder().setIgnoreSurroundingSpaces(ignoreSurroundingSpaces).build()

    def withIgnoreSurroundingSpaces0(self) -> "CSVFormat":
        return self.builder().setIgnoreSurroundingSpaces(True).build()

    def withIgnoreHeaderCase1(self, ignoreHeaderCase: bool) -> "CSVFormat":
        return self.builder().setIgnoreHeaderCase(ignoreHeaderCase).build()

    def withIgnoreHeaderCase0(self) -> "CSVFormat":
        return self.builder().setIgnoreHeaderCase(True).build()

    def withIgnoreEmptyLines1(self, ignoreEmptyLines: bool) -> "CSVFormat":
        return self.builder().setIgnoreEmptyLines(ignoreEmptyLines).build()

    def withIgnoreEmptyLines0(self) -> "CSVFormat":
        return self.builder().setIgnoreEmptyLines(True).build()

    def withHeaderComments(self, headerComments: typing.List[typing.Any]) -> "CSVFormat":
        return self.builder().setHeaderComments0(headerComments).build()

    def withEscape1(self, escape: Optional[str]) -> "CSVFormat":
        return self.builder().setEscape1(escape).build()

    def withEscape0(self, escape: str) -> "CSVFormat":
        return self.builder().setEscape0(escape).build()

    def withDelimiter(self, delimiter: str) -> "CSVFormat":
        return self.builder().setDelimiter0(delimiter).build()

    def withCommentMarker1(self, commentMarker: Optional[str]) -> "CSVFormat":
        return self.builder().setCommentMarker1(commentMarker).build()

    def withCommentMarker0(self, commentMarker: str) -> "CSVFormat":
        return self.builder().setCommentMarker0(commentMarker).build()

    def withAutoFlush(self, autoFlush: bool) -> "CSVFormat":
        return self.builder().setAutoFlush(autoFlush).build()

    def withAllowMissingColumnNames1(self, allowMissingColumnNames: bool) -> "CSVFormat":
        return self.builder().setAllowMissingColumnNames(allowMissingColumnNames).build()

    def withAllowMissingColumnNames0(self) -> "CSVFormat":
        return self.builder().setAllowMissingColumnNames(True).build()

    def withAllowDuplicateHeaderNames1(
        self, allowDuplicateHeaderNames: bool
    ) -> "CSVFormat":
        mode = (
            DuplicateHeaderMode.ALLOW_ALL
            if allowDuplicateHeaderNames
            else DuplicateHeaderMode.ALLOW_EMPTY
        )
        return self.builder().setDuplicateHeaderMode(mode).build()

    def withAllowDuplicateHeaderNames0(self) -> "CSVFormat":
        return self.builder().setDuplicateHeaderMode(DuplicateHeaderMode.ALLOW_ALL).build()

    def toString(self) -> str:
        sb: typing.List[str] = []
        sb.append(f"Delimiter=<{self.__delimiter}>")
        if self.isEscapeCharacterSet():
            sb.append(" ")
            sb.append(f"Escape=<{self.__escapeCharacter}>")
        if self.isQuoteCharacterSet():
            sb.append(" ")
            sb.append(f"QuoteChar=<{self.__quoteCharacter}>")
        if self.__quoteMode is not None:
            sb.append(" ")
            sb.append(f"QuoteMode=<{self.__quoteMode}>")
        if self.isCommentMarkerSet():
            sb.append(" ")
            sb.append(f"CommentStart=<{self.__commentMarker}>")
        if self.isNullStringSet():
            sb.append(" ")
            sb.append(f"NullString=<{self.__nullString}>")
        if self.__recordSeparator is not None:
            sb.append(" ")
            sb.append(f"RecordSeparator=<{self.__recordSeparator}>")
        if self.getIgnoreEmptyLines():
            sb.append(" EmptyLines:ignored")
        if self.getIgnoreSurroundingSpaces():
            sb.append(" SurroundingSpaces:ignored")
        if self.getIgnoreHeaderCase():
            sb.append(" IgnoreHeaderCase:ignored")
        sb.append(f" SkipHeaderRecord:{_java_bool(self.__skipHeaderRecord)}")
        if self.__headerComments is not None:
            sb.append(" ")
            sb.append(f"HeaderComments:{_arrays_to_string(self.__headerComments)}")
        if self.__headers is not None:
            sb.append(" ")
            sb.append(f"Header:{_arrays_to_string(self.__headers)}")
        return "".join(sb)

    def __str__(self) -> str:
        return self.toString()

    def print4(self, out: pathlib.Path, charset: str) -> CSVPrinter:
        return self.print0(open(out, mode="w", encoding=charset, newline=""))

    def print1(self, out: pathlib.Path, charset: str) -> CSVPrinter:
        return CSVPrinter(open(out, mode="w", encoding=charset, newline=""), self)

    def hashCode(self) -> int:
        prime = 31
        result = 1
        result = prime * result + (hash(tuple(self.__headers)) if self.__headers is not None else 0)
        result = prime * result + (
            hash(tuple(self.__headerComments)) if self.__headerComments is not None else 0
        )
        values = (
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
        return prime * result + hash(values)

    def __hash__(self) -> int:
        return self.hashCode()

    def getDelimiter(self) -> str:
        return self.__delimiter[0]

    def getAllowDuplicateHeaderNames(self) -> bool:
        return self.__duplicateHeaderMode == DuplicateHeaderMode.ALLOW_ALL

    def equals(self, obj: typing.Any) -> bool:
        if self is obj:
            return True
        if obj is None or type(obj) is not type(self):
            return False
        other = obj
        return (
            self.__duplicateHeaderMode == other._CSVFormat__duplicateHeaderMode
            and self.__allowMissingColumnNames == other._CSVFormat__allowMissingColumnNames
            and self.__autoFlush == other._CSVFormat__autoFlush
            and self.__commentMarker == other._CSVFormat__commentMarker
            and self.__delimiter == other._CSVFormat__delimiter
            and self.__escapeCharacter == other._CSVFormat__escapeCharacter
            and self.__headers == other._CSVFormat__headers
            and self.__headerComments == other._CSVFormat__headerComments
            and self.__ignoreEmptyLines == other._CSVFormat__ignoreEmptyLines
            and self.__ignoreHeaderCase == other._CSVFormat__ignoreHeaderCase
            and self.__ignoreSurroundingSpaces == other._CSVFormat__ignoreSurroundingSpaces
            and self.__nullString == other._CSVFormat__nullString
            and self.__quoteCharacter == other._CSVFormat__quoteCharacter
            and self.__quoteMode == other._CSVFormat__quoteMode
            and self.__quotedNullString == other._CSVFormat__quotedNullString
            and self.__recordSeparator == other._CSVFormat__recordSeparator
            and self.__skipHeaderRecord == other._CSVFormat__skipHeaderRecord
            and self.__trailingDelimiter == other._CSVFormat__trailingDelimiter
            and self.__trim == other._CSVFormat__trim
        )

    def __eq__(self, other: typing.Any) -> bool:
        return self.equals(other)

    @staticmethod
    def clone(values: typing.List[typing.Any]) -> typing.List[typing.Any]:
        return None if values is None else list(values)

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
        return CSVPrinter(sys.stdout, self)

    def print2(
        self,
        value: typing.Any,
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        if value is None:
            if self.__nullString is None:
                char_sequence = EMPTY
            elif QuoteMode.ALL == self.__quoteMode:
                char_sequence = self.__quotedNullString
            else:
                char_sequence = self.__nullString
        elif isinstance(value, str):
            char_sequence = value
        elif hasattr(value, "read") and not isinstance(value, (bytes, bytearray)):
            self.__print5(value, out, newRecord)
            return
        else:
            char_sequence = str(value)
        char_sequence = CSVFormat.trim0(char_sequence) if self.getTrim() else char_sequence
        self.__print3(value, char_sequence, out, newRecord)

    def print0(self, out: typing.Union[typing.List, io.TextIOBase]) -> CSVPrinter:
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
        csv_printer = CSVPrinter(out, self)
        try:
            csv_printer.printRecord1(list(values))
            res = out.getvalue()
            if self.__recordSeparator is not None:
                length = len(res) - len(self.__recordSeparator)
            else:
                length = len(res)
            return res[:length]
        except IOError as e:
            raise RuntimeError(e)
        finally:
            try:
                csv_printer.close()
            except Exception:
                pass

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
            self.__headerComments = CSVFormat.toStringArray(headerComments)
            self.__headers = CSVFormat.clone(header)
            self.__skipHeaderRecord = skipHeaderRecord
            self.__ignoreHeaderCase = ignoreHeaderCase
            self.__trailingDelimiter = trailingDelimiter
            self.__trim = trim
            self.__autoFlush = autoFlush
            self.__quotedNullString = (
                _java_str(self.__quoteCharacter) + _java_str(nullString) + _java_str(self.__quoteCharacter)
            )
            self.__duplicateHeaderMode = duplicateHeaderMode
            self.__validate()
        else:
            self.__delimiter = builder._Builder__delimiter
            self.__quoteCharacter = builder._Builder__quoteCharacter
            self.__quoteMode = builder._Builder__quoteMode
            self.__commentMarker = builder._Builder__commentMarker
            self.__escapeCharacter = builder._Builder__escapeCharacter
            self.__ignoreSurroundingSpaces = builder._Builder__ignoreSurroundingSpaces
            self.__allowMissingColumnNames = builder._Builder__allowMissingColumnNames
            self.__ignoreEmptyLines = builder._Builder__ignoreEmptyLines
            self.__recordSeparator = builder._Builder__recordSeparator
            self.__nullString = builder._Builder__nullString
            self.__headerComments = builder._Builder__headerComments
            self.__headers = builder._Builder__headers
            self.__skipHeaderRecord = builder._Builder__skipHeaderRecord
            self.__ignoreHeaderCase = builder._Builder__ignoreHeaderCase
            self.__trailingDelimiter = builder._Builder__trailingDelimiter
            self.__trim = builder._Builder__trim
            self.__autoFlush = builder._Builder__autoFlush
            self.__quotedNullString = builder._Builder__quotedNullString
            self.__duplicateHeaderMode = builder._Builder__duplicateHeaderMode
            self.__validate()

    @staticmethod
    def valueOf(format_: str) -> "CSVFormat":
        try:
            predefined = getattr(Predefined, format_)
        except AttributeError:
            raise ValueError(f"No enum constant {format_}")
        if predefined is None:
            raise ValueError(f"No enum constant {format_}")
        return predefined.getFormat()

    @staticmethod
    def trim0(charSequence: str) -> str:
        count = len(charSequence)
        length = count
        pos = 0
        while pos < length and CSVFormat.__isTrimChar1(charSequence, pos):
            pos += 1
        while pos < length and CSVFormat.__isTrimChar1(charSequence, length - 1):
            length -= 1
        return charSequence[pos:length] if (pos > 0 or length < count) else charSequence

    @staticmethod
    def toStringArray(values: typing.List[typing.Any]) -> typing.List[typing.List[str]]:
        if values is None:
            return None
        return [None if v is None else str(v) for v in values]

    @staticmethod
    def newFormat(delimiter: str) -> "CSVFormat":
        return CSVFormat(
            0, False, False, str(delimiter), None, None, False, False, None, None,
            False, None, None, False, DuplicateHeaderMode.ALLOW_ALL, None, False,
            False, None, None,
        )

    @staticmethod
    def isBlank(value: str) -> bool:
        return value is None or value.strip() == ""

    def __validate(self) -> None:
        if CSVFormat.__containsLineBreak(self.__delimiter):
            raise ValueError("The delimiter cannot be a line break")

        if self.__quoteCharacter is not None and CSVFormat.__contains(
            self.__delimiter, self.__quoteCharacter
        ):
            raise ValueError(
                f"The quoteChar character and the delimiter cannot be the same ('{self.__quoteCharacter}')"
            )

        if self.__escapeCharacter is not None and CSVFormat.__contains(
            self.__delimiter, self.__escapeCharacter
        ):
            raise ValueError(
                f"The escape character and the delimiter cannot be the same ('{self.__escapeCharacter}')"
            )

        if self.__commentMarker is not None and CSVFormat.__contains(
            self.__delimiter, self.__commentMarker
        ):
            raise ValueError(
                f"The comment start character and the delimiter cannot be the same ('{self.__commentMarker}')"
            )

        if self.__quoteCharacter is not None and self.__quoteCharacter == self.__commentMarker:
            raise ValueError(
                f"The comment start character and the quoteChar cannot be the same ('{self.__commentMarker}')"
            )

        if self.__escapeCharacter is not None and self.__escapeCharacter == self.__commentMarker:
            raise ValueError(
                f"The comment start and the escape character cannot be the same ('{self.__commentMarker}')"
            )

        if self.__escapeCharacter is None and self.__quoteMode == QuoteMode.NONE:
            raise ValueError("No quotes mode set but no escape character is set")

        if self.__headers is not None and self.__duplicateHeaderMode != DuplicateHeaderMode.ALLOW_ALL:
            dup_check_set: typing.Set[str] = set()
            empty_duplicates_allowed = self.__duplicateHeaderMode == DuplicateHeaderMode.ALLOW_EMPTY
            for header in self.__headers:
                blank = CSVFormat.isBlank(header)
                key = "" if blank else header
                contains_header = key in dup_check_set
                dup_check_set.add(key)
                if contains_header and not (blank and empty_duplicates_allowed):
                    raise ValueError(
                        f'The header contains a duplicate name: "{header}" in {list(self.__headers)}. '
                        "If this is valid then use CSVFormat.Builder.setDuplicateHeaderMode()."
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
        quote = self.getQuoteCharacter()
        builder: typing.List[str] = []

        self.__append0(quote, appendable)

        c = reader.read(1)
        while c:
            builder.append(c)
            if c == quote:
                if pos > 0:
                    self.__append1("".join(builder[:pos]), appendable)
                    self.__append0(quote, appendable)
                    builder = []
                    pos = -1
                self.__append0(c, appendable)
            pos += 1
            c = reader.read(1)

        if pos > 0:
            self.__append1("".join(builder[:pos]), appendable)

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
        delim_length = len(delim)
        quote_char = self.getQuoteCharacter()
        escape_char = self.getEscapeCharacter() if self.isEscapeCharacterSet() else quote_char

        quote_mode_policy = self.getQuoteMode()
        if quote_mode_policy is None:
            quote_mode_policy = QuoteMode.MINIMAL

        if quote_mode_policy in (QuoteMode.ALL, QuoteMode.ALL_NON_NULL):
            quote = True
        elif quote_mode_policy == QuoteMode.NON_NUMERIC:
            quote = isinstance(object_, bool) or not isinstance(object_, (int, float))
        elif quote_mode_policy == QuoteMode.NONE:
            self.__printWithEscapes0(charSeq, out)
            return
        elif quote_mode_policy == QuoteMode.MINIMAL:
            if length <= 0:
                if newRecord:
                    quote = True
            else:
                c = charSeq[pos]
                if c <= COMMENT:
                    quote = True
                else:
                    while pos < length:
                        c = charSeq[pos]
                        if (
                            c == LF
                            or c == CR
                            or c == quote_char
                            or c == escape_char
                            or self.__isDelimiter(c, charSeq, pos, delim, delim_length)
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
                _appendable_append(out, charSeq[start:length])
                return
        else:
            raise ValueError(f"Unexpected Quote value: {quote_mode_policy}")

        if not quote:
            _appendable_append(out, charSeq[start:length])
            return

        _appendable_append(out, quote_char)

        while pos < length:
            c = charSeq[pos]
            if c == quote_char or c == escape_char:
                _appendable_append(out, charSeq[start:pos])
                _appendable_append(out, escape_char)
                start = pos
            pos += 1

        _appendable_append(out, charSeq[start:pos])
        _appendable_append(out, quote_char)

    def __printWithEscapes1(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        appendable: typing.Union[typing.List, io.TextIOBase],
    ) -> None:
        start = 0
        pos = 0
        buffered_reader = ExtendedBufferedReader(reader)
        delim = list(self.getDelimiterString())
        delim_length = len(delim)
        escape = self.getEscapeCharacter()
        builder: typing.List[str] = []

        c = buffered_reader.read0()
        while c != -1 and c != "":
            ch = _to_char(c)
            builder.append(ch)
            lookahead = buffered_reader.lookAhead2(delim_length - 1)
            lookahead_str = "".join(_to_char(x) for x in lookahead) if lookahead else ""
            current_str = "".join(builder) + lookahead_str
            is_delimiter_start = self.__isDelimiter(ch, current_str, pos, delim, delim_length)
            if ch == CR or ch == LF or ch == escape or is_delimiter_start:
                if pos > start:
                    self.__append1("".join(builder[start:pos]), appendable)
                    builder = []
                    pos = -1
                out_ch = "n" if ch == LF else ("r" if ch == CR else ch)
                self.__append0(escape, appendable)
                self.__append0(out_ch, appendable)

                if is_delimiter_start:
                    for _ in range(1, delim_length):
                        c = buffered_reader.read0()
                        ch2 = _to_char(c)
                        self.__append0(escape, appendable)
                        self.__append0(ch2, appendable)

                start = pos + 1
            pos += 1
            c = buffered_reader.read0()

        if pos > start:
            self.__append1("".join(builder[start:pos]), appendable)

    def __printWithEscapes0(
        self, charSeq: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        start = 0
        pos = 0
        end = len(charSeq)

        delim = list(self.getDelimiterString())
        delim_length = len(delim)
        escape = self.getEscapeCharacter()

        while pos < end:
            c = charSeq[pos]
            is_delimiter_start = self.__isDelimiter(c, charSeq, pos, delim, delim_length)
            if c == CR or c == LF or c == escape or is_delimiter_start:
                if pos > start:
                    _appendable_append(appendable, charSeq[start:pos])
                if c == LF:
                    c = "n"
                elif c == CR:
                    c = "r"

                _appendable_append(appendable, escape)
                _appendable_append(appendable, c)

                if is_delimiter_start:
                    for _ in range(1, delim_length):
                        pos += 1
                        c = charSeq[pos]
                        _appendable_append(appendable, escape)
                        _appendable_append(appendable, c)

                start = pos + 1
            pos += 1

        if pos > start:
            _appendable_append(appendable, charSeq[start:pos])

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
        else:
            content = reader.read()
            _appendable_append(out, content)

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
            _appendable_append(out, self.getDelimiterString())
        if object_ is None:
            _appendable_append(out, value)
        elif self.isQuoteCharacterSet():
            self.__printWithQuotes0(object_, value, out, newRecord)
        elif self.isEscapeCharacterSet():
            self.__printWithEscapes0(value, out)
        else:
            _appendable_append(out, value[offset:length])

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
        _appendable_append(appendable, csq)

    def __append0(
        self, c: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        _appendable_append(appendable, c)

    @staticmethod
    def __isTrimChar1(charSequence: str, pos: int) -> bool:
        return CSVFormat.__isTrimChar0(charSequence[pos])

    @staticmethod
    def __isTrimChar0(ch: str) -> bool:
        return ch <= SP

    @staticmethod
    def __isLineBreak1(c: Optional[str]) -> bool:
        return c is not None and CSVFormat.__isLineBreak0(c)

    @staticmethod
    def __isLineBreak0(c: str) -> bool:
        return c == LF or c == CR

    @staticmethod
    def __containsLineBreak(source: str) -> bool:
        return CSVFormat.__contains(source, CR) or CSVFormat.__contains(source, LF)

    @staticmethod
    def __contains(source: str, searchCh: str) -> bool:
        if source is None:
            raise ValueError("source")
        return searchCh in source

    def trim1(self, value: str) -> str:
        return value.strip() if self.getTrim() else value

    def copy(self) -> "CSVFormat":
        return self.builder().build()

    # Class Methods End


# Static predefined formats.
CSVFormat.DEFAULT = CSVFormat(
    0, False, False, COMMA, None, None, False, False, None, None, False,
    DOUBLE_QUOTE_CHAR, None, True, DuplicateHeaderMode.ALLOW_ALL, None, False,
    False, None, CRLF,
)

CSVFormat.EXCEL = (
    CSVFormat.DEFAULT.builder().setIgnoreEmptyLines(False).setAllowMissingColumnNames(True).build()
)

CSVFormat.INFORMIX_UNLOAD = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(PIPE)
    .setEscape0(BACKSLASH)
    .setQuote1(DOUBLE_QUOTE_CHAR)
    .setRecordSeparator0(LF)
    .build()
)

CSVFormat.INFORMIX_UNLOAD_CSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(COMMA)
    .setQuote1(DOUBLE_QUOTE_CHAR)
    .setRecordSeparator0(LF)
    .build()
)

CSVFormat.MONGODB_CSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(COMMA)
    .setEscape1(DOUBLE_QUOTE_CHAR)
    .setQuote1(DOUBLE_QUOTE_CHAR)
    .setQuoteMode(QuoteMode.MINIMAL)
    .setSkipHeaderRecord(False)
    .build()
)

CSVFormat.MONGODB_TSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(TAB)
    .setEscape1(DOUBLE_QUOTE_CHAR)
    .setQuote1(DOUBLE_QUOTE_CHAR)
    .setQuoteMode(QuoteMode.MINIMAL)
    .setSkipHeaderRecord(False)
    .build()
)

CSVFormat.MYSQL = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(TAB)
    .setEscape0(BACKSLASH)
    .setIgnoreEmptyLines(False)
    .setQuote1(None)
    .setRecordSeparator0(LF)
    .setNullString(SQL_NULL_STRING)
    .setQuoteMode(QuoteMode.ALL_NON_NULL)
    .build()
)

CSVFormat.ORACLE = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(COMMA)
    .setEscape0(BACKSLASH)
    .setIgnoreEmptyLines(False)
    .setQuote1(DOUBLE_QUOTE_CHAR)
    .setNullString(SQL_NULL_STRING)
    .setTrim(True)
    .setRecordSeparator1(os.linesep)
    .setQuoteMode(QuoteMode.MINIMAL)
    .build()
)

CSVFormat.POSTGRESQL_CSV = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter1(COMMA)
    .setEscape1(None)
    .setIgnoreEmptyLines(False)
    .setQuote1(DOUBLE_QUOTE_CHAR)
    .setRecordSeparator0(LF)
    .setNullString(EMPTY)
    .setQuoteMode(QuoteMode.ALL_NON_NULL)
    .build()
)

CSVFormat.POSTGRESQL_TEXT = (
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(TAB)
    .setEscape0(BACKSLASH)
    .setIgnoreEmptyLines(False)
    .setQuote1(None)
    .setRecordSeparator0(LF)
    .setNullString(SQL_NULL_STRING)
    .setQuoteMode(QuoteMode.ALL_NON_NULL)
    .build()
)

CSVFormat.RFC4180 = CSVFormat.DEFAULT.builder().setIgnoreEmptyLines(False).build()

CSVFormat.TDF = (
    CSVFormat.DEFAULT.builder().setDelimiter0(TAB).setIgnoreSurroundingSpaces(True).build()
)


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
