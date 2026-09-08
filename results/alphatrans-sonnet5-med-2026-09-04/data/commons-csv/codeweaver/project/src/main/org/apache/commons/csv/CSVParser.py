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

# typing's wildcard import above shadows Token.Type with typing.Type; reclaim
# the real (enum-like) Token.Type symbol used by the token-type state machine.
from src.main.org.apache.commons.csv.Token import Type

# Imports End


def _java_array_to_string(arr: typing.Optional[typing.List[typing.Any]]) -> str:
    """Mirrors java.util.Arrays.toString() formatting used in error messages."""
    if arr is None:
        return "null"
    return "[" + ", ".join("null" if e is None else str(e) for e in arr) + "]"


class _CaseInsensitiveHeaderMap(dict):
    """Emulates ``new TreeMap<>(String.CASE_INSENSITIVE_ORDER)`` closely enough
    for CSVParser's createEmptyHeaderMap(): case-insensitive key lookups, and
    keys iterate in case-insensitive sorted order, while preserving the
    original casing of each inserted key for display purposes.
    """

    def __init__(self) -> None:
        super().__init__()
        self.__foldToKey: typing.Dict[str, str] = {}

    @staticmethod
    def __fold(key: typing.Any) -> typing.Any:
        return key.casefold() if isinstance(key, str) else key

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        fold = self.__fold(key)
        existing = self.__foldToKey.get(fold)
        if existing is not None and existing != key:
            dict.__delitem__(self, existing)
        self.__foldToKey[fold] = key
        dict.__setitem__(self, key, value)

    def __delitem__(self, key: typing.Any) -> None:
        fold = self.__fold(key)
        existing = self.__foldToKey.pop(fold, None)
        if existing is not None:
            dict.__delitem__(self, existing)

    def __contains__(self, key: typing.Any) -> bool:
        return self.__fold(key) in self.__foldToKey

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        actual = self.__foldToKey.get(self.__fold(key))
        return dict.get(self, actual, default) if actual is not None else default

    def __getitem__(self, key: typing.Any) -> typing.Any:
        actual = self.__foldToKey.get(self.__fold(key))
        if actual is None:
            raise KeyError(key)
        return dict.__getitem__(self, actual)

    def __iter__(self):
        return iter(sorted(dict.keys(self), key=self.__fold))

    def keys(self):
        return list(self.__iter__())

    def items(self):
        return [(k, dict.__getitem__(self, k)) for k in self.__iter__()]

    def values(self):
        return [dict.__getitem__(self, k) for k in self.__iter__()]

    def update(self, other: typing.Mapping) -> None:
        for k, v in other.items():
            self[k] = v


class CSVRecordIterator:

    # Class Fields Begin
    __current: CSVRecord = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self, parser: "CSVParser") -> None:
        self.__parser = parser
        self.__current = None

    def remove(self) -> None:
        raise NotImplementedError()

    def next_(self) -> CSVRecord:
        if self.__parser.isClosed():
            raise StopIteration("CSVParser has been closed")
        next_record = self.__current
        self.__current = None

        if next_record is None:
            next_record = self.__getNextRecord()
            if next_record is None:
                raise StopIteration("No more CSV records available")

        return next_record

    def hasNext(self) -> bool:
        if self.__parser.isClosed():
            return False
        if self.__current is None:
            self.__current = self.__getNextRecord()

        return self.__current is not None

    def __getNextRecord(self) -> CSVRecord:
        try:
            return self.__parser.nextRecord()
        except OSError as e:
            raise OSError(
                f"{type(e).__name__} reading next record: {e}"
            ) from e

    def __iter__(self) -> "CSVRecordIterator":
        return self

    def __next__(self) -> CSVRecord:
        return self.next_()

    # Class Methods End


class Headers:

    # Class Fields Begin
    headerMap: typing.Dict[str, int] = None
    headerNames: typing.List[str] = None
    # Class Fields End

    # Class Methods Begin
    def __init__(
        self, headerMap: typing.Dict[str, int], headerNames: typing.List[str]
    ) -> None:
        self.headerMap = headerMap
        self.headerNames = headerNames

    # Class Methods End


class CSVParser:

    # Class Fields Begin
    __headerComment: str = None
    __trailerComment: str = None
    __format: CSVFormat = None
    __headers: Headers = None
    __lexer: Lexer = None
    __csvRecordIterator: CSVRecordIterator = None
    __recordList: typing.List[str] = None
    __recordNumber: int = None
    __characterOffset: int = None
    __reusableToken: Token = None
    # Class Fields End

    # Class Methods Begin
    def iterator(self) -> typing.Iterator[CSVRecord]:
        return self.__csvRecordIterator

    def __iter__(self) -> typing.Iterator[CSVRecord]:
        return self.iterator()

    def close(self) -> None:
        if self.__lexer is not None:
            self.__lexer.close()

    @staticmethod
    def parse5(
        url: typing.Union[
            urllib.parse.ParseResult,
            urllib.parse.SplitResult,
            urllib.parse.DefragResult,
            str,
        ],
        charset: str,
        format_: CSVFormat,
    ) -> CSVParser:
        if url is None:
            raise ValueError("url")
        if charset is None:
            raise ValueError("charset")
        if format_ is None:
            raise ValueError("format")
        url_str = url if isinstance(url, str) else url.geturl()
        stream = urllib.request.urlopen(url_str)
        return CSVParser.parse1(stream, charset, format_)

    @staticmethod
    def parse2(path: "pathlib.Path", charset: str, format_: CSVFormat) -> CSVParser:
        if path is None:
            raise ValueError("path")
        if format_ is None:
            raise ValueError("format")
        stream = open(path, "rb")
        return CSVParser.parse1(stream, charset, format_)

    @staticmethod
    def parse1(
        inputStream: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        charset: str,
        format_: CSVFormat,
    ) -> CSVParser:
        if inputStream is None:
            raise ValueError("inputStream")
        if format_ is None:
            raise ValueError("format")
        reader = io.TextIOWrapper(inputStream, encoding=charset)
        return CSVParser.parse3(reader, format_)

    def __addRecordValue(self, lastRecord: bool) -> None:
        input_ = self.__format.trim1(self.__reusableToken.content.getvalue())
        if lastRecord and input_ == "" and self.__format.getTrailingDelimiter():
            return
        self.__recordList.append(self.__handleNull(input_))

    def stream(self) -> typing.Iterable[CSVRecord]:
        return self.iterator()

    def isClosed(self) -> bool:
        return self.__lexer.isClosed()

    def hasTrailerComment(self) -> bool:
        return self.__trailerComment is not None

    def hasHeaderComment(self) -> bool:
        return self.__headerComment is not None

    def getTrailerComment(self) -> str:
        return self.__trailerComment

    def getRecords(self) -> typing.List[CSVRecord]:
        return list(self.stream())

    def getRecordNumber(self) -> int:
        return self.__recordNumber

    def getHeaderNames(self) -> typing.List[str]:
        return list(self.__headers.headerNames)

    def getHeaderMap(self) -> typing.Dict[str, int]:
        if self.__headers.headerMap is None:
            return None
        map_ = self.__createEmptyHeaderMap()
        map_.update(self.__headers.headerMap)
        return map_

    def getHeaderComment(self) -> str:
        return self.__headerComment

    def getFirstEndOfLine(self) -> str:
        return self.__lexer.getFirstEol()

    def getCurrentLineNumber(self) -> int:
        return self.__lexer.getCurrentLineNumber()

    @staticmethod
    def CSVParser1(
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        format_: CSVFormat,
    ) -> CSVParser:
        return CSVParser(reader, format_, 0, 1)

    def __init__(
        self,
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        format_: CSVFormat,
        characterOffset: int,
        recordNumber: int,
    ) -> None:
        if reader is None:
            raise ValueError("reader")
        if format_ is None:
            raise ValueError("format")

        self.__format = format_.copy()
        self.__lexer = Lexer(self.__format, ExtendedBufferedReader(reader))
        self.__csvRecordIterator = CSVRecordIterator(self)
        self.__recordList = []
        self.__reusableToken = Token()
        self.__headerComment = None
        self.__trailerComment = None
        # These two match their final constructor arguments only after
        # createHeaders() runs; Java's final fields default to 0 while
        # createHeaders() may itself consume records via nextRecord().
        self.__recordNumber = 0
        self.__characterOffset = 0
        self.__headers = self.__createHeaders()
        self.__characterOffset = characterOffset
        self.__recordNumber = recordNumber - 1

    @staticmethod
    def parse4(string: str, format_: CSVFormat) -> CSVParser:
        if string is None:
            raise ValueError("string")
        if format_ is None:
            raise ValueError("format")
        return CSVParser.CSVParser1(io.StringIO(string), format_)

    @staticmethod
    def parse3(
        reader: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        format_: CSVFormat,
    ) -> CSVParser:
        return CSVParser.CSVParser1(reader, format_)

    @staticmethod
    def parse0(file: pathlib.Path, charset: str, format_: CSVFormat) -> CSVParser:
        if file is None:
            raise ValueError("file")
        return CSVParser.parse2(pathlib.Path(file), charset, format_)

    def __isStrictQuoteMode(self) -> bool:
        return (
            self.__format.getQuoteMode() == QuoteMode.ALL_NON_NULL
            or self.__format.getQuoteMode() == QuoteMode.NON_NUMERIC
        )

    def __handleNull(self, input_: str) -> str:
        isQuoted = self.__reusableToken.isQuoted
        nullString = self.__format.getNullString()
        strictQuoteMode = self.__isStrictQuoteMode()
        if input_ == nullString and nullString is not None:
            return input_ if (strictQuoteMode and isQuoted) else None
        return (
            None
            if (strictQuoteMode and nullString is None and input_ == "" and not isQuoted)
            else input_
        )

    def __createHeaders(self) -> Headers:
        # Deferred import: CSVFormat and CSVParser import each other, so a
        # module-level "from CSVFormat import *" can lose the CSVFormat name
        # depending on which module happens to be imported first. Resolving
        # it here (at call time, well after both modules have fully loaded)
        # sidesteps the circular-import ordering hazard.
        from src.main.org.apache.commons.csv.CSVFormat import CSVFormat

        hdrMap: typing.Optional[typing.Dict[str, int]] = None
        headerNames: typing.Optional[typing.List[str]] = None
        formatHeader = self.__format.getHeader()
        if formatHeader is not None:
            hdrMap = self.__createEmptyHeaderMap()
            headerRecord = None
            if len(formatHeader) == 0:
                nextRecord = self.nextRecord()
                if nextRecord is not None:
                    headerRecord = nextRecord.values()
                    self.__headerComment = nextRecord.getComment()
            else:
                if self.__format.getSkipHeaderRecord():
                    nextRecord = self.nextRecord()
                    if nextRecord is not None:
                        self.__headerComment = nextRecord.getComment()
                headerRecord = formatHeader

            if headerRecord is not None:
                observedMissing = False
                for i, header in enumerate(headerRecord):
                    blankHeader = CSVFormat.isBlank(header)
                    if blankHeader and not self.__format.getAllowMissingColumnNames():
                        raise ValueError(
                            "A header name is missing in "
                            + _java_array_to_string(headerRecord)
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
                            'The header contains a duplicate name: "%s" in %s. If '
                            "this is valid then use "
                            "CSVFormat.Builder.setDuplicateHeaderMode()."
                            % (header, _java_array_to_string(headerRecord))
                        )
                    observedMissing = observedMissing or blankHeader
                    if header is not None:
                        hdrMap[header] = i
                        if headerNames is None:
                            headerNames = []
                        headerNames.append(header)
        if headerNames is None:
            headerNames = []
        else:
            headerNames = list(headerNames)
        return Headers(hdrMap, headerNames)

    def __createEmptyHeaderMap(self) -> typing.Dict[str, int]:
        return (
            _CaseInsensitiveHeaderMap() if self.__format.getIgnoreHeaderCase() else {}
        )

    def nextRecord(self) -> CSVRecord:
        result = None
        self.__recordList.clear()
        sb = None
        startCharPosition = self.__lexer.getCharacterPosition() + self.__characterOffset
        while True:
            self.__reusableToken.reset()
            self.__lexer.nextToken(self.__reusableToken)
            token_type = self.__reusableToken.type
            if token_type == Type.TOKEN:
                self.__addRecordValue(False)
            elif token_type == Type.EORECORD:
                self.__addRecordValue(True)
            elif token_type == Type.EOF:
                if self.__reusableToken.isReady:
                    self.__addRecordValue(True)
                elif sb is not None:
                    self.__trailerComment = sb.getvalue()
            elif token_type == Type.INVALID:
                raise IOError(
                    f"(line {self.getCurrentLineNumber()}) invalid parse sequence"
                )
            elif token_type == Type.COMMENT:  # Ignored currently
                if sb is None:  # first comment for this record
                    sb = io.StringIO()
                else:
                    sb.write(Constants.LF)
                sb.write(self.__reusableToken.content.getvalue())
                self.__reusableToken.type = Type.TOKEN  # Read another token
            else:
                raise RuntimeError(
                    f"Unexpected Token type: {self.__reusableToken.type}"
                )
            if self.__reusableToken.type != Type.TOKEN:
                break

        if self.__recordList:
            self.__recordNumber += 1
            comment = None if sb is None else sb.getvalue()
            result = CSVRecord(
                self,
                list(self.__recordList),
                comment,
                self.__recordNumber,
                startCharPosition,
            )
        return result

    def getHeaderMapRaw(self) -> typing.Dict[str, int]:
        return self.__headers.headerMap

    # Class Methods End
