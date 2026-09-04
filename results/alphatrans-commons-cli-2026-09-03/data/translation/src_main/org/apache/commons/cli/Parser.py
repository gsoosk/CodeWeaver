from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.Util import *
from src.main.org.apache.commons.cli.UnrecognizedOptionException import *
from src.main.org.apache.commons.cli.ParseException import *
from src.main.org.apache.commons.cli.Options import *
from src.main.org.apache.commons.cli.OptionGroup import *
from src.main.org.apache.commons.cli.Option import *
from src.main.org.apache.commons.cli.MissingOptionException import *
from src.main.org.apache.commons.cli.MissingArgumentException import *
from src.main.org.apache.commons.cli.CommandLineParser import *
from src.main.org.apache.commons.cli.CommandLine import *
import configparser
import typing
from typing import *
import io
from abc import ABC

# Imports End


class _ListIterator:
    """A bidirectional iterator mirroring java.util.ListIterator semantics."""

    def __init__(self, data: typing.Iterable[str]) -> None:
        self.__data = list(data)
        self.__cursor = 0

    def hasNext(self) -> bool:
        return self.__cursor < len(self.__data)

    def next(self) -> str:
        item = self.__data[self.__cursor]
        self.__cursor += 1
        return item

    def hasPrevious(self) -> bool:
        return self.__cursor > 0

    def previous(self) -> str:
        self.__cursor -= 1
        return self.__data[self.__cursor]


class Parser(CommandLineParser, ABC):

    # Class Fields Begin
    _cmd: CommandLine = None
    __options: Options = None
    __requiredOptions: typing.List[typing.Any] = None
    # Class Fields End

    # Class Methods Begin
    def _setOptions(self, options: Options) -> None:
        self.__options = options
        self.__requiredOptions = list(options.getRequiredOptions())

    def _processProperties(
        self, properties: typing.Union[configparser.ConfigParser, typing.Dict]
    ) -> None:
        if properties is None:
            return

        for name in list(properties.keys()):
            option = str(name)

            opt = self._getOptions().getOption(option)
            if opt is None:
                raise UnrecognizedOptionException(
                    "Default option wasn't defined", option
                )

            group = self._getOptions().getOptionGroup(opt)
            selected = group is not None and group.getSelected() is not None

            if not self._cmd.hasOption2(option) and not selected:
                value = properties.get(option)

                if opt.hasArg():
                    if opt.getValues() is None or len(opt.getValues()) == 0:
                        try:
                            opt.addValueForProcessing(value)
                        except RuntimeError:
                            pass
                elif not (
                    value is not None and value.lower() in ("yes", "true", "1")
                ):
                    continue

                self._cmd._addOption(opt)
                self.__updateRequiredOptions(opt)

    def _processOption(self, arg: str, iter_: typing.Iterator[str]) -> None:
        hasOption = self._getOptions().hasOption(arg)

        if not hasOption:
            raise UnrecognizedOptionException("Unrecognized option: " + arg, arg)

        opt = self._getOptions().getOption(arg).clone()

        self.__updateRequiredOptions(opt)

        if opt.hasArg():
            self.processArgs(opt, iter_)

        self._cmd._addOption(opt)

    def processArgs(self, opt: Option, iter_: typing.Iterator[str]) -> None:
        while iter_.hasNext():
            str_ = iter_.next()

            if self._getOptions().hasOption(str_) and str_.startswith("-"):
                iter_.previous()
                break

            try:
                opt.addValueForProcessing(Util.stripLeadingAndTrailingQuotes(str_))
            except RuntimeError:
                iter_.previous()
                break

        if opt.getValues() is None and not opt.hasOptionalArg():
            raise MissingArgumentException.MissingArgumentException1(1, None, opt)

    def parse3(
        self,
        options: Options,
        arguments: typing.List[typing.List[str]],
        properties: typing.Union[configparser.ConfigParser, typing.Dict],
        stopAtNonOption: bool,
    ) -> CommandLine:
        for opt in options.helpOptions():
            opt.clearValues()

        for group in options.getOptionGroups():
            group.setSelected(None)

        self._setOptions(options)

        self._cmd = CommandLine()

        eatTheRest = False

        if arguments is None:
            arguments = []

        tokenList = list(
            self._flatten(self._getOptions(), arguments, stopAtNonOption)
        )

        iterator = _ListIterator(tokenList)

        while iterator.hasNext():
            t = iterator.next()

            if t == "--":
                eatTheRest = True
            elif t == "-":
                if stopAtNonOption:
                    eatTheRest = True
                else:
                    self._cmd._addArg(t)
            elif t.startswith("-"):
                if stopAtNonOption and not self._getOptions().hasOption(t):
                    eatTheRest = True
                    self._cmd._addArg(t)
                else:
                    self._processOption(t, iterator)
            else:
                self._cmd._addArg(t)

                if stopAtNonOption:
                    eatTheRest = True

            if eatTheRest:
                while iterator.hasNext():
                    str_ = iterator.next()

                    if str_ != "--":
                        self._cmd._addArg(str_)

        self._processProperties(properties)
        self._checkRequiredOptions()

        return self._cmd

    def parse2(
        self,
        options: Options,
        arguments: typing.List[typing.List[str]],
        properties: typing.Union[configparser.ConfigParser, typing.Dict],
    ) -> CommandLine:
        return self.parse3(options, arguments, properties, False)

    def parse1(
        self,
        options: Options,
        arguments: typing.List[typing.List[str]],
        stopAtNonOption: bool,
    ) -> CommandLine:
        return self.parse3(options, arguments, None, stopAtNonOption)

    def parse0(
        self, options: Options, arguments: typing.List[typing.List[str]]
    ) -> CommandLine:
        return self.parse3(options, arguments, None, False)

    def _getRequiredOptions(self) -> typing.List[typing.Any]:
        return self.__requiredOptions

    def _getOptions(self) -> Options:
        return self.__options

    def _checkRequiredOptions(self) -> None:
        if len(self._getRequiredOptions()) != 0:
            raise MissingOptionException.MissingOptionException1(
                1, self._getRequiredOptions(), None
            )

    def __updateRequiredOptions(self, opt: Option) -> None:
        if opt.isRequired():
            required = self._getRequiredOptions()
            key = opt.getKey()
            if key in required:
                required.remove(key)

        if self._getOptions().getOptionGroup(opt) is not None:
            group = self._getOptions().getOptionGroup(opt)

            if group.isRequired():
                required = self._getRequiredOptions()
                if group in required:
                    required.remove(group)

            group.setSelected(opt)

    def _flatten(
        self,
        opts: Options,
        arguments: typing.List[typing.List[str]],
        stopAtNonOption: bool,
    ) -> typing.List[typing.List[str]]:
        """Abstract hook (Java ``Parser.flatten``): rewrite the raw token list.

        Concrete parsers (``BasicParser``, ``GnuParser``, ``PosixParser``)
        override this; the abstract base never runs it directly.
        """

    # Class Methods End
