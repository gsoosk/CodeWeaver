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
    """A dict that behaves roughly like a Java TreeMap with
    String.CASE_INSENSITIVE_ORDER: lookups/containment are case
    insensitive, and iteration order is sorted case-insensitively."""

    def __contains__(self, key):
        if not isinstance(key, str):
            return dict.__contains__(self, key)
        kl = key.casefold()
        for k in dict.keys(self):
            if isinstance(k, str) and k.casefold() == kl:
                return True
        return False

    def get(self, key, default=None):
        if isinstance(key, str):
            kl = key.casefold()
            for k, v in dict.items(self):
                if isinstance(k, str) and k.casefold() == kl:
                    return v
            return default
        return dict.get(self, key, default)

    def keys(self):
        return sorted(dict.keys(self), key=lambda x: x.casefold() if isinstance(x, str) else x)

    def items(self):
        return sorted(dict.items(self), key=lambda x: x[0].casefold() if isinstance(x[0], str) else x[0])

    def __iter__(self):
        return iter(self.keys())


class CSVRecordIterator:

    # Class Fields Begin
    __current: CSVRecord = None
    # Class Fields End

    def __init__(self, parser: "CSVParser" = None) -> None:
        self.__parser = parser
        self.__current = None

    # Class Methods Begin
    def remove(self) -> None:
        raise NotImplementedError("remove is not supported")

    def next_(self) -> CSVRecord:
        if self.__parser.isClosed():
            raise StopIteration("CSVParser has been closed")
        next_ = self.__current
        self.__current = None

        if next_ is None:
            next_ = self.__getNextRecord()
            if next_ is None:
                raise StopIteration("No more CSV records available")

        return next_

    def hasNext(self) -> bool:
        if self.__parser.isClosed():
            return False
        if self.__current is None:
            self.__current = self.__getNextRecord()

        return self.__current is not None

    def __getNextRecord(self) -> CSVRecord:
        try:
            return self.__parser.nextRecord()
        except IOError as e:
            raise IOError(
                f"{type(e).__name__} reading next record: {e}"
            ) from e

    # Python iteration protocol
    def __iter__(self):
        return self

    def __next__(self):
        if self.__parser.isClosed():
            raise StopIteration
        if self.__current is None:
            self.__current = self.__getNextRecord()
        if self.__current is None:
            raise StopIteration
        result = self.__current
        self.__current = None
        return result

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

    def __iter__(self):
        return iter(self.iterator())

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
        response = urllib.request.urlopen(url_str)
        reader = io.TextIOWrapper(response, encoding=charset)
        return CSVParser.CSVParser1(reader, format_)

    @staticmethod
    def parse2(path: "Path", charset: str, format_: CSVFormat) -> CSVParser:
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
        content = self.__reusableToken.content
        content_str = content.getvalue() if isinstance(content, io.StringIO) else str(content)
        input_ = self.__format.trim1(content_str)
        if lastRecord and input_ == "" and self.__format.getTrailingDelimiter():
            return
        self.__recordList.append(self.__handleNull(input_))

    def stream(self) -> typing.Iterable[CSVRecord]:
        def gen():
            for record in self.iterator():
                yield record

        return gen()

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
        m = self.__createEmptyHeaderMap()
        m.update(self.__headers.headerMap)
        return m

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
        self.__lexer = Lexer(format_, ExtendedBufferedReader(reader))
        self.__csvRecordIterator = CSVRecordIterator(self)
        self.__recordList = []
        self.__reusableToken = Token()
        self.__headerComment = None
        self.__trailerComment = None
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
        path = file if isinstance(file, pathlib.Path) else pathlib.Path(str(file))
        return CSVParser.parse2(path, charset, format_)

    def __isStrictQuoteMode(self) -> bool:
        return (
            self.__format.getQuoteMode() == QuoteMode.ALL_NON_NULL
            or self.__format.getQuoteMode() == QuoteMode.NON_NUMERIC
        )

    def __handleNull(self, input_: str) -> str:
        isQuoted = self.__reusableToken.isQuoted
        nullString = self.__format.getNullString()
        strictQuoteMode = self.__isStrictQuoteMode()
        if input_ == nullString:
            return input_ if (strictQuoteMode and isQuoted) else None
        return (
            None
            if (strictQuoteMode and nullString is None and input_ == "" and not isQuoted)
            else input_
        )

    def __createHeaders(self) -> Headers:
        hdrMap = None
        headerNames = None
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
                            f"A header name is missing in {list(headerRecord)}"
                        )

                    containsHeader = (
                        observedMissing if blankHeader else (header in hdrMap)
                    )
                    headerMode = self.__format.getDuplicateHeaderMode()
                    duplicatesAllowed = headerMode == DuplicateHeaderMode.ALLOW_ALL
                    emptyDuplicatesAllowed = headerMode == DuplicateHeaderMode.ALLOW_EMPTY

                    if (
                        containsHeader
                        and not duplicatesAllowed
                        and not (blankHeader and emptyDuplicatesAllowed)
                    ):
                        raise ValueError(
                            'The header contains a duplicate name: "%s" in %s. If '
                            "this is valid then use "
                            "CSVFormat.Builder.setDuplicateHeaderMode()."
                            % (header, list(headerRecord))
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

    def __createEmptyHeaderMap(self) -> typing.Dict[str, int]:
        if self.__format.getIgnoreHeaderCase():
            return _CaseInsensitiveDict()
        return {}

    def nextRecord(self) -> CSVRecord:
        result = None
        self.__recordList.clear()
        sb = None
        startCharPosition = self.__lexer.getCharacterPosition() + self.__characterOffset
        while True:
            self.__reusableToken.reset()
            self.__lexer.nextToken(self.__reusableToken)
            t = self.__reusableToken.type
            if t == TOKEN:
                self.__addRecordValue(False)
            elif t == EORECORD:
                self.__addRecordValue(True)
            elif t == EOF:
                if self.__reusableToken.isReady:
                    self.__addRecordValue(True)
                elif sb is not None:
                    self.__trailerComment = sb.getvalue()
            elif t == INVALID:
                raise IOError(
                    f"(line {self.getCurrentLineNumber()}) invalid parse sequence"
                )
            elif t == COMMENT:
                if sb is None:
                    sb = io.StringIO()
                else:
                    sb.write(Constants.LF)
                content = self.__reusableToken.content
                content_str = (
                    content.getvalue() if isinstance(content, io.StringIO) else str(content)
                )
                sb.write(content_str)
                self.__reusableToken.type = TOKEN
            else:
                raise RuntimeError(f"Unexpected Token type: {t}")

            if self.__reusableToken.type != TOKEN:
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
