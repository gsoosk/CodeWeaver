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
GATE=""
ALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --working-copy) WORKING_COPY_REL="$2"; shift 2 ;;
    --json) JSON=1; shift ;;
    --keep-staging) KEEP_STAGING=1; shift ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --all) ALL=1; shift ;;
    --gate) GATE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PROJECT" ] || { echo "usage: $0 --project <name>" >&2; exit 2; }

SUBJECT="$ROOT/subjects/$PROJECT"
[ -d "$SUBJECT" ] || { echo "subject not materialized: $SUBJECT" >&2; exit 2; }
# The oracle location is derived by CONVENTION, not read from a pointer inside the
# subject directory. A pointer there is itself a leak: an agent read one and then
# viewed the directory it named. Nothing in the agents' working tree names this path.
ORACLE="${CRUST_ORACLE_ROOT:-$HOME/.crust-oracles}/$PROJECT"
# Legacy in-tree location, so older materializations still re-score.
[ -d "$ORACLE/bin" ] || ORACLE="$SUBJECT/.oracle-master"
[ -d "$ORACLE/bin" ] || { echo "no held-out tests for $PROJECT" >&2; exit 2; }

REL="${WORKING_COPY_REL:-pipeline/project}"
SRC="$SUBJECT/$REL"
[ -d "$SRC/src" ] || { echo "no translation at $SRC/src" >&2; exit 2; }

STAGING="$(mktemp -d)"
cleanup() { [ "$KEEP_STAGING" -eq 1 ] || rm -rf "$STAGING"; }
trap cleanup EXIT

# Stage the translation, then synthesize a canonical manifest and restore the tests.
#
# The manifest is REBUILT rather than copied, because cargo's defaults make the
# denominator unstable:
#   * src/bin/*.rs is auto-discovered as binaries, and `cargo test` runs the
#     `#[test]` functions inside them;
#   * a file ALSO named in a [[test]] block is compiled a second time as an
#     integration target, so every one of its tests is counted TWICE;
#   * a bare `cargo test` additionally runs the crate's own `#[cfg(test)] mod tests`,
#     which CodeWeaver's agents write -- tests the translation graded itself on.
# Subjects therefore reported 2x, 1x or 1x+agent-tests depending on whether CRUST
# happened to declare [[test]] blocks. Disabling auto-discovery and declaring each
# staged file exactly once makes every subject count each oracle test exactly once.
cp -r "$SRC/." "$STAGING/"
rm -rf "$STAGING/target" "$STAGING/src/bin"
cp -r "$ORACLE/bin" "$STAGING/src/bin"

awk '
  /^\[\[test\]\]/ || /^\[\[bin\]\]/ { skip=1; next }
  /^\[/                             { skip=0 }
  !skip                             { print }
' "$ORACLE/Cargo.toml.oracle" > "$STAGING/Cargo.toml"
# autobins/autotests off: nothing is a target unless declared below.
python3 - "$STAGING/Cargo.toml" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path).read()
# Place the auto-discovery switches inside [package], where cargo reads them.
text = re.sub(r'(?m)^(\[package\]\s*$)', r'\1\nautobins = false\nautotests = false', text, count=1)
open(path, 'w').write(text)
PY
for f in "$STAGING/src/bin"/*.rs; do
  [ -e "$f" ] || continue
  name="$(basename "$f" .rs)"
  printf '\n[[test]]\nname = "%s"\npath = "src/bin/%s.rs"\nharness = true\n' "$name" "$name" \
    >> "$STAGING/Cargo.toml"
done

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
  exit 2
fi

TEST_LOG="$STAGING/.test.log"
# Select the oracle's test TARGETS explicitly, always.
#
# A bare `cargo test` also runs the crate's own `#[cfg(test)] mod tests` -- and
# CodeWeaver's agents write those. Counting them inflates both numerator and
# denominator with tests the translation graded itself on, which is not a held-out
# score at all. Naming each target with --test restricts the run to the staged
# oracle and nothing else.
#
# A gate narrows that set further, to the targets a milestone is responsible for.
SELECT=""
if [ -n "$GATE" ] && [ "$ALL" -eq 0 ]; then
  for token in $GATE; do
    if [ -f "$ORACLE/bin/$token.rs" ]; then
      SELECT="$SELECT --test $token"
    else
      match="$(cd "$ORACLE/bin" && ls | sed 's/\.rs$//' | grep -ix "$token" | head -1 || true)"
      if [ -n "$match" ]; then
        SELECT="$SELECT --test $match"
      else
        echo "[oracle] gate token matched no test target: $token" >&2
        exit 2
      fi
    fi
  done
else
  for f in "$ORACLE/bin"/*.rs; do
    [ -e "$f" ] || continue
    SELECT="$SELECT --test $(basename "$f" .rs)"
  done
fi

set +e
# shellcheck disable=SC2086
( cd "$STAGING" && timeout "$TIMEOUT" cargo test $SELECT --no-fail-fast >"$TEST_LOG" 2>&1 )
TRC=$?
set -e

PASSED="$(grep -cE '^test .* \.\.\. ok$' "$TEST_LOG" || true)"
FAILED="$(grep -cE '^test .* \.\.\. FAILED$' "$TEST_LOG" || true)"
IGNORED="$(grep -cE '^test .* \.\.\. ignored$' "$TEST_LOG" || true)"
TOTAL=$((PASSED + FAILED + IGNORED))

# cargo exits 101 when any test fails. The harness reads pytest's convention, and
# cross-checks the reported code against the process's own exit status, so the two
# must agree: 0 = everything passed, 1 = some test failed, 2 = could not build.
STATUS=$([ "$FAILED" -eq 0 ] && echo 0 || echo 1)

if [ "$TOTAL" -eq 0 ]; then
  # Compiled, but not one test ran. Never report that as a clean pass.
  if [ "$JSON" -eq 1 ]; then
    printf '{"project":"%s","state":"no_tests_ran","passed":0,"failed":0,"ignored":0,"total":0}\n' "$PROJECT"
  else
    echo "[oracle] project  : $PROJECT"
    echo "[oracle] result   : NO TESTS RAN - the oracle collected nothing"
    echo "[oracle] exitcode : 2"
  fi
  exit 2
fi

if [ "$JSON" -eq 1 ]; then
  printf '{"project":"%s","state":"scored","passed":%d,"failed":%d,"ignored":%d,"total":%d,"exit_code":%d}\n' \
    "$PROJECT" "$PASSED" "$FAILED" "$IGNORED" "$TOTAL" "$STATUS"
else
  echo "[oracle] project  : $PROJECT"
  echo "[oracle] source   : $SRC"
  echo "[oracle] gate     : ${GATE:-(whole suite)}"
  echo "[oracle] result   : $PASSED passed, $FAILED failed, $IGNORED ignored (of $TOTAL)"
  if [ "$FAILED" -gt 0 ]; then
    echo "[oracle] failures :"
    grep -E '^test .* \.\.\. FAILED$' "$TEST_LOG" | head -20 | sed 's/^/[oracle]   /'
  fi
  echo "[oracle] exitcode : $STATUS"
fi
[ "$KEEP_STAGING" -eq 1 ] && echo "[oracle] staging  : $STAGING"
exit "$STATUS"
