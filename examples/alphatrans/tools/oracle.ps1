<#
.SYNOPSIS
  Run the AlphaTrans oracle (the human-written Python tests) against a translation.

.DESCRIPTION
  This is the ONLY sanctioned way to score a translation, and it exists to make the
  oracle tamper-evident and invisible to the agents.

  The oracle tests are never placed in the working copy. Instead, every scored run:

    1. VERIFIES <subject>/.oracle-master against its SHA256 manifest. Any mismatch,
       missing or extra file aborts with ORACLE-TAMPERED (exit 3) -- an agent that
       edited the oracle produces a loud failure, not a silent pass.
    2. Builds a throwaway staging tree:
           <staging>/src/main   <- the translation under test
           <staging>/src/test   <- from .oracle-master (pristine)
           <staging>/pytest.ini, conftest.py
    3. Resolves each mechanical <Class>Test gate token to the EXACT oracle test file
       (never `pytest -k`, whose substring matching pulls later milestones' tests
       into earlier gates).
    4. Runs pytest there with PYTHONPATH=<staging>, deselecting the environment-broken
       baseline and any skip-on-give-up deferrals.
    5. Deletes the staging tree.

.PARAMETER Project
  Which subject under subjects/ to score. Required.

.PARAMETER Gate
  Space-separated mechanical <Class>Test tokens for the milestone's cumulative gate.
  Empty means "this milestone has no oracle obligation" (typically M0).

.PARAMETER Baseline
  Score a reference translation instead of the working copy:
    golden   -> AlphaTrans's manually verified translation (expected: all pass)
    skeleton -> the unimplemented interface (expected: fail)

.EXAMPLE
  ./tools/oracle.ps1 -Project commons-cli -Baseline golden -All
  ./tools/oracle.ps1 -Project commons-cli -Gate "OptionTest CommandLineTest"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Project,

    [string]$Gate = "",

    [ValidateSet("", "golden", "skeleton")]
    [string]$Baseline = "",

    [switch]$All,
    [switch]$RecordExclusions,
    [switch]$KeepStaging
)

# Files inside .oracle-master that are harness bookkeeping, not oracle content, and
# so are excluded from the tamper manifest.
$script:NonOracleFiles = @("SHA256SUMS.txt", "baseline_excluded.txt")

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$example = Split-Path -Parent $here
$subject = Join-Path $example "subjects\$Project"

$oracleMaster = Join-Path $subject ".oracle-master"
$scaffold     = Join-Path $subject ".scaffold"
$workingCopy  = Join-Path $subject "pipeline\project"
$staging      = Join-Path $subject "pipeline\_oracle_run"

if (-not (Test-Path $oracleMaster)) { throw "No .oracle-master for '$Project'. Run setup.ps1 -Project $Project first." }

# --------------------------------------------------------------------------- #
# 1. Verify the oracle has not been modified.
# --------------------------------------------------------------------------- #
$manifest = Join-Path $oracleMaster "SHA256SUMS.txt"
if (-not (Test-Path $manifest)) { throw "ORACLE-TAMPERED: manifest missing ($manifest)" }

$expected = @{}
foreach ($line in Get-Content $manifest) {
    if ($line -match '^([0-9A-Fa-f]{64})\s\s(.+)$') { $expected[$Matches[2]] = $Matches[1].ToUpper() }
}
$actual = @{}
Get-ChildItem $oracleMaster -Recurse -File |
    Where-Object { $script:NonOracleFiles -notcontains $_.Name } |
    ForEach-Object {
        $rel = $_.FullName.Substring($oracleMaster.Length + 1)
        $actual[$rel] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToUpper()
    }

$problems = @()
foreach ($k in $expected.Keys) {
    if (-not $actual.ContainsKey($k))      { $problems += "MISSING  $k" }
    elseif ($actual[$k] -ne $expected[$k]) { $problems += "MODIFIED $k" }
}
foreach ($k in $actual.Keys) {
    if (-not $expected.ContainsKey($k))    { $problems += "ADDED    $k" }
}
if ($problems.Count -gt 0) {
    Write-Host "ORACLE-TAMPERED [$Project]: the fixed oracle no longer matches its manifest." -ForegroundColor Red
    $problems | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Re-run setup.ps1 -Project $Project to restore, and treat this run as INVALID."
    exit 3
}

# --------------------------------------------------------------------------- #
# 2. Pick the src/main to score.
# --------------------------------------------------------------------------- #
switch ($Baseline) {
    "golden" {
        $cfg = Join-Path $subject "codeweaver.toml"
        if (-not (Test-Path $cfg)) { throw "codeweaver.toml missing for '$Project'." }
        $ds = ((Select-String -Path $cfg -Pattern '^#\s*dataset_root\s*=\s*(.+)$').Matches[0].Groups[1].Value).Trim()
        $srcMain = Join-Path $ds "data\manually_verified_translations\$Project\manual_translation\src\main"
        if (-not (Test-Path $srcMain)) { throw "Golden translation not found: $srcMain" }
    }
    "skeleton" { $srcMain = Join-Path $scaffold "src\main" }
    default    { $srcMain = Join-Path $workingCopy "src\main" }
}
if (-not (Test-Path $srcMain)) { throw "No translation to score at: $srcMain" }

# --------------------------------------------------------------------------- #
# 3. An empty gate = this milestone has no oracle obligation yet (typically M0).
#    Running the whole suite here would fail M0 forever and burn its repair budget.
# --------------------------------------------------------------------------- #
if (-not $All -and -not $Gate.Trim()) {
    Write-Host "[oracle] project  : $Project"
    Write-Host "[oracle] source   : $srcMain"
    Write-Host "[oracle] gate     : (empty - milestone selects no oracle tests)"
    Write-Host "[oracle] result   : skipped; no oracle obligation for this milestone"
    Write-Host "[oracle] exitcode : 0"
    exit 0
}

# --------------------------------------------------------------------------- #
# 4. Stage: translation + pristine oracle, in a throwaway tree.
# --------------------------------------------------------------------------- #
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path "$staging\src" | Out-Null
Copy-Item -Recurse $srcMain "$staging\src\main"
Copy-Item -Recurse (Join-Path $oracleMaster "test") "$staging\src\test"
foreach ($harness in @("pytest.ini", "conftest.py")) {
    $p = Join-Path $oracleMaster $harness
    if (Test-Path $p) { Copy-Item $p (Join-Path $staging $harness) }
}
foreach ($pkg in @("$staging\src", "$staging\src\main", "$staging\src\test")) {
    $init = Join-Path $pkg "__init__.py"
    if (-not (Test-Path $init)) { Set-Content -Path $init -Value "" -NoNewline }
}

# --------------------------------------------------------------------------- #
# 5. Resolve gate tokens to exact oracle test FILES.
# --------------------------------------------------------------------------- #
$pytestArgs = @()
if ($Gate.Trim()) {
    $tokens = @($Gate -split '\s+or\s+|\s+' | ForEach-Object { $_.Trim() } |
                Where-Object { $_ -and $_ -notin @('or','and','not') })
    $selectedFiles = @()
    $unresolved = @()
    foreach ($tok in ($tokens | Select-Object -Unique)) {
        $hit = Get-ChildItem (Join-Path $staging "src\test") -Recurse -Filter "$tok.py" -ErrorAction SilentlyContinue
        if ($hit) { $selectedFiles += ($hit | ForEach-Object { $_.FullName.Substring($staging.Length + 1) }) }
        else      { $unresolved += $tok }
    }
    if ($unresolved.Count -gt 0) {
        Write-Host "[oracle] note     : $($unresolved.Count) gate token(s) matched no oracle test file (no obligation): $($unresolved -join ', ')"
    }
    if ($selectedFiles.Count -eq 0) {
        Write-Host "[oracle] project  : $Project"
        Write-Host "[oracle] source   : $srcMain"
        Write-Host "[oracle] gate     : $Gate"
        Write-Host "[oracle] result   : gate selected no oracle tests -> no obligation for this milestone"
        Write-Host "[oracle] exitcode : 0"
        if (-not $KeepStaging -and (Test-Path $staging)) { Remove-Item -Recurse -Force $staging }
        exit 0
    }
    $pytestArgs += ($selectedFiles | Select-Object -Unique)
}

# Environment-broken baseline: tests that fail even against the golden translation.
$exclusionFile = Join-Path $oracleMaster "baseline_excluded.txt"
$excluded = @()
if (-not $RecordExclusions -and (Test-Path $exclusionFile)) {
    $excluded = @(Get-Content $exclusionFile | Where-Object { $_.Trim() -and -not $_.StartsWith("#") })
    foreach ($nodeid in $excluded) { $pytestArgs += @("--deselect", $nodeid.Trim()) }
}

# Tests deferred by skip-on-give-up.
$skipsFile = Join-Path $subject "pipeline\skips.json"
if (-not $RecordExclusions -and (Test-Path $skipsFile)) {
    try {
        $skipsJson = Get-Content $skipsFile -Raw | ConvertFrom-Json
        foreach ($nodeid in @($skipsJson.tests_to_skip | Where-Object { $_ -and "$_".Contains("::") })) {
            $pytestArgs += @("--deselect", "$nodeid".Trim())
        }
    } catch { }
}

# --------------------------------------------------------------------------- #
# 6. Run pytest.
# --------------------------------------------------------------------------- #
Push-Location $staging
$prevPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $staging
try {
    & python -m pytest @pytestArgs 2>&1 | Tee-Object -Variable out | Out-Host
    $code = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $prevPythonPath
    Pop-Location
}

# --------------------------------------------------------------------------- #
# 7. Summarize, record exclusions if asked, clean up.
#    pytest's final status line is the last line that both starts/ends with '=' AND
#    carries a count -- matching on '=' alone would catch section separators such as
#    '==== ERROR at teardown of X ===='.
# --------------------------------------------------------------------------- #
$countLine = '\d+\s+(passed|failed|error|errors|skipped|deselected|xfailed|xpassed)'
$summary = ($out | Select-String -Pattern "^=+.*$countLine.*=+$" | Select-Object -Last 1)
if (-not $summary) { $summary = ($out | Select-String -Pattern "^\s*$countLine" | Select-Object -Last 1) }
if (-not $summary) { $summary = ($out | Select-String -Pattern $countLine | Select-Object -Last 1) }

if ($RecordExclusions) {
    $failing = @($out | Select-String -Pattern '^(FAILED|ERROR)\s+(\S+::\S+)' |
                 ForEach-Object { $_.Matches[0].Groups[2].Value } | Sort-Object -Unique)
    $header = @(
        "# Tests that FAIL or ERROR against AlphaTrans's own manually verified",
        "# translation in THIS environment. They measure the environment (locale,",
        "# timezone, platform), not the translation under test, so every scored run",
        "# deselects them. Excluded from the tamper manifest by design.",
        "# Subject: $Project    Recorded: $(Get-Date -Format o)"
    )
    Set-Content -Path $exclusionFile -Value ($header + $failing) -Encoding utf8
    Write-Host "[oracle] recorded $($failing.Count) environment-broken test(s) -> $exclusionFile"
}

# pytest exit 5 = "no tests were collected" -> a mechanical token matched nothing.
if ($code -eq 5) {
    Write-Host "[oracle] note     : gate selected no tests -> treating as no obligation"
    $code = 0
}

Write-Host ""
Write-Host "[oracle] project  : $Project"
Write-Host "[oracle] source   : $srcMain"
Write-Host "[oracle] gate     : $(if ($Gate) { $Gate } else { '(whole suite)' })"
if ($excluded.Count -gt 0) {
    Write-Host "[oracle] excluded : $($excluded.Count) environment-broken test(s)"
}
Write-Host "[oracle] result   : $($summary -replace '=','' -replace '\s+',' ')".Trim()
Write-Host "[oracle] exitcode : $code"

if (-not $KeepStaging -and (Test-Path $staging)) { Remove-Item -Recurse -Force $staging }
exit $code
