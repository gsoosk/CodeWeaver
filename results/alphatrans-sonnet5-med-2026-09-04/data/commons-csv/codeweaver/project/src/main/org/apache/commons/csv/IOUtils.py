from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from io import StringIO
from io import IOBase

# Imports End


class IOUtils:
    """Copied from Apache Commons IO."""

    # Class Fields Begin
    DEFAULT_BUFFER_SIZE: int = 1024 * 4
    __EOF: int = -1
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def rethrow(throwable: BaseException) -> RuntimeError:
        """Re-raises the given throwable unchanged.

        Java uses an unchecked-cast trick to rethrow a checked exception as
        if it were unchecked; Python has no checked exceptions, so simply
        re-raising the original object reproduces the same observable
        behavior (the original exception type/message propagate untouched).
        The declared `RuntimeError` return type is never actually returned,
        matching the Java method (it always throws).
        """
        raise throwable

    @staticmethod
    def _buffer_size(buffer: typing.Any) -> int:
        if isinstance(buffer, int):
            size = buffer
        else:
            try:
                size = len(buffer)
            except TypeError:
                size = IOUtils.DEFAULT_BUFFER_SIZE
        return size if size > 0 else IOUtils.DEFAULT_BUFFER_SIZE

    @staticmethod
    def copyLarge1(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[io.TextIOWrapper, io.BufferedWriter, io.TextIOBase],
        buffer: typing.List[str],
    ) -> int:
        buffer_size = IOUtils._buffer_size(buffer)
        count = 0
        while True:
            chunk = input_.read(buffer_size)
            if not chunk:
                break
            output.write(chunk)
            count += len(chunk)
        return count

    @staticmethod
    def copyLarge0(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[io.TextIOWrapper, io.BufferedWriter, io.TextIOBase],
    ) -> int:
        return IOUtils.copyLarge1(input_, output, [""] * IOUtils.DEFAULT_BUFFER_SIZE)

    @staticmethod
    def copy1(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[typing.List, io.TextIOBase],
        buffer: typing.Union[str, typing.List[str], io.StringIO],
    ) -> int:
        buffer_size = IOUtils._buffer_size(buffer)
        count = 0
        while True:
            chunk = input_.read(buffer_size)
            if not chunk:
                break
            if isinstance(output, list):
                output.append(chunk)
            else:
                output.write(chunk)
            count += len(chunk)
        return count

    @staticmethod
    def copy0(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[typing.List, io.TextIOBase],
    ) -> int:
        return IOUtils.copy1(input_, output, IOUtils.DEFAULT_BUFFER_SIZE)

    def __init__(self) -> None:
        """No instances."""

    # Class Methods End
