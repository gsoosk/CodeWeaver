"""build_check for the AlphaTrans Java->Python example.

The Python analogue of "does it compile". Two passes over the working copy's
`src/main`:

  1. syntax  -- every module must parse (`ast.parse`).
  2. import  -- every module must import cleanly with the working copy on sys.path.

Import errors are what actually break the oracle run (the tests do
`from src.main.<pkg>.<Mod> import *`), so catching them here gives the Translator a
fast, oracle-free signal.

Invoked as `python ../../tools/build_check.py` from a subject directory, so the
working copy is resolved from the CURRENT WORKING DIRECTORY, not from this file's
location. Pass an explicit subject directory as argv[1] to override.

Exit 0 when every module parses and imports; exit 1 otherwise, printing one line
per failure.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import sys
import traceback


def main() -> int:
    subject = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
    working_copy = subject / "pipeline" / "project"
    src_main = working_copy / "src" / "main"

    if not src_main.is_dir():
        print(f"build_check: no working copy at {src_main}", file=sys.stderr)
        return 1

    modules = sorted(p for p in src_main.rglob("*.py") if p.name != "__init__.py")
    if not modules:
        print(f"build_check: no modules under {src_main}", file=sys.stderr)
        return 1

    syntax_errors: list[str] = []
    for path in modules:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            rel = path.relative_to(working_copy)
            syntax_errors.append(f"SYNTAX  {rel}:{exc.lineno}: {exc.msg}")

    if syntax_errors:
        for line in syntax_errors:
            print(line)
        print(f"build_check: FAILED ({len(syntax_errors)} syntax error(s))")
        return 1

    sys.path.insert(0, str(working_copy))
    import_errors: list[str] = []
    for path in modules:
        dotted = ".".join(path.relative_to(working_copy).with_suffix("").parts)
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
