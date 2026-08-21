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
| CodeWeaver rep 1 | 50/50 | 31/50 (62.00%) | 268/319 (84.01%) | 41/50 | 99.83% |
| CodeWeaver rep 2 | 50/50 | 31/50 (62.00%) | 278/319 (87.15%) | 43/50 | 99.77% |
| CodeWeaver rep 3 | 50/50 | 30/50 (60.00%) | 261/319 (81.82%) | 40/50 | 99.68% |

## SACTOR v3 CRUST-Bench function-level comparison boundary

| System | Unit | Function success | Complete samples | Unsafe-free | Note |
| --- | --- | --- | --- | --- | --- |
| SACTOR unidiomatic | function | 81.57% | 32/50 (64.00%) | 0% | heavy unsafe |
| SACTOR idiomatic | function, conditional | 42.93% | 8/32 (25.00%) | 100% | 32 survivors only |
| CodeWeaver rep 1 | whole project | N/A | 31/50 | 41/50 | 99.83% |
| CodeWeaver rep 2 | whole project | N/A | 31/50 | 43/50 | 99.77% |
| CodeWeaver rep 3 | whole project | N/A | 30/50 | 40/50 | 99.68% |

## CodeWeaver execution and model-use telemetry

| Scope | Cells | Elapsed h | Assistant turns | Tool calls | Premium requests | AIU | Output tokens | Input tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repetition 1 | 50 | 68.29 | 20716 | 32556 | 660 | 94632.82 | 11808699 | N/A (unavailable) |
| repetition 2 | 50 | 64.56 | 19378 | 30588 | 608 | 87893.54 | 11209964 | N/A (unavailable) |
| repetition 3 | 50 | 63.99 | 19108 | 30395 | 625 | 85477.36 | 10752289 | N/A (unavailable) |
| all measured cells | 150 | 196.85 | 59202 | 93539 | 1893 | 268003.71 | 33770952 | N/A (unavailable) |

## CodeWeaver coverage measurements

| Rep | Metric | Cells | Mean | Min | Max |
| --- | --- | --- | --- | --- | --- |
| 1 | coverage_before | 48 | 64.21% | 4.19% | 100.00% |
| 1 | coverage_after | 48 | 64.25% | 4.19% | 100.00% |
| 2 | coverage_before | 49 | 67.94% | 3.62% | 100.00% |
| 2 | coverage_after | 49 | 68.12% | 3.62% | 100.00% |
| 3 | coverage_before | 49 | 64.29% | 4.58% | 100.00% |
| 3 | coverage_after | 49 | 64.33% | 4.58% | 100.00% |

## CodeWeaver final-output Clippy comparison

| Rep | Complete | Incomplete | Warning-free | Warnings | Errors | Alerts/project | Alerts/function |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 48 | 2 | 0 | 693 | 0 | 14.44 | 0.176 |
| 2 | 48 | 2 | 1 | 627 | 0 | 13.06 | 0.161 |
| 3 | 48 | 2 | 0 | 601 | 0 | 12.52 | 0.161 |

## Complete source-paper surface audit

| Surface | Denominator | Metrics | Artifact status |
| --- | --- | --- | --- |
| Figure 2 | 100 + 100 programs | unidiomatic and idiomatic SR through six attempts for five models | structured_reference |
| Figure 3 | TransCoder-IR and CodeNet | warnings plus errors across six systems | paper_only |
| Table 1 | TransCoder-IR and CodeNet | success, unsafe-free, average unsafe | structured_reference |
| Table 2 | 50 samples / 966 functions; conditional 32 / 580 | per-sample, aggregate, full success, lint/function | structured_reference_and_codeweaver_comparison |
| Table 3 | 77 functions | success, lint/function, attempts for GPT-4o and GPT-5 | structured_reference |
| Table 5 | four datasets/codebases | size, preprocessing, tests, line/function coverage | structured_reference |
| Table 6 | six models | version, size, temperature | documented_reference |
| Table 7 / Figure 7 | TransCoder-IR and CodeNet failures | six and seven failure categories by model | structured_reference_categories |
| Table 8 | successful idiomatic translations | tokens and average queries per program/model/dataset | structured_reference |
| Figure 8 | 100 programs per dataset | with/without feedback for Llama 3.3 and GPT-4o | structured_reference_summary |
| Table 9 | 50 samples / 966 functions | function/sample success and Clippy | structured_reference |
| Table 10 | 77 functions | idiomatic successes and relative drop | structured_reference |
| Tables 11-12 | 77 functions | success, Clippy, hidden unsafe dereferences, unsafe fraction | structured_reference |
| Figure 9 | 100 programs per dataset | success at temperatures 0.0, 0.5, 1.0 | structured_reference_summary |
| Table 13 | supported representation patterns | unidiomatic/idiomatic harness coverage | paper_only |
| Table 14 | 50 named samples | unidiomatic/idiomatic function success and primary failure | subset_lock_and_paper_reference |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `data/paper-reference/`: structured references for omitted source-paper tables.
- `data/paper_surface_inventory.csv`: every source-paper evaluation surface and status.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
