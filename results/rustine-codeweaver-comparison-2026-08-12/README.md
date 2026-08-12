# CodeWeaver - Rustine same-subject comparison

This package reports the leakage-aware 23-subject C-to-Rust comparison with
Rustine ([arXiv:2511.20617](https://arxiv.org/abs/2511.20617)). Rustine values
are the paper's published reference values; CodeWeaver values are independently
measured from the immutable disclosed contracts.

## Headline inventory

- Terminal CodeWeaver runs: 23/23
- CodeWeaver compilations: 21/23
- CodeWeaver fixed-contract passes: 10/21 testable
- Rustine paper compilation reference: 23/23
- Raw archive files: 2479
- Raw archive parts: 2

The primary human-readable output is `report/comparison.pdf`, with the headline
chart in `report/summary_figure.pdf`. Exact companion tables are under
`report/`, normalized measurements under `data/evaluation/`, and
provenance/checksums under `metadata/`.

Verify all packaged bytes from the package root with:

```sh
sha256sum -c metadata/checksums.sha256
```

## Raw archive reconstruction

If multiple numbered parts are present, concatenate them in lexical order to
recover `full.tar.gz`, then extract it. On POSIX:

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

No Rustine production translation is redistributed or exposed to CodeWeaver.
The [official artifact](https://github.com/Intelligent-CAT-Lab/Rustine) is identified by its
pinned commit in `reproduction/prepared_manifest.json`.
