"""Command dispatcher for the related-paper reproduction harness."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from . import actor_li, analysis, citation_report, evaluate, package, prepare, report

COMMANDS: dict[str, tuple[str, Callable[[list[str] | None], int]]] = {
    "analyze": ("derive static Clippy measurements", analysis.main),
    "actor-li": ("run the ACToR absolute-micro campaign", actor_li.main),
    "citations": ("build the citation-complete artifact", citation_report.main),
    "prepare": ("prepare leakage-safe benchmark workspaces", prepare.main),
    "evaluate": ("independently evaluate generated translations", evaluate.main),
    "report": ("render the five publication artifacts", report.main),
    "package": ("archive raw runs and verify result artifacts", package.main),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=sorted(COMMANDS))
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        parser = build_parser()
        parser.print_help()
        print("\ncommands:")
        for command, (description, _) in COMMANDS.items():
            print(f"  {command:<10} {description}")
        return 0
    command = arguments.pop(0)
    if command not in COMMANDS:
        build_parser().error(f"invalid command: {command}")
    return COMMANDS[command][1](arguments)


if __name__ == "__main__":
    raise SystemExit(main())
