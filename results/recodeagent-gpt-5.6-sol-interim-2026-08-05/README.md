# CodeWeaver GPT-5.6 Sol comparison — interim snapshot

This is a reviewable, non-final snapshot of the 118-project ReCodeAgent-paper
comparison captured on 2026-08-05. The frozen experiment contains 354
CodeWeaver cells (118 projects x 3 repetitions) using `gpt-5.6-sol` with
maximum reasoning effort.

At capture time, 80 cells were terminal (59 completed and 21 genuine
max-repair failures), 53 were actively running, and 221 were queued. The four
earlier telemetry-schema crashes are separately audited as infrastructure
failures and are not counted as measured outcomes.

**Important:** `completed` here means that the CodeWeaver orchestration
reached its successful terminal state. It is not an independent correctness
claim. Build, fixed-oracle tests, coverage, repeated-run statistics, exact
paper tables, figures, and the final publication PDF are generated only after
the full matrix reaches terminal state.

## Review map

- [`metadata/interim_snapshot.json`](metadata/interim_snapshot.json) — frozen
  status, scope, baseline availability, and explicit outstanding work.
- [`data/matrix_cells.csv`](data/matrix_cells.csv) and
  [`data/matrix_cells.jsonl`](data/matrix_cells.jsonl) — all 354 cells,
  including terminal, active, and queued outcomes.
- [`protocol/experiment-gpt-5.6-sol.toml`](protocol/experiment-gpt-5.6-sol.toml)
  — measured protocol.
- [`data/manifest.json`](data/manifest.json) — exact 118-project benchmark.
- [`metadata/shard-plan.json`](metadata/shard-plan.json) — deterministic
  concurrency and reconciliation provenance.
- [`data/baselines/prior/`](data/baselines/prior/) — completed released-artifact
  replay for Oxidizer, AlphaTrans, and SKEL, plus 100 explicit unavailable
  SWE-agent CRUST rows. Stub CRUST scaffolds were never substituted as
  SWE-agent outputs.
- [`metadata/infrastructure_failures.json`](metadata/infrastructure_failures.json)
  — audit of the four archived telemetry failures.
- [`interim_progress.pdf`](interim_progress.pdf) — concise review PDF.
- [`metadata/checksums.sha256`](metadata/checksums.sha256) — SHA-256 for every
  file in this snapshot.

The ReCodeAgent released-artifact replay and CodeWeaver matrix were still
running at capture time. Their partial in-memory results are intentionally not
presented as final measurements.
