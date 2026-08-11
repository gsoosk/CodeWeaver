# CodeWeaver ReCodeAgent experiment results

This repository contains the measured 118-project reproduction of
the experiments in arXiv:2604.07341 for the Full variant, including raw normalized data, independent
test/coverage evidence, paper-equivalent tables and figures, PDFs, provenance,
and filtered raw run archives.

- `results/`: final tables, figures, the exact paper comparison PDF, and
  reproducibility report.
- `results/analysis/paper_tables_side_by_side.pdf`: exact paper Tables 1 and 2
  with the measured CodeWeaver Full result beside every corresponding metric.
- `results/system-comparison/`: GPT-5.6 Sol cross-system JSON/CSVs/LaTeX/PDF
  and its provenance, when a system-comparison root was supplied.
- `results/analysis/paper_table{1,2}_side_by_side.csv`: machine-readable
  paper and CodeWeaver values with distinct provenance/status columns.
- `data/`: normalized raw rows, project-level RQ2/generated-test evidence,
  heuristic test-comparison outputs, and complete baseline replays under
  `data/baselines/<label>/` when supplied.
- `raw-run-archives/`: split compressed run outputs; concatenate numbered
  parts before extracting when an archive was split.
- `metadata/campaign/<label>/`: supplied campaign summaries/logs only; run
  workspaces are deliberately rejected to avoid duplicate raw packaging.
- `infrastructure-failure-archives/`: excluded retries, retained separately
  so authentication, transport, and interrupted-state decisions are auditable.
- `reproduction/source/`: exact CodeWeaver/harness source snapshot.
- `metadata/package_manifest.json`: input paths, copied-file counts, archive
  selection, and system-comparison completeness evidence.
- `metadata/checksums.sha256`: SHA-256 for every packaged file, including all
  supplied baseline/comparison/test/campaign evidence.

Official benchmark artifacts are not redistributed. Their pinned Zenodo
record, filenames, and MD5 checksums are recorded in the harness source and
manifest so acquisition remains reproducible.
