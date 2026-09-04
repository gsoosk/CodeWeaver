#!/usr/bin/env bash
# Run the AlphaTrans oracle (the human-written Python tests) against a translation.
# POSIX equivalent of tools/oracle.ps1 -- see that file for the full rationale.
#
#   ./tools/oracle.sh --project commons-cli
#   ./tools/oracle.sh --project commons-cli --gate "OptionTest CommandLineTest"
#   ./tools/oracle.sh --project commons-cli --all
#   ./tools/oracle.sh --project commons-cli --baseline golden --all
#   ./tools/oracle.sh --project commons-cli --baseline skeleton --all
#
# Exit codes: 0 pass, 1 test failure, 3 ORACLE-TAMPERED.
set -uo pipefail

PROJECT=""
GATE=""
BASELINE=""
ALL=0
RECORD_EXCLUSIONS=0
KEEP_STAGING=0
WORKING_COPY_REL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project)  PROJECT="${2:-}"; shift 2 ;;
    --gate)     GATE="${2:-}"; shift 2 ;;
    --baseline) BASELINE="${2:-}"; shift 2 ;;
    --all)      ALL=1; shift ;;
    --working-copy) WORKING_COPY_REL="${2:-}"; shift 2 ;;
    --record-exclusions) RECORD_EXCLUSIONS=1; shift ;;
    --keep-staging) KEEP_STAGING=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PROJECT" ] || { echo "usage: $0 --project <name> [--gate ...] [--all] [--baseline golden|skeleton] [--working-copy <rel>]" >&2; exit 2; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE="$(dirname "$HERE")"
SUBJECT="$EXAMPLE/subjects/$PROJECT"
ORACLE_MASTER="$SUBJECT/.oracle-master"
SCAFFOLD="$SUBJECT/.scaffold"
# --working-copy lets a BASELINE arm (single-shot, SWE-agent, ...) be scored by the
# identical oracle, e.g. --working-copy pipeline-baseline-20260904/project.
WORKING_COPY="$SUBJECT/${WORKING_COPY_REL:-pipeline/project}"
STAGING="$SUBJECT/pipeline/_oracle_run"

[ -d "$ORACLE_MASTER" ] || { echo "No .oracle-master for '$PROJECT'. Run setup.sh $PROJECT first." >&2; exit 1; }

# 1. Verify the oracle has not been modified.
if ! ( cd "$ORACLE_MASTER" && sha256sum --quiet -c SHA256SUMS.txt ) 2>/dev/null; then
  echo "ORACLE-TAMPERED [$PROJECT]: the fixed oracle no longer matches its manifest." >&2
  ( cd "$ORACLE_MASTER" && sha256sum -c SHA256SUMS.txt 2>&1 | grep -v ': OK$' || true ) >&2
  echo "Re-run setup.sh $PROJECT to restore, and treat this run as INVALID." >&2
  exit 3
fi

# 2. Pick the src/main to score.
case "$BASELINE" in
  golden)
    DS="$(sed -n 's/^#[[:space:]]*dataset_root[[:space:]]*=[[:space:]]*//p' "$SUBJECT/codeweaver.toml" | head -1)"
    SRC_MAIN="$DS/data/manually_verified_translations/$PROJECT/manual_translation/src/main" ;;
  skeleton) SRC_MAIN="$SCAFFOLD/src/main" ;;
  "")       SRC_MAIN="$WORKING_COPY/src/main" ;;
  *) echo "--baseline must be golden or skeleton" >&2; exit 2 ;;
esac
[ -d "$SRC_MAIN" ] || { echo "No translation to score at: $SRC_MAIN" >&2; exit 1; }

# 3. An empty gate means the milestone has no oracle obligation yet (typically M0).
if [ "$ALL" -eq 0 ] && [ -z "${GATE// /}" ]; then
  echo "[oracle] project  : $PROJECT"
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

# 5. Resolve each mechanical <Class>Test token to the EXACT oracle test file.
#    Never `pytest -k`: substring matching would let "OptionTest" also select
#    "ArgumentIsOptionTest", dragging a later milestone's tests into this gate.
SELECT=()
if [ -n "${GATE// /}" ]; then
  UNRESOLVED=""
  for tok in $(echo "$GATE" | tr ' ' '\n' | grep -vE '^(or|and|not)$' | sort -u); do
    [ -z "$tok" ] && continue
    hits="$(find "$STAGING/src/test" -type f -name "$tok.py" 2>/dev/null || true)"
    if [ -n "$hits" ]; then
      while IFS= read -r h; do SELECT+=("${h#$STAGING/}"); done <<< "$hits"
    else
      UNRESOLVED="$UNRESOLVED $tok"
    fi
  done
  [ -n "$UNRESOLVED" ] && echo "[oracle] note     : gate token(s) matched no oracle test file (no obligation):$UNRESOLVED"
  if [ ${#SELECT[@]} -eq 0 ]; then
    echo "[oracle] project  : $PROJECT"
    echo "[oracle] source   : $SRC_MAIN"
    echo "[oracle] gate     : $GATE"
    echo "[oracle] result   : gate selected no oracle tests -> no obligation for this milestone"
    echo "[oracle] exitcode : 0"
    [ "$KEEP_STAGING" -eq 1 ] || rm -rf "$STAGING"
    exit 0
  fi
fi

# 6. Deselect the environment-broken baseline and any skip-on-give-up deferrals.
EXCL_FILE="$ORACLE_MASTER/baseline_excluded.txt"
DESELECT=()
N_EXCL=0
if [ "$RECORD_EXCLUSIONS" -eq 0 ] && [ -f "$EXCL_FILE" ]; then
  while IFS= read -r line; do
    case "$line" in ''|\#*) continue ;; esac
    DESELECT+=(--deselect "$line"); N_EXCL=$((N_EXCL + 1))
  done < "$EXCL_FILE"
fi
SKIPS_FILE="$SUBJECT/pipeline/skips.json"
if [ "$RECORD_EXCLUSIONS" -eq 0 ] && [ -f "$SKIPS_FILE" ]; then
  while IFS= read -r nodeid; do
    [ -n "$nodeid" ] && DESELECT+=(--deselect "$nodeid")
  done < <(python3 -c "
import json
try:
    d=json.load(open('$SKIPS_FILE'))
    for t in d.get('tests_to_skip',[]):
        if '::' in str(t): print(t)
except Exception: pass
" 2>/dev/null)
fi

OUT="$(cd "$STAGING" && PYTHONPATH="$STAGING" python3 -m pytest "${SELECT[@]}" "${DESELECT[@]}" 2>&1)"
CODE=$?
echo "$OUT"

if [ "$RECORD_EXCLUSIONS" -eq 1 ]; then
  {
    echo "# Tests that FAIL or ERROR against AlphaTrans's own manually verified"
    echo "# translation in THIS environment. They measure the environment (locale,"
    echo "# timezone, platform), not the translation under test, so every scored run"
    echo "# deselects them. Excluded from the tamper manifest by design."
    echo "# Subject: $PROJECT    Recorded: $(date -Is)"
    echo "$OUT" | grep -E '^(FAILED|ERROR) ' | awk '{print $2}' | grep '::' | sort -u
  } > "$EXCL_FILE"
  echo "[oracle] recorded $(grep -vc '^#' "$EXCL_FILE" || true) environment-broken test(s) -> $EXCL_FILE"
fi

# pytest exit 5 = "no tests were collected" -> a mechanical token matched nothing.
[ "$CODE" -eq 5 ] && CODE=0

SUMMARY="$(echo "$OUT" | grep -E '[0-9]+ (passed|failed|error|deselected)|no tests ran' | tail -1 | tr -s ' =')"
echo
echo "[oracle] project  : $PROJECT"
echo "[oracle] source   : $SRC_MAIN"
echo "[oracle] gate     : ${GATE:-(whole suite)}"
[ "$N_EXCL" -gt 0 ] && echo "[oracle] excluded : $N_EXCL environment-broken test(s)"
echo "[oracle] result   : $SUMMARY"
echo "[oracle] exitcode : $CODE"

[ "$KEEP_STAGING" -eq 1 ] || rm -rf "$STAGING"
exit $CODE
