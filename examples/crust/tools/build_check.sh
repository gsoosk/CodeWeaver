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
SCAFFOLD_ARG="${2:-}"
[ -d "$WORK/src" ] || { echo "build_check: no working copy at $WORK/src" >&2; exit 2; }

# The declared module list is part of the contract, not of the implementation.
#
# A repair loop scored on "does it compile" can satisfy that by DELETING whatever
# fails -- dropping `pub mod parser;` from lib.rs makes the crate build and makes
# every test referring to it fail to link. That is not a repair, and it was
# observed happening. So check the contract first, using only the scaffold, which
# the translator was given anyway. This stays fully test-blind.
SCAFFOLD=""
for candidate in "$SCAFFOLD_ARG" "$WORK/../../.scaffold" "$WORK/../../../.scaffold"; do
  [ -n "$candidate" ] && [ -f "$candidate/src/lib.rs" ] && { SCAFFOLD="$candidate"; break; }
done
if [ -n "$SCAFFOLD" ] && [ -f "$WORK/src/lib.rs" ]; then
  MISSING=""
  while IFS= read -r module; do
    grep -qE "^[[:space:]]*pub[[:space:]]+mod[[:space:]]+${module}[[:space:]]*;" \
      "$WORK/src/lib.rs" || MISSING="$MISSING $module"
  done <<EOF
$(grep -oE '^[[:space:]]*pub[[:space:]]+mod[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' "$SCAFFOLD/src/lib.rs" \
   | awk '{print $NF}')
EOF
  if [ -n "$MISSING" ]; then
    echo "build_check: FAILED with 1 error(s)"
    echo "error: lib.rs no longer declares module(s) the interface requires:$MISSING"
    echo "  --> $WORK/src/lib.rs"
    echo "note: removing a module from the crate does not repair it; the tests link"
    echo "      against these paths and will fail to compile without them."
    exit 1
  fi
fi

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
