from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from io import StringIO

# Imports End


class FileUploadException(Exception):

    # Class Fields Begin
    __serialVersionUID: int = None
    __cause: BaseException = None
    # Class Fields End

    # Class Methods Begin
    def getCause(self) -> BaseException:
        return self.__cause

    def printStackTrace1(
        self, writer: typing.Union[io.TextIOWrapper, io.StringIO]
    ) -> None:
        import traceback

        traceback.print_exception(
            type(self), self, self.__traceback__, file=writer
        )
        if self.__cause is not None:
            writer.write("Caused by:\n")
            traceback.print_exception(
                type(self.__cause),
                self.__cause,
                self.__cause.__traceback__,
                file=writer,
            )

    def printStackTrace0(self, stream: typing.IO) -> None:
        import traceback

        traceback.print_exception(
            type(self), self, self.__traceback__, file=stream
        )
        if self.__cause is not None:
            stream.write("Caused by:\n")
            traceback.print_exception(
                type(self.__cause),
                self.__cause,
                self.__cause.__traceback__,
                file=stream,
            )

    def __init__(self, msg: str, cause: BaseException) -> None:
        super().__init__(msg)
        self.__cause = cause

    @staticmethod
    def FileUploadException1(msg: str) -> FileUploadException:
        return FileUploadException(msg, None)

    @staticmethod
    def FileUploadException0() -> FileUploadException:
        return FileUploadException(None, None)

    # Class Methods End
