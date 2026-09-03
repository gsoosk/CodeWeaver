"""build_check for the AlphaTrans Java->Python example.

The Python analogue of "does it compile". Two passes over the working copy's
`src/main`:

  1. syntax  -- every module must parse (`ast.parse`).
  2. import  -- every module must import cleanly with the working copy on sys.path.

Import errors are what actually break the oracle run (the tests do
`from src.main.<pkg>.<Mod> import *`), so catching them here gives the Translator a
fast, oracle-free signal.

Exit 0 when every module parses and imports; exit 1 otherwise, printing one line
per failure.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
WORKING_COPY = EXAMPLE / "pipeline" / "project"
SRC_MAIN = WORKING_COPY / "src" / "main"


def main() -> int:
    if not SRC_MAIN.is_dir():
        print(f"build_check: no working copy at {SRC_MAIN}", file=sys.stderr)
        return 1

    modules = sorted(p for p in SRC_MAIN.rglob("*.py") if p.name != "__init__.py")
    if not modules:
        print(f"build_check: no modules under {SRC_MAIN}", file=sys.stderr)
        return 1

    syntax_errors: list[str] = []
    for path in modules:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            rel = path.relative_to(WORKING_COPY)
            syntax_errors.append(f"SYNTAX  {rel}:{exc.lineno}: {exc.msg}")

    if syntax_errors:
        for line in syntax_errors:
            print(line)
        print(f"build_check: FAILED ({len(syntax_errors)} syntax error(s))")
        return 1

    sys.path.insert(0, str(WORKING_COPY))
    import_errors: list[str] = []
    for path in modules:
        dotted = ".".join(path.relative_to(WORKING_COPY).with_suffix("").parts)
        try:
            importlib.import_module(dotted)
        except Exception as exc:
            tb = traceback.extract_tb(sys.exc_info()[2])
            where = f":{tb[-1].lineno}" if tb else ""
            import_errors.append(f"IMPORT  {dotted}{where}: {type(exc).__name__}: {exc}")

    for line in import_errors:
        print(line)

    ok = len(modules) - len(import_errors)
    print(f"build_check: {ok}/{len(modules)} modules parse and import")
    return 1 if import_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
