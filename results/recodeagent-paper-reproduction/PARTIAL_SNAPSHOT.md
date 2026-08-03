# PARTIAL snapshot provenance

Status: **PARTIAL**

- Frozen collected rows: **542 / 708**
- Pending at freeze time: **166**
- Coverage fraction: **0.7655367231638418**
- Report verdict: **INCOMPLETE**

Frozen cumulative roots:
- `/opt/codeweaver-experiments/final-shards/base-complete` (236 rows)
- `/opt/codeweaver-experiments/final-shards/merged-progress/full-current-18` (118 rows)
- `/opt/codeweaver-experiments/final-shards/merged-progress/noanalyzer-current-41` (89 rows)
- `/opt/codeweaver-experiments/final-shards/merged-progress/noplanning-current-44` (99 rows)

Paper corpus root:
- `/opt/codeweaver-experiments/final-shards/paper-current-118`
- 18 paper comparison rows
- 118 generated-test rows
- 1,472 static methods / 1,484 runtime cases
- zero merge/evaluator failures

Raw archive scope:
- Includes only files reachable from the exact 542 frozen `(variant, project_id, repetition)` keys
- Excludes active/incomplete cells
- Preserves measured failures/timeouts as collected
- `novalidator` archive is intentionally empty at freeze time

Run-status mix across frozen rows:
- completed: 523
- failed: 17
- timeout: 2
