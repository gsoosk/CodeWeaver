#!/usr/bin/env bash
# Did any agent touch the held-out oracle during a CodeWeaver run?
#
#   bash tools/oracle_audit.sh <subject> [more subjects...]
#
# CodeWeaver runs its agents with --allow-all, so nothing at the filesystem level
# stops them reading the oracle. The only honest position is to keep the oracle out
# of the tree they work in AND to check afterwards whether they found it anyway.
#
# This is not a formality. A scoper run listed `<subject>/.oracle-master/bin/` and
# lifted the exact test-target names out of it -- names that are NOT derivable from
# the C source, because the C tests are withheld. That run's milestones were the
# answer key. The oracle now lives outside the subject tree; this script confirms
# it stayed unread.
#
# Exit 0 when clean, 1 when any agent log references the oracle location.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
[ "$#" -ge 1 ] || { echo "usage: $0 <subject> [subject...]" >&2; exit 2; }

RC=0
for PROJECT in "$@"; do
  SUBJECT="$ROOT/subjects/$PROJECT"
  [ -d "$SUBJECT" ] || { echo "[audit] $PROJECT: not materialized"; continue; }
  ORACLE="${CRUST_ORACLE_ROOT:-$HOME/.crust-oracles}/$PROJECT"
  [ -d "$ORACLE/bin" ] || ORACLE="$SUBJECT/.oracle-master"

  LOGS="$SUBJECT/pipeline/logs"
  if [ ! -d "$LOGS" ]; then
    echo "[audit] $PROJECT: no agent logs to audit (run not started, or logs pruned)"
    continue
  fi

  # Match the oracle's absolute path, its basename, and the legacy in-tree name.
  HITS="$(grep -l -e "$ORACLE" -e "crust-oracles" -e ".oracle-master" -e ".oracle-path" \
            "$LOGS"/*.log "$LOGS"/*.jsonl 2>/dev/null | sort -u)"
  if [ -n "$HITS" ]; then
    echo "[audit] $PROJECT: ORACLE REFERENCED in $(echo "$HITS" | wc -l) log(s)"
    echo "$HITS" | sed "s|$SUBJECT/|    |"
    grep -ho -e "$ORACLE[^ \"\\]*" -e "\.oracle-master[^ \"\\]*" \
      "$LOGS"/*.log "$LOGS"/*.jsonl 2>/dev/null | sort -u | head -6 | sed 's/^/      /'
    RC=1
  else
    echo "[audit] $PROJECT: clean (no agent log references the oracle)"
  fi

  # Independent cross-check: gate tokens that are not derivable from the source.
  # If the milestones name a test target verbatim, say so -- it is the strongest
  # single signal that the oracle was read.
  MS="$SUBJECT/pipeline/milestones.json"
  if [ -f "$MS" ] && [ -f "$ORACLE/gate-tokens.txt" ]; then
    MATCHED=0
    while IFS= read -r token; do
      [ -n "$token" ] || continue
      grep -q "\"$token\"" "$MS" 2>/dev/null && MATCHED=$((MATCHED + 1))
    done < "$ORACLE/gate-tokens.txt"
    TOTAL="$(wc -l < "$ORACLE/gate-tokens.txt")"
    echo "[audit] $PROJECT: milestones name $MATCHED/$TOTAL real test target(s)"
    if [ "$MATCHED" -gt 0 ] && [ "$RC" -eq 0 ]; then
      echo "        NOTE: verify these are derivable from the source before trusting the run."
    fi
  fi
done
exit "$RC"
