from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.Options import *
from src.main.org.apache.commons.cli.Option import *
import urllib
import urllib.parse
from datetime import datetime, date
import typing
from typing import *
import numbers
import io
import pathlib

# Imports End


class PatternOptionBuilder:

    # Class Fields Begin
    STRING_VALUE: typing.Type[str] = str
    OBJECT_VALUE: typing.Type[typing.Any] = object
    NUMBER_VALUE: typing.Type[typing.Union[int, float, numbers.Number]] = numbers.Number
    DATE_VALUE: typing.Type[typing.Union[datetime.date, datetime.datetime]] = date
    CLASS_VALUE: typing.Type[typing.Any] = type
    EXISTING_FILE_VALUE: typing.Type[
        typing.Union[io.FileIO, io.BufferedReader, io.TextIOWrapper]
    ] = io.TextIOWrapper
    FILE_VALUE: typing.Type[pathlib.Path] = pathlib.Path
    FILES_VALUE: typing.Type[typing.List[pathlib.Path]] = list
    URL_VALUE: typing.Type[
        typing.Union[
            urllib.parse.ParseResult,
            urllib.parse.SplitResult,
            urllib.parse.DefragResult,
            str,
        ]
    ] = urllib.parse.ParseResult
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def parsePattern(pattern: str) -> Options:
        opt = ' '
        required = False
        type_ = None

        options = Options()

        for ch in pattern:
            if not PatternOptionBuilder.isValueCode(ch):
                if opt != ' ':
                    option = (
                        Option.builder1(str(opt))
                        .hasArg1(type_ is not None)
                        .required1(required)
                        .type_(type_)
                        .build()
                    )

                    options.addOption0(option)
                    required = False
                    type_ = None
                    opt = ' '

                opt = ch
            elif ch == '!':
                required = True
            else:
                type_ = PatternOptionBuilder.getValueClass(ch)

        if opt != ' ':
            option = (
                Option.builder1(str(opt))
                .hasArg1(type_ is not None)
                .required1(required)
                .type_(type_)
                .build()
            )

            options.addOption0(option)

        return options

    @staticmethod
    def isValueCode(ch: str) -> bool:
        return (
            ch == '@'
            or ch == ':'
            or ch == '%'
            or ch == '+'
            or ch == '#'
            or ch == '<'
            or ch == '>'
            or ch == '*'
            or ch == '/'
            or ch == '!'
        )

    @staticmethod
    def getValueClass(ch: str) -> typing.Any:
        if ch == '@':
            return PatternOptionBuilder.OBJECT_VALUE
        elif ch == ':':
            return PatternOptionBuilder.STRING_VALUE
        elif ch == '%':
            return PatternOptionBuilder.NUMBER_VALUE
        elif ch == '+':
            return PatternOptionBuilder.CLASS_VALUE
        elif ch == '#':
            return PatternOptionBuilder.DATE_VALUE
        elif ch == '<':
            return PatternOptionBuilder.EXISTING_FILE_VALUE
        elif ch == '>':
            return PatternOptionBuilder.FILE_VALUE
        elif ch == '*':
            return PatternOptionBuilder.FILES_VALUE
        elif ch == '/':
            return PatternOptionBuilder.URL_VALUE

        return None

    # Class Methods End
