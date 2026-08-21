# CodeWeaver comparison with the complete CRUST-Bench citation corpus

Read `report/comparison.pdf` first. This directory separates measured
CodeWeaver outcomes, published reference values, and unavailable surfaces.

Paper: [30-record citation census as of 2026-08-20](https://arxiv.org/abs/2504.15254)

The `paper-profiles/` directory contains one PDF/Markdown evidence profile and
complete empirical-surface inventory for each included work. When the ACToR
campaign is supplied, `data/actor-li/` contains all normalized measurements,
generated candidates, post-run public oracle snapshots, and qualification
logs; `raw-run-archives/` contains filtered run states and agent trajectories.
Benchmark inputs are excluded from model-readable workspaces during execution.


Verify this artifact with:

```sh
sha256sum -c metadata/checksums.sha256
```
