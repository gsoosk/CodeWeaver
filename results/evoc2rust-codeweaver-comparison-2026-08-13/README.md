# CodeWeaver - EvoC2Rust Vivo-Bench comparison

This artifact contains the leakage-safe, three-repetition CodeWeaver
comparison with *EvoC2Rust* (DOI `10.1145/3786583.3786856`) on the public
Vivo-Bench revision.

## Headline results

- Terminal measured runs: 45/45
- Mean ICompRate: 100.00%
- Mean FCompRate: 100.00%
- Mean TestRate: 100.00%
- Mean SafeRate: 30.92%
- Raw archive files: 3515
- Campaign metadata files: 13
- Infrastructure-failure evidence: archived separately

Read `report/comparison.pdf` first. Exact tables and figures are under
`report/`, normalized measurements under `data/evaluation/`, immutable
prepared contracts under `reproduction/prepared-workspaces/`, and provenance
under `metadata/`. Pre-model failures excluded from the measured matrix are
preserved under `infrastructure-failure-archives/`.

The paper reports 113 Vivo-Bench test cases; the pinned public revision enables
125 test functions. The report preserves this denominator drift. C2R-Bench,
AccRate references, the EvoC2Rust implementation, ablations, and runtime traces
are unreleased, so those experiments are reference-only rather than fabricated.

Verify the artifact from this directory with:

```sh
sha256sum -c metadata/checksums.sha256
```

If the raw archive is split, concatenate numbered parts in lexical order:

```sh
cat raw-run-archives/full.tar.gz.part-* > full.tar.gz
tar -xzf full.tar.gz
```

On PowerShell:

```powershell
$parts = Get-ChildItem raw-run-archives\full.tar.gz.part-* | Sort-Object Name
$out = [IO.File]::Create('full.tar.gz')
try { foreach ($part in $parts) { $bytes = [IO.File]::ReadAllBytes($part); $out.Write($bytes) } }
finally { $out.Dispose() }
tar -xzf full.tar.gz
```
