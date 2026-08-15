# CodeWeaver comparison with CRUST-Bench

## Abstract

On all 100 exact CRUST-Bench subjects, 300/300 CodeWeaver cells compiled and 165/300 passed every fixed project test. Mean project success was 55.00% (sample SD 1.00 pp). The paper's single-shot and three-round repair settings are preserved as references; CodeWeaver's multi-stage five-repair/three-parity protocol is not relabeled as those settings.

## Method

This exact-subject re-analysis imports the published CodeWeaver campaign's independently restored CRUST interfaces and fixed tests. All three terminal outcomes are retained; no best-of-three selection is used.

## Validity boundary

CRUST-Bench's Table 4 reports pass rates under single-shot, compiler repair, test repair, and an adapted SWE-agent. CodeWeaver uses a different architecture and larger repair budget. Comparison is descriptive, not a controlled model ablation.

## Exact CodeWeaver measurements

| Run | Build | Pass all | Fixed tests | Test rate |
| --- | --- | --- | --- | --- |
| CodeWeaver rep 1 | 100/100 | 56/100 (56.00%) | 500/623 | 80.26% |
| CodeWeaver rep 2 | 100/100 | 55/100 (55.00%) | 507/623 | 81.38% |
| CodeWeaver rep 3 | 100/100 | 54/100 (54.00%) | 464/623 | 74.48% |
| CodeWeaver mean | 100.00% | 55.00% +/- 1.00 pp | three independent repetitions | 95% t-CI +/- 2.48 pp |

## Published CRUST-Bench Table 4

| System | Base build | Base test | Compiler-repair build | Compiler-repair test | Test-repair build | Test-repair test |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAI o3 | 35.00% | 19.00% | 68.00% | 31.00% | 63.00% | 48.00% |
| Claude Opus 4 | 43.00% | 22.00% | 78.00% | 29.00% | 65.00% | 40.00% |
| OpenAI o1 | 32.00% | 15.00% | 69.00% | 28.00% | 54.00% | 37.00% |
| Claude 3.7 | 26.00% | 13.00% | 54.00% | 23.00% | 49.00% | 32.00% |
| Claude 3.5 | 26.00% | 11.00% | 49.00% | 21.00% | 38.00% | 24.00% |
| o1-mini | 19.00% | 9.00% | 47.00% | 16.00% | 27.00% | 21.00% |
| GPT-4o | 18.00% | 7.00% | 52.00% | 18.00% | 42.00% | 22.00% |
| Gemini 1.5 Pro | 11.00% | 3.00% | 35.00% | 11.00% | 30.00% | 14.00% |
| Virtuoso (Distilled Deepseek V3) | 2.00% | 2.00% | 21.00% | 6.00% | 10.00% | 6.00% |
| Deepseek-Coder-32B | 1.00% | 0.00% | 2.00% | 0.00% | 2.00% | 0.00% |
| QwQ-32B-Preview | 1.00% | 0.00% | 1.00% | 0.00% | 1.00% | 0.00% |
| Qwen-2.5-Coder-32B | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Adapted SWE-agent (Claude-3.7) | 41.00% | 32.00% | N/A | N/A | N/A | N/A |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
