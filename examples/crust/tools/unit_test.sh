#!/usr/bin/env bash
# LAYER 1: the agents' OWN tests, inside the working copy. Never the oracle.
#
# Rust keeps unit tests beside the code in `#[cfg(test)] mod tests`, so there is no
# separate directory to point at. `cargo test --lib` runs exactly those and nothing
# else: it does not build the integration targets in src/bin, which is where the
# held-out oracle is staged at validation time. That separation is the whole point.
#
# Exit 0 when the agents' own tests pass, or when they have not written any yet --
# an empty layer 1 is a legitimate early state, not a failure.
set -eu
export PATH="$HOME/.cargo/bin:$PATH"

WORK="${1:-pipeline/project}"
[ -d "$WORK/src" ] || { echo "unit_test: no working copy at $WORK/src" >&2; exit 2; }

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

if ! ( cd "$WORK" && timeout 900 cargo test --lib --no-fail-fast >"$LOG" 2>&1 ); then
  if grep -qE '^error(\[|:)' "$LOG"; then
    echo "unit_test: crate does not compile"
    grep -E '^error(\[|:)' "$LOG" | head -10
    exit 1
  fi
  echo "unit_test: FAILED"
  grep -E '^test .* \.\.\. FAILED$|^test result:' "$LOG" | head -20
  exit 1
fi

N="$(grep -cE '^test .* \.\.\. ok$' "$LOG" || true)"
if [ "${N:-0}" -eq 0 ]; then
  echo "unit_test: OK (no agent-written tests yet)"
else
  echo "unit_test: OK ($N test(s) passed)"
fi
