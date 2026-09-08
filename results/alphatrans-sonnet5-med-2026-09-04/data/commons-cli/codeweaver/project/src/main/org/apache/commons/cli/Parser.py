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
from abc import ABC, abstractmethod

# Imports End


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

        if isinstance(properties, configparser.ConfigParser):
            items = []
            for section in properties.sections():
                items.extend(properties.items(section))
        else:
            items = properties.items()

        for option, value in items:
            opt = self.__options.getOption(option)
            if opt is None:
                raise UnrecognizedOptionException(
                    "Default option wasn't defined", option
                )

            group = self.__options.getOptionGroup(opt)
            selected = group is not None and group.getSelected() is not None

            if not self._cmd.hasOption2(option) and not selected:
                if opt.hasArg():
                    if opt.getValues() is None or len(opt.getValues()) == 0:
                        try:
                            opt.addValueForProcessing(value)
                        except RuntimeError:
                            pass
                elif str(value).lower() not in ("yes", "true", "1"):
                    continue

                self._cmd._addOption(opt)
                self.__updateRequiredOptions(opt)

    def _processOption(self, arg: str, iter_: typing.Iterator[str]) -> None:
        hasOption = self.__options.hasOption(arg)

        if not hasOption:
            raise UnrecognizedOptionException("Unrecognized option: " + arg, arg)

        opt = self.__options.getOption(arg).clone()

        self.__updateRequiredOptions(opt)

        if opt.hasArg():
            self.processArgs(opt, iter_)

        self._cmd._addOption(opt)

    def processArgs(self, opt: Option, iter_: typing.Iterator[str]) -> None:
        while iter_.hasNext():
            str_ = iter_.next()

            if self.__options.hasOption(str_) and str_.startswith("-"):
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

        tokenList = self._flatten(self._getOptions(), arguments, stopAtNonOption)

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
        if len(self._getRequiredOptions()) > 0:
            raise MissingOptionException.MissingOptionException1(
                1, self._getRequiredOptions(), None
            )

    def __updateRequiredOptions(self, opt: Option) -> None:
        if opt.isRequired():
            if opt.getKey() in self._getRequiredOptions():
                self._getRequiredOptions().remove(opt.getKey())

        if self._getOptions().getOptionGroup(opt) is not None:
            group = self._getOptions().getOptionGroup(opt)

            if group.isRequired():
                if group in self._getRequiredOptions():
                    self._getRequiredOptions().remove(group)

            group.setSelected(opt)

    @abstractmethod
    def _flatten(
        self,
        opts: Options,
        arguments: typing.List[typing.List[str]],
        stopAtNonOption: bool,
    ) -> typing.List[typing.List[str]]:
        raise NotImplementedError

    # Class Methods End


class _ListIterator:
    """A minimal ListIterator-like helper supporting next()/previous()/hasNext(),
    mirroring java.util.ListIterator semantics used by Parser.parse3/processArgs."""

    def __init__(self, values: typing.List[str]) -> None:
        self.__values = list(values)
        self.__index = 0

    def hasNext(self) -> bool:
        return self.__index < len(self.__values)

    def next(self) -> str:
        value = self.__values[self.__index]
        self.__index += 1
        return value

    def previous(self) -> str:
        self.__index -= 1
        return self.__values[self.__index]

    def __next__(self) -> str:
        if not self.hasNext():
            raise StopIteration
        return self.next()

    def __iter__(self) -> "_ListIterator":
        return self
