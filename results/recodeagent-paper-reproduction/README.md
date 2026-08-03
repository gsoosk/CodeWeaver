# CodeWeaver ReCodeAgent results — PARTIAL snapshot

This repository is a **PARTIAL** CodeWeaver reproduction snapshot for the
ReCodeAgent paper (`arXiv:2604.07341`), frozen at **542 / 708** independently
collected terminal cells (**166 pending at freeze time**). It is **not** the
final reproduction.

Included now:
- normalized raw data for exactly the frozen 542 collected cells
- paper-aligned comparison corpus from `paper-current-118` (complete)
- all seven analysis CSV/PDF table/figure pairs for the current partial state
- the reproducibility report PDF/Markdown, which explicitly says INCOMPLETE
- filtered raw-run archives limited to the frozen keys only
- infrastructure-failure archives, provenance, checksums, and source snapshot

Frozen collection roots:
- `base-complete` — 236 rows
- `full-current-18` — 118 rows
- `noanalyzer-current-41` — 89 rows
- `noplanning-current-44` — 99 rows

Paper corpus status:
- 18 paper comparison rows
- 118 generated-test rows
- 1,472 static source methods / 1,484 runtime cases
- zero merge/evaluator failures

See `PARTIAL_SNAPSHOT.md` and `metadata/partial_snapshot.json` for exact freeze
provenance.
