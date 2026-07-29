#!/usr/bin/env bash
# Prepare the CodeWeaver CRUST-Bench example for a chosen benchmark project.
#
# CRUST-Bench (arXiv:2504.15254) ships 100 C projects, each paired with a Rust
# interface + tests under datasets/RBench/<project> and C source under
# datasets/CBench/<project>. This targets ONE project: copies a clean scaffold
# (the RBench crate, minus .git/target) to .scaffold/, and generates
# codeweaver.toml from codeweaver.template.toml with resolved paths.
#
# Usage:
#   ./setup.sh <project> [dataset_dir]
#   ./setup.sh bitset
#   ./setup.sh lambda-calculus-eval /data/CRUST-bench/datasets
#
# Prereqs: rust/cargo on PATH; the CRUST-Bench dataset extracted so that
# <dataset>/CBench and <dataset>/RBench exist (datasets/CRUST_bench.zip from
# https://github.com/anirudhkhatry/CRUST-bench).
set -euo pipefail

PROJECT="${1:?usage: setup.sh <project> [dataset_dir]}"
DATASET="${2:-$HOME/Desktop/_cw_local/CRUST-bench/datasets}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CBENCH="$DATASET/CBench/$PROJECT"
RBENCH="$DATASET/RBench/$PROJECT"
IFACE="$RBENCH/src/interfaces"
TESTS="$RBENCH/src/bin"
[ -d "$CBENCH" ] || { echo "C source not found: $CBENCH" >&2; exit 1; }
[ -d "$RBENCH" ] || { echo "Rust scaffold not found: $RBENCH" >&2; exit 1; }
[ -d "$IFACE" ]  || { echo "No interfaces dir: $IFACE" >&2; exit 1; }

# 1. Clean scaffold copy.
SCAFFOLD="$HERE/.scaffold"
rm -rf "$SCAFFOLD"
cp -r "$RBENCH" "$SCAFFOLD"
rm -rf "$SCAFFOLD/.git" "$SCAFFOLD/target"

# 2. Generate codeweaver.toml from the template.
python3 - "$HERE" "$PROJECT" "$CBENCH" "$IFACE" "$TESTS" <<'PY'
import sys, pathlib
here, project, csrc, iface, tests = sys.argv[1:6]
tpl = (pathlib.Path(here) / "codeweaver.template.toml").read_text(encoding="utf-8")
tpl = (tpl.replace("__PROJECT__", project)
          .replace("__C_SOURCE_ABS__", csrc)
          .replace("__IFACE_ABS__", iface)
          .replace("__TESTS_ABS__", tests))
(pathlib.Path(here) / "codeweaver.toml").write_text(tpl, encoding="utf-8")
PY

# 3. Clear stale run state.
rm -rf "$HERE/pipeline"

echo "[setup] target project : $PROJECT"
echo "[setup] scaffold        : $SCAFFOLD (clean copy of the RBench crate)"
echo "[setup] wrote           : $HERE/codeweaver.toml"
echo
echo "Next:"
echo "  python -m codeweaver run --config examples/crust-bench/codeweaver.toml --app-id crust-$PROJECT-001"
