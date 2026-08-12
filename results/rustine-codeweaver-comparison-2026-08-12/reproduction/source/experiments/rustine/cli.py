"""Command-line entry point for the Rustine comparison harness."""
from __future__ import annotations

import argparse
import sys

from experiments.rustine import evaluate, package, prepare, report
from experiments.rustine.config import load_subject_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m experiments.rustine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-config", help="strictly validate subjects.json")
    subparsers.add_parser("prepare", help="prepare leakage-safe workspaces")
    subparsers.add_parser("evaluate", help="evaluate existing run workspaces")
    subparsers.add_parser("report", help="render comparison reports")
    subparsers.add_parser("package", help="build a checksummed publication package")
    return parser


def main(argv: list[str] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if not tokens or tokens[0] in {"-h", "--help"}:
        build_parser().print_help()
        return 0
    command = tokens[0]
    if command == "validate-config":
        config = load_subject_config()
        print(f"valid Rustine config: {len(config['subjects'])} subjects")
        return 0
    if command == "prepare":
        return prepare.main(tokens[1:])
    if command == "evaluate":
        return evaluate.main(tokens[1:])
    if command == "report":
        return report.main(tokens[1:])
    if command == "package":
        return package.main(tokens[1:])
    build_parser().error(f"unknown command: {command}")
    return 2
