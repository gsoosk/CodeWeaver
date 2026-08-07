# CodeWeaver GPT-5.6 Sol comparison - interim snapshot

This is a reviewable, non-final snapshot of the 118-project ReCodeAgent-paper
comparison captured on 2026-08-07. The frozen experiment contains 354
CodeWeaver cells (118 projects x 3 repetitions) using `gpt-5.6-sol` with
maximum reasoning effort.

At capture time, **329/354 cells were terminal (92.9%)**:
221 completed pipelines, 108 genuine max-repair failures, and
0 timeouts. 1 cells were actively running and 24
were queued. Four earlier telemetry-schema crashes are separately audited as
infrastructure failures and are not counted as measured outcomes.

**Important:** `completed` means that CodeWeaver orchestration reached its
successful terminal state. It is not an independent correctness claim. Build,
fixed-oracle tests, coverage, repeated-run statistics, exact paper tables,
figures, and the final publication PDF are generated only after the complete
matrix reaches terminal state.

## Review map

- [`metadata/interim_snapshot.json`](metadata/interim_snapshot.json) - frozen
  status, scope, baseline availability, and explicit outstanding work.
- [`data/matrix_cells.csv`](data/matrix_cells.csv) and
  [`data/matrix_cells.jsonl`](data/matrix_cells.jsonl) - all 354 cell states.
- [`protocol/experiment-gpt-5.6-sol.toml`](protocol/experiment-gpt-5.6-sol.toml)
  - frozen measured protocol.
- [`data/manifest.json`](data/manifest.json) - exact 118-project benchmark.
- [`data/baselines/recodeagent/`](data/baselines/recodeagent/) - 117 measured
  released ReCodeAgent outputs and one explicit accounted missing artifact.
- [`data/baselines/prior/`](data/baselines/prior/) - 18 measured prior-system
  outputs and 100 explicit unavailable SWE-agent CRUST artifacts.
- [`metadata/recovery/`](metadata/recovery/) - completed recovery scheduler
  summaries at capture time; pending schedulers are named in the snapshot JSON.
- [`metadata/infrastructure_failures.json`](metadata/infrastructure_failures.json)
  and restart/resource records - recovery and exclusion audit trail.
- [`interim_progress.pdf`](interim_progress.pdf) - concise review PDF.
- [`metadata/checksums.sha256`](metadata/checksums.sha256) - SHA-256 for every
  other file in this snapshot.

The matrix is still running. Partial orchestration states and baseline replay
evidence are intentionally not presented as final CodeWeaver effectiveness
measurements.
