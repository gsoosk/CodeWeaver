from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.ProgressListener import *
from src.main.org.apache.commons.fileupload.util.Closeable import *
from src.main.org.apache.commons.fileupload.FileItemStream import *
from src.main.org.apache.commons.fileupload.FileUploadBase import *
import os
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO

# Imports End


class MalformedStreamException(IOError):

    # Class Fields Begin
    __serialVersionUID: int = 6466926458059796677
    # Class Fields End

    # Class Methods Begin
    def __init__(self, message: str) -> None:
        super().__init__(message)

    # Class Methods End


class IllegalBoundaryException(IOError):

    # Class Fields Begin
    __serialVersionUID: int = -161533165102632918
    # Class Fields End

    # Class Methods Begin
    def __init__(self, message: str) -> None:
        super().__init__(message)

    # Class Methods End


class ItemInputStream:

    # Class Fields Begin
    __total: int = None
    __pad: int = None
    __pos: int = None
    __closed: bool = None
    __BYTE_POSITIVE_OFFSET: int = 256
    # Class Fields End

    # Class Methods Begin
    def isClosed(self) -> bool:
        return self.__closed

    def skip(self, bytes_: int) -> int:
        if self.__closed:
            raise ItemSkippedException()
        av = self.available()
        if av == 0:
            av = self.__makeAvailable()
            if av == 0:
                return 0
        res = min(av, bytes_)
        outer = self.__outer
        outer._MultipartStream__head += res
        return res

    def read(self) -> int:
        return self.read0()

    def available(self) -> int:
        outer = self.__outer
        if self.__pos == -1:
            return outer._MultipartStream__tail - outer._MultipartStream__head - self.__pad
        return self.__pos - outer._MultipartStream__head

    def close1(self, pCloseUnderlying: bool) -> None:
        if self.__closed:
            return
        if pCloseUnderlying:
            self.__closed = True
            self.__outer._MultipartStream__input.close()
        else:
            while True:
                av = self.available()
                if av == 0:
                    av = self.__makeAvailable()
                    if av == 0:
                        break
                self.skip(av)
        self.__closed = True

    def close0(self) -> None:
        self.close1(False)

    def read1(self, b: typing.List[int], off: int, len_: int) -> int:
        if self.__closed:
            raise ItemSkippedException()
        if len_ == 0:
            return 0
        res = self.available()
        if res == 0:
            res = self.__makeAvailable()
            if res == 0:
                return -1
        res = min(res, len_)
        outer = self.__outer
        head = outer._MultipartStream__head
        b[off : off + res] = outer._MultipartStream__buffer[head : head + res]
        outer._MultipartStream__head += res
        self.__total += res
        return res

    def read0(self) -> int:
        if self.__closed:
            raise ItemSkippedException()
        if self.available() == 0 and self.__makeAvailable() == 0:
            return -1
        self.__total += 1
        outer = self.__outer
        b = outer._MultipartStream__buffer[outer._MultipartStream__head]
        outer._MultipartStream__head += 1
        return b

    def getBytesRead(self) -> int:
        return self.__total

    def __makeAvailable(self) -> int:
        outer = self.__outer
        if self.__pos != -1:
            return 0

        self.__total += (
            outer._MultipartStream__tail - outer._MultipartStream__head - self.__pad
        )
        buf = outer._MultipartStream__buffer
        tail = outer._MultipartStream__tail
        pad = self.__pad
        buf[0:pad] = buf[tail - pad : tail]

        outer._MultipartStream__head = 0
        outer._MultipartStream__tail = pad

        while True:
            data = outer._MultipartStream__input.read(
                outer._MultipartStream__bufSize - outer._MultipartStream__tail
            )
            if not data:
                raise MalformedStreamException("Stream ended unexpectedly")
            n = len(data)
            buf[outer._MultipartStream__tail : outer._MultipartStream__tail + n] = data
            if outer._MultipartStream__notifier is not None:
                outer._MultipartStream__notifier.noteBytesRead(n)
            outer._MultipartStream__tail += n

            self.__findSeparator()
            av = self.available()

            if av > 0 or self.__pos != -1:
                return av

    def __findSeparator(self) -> None:
        outer = self.__outer
        self.__pos = outer._findSeparator()
        if self.__pos == -1:
            if (
                outer._MultipartStream__tail - outer._MultipartStream__head
                > outer._MultipartStream__keepRegion
            ):
                self.__pad = outer._MultipartStream__keepRegion
            else:
                self.__pad = outer._MultipartStream__tail - outer._MultipartStream__head

    def __init__(self, outer: "MultipartStream" = None) -> None:
        self.__outer = outer
        self.__total = 0
        self.__pad = 0
        self.__pos = 0
        self.__closed = False
        self.__findSeparator()

    # Class Methods End


class ProgressNotifier:

    # Class Fields Begin
    __listener: ProgressListener = None
    __contentLength: int = None
    __bytesRead: int = None
    __items: int = None
    # Class Fields End

    # Class Methods Begin
    def __notifyListener(self) -> None:
        if self.__listener is not None:
            self.__listener.update(self.__bytesRead, self.__contentLength, self.__items)

    def noteItem(self) -> None:
        self.__items += 1
        self.__notifyListener()

    def noteBytesRead(self, pBytes: int) -> None:
        self.__bytesRead += pBytes
        self.__notifyListener()

    def __init__(self, pListener: ProgressListener, pContentLength: int) -> None:
        self.__listener = pListener
        self.__contentLength = pContentLength
        self.__bytesRead = 0
        self.__items = 0

    # Class Methods End


class MultipartStream:

    # Class Fields Begin
    CR: int = 0x0D
    LF: int = 0x0A
    DASH: int = 0x2D
    HEADER_PART_SIZE_MAX: int = 10240
    _DEFAULT_BUFSIZE: int = 4096
    _HEADER_SEPARATOR: typing.List[int] = [0x0D, 0x0A, 0x0D, 0x0A]
    _FIELD_SEPARATOR: typing.List[int] = [0x0D, 0x0A]
    _STREAM_TERMINATOR: typing.List[int] = [0x2D, 0x2D]
    _BOUNDARY_PREFIX: typing.List[int] = [0x0D, 0x0A, 0x2D, 0x2D]
    __input: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader] = None
    __boundaryLength: int = None
    __keepRegion: int = None
    __boundary: typing.List[int] = None
    __boundaryTable: typing.List[int] = None
    __bufSize: int = None
    __buffer: typing.List[int] = None
    __head: int = None
    __tail: int = None
    __headerEncoding: str = None
    __notifier: ProgressNotifier = None
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def MultipartStream3(
        input_: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        boundary: typing.List[int],
    ) -> MultipartStream:
        return MultipartStream(input_, boundary, MultipartStream._DEFAULT_BUFSIZE, None)

    @staticmethod
    def MultipartStream1(
        input_: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        boundary: typing.List[int],
        bufSize: int,
    ) -> MultipartStream:
        return MultipartStream(input_, boundary, bufSize, None)

    @staticmethod
    def MultipartStream0() -> MultipartStream:
        return MultipartStream.MultipartStream2(None, None, None)

    def _findSeparator(self) -> int:
        bufferPos = self.__head
        tablePos = 0
        while bufferPos < self.__tail:
            while tablePos >= 0 and self.__buffer[bufferPos] != self.__boundary[tablePos]:
                tablePos = self.__boundaryTable[tablePos]
            bufferPos += 1
            tablePos += 1
            if tablePos == self.__boundaryLength:
                return bufferPos - self.__boundaryLength
        return -1

    def _findByte(self, value: int, pos: int) -> int:
        for i in range(pos, self.__tail):
            if self.__buffer[i] == value:
                return i
        return -1

    @staticmethod
    def arrayequals(a: typing.List[int], b: typing.List[int], count: int) -> bool:
        for i in range(count):
            if a[i] != b[i]:
                return False
        return True

    def readHeaders(self) -> str:
        i = 0
        size = 0
        baos = bytearray()
        while i < len(self._HEADER_SEPARATOR):
            try:
                b = self.readByte()
            except IOError:
                raise MalformedStreamException("Stream ended unexpectedly")
            size += 1
            if size > self.HEADER_PART_SIZE_MAX:
                raise MalformedStreamException(
                    "Header section has more than %s bytes (maybe it is not properly"
                    " terminated)" % self.HEADER_PART_SIZE_MAX
                )
            if b == self._HEADER_SEPARATOR[i]:
                i += 1
            else:
                i = 0
            baos.append(b)

        if self.__headerEncoding is not None:
            try:
                headers = baos.decode(self.__headerEncoding)
            except (LookupError, UnicodeDecodeError):
                headers = baos.decode("ISO-8859-1")
        else:
            headers = baos.decode("ISO-8859-1")

        return headers

    def setBoundary(self, boundary: typing.List[int]) -> None:
        if len(boundary) != self.__boundaryLength - len(self._BOUNDARY_PREFIX):
            raise IllegalBoundaryException(
                "The length of a boundary token cannot be changed"
            )
        prefixLen = len(self._BOUNDARY_PREFIX)
        self.__boundary[prefixLen : prefixLen + len(boundary)] = bytes(boundary)
        self.__computeBoundaryTable()

    def readBoundary(self) -> bool:
        marker = bytearray(2)
        nextChunk = False

        self.__head += self.__boundaryLength
        try:
            marker[0] = self.readByte()
            if marker[0] == self.LF:
                return True

            marker[1] = self.readByte()
            if self.arrayequals(marker, self._STREAM_TERMINATOR, 2):
                nextChunk = False
            elif self.arrayequals(marker, self._FIELD_SEPARATOR, 2):
                nextChunk = True
            else:
                raise MalformedStreamException("Unexpected characters follow a boundary")
        except FileUploadIOException:
            raise
        except IOError:
            raise MalformedStreamException("Stream ended unexpectedly")
        return nextChunk

    def readByte(self) -> int:
        if self.__head == self.__tail:
            self.__head = 0
            data = self.__input.read(self.__bufSize)
            if not data:
                raise IOError("No more data is available")
            n = len(data)
            self.__buffer[0:n] = data
            self.__tail = n
            if self.__notifier is not None:
                self.__notifier.noteBytesRead(self.__tail)
        b = self.__buffer[self.__head]
        self.__head += 1
        return b

    def setHeaderEncoding(self, encoding: str) -> None:
        self.__headerEncoding = encoding

    def getHeaderEncoding(self) -> str:
        return self.__headerEncoding

    @staticmethod
    def MultipartStream2(
        input_: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        boundary: typing.List[int],
        pNotifier: ProgressNotifier,
    ) -> MultipartStream:
        return MultipartStream(input_, boundary, MultipartStream._DEFAULT_BUFSIZE, pNotifier)

    def __init__(
        self,
        input_: typing.Union[io.BytesIO, io.StringIO, io.BufferedReader],
        boundary: typing.List[int],
        bufSize: int,
        pNotifier: ProgressNotifier,
    ) -> None:
        if boundary is None:
            raise ValueError("boundary may not be null")
        self.__boundaryLength = len(boundary) + len(self._BOUNDARY_PREFIX)
        if bufSize < self.__boundaryLength + 1:
            raise ValueError(
                "The buffer size specified for the MultipartStream is too small"
            )

        self.__input = input_
        self.__bufSize = max(bufSize, self.__boundaryLength * 2)
        self.__buffer = bytearray(self.__bufSize)
        self.__notifier = pNotifier

        self.__boundary = bytearray(self.__boundaryLength)
        self.__boundaryTable = [0] * (self.__boundaryLength + 1)
        self.__keepRegion = len(self.__boundary)

        self.__boundary[0 : len(self._BOUNDARY_PREFIX)] = bytes(self._BOUNDARY_PREFIX)
        self.__boundary[
            len(self._BOUNDARY_PREFIX) : len(self._BOUNDARY_PREFIX) + len(boundary)
        ] = bytes(boundary)
        self.__computeBoundaryTable()

        self.__head = 0
        self.__tail = 0
        self.__headerEncoding = None

    def __computeBoundaryTable(self) -> None:
        position = 2
        candidate = 0

        self.__boundaryTable[0] = -1
        self.__boundaryTable[1] = 0

        while position <= self.__boundaryLength:
            if self.__boundary[position - 1] == self.__boundary[candidate]:
                self.__boundaryTable[position] = candidate + 1
                candidate += 1
                position += 1
            elif candidate > 0:
                candidate = self.__boundaryTable[candidate]
            else:
                self.__boundaryTable[position] = 0
                position += 1

    def newInputStream(self) -> ItemInputStream:
        return ItemInputStream(self)

    # Class Methods End
