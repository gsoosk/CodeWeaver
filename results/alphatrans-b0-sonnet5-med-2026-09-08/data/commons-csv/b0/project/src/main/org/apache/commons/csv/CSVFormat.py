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
import typing
from typing import *
import io
from io import IOBase
import pathlib
import numbers

# Imports End


def _append_str(appendable: typing.Any, s: str) -> None:
    if s is None:
        return
    if hasattr(appendable, "write"):
        appendable.write(s)
    else:
        appendable.append(s)


def _is_line_break_char(c: typing.Optional[str]) -> bool:
    return c == LF or c == CR


def _is_line_break(c: typing.Optional[str]) -> bool:
    return c is not None and _is_line_break_char(c)


def _contains(source: str, ch: str) -> bool:
    if source is None:
        raise ValueError("source")
    return source.find(ch) >= 0


def _contains_line_break(source: str) -> bool:
    return _contains(source, CR) or _contains(source, LF)


def _is_trim_char(ch: str) -> bool:
    return ch <= SP


def _clone_list(values: typing.Optional[typing.List[typing.Any]]):
    return None if values is None else list(values)


def _to_string_array(values: typing.Optional[typing.List[typing.Any]]):
    if values is None:
        return None
    return [None if v is None else str(v) for v in values]


def _is_blank(value: typing.Optional[str]) -> bool:
    return value is None or value.strip() == ""


class Builder:
    """Builds CSVFormat instances."""

    def __init__(self, csvFormat: "CSVFormat") -> None:
        self.__delimiter = csvFormat.getDelimiterString()
        self.__quoteCharacter = csvFormat.getQuoteCharacter()
        self.__quoteMode = csvFormat.getQuoteMode()
        self.__commentMarker = csvFormat.getCommentMarker()
        self.__escapeCharacter = csvFormat.getEscapeCharacter()
        self.__ignoreSurroundingSpaces = csvFormat.getIgnoreSurroundingSpaces()
        self.__allowMissingColumnNames = csvFormat.getAllowMissingColumnNames()
        self.__ignoreEmptyLines = csvFormat.getIgnoreEmptyLines()
        self.__recordSeparator = csvFormat.getRecordSeparator()
        self.__nullString = csvFormat.getNullString()
        self.__headerComments = csvFormat.getHeaderComments()
        self.__headers = csvFormat.getHeader()
        self.__skipHeaderRecord = csvFormat.getSkipHeaderRecord()
        self.__ignoreHeaderCase = csvFormat.getIgnoreHeaderCase()
        self.__trailingDelimiter = csvFormat.getTrailingDelimiter()
        self.__trim = csvFormat.getTrim()
        self.__autoFlush = csvFormat.getAutoFlush()
        self.__quotedNullString = getattr(
            csvFormat, "_CSVFormat__quotedNullString", None
        )
        self.__duplicateHeaderMode = csvFormat.getDuplicateHeaderMode()

    @staticmethod
    def create0() -> "Builder":
        return Builder(CSVFormat.DEFAULT)

    @staticmethod
    def create1(csvFormat: "CSVFormat") -> "Builder":
        return Builder(csvFormat)

    def build(self) -> "CSVFormat":
        return CSVFormat(
            1,
            False,
            False,
            None,
            None,
            None,
            False,
            False,
            self,
            None,
            False,
            None,
            None,
            False,
            None,
            None,
            False,
            False,
            None,
            None,
        )

    def setAllowDuplicateHeaderNames(self, allowDuplicateHeaderNames: bool) -> "Builder":
        self.setDuplicateHeaderMode(
            DuplicateHeaderMode.ALLOW_ALL
            if allowDuplicateHeaderNames
            else DuplicateHeaderMode.ALLOW_EMPTY
        )
        return self

    def setAllowMissingColumnNames(self, allowMissingColumnNames: bool) -> "Builder":
        self.__allowMissingColumnNames = allowMissingColumnNames
        return self

    def setAutoFlush(self, autoFlush: bool) -> "Builder":
        self.__autoFlush = autoFlush
        return self

    def setCommentMarker0(self, commentMarker: str) -> "Builder":
        self.setCommentMarker1(commentMarker)
        return self

    def setCommentMarker1(self, commentMarker: typing.Optional[str]) -> "Builder":
        if _is_line_break(commentMarker):
            raise ValueError("The comment start marker character cannot be a line break")
        self.__commentMarker = commentMarker
        return self

    def setDelimiter0(self, delimiter: str) -> "Builder":
        return self.setDelimiter1(delimiter)

    def setDelimiter1(self, delimiter: str) -> "Builder":
        if _contains_line_break(delimiter):
            raise ValueError("The delimiter cannot be a line break")
        if delimiter == "":
            raise ValueError("The delimiter cannot be empty")
        self.__delimiter = delimiter
        return self

    def setDuplicateHeaderMode(
        self, duplicateHeaderMode: DuplicateHeaderMode
    ) -> "Builder":
        if duplicateHeaderMode is None:
            raise ValueError("duplicateHeaderMode")
        self.__duplicateHeaderMode = duplicateHeaderMode
        return self

    def setEscape0(self, escapeCharacter: str) -> "Builder":
        self.setEscape1(escapeCharacter)
        return self

    def setEscape1(self, escapeCharacter: typing.Optional[str]) -> "Builder":
        if _is_line_break(escapeCharacter):
            raise ValueError("The escape character cannot be a line break")
        self.__escapeCharacter = escapeCharacter
        return self

    def setHeaderComments0(self, headerComments: typing.List[typing.Any]) -> "Builder":
        self.__headerComments = _to_string_array(headerComments)
        return self

    def setHeaderComments1(self, headerComments: typing.List[str]) -> "Builder":
        self.__headerComments = _clone_list(headerComments)
        return self

    def setIgnoreEmptyLines(self, ignoreEmptyLines: bool) -> "Builder":
        self.__ignoreEmptyLines = ignoreEmptyLines
        return self

    def setIgnoreHeaderCase(self, ignoreHeaderCase: bool) -> "Builder":
        self.__ignoreHeaderCase = ignoreHeaderCase
        return self

    def setIgnoreSurroundingSpaces(self, ignoreSurroundingSpaces: bool) -> "Builder":
        self.__ignoreSurroundingSpaces = ignoreSurroundingSpaces
        return self

    def setNullString(self, nullString: str) -> "Builder":
        self.__nullString = nullString
        q = self.__quoteCharacter if self.__quoteCharacter is not None else "null"
        n = nullString if nullString is not None else "null"
        self.__quotedNullString = f"{q}{n}{q}"
        return self

    def setQuote0(self, quoteCharacter: str) -> "Builder":
        self.setQuote1(quoteCharacter)
        return self

    def setQuote1(self, quoteCharacter: typing.Optional[str]) -> "Builder":
        if _is_line_break(quoteCharacter):
            raise ValueError("The quoteChar cannot be a line break")
        self.__quoteCharacter = quoteCharacter
        return self

    def setQuoteMode(self, quoteMode: QuoteMode) -> "Builder":
        self.__quoteMode = quoteMode
        return self

    def setRecordSeparator0(self, recordSeparator: str) -> "Builder":
        self.__recordSeparator = recordSeparator
        return self

    def setRecordSeparator1(self, recordSeparator: str) -> "Builder":
        self.__recordSeparator = recordSeparator
        return self

    def setSkipHeaderRecord(self, skipHeaderRecord: bool) -> "Builder":
        self.__skipHeaderRecord = skipHeaderRecord
        return self

    def setTrailingDelimiter(self, trailingDelimiter: bool) -> "Builder":
        self.__trailingDelimiter = trailingDelimiter
        return self

    def setTrim(self, trim: bool) -> "Builder":
        self.__trim = trim
        return self


class Predefined:
    """Predefines formats."""

    def __init__(self, format_: "CSVFormat") -> None:
        self.__format = format_

    def getFormat(self) -> "CSVFormat":
        return self.__format


class CSVFormat:
    """Specifies the format of a CSV file for parsing and writing."""

    __serialVersionUID: int = 2

    def __init__(
        self,
        constructorId: int,
        autoFlush: bool,
        skipHeaderRecord: bool,
        delimiter: typing.Optional[str],
        nullString: typing.Optional[str],
        escape: typing.Optional[str],
        ignoreSurroundingSpaces: bool,
        trim: bool,
        builder: typing.Optional["Builder"],
        commentStart: typing.Optional[str],
        ignoreHeaderCase: bool,
        quoteChar: typing.Optional[str],
        quoteMode: typing.Optional[QuoteMode],
        ignoreEmptyLines: bool,
        duplicateHeaderMode: typing.Optional[DuplicateHeaderMode],
        header: typing.Optional[typing.List[str]],
        allowMissingColumnNames: bool,
        trailingDelimiter: bool,
        headerComments: typing.Optional[typing.List[typing.Any]],
        recordSeparator: typing.Optional[str],
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
            self.__headers = _clone_list(header)
            self.__skipHeaderRecord = skipHeaderRecord
            self.__ignoreHeaderCase = ignoreHeaderCase
            self.__trailingDelimiter = trailingDelimiter
            self.__trim = trim
            self.__autoFlush = autoFlush
            q = quoteChar if quoteChar is not None else "null"
            n = nullString if nullString is not None else "null"
            self.__quotedNullString = f"{q}{n}{q}"
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

    # ---- static helpers ----

    @staticmethod
    def clone(values: typing.Optional[typing.List[typing.Any]]):
        return _clone_list(values)

    @staticmethod
    def isBlank(value: typing.Optional[str]) -> bool:
        return _is_blank(value)

    @staticmethod
    def toStringArray(values: typing.Optional[typing.List[typing.Any]]):
        return _to_string_array(values)

    @staticmethod
    def newFormat(delimiter: str) -> "CSVFormat":
        return CSVFormat(
            0,
            False,
            False,
            delimiter,
            None,
            None,
            False,
            False,
            None,
            None,
            False,
            None,
            None,
            False,
            DuplicateHeaderMode.ALLOW_ALL,
            None,
            False,
            False,
            None,
            None,
        )

    @staticmethod
    def valueOf(format_: str) -> "CSVFormat":
        return Predefined[format_].getFormat()

    @staticmethod
    def trim0(charSequence: str) -> str:
        return charSequence.strip()

    # ---- builder / copy ----

    def builder(self) -> "Builder":
        return Builder.create1(self)

    def copy(self) -> "CSVFormat":
        return self.builder().build()

    # ---- getters ----

    def getAllowDuplicateHeaderNames(self) -> bool:
        return self.__duplicateHeaderMode == DuplicateHeaderMode.ALLOW_ALL

    def getAllowMissingColumnNames(self) -> bool:
        return self.__allowMissingColumnNames

    def getAutoFlush(self) -> bool:
        return self.__autoFlush

    def getCommentMarker(self) -> typing.Optional[str]:
        return self.__commentMarker

    def getDelimiter(self) -> str:
        return self.__delimiter[0]

    def getDelimiterString(self) -> str:
        return self.__delimiter

    def getDuplicateHeaderMode(self) -> DuplicateHeaderMode:
        return self.__duplicateHeaderMode

    def getEscapeCharacter(self) -> typing.Optional[str]:
        return self.__escapeCharacter

    def getHeader(self) -> typing.Optional[typing.List[str]]:
        return None if self.__headers is None else list(self.__headers)

    def getHeaderComments(self) -> typing.Optional[typing.List[str]]:
        return None if self.__headerComments is None else list(self.__headerComments)

    def getIgnoreEmptyLines(self) -> bool:
        return self.__ignoreEmptyLines

    def getIgnoreHeaderCase(self) -> bool:
        return self.__ignoreHeaderCase

    def getIgnoreSurroundingSpaces(self) -> bool:
        return self.__ignoreSurroundingSpaces

    def getNullString(self) -> typing.Optional[str]:
        return self.__nullString

    def getQuoteCharacter(self) -> typing.Optional[str]:
        return self.__quoteCharacter

    def getQuoteMode(self) -> typing.Optional[QuoteMode]:
        return self.__quoteMode

    def getRecordSeparator(self) -> typing.Optional[str]:
        return self.__recordSeparator

    def getSkipHeaderRecord(self) -> bool:
        return self.__skipHeaderRecord

    def getTrailingDelimiter(self) -> bool:
        return self.__trailingDelimiter

    def getTrim(self) -> bool:
        return self.__trim

    # ---- predicates ----

    def isCommentMarkerSet(self) -> bool:
        return self.__commentMarker is not None

    def isEscapeCharacterSet(self) -> bool:
        return self.__escapeCharacter is not None

    def isNullStringSet(self) -> bool:
        return self.__nullString is not None

    def isQuoteCharacterSet(self) -> bool:
        return self.__quoteCharacter is not None

    # ---- equals / hash / str ----

    def equals(self, obj: typing.Any) -> bool:
        if self is obj:
            return True
        if obj is None or not isinstance(obj, CSVFormat):
            return False
        o = obj
        return (
            self.__duplicateHeaderMode == o.__duplicateHeaderMode
            and self.__allowMissingColumnNames == o.__allowMissingColumnNames
            and self.__autoFlush == o.__autoFlush
            and self.__commentMarker == o.__commentMarker
            and self.__delimiter == o.__delimiter
            and self.__escapeCharacter == o.__escapeCharacter
            and self.__headers == o.__headers
            and self.__headerComments == o.__headerComments
            and self.__ignoreEmptyLines == o.__ignoreEmptyLines
            and self.__ignoreHeaderCase == o.__ignoreHeaderCase
            and self.__ignoreSurroundingSpaces == o.__ignoreSurroundingSpaces
            and self.__nullString == o.__nullString
            and self.__quoteCharacter == o.__quoteCharacter
            and self.__quoteMode == o.__quoteMode
            and self.__quotedNullString == o.__quotedNullString
            and self.__recordSeparator == o.__recordSeparator
            and self.__skipHeaderRecord == o.__skipHeaderRecord
            and self.__trailingDelimiter == o.__trailingDelimiter
            and self.__trim == o.__trim
        )

    def __eq__(self, other: typing.Any) -> bool:
        return self.equals(other)

    def hashCode(self) -> int:
        return hash(
            (
                tuple(self.__headers) if self.__headers is not None else None,
                tuple(self.__headerComments)
                if self.__headerComments is not None
                else None,
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

    def __hash__(self) -> int:
        return self.hashCode()

    def toString(self) -> str:
        parts = [f"Delimiter=<{self.__delimiter}>"]
        if self.isEscapeCharacterSet():
            parts.append(f"Escape=<{self.__escapeCharacter}>")
        if self.isQuoteCharacterSet():
            parts.append(f"QuoteChar=<{self.__quoteCharacter}>")
        if self.__quoteMode is not None:
            parts.append(f"QuoteMode=<{self.__quoteMode}>")
        if self.isCommentMarkerSet():
            parts.append(f"CommentStart=<{self.__commentMarker}>")
        if self.isNullStringSet():
            parts.append(f"NullString=<{self.__nullString}>")
        if self.__recordSeparator is not None:
            parts.append(f"RecordSeparator=<{self.__recordSeparator}>")
        result = " ".join(parts)
        if self.getIgnoreEmptyLines():
            result += " EmptyLines:ignored"
        if self.getIgnoreSurroundingSpaces():
            result += " SurroundingSpaces:ignored"
        if self.getIgnoreHeaderCase():
            result += " IgnoreHeaderCase:ignored"
        result += f" SkipHeaderRecord:{self.__skipHeaderRecord}"
        if self.__headerComments is not None:
            result += f" HeaderComments:{self.__headerComments}"
        if self.__headers is not None:
            result += f" Header:{self.__headers}"
        return result

    def __str__(self) -> str:
        return self.toString()

    def __repr__(self) -> str:
        return self.toString()

    # ---- format / parse / print ----

    def format_(self, values: typing.List[typing.Any]) -> str:
        out = io.StringIO()
        printer = CSVPrinter(out, self)
        printer.printRecord1(list(values))
        res = out.getvalue()
        length = (
            len(res) - len(self.__recordSeparator)
            if self.__recordSeparator is not None
            else len(res)
        )
        return res[:length]

    def parse(
        self, reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase]
    ) -> "CSVParser":
        return CSVParser.CSVParser1(reader, self)

    def print0(self, out: typing.Union[typing.List, io.TextIOBase]) -> "CSVPrinter":
        return CSVPrinter(out, self)

    def print1(self, out: pathlib.Path, charset: str) -> "CSVPrinter":
        f = open(out, "w", encoding=charset, newline="")
        return CSVPrinter(f, self)

    def print4(self, out: pathlib.Path, charset: str) -> "CSVPrinter":
        f = open(out, "w", encoding=charset, newline="")
        return CSVPrinter(f, self)

    def printer(self) -> "CSVPrinter":
        import sys

        return CSVPrinter(sys.stdout, self)

    def print2(
        self,
        value: typing.Any,
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        if value is None:
            if self.__nullString is None:
                charSequence = EMPTY
            elif self.__quoteMode == QuoteMode.ALL:
                charSequence = self.__quotedNullString
            else:
                charSequence = self.__nullString
        elif isinstance(value, str):
            charSequence = value
        elif hasattr(value, "read"):
            self.__print5(value, out, newRecord)
            return
        else:
            charSequence = str(value)
        charSequence = CSVFormat.trim0(charSequence) if self.getTrim() else charSequence
        self.__print3(value, charSequence, out, newRecord)

    def println(self, appendable: typing.Union[typing.List, io.TextIOBase]) -> None:
        if self.getTrailingDelimiter():
            self.__append1(self.getDelimiterString(), appendable)
        if self.__recordSeparator is not None:
            self.__append1(self.__recordSeparator, appendable)

    def printRecord(
        self,
        appendable: typing.Union[typing.List, io.TextIOBase],
        values: typing.List[typing.Any],
    ) -> None:
        for i, v in enumerate(values):
            self.print2(v, appendable, i == 0)
        self.println(appendable)

    # ---- private print helpers ----

    def __append0(
        self, c: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        _append_str(appendable, c)

    def __append1(
        self, csq: str, appendable: typing.Union[typing.List, io.TextIOBase]
    ) -> None:
        _append_str(appendable, csq)

    def __print3(
        self,
        object_: typing.Any,
        value: str,
        out: typing.Union[typing.List, io.TextIOBase],
        newRecord: bool,
    ) -> None:
        if not newRecord:
            _append_str(out, self.getDelimiterString())
        if object_ is None:
            _append_str(out, value)
        elif self.isQuoteCharacterSet():
            self.__printWithQuotes0(object_, value, out, newRecord)
        elif self.isEscapeCharacterSet():
            self.__printWithEscapes0(value, out)
        else:
            _append_str(out, value)

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
            _append_str(out, content)

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
            if c == CR or c == LF or c == escape or isDelimiterStart:
                if pos > start:
                    _append_str(appendable, charSeq[start:pos])
                if c == LF:
                    c = "n"
                elif c == CR:
                    c = "r"

                _append_str(appendable, escape)
                _append_str(appendable, c)

                if isDelimiterStart:
                    for _ in range(1, delimLength):
                        pos += 1
                        c = charSeq[pos]
                        _append_str(appendable, escape)
                        _append_str(appendable, c)

                start = pos + 1
            pos += 1

        if pos > start:
            _append_str(appendable, charSeq[start:pos])

    def __printWithEscapes1(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        appendable: typing.Union[typing.List, io.TextIOBase],
    ) -> None:
        content = reader.read()
        self.__printWithEscapes0(content, appendable)

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
            quote = not isinstance(object_, numbers.Number) or isinstance(object_, bool)
        elif quoteModePolicy == QuoteMode.NONE:
            self.__printWithEscapes0(charSeq, out)
            return
        elif quoteModePolicy == QuoteMode.MINIMAL:
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
                        if _is_trim_char(c):
                            quote = True

            if not quote:
                _append_str(out, charSeq[start:length])
                return
        else:
            raise ValueError(f"Unexpected Quote value: {quoteModePolicy}")

        if not quote:
            _append_str(out, charSeq[start:length])
            return

        _append_str(out, quoteChar)

        while pos < length:
            c = charSeq[pos]
            if c == quoteChar or c == escapeChar:
                _append_str(out, charSeq[start:pos])
                _append_str(out, escapeChar)
                start = pos
            pos += 1

        _append_str(out, charSeq[start:pos])
        _append_str(out, quoteChar)

    def __printWithQuotes1(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        appendable: typing.Union[typing.List, io.TextIOBase],
    ) -> None:
        if self.getQuoteMode() == QuoteMode.NONE:
            self.__printWithEscapes1(reader, appendable)
            return

        quote = self.__quoteCharacter
        content = reader.read()
        _append_str(appendable, quote)
        _append_str(appendable, content.replace(quote, quote + quote))
        _append_str(appendable, quote)

    # ---- validation ----

    def __validate(self) -> None:
        if _contains_line_break(self.__delimiter):
            raise ValueError("The delimiter cannot be a line break")

        if self.__quoteCharacter is not None and _contains(
            self.__delimiter, self.__quoteCharacter
        ):
            raise ValueError(
                "The quoteChar character and the delimiter cannot be the same ('"
                + str(self.__quoteCharacter)
                + "')"
            )

        if self.__escapeCharacter is not None and _contains(
            self.__delimiter, self.__escapeCharacter
        ):
            raise ValueError(
                "The escape character and the delimiter cannot be the same ('"
                + str(self.__escapeCharacter)
                + "')"
            )

        if self.__commentMarker is not None and _contains(
            self.__delimiter, self.__commentMarker
        ):
            raise ValueError(
                "The comment start character and the delimiter cannot be the same ('"
                + str(self.__commentMarker)
                + "')"
            )

        if self.__quoteCharacter is not None and self.__quoteCharacter == self.__commentMarker:
            raise ValueError(
                "The comment start character and the quoteChar cannot be the same ('"
                + str(self.__commentMarker)
                + "')"
            )

        if self.__escapeCharacter is not None and self.__escapeCharacter == self.__commentMarker:
            raise ValueError(
                "The comment start and the escape character cannot be the same ('"
                + str(self.__commentMarker)
                + "')"
            )

        if self.__escapeCharacter is None and self.__quoteMode == QuoteMode.NONE:
            raise ValueError("No quotes mode set but no escape character is set")

        if (
            self.__headers is not None
            and self.__duplicateHeaderMode != DuplicateHeaderMode.ALLOW_ALL
        ):
            dupCheckSet: typing.Set[str] = set()
            emptyDuplicatesAllowed = (
                self.__duplicateHeaderMode == DuplicateHeaderMode.ALLOW_EMPTY
            )
            for header in self.__headers:
                blank = _is_blank(header)
                key = "" if blank else header
                containsHeader = key in dupCheckSet
                dupCheckSet.add(key)
                if containsHeader and not (blank and emptyDuplicatesAllowed):
                    raise ValueError(
                        'The header contains a duplicate name: "'
                        + str(header)
                        + '" in '
                        + str(self.__headers)
                        + ". If this is valid then use"
                        " CSVFormat.Builder.setDuplicateHeaderMode()."
                    )

    def trim1(self, value: str) -> str:
        return value.strip() if self.getTrim() else value

    # ---- deprecated with* methods ----

    def withAllowDuplicateHeaderNames0(self) -> "CSVFormat":
        return self.builder().setDuplicateHeaderMode(DuplicateHeaderMode.ALLOW_ALL).build()

    def withAllowDuplicateHeaderNames1(self, allowDuplicateHeaderNames: bool) -> "CSVFormat":
        mode = (
            DuplicateHeaderMode.ALLOW_ALL
            if allowDuplicateHeaderNames
            else DuplicateHeaderMode.ALLOW_EMPTY
        )
        return self.builder().setDuplicateHeaderMode(mode).build()

    def withAllowMissingColumnNames0(self) -> "CSVFormat":
        return self.builder().setAllowMissingColumnNames(True).build()

    def withAllowMissingColumnNames1(self, allowMissingColumnNames: bool) -> "CSVFormat":
        return self.builder().setAllowMissingColumnNames(allowMissingColumnNames).build()

    def withAutoFlush(self, autoFlush: bool) -> "CSVFormat":
        return self.builder().setAutoFlush(autoFlush).build()

    def withCommentMarker0(self, commentMarker: str) -> "CSVFormat":
        return self.builder().setCommentMarker0(commentMarker).build()

    def withCommentMarker1(self, commentMarker: typing.Optional[str]) -> "CSVFormat":
        return self.builder().setCommentMarker1(commentMarker).build()

    def withDelimiter(self, delimiter: str) -> "CSVFormat":
        return self.builder().setDelimiter0(delimiter).build()

    def withEscape0(self, escape: str) -> "CSVFormat":
        return self.builder().setEscape0(escape).build()

    def withEscape1(self, escape: typing.Optional[str]) -> "CSVFormat":
        return self.builder().setEscape1(escape).build()

    def withHeaderComments(self, headerComments: typing.List[typing.Any]) -> "CSVFormat":
        return self.builder().setHeaderComments0(headerComments).build()

    def withIgnoreEmptyLines0(self) -> "CSVFormat":
        return self.builder().setIgnoreEmptyLines(True).build()

    def withIgnoreEmptyLines1(self, ignoreEmptyLines: bool) -> "CSVFormat":
        return self.builder().setIgnoreEmptyLines(ignoreEmptyLines).build()

    def withIgnoreHeaderCase0(self) -> "CSVFormat":
        return self.builder().setIgnoreHeaderCase(True).build()

    def withIgnoreHeaderCase1(self, ignoreHeaderCase: bool) -> "CSVFormat":
        return self.builder().setIgnoreHeaderCase(ignoreHeaderCase).build()

    def withIgnoreSurroundingSpaces0(self) -> "CSVFormat":
        return self.builder().setIgnoreSurroundingSpaces(True).build()

    def withIgnoreSurroundingSpaces1(self, ignoreSurroundingSpaces: bool) -> "CSVFormat":
        return self.builder().setIgnoreSurroundingSpaces(ignoreSurroundingSpaces).build()

    def withNullString(self, nullString: str) -> "CSVFormat":
        return self.builder().setNullString(nullString).build()

    def withQuote0(self, quoteChar: str) -> "CSVFormat":
        return self.builder().setQuote0(quoteChar).build()

    def withQuote1(self, quoteChar: typing.Optional[str]) -> "CSVFormat":
        return self.builder().setQuote1(quoteChar).build()

    def withQuoteMode(self, quoteMode: QuoteMode) -> "CSVFormat":
        return self.builder().setQuoteMode(quoteMode).build()

    def withRecordSeparator0(self, recordSeparator: str) -> "CSVFormat":
        return self.builder().setRecordSeparator0(recordSeparator).build()

    def withRecordSeparator1(self, recordSeparator: str) -> "CSVFormat":
        return self.builder().setRecordSeparator1(recordSeparator).build()

    def withSkipHeaderRecord0(self) -> "CSVFormat":
        return self.builder().setSkipHeaderRecord(True).build()

    def withSkipHeaderRecord1(self, skipHeaderRecord: bool) -> "CSVFormat":
        return self.builder().setSkipHeaderRecord(skipHeaderRecord).build()

    def withSystemRecordSeparator(self) -> "CSVFormat":
        return self.builder().setRecordSeparator1(os.linesep).build()

    def withTrailingDelimiter0(self) -> "CSVFormat":
        return self.builder().setTrailingDelimiter(True).build()

    def withTrailingDelimiter1(self, trailingDelimiter: bool) -> "CSVFormat":
        return self.builder().setTrailingDelimiter(trailingDelimiter).build()

    def withTrim0(self) -> "CSVFormat":
        return self.builder().setTrim(True).build()

    def withTrim1(self, trim: bool) -> "CSVFormat":
        return self.builder().setTrim(trim).build()


# ---------------------------------------------------------------------------
# Predefined static CSVFormat instances (mirrors Java's static final fields).
# ---------------------------------------------------------------------------

CSVFormat.DEFAULT = CSVFormat(
    0,
    False,
    False,
    COMMA,
    None,
    None,
    False,
    False,
    None,
    None,
    False,
    DOUBLE_QUOTE_CHAR,
    None,
    True,
    DuplicateHeaderMode.ALLOW_ALL,
    None,
    False,
    False,
    None,
    CRLF,
)

CSVFormat.EXCEL = (
    CSVFormat.DEFAULT.builder()
    .setIgnoreEmptyLines(False)
    .setAllowMissingColumnNames(True)
    .build()
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
    CSVFormat.DEFAULT.builder()
    .setDelimiter0(TAB)
    .setIgnoreSurroundingSpaces(True)
    .build()
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


def _predefined_get_item(name: str) -> Predefined:
    return getattr(Predefined, name)


# Allow CSVFormat.valueOf(name) to behave like Predefined.valueOf(name).getFormat()
class _PredefinedMeta(type):
    def __getitem__(cls, name: str) -> Predefined:
        value = getattr(cls, name, None)
        if value is None or not isinstance(value, Predefined):
            raise KeyError(name)
        return value


Predefined.__class__ = _PredefinedMeta
