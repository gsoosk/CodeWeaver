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

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
