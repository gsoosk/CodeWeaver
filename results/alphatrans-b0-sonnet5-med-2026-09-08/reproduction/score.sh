#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: bash score.sh <subject> <b0|b0-rerun> [AlphaTrans-root]" >&2
  exit 2
fi
SUBJECT="$1"
ARM="$2"
DATASET="${3:-$HOME/AlphaTrans}"
case "$SUBJECT" in
  commons-cli|commons-csv|commons-fileupload|commons-validator) ;;
  *) echo "Unknown subject: $SUBJECT" >&2; exit 2 ;;
esac
case "$ARM" in
  b0|b0-rerun) ;;
  *) echo "Unknown arm: $ARM" >&2; exit 2 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE="$(cd "$HERE/.." && pwd)"
TRANSLATION="$PACKAGE/data/$SUBJECT/$ARM/project/src/main"
ORACLE="$DATASET/data/manually_verified_translations/$SUBJECT/manual_translation"
RUNNER="$HERE/oracle.sh"
[ -d "$TRANSLATION" ] || { echo "No published result for $SUBJECT/$ARM" >&2; exit 2; }
[ -d "$ORACLE/src/test" ] || { echo "AlphaTrans oracle not found: $ORACLE" >&2; exit 2; }
[ "$(git -C "$DATASET" rev-parse HEAD)" = "c1cabf93d41a153de207d6b098e1da7bbd79abab" ] || {
  echo "AlphaTrans revision differs from the recorded dataset revision." >&2
  exit 2
}
printf '%s  %s\n' \
  "4231cf66d506f45f6e6def8c18319ffe8c54e962b346c91a694511eb226cb3ff" \
  "$RUNNER" | sha256sum --quiet -c -
(cd "$PACKAGE" && sha256sum --quiet -c SHA256SUMS.txt)

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
MASTER="$STAGING/subjects/$SUBJECT/.oracle-master"
mkdir -p "$MASTER" "$STAGING/tools" "$STAGING/subjects/$SUBJECT/pipeline/project/src"
cp "$RUNNER" "$STAGING/tools/oracle.sh"
cp -R "$TRANSLATION" "$STAGING/subjects/$SUBJECT/pipeline/project/src/main"
cp -R "$ORACLE/src/test" "$MASTER/test"
for name in pytest.ini conftest.py; do
  if [ -f "$ORACLE/$name" ]; then
    cp "$ORACLE/$name" "$MASTER/$name"
  fi
done
cp "$PACKAGE/metadata/$SUBJECT/oracle_SHA256SUMS.txt" "$MASTER/SHA256SUMS.txt"
cp "$PACKAGE/metadata/$SUBJECT/oracle_baseline_excluded.txt" "$MASTER/baseline_excluded.txt"

# No pipeline/skips.json is copied, so repair deferrals cannot hide failures.
bash "$STAGING/tools/oracle.sh" --project "$SUBJECT" --all
