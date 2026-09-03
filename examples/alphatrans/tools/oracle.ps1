<#
.SYNOPSIS
  Run the AlphaTrans oracle (the human-written Python tests) against a translation.

.DESCRIPTION
  This is the ONLY sanctioned way to score a translation, and it exists to make the
  oracle tamper-evident and invisible to the agents.

  The oracle tests are never placed in the working copy. Instead, every scored run:

    1. VERIFIES .oracle-master against its SHA256 manifest. Any mismatch, missing or
       extra file aborts the run with ORACLE-TAMPERED -- an agent that edited the
       oracle produces a loud failure, not a silent pass.
    2. Builds a throwaway staging tree:
           <staging>/src/main   <- copied from the working copy (the translation)
           <staging>/src/test   <- copied from .oracle-master (pristine)
           <staging>/pytest.ini, conftest.py
    3. Runs pytest there with PYTHONPATH=<staging>.
    4. Deletes the staging tree.

  Because src/test only ever exists inside the throwaway tree, the agents cannot
  read the oracle from their own working copy.

.PARAMETER Gate
  Optional pytest -k expression selecting the milestone's cumulative test subset.
  Omit to run the whole suite.

.PARAMETER Baseline
  Score a reference translation instead of the working copy:
    golden   -> AlphaTrans's manually verified translation (expected: all pass)
    skeleton -> the unimplemented interface (expected: fail)
  Use these to establish the ceiling and floor of the harness.

.EXAMPLE
  ./tools/oracle.ps1
  ./tools/oracle.ps1 -Gate "OptionTest or CommandLineTest"
  ./tools/oracle.ps1 -Baseline golden
#>
param(
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

$ErrorActionPreference = "Stop"
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$example = Split-Path -Parent $here

$oracleMaster = Join-Path $example ".oracle-master"
$scaffold     = Join-Path $example ".scaffold"
$workingCopy  = Join-Path $example "pipeline\project"
$staging      = Join-Path $example "pipeline\_oracle_run"

if (-not (Test-Path $oracleMaster)) { throw "No .oracle-master. Run setup.ps1 first." }

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
    Write-Host "ORACLE-TAMPERED: the fixed oracle no longer matches its manifest." -ForegroundColor Red
    $problems | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Re-run setup.ps1 to restore, and treat this run as INVALID."
    exit 3
}

# --------------------------------------------------------------------------- #
# 2. Pick the src/main to score.
# --------------------------------------------------------------------------- #
switch ($Baseline) {
    "golden" {
        $cfg = Join-Path $example "codeweaver.toml"
        if (-not (Test-Path $cfg)) { throw "codeweaver.toml missing. Run setup.ps1 first." }
        $proj = ((Select-String -Path $cfg -Pattern '^name\s*=\s*"alphatrans-(.+?)"').Matches[0].Groups[1].Value)
        $ds   = ((Select-String -Path $cfg -Pattern '^#\s*dataset_root\s*=\s*(.+)$').Matches[0].Groups[1].Value).Trim()
        $srcMain = Join-Path $ds "data\manually_verified_translations\$proj\manual_translation\src\main"
        if (-not (Test-Path $srcMain)) { throw "Golden translation not found: $srcMain" }
    }
    "skeleton" { $srcMain = Join-Path $scaffold "src\main" }
    default    { $srcMain = Join-Path $workingCopy "src\main" }
}
if (-not (Test-Path $srcMain)) { throw "No translation to score at: $srcMain" }

# --------------------------------------------------------------------------- #
# 3. Stage: translation + pristine oracle, in a throwaway tree.
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
# 4. Run pytest.
#    An EMPTY gate means the milestone selected no oracle tests (typically M0, the
#    skeleton milestone). That is not "run everything" -- it is "this milestone has
#    no oracle obligation yet". Running the full suite here would fail M0 forever
#    and burn its whole repair budget.
# --------------------------------------------------------------------------- #
if (-not $All -and -not $Gate.Trim()) {
    Write-Host "[oracle] source   : $srcMain"
    Write-Host "[oracle] gate     : (empty - milestone selects no oracle tests)"
    Write-Host "[oracle] result   : skipped; no oracle obligation for this milestone"
    Write-Host "[oracle] exitcode : 0"
    if (-not $KeepStaging -and (Test-Path $staging)) { Remove-Item -Recurse -Force $staging }
    exit 0
}

$pytestArgs = @()
if ($Gate.Trim()) { $pytestArgs = @("-k", $Gate) }

# Deselect the environment-broken baseline: tests that fail even against AlphaTrans's
# own manually verified translation (locale/timezone-sensitive cases in
# commons-validator). They measure the environment, not the translation under test,
# so charging them to CodeWeaver would understate its score. Recorded by
# `setup` via -RecordExclusions.
$exclusionFile = Join-Path $oracleMaster "baseline_excluded.txt"
$excluded = @()
if (-not $RecordExclusions -and (Test-Path $exclusionFile)) {
    $excluded = @(Get-Content $exclusionFile | Where-Object { $_.Trim() -and -not $_.StartsWith("#") })
    foreach ($nodeid in $excluded) { $pytestArgs += @("--deselect", $nodeid.Trim()) }
}

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
# 5. Summarize for the Validator agent, then clean up.
#    pytest's final status line is the LAST line that both starts/ends with '=' and
#    carries a count. Matching on '=' alone would catch section separators such as
#    '==== ERROR at teardown of X ====', so require a leading count token.
# --------------------------------------------------------------------------- #
$countLine = '\d+\s+(passed|failed|error|errors|skipped|deselected|xfailed|xpassed)'
$summary = ($out | Select-String -Pattern "^=+.*$countLine.*=+$" | Select-Object -Last 1)
if (-not $summary) { $summary = ($out | Select-String -Pattern "^\s*$countLine" | Select-Object -Last 1) }
if (-not $summary) { $summary = ($out | Select-String -Pattern $countLine | Select-Object -Last 1) }

# Record the environment-broken baseline (setup runs this once against `golden`).
if ($RecordExclusions) {
    $failing = @($out | Select-String -Pattern '^(FAILED|ERROR)\s+(\S+::\S+)' |
                 ForEach-Object { $_.Matches[0].Groups[2].Value } | Sort-Object -Unique)
    $header = @(
        "# Tests that FAIL or ERROR against AlphaTrans's own manually verified",
        "# translation in THIS environment. They measure the environment (locale,",
        "# timezone, platform), not the translation under test, so every scored run",
        "# deselects them. Regenerate with: setup.ps1 (or oracle.ps1 -Baseline golden",
        "# -All -RecordExclusions). Excluded from the tamper manifest by design.",
        "# Recorded: $(Get-Date -Format o)"
    )
    Set-Content -Path $exclusionFile -Value ($header + $failing) -Encoding utf8
    Write-Host "[oracle] recorded $($failing.Count) environment-broken test(s) -> $exclusionFile"
}

# pytest exit 5 = "no tests were collected". For a milestone gate that names a test
# class which does not exist (the mechanical <Class>Test convention does not always
# land), that is "this milestone has no oracle obligation", not a failure.
if ($code -eq 5) {
    Write-Host "[oracle] note     : gate '$Gate' selected no tests -> treating as no obligation"
    $code = 0
}
Write-Host ""
Write-Host "[oracle] source   : $srcMain"
Write-Host "[oracle] gate     : $(if ($Gate) { $Gate } else { '(whole suite)' })"
if ($excluded.Count -gt 0) {
    Write-Host "[oracle] excluded : $($excluded.Count) environment-broken test(s) (baseline_excluded.txt)"
}
Write-Host "[oracle] result   : $($summary -replace '=','' -replace '\s+',' ')".Trim()
Write-Host "[oracle] exitcode : $code"

if (-not $KeepStaging -and (Test-Path $staging)) { Remove-Item -Recurse -Force $staging }
exit $code
