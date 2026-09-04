#!/usr/bin/env bash
# Materialize AlphaTrans subject project(s) for CodeWeaver. POSIX equivalent of
# setup.ps1 -- see that file for the full rationale.
#
#   ./setup.sh commons-cli [/path/to/AlphaTrans]
#   ./setup.sh --all       [/path/to/AlphaTrans]     # all 10 subjects
#   ./setup.sh --tier-a    [/path/to/AlphaTrans]     # only the 4 with a real oracle
#
# TWO TIERS (see README "Two tiers of subject"):
#   A  commons-cli commons-csv commons-fileupload commons-validator
#      -> ship a manually verified Python test suite = a real, held-out oracle.
#         Scored on TEST PASS RATE.
#   B  JavaFastPFOR commons-codec commons-exec commons-graph commons-pool jansi
#      -> ship NO human Python tests (only `pass`-bodied skeletons and
#         model-generated .json schemas). No functional oracle is possible.
#         Scored on BUILD/IMPORT + PARITY COMPLETENESS only.
#
# Set SKIP_BASELINE=1 to skip the tier-A golden-baseline recording pass.
set -euo pipefail

TIER_A="commons-cli commons-csv commons-fileupload commons-validator"
TIER_B="JavaFastPFOR commons-codec commons-exec commons-graph commons-pool jansi"
ALL_SUBJECTS="$TIER_A $TIER_B"

ARG="${1:-}"
DATASET="${2:-$HOME/AlphaTrans}"
[ -n "$ARG" ] || { echo "usage: $0 <project|--all|--tier-a> [dataset-root]" >&2; exit 2; }

case "$ARG" in
  --all)    TARGETS="$ALL_SUBJECTS" ;;
  --tier-a) TARGETS="$TIER_A" ;;
  *)
    case " $ALL_SUBJECTS " in
      *" $ARG "*) TARGETS="$ARG" ;;
      *) echo "unknown project '$ARG'. Available: $ALL_SUBJECTS" >&2; exit 2 ;;
    esac ;;
esac

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

  # Tier is decided by whether a manually verified Python test suite exists.
  if [ -d "$ORACLE/src/test" ]; then TIER=A; else TIER=B; fi

  SUBJECT="$HERE/subjects/$PROJECT"
  mkdir -p "$SUBJECT"

  # .scaffold = the interface skeleton (src/main ONLY; the skeleton's src/test is
  # dropped deliberately -- its test method names would leak the oracle's surface).
  SCAFFOLD="$SUBJECT/.scaffold"
  rm -rf "$SCAFFOLD"; mkdir -p "$SCAFFOLD/src"
  cp -r "$SKELETON" "$SCAFFOLD/src/main"
  : > "$SCAFFOLD/src/__init__.py"
  [ -f "$SCAFFOLD/src/main/__init__.py" ] || : > "$SCAFFOLD/src/main/__init__.py"

  if [ "$TIER" = A ]; then
    ORACLE_MASTER="$SUBJECT/.oracle-master"
    rm -rf "$ORACLE_MASTER"; mkdir -p "$ORACLE_MASTER"
    cp -r "$ORACLE/src/test" "$ORACLE_MASTER/test"
    for f in pytest.ini conftest.py; do
      [ -f "$ORACLE/$f" ] && cp "$ORACLE/$f" "$ORACLE_MASTER/$f"
    done
    ( cd "$ORACLE_MASTER" && find . -type f ! -name SHA256SUMS.txt ! -name baseline_excluded.txt -print0 \
        | sort -z | xargs -0 sha256sum > SHA256SUMS.txt )
    VALIDATE="bash ../../tools/oracle.sh --project $PROJECT --gate \"{gate}\""
    TIER_NOTE="TIER A: a manually verified, human-written pytest suite is the held-out oracle."
  else
    # No human Python tests exist for this subject, so there is no functional oracle.
    # The milestone gate falls back to build_check (parse + import); completeness is
    # carried entirely by the parity verifier. Results are NOT comparable to tier A.
    rm -rf "$SUBJECT/.oracle-master"
    VALIDATE="python ../../tools/build_check.py"
    TIER_NOTE="TIER B: NO human Python test suite exists for this subject, so there is no
# functional oracle. validate falls back to build_check (parse + import) and
# completeness rests entirely on the parity verifier. Do NOT pool its numbers
# with tier A -- the metrics measure different things."
  fi

  sed -e "s|__PROJECT__|$PROJECT|g" \
      -e "s|__PROJECT_SLUG__|$PROJECT|g" \
      -e "s|__JAVA_SRC_ABS__|$JAVA_SRC|g" \
      -e "s|__DATASET_ROOT__|$DATASET_ABS|g" \
      -e "s|__TIER__|$TIER|g" \
      -e "s|__VALIDATE_CMD__|$VALIDATE|g" \
      "$HERE/codeweaver.template.toml" > "$SUBJECT/codeweaver.toml.tmp"
  # TIER_NOTE can contain newlines -> substitute in python, not sed.
  TIER_NOTE="$TIER_NOTE" python3 -c "
import os, sys
p = sys.argv[1]
s = open(p).read().replace('__TIER_NOTE__', os.environ['TIER_NOTE'])
open(p[:-4], 'w').write(s)
os.remove(p)
" "$SUBJECT/codeweaver.toml.tmp"

  rm -rf "$SUBJECT/pipeline"

  if [ "$TIER" = A ] && [ "${SKIP_BASELINE:-0}" != "1" ]; then
    echo "[$PROJECT] recording environment-broken baseline..."
    bash "$HERE/tools/oracle.sh" --project "$PROJECT" --baseline golden --all --record-exclusions >/dev/null 2>&1 || true
  fi

  N_JAVA=$(find "$JAVA_SRC" -name '*.java' | wc -l | tr -d ' ')
  N_IFACE=$(find "$SCAFFOLD/src/main" -name '*.py' ! -name '__init__.py' | wc -l | tr -d ' ')
  if [ "$TIER" = A ]; then
    N_ORACLE=$(find "$SUBJECT/.oracle-master/test" -name '*.py' ! -name '__init__.py' | wc -l | tr -d ' ')
    N_EXCL=0
    [ -f "$SUBJECT/.oracle-master/baseline_excluded.txt" ] && \
      N_EXCL=$(grep -vc '^#' "$SUBJECT/.oracle-master/baseline_excluded.txt" 2>/dev/null || echo 0)
    printf '%-18s [A] java:%4s  iface:%4s  oracle-mods:%4s  env-broken:%3s\n' \
      "$PROJECT" "$N_JAVA" "$N_IFACE" "$N_ORACLE" "$N_EXCL"
  else
    printf '%-18s [B] java:%4s  iface:%4s  oracle: NONE (build+parity only)\n' \
      "$PROJECT" "$N_JAVA" "$N_IFACE"
  fi
done

echo
echo "Next:"
echo "  bash examples/alphatrans/tools/smoke_all.sh          # offline mock smoke test, all subjects (free)"
echo "  bash examples/alphatrans/tools/oracle.sh --project commons-cli --baseline golden --all"
