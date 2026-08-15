# CodeWeaver comparison with RepoTransBench

Read `report/comparison.pdf` first. This directory separates measured
CodeWeaver outcomes, published reference values, and unavailable surfaces.

Paper: [arXiv:2412.17744](https://arxiv.org/abs/2412.17744)

Filtered raw run states and agent artifacts are under `raw-run-archives/`.
Generated Java files or Rust functions are exported separately under
`data/generated/`. Benchmark inputs and full external project trees are omitted;
their hashes are recorded in `metadata/withheld_scaffold_manifest.csv`.
Pre-model launcher failures are preserved under
`infrastructure-failure-archives/` and excluded from measured cells.

If the archive is split, concatenate `full.tar.gz.part-*` in lexical order
before extracting it:

```sh
cat raw-run-archives/full.tar.gz.part-* > full.tar.gz
tar -xzf full.tar.gz
```

```powershell
$parts = Get-ChildItem raw-run-archives\full.tar.gz.part-* | Sort-Object Name
$out = [IO.File]::Create('full.tar.gz')
try { foreach ($part in $parts) { $bytes = [IO.File]::ReadAllBytes($part); $out.Write($bytes) } }
finally { $out.Dispose() }
tar -xzf full.tar.gz
```


Verify this artifact with:

```sh
sha256sum -c metadata/checksums.sha256
```
