#!/usr/bin/env bash
# Run the held-out CRUST oracle against a translation.
#
#   bash tools/oracle.sh --project cset [--working-copy <rel>] [--json]
#
# Mirrors examples/alphatrans/tools/oracle.sh: the translation is copied into a
# throwaway tree, the pristine tests are staged beside it, and cargo test runs
# there. The working copy is never modified and never sees the tests.
#
# `cargo test` here is a genuinely stronger gate than the Python oracle: the
# translation must COMPILE before a single test runs. A Rust project that does
# not build scores zero, with no partial credit, which is why build failure is
# reported as its own state rather than as "0 passed".
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"

PROJECT=""
WORKING_COPY_REL=""
JSON=0
KEEP_STAGING=0
TIMEOUT=1200
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --working-copy) WORKING_COPY_REL="$2"; shift 2 ;;
    --json) JSON=1; shift ;;
    --keep-staging) KEEP_STAGING=1; shift ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PROJECT" ] || { echo "usage: $0 --project <name>" >&2; exit 2; }

SUBJECT="$ROOT/subjects/$PROJECT"
[ -d "$SUBJECT" ] || { echo "subject not materialized: $SUBJECT" >&2; exit 2; }
ORACLE="$SUBJECT/.oracle-master"
[ -d "$ORACLE/bin" ] || { echo "no held-out tests at $ORACLE/bin" >&2; exit 2; }

REL="${WORKING_COPY_REL:-pipeline/project}"
SRC="$SUBJECT/$REL"
[ -d "$SRC/src" ] || { echo "no translation at $SRC/src" >&2; exit 2; }

STAGING="$(mktemp -d)"
cleanup() { [ "$KEEP_STAGING" -eq 1 ] || rm -rf "$STAGING"; }
trap cleanup EXIT

# Stage the translation, then overwrite the manifest and restore the tests.
# Order matters: the oracle manifest wins, so a translation cannot disable a
# test target by editing its own Cargo.toml.
cp -r "$SRC/." "$STAGING/"
rm -rf "$STAGING/target" "$STAGING/src/bin"
cp "$ORACLE/Cargo.toml.oracle" "$STAGING/Cargo.toml"
cp -r "$ORACLE/bin" "$STAGING/src/bin"

BUILD_LOG="$STAGING/.build.log"
if ! ( cd "$STAGING" && timeout "$TIMEOUT" cargo build --tests >"$BUILD_LOG" 2>&1 ); then
  NERR="$(grep -cE '^error(\[|:)' "$BUILD_LOG" || true)"
  if [ "$JSON" -eq 1 ]; then
    printf '{"project":"%s","state":"build_failed","passed":0,"failed":0,"ignored":0,"total":0,"build_errors":%s}\n' \
      "$PROJECT" "${NERR:-0}"
  else
    echo "[oracle] project  : $PROJECT"
    echo "[oracle] source   : $SRC"
    echo "[oracle] result   : BUILD FAILED, ${NERR:-0} compile error(s), 0 tests ran"
    grep -E '^error(\[|:)' "$BUILD_LOG" | head -10 | sed 's/^/[oracle]   /'
    echo "[oracle] exitcode : 2"
  fi
  exit 1
fi

TEST_LOG="$STAGING/.test.log"
set +e
( cd "$STAGING" && timeout "$TIMEOUT" cargo test --no-fail-fast >"$TEST_LOG" 2>&1 )
TRC=$?
set -e

PASSED="$(grep -cE '^test .* \.\.\. ok$' "$TEST_LOG" || true)"
FAILED="$(grep -cE '^test .* \.\.\. FAILED$' "$TEST_LOG" || true)"
IGNORED="$(grep -cE '^test .* \.\.\. ignored$' "$TEST_LOG" || true)"
TOTAL=$((PASSED + FAILED + IGNORED))

if [ "$JSON" -eq 1 ]; then
  printf '{"project":"%s","state":"scored","passed":%d,"failed":%d,"ignored":%d,"total":%d,"exit_code":%d}\n' \
    "$PROJECT" "$PASSED" "$FAILED" "$IGNORED" "$TOTAL" "$TRC"
else
  echo "[oracle] project  : $PROJECT"
  echo "[oracle] source   : $SRC"
  echo "[oracle] result   : $PASSED passed, $FAILED failed, $IGNORED ignored (of $TOTAL)"
  if [ "$FAILED" -gt 0 ]; then
    echo "[oracle] failures :"
    grep -E '^test .* \.\.\. FAILED$' "$TEST_LOG" | head -20 | sed 's/^/[oracle]   /'
  fi
  # cargo exits 101 when tests fail; the harness reads pytest's 0/1 convention,
  # so report the same meaning in the same shape: 0 all passed, 1 some failed.
  echo "[oracle] exitcode : $([ "$FAILED" -eq 0 ] && echo 0 || echo 1)"
fi
[ "$KEEP_STAGING" -eq 1 ] && echo "[oracle] staging  : $STAGING"
exit "$TRC"
