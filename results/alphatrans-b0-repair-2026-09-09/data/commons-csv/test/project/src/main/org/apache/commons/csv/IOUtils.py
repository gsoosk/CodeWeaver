from __future__ import annotations

# Imports Begin
import typing
from typing import *
import io
from io import StringIO
from io import IOBase

# Imports End


class IOUtils:

    # Class Fields Begin
    DEFAULT_BUFFER_SIZE: int = 1024 * 4
    __EOF: int = -1
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def rethrow(throwable: BaseException) -> RuntimeError:
        raise throwable

    @staticmethod
    def copyLarge1(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[io.TextIOWrapper, io.BufferedWriter, io.TextIOBase],
        buffer: typing.List[str],
    ) -> int:
        count = 0
        buf_len = len(buffer)
        while True:
            chunk = input_.read(buf_len)
            n = len(chunk) if chunk else 0
            if n == IOUtils.__EOF or n == 0:
                break
            output.write(chunk)
            count += n
        return count

    @staticmethod
    def copyLarge0(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[io.TextIOWrapper, io.BufferedWriter, io.TextIOBase],
    ) -> int:
        return IOUtils.copyLarge1(input_, output, [' '] * IOUtils.DEFAULT_BUFFER_SIZE)

    @staticmethod
    def copy1(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[typing.List, io.TextIOBase],
        buffer: typing.Union[str, typing.List[str], io.StringIO],
    ) -> int:
        count = 0
        buf_len = IOUtils.DEFAULT_BUFFER_SIZE
        if isinstance(buffer, list):
            buf_len = len(buffer)
        while True:
            chunk = input_.read(buf_len)
            n = len(chunk) if chunk else 0
            if n == IOUtils.__EOF or n == 0:
                break
            if hasattr(output, 'append'):
                output.append(chunk)
            elif hasattr(output, 'write'):
                output.write(chunk)
            count += n
        return count

    @staticmethod
    def copy0(
        input_: typing.Union[io.TextIOWrapper, io.BufferedReader, io.TextIOBase],
        output: typing.Union[typing.List, io.TextIOBase],
    ) -> int:
        return IOUtils.copy1(input_, output, [' '] * IOUtils.DEFAULT_BUFFER_SIZE)

    def __init__(self) -> None:
        pass

    # Class Methods End
