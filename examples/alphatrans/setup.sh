#!/usr/bin/env bash
# Prepare the CodeWeaver AlphaTrans (Java -> Python) example for one subject project.
# See setup.ps1 for the full rationale; this is the POSIX equivalent.
#
#   ./setup.sh commons-cli [/path/to/AlphaTrans]
#
# Only these four projects ship a manually verified oracle:
#   commons-cli, commons-csv, commons-fileupload, commons-validator
set -euo pipefail

PROJECT="${1:-}"
DATASET="${2:-$HOME/Desktop/AlphaTrans}"

case "$PROJECT" in
  commons-cli|commons-csv|commons-fileupload|commons-validator) ;;
  *)
    echo "usage: $0 <commons-cli|commons-csv|commons-fileupload|commons-validator> [dataset-root]" >&2
    exit 2 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

JAVA_SRC="$DATASET/java_projects/cleaned_final_projects_decomposed_tests/$PROJECT/src/main"
SKELETON="$DATASET/data/skeletons/$PROJECT/src/main"
ORACLE="$DATASET/data/manually_verified_translations/$PROJECT/manual_translation"

[ -d "$JAVA_SRC" ] || { echo "Java source not found: $JAVA_SRC" >&2; exit 1; }
[ -d "$SKELETON" ] || { echo "Skeleton (interface) not found: $SKELETON" >&2; exit 1; }
[ -d "$ORACLE/src/test" ] || { echo "Oracle tests not found: $ORACLE/src/test" >&2; exit 1; }

# 1. .scaffold/ = the interface skeleton (src/main ONLY; the skeleton's src/test is
#    dropped deliberately -- test method names would leak the oracle's surface).
SCAFFOLD="$HERE/.scaffold"
rm -rf "$SCAFFOLD"
mkdir -p "$SCAFFOLD/src"
cp -r "$SKELETON" "$SCAFFOLD/src/main"
: > "$SCAFFOLD/src/__init__.py"
[ -f "$SCAFFOLD/src/main/__init__.py" ] || : > "$SCAFFOLD/src/main/__init__.py"

# 2. .oracle-master/ = pristine oracle + pytest harness + SHA256 manifest.
ORACLE_MASTER="$HERE/.oracle-master"
rm -rf "$ORACLE_MASTER"
mkdir -p "$ORACLE_MASTER"
cp -r "$ORACLE/src/test" "$ORACLE_MASTER/test"
for f in pytest.ini conftest.py; do
  [ -f "$ORACLE/$f" ] && cp "$ORACLE/$f" "$ORACLE_MASTER/$f"
done
( cd "$ORACLE_MASTER" && find . -type f ! -name SHA256SUMS.txt ! -name baseline_excluded.txt -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS.txt )

# 3. Render codeweaver.toml.
DATASET_ABS="$(cd "$DATASET" && pwd)"
sed -e "s|__PROJECT__|$PROJECT|g" \
    -e "s|__PROJECT_SLUG__|$PROJECT|g" \
    -e "s|__JAVA_SRC_ABS__|$JAVA_SRC|g" \
    -e "s|__DATASET_ROOT__|$DATASET_ABS|g" \
    "$HERE/codeweaver.template.toml" > "$HERE/codeweaver.toml"

# 4. Clear stale run state.
rm -rf "$HERE/pipeline"

# 4b. Record the environment-broken baseline: tests that fail against AlphaTrans's
#     OWN manually verified translation are broken by this environment (locale,
#     timezone, platform), not by the translation under test. Every scored run
#     deselects them. Skip with SKIP_BASELINE=1.
if [ "${SKIP_BASELINE:-0}" != "1" ]; then
  echo "[setup] recording environment-broken baseline (running the golden translation)..."
  bash "$HERE/tools/oracle.sh" --baseline golden --all --record-exclusions >/dev/null 2>&1 || true
fi

N_JAVA=$(find "$JAVA_SRC" -name '*.java' | wc -l | tr -d ' ')
N_IFACE=$(find "$SCAFFOLD/src/main" -name '*.py' ! -name '__init__.py' | wc -l | tr -d ' ')
N_ORACLE=$(find "$ORACLE_MASTER/test" -name '*.py' ! -name '__init__.py' | wc -l | tr -d ' ')

echo "[setup] project          : $PROJECT"
echo "[setup] java source      : $JAVA_SRC  ($N_JAVA .java files)"
echo "[setup] interface        : $SCAFFOLD/src/main  ($N_IFACE modules, 'pass' bodies)"
echo "[setup] oracle (hidden)  : $ORACLE_MASTER  ($N_ORACLE test modules)"
echo "[setup] wrote            : $HERE/codeweaver.toml"
echo
echo "Next:"
echo "  bash examples/alphatrans/tools/oracle.sh --baseline golden"
echo "  bash examples/alphatrans/tools/oracle.sh --baseline skeleton"
echo "  python -m codeweaver check --config examples/alphatrans/codeweaver.toml"
