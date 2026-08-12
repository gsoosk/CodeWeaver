"""Command-line entry point for the EvoC2Rust comparison harness."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from experiments.evoc2rust import evaluate, package, prepare, report
from experiments.evoc2rust.config import load_config
from experiments.recodeagent import run

DEFAULT_EXPERIMENT = Path(__file__).with_name("experiment.toml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m experiments.evoc2rust")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-config", help="validate frozen subjects.json")
    subparsers.add_parser("prepare", help="prepare and calibrate safe workspaces")
    subparsers.add_parser("run", help="run the resumable CodeWeaver matrix")
    subparsers.add_parser("evaluate", help="independently evaluate terminal runs")
    subparsers.add_parser("report", help="render tables, figures, and report")
    subparsers.add_parser("package", help="build a checksummed result package")
    return parser


def main(argv: list[str] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if not tokens or tokens[0] in {"-h", "--help"}:
        build_parser().print_help()
        return 0
    command = tokens[0]
    if command == "validate-config":
        config = load_config()
        print(
            f"valid EvoC2Rust config: {len(config['subjects'])} groups, "
            "19 modules, 125 active tests"
        )
        return 0
    if command == "prepare":
        return prepare.main(tokens[1:])
    if command == "run":
        arguments = tokens[1:]
        if "--config" not in arguments:
            arguments = [
                "--config",
                str(DEFAULT_EXPERIMENT),
                *arguments,
            ]
        return run.main(arguments)
    if command == "evaluate":
        return evaluate.main(tokens[1:])
    if command == "report":
        return report.main(tokens[1:])
    if command == "package":
        return package.main(tokens[1:])
    build_parser().error(f"unknown command: {command}")
    return 2
