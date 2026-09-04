<#
.SYNOPSIS
  Materialize one (or all) AlphaTrans subject project(s) for CodeWeaver.

.DESCRIPTION
  AlphaTrans (FSE 2025, arXiv:2410.24117) ships ten Java subject projects, but only
  FOUR carry a manually verified Python translation. Only those four give us a
  trustworthy fixed oracle; see README.md ("Why only four projects").

  Each subject is materialized into its own directory so a campaign over several
  projects never clobbers a previous subject's artifacts:

    subjects/<project>/
      .scaffold/        interface skeleton (typed signatures, `pass` bodies)
      .oracle-master/   pristine human-written tests + pytest harness + SHA256 manifest
      codeweaver.toml   generated from ../../codeweaver.template.toml
      pipeline/         run artifacts (created by the run itself)

.EXAMPLE
  ./setup.ps1 -Project commons-cli
  ./setup.ps1 -All -SkipBaseline
  ./setup.ps1 -Project commons-validator -Dataset D:\src\AlphaTrans

.NOTES
  Prereqs: Python 3.11+ with pytest (and `tzdata` for commons-validator).
  No JDK, GraalVM, CodeQL, Maven or Docker is needed -- those are only required by
  AlphaTrans's own pipeline, not by this harness.
#>
param(
    [ValidateSet("commons-cli", "commons-csv", "commons-fileupload", "commons-validator")]
    [string]$Project,

    [switch]$All,

    [string]$Dataset = "$HOME\Desktop\AlphaTrans",

    [switch]$SkipBaseline
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# The four AlphaTrans subjects that ship a manually verified Python translation.
$SUBJECTS = @("commons-cli", "commons-csv", "commons-fileupload", "commons-validator")

if (-not $All -and -not $Project) {
    throw "Pass -Project <name> or -All. Available: $($SUBJECTS -join ', ')"
}
$targets = if ($All) { $SUBJECTS } else { @($Project) }

function Initialize-Subject {
    param([string]$Name)

    $javaSrc  = Join-Path $Dataset "java_projects\cleaned_final_projects_decomposed_tests\$Name\src\main"
    $skeleton = Join-Path $Dataset "data\skeletons\$Name\src\main"
    $oracle   = Join-Path $Dataset "data\manually_verified_translations\$Name\manual_translation"

    if (-not (Test-Path $javaSrc))  { throw "[$Name] Java source not found: $javaSrc" }
    if (-not (Test-Path $skeleton)) { throw "[$Name] Skeleton (interface) not found: $skeleton" }
    if (-not (Test-Path (Join-Path $oracle "src\test"))) { throw "[$Name] Oracle tests not found: $oracle\src\test" }

    $subject = Join-Path $here "subjects\$Name"
    New-Item -ItemType Directory -Force -Path $subject | Out-Null

    # ---- .scaffold = the interface skeleton (src/main ONLY) -------------------
    # The skeleton tree also ships a src/test directory holding AlphaTrans's own
    # translated-test skeletons. We deliberately DROP it: those test method names
    # would leak the oracle's surface into the agents' working copy.
    $scaffold = Join-Path $subject ".scaffold"
    if (Test-Path $scaffold) { Remove-Item -Recurse -Force $scaffold }
    New-Item -ItemType Directory -Force -Path "$scaffold\src" | Out-Null
    Copy-Item -Recurse $skeleton "$scaffold\src\main"
    Set-Content -Path "$scaffold\src\__init__.py" -Value "" -NoNewline
    if (-not (Test-Path "$scaffold\src\main\__init__.py")) {
        Set-Content -Path "$scaffold\src\main\__init__.py" -Value "" -NoNewline
    }

    # ---- .oracle-master = pristine oracle + harness + hash manifest -----------
    $oracleMaster = Join-Path $subject ".oracle-master"
    if (Test-Path $oracleMaster) { Remove-Item -Recurse -Force $oracleMaster }
    New-Item -ItemType Directory -Force -Path $oracleMaster | Out-Null
    Copy-Item -Recurse (Join-Path $oracle "src\test") "$oracleMaster\test"
    foreach ($harness in @("pytest.ini", "conftest.py")) {
        $p = Join-Path $oracle $harness
        if (Test-Path $p) { Copy-Item $p (Join-Path $oracleMaster $harness) }
    }

    # Tamper manifest. tools/oracle.ps1 re-verifies this before each scored run, so an
    # agent editing the oracle is a reported FAILURE rather than a silent pass.
    # baseline_excluded.txt is harness bookkeeping, not oracle content -> not hashed.
    $manifest  = Join-Path $oracleMaster "SHA256SUMS.txt"
    $nonOracle = @("SHA256SUMS.txt", "baseline_excluded.txt")
    Get-ChildItem $oracleMaster -Recurse -File |
        Where-Object { $nonOracle -notcontains $_.Name } |
        ForEach-Object {
            $rel = $_.FullName.Substring($oracleMaster.Length + 1)
            "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)  $rel"
        } | Set-Content -Path $manifest -Encoding utf8

    # ---- codeweaver.toml -----------------------------------------------------
    # The template wraps __VALIDATE_CMD__ in a TOML literal string ('...'), so the
    # embedded double quotes around {gate} need no escaping.
    $validate = 'pwsh -NoProfile -File ../../tools/oracle.ps1 -Project ' + $Name + ' -Gate "{gate}"'
    $tpl = Get-Content (Join-Path $here "codeweaver.template.toml") -Raw
    $tpl = $tpl.Replace("__PROJECT__", $Name)
    $tpl = $tpl.Replace("__PROJECT_SLUG__", $Name)
    $tpl = $tpl.Replace("__JAVA_SRC_ABS__", $javaSrc.Replace("\", "\\"))
    $tpl = $tpl.Replace("__DATASET_ROOT__", (Resolve-Path $Dataset).Path)
    $tpl = $tpl.Replace("__VALIDATE_CMD__", $validate)
    # Write WITHOUT a BOM (tomllib rejects a leading BOM).
    [System.IO.File]::WriteAllText((Join-Path $subject "codeweaver.toml"), $tpl,
                                   (New-Object System.Text.UTF8Encoding($false)))

    # ---- clear stale run state ----------------------------------------------
    $pipeline = Join-Path $subject "pipeline"
    if (Test-Path $pipeline) { Remove-Item -Recurse -Force $pipeline }

    # ---- record the environment-broken baseline ------------------------------
    # Run the oracle against AlphaTrans's OWN manually verified translation. Any test
    # that fails there is broken by this environment (locale, timezone, platform), not
    # by the translation under test -- commons-validator has ten such cases. Every
    # scored run deselects them, so they are never charged to CodeWeaver.
    if (-not $SkipBaseline) {
        Write-Host "[$Name] recording environment-broken baseline..."
        & (Join-Path $here "tools\oracle.ps1") -Project $Name -Baseline golden -All -RecordExclusions | Out-Null
    }

    $nJava   = (Get-ChildItem $javaSrc -Recurse -Filter *.java).Count
    $nIface  = (Get-ChildItem "$scaffold\src\main" -Recurse -Filter *.py | Where-Object Name -ne "__init__.py").Count
    $nOracle = (Get-ChildItem "$oracleMaster\test" -Recurse -Filter *.py | Where-Object Name -ne "__init__.py").Count
    $exclF   = Join-Path $oracleMaster "baseline_excluded.txt"
    $nExcl   = if (Test-Path $exclF) { @(Get-Content $exclF | Where-Object { $_.Trim() -and -not $_.StartsWith('#') }).Count } else { 0 }

    "{0,-20} java:{1,4}  iface:{2,4}  oracle-mods:{3,4}  env-broken:{4,3}" -f $Name, $nJava, $nIface, $nOracle, $nExcl
}

Write-Host "[setup] dataset: $Dataset"
Write-Host ""
foreach ($t in $targets) { Initialize-Subject -Name $t }
Write-Host ""
Write-Host "Next:"
Write-Host "  pwsh examples/alphatrans/tools/smoke_all.ps1              # offline mock smoke test, all subjects (free)"
Write-Host "  pwsh examples/alphatrans/tools/oracle.ps1 -Project commons-cli -Baseline golden -All"
Write-Host "  python -m codeweaver run --config examples/alphatrans/subjects/commons-cli/codeweaver.toml --app-id <id>"
