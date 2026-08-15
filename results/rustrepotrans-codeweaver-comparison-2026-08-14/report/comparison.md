# CodeWeaver comparison with RustRepoTrans

## Abstract

We selected one leakage-safe RustRepoTrans task per source language (C, Java, Python), ran three CodeWeaver repetitions, and evaluated each by replacing only the target function in a pristine licensed Rust project. Golden target bodies were hashed and excluded from every model-visible workspace. This 3/375-task slice measures feasibility and is not presented as a full-benchmark estimate.

## Oracle calibration

The pristine goldens pass 284, 284, and 64 fixed tests. Replacing the selected functions with compiling panic stubs causes 50, 73, and at least 13 failures respectively, demonstrating non-vacuous coverage of each selected function.

## Metric boundary

RustRepoTrans reports Pass@1 and one-round DSR@1 over 375 tasks. CodeWeaver is a multi-stage system with up to five repairs and three parity rounds. Its fixed-oracle pass-all rate is shown beside, but not relabeled as, Pass@1 or DSR@1.

## Leakage audit

4/9 generated functions are byte-identical to the withheld golden body. This is disclosed as an output property, not evidence of exposure: every golden was hashed and removed before model access, and the actual workspace exclusion check is recorded in prepared metadata.

## Redistribution

The RustRepoTrans repository has no visible repository-level license, so benchmark task text and full external projects are not redistributed. This artifact contains hashes, normalized outcomes, evaluation logs, and generated target functions under the target projects' MIT/Apache-2.0 licenses.

## Measured stratified slice

| Run | Pipeline terminal | Pass all | Build | Fixed tests | Test rate |
| --- | --- | --- | --- | --- | --- |
| CodeWeaver rep 1 | 3/3 | 3/3 (100.00%) | 3/3 (100.00%) | 632/632 | 100.00% |
| CodeWeaver rep 2 | 3/3 | 3/3 (100.00%) | 3/3 (100.00%) | 632/632 | 100.00% |
| CodeWeaver rep 3 | 3/3 | 3/3 (100.00%) | 3/3 (100.00%) | 632/632 | 100.00% |

## Per-language selected tasks

| Source | Task | Build cells | Pass-all cells | Tests | Exact golden | Stub failures |
| --- | --- | --- | --- | --- | --- | --- |
| C | incubator-milagro-crypto:RAND::clean | 3/3 | 3/3 | 852/852 | 0/3 | 50 |
| Java | incubator-milagro-crypto:big::set | 3/3 | 3/3 | 852/852 | 3/3 | 73 |
| Python | charset-normalizer:CharsetMatch::encoding | 3/3 | 3/3 | 192/192 | 1/3 | 13 |

## Published full-benchmark references

| Model | Pass@1 | DSR@1 |
| --- | --- | --- |
| DeepSeek-R1 | 51.50% | 62.10% |
| DeepSeek-V3 | 50.10% | 58.70% |
| Claude-3.5 | 43.50% | 56.50% |
| Qwen-2.5-coder-32B | 34.40% | 38.90% |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
- `raw-run-archives/`: filtered run states and agent artifacts; benchmark inputs and full project trees are withheld.
