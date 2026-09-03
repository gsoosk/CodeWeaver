<#
.SYNOPSIS
  Prepare the CodeWeaver AlphaTrans (Java -> Python) example for one subject project.

.DESCRIPTION
  AlphaTrans (FSE 2025, arXiv:2410.24117) ships, for four of its ten subject
  projects, a MANUALLY VERIFIED Python translation that passes 100% of its tests.
  We reuse three of its assets and nothing else -- we do NOT run AlphaTrans's
  pipeline:

    * java_projects/cleaned_final_projects_decomposed_tests/<proj>  -> the Java SOURCE
    * data/skeletons/<proj>/src/main                                -> the INTERFACE
      (typed Python class/method signatures with `pass` bodies, including the
      disambiguated overload names such as hasOption1 / hasOption2)
    * data/manually_verified_translations/<proj>/manual_translation/src/test
                                                                    -> the ORACLE
      (human-written Python tests; never authored or edited by the agents)

  This script materializes:
    .scaffold/        a clean copy of the skeleton's src/main (the working copy is
                      copied FROM this; it is never edited)
    .oracle-master/   a pristine, hash-manifested copy of the oracle tests plus the
                      pytest harness files. tools/oracle.ps1 restores from here and
                      verifies the manifest before every scored run.
    codeweaver.toml   rendered from codeweaver.template.toml with resolved paths.

  The oracle is deliberately kept OUT of the working copy: tools/oracle.ps1 stages
  src/main (from the working copy) and src/test (from .oracle-master) into a
  throwaway directory at validation time, so the agents never have the tests on
  disk in a directory they can read.

.EXAMPLE
  ./setup.ps1 -Project commons-cli
  ./setup.ps1 -Project commons-validator -Dataset D:\src\AlphaTrans

.NOTES
  Prereqs: Python 3.11+ with pytest (and `tzdata` for commons-validator).
  No JDK, GraalVM, CodeQL, Maven or Docker is needed -- those are only required by
  AlphaTrans's own pipeline, not by this harness.

  Only these four projects ship a manually verified oracle:
    commons-cli, commons-csv, commons-fileupload, commons-validator
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("commons-cli", "commons-csv", "commons-fileupload", "commons-validator")]
    [string]$Project,

    [string]$Dataset = "$HOME\Desktop\AlphaTrans",

    [switch]$SkipBaseline
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# --------------------------------------------------------------------------- #
# 0. Locate the three AlphaTrans assets.
# --------------------------------------------------------------------------- #
$javaSrc  = Join-Path $Dataset "java_projects\cleaned_final_projects_decomposed_tests\$Project\src\main"
$skeleton = Join-Path $Dataset "data\skeletons\$Project\src\main"
$oracle   = Join-Path $Dataset "data\manually_verified_translations\$Project\manual_translation"

if (-not (Test-Path $javaSrc))  { throw "Java source not found: $javaSrc  (check -Dataset / -Project)" }
if (-not (Test-Path $skeleton)) { throw "Skeleton (interface) not found: $skeleton" }
if (-not (Test-Path $oracle))   { throw "Manually verified translation not found: $oracle`nOnly commons-cli, commons-csv, commons-fileupload and commons-validator ship one." }
if (-not (Test-Path (Join-Path $oracle "src\test"))) { throw "Oracle tests not found: $oracle\src\test" }

# --------------------------------------------------------------------------- #
# 1. .scaffold/ = the interface skeleton (src/main only; NEVER the tests).
#    The skeleton tree also contains a src/test directory holding AlphaTrans's own
#    translated-test skeletons. We deliberately DROP it: test method names would
#    leak the oracle's surface into the agents' working copy.
# --------------------------------------------------------------------------- #
$scaffold = Join-Path $here ".scaffold"
if (Test-Path $scaffold) { Remove-Item -Recurse -Force $scaffold }
New-Item -ItemType Directory -Force -Path "$scaffold\src" | Out-Null
Copy-Item -Recurse $skeleton "$scaffold\src\main"

# package __init__.py files so `src.main.<pkg>` imports resolve
Set-Content -Path "$scaffold\src\__init__.py" -Value "" -NoNewline
if (-not (Test-Path "$scaffold\src\main\__init__.py")) {
    Set-Content -Path "$scaffold\src\main\__init__.py" -Value "" -NoNewline
}

# --------------------------------------------------------------------------- #
# 2. .oracle-master/ = pristine oracle tests + pytest harness + a hash manifest.
# --------------------------------------------------------------------------- #
$oracleMaster = Join-Path $here ".oracle-master"
if (Test-Path $oracleMaster) { Remove-Item -Recurse -Force $oracleMaster }
New-Item -ItemType Directory -Force -Path $oracleMaster | Out-Null
Copy-Item -Recurse (Join-Path $oracle "src\test") "$oracleMaster\test"

foreach ($harness in @("pytest.ini", "conftest.py")) {
    $p = Join-Path $oracle $harness
    if (Test-Path $p) { Copy-Item $p (Join-Path $oracleMaster $harness) }
}

# Tamper manifest: every oracle file, hashed. tools/oracle.ps1 re-verifies this
# before each scored run, so an agent editing the oracle is a reported FAILURE
# rather than a silent pass.
$manifest = Join-Path $oracleMaster "SHA256SUMS.txt"
$nonOracle = @("SHA256SUMS.txt", "baseline_excluded.txt")
Get-ChildItem $oracleMaster -Recurse -File |
    Where-Object { $nonOracle -notcontains $_.Name } |
    ForEach-Object {
        $rel = $_.FullName.Substring($oracleMaster.Length + 1)
        "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)  $rel"
    } | Set-Content -Path $manifest -Encoding utf8

# --------------------------------------------------------------------------- #
# 3. Render codeweaver.toml.
# --------------------------------------------------------------------------- #
$tpl = Get-Content (Join-Path $here "codeweaver.template.toml") -Raw
$tpl = $tpl.Replace("__PROJECT__", $Project)
$tpl = $tpl.Replace("__PROJECT_SLUG__", $Project.Replace(".", "-"))
$tpl = $tpl.Replace("__JAVA_SRC_ABS__", $javaSrc.Replace("\", "\\"))
$tpl = $tpl.Replace("__DATASET_ROOT__", (Resolve-Path $Dataset).Path)
# Write WITHOUT a BOM (tomllib rejects a leading BOM).
[System.IO.File]::WriteAllText((Join-Path $here "codeweaver.toml"), $tpl, (New-Object System.Text.UTF8Encoding($false)))

# --------------------------------------------------------------------------- #
# 4. Clear stale run state so a retarget starts clean.
# --------------------------------------------------------------------------- #
$pipeline = Join-Path $here "pipeline"
if (Test-Path $pipeline) { Remove-Item -Recurse -Force $pipeline }

# --------------------------------------------------------------------------- #
# 4b. Record the environment-broken baseline.
#     Run the oracle against AlphaTrans's OWN manually verified translation. Any
#     test that fails there is broken by this environment (locale, timezone,
#     platform), not by the translation under test -- commons-validator has ten such
#     cases. Every scored run deselects them, so they are never charged to
#     CodeWeaver. Skip with -SkipBaseline (commons-csv takes a couple of minutes).
# --------------------------------------------------------------------------- #
if (-not $SkipBaseline) {
    Write-Host "[setup] recording environment-broken baseline (running the golden translation)..."
    & (Join-Path $here "tools\oracle.ps1") -Baseline golden -All -RecordExclusions | Out-Null
}

# --------------------------------------------------------------------------- #
# 5. Report.
# --------------------------------------------------------------------------- #
$nJava     = (Get-ChildItem $javaSrc -Recurse -Filter *.java).Count
$nIface    = (Get-ChildItem "$scaffold\src\main" -Recurse -Filter *.py | Where-Object Name -ne "__init__.py").Count
$nOracle   = (Get-ChildItem "$oracleMaster\test" -Recurse -Filter *.py | Where-Object Name -ne "__init__.py").Count
$nHashed   = (Get-Content $manifest).Count
$exclFile  = Join-Path $oracleMaster "baseline_excluded.txt"
$nExcluded = if (Test-Path $exclFile) { @(Get-Content $exclFile | Where-Object { $_.Trim() -and -not $_.StartsWith('#') }).Count } else { 0 }

Write-Host "[setup] project          : $Project"
Write-Host "[setup] java source      : $javaSrc  ($nJava .java files)"
Write-Host "[setup] interface        : $scaffold\src\main  ($nIface modules, 'pass' bodies)"
Write-Host "[setup] oracle (hidden)  : $oracleMaster  ($nOracle test modules, $nHashed files hashed)"
Write-Host "[setup] env-broken       : $nExcluded test(s) deselected from every scored run (fail on the golden translation too)"
Write-Host "[setup] wrote            : $(Join-Path $here 'codeweaver.toml')"
Write-Host ""
Write-Host "Next:"
Write-Host "  pwsh examples/alphatrans/tools/oracle.ps1 -Baseline golden   # ceiling: golden translation should pass"
Write-Host "  pwsh examples/alphatrans/tools/oracle.ps1 -Baseline skeleton # floor:   unimplemented skeleton should fail"
Write-Host "  python -m codeweaver check --config examples/alphatrans/codeweaver.toml"
Write-Host "  python -m codeweaver run   --config examples/alphatrans/codeweaver.toml --app-id alphatrans-$Project-001"
