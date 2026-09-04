from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.ParseException import *
from src.main.org.apache.commons.cli.Options import *
from src.main.org.apache.commons.cli.CommandLine import *
import typing
from typing import *
import io
from abc import ABC

# Imports End


class CommandLineParser(ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def parse1(
        self,
        options: Options,
        arguments: typing.List[typing.List[str]],
        stopAtNonOption: bool,
    ) -> CommandLine:
        """SPI method: parse ``arguments`` against ``options``.

        This is an interface method (Java ``CommandLineParser.parse``); concrete
        parsers (``Parser`` and ``DefaultParser``) provide the implementation.
        """

    def parse0(
        self, options: Options, arguments: typing.List[typing.List[str]]
    ) -> CommandLine:
        """SPI method: parse ``arguments`` against ``options``.

        This is an interface method (Java ``CommandLineParser.parse``); concrete
        parsers (``Parser`` and ``DefaultParser``) provide the implementation.
        """

    # Class Methods End
