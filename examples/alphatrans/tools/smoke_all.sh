#!/usr/bin/env bash
# Offline smoke test across every materialized AlphaTrans subject. FREE: no Copilot,
# no LLM, no cost. Verifies, per subject:
#
#   1. config loads and the milestone matrix resolves
#   2. the oracle CEILING  -- AlphaTrans's manually verified translation passes
#   3. the oracle FLOOR    -- the unimplemented skeleton fails
#   4. gate resolution     -- an exact <Class>Test token selects only that file
#   5. tamper detection    -- a modified oracle aborts with exit 3
#   6. build_check         -- passes on the skeleton working copy
#   7. the whole Burr graph, against mock agents (`codeweaver check`)
#
# Usage: bash tools/smoke_all.sh [project ...]     (default: every subject present)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE="$(dirname "$HERE")"
REPO="$(cd "$EXAMPLE/../.." && pwd)"

if [ $# -gt 0 ]; then
  PROJECTS="$*"
else
  PROJECTS="$(ls "$EXAMPLE/subjects" 2>/dev/null || true)"
fi
[ -n "$PROJECTS" ] || { echo "no subjects materialized -- run setup.sh --all first" >&2; exit 2; }

PASS=0; FAIL=0
ok(){ echo "    PASS  $1"; PASS=$((PASS+1)); }
bad(){ echo "    FAIL  $1"; FAIL=$((FAIL+1)); }

for P in $PROJECTS; do
  S="$EXAMPLE/subjects/$P"
  echo
  echo "==================== $P ===================="
  [ -d "$S" ] || { bad "$P: not materialized"; continue; }

  # Tier A subjects carry an oracle; tier B does not.
  if [ -d "$S/.oracle-master" ]; then TIER=A; else TIER=B; fi
  echo "    (tier $TIER)"

  # 1. config + milestone matrix
  if (cd "$REPO" && python -m codeweaver milestones --config "examples/alphatrans/subjects/$P/codeweaver.toml" >/dev/null 2>&1); then
    ok "config loads"
  else
    bad "config loads"
  fi

  if [ "$TIER" = A ]; then
    # 2. ceiling
    out="$(bash "$HERE/oracle.sh" --project "$P" --baseline golden --all 2>&1)"
    code=$?
    res="$(echo "$out" | grep '^\[oracle\] result' | sed 's/.*: //')"
    if [ $code -eq 0 ]; then ok "ceiling (golden): $res"; else bad "ceiling (golden) exit=$code: $res"; fi

    # 3. floor
    out="$(bash "$HERE/oracle.sh" --project "$P" --baseline skeleton --all 2>&1)"
    code=$?
    res="$(echo "$out" | grep '^\[oracle\] result' | sed 's/.*: //')"
    if [ $code -ne 0 ]; then ok "floor (skeleton) correctly fails: $res"; else bad "floor (skeleton) PASSED -- oracle is not discriminating!"; fi

    # 4. gate resolution: first oracle test file, by exact name
    tok="$(find "$S/.oracle-master/test" -name '*Test.py' -printf '%f\n' 2>/dev/null | sed 's/\.py$//' | sort | head -1)"
    if [ -n "$tok" ]; then
      out="$(bash "$HERE/oracle.sh" --project "$P" --baseline golden --gate "$tok" 2>&1)"
      code=$?
      res="$(echo "$out" | grep '^\[oracle\] result' | sed 's/.*: //')"
      if [ $code -eq 0 ] && ! echo "$res" | grep -q 'deselected'; then
        ok "gate '$tok' resolves to an exact file: $res"
      else
        bad "gate '$tok' exit=$code: $res"
      fi
    else
      bad "no *Test.py found to exercise gate resolution"
    fi

    # 5. tamper detection
    victim="$(find "$S/.oracle-master/test" -name '*Test.py' | head -1)"
    if [ -n "$victim" ]; then
      cp "$victim" "$victim.bak"
      echo "# tampered" >> "$victim"
      bash "$HERE/oracle.sh" --project "$P" --baseline golden --all >/dev/null 2>&1
      code=$?
      mv -f "$victim.bak" "$victim"
      if [ $code -eq 3 ]; then ok "tamper detected (exit 3)"; else bad "tamper NOT detected (exit $code)"; fi
    fi
  else
    # Tier B: no oracle exists. Assert that fact holds, so a stray .oracle-master
    # (or a silently-wired oracle command) is caught rather than trusted.
    if grep -q 'tier         = B' "$S/codeweaver.toml"; then ok "declared tier B in config"; else bad "config does not declare tier B"; fi
    if ! grep -q 'oracle.sh' "$S/codeweaver.toml"; then ok "validate does NOT reference the oracle"; else bad "tier-B config references oracle.sh"; fi
  fi

  # 6. build_check on a skeleton working copy (both tiers)
  rm -rf "$S/pipeline/project"
  mkdir -p "$S/pipeline"
  cp -r "$S/.scaffold" "$S/pipeline/project"
  if (cd "$S" && python "$HERE/build_check.py" >/dev/null 2>&1); then
    ok "build_check passes on the skeleton"
  else
    bad "build_check FAILS on the skeleton"
  fi
  rm -rf "$S/pipeline"
done

# 7. the Burr graph itself, once, against mock agents
echo
echo "==================== orchestrator graph (mock) ===================="
first="$(echo $PROJECTS | awk '{print $1}')"
if (cd "$REPO" && python -m codeweaver check --config "examples/alphatrans/subjects/$first/codeweaver.toml" >/tmp/cw_check.log 2>&1); then
  ok "codeweaver check (all 7 scenarios)"
else
  bad "codeweaver check -- see /tmp/cw_check.log"
  tail -15 /tmp/cw_check.log
fi
# the mock run leaves state behind; clear it so a real run starts clean
rm -rf "$EXAMPLE/subjects/$first/pipeline"

echo
echo "==================== SMOKE SUMMARY ===================="
echo "  passed: $PASS    failed: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
