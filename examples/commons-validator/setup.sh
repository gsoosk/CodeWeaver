#!/usr/bin/env bash
# Prepare the CodeWeaver Apache Commons Validator (Java -> Python) example.
#
# Points the example at a local clone of https://github.com/apache/commons-validator
# and generates codeweaver.toml from codeweaver.template.toml with resolved paths to
# the `routines` package (Java source) and its JUnit tests (behavioral spec).
#
# Usage:
#   ./setup.sh [repo_dir]
#   ./setup.sh /src/commons-validator
#
# Prereqs: Python 3.11+ on PATH; a git clone of apache/commons-validator. No JDK is
# needed (the Java tests are translated into Python unittest, not executed).
set -euo pipefail

REPO="${1:-$HOME/Desktop/_cw_local/commons-validator}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MAIN="$REPO/src/main/java/org/apache/commons/validator/routines"
TEST="$REPO/src/test/java/org/apache/commons/validator/routines"
[ -d "$MAIN" ] || { echo "routines source not found: $MAIN (clone apache/commons-validator and pass the repo path)" >&2; exit 1; }
[ -d "$TEST" ] || { echo "routines tests not found: $TEST" >&2; exit 1; }

python3 - "$HERE" "$MAIN" "$TEST" <<'PY'
import sys, pathlib
here, main, test = sys.argv[1:4]
tpl = (pathlib.Path(here) / "codeweaver.template.toml").read_text(encoding="utf-8")
tpl = tpl.replace("__ROUTINES_MAIN__", main).replace("__ROUTINES_TEST__", test)
(pathlib.Path(here) / "codeweaver.toml").write_text(tpl, encoding="utf-8")
PY

rm -rf "$HERE/pipeline"

echo "[setup] commons-validator repo : $REPO"
echo "[setup] wrote                  : $HERE/codeweaver.toml"
echo
echo "Next (from the CodeWeaver repo root):"
echo "  python -m codeweaver run --config examples/commons-validator/codeweaver.toml --app-id commons-validator-001"
