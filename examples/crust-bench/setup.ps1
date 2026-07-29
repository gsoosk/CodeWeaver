<#
.SYNOPSIS
  Prepare the CodeWeaver CRUST-Bench example for a chosen benchmark project.

.DESCRIPTION
  CRUST-Bench (arXiv:2504.15254) ships 100 C projects, each paired with a Rust
  interface + tests under datasets/RBench/<project> and C source under
  datasets/CBench/<project>. This script targets ONE project:
    * copies a clean scaffold (the RBench crate, minus .git/target) to .scaffold/
    * generates codeweaver.toml from codeweaver.template.toml with resolved paths.

.EXAMPLE
  ./setup.ps1 -Project bitset
  ./setup.ps1 -Project lambda-calculus-eval -Dataset D:\data\CRUST-bench\datasets

.NOTES
  Prereqs: Rust/cargo on PATH; the CRUST-Bench dataset extracted so that
  <Dataset>\CBench and <Dataset>\RBench exist. Download + extract from
  https://github.com/anirudhkhatry/CRUST-bench (datasets/CRUST_bench.zip).
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Project,
    [string]$Dataset = "$HOME\Desktop\_cw_local\CRUST-bench\datasets"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$cbench = Join-Path $Dataset "CBench\$Project"
$rbench = Join-Path $Dataset "RBench\$Project"
if (-not (Test-Path $cbench)) { throw "C source not found: $cbench  (check -Dataset and -Project)" }
if (-not (Test-Path $rbench)) { throw "Rust scaffold not found: $rbench (check -Dataset and -Project)" }

$iface = Join-Path $rbench "src\interfaces"
$tests = Join-Path $rbench "src\bin"
if (-not (Test-Path $iface)) { throw "No interfaces dir: $iface" }

# 1. Clean scaffold copy (the crate the agents fill in is copied FROM this).
$scaffold = Join-Path $here ".scaffold"
if (Test-Path $scaffold) { Remove-Item -Recurse -Force $scaffold }
Copy-Item -Recurse $rbench $scaffold
foreach ($junk in @(".git", "target")) {
    $p = Join-Path $scaffold $junk
    if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

# 2. Generate codeweaver.toml from the template.
$tpl = Get-Content (Join-Path $here "codeweaver.template.toml") -Raw
$tpl = $tpl.Replace("__PROJECT__", $Project)
$tpl = $tpl.Replace("__C_SOURCE_ABS__", $cbench.Replace("\", "\\"))
$tpl = $tpl.Replace("__IFACE_ABS__", $iface.Replace("\", "\\"))
$tpl = $tpl.Replace("__TESTS_ABS__", $tests.Replace("\", "\\"))
# Write WITHOUT a BOM (tomllib rejects a leading BOM).
[System.IO.File]::WriteAllText((Join-Path $here "codeweaver.toml"), $tpl, (New-Object System.Text.UTF8Encoding($false)))

# 3. Clear any stale run state for a fresh target.
$pipeline = Join-Path $here "pipeline"
if (Test-Path $pipeline) { Remove-Item -Recurse -Force $pipeline }

$nfns  = (Get-ChildItem $iface -Filter *.rs | ForEach-Object { Select-String -Path $_.FullName -Pattern 'pub fn ' } | Measure-Object).Count
$ntest = (Get-ChildItem $tests -Filter *.rs | ForEach-Object { Select-String -Path $_.FullName -Pattern '#\[test\]' } | Measure-Object).Count
Write-Host "[setup] target project : $Project"
Write-Host "[setup] scaffold        : $scaffold  (clean copy of RBench crate)"
Write-Host "[setup] interface fns   : $nfns    tests: $ntest"
Write-Host "[setup] wrote           : $(Join-Path $here 'codeweaver.toml')"
Write-Host ""
Write-Host "Next:"
Write-Host "  cd $(Split-Path -Parent (Split-Path -Parent $here))    # CodeWeaver repo root"
Write-Host "  python -m codeweaver milestones --config examples/crust-bench/codeweaver.toml   # (auto-generated at runtime)"
Write-Host "  python -m codeweaver run        --config examples/crust-bench/codeweaver.toml --app-id crust-$Project-001"
