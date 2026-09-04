<#
.SYNOPSIS
  Print the live status of a CodeWeaver run from its SQLite persister.

.DESCRIPTION
  The Burr telemetry UI only shows runs whose tracker was enabled (it needs the
  optional `apache-burr[start]` extra installed AND CODEWEAVER_NO_TRACKER unset).
  The SQLite persister is always written after every action, so it is the
  authoritative record either way.

.EXAMPLE
  ./tools/status.ps1 -Project commons-cli
  ./tools/status.ps1 -All
  ./tools/status.ps1 -Project commons-csv -Watch
#>
param(
    [string]$Project,
    [switch]$All,
    [switch]$Watch,
    [int]$IntervalSeconds = 60
)

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$example = Split-Path -Parent $here

if (-not $All -and -not $Project) { throw "Pass -Project <name> or -All." }
$targets = if ($All) {
    Get-ChildItem (Join-Path $example "subjects") -Directory -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Name
} else { @($Project) }

$py = @'
import json, os, sqlite3, sys

pipeline = sys.argv[1]
db = os.path.join(pipeline, "burr.db")
if not os.path.exists(db):
    print("  (no run yet)"); raise SystemExit(0)

con = sqlite3.connect(db)
try:
    cols = [d[0] for d in con.execute("select * from codeweaver_state limit 1").description]
except Exception:
    print("  (no state table yet)"); raise SystemExit(0)
row = con.execute("select * from codeweaver_state order by rowid desc limit 1").fetchone()
if row is None:
    print("  (run started; no state persisted yet)"); raise SystemExit(0)
d = dict(zip(cols, row))
st = json.loads(d["state"]) if isinstance(d.get("state"), str) else d.get("state")

ms = []
mp = os.path.join(pipeline, "milestones.json")
if os.path.exists(mp):
    raw = json.load(open(mp, encoding="utf-8"))
    ms = raw if isinstance(raw, list) else raw.get("milestones", [])

hist   = st.get("history", [])
passed = {h["milestone"] for h in hist if h.get("passed")}
gave   = {h["milestone"] for h in hist if h.get("gave_up")}
idx    = st.get("milestone_idx", 0)

print(f"  app_id     : {d.get('app_id')}")
print(f"  position   : milestone {idx} of {st.get('last_idx')}")
print(f"  repair     : iter {st.get('iter_count')} of {st.get('max_iter')}")
print(f"  last agent : {st.get('last_agent')}")
print(f"  parity     : round {st.get('parity_round', 0)} of {st.get('max_parity_rounds')}  complete={st.get('parity_complete')}")
print(f"  done       : {st.get('done')}   skipped: {st.get('skipped') or '[]'}")
if ms:
    print()
    for i, m in enumerate(ms):
        mid = m.get("id")
        mark = ("SKIP" if mid in gave else "PASS" if mid in passed
                else ">>>>" if i == idx else "  - " if i < idx else "    ")
        print(f"    {mark} {mid:4} {m.get('title','')}")
if hist:
    print()
    for h in hist[-8:]:
        flag = "  GAVE-UP" if h.get("gave_up") else ""
        if h.get("retry_for"): flag += f"  [retry {h['retry_for']}]"
        print(f"    {h['milestone']:4} iter={h['iter']} passed={h['passed']}{flag}")
rp = os.path.join(pipeline, "report.json")
if os.path.exists(rp):
    try:
        r = json.load(open(rp, encoding="utf-8"))
        t = r.get("tests", {})
        print(f"\n  last report: {r.get('milestone')} passed={r.get('passed')}")
        for L in ("unit", "e2e"):
            if L in t:
                v = t[L]
                print(f"    {L:5} total={v.get('total')} passed={v.get('passed')} failed={v.get('failed')}")
    except Exception:
        pass
'@

$tmp = Join-Path $env:TEMP "cw_status.py"
Set-Content -Path $tmp -Value $py -Encoding utf8

do {
    if ($Watch) { Clear-Host; Write-Host "=== $(Get-Date -Format 'HH:mm:ss') ===" }
    foreach ($t in $targets) {
        Write-Host ""
        Write-Host "==================== $t ===================="
        python $tmp (Join-Path $example "subjects\$t\pipeline")
    }
    if ($Watch) { Start-Sleep -Seconds $IntervalSeconds }
} while ($Watch)
