# CodeWeaver ReCodeAgent experiment results

This repository contains the measured 118-project x 6-variant reproduction of
the experiments in arXiv:2604.07341, including raw normalized data, independent
test/coverage evidence, paper-equivalent tables and figures, PDFs, provenance,
and filtered raw run archives.

- `results/`: final tables, figures, and reproducibility report.
- `data/`: normalized raw rows and project-level RQ2/generated-test evidence.
- `raw-run-archives/`: split compressed run outputs; concatenate numbered
  parts before extracting when an archive was split.
- `infrastructure-failure-archives/`: excluded retries, retained separately
  so authentication, transport, and interrupted-state decisions are auditable.
- `reproduction/source/`: exact CodeWeaver/harness source snapshot.
- `metadata/checksums.sha256`: SHA-256 for every packaged file.

Official benchmark artifacts are not redistributed. Their pinned Zenodo
record, filenames, and MD5 checksums are recorded in the harness source and
manifest so acquisition remains reproducible.
