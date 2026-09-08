from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.Options import *
from src.main.org.apache.commons.cli.OptionGroup import *
from src.main.org.apache.commons.cli.Option import *
import os
import typing
from typing import *
import io
from io import StringIO
from io import IOBase
import functools
import sys

# Imports End


class OptionComparator:

    # Class Fields Begin
    __serialVersionUID: int = 5305467873966684014
    # Class Fields End

    # Class Methods Begin
    def compare(self, opt1: Option, opt2: Option) -> int:
        key1 = opt1.getKey().lower()
        key2 = opt2.getKey().lower()
        if key1 < key2:
            return -1
        if key1 > key2:
            return 1
        return 0

    def __call__(self, opt1: Option, opt2: Option) -> int:
        return self.compare(opt1, opt2)

    # Class Methods End


class HelpFormatter:

    # Class Fields Begin
    DEFAULT_WIDTH: int = 74
    DEFAULT_LEFT_PAD: int = 1
    DEFAULT_DESC_PAD: int = 3
    DEFAULT_SYNTAX_PREFIX: str = "usage: "
    DEFAULT_OPT_PREFIX: str = "-"
    DEFAULT_LONG_OPT_PREFIX: str = "--"
    DEFAULT_LONG_OPT_SEPARATOR: str = " "
    DEFAULT_ARG_NAME: str = "arg"

    defaultWidth: int = None
    defaultLeftPad: int = None
    defaultDescPad: int = None
    defaultSyntaxPrefix: str = None
    defaultNewLine: str = None
    defaultOptPrefix: str = None
    defaultLongOptPrefix: str = None
    defaultArgName: str = None
    _optionComparator: typing.Callable[[Option, Option], int] = None
    __longOptSeparator: str = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.defaultWidth = HelpFormatter.DEFAULT_WIDTH
        self.defaultLeftPad = HelpFormatter.DEFAULT_LEFT_PAD
        self.defaultDescPad = HelpFormatter.DEFAULT_DESC_PAD
        self.defaultSyntaxPrefix = HelpFormatter.DEFAULT_SYNTAX_PREFIX
        self.defaultNewLine = os.linesep
        self.defaultOptPrefix = HelpFormatter.DEFAULT_OPT_PREFIX
        self.defaultLongOptPrefix = HelpFormatter.DEFAULT_LONG_OPT_PREFIX
        self.defaultArgName = HelpFormatter.DEFAULT_ARG_NAME
        self._optionComparator = OptionComparator()
        self.__longOptSeparator = HelpFormatter.DEFAULT_LONG_OPT_SEPARATOR

    def setWidth(self, width: int) -> None:
        self.defaultWidth = width

    def setSyntaxPrefix(self, prefix: str) -> None:
        self.defaultSyntaxPrefix = prefix

    def setOptPrefix(self, prefix: str) -> None:
        self.defaultOptPrefix = prefix

    def setOptionComparator(
        self, comparator: typing.Callable[[Option, Option], int]
    ) -> None:
        self._optionComparator = comparator

    def setNewLine(self, newline: str) -> None:
        self.defaultNewLine = newline

    def setLongOptSeparator(self, longOptSeparator: str) -> None:
        self.__longOptSeparator = longOptSeparator

    def setLongOptPrefix(self, prefix: str) -> None:
        self.defaultLongOptPrefix = prefix

    def setLeftPadding(self, padding: int) -> None:
        self.defaultLeftPad = padding

    def setDescPadding(self, padding: int) -> None:
        self.defaultDescPad = padding

    def setArgName(self, name: str) -> None:
        self.defaultArgName = name

    def _rtrim(self, s: str) -> str:
        if s is None or len(s) == 0:
            return s

        pos = len(s)

        while pos > 0 and s[pos - 1].isspace():
            pos -= 1

        return s[:pos]

    def _renderWrappedText(
        self, sb: io.StringIO, width: int, nextLineTabStop: int, text: str
    ) -> io.StringIO:
        pos = self._findWrapPos(text, width, 0)

        if pos == -1:
            sb.write(self._rtrim(text))
            return sb

        sb.write(self._rtrim(text[:pos]))
        sb.write(self.getNewLine())

        if nextLineTabStop >= width:
            nextLineTabStop = 1

        padding = self._createPadding(nextLineTabStop)

        while True:
            text = padding + text[pos:].strip()
            pos = self._findWrapPos(text, width, 0)

            if pos == -1:
                sb.write(text)
                return sb

            if len(text) > width and pos == nextLineTabStop - 1:
                pos = width

            sb.write(self._rtrim(text[:pos]))
            sb.write(self.getNewLine())

    def _renderOptions(
        self, sb: io.StringIO, width: int, options: Options, leftPad: int, descPad: int
    ) -> io.StringIO:
        lpad = self._createPadding(leftPad)
        dpad = self._createPadding(descPad)

        max_len = 0
        prefixList: typing.List[str] = []

        optList = list(options.helpOptions())

        if self.getOptionComparator() is not None:
            optList.sort(key=functools.cmp_to_key(self.getOptionComparator()))

        for option in optList:
            optBuf = io.StringIO()

            if option.getOpt() is None:
                optBuf.write(lpad)
                optBuf.write("   ")
                optBuf.write(self.getLongOptPrefix())
                optBuf.write(option.getLongOpt())
            else:
                optBuf.write(lpad)
                optBuf.write(self.getOptPrefix())
                optBuf.write(option.getOpt())

                if option.hasLongOpt():
                    optBuf.write(",")
                    optBuf.write(self.getLongOptPrefix())
                    optBuf.write(option.getLongOpt())

            if option.hasArg():
                argName = option.getArgName()
                if argName is not None and len(argName) == 0:
                    optBuf.write(" ")
                else:
                    optBuf.write(self.__longOptSeparator if option.hasLongOpt() else " ")
                    optBuf.write("<")
                    optBuf.write(argName if argName is not None else self.getArgName())
                    optBuf.write(">")

            optStr = optBuf.getvalue()
            prefixList.append(optStr)
            max_len = len(optStr) if len(optStr) > max_len else max_len

        x = 0

        for option in optList:
            optBuf = prefixList[x]
            x += 1

            if len(optBuf) < max_len:
                optBuf = optBuf + self._createPadding(max_len - len(optBuf))

            optBuf = optBuf + dpad

            nextLineTabStop = max_len + descPad

            if option.getDescription() is not None:
                optBuf = optBuf + option.getDescription()

            self._renderWrappedText(sb, width, nextLineTabStop, optBuf)

            if x < len(optList):
                sb.write(self.getNewLine())

        return sb

    def printWrapped1(
        self, pw: typing.Union[io.TextIOWrapper, io.StringIO], width: int, text: str
    ) -> None:
        self.printWrapped0(pw, width, 0, text)

    @staticmethod
    def _writeToWriter(pw: typing.Any, text: str) -> None:
        # PrintWriter over an OutputStream (e.g. an io.BytesIO) auto-encodes str
        # to bytes; mirror that behavior so both text and binary streams work.
        try:
            pw.write(text)
        except TypeError:
            pw.write(text.encode(sys.getdefaultencoding()))

    def printWrapped0(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        nextLineTabStop: int,
        text: str,
    ) -> None:
        sb = io.StringIO()

        self.__renderWrappedTextBlock(sb, width, nextLineTabStop, text)
        self._writeToWriter(pw, sb.getvalue())
        self._writeToWriter(pw, os.linesep)

    def printUsage1(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        app: str,
        options: Options,
    ) -> None:
        buff = io.StringIO()
        buff.write(self.getSyntaxPrefix())
        buff.write(app)
        buff.write(" ")

        processedGroups: typing.List[OptionGroup] = []

        optList = list(options.getOptions())
        if self.getOptionComparator() is not None:
            optList.sort(key=functools.cmp_to_key(self.getOptionComparator()))

        for i, option in enumerate(optList):
            group = options.getOptionGroup(option)

            if group is not None:
                if group not in processedGroups:
                    processedGroups.append(group)

                    self.__appendOptionGroup(buff, group)
            else:
                self.__appendOption(buff, option, option.isRequired())

            if i < len(optList) - 1:
                buff.write(" ")

        text = buff.getvalue()
        self.printWrapped0(pw, width, text.find(' ') + 1, text)

    def printUsage0(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        cmdLineSyntax: str,
    ) -> None:
        argPos = cmdLineSyntax.find(' ') + 1

        self.printWrapped0(
            pw,
            width,
            len(self.getSyntaxPrefix()) + argPos,
            self.getSyntaxPrefix() + cmdLineSyntax,
        )

    def printOptions(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        options: Options,
        leftPad: int,
        descPad: int,
    ) -> None:
        sb = io.StringIO()

        self._renderOptions(sb, width, options, leftPad, descPad)
        self._writeToWriter(pw, sb.getvalue())
        self._writeToWriter(pw, os.linesep)

    def printHelp7(
        self,
        cmdLineSyntax: str,
        header: str,
        options: Options,
        footer: str,
        autoUsage: bool,
    ) -> None:
        self.printHelp1(self.getWidth(), cmdLineSyntax, header, options, footer, autoUsage)

    def printHelp6(
        self, cmdLineSyntax: str, header: str, options: Options, footer: str
    ) -> None:
        self.printHelp7(cmdLineSyntax, header, options, footer, False)

    def printHelp5(self, cmdLineSyntax: str, options: Options, autoUsage: bool) -> None:
        self.printHelp1(self.getWidth(), cmdLineSyntax, None, options, None, autoUsage)

    def printHelp4(self, cmdLineSyntax: str, options: Options) -> None:
        self.printHelp1(self.getWidth(), cmdLineSyntax, None, options, None, False)

    def printHelp3(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        cmdLineSyntax: str,
        header: str,
        options: Options,
        leftPad: int,
        descPad: int,
        footer: str,
        autoUsage: bool,
    ) -> None:
        if cmdLineSyntax is None or len(cmdLineSyntax) == 0:
            raise ValueError("cmdLineSyntax not provided")

        if autoUsage:
            self.printUsage1(pw, width, cmdLineSyntax, options)
        else:
            self.printUsage0(pw, width, cmdLineSyntax)

        if header is not None and len(header) > 0:
            self.printWrapped1(pw, width, header)

        self.printOptions(pw, width, options, leftPad, descPad)

        if footer is not None and len(footer) > 0:
            self.printWrapped1(pw, width, footer)

    def printHelp2(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        cmdLineSyntax: str,
        header: str,
        options: Options,
        leftPad: int,
        descPad: int,
        footer: str,
    ) -> None:
        self.printHelp3(pw, width, cmdLineSyntax, header, options, leftPad, descPad, footer, False)

    def printHelp1(
        self,
        width: int,
        cmdLineSyntax: str,
        header: str,
        options: Options,
        footer: str,
        autoUsage: bool,
    ) -> None:
        pw = sys.stdout

        self.printHelp3(
            pw,
            width,
            cmdLineSyntax,
            header,
            options,
            self.getLeftPadding(),
            self.getDescPadding(),
            footer,
            autoUsage,
        )
        pw.flush()

    def printHelp0(
        self, width: int, cmdLineSyntax: str, header: str, options: Options, footer: str
    ) -> None:
        self.printHelp1(width, cmdLineSyntax, header, options, footer, False)

    def getWidth(self) -> int:
        return self.defaultWidth

    def getSyntaxPrefix(self) -> str:
        return self.defaultSyntaxPrefix

    def getOptPrefix(self) -> str:
        return self.defaultOptPrefix

    def getOptionComparator(self) -> typing.Callable[[Option, Option], int]:
        return self._optionComparator

    def getNewLine(self) -> str:
        return self.defaultNewLine

    def getLongOptSeparator(self) -> str:
        return self.__longOptSeparator

    def getLongOptPrefix(self) -> str:
        return self.defaultLongOptPrefix

    def getLeftPadding(self) -> int:
        return self.defaultLeftPad

    def getDescPadding(self) -> int:
        return self.defaultDescPad

    def getArgName(self) -> str:
        return self.defaultArgName

    def _findWrapPos(self, text: str, width: int, startPos: int) -> int:
        pos = text.find('\n', startPos)
        if pos != -1 and pos <= width:
            return pos + 1

        pos = text.find('\t', startPos)
        if pos != -1 and pos <= width:
            return pos + 1

        if startPos + width >= len(text):
            return -1

        pos = startPos + width
        while pos >= startPos:
            c = text[pos]
            if c == ' ' or c == '\n' or c == '\r':
                break
            pos -= 1

        if pos > startPos:
            return pos

        pos = startPos + width

        return -1 if pos == len(text) else pos

    def _createPadding(self, len_: int) -> str:
        return ' ' * len_

    def __renderWrappedTextBlock(
        self, sb: io.StringIO, width: int, nextLineTabStop: int, text: str
    ) -> typing.Union[typing.List, io.TextIOBase]:
        lines = text.split('\n')
        # Mirror BufferedReader.readLine(): a trailing '\n' does not produce
        # an extra empty final line.
        if len(lines) > 1 and lines[-1] == "":
            lines.pop()

        firstLine = True
        for line in lines:
            # readLine() also strips a trailing '\r' from each line.
            if line.endswith('\r'):
                line = line[:-1]
            if not firstLine:
                sb.write(self.getNewLine())
            else:
                firstLine = False
            self._renderWrappedText(sb, width, nextLineTabStop, line)

        return sb

    def __appendOptionGroup(self, buff: io.StringIO, group: OptionGroup) -> None:
        if not group.isRequired():
            buff.write("[")

        optList = list(group.getOptions())
        if self.getOptionComparator() is not None:
            optList.sort(key=functools.cmp_to_key(self.getOptionComparator()))

        for i, option in enumerate(optList):
            self.__appendOption(buff, option, True)

            if i < len(optList) - 1:
                buff.write(" | ")

        if not group.isRequired():
            buff.write("]")

    def __appendOption(self, buff: io.StringIO, option: Option, required: bool) -> None:
        if not required:
            buff.write("[")

        if option.getOpt() is not None:
            buff.write("-")
            buff.write(option.getOpt())
        else:
            buff.write("--")
            buff.write(option.getLongOpt())

        if option.hasArg() and (option.getArgName() is None or len(option.getArgName()) != 0):
            buff.write(self.__longOptSeparator if option.getOpt() is None else " ")
            buff.write("<")
            buff.write(option.getArgName() if option.getArgName() is not None else self.getArgName())
            buff.write(">")

        if not required:
            buff.write("]")

    # Class Methods End
