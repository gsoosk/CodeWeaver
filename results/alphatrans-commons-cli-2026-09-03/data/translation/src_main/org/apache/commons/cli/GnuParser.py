from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.cli.Util import *
from src.main.org.apache.commons.cli.Parser import *
from src.main.org.apache.commons.cli.Options import *
import typing
from typing import *
import io

# Imports End


class GnuParser(Parser):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def _flatten(
        self,
        options: Options,
        arguments: typing.List[typing.List[str]],
        stopAtNonOption: bool,
    ) -> typing.List[typing.List[str]]:
        tokens = []

        eatTheRest = False

        i = 0
        while i < len(arguments):
            arg = arguments[i]

            if arg == "--":
                eatTheRest = True
                tokens.append("--")
            elif arg == "-":
                tokens.append("-")
            elif arg.startswith("-"):
                opt = Util.stripLeadingHyphens(arg)

                if options.hasOption(opt):
                    tokens.append(arg)
                elif opt.find("=") != -1 and options.hasOption(
                    opt[0 : opt.find("=")]
                ):
                    tokens.append(arg[0 : arg.find("=")])
                    tokens.append(arg[arg.find("=") + 1 :])
                elif options.hasOption(arg[0:2]):
                    tokens.append(arg[0:2])
                    tokens.append(arg[2:])
                else:
                    eatTheRest = stopAtNonOption
                    tokens.append(arg)
            else:
                tokens.append(arg)

            if eatTheRest:
                i += 1
                while i < len(arguments):
                    tokens.append(arguments[i])
                    i += 1

            i += 1

        return list(tokens)

    # Class Methods End
