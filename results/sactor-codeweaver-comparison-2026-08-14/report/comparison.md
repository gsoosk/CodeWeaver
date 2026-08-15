# CodeWeaver comparison with SACTOR

## Abstract

SACTOR's Appendix Table 14 identifies an exact 50-project CRUST-Bench subset, enabling an exact-subject CodeWeaver re-analysis. All 150 CodeWeaver cells compiled; 92/150 passed every fixed project test. CodeWeaver's end-to-end project metric and static safety scan are not pooled with SACTOR's function-level, two-stage, conditionally evaluated idiomatic metric.

## Denominator discipline

SACTOR evaluates 966 functions in its unidiomatic stage, then only the 32 fully successful samples in its idiomatic stage. CodeWeaver evaluates all 50 projects in every repetition against 319 fixed project tests. These denominators remain explicit.

## Safety metric

CodeWeaver SafeRate is the line-weighted fraction of nonblank production Rust outside unsafe functions or blocks. SACTOR reports unsafe-free programs and average unsafe fraction with its own analyzer. The intent overlaps, but the implementations are not assumed identical.

## Exact CodeWeaver measurements

| Run | Build | Pass all | Fixed tests | Unsafe-free | SafeRate |
| --- | --- | --- | --- | --- | --- |
| CodeWeaver rep 1 | 50/50 | 31/50 (62.00%) | 297/319 (93.10%) | 41/50 | 99.83% |
| CodeWeaver rep 2 | 50/50 | 31/50 (62.00%) | 304/319 (95.30%) | 43/50 | 99.77% |
| CodeWeaver rep 3 | 50/50 | 30/50 (60.00%) | 285/319 (89.34%) | 40/50 | 99.68% |

## SACTOR Table 2 comparison boundary

| System | Unit | Function success | Complete samples | Unsafe-free | Note |
| --- | --- | --- | --- | --- | --- |
| SACTOR unidiomatic | function | 81.57% | 32/50 (64.00%) | 0% | heavy unsafe |
| SACTOR idiomatic | function, conditional | 42.93% | 8/32 (25.00%) | 100% | 32 survivors only |
| CodeWeaver rep 1 | whole project | N/A | 31/50 | 41/50 | 99.83% |
| CodeWeaver rep 2 | whole project | N/A | 31/50 | 43/50 | 99.77% |
| CodeWeaver rep 3 | whole project | N/A | 30/50 | 40/50 | 99.68% |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
