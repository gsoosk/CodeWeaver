from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.util.FileItemHeadersImpl import *
from src.main.org.apache.commons.fileupload.RequestContext import *
from src.main.org.apache.commons.fileupload.ProgressListener import *
from src.main.org.apache.commons.fileupload.ParameterParser import *
from src.main.org.apache.commons.fileupload.FileUploadException import *
from src.main.org.apache.commons.fileupload.FileItemHeaders import *
from src.main.org.apache.commons.fileupload.FileItemFactory import *
from src.main.org.apache.commons.fileupload.FileItem import *
import os
import typing
from typing import *
import io
from abc import ABC

# Imports End


class FileUploadIOException:

    # Class Fields Begin
    __serialVersionUID: int = None
    __cause: FileUploadException = None
    # Class Fields End

    # Class Methods Begin
    def getCause(self) -> BaseException:
        return self.__cause

    def __init__(self, pCause: FileUploadException) -> None:
        self.__cause = pCause

    # Class Methods End


class IOFileUploadException(FileUploadException):

    # Class Fields Begin
    __serialVersionUID: int = None
    __cause: typing.Union[IOError, OSError] = None
    # Class Fields End

    # Class Methods Begin
    def getCause(self) -> BaseException:
        return self.__cause

    def __init__(self, pMsg: str, pException: typing.Union[IOError, OSError]) -> None:
        super().__init__(pMsg, None)
        self.__cause = pException

    # Class Methods End


class FileItemStreamImpl:

    # Class Fields Begin
    __opened: bool = None
    __headers: FileItemHeaders = None
    # Class Fields End

    # Class Methods Begin
    def setHeaders(self, pHeaders: FileItemHeaders) -> None:
        self.__headers = pHeaders

    def getHeaders(self) -> FileItemHeaders:
        return self.__headers

    # Class Methods End


class FileItemIteratorImpl:

    # Class Fields Begin
    __currentItem: FileItemStreamImpl = None
    __currentFieldName: str = None
    __skipPreamble: bool = None
    __itemValid: bool = None
    __eof: bool = None
    # Class Fields End

    # Class Methods Begin
    def __getContentLength(self, pHeaders: FileItemHeaders) -> int:
        try:
            return int(pHeaders.getHeader(FileUploadBase.CONTENT_LENGTH))
        except Exception:
            return -1

    # Class Methods End


class SizeException(FileUploadException, ABC):

    # Class Fields Begin
    __serialVersionUID: int = None
    __actual: int = None
    __permitted: int = None
    # Class Fields End

    # Class Methods Begin
    def getPermittedSize(self) -> int:
        return self.__permitted

    def getActualSize(self) -> int:
        return self.__actual

    def __init__(self, message: str, actual: int, permitted: int) -> None:
        super().__init__(message, None)
        self.__actual = actual
        self.__permitted = permitted

    # Class Methods End


class InvalidContentTypeException(FileUploadException):

    # Class Fields Begin
    __serialVersionUID: int = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self, msg: str, cause: BaseException) -> None:
        super().__init__(msg, cause)

    # Class Methods End


class UnknownSizeException(FileUploadException):

    # Class Fields Begin
    __serialVersionUID: int = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self, message: str) -> None:
        super().__init__(message, None)

    # Class Methods End


class SizeLimitExceededException(SizeException):

    # Class Fields Begin
    __serialVersionUID: int = None
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def SizeLimitExceededException1(message: str) -> SizeLimitExceededException:
        return SizeLimitExceededException(message, 0, 0)

    @staticmethod
    def SizeLimitExceededException0() -> SizeLimitExceededException:
        return SizeLimitExceededException(None, 0, 0)

    def __init__(self, message: str, actual: int, permitted: int) -> None:
        super().__init__(message, actual, permitted)

    # Class Methods End


class FileSizeLimitExceededException(SizeException):

    # Class Fields Begin
    __serialVersionUID: int = None
    __fileName: str = None
    __fieldName: str = None
    # Class Fields End

    # Class Methods Begin
    def setFieldName(self, pFieldName: str) -> None:
        self.__fieldName = pFieldName

    def getFieldName(self) -> str:
        return self.__fieldName

    def setFileName(self, pFileName: str) -> None:
        self.__fileName = pFileName

    def getFileName(self) -> str:
        return self.__fileName

    def __init__(self, message: str, actual: int, permitted: int) -> None:
        super().__init__(message, actual, permitted)
        self.__fileName = None
        self.__fieldName = None

    # Class Methods End


class FileUploadBase(ABC):

    # Class Fields Begin
    MAX_HEADER_SIZE: int = 1024
    __sizeMax: int = -1
    __fileSizeMax: int = -1
    __fileCountMax: int = -1
    __headerEncoding: str = None
    __listener: ProgressListener = None
    CONTENT_TYPE: str = "Content-type"
    CONTENT_DISPOSITION: str = "Content-disposition"
    CONTENT_LENGTH: str = "Content-length"
    FORM_DATA: str = "form-data"
    ATTACHMENT: str = "attachment"
    MULTIPART: str = "multipart/"
    MULTIPART_FORM_DATA: str = "multipart/form-data"
    MULTIPART_MIXED: str = "multipart/mixed"
    # Class Fields End

    # Class Methods Begin
    def _getHeader(self, headers: typing.Dict[str, str], name: str) -> str:
        return headers.get(name.lower())

    def _parseHeaders(self, headerPart: str) -> typing.Dict[str, str]:
        headers = self._getParsedHeaders(headerPart)
        result: typing.Dict[str, str] = {}
        for headerName in headers.getHeaderNames():
            iter2 = headers.getHeaders(headerName)
            headerValue = next(iter2)
            for value in iter2:
                headerValue = headerValue + "," + value
            result[headerName] = headerValue
        return result

    def _createItem(
        self, headers: typing.Dict[str, str], isFormField: bool
    ) -> FileItem:
        return self.getFileItemFactory().createItem(
            self._getFieldName2(headers),
            self._getHeader(headers, FileUploadBase.CONTENT_TYPE),
            isFormField,
            self._getFileName0(headers),
        )

    def _getFieldName2(self, headers: typing.Dict[str, str]) -> str:
        return self.__getFieldName1(self._getHeader(headers, FileUploadBase.CONTENT_DISPOSITION))

    def _getFileName0(self, headers: typing.Dict[str, str]) -> str:
        return self.__getFileName2(self._getHeader(headers, FileUploadBase.CONTENT_DISPOSITION))

    def setProgressListener(self, pListener: ProgressListener) -> None:
        self.__listener = pListener

    def getProgressListener(self) -> ProgressListener:
        return self.__listener

    def _newFileItemHeaders(self) -> FileItemHeadersImpl:
        return FileItemHeadersImpl()

    def _getParsedHeaders(self, headerPart: str) -> FileItemHeaders:
        length = len(headerPart)
        headers = self._newFileItemHeaders()
        start = 0
        while True:
            end = self.__parseEndOfLine(headerPart, start)
            if start == end:
                break
            header = headerPart[start:end]
            start = end + 2
            while start < length:
                nonWs = start
                while nonWs < length:
                    c = headerPart[nonWs]
                    if c != ' ' and c != '\t':
                        break
                    nonWs += 1
                if nonWs == start:
                    break
                end = self.__parseEndOfLine(headerPart, nonWs)
                header = header + " " + headerPart[nonWs:end]
                start = end + 2
            self.__parseHeaderLine(headers, header)
        return headers

    def _getFieldName0(self, headers: FileItemHeaders) -> str:
        return self.__getFieldName1(headers.getHeader(FileUploadBase.CONTENT_DISPOSITION))

    def _getFileName1(self, headers: FileItemHeaders) -> str:
        return self.__getFileName2(headers.getHeader(FileUploadBase.CONTENT_DISPOSITION))

    def _getBoundary(self, contentType: str) -> typing.List[int]:
        parser = ParameterParser()
        parser.setLowerCaseNames(True)
        params = parser.parse0(contentType, [';', ','])
        boundaryStr = params.get("boundary")
        if boundaryStr is None:
            return None
        try:
            boundary = boundaryStr.encode("ISO-8859-1")
        except UnicodeEncodeError:
            boundary = boundaryStr.encode()
        return boundary

    def setHeaderEncoding(self, encoding: str) -> None:
        self.__headerEncoding = encoding

    def getHeaderEncoding(self) -> str:
        return self.__headerEncoding

    def setFileCountMax(self, fileCountMax: int) -> None:
        self.__fileCountMax = fileCountMax

    def getFileCountMax(self) -> int:
        return self.__fileCountMax

    def setFileSizeMax(self, fileSizeMax: int) -> None:
        self.__fileSizeMax = fileSizeMax

    def getFileSizeMax(self) -> int:
        return self.__fileSizeMax

    def setSizeMax(self, sizeMax: int) -> None:
        self.__sizeMax = sizeMax

    def getSizeMax(self) -> int:
        return self.__sizeMax

    @staticmethod
    def isMultipartContent(ctx: RequestContext) -> bool:
        contentType = ctx.getContentType()
        if contentType is None:
            return False
        if contentType.lower().startswith(FileUploadBase.MULTIPART):
            return True
        return False

    def __parseHeaderLine(self, headers: FileItemHeadersImpl, header: str) -> None:
        colonOffset = header.find(':')
        if colonOffset == -1:
            return
        headerName = header[:colonOffset].strip()
        headerValue = header[header.find(':') + 1:].strip()
        headers.addHeader(headerName, headerValue)

    def __parseEndOfLine(self, headerPart: str, end: int) -> int:
        index = end
        while True:
            offset = headerPart.find('\r', index)
            if offset == -1 or offset + 1 >= len(headerPart):
                raise RuntimeError("Expected headers to be terminated by an empty line.")
            if headerPart[offset + 1] == '\n':
                return offset
            index = offset + 1

    def __getFieldName1(self, pContentDisposition: str) -> str:
        fieldName = None
        if pContentDisposition is not None and pContentDisposition.lower().startswith(
            FileUploadBase.FORM_DATA
        ):
            parser = ParameterParser()
            parser.setLowerCaseNames(True)
            params = parser.parse1(pContentDisposition, ';')
            fieldName = params.get("name")
            if fieldName is not None:
                fieldName = fieldName.strip()
        return fieldName

    def __getFileName2(self, pContentDisposition: str) -> str:
        fileName = None
        if pContentDisposition is not None:
            cdl = pContentDisposition.lower()
            if cdl.startswith(FileUploadBase.FORM_DATA) or cdl.startswith(
                FileUploadBase.ATTACHMENT
            ):
                parser = ParameterParser()
                parser.setLowerCaseNames(True)
                params = parser.parse1(pContentDisposition, ';')
                if "filename" in params:
                    fileName = params.get("filename")
                    if fileName is not None:
                        fileName = fileName.strip()
                    else:
                        fileName = ""
        return fileName

    def setFileItemFactory(self, factory: FileItemFactory) -> None:
        raise NotImplementedError("setFileItemFactory is abstract in FileUploadBase")

    def getFileItemFactory(self) -> FileItemFactory:
        raise NotImplementedError("getFileItemFactory is abstract in FileUploadBase")

    # Class Methods End
