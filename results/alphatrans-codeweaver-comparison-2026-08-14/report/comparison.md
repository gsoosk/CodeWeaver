# CodeWeaver comparison with AlphaTrans

## Abstract

Four of AlphaTrans's ten exact Java projects were already measured in the published CodeWeaver matrix. All 12 translations compiled; none passed every available fixed runtime case. Across repetitions, 1130/3543 fixed cases passed. AlphaTrans's fragment-level TPR is preserved separately because it is not the same unit or denominator as CodeWeaver's project-test execution.

## Scope

The exact common subjects are commons-cli, commons-csv, commons-fileupload, and commons-validator. Six paper subjects were not run, so this artifact makes no ten-project aggregate claim.

## Unavailable surface

AlphaTrans's manual type-map completion, manual repair effort, GraalVM fragment validation, and human bug taxonomy cannot be recovered from CodeWeaver's end-to-end project outputs and are reported as unavailable rather than zero.

## Exact-subject comparison

| Project | AlphaTrans syntax | AlphaTrans TPR | CW builds | CW fixed tests |
| --- | --- | --- | --- | --- |
| commons-cli | 100.00% | 10.08% | 3/3 | 1103/1143 (96.50%) |
| commons-csv | 98.72% | 0.00% | 3/3 | 0/894 (0.00%) |
| commons-fileupload | 100.00% | 63.44% | 3/3 | 27/117 (23.08%) |
| commons-validator | 99.23% | 11.70% | 3/3 | 0/1389 (0.00%) |

## CodeWeaver repetitions

| Rep | Build | Pass all | Fixed tests | Test rate |
| --- | --- | --- | --- | --- |
| 1 | 4/4 | 0/4 | 379/1181 | 32.09% |
| 2 | 4/4 | 0/4 | 373/1181 | 31.58% |
| 3 | 4/4 | 0/4 | 378/1181 | 32.01% |

## CodeWeaver execution and model-use telemetry

| Scope | Cells | Elapsed h | Assistant turns | Tool calls | Premium requests | AIU | Output tokens | Input tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repetition 1 | 4 | 16.93 | 5325 | 9273 | 33 | 29125.47 | 3376395 | N/A (unavailable) |
| repetition 2 | 4 | 16.37 | 5253 | 9069 | 0 | 28834.56 | 3194237 | N/A (unavailable) |
| repetition 3 | 4 | 14.51 | 5203 | 8791 | 0 | 26315.46 | 3188225 | N/A (unavailable) |
| all measured cells | 12 | 47.81 | 15781 | 27133 | 33 | 84275.49 | 9758857 | N/A (unavailable) |

## CodeWeaver standardized coverage measurements

| Rep | Metric | Cells | Mean | Min | Max |
| --- | --- | --- | --- | --- | --- |
| 1 | coverage_before | 4 | 54.06% | 38.33% | 90.71% |
| 1 | standardized_coverage_before | 4 | 54.06% | 38.33% | 90.71% |
| 1 | standardized_coverage_after | 4 | 68.48% | 51.69% | 90.71% |
| 2 | coverage_before | 4 | 50.76% | 35.26% | 88.76% |
| 2 | standardized_coverage_before | 4 | 50.76% | 35.26% | 88.76% |
| 2 | standardized_coverage_after | 4 | 60.95% | 35.26% | 89.41% |
| 3 | coverage_before | 4 | 52.61% | 26.58% | 96.11% |
| 3 | standardized_coverage_before | 4 | 52.61% | 26.58% | 96.11% |
| 3 | standardized_coverage_after | 4 | 69.50% | 45.02% | 96.11% |

## Complete source-paper surface audit

| Surface | Denominator | Metrics | Artifact status |
| --- | --- | --- | --- |
| Table 1 | 10 projects / 1,797 types | classes, methods, tests, method coverage, ATR, SV, fragments | structured_reference |
| Table 2 | 10 projects / 4,654 application-method fragments | syntax, source coverage, GraalVM outcomes, translated-test outcomes, TPR | structured_reference_summary_and_four_project_comparison |
| RQ2 human study | 4 projects / 2 developers | hours, additions, deletions, bug examples | structured_reference |
| Figure 6 | eligible decomposed tests in 9 projects | selected/fail/success ratios and fragment pass-rate distribution | structured_reference_summary |
| Table 3 | 10 projects | coverage, decomposed tests, methods per test, TPR+, ATP+ | structured_reference_summary |
| Table 4 | 10 projects | GraalVM and translated-test outcomes | structured_reference_summary |
| Table 5 | 10 projects | syntax, GraalVM, translated tests, functional equivalence, cost | structured_reference_summary |
| Table 6 | 782 files | context overflow, syntax errors, Graal success, TPR | structured_reference_summary |
| Figure 7 | application-method fragments | DeepSeek-Coder and GPT-4o overlap | structured_reference_summary |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `data/paper-reference/`: structured references for omitted source-paper tables.
- `data/paper_surface_inventory.csv`: every source-paper evaluation surface and status.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
