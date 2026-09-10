#!/usr/bin/env bash
# build_check for the CRUST C->Rust example: does the translation compile?
#
# Invoked as `bash ../../tools/build_check.sh` from a subject directory, matching
# how examples/alphatrans invokes its Python build_check.
#
# This is the direct analogue of the AlphaTrans build_check, but it is a far
# stronger signal. There, "does it compile" could only mean parse + import,
# because Python defers everything else to runtime. Here rustc checks types,
# ownership, lifetimes and exhaustiveness before anything runs. A compiler-guided
# repair arm therefore has much more to work with on this example than on that
# one -- which is exactly the asymmetry CRUST-bench relies on and the AlphaTrans
# subjects cannot exercise.
#
# The tests are NOT staged here: this must stay test-blind so it can feed a
# test-blind repair arm. It compiles the library only.
#
# Exit 0 when the crate builds, 1 otherwise, printing the diagnostics.
set -eu
export PATH="$HOME/.cargo/bin:$PATH"

WORK="${1:-pipeline/project}"
[ -d "$WORK/src" ] || { echo "build_check: no working copy at $WORK/src" >&2; exit 2; }

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

if ( cd "$WORK" && timeout 900 cargo build --lib >"$LOG" 2>&1 ); then
  NWARN="$(grep -cE '^warning' "$LOG" || true)"
  echo "build_check: OK (crate builds; ${NWARN:-0} warning(s))"
  exit 0
fi

NERR="$(grep -cE '^error(\[|:)' "$LOG" || true)"
echo "build_check: FAILED with ${NERR:-0} error(s)"
# One line per diagnostic, in the compiler's own words, so a repair arm gets
# the real message rather than a summary of it.
grep -E '^(error(\[|:)|  --> )' "$LOG" | head -60
exit 1
