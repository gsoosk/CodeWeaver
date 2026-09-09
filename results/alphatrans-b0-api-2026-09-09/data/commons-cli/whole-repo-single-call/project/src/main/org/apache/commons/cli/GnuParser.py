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
        arguments: typing.List[str],
        stopAtNonOption: bool,
    ) -> typing.List[str]:
        tokens: typing.List[str] = []

        eatTheRest = False

        i = 0
        n = len(arguments)
        while i < n:
            arg = arguments[i]

            if arg == "--":
                eatTheRest = True
                tokens.append("--")
            elif arg == "-":
                tokens.append("-")
            elif arg.startswith("-"):
                opt = Util.stripLeadingHyphens(arg)

                eq = opt.find("=")
                if options.hasOption(opt):
                    tokens.append(arg)
                elif eq != -1 and options.hasOption(opt[:eq]):
                    aeq = arg.find("=")
                    tokens.append(arg[:aeq])
                    tokens.append(arg[aeq + 1 :])
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
                while i < n:
                    tokens.append(arguments[i])
                    i += 1
            else:
                i += 1

        return tokens

    # Class Methods End
