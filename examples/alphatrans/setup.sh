#!/usr/bin/env bash
# Materialize AlphaTrans subject project(s) for CodeWeaver. POSIX equivalent of
# setup.ps1 -- see that file for the full rationale.
#
#   ./setup.sh commons-cli [/path/to/AlphaTrans]
#   ./setup.sh --all       [/path/to/AlphaTrans]
#
# Only these four AlphaTrans subjects ship a manually verified Python translation,
# and therefore a trustworthy fixed oracle:
#   commons-cli, commons-csv, commons-fileupload, commons-validator
# Set SKIP_BASELINE=1 to skip the golden-baseline recording pass.
set -euo pipefail

SUBJECTS="commons-cli commons-csv commons-fileupload commons-validator"

ARG="${1:-}"
DATASET="${2:-$HOME/AlphaTrans}"
[ -n "$ARG" ] || { echo "usage: $0 <project|--all> [dataset-root]" >&2; exit 2; }

if [ "$ARG" = "--all" ]; then
  TARGETS="$SUBJECTS"
else
  case " $SUBJECTS " in
    *" $ARG "*) TARGETS="$ARG" ;;
    *) echo "unknown project '$ARG'. Available: $SUBJECTS" >&2; exit 2 ;;
  esac
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET_ABS="$(cd "$DATASET" && pwd)"

echo "[setup] dataset: $DATASET_ABS"
echo

for PROJECT in $TARGETS; do
  JAVA_SRC="$DATASET_ABS/java_projects/cleaned_final_projects_decomposed_tests/$PROJECT/src/main"
  SKELETON="$DATASET_ABS/data/skeletons/$PROJECT/src/main"
  ORACLE="$DATASET_ABS/data/manually_verified_translations/$PROJECT/manual_translation"

  [ -d "$JAVA_SRC" ] || { echo "[$PROJECT] Java source not found: $JAVA_SRC" >&2; exit 1; }
  [ -d "$SKELETON" ] || { echo "[$PROJECT] Skeleton not found: $SKELETON" >&2; exit 1; }
  [ -d "$ORACLE/src/test" ] || { echo "[$PROJECT] Oracle tests not found: $ORACLE/src/test" >&2; exit 1; }

  SUBJECT="$HERE/subjects/$PROJECT"
  mkdir -p "$SUBJECT"

  # .scaffold = the interface skeleton (src/main ONLY; the skeleton's src/test is
  # dropped deliberately -- its test method names would leak the oracle's surface).
  SCAFFOLD="$SUBJECT/.scaffold"
  rm -rf "$SCAFFOLD"; mkdir -p "$SCAFFOLD/src"
  cp -r "$SKELETON" "$SCAFFOLD/src/main"
  : > "$SCAFFOLD/src/__init__.py"
  [ -f "$SCAFFOLD/src/main/__init__.py" ] || : > "$SCAFFOLD/src/main/__init__.py"

  # .oracle-master = pristine oracle + pytest harness + SHA256 manifest.
  ORACLE_MASTER="$SUBJECT/.oracle-master"
  rm -rf "$ORACLE_MASTER"; mkdir -p "$ORACLE_MASTER"
  cp -r "$ORACLE/src/test" "$ORACLE_MASTER/test"
  for f in pytest.ini conftest.py; do
    [ -f "$ORACLE/$f" ] && cp "$ORACLE/$f" "$ORACLE_MASTER/$f"
  done
  ( cd "$ORACLE_MASTER" && find . -type f ! -name SHA256SUMS.txt ! -name baseline_excluded.txt -print0 \
      | sort -z | xargs -0 sha256sum > SHA256SUMS.txt )

  # codeweaver.toml. The template wraps __VALIDATE_CMD__ in a TOML literal string,
  # so the embedded double quotes need no escaping.
  VALIDATE="bash ../../tools/oracle.sh --project $PROJECT --gate \"{gate}\""
  sed -e "s|__PROJECT__|$PROJECT|g" \
      -e "s|__PROJECT_SLUG__|$PROJECT|g" \
      -e "s|__JAVA_SRC_ABS__|$JAVA_SRC|g" \
      -e "s|__DATASET_ROOT__|$DATASET_ABS|g" \
      -e "s|__VALIDATE_CMD__|$VALIDATE|g" \
      "$HERE/codeweaver.template.toml" > "$SUBJECT/codeweaver.toml"

  rm -rf "$SUBJECT/pipeline"

  # Record the environment-broken baseline (tests that fail against the golden
  # translation too -- locale/timezone/platform, not the translation under test).
  if [ "${SKIP_BASELINE:-0}" != "1" ]; then
    echo "[$PROJECT] recording environment-broken baseline..."
    bash "$HERE/tools/oracle.sh" --project "$PROJECT" --baseline golden --all --record-exclusions >/dev/null 2>&1 || true
  fi

  N_JAVA=$(find "$JAVA_SRC" -name '*.java' | wc -l | tr -d ' ')
  N_IFACE=$(find "$SCAFFOLD/src/main" -name '*.py' ! -name '__init__.py' | wc -l | tr -d ' ')
  N_ORACLE=$(find "$ORACLE_MASTER/test" -name '*.py' ! -name '__init__.py' | wc -l | tr -d ' ')
  N_EXCL=0
  [ -f "$ORACLE_MASTER/baseline_excluded.txt" ] && \
    N_EXCL=$(grep -vc '^#' "$ORACLE_MASTER/baseline_excluded.txt" 2>/dev/null || echo 0)

  printf '%-20s java:%4s  iface:%4s  oracle-mods:%4s  env-broken:%3s\n' \
    "$PROJECT" "$N_JAVA" "$N_IFACE" "$N_ORACLE" "$N_EXCL"
done

echo
echo "Next:"
echo "  bash examples/alphatrans/tools/smoke_all.sh          # offline mock smoke test, all subjects (free)"
echo "  bash examples/alphatrans/tools/oracle.sh --project commons-cli --baseline golden --all"
