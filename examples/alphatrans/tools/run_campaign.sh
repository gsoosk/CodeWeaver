#!/usr/bin/env bash
# Launch a CodeWeaver run for every tier-A subject IN PARALLEL, with Burr telemetry
# enabled so each appears in the UI as its own project.
#
#   bash tools/run_campaign.sh <run-tag> [project ...]
#
# Each subject is fully isolated (its own scaffold, oracle, pipeline, burr.db and
# Burr project slug), so parallel execution is safe. Logs land in ~/cwruns/<tag>/.
set -uo pipefail

TAG="${1:-}"
[ -n "$TAG" ] || { echo "usage: $0 <run-tag> [project ...]" >&2; exit 2; }
shift || true

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE="$(dirname "$HERE")"
REPO="$(cd "$EXAMPLE/../.." && pwd)"

TIER_A="commons-cli commons-csv commons-fileupload commons-validator"
PROJECTS="${*:-$TIER_A}"

LOGDIR="$HOME/cwruns/$TAG"
mkdir -p "$LOGDIR"

# Telemetry ON: tracker_enabled() needs `apache-burr[start]` importable AND
# CODEWEAVER_NO_TRACKER unset. Assert it rather than discovering it afterwards.
unset CODEWEAVER_NO_TRACKER || true
if ! python -c 'import burr.tracking.client' 2>/dev/null; then
  echo "FATAL: burr.tracking.client not importable -- the run would silently produce" >&2
  echo "       no Burr UI data. Install with: pip install 'apache-burr[start]'"      >&2
  exit 1
fi
echo "[campaign] burr tracking: ENABLED"

cd "$REPO"
for P in $PROJECTS; do
  CFG="examples/alphatrans/subjects/$P/codeweaver.toml"
  [ -f "$CFG" ] || { echo "[campaign] SKIP $P (not materialized)"; continue; }

  APPID="$TAG-$P"
  LOG="$LOGDIR/$P.log"

  nohup setsid python -m codeweaver run --config "$CFG" --app-id "$APPID" \
      > "$LOG" 2>&1 < /dev/null &

  sleep 3
  PID="$(pgrep -f "app-id $APPID" | head -1)"
  printf '[campaign] %-20s app-id=%-34s pid=%-8s log=%s\n' "$P" "$APPID" "${PID:-?}" "$LOG"
done

echo
echo "[campaign] launched. Monitor with:"
echo "    bash ~/azure_status.sh                     # all subjects, from the persister"
echo "    tail -f $LOGDIR/<project>.log"
echo "    Burr UI on :7250 (one project per subject: alphatrans-<name>)"
