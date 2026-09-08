from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from io import StringIO
from io import IOBase

# Imports End


def _write_to_appendable(appendable: typing.Any, s: str) -> None:
    if hasattr(appendable, "write"):
        appendable.write(s)
    else:
        appendable.append(s)


class IOUtils:
    """Copied from Apache Commons IO."""

    DEFAULT_BUFFER_SIZE: int = 1024 * 4
    __EOF: int = -1

    @staticmethod
    def copy0(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[typing.List, io.TextIOBase],
    ) -> int:
        return IOUtils.copy1(input_, output, io.StringIO())

    @staticmethod
    def copy1(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[typing.List, io.TextIOBase],
        buffer: typing.Union[str, typing.List[str], io.StringIO],
    ) -> int:
        count = 0
        buf_size = IOUtils.DEFAULT_BUFFER_SIZE
        while True:
            chunk = input_.read(buf_size)
            if not chunk:
                break
            _write_to_appendable(output, chunk)
            count += len(chunk)
        return count

    @staticmethod
    def copyLarge0(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[io.TextIOWrapper, io.BufferedWriter, io.TextIOBase],
    ) -> int:
        return IOUtils.copyLarge1(input_, output, [None] * IOUtils.DEFAULT_BUFFER_SIZE)

    @staticmethod
    def copyLarge1(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[io.TextIOWrapper, io.BufferedWriter, io.TextIOBase],
        buffer: typing.List[str],
    ) -> int:
        count = 0
        buf_size = len(buffer) if buffer else IOUtils.DEFAULT_BUFFER_SIZE
        while True:
            chunk = input_.read(buf_size)
            if not chunk:
                break
            output.write(chunk)
            count += len(chunk)
        return count

    @staticmethod
    def rethrow(throwable: BaseException) -> RuntimeError:
        raise throwable

    def __init__(self) -> None:
        raise TypeError("No instances.")
