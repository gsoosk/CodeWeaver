<#
.SYNOPSIS
  Prepare the CodeWeaver Apache Commons Validator (Java -> Python) example.

.DESCRIPTION
  Points the example at a local clone of https://github.com/apache/commons-validator
  and generates codeweaver.toml from codeweaver.template.toml with resolved paths to
  the `routines` package (Java source) and its JUnit tests (behavioral spec).

.EXAMPLE
  ./setup.ps1
  ./setup.ps1 -Repo D:\src\commons-validator

.NOTES
  Prereqs: Python 3.11+ on PATH; a git clone of apache/commons-validator. No JDK
  is needed (the Java tests are translated into Python unittest, not executed).
#>
param(
    [string]$Repo = "$HOME\Desktop\_cw_local\commons-validator"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$main = Join-Path $Repo "src\main\java\org\apache\commons\validator\routines"
$test = Join-Path $Repo "src\test\java\org\apache\commons\validator\routines"
if (-not (Test-Path $main)) { throw "routines source not found: $main  (clone apache/commons-validator and pass -Repo)" }
if (-not (Test-Path $test)) { throw "routines tests not found: $test" }

$tpl = Get-Content (Join-Path $here "codeweaver.template.toml") -Raw
$tpl = $tpl.Replace("__ROUTINES_MAIN__", $main.Replace("\", "\\"))
$tpl = $tpl.Replace("__ROUTINES_TEST__", $test.Replace("\", "\\"))
# Write WITHOUT a BOM (tomllib rejects a leading BOM).
[System.IO.File]::WriteAllText((Join-Path $here "codeweaver.toml"), $tpl, (New-Object System.Text.UTF8Encoding($false)))

# Clear any stale run state.
$pipeline = Join-Path $here "pipeline"
if (Test-Path $pipeline) { Remove-Item -Recurse -Force $pipeline }

$nmain = (Get-ChildItem $main -Filter *.java -Recurse | Measure-Object).Count
$ntest = (Get-ChildItem $test -Filter *.java | Measure-Object).Count
Write-Host "[setup] commons-validator repo : $Repo"
Write-Host "[setup] routines source files  : $nmain    test files: $ntest"
Write-Host "[setup] wrote                  : $(Join-Path $here 'codeweaver.toml')"
Write-Host ""
Write-Host "Next (from the CodeWeaver repo root):"
Write-Host "  python -m codeweaver check --config examples/commons-validator/codeweaver.toml   # offline dry-run"
Write-Host "  python -m codeweaver run   --config examples/commons-validator/codeweaver.toml --app-id commons-validator-001"
