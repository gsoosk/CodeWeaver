<#
.SYNOPSIS
  Print the live status of a CodeWeaver run from its SQLite persister.

.DESCRIPTION
  The Burr telemetry UI (`burr`) only shows runs whose tracker was enabled. When a
  run is launched with CODEWEAVER_NO_TRACKER=1 the UI has nothing to show -- but the
  SQLite persister (`pipeline/burr.db`) is always written after every action, so it
  is the authoritative record either way.

  This reads that persister and prints milestone progress, the repair history, and
  the latest validator verdict.

.EXAMPLE
  ./tools/status.ps1
  ./tools/status.ps1 -Watch
#>
param(
    [switch]$Watch,
    [int]$IntervalSeconds = 60
)

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$example = Split-Path -Parent $here

$py = @'
import json, os, sqlite3, sys

pipeline = sys.argv[1]
db = os.path.join(pipeline, "burr.db")
if not os.path.exists(db):
    print("no run yet (pipeline/burr.db missing)"); raise SystemExit(0)

con = sqlite3.connect(db)
cols = [d[0] for d in con.execute("select * from codeweaver_state limit 1").description]
row = con.execute("select * from codeweaver_state order by rowid desc limit 1").fetchone()
d = dict(zip(cols, row))
st = json.loads(d["state"]) if isinstance(d.get("state"), str) else d.get("state")

ms = []
mpath = os.path.join(pipeline, "milestones.json")
if os.path.exists(mpath):
    raw = json.load(open(mpath, encoding="utf-8"))
    ms = raw if isinstance(raw, list) else raw.get("milestones", [])

hist = st.get("history", [])
done_ids = {h["milestone"] for h in hist if h.get("passed")}
gaveup   = {h["milestone"] for h in hist if h.get("gave_up")}
idx      = st.get("milestone_idx", 0)
cur      = ms[idx]["id"] if 0 <= idx < len(ms) else "?"

print(f"app_id     : {d.get('app_id')}")
print(f"position   : milestone {idx} of {st.get('last_idx')}  (current: {cur})")
print(f"repair     : iter {st.get('iter_count')} of {st.get('max_iter')}")
print(f"last agent : {st.get('last_agent')}")
print(f"parity     : round {st.get('parity_round', 0)} of {st.get('max_parity_rounds')}  complete={st.get('parity_complete')}")
print(f"done       : {st.get('done')}   skipped: {st.get('skipped') or '[]'}")
print()

if ms:
    print("milestones:")
    for i, m in enumerate(ms):
        mid = m.get("id")
        if mid in gaveup:      mark = "SKIP"
        elif mid in done_ids:  mark = "PASS"
        elif i == idx:         mark = ">>>>"
        elif i < idx:          mark = "  - "
        else:                  mark = "    "
        print(f"  {mark} {mid:4} {m.get('title','')}")
    print()

if hist:
    print("history (last 12):")
    for h in hist[-12:]:
        flag = "  GAVE-UP" if h.get("gave_up") else ""
        if h.get("retry_for"): flag += f"  [retry {h['retry_for']}]"
        print(f"  {h['milestone']:4} iter={h['iter']}  passed={h['passed']}{flag}")
    print()

rpath = os.path.join(pipeline, "report.json")
if os.path.exists(rpath):
    try:
        rep = json.load(open(rpath, encoding="utf-8"))
        t = rep.get("tests", {})
        print(f"last report: {rep.get('milestone')}  passed={rep.get('passed')}")
        for layer in ("unit", "e2e"):
            if layer in t:
                v = t[layer]
                print(f"  {layer:5} total={v.get('total')} passed={v.get('passed')} failed={v.get('failed')} skipped={v.get('skipped', 0)}")
        for f in (rep.get("failures") or [])[:3]:
            print(f"  FAIL  {f.get('test')}")
    except Exception as e:
        print(f"(could not read report.json: {e})")
'@

$tmp = Join-Path $env:TEMP "cw_status.py"
Set-Content -Path $tmp -Value $py -Encoding utf8

do {
    if ($Watch) { Clear-Host; Write-Host "=== $(Get-Date -Format 'HH:mm:ss') ===" }
    python $tmp (Join-Path $example "pipeline")
    if ($Watch) { Start-Sleep -Seconds $IntervalSeconds }
} while ($Watch)
