from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.csv.Token import *
from src.main.org.apache.commons.csv.QuoteMode import *
from src.main.org.apache.commons.csv.Lexer import *
from src.main.org.apache.commons.csv.ExtendedBufferedReader import *
from src.main.org.apache.commons.csv.DuplicateHeaderMode import *
from src.main.org.apache.commons.csv.Constants import *
from src.main.org.apache.commons.csv.CSVRecord import *
from src.main.org.apache.commons.csv.CSVFormat import *
import urllib
import urllib.request
import os
import typing
from typing import *
import numbers
from io import BytesIO
import io
from io import StringIO
from io import IOBase
import pathlib

# Imports End


class _CaseInsensitiveDict(dict):
    """A dict-like mapping that treats string keys case-insensitively for
    lookups, membership tests and assignment, while preserving the case of
    the first-inserted key for a given case-insensitive key (mirroring the
    behavior of a java.util.TreeMap with a case-insensitive comparator)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.__keys_orig: typing.Dict[str, str] = {}
        if args:
            source = args[0]
            if hasattr(source, "items"):
                for k, v in source.items():
                    self[k] = v
            else:
                for k, v in source:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    @staticmethod
    def __norm(key: typing.Any) -> typing.Any:
        return key.lower() if isinstance(key, str) else key

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        norm = self.__norm(key)
        if norm in self.__keys_orig:
            key = self.__keys_orig[norm]
        else:
            self.__keys_orig[norm] = key
        super().__setitem__(key, value)

    def __getitem__(self, key: typing.Any) -> typing.Any:
        norm = self.__norm(key)
        orig = self.__keys_orig.get(norm, key)
        return super().__getitem__(orig)

    def __contains__(self, key: typing.Any) -> bool:
        return self.__norm(key) in self.__keys_orig

    def __delitem__(self, key: typing.Any) -> None:
        norm = self.__norm(key)
        orig = self.__keys_orig.pop(norm, key)
        super().__delitem__(orig)

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        try:
            return self[key]
        except KeyError:
            return default


class CSVRecordIterator:
    """Iterator over CSVRecord instances produced by a CSVParser."""

    def __init__(self, parser: "CSVParser") -> None:
        self.__parser = parser
        self.__current: typing.Optional["CSVRecord"] = None

    def __getNextRecord(self) -> typing.Optional["CSVRecord"]:
        try:
            return self.__parser.nextRecord()
        except OSError as e:
            raise RuntimeError(
                f"{type(e).__name__} reading next record: {e}"
            ) from e

    def hasNext(self) -> bool:
        if self.__parser.isClosed():
            return False
        if self.__current is None:
            self.__current = self.__getNextRecord()
        return self.__current is not None

    def next_(self) -> "CSVRecord":
        if self.__parser.isClosed():
            raise StopIteration("CSVParser has been closed")
        nxt = self.__current
        self.__current = None
        if nxt is None:
            nxt = self.__getNextRecord()
            if nxt is None:
                raise StopIteration("No more CSV records available")
        return nxt

    def remove(self) -> None:
        raise NotImplementedError("remove is not supported")

    def __iter__(self) -> "CSVRecordIterator":
        return self

    def __next__(self) -> "CSVRecord":
        if not self.hasNext():
            raise StopIteration
        return self.next_()


class Headers:
    """Header information based on name and position."""

    def __init__(
        self,
        headerMap: typing.Optional[typing.Dict[str, int]],
        headerNames: typing.List[str],
    ) -> None:
        self.headerMap = headerMap
        self.headerNames = headerNames


def _open_text(
    source: typing.Any, charset: typing.Optional[str]
) -> typing.Union[io.TextIOWrapper, io.StringIO]:
    """Best-effort conversion of a byte-oriented source to a text reader."""
    if hasattr(source, "read"):
        data = source.read()
        if isinstance(data, bytes):
            return io.StringIO(data.decode(charset or "utf-8"))
        return io.StringIO(data)
    if isinstance(source, bytes):
        return io.StringIO(source.decode(charset or "utf-8"))
    return io.StringIO(str(source))


class CSVParser:
    """Parses CSV files according to the specified format."""

    def __init__(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        format_: "CSVFormat",
        characterOffset: int,
        recordNumber: int,
    ) -> None:
        if reader is None:
            raise ValueError("reader")
        if format_ is None:
            raise ValueError("format")

        self.__headerComment: typing.Optional[str] = None
        self.__trailerComment: typing.Optional[str] = None
        self.__format = format_.copy()
        self.__lexer = Lexer(self.__format, ExtendedBufferedReader(reader))
        self.__csvRecordIterator = CSVRecordIterator(self)
        self.__recordList: typing.List[str] = []
        self.__reusableToken = Token()
        self.__headers = self.__createHeaders()
        self.__characterOffset = characterOffset
        self.__recordNumber = recordNumber - 1

    @staticmethod
    def CSVParser1(
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        format_: "CSVFormat",
    ) -> "CSVParser":
        return CSVParser(reader, format_, 0, 1)

    # ---- static factory methods ----

    @staticmethod
    def parse0(file: pathlib.Path, charset: str, format_: "CSVFormat") -> "CSVParser":
        if file is None:
            raise ValueError("file")
        return CSVParser.parse2(pathlib.Path(file), charset, format_)

    @staticmethod
    def parse1(
        inputStream: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        charset: str,
        format_: "CSVFormat",
    ) -> "CSVParser":
        if inputStream is None:
            raise ValueError("inputStream")
        if format_ is None:
            raise ValueError("format")
        reader = _open_text(inputStream, charset)
        return CSVParser.parse3(reader, format_)

    @staticmethod
    def parse2(path: pathlib.Path, charset: str, format_: "CSVFormat") -> "CSVParser":
        if path is None:
            raise ValueError("path")
        if format_ is None:
            raise ValueError("format")
        f = open(path, "rb")
        return CSVParser.parse1(f, charset, format_)

    @staticmethod
    def parse3(
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        format_: "CSVFormat",
    ) -> "CSVParser":
        return CSVParser.CSVParser1(reader, format_)

    @staticmethod
    def parse4(string: str, format_: "CSVFormat") -> "CSVParser":
        if string is None:
            raise ValueError("string")
        if format_ is None:
            raise ValueError("format")
        return CSVParser.CSVParser1(io.StringIO(string), format_)

    @staticmethod
    def parse5(
        url: typing.Union[
            urllib.parse.ParseResult,
            urllib.parse.SplitResult,
            urllib.parse.DefragResult,
            str,
        ],
        charset: str,
        format_: "CSVFormat",
    ) -> "CSVParser":
        if url is None:
            raise ValueError("url")
        if charset is None:
            raise ValueError("charset")
        if format_ is None:
            raise ValueError("format")
        response = urllib.request.urlopen(str(url))
        return CSVParser.CSVParser1(_open_text(response, charset), format_)

    # ---- private helpers ----

    def __addRecordValue(self, lastRecord: bool) -> None:
        input_ = self.__format.trim1(self.__reusableToken.content.toString())
        if lastRecord and input_ == "" and self.__format.getTrailingDelimiter():
            return
        self.__recordList.append(self.__handleNull(input_))

    def __createEmptyHeaderMap(self) -> typing.Dict[str, int]:
        if self.__format.getIgnoreHeaderCase():
            return _CaseInsensitiveDict()
        return {}

    def __createHeaders(self) -> Headers:
        hdrMap: typing.Optional[typing.Dict[str, int]] = None
        headerNames: typing.Optional[typing.List[str]] = None
        formatHeader = self.__format.getHeader()
        if formatHeader is not None:
            hdrMap = self.__createEmptyHeaderMap()
            headerRecord: typing.Optional[typing.List[str]] = None
            if len(formatHeader) == 0:
                nextRecord = self.nextRecord()
                if nextRecord is not None:
                    headerRecord = list(nextRecord.values())
                    self.__headerComment = nextRecord.getComment()
            else:
                if self.__format.getSkipHeaderRecord():
                    nextRecord = self.nextRecord()
                    if nextRecord is not None:
                        self.__headerComment = nextRecord.getComment()
                headerRecord = list(formatHeader)

            if headerRecord is not None:
                observedMissing = False
                for i, header in enumerate(headerRecord):
                    blankHeader = CSVFormat.isBlank(header)
                    if blankHeader and not self.__format.getAllowMissingColumnNames():
                        raise ValueError(
                            "A header name is missing in " + str(headerRecord)
                        )

                    containsHeader = (
                        observedMissing if blankHeader else (header in hdrMap)
                    )
                    headerMode = self.__format.getDuplicateHeaderMode()
                    duplicatesAllowed = headerMode == DuplicateHeaderMode.ALLOW_ALL
                    emptyDuplicatesAllowed = (
                        headerMode == DuplicateHeaderMode.ALLOW_EMPTY
                    )

                    if (
                        containsHeader
                        and not duplicatesAllowed
                        and not (blankHeader and emptyDuplicatesAllowed)
                    ):
                        raise ValueError(
                            'The header contains a duplicate name: "'
                            + str(header)
                            + '" in '
                            + str(headerRecord)
                            + ". If this is valid then use"
                            " CSVFormat.Builder.setDuplicateHeaderMode()."
                        )
                    observedMissing = observedMissing or blankHeader
                    if header is not None:
                        hdrMap[header] = i
                        if headerNames is None:
                            headerNames = []
                        headerNames.append(header)
        if headerNames is None:
            headerNames = []
        return Headers(hdrMap, headerNames)

    def __handleNull(self, input_: str) -> typing.Optional[str]:
        isQuoted = self.__reusableToken.isQuoted
        nullString = self.__format.getNullString()
        strictQuoteMode = self.__isStrictQuoteMode()
        if input_ == nullString:
            return input_ if (strictQuoteMode and isQuoted) else None
        return (
            None
            if (
                strictQuoteMode
                and nullString is None
                and input_ == ""
                and not isQuoted
            )
            else input_
        )

    def __isStrictQuoteMode(self) -> bool:
        return self.__format.getQuoteMode() == QuoteMode.ALL_NON_NULL or (
            self.__format.getQuoteMode() == QuoteMode.NON_NUMERIC
        )

    # ---- public API ----

    def close(self) -> None:
        if self.__lexer is not None:
            self.__lexer.close()

    def getCurrentLineNumber(self) -> int:
        return self.__lexer.getCurrentLineNumber()

    def getFirstEndOfLine(self) -> str:
        return self.__lexer.getFirstEol()

    def getHeaderComment(self) -> typing.Optional[str]:
        return self.__headerComment

    def getHeaderMap(self) -> typing.Optional[typing.Dict[str, int]]:
        if self.__headers.headerMap is None:
            return None
        map_ = self.__createEmptyHeaderMap()
        for k, v in self.__headers.headerMap.items():
            map_[k] = v
        return map_

    def getHeaderMapRaw(self) -> typing.Optional[typing.Dict[str, int]]:
        return self.__headers.headerMap

    def getHeaderNames(self) -> typing.List[str]:
        return list(self.__headers.headerNames)

    def getRecordNumber(self) -> int:
        return self.__recordNumber

    def getRecords(self) -> typing.List["CSVRecord"]:
        return list(self.stream())

    def getTrailerComment(self) -> typing.Optional[str]:
        return self.__trailerComment

    def hasHeaderComment(self) -> bool:
        return self.__headerComment is not None

    def hasTrailerComment(self) -> bool:
        return self.__trailerComment is not None

    def isClosed(self) -> bool:
        return self.__lexer.isClosed()

    def iterator(self) -> CSVRecordIterator:
        return self.__csvRecordIterator

    def __iter__(self) -> CSVRecordIterator:
        return self.iterator()

    def nextRecord(self) -> typing.Optional["CSVRecord"]:
        result = None
        self.__recordList.clear()
        sb: typing.Optional[str] = None
        startCharPosition = self.__lexer.getCharacterPosition() + self.__characterOffset
        while True:
            self.__reusableToken.reset()
            self.__lexer.nextToken(self.__reusableToken)
            ttype = self.__reusableToken.type
            if ttype == Type.TOKEN:
                self.__addRecordValue(False)
            elif ttype == Type.EORECORD:
                self.__addRecordValue(True)
            elif ttype == Type.EOF:
                if self.__reusableToken.isReady:
                    self.__addRecordValue(True)
                elif sb is not None:
                    self.__trailerComment = sb
            elif ttype == Type.INVALID:
                raise OSError(
                    f"(line {self.getCurrentLineNumber()}) invalid parse sequence"
                )
            elif ttype == Type.COMMENT:
                content = self.__reusableToken.content.toString()
                if sb is None:
                    sb = content
                else:
                    sb = sb + LF + content
                self.__reusableToken.type = Type.TOKEN
            else:
                raise ValueError(f"Unexpected Token type: {ttype}")
            if self.__reusableToken.type != Type.TOKEN:
                break

        if self.__recordList:
            self.__recordNumber += 1
            comment = sb
            result = CSVRecord(
                self,
                list(self.__recordList),
                comment,
                self.__recordNumber,
                startCharPosition,
            )
        return result

    def stream(self) -> typing.Iterable["CSVRecord"]:
        return iter(self.iterator())
