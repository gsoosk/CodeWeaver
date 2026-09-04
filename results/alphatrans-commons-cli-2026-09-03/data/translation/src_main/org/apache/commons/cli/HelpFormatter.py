from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.Options import *
from src.main.org.apache.commons.cli.OptionGroup import *
from src.main.org.apache.commons.cli.Option import *
import os
import sys
import functools
import typing
from typing import *
import io
from io import StringIO
from io import IOBase

# Imports End


def _compare_to_ignore_case(s1: str, s2: str) -> int:
    """Faithful port of Java ``String.compareToIgnoreCase``.

    Returns the first non-zero difference of case-folded characters, else the
    length difference. Preserves Java's exact integer contract for ASCII keys.
    """
    n1 = len(s1)
    n2 = len(s2)
    min_ = n1 if n1 < n2 else n2
    for i in range(min_):
        c1 = s1[i]
        c2 = s2[i]
        if c1 != c2:
            u1 = c1.upper()
            u2 = c2.upper()
            if u1 != u2:
                l1 = u1.lower()
                l2 = u2.lower()
                if l1 != l2:
                    return ord(l1) - ord(l2)
    return n1 - n2


class OptionComparator:

    # Class Fields Begin
    __serialVersionUID: int = 5305467873966684014
    # Class Fields End

    # Class Methods Begin
    def compare(self, opt1: Option, opt2: Option) -> int:
        return _compare_to_ignore_case(opt1.getKey(), opt2.getKey())

    def __call__(self, opt1: Option, opt2: Option) -> int:
        return self.compare(opt1, opt2)

    # Class Methods End


class HelpFormatter:

    # Class Fields Begin
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
    DEFAULT_WIDTH: int = 74
    DEFAULT_LEFT_PAD: int = 1
    DEFAULT_DESC_PAD: int = 3
    DEFAULT_SYNTAX_PREFIX: str = "usage: "
    DEFAULT_OPT_PREFIX: str = "-"
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

        return s[0:pos]

    def _renderWrappedText(
        self, sb: io.StringIO, width: int, nextLineTabStop: int, text: str
    ) -> io.StringIO:
        pos = self._findWrapPos(text, width, 0)

        if pos == -1:
            sb.write(self._rtrim(text))

            return sb
        sb.write(self._rtrim(text[0:pos]) + self.getNewLine())

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

            sb.write(self._rtrim(text[0:pos]) + self.getNewLine())

    def _renderOptions(
        self, sb: io.StringIO, width: int, options: Options, leftPad: int, descPad: int
    ) -> io.StringIO:
        lpad = self._createPadding(leftPad)
        dpad = self._createPadding(descPad)

        max_ = 0
        prefixList = []

        optList = options.helpOptions()

        if self.getOptionComparator() is not None:
            optList.sort(key=functools.cmp_to_key(self.getOptionComparator()))

        for option in optList:
            optBuf = ""

            if option.getOpt() is None:
                optBuf += (
                    lpad + "   " + self.getLongOptPrefix() + option.getLongOpt()
                )
            else:
                optBuf += lpad + self.getOptPrefix() + option.getOpt()

                if option.hasLongOpt():
                    optBuf += "," + self.getLongOptPrefix() + option.getLongOpt()

            if option.hasArg():
                argName = option.getArgName()
                if argName is not None and len(argName) == 0:
                    optBuf += " "
                else:
                    optBuf += (
                        self.__longOptSeparator if option.hasLongOpt() else " "
                    )
                    optBuf += (
                        "<"
                        + (option.getArgName() if argName is not None else self.getArgName())
                        + ">"
                    )

            prefixList.append(optBuf)
            max_ = len(optBuf) if len(optBuf) > max_ else max_

        x = 0

        count = len(optList)
        for i in range(count):
            option = optList[i]
            optBuf = prefixList[x]
            x += 1

            if len(optBuf) < max_:
                optBuf += self._createPadding(max_ - len(optBuf))

            optBuf += dpad

            nextLineTabStop = max_ + descPad

            if option.getDescription() is not None:
                optBuf += option.getDescription()

            self._renderWrappedText(sb, width, nextLineTabStop, optBuf)

            if i < count - 1:
                sb.write(self.getNewLine())

        return sb

    def printWrapped1(
        self, pw: typing.Union[io.TextIOWrapper, io.StringIO], width: int, text: str
    ) -> None:
        self.printWrapped0(pw, width, 0, text)

    def printWrapped0(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        nextLineTabStop: int,
        text: str,
    ) -> None:
        sb = io.StringIO()

        self.__renderWrappedTextBlock(sb, width, nextLineTabStop, text)
        self.__writeLine(pw, sb.getvalue())

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

        processedGroups = []

        optList = list(options.getOptions())
        if self.getOptionComparator() is not None:
            optList.sort(key=functools.cmp_to_key(self.getOptionComparator()))

        count = len(optList)
        for i in range(count):
            option = optList[i]

            group = options.getOptionGroup(option)

            if group is not None:
                if group not in processedGroups:
                    processedGroups.append(group)

                    self.__appendOptionGroup(buff, group)

            else:
                self.__appendOption(buff, option, option.isRequired())

            if i < count - 1:
                buff.write(" ")

        text = buff.getvalue()
        self.printWrapped0(pw, width, text.find(" ") + 1, text)

    def printUsage0(
        self,
        pw: typing.Union[io.TextIOWrapper, io.StringIO],
        width: int,
        cmdLineSyntax: str,
    ) -> None:
        argPos = cmdLineSyntax.find(" ") + 1

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
        self.__writeLine(pw, sb.getvalue())

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

        if header is not None and len(header) != 0:
            self.printWrapped1(pw, width, header)

        self.printOptions(pw, width, options, leftPad, descPad)

        if footer is not None and len(footer) != 0:
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
        self.printHelp3(
            pw, width, cmdLineSyntax, header, options, leftPad, descPad, footer, False
        )

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
        pos = text.find("\n", startPos)
        if pos != -1 and pos <= width:
            return pos + 1

        pos = text.find("\t", startPos)
        if pos != -1 and pos <= width:
            return pos + 1

        if startPos + width >= len(text):
            return -1

        pos = startPos + width
        while pos >= startPos:
            c = text[pos]
            if c == " " or c == "\n" or c == "\r":
                break
            pos -= 1

        if pos > startPos:
            return pos

        pos = startPos + width

        return -1 if pos == len(text) else pos

    def _createPadding(self, len_: int) -> str:
        return " " * len_

    def __renderWrappedTextBlock(
        self, sb: io.StringIO, width: int, nextLineTabStop: int, text: str
    ) -> typing.Union[typing.List, io.TextIOBase]:
        try:
            firstLine = True
            for line in text.splitlines():
                if not firstLine:
                    sb.write(self.getNewLine())
                else:
                    firstLine = False
                self._renderWrappedText(sb, width, nextLineTabStop, line)
        except IOError:  # NOPMD
            pass

        return sb

    def __writeLine(
        self, pw: typing.Union[io.TextIOWrapper, io.StringIO], text: str
    ) -> None:
        """Emit ``text`` followed by the newline, mirroring ``PrintWriter.println``.

        A Java ``PrintWriter`` accepts characters and encodes to bytes internally,
        so it works whether it wraps a character sink (``StringWriter``) or a byte
        sink (``ByteArrayOutputStream``). Python text streams accept ``str`` while
        byte-oriented streams (``io.BytesIO``, files opened in binary mode) require
        ``bytes``; encode when the sink rejects ``str`` so both idioms behave like
        the Java original.
        """
        data = text + self.getNewLine()

        try:
            pw.write(data)
        except TypeError:
            pw.write(data.encode())

    def __appendOptionGroup(self, buff: io.StringIO, group: OptionGroup) -> None:
        if not group.isRequired():
            buff.write("[")

        optList = list(group.getOptions())
        if self.getOptionComparator() is not None:
            optList.sort(key=functools.cmp_to_key(self.getOptionComparator()))

        count = len(optList)
        for i in range(count):
            self.__appendOption(buff, optList[i], True)

            if i < count - 1:
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

        if option.hasArg() and (
            option.getArgName() is None or len(option.getArgName()) != 0
        ):
            buff.write(self.__longOptSeparator if option.getOpt() is None else " ")
            buff.write("<")
            buff.write(
                option.getArgName() if option.getArgName() is not None else self.getArgName()
            )
            buff.write(">")

        if not required:
            buff.write("]")

    # Class Methods End
