#!/usr/bin/env bash
# Run the AlphaTrans oracle (the human-written Python tests) against a translation.
# POSIX equivalent of tools/oracle.ps1 -- see that file for the full rationale.
#
#   ./tools/oracle.sh                       # score the working copy, whole suite gate rules apply
#   ./tools/oracle.sh --gate "OptionTest"   # milestone gate (pytest -k)
#   ./tools/oracle.sh --all                 # force the whole suite (final scoring)
#   ./tools/oracle.sh --baseline golden     # ceiling: AlphaTrans's manual translation
#   ./tools/oracle.sh --baseline skeleton   # floor:   the unimplemented interface
#
# Exit codes: 0 pass, 1 test failure, 3 ORACLE-TAMPERED.
set -uo pipefail

GATE=""
BASELINE=""
ALL=0
RECORD_EXCLUSIONS=0
KEEP_STAGING=0
while [ $# -gt 0 ]; do
  case "$1" in
    --gate)     GATE="${2:-}"; shift 2 ;;
    --baseline) BASELINE="${2:-}"; shift 2 ;;
    --all)      ALL=1; shift ;;
    --record-exclusions) RECORD_EXCLUSIONS=1; shift ;;
    --keep-staging) KEEP_STAGING=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE="$(dirname "$HERE")"
ORACLE_MASTER="$EXAMPLE/.oracle-master"
SCAFFOLD="$EXAMPLE/.scaffold"
WORKING_COPY="$EXAMPLE/pipeline/project"
STAGING="$EXAMPLE/pipeline/_oracle_run"

[ -d "$ORACLE_MASTER" ] || { echo "No .oracle-master. Run setup.sh first." >&2; exit 1; }

# 1. Verify the oracle has not been modified.
if ! ( cd "$ORACLE_MASTER" && sha256sum --quiet -c SHA256SUMS.txt ) 2>/dev/null; then
  echo "ORACLE-TAMPERED: the fixed oracle no longer matches its manifest." >&2
  ( cd "$ORACLE_MASTER" && sha256sum -c SHA256SUMS.txt 2>&1 | grep -v ': OK$' || true ) >&2
  echo "Re-run setup.sh to restore, and treat this run as INVALID." >&2
  exit 3
fi

# 2. Pick the src/main to score.
case "$BASELINE" in
  golden)
    DS="$(sed -n 's/^#[[:space:]]*dataset_root[[:space:]]*=[[:space:]]*//p' "$EXAMPLE/codeweaver.toml" | head -1)"
    PROJ="$(sed -n 's/^name[[:space:]]*=[[:space:]]*"alphatrans-\(.*\)"/\1/p' "$EXAMPLE/codeweaver.toml" | head -1)"
    SRC_MAIN="$DS/data/manually_verified_translations/$PROJ/manual_translation/src/main" ;;
  skeleton) SRC_MAIN="$SCAFFOLD/src/main" ;;
  "")       SRC_MAIN="$WORKING_COPY/src/main" ;;
  *) echo "--baseline must be golden or skeleton" >&2; exit 2 ;;
esac
[ -d "$SRC_MAIN" ] || { echo "No translation to score at: $SRC_MAIN" >&2; exit 1; }

# 3. An empty gate means the milestone has no oracle obligation yet (typically M0).
if [ "$ALL" -eq 0 ] && [ -z "${GATE// /}" ]; then
  echo "[oracle] source   : $SRC_MAIN"
  echo "[oracle] gate     : (empty - milestone selects no oracle tests)"
  echo "[oracle] result   : skipped; no oracle obligation for this milestone"
  echo "[oracle] exitcode : 0"
  exit 0
fi

# 4. Stage: translation + pristine oracle, in a throwaway tree.
rm -rf "$STAGING"
mkdir -p "$STAGING/src"
cp -r "$SRC_MAIN" "$STAGING/src/main"
cp -r "$ORACLE_MASTER/test" "$STAGING/src/test"
for f in pytest.ini conftest.py; do
  [ -f "$ORACLE_MASTER/$f" ] && cp "$ORACLE_MASTER/$f" "$STAGING/$f"
done
for pkg in "$STAGING/src" "$STAGING/src/main" "$STAGING/src/test"; do
  [ -f "$pkg/__init__.py" ] || : > "$pkg/__init__.py"
done

# 5. Run pytest. Deselect the environment-broken baseline (tests that fail against
#    the golden translation too), unless we are recording that baseline right now.
EXCL_FILE="$ORACLE_MASTER/baseline_excluded.txt"
DESELECT=()
N_EXCL=0
if [ "$RECORD_EXCLUSIONS" -eq 0 ] && [ -f "$EXCL_FILE" ]; then
  while IFS= read -r line; do
    case "$line" in ''|\#*) continue ;; esac
    DESELECT+=(--deselect "$line")
    N_EXCL=$((N_EXCL + 1))
  done < "$EXCL_FILE"
fi

OUT="$(cd "$STAGING" && PYTHONPATH="$STAGING" python3 -m pytest ${GATE:+-k "$GATE"} "${DESELECT[@]}" 2>&1)"
CODE=$?
echo "$OUT"

if [ "$RECORD_EXCLUSIONS" -eq 1 ]; then
  {
    echo "# Tests that FAIL or ERROR against AlphaTrans's own manually verified"
    echo "# translation in THIS environment. They measure the environment (locale,"
    echo "# timezone, platform), not the translation under test, so every scored run"
    echo "# deselects them. Excluded from the tamper manifest by design."
    echo "# Recorded: $(date -Is)"
    echo "$OUT" | grep -E '^(FAILED|ERROR) ' | awk '{print $2}' | grep '::' | sort -u
  } > "$EXCL_FILE"
  echo "[oracle] recorded $(grep -vc '^#' "$EXCL_FILE" || true) environment-broken test(s) -> $EXCL_FILE"
fi

# pytest exit 5 = "no tests were collected" -> the mechanical <Class>Test token
# matched nothing, which is "no obligation", not a failure.
[ "$CODE" -eq 5 ] && CODE=0

SUMMARY="$(echo "$OUT" | grep -E '[0-9]+ (passed|failed|error|deselected)' | tail -1 | tr -s ' =')"
echo
echo "[oracle] source   : $SRC_MAIN"
echo "[oracle] gate     : ${GATE:-(whole suite)}"
[ "$N_EXCL" -gt 0 ] && echo "[oracle] excluded : $N_EXCL environment-broken test(s)"
echo "[oracle] result   : $SUMMARY"
echo "[oracle] exitcode : $CODE"

[ "$KEEP_STAGING" -eq 1 ] || rm -rf "$STAGING"
exit $CODE
