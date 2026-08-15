# CodeWeaver comparison with RepoTransBench

## Abstract

RepoTransBench's currently advertised 1,897-repository asset returned HTTP 404, and its historical Python source archive was unavailable. We reconstructed three licensed historical v1.0 Python-to-Java subjects from pinned upstream repositories and evaluated nine CodeWeaver cells against 37 released fixed tests. Seven cells reached CodeWeaver's own terminal-success state; all nine independently built and passed every fixed test. Results are a measured, stratified subset—not a full-current-benchmark claim.

## Release audit

Seven small historical candidates were calibrated. Three had meaningful passing goldens and were selected. Three released goldens failed their own tests; one passing oracle never called the translated class. The complete audit is in data/oracle_audit.csv.

## Comparison tracks

The historical v1 README's 100-project table is the nearest benchmark family reference. The current paper's 1,897-project Python-to-Java Table V values are also preserved, but neither is pooled with the three-project CodeWeaver subset.

## Outcome interpretation

The two nonterminal-success cells exhausted the parity loop after all generated milestones passed. Their extracted Java outputs nevertheless pass the independently restored pristine oracle. Pipeline terminal status and external functional success are therefore reported separately.

## Leakage audit

0/9 generated implementations are byte-identical to the withheld released Java file set. The released Java files were hashed and removed before model access; per-cell file-level comparisons are in data/leakage_audit.csv.

## Redistribution

The reconstructed Python sources and generated Java files are covered by their upstream MIT licenses. RepoTransBench has no visible repository-level license, so released scaffold and test bytes are omitted from the result package; a path/hash manifest preserves their exact evaluated identity.

## Measured three-project subset

| Run | Pipeline terminal | SR | CR | APR | AMPR |
| --- | --- | --- | --- | --- | --- |
| CodeWeaver rep 1 | 3/3 | 3/3 (100.00%) | 3/3 (100.00%) | 100.00% | 100.00% |
| CodeWeaver rep 2 | 2/3 | 3/3 (100.00%) | 3/3 (100.00%) | 100.00% | 100.00% |
| CodeWeaver rep 3 | 2/3 | 3/3 (100.00%) | 3/3 (100.00%) | 100.00% | 100.00% |

## Historical v1 full-benchmark references

| Model | Success@1 | Build@1 | APR |
| --- | --- | --- | --- |
| Llama-3.1-8B-Inst | 0.00% | 0.00% | 0.00% |
| Llama-3.1-70B-Inst | 1.33% | 2.67% | 1.30% |
| Llama-3.1-405B-Inst | 2.67% | 5.67% | 4.70% |
| DeepSeek-V2.5 | 3.00% | 12.00% | 6.20% |
| GPT-3.5-Turbo | 0.67% | 2.33% | 1.10% |
| GPT-4 | 2.33% | 4.33% | 2.00% |
| GPT-4o | 4.00% | 9.00% | 6.40% |
| Claude-3.5-Sonnet | 7.33% | 28.33% | 16.50% |
| CodeLlama-34B-Inst | 0.00% | 0.37% | 0.00% |
| Codestral-22B | 2.08% | 5.90% | 2.60% |
| DeepSeek-Coder-V2-Inst | 4.86% | 16.84% | 8.40% |

## Current paper Python-to-Java references

| Model | SR | CR | APR | AMPR |
| --- | --- | --- | --- | --- |
| Qwen3 | 0.60% | 1.20% | 1.20% | 1.20% |
| Qwen3-think | 1.20% | 1.20% | 1.70% | 1.20% |
| DeepSeek | 1.80% | 2.90% | 2.30% | 1.80% |
| DeepSeek-R | 0.00% | 0.00% | 0.00% | 0.00% |
| Claude | 5.80% | 8.80% | 8.20% | 8.20% |
| Gemini | 0.00% | 0.00% | 0.00% | 0.00% |
| GPT-4.1 | 7.00% | 7.00% | 9.00% | 7.00% |
| o3-mini | 1.80% | 1.80% | 1.80% | 1.80% |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
- `raw-run-archives/`: filtered run states and agent artifacts; benchmark inputs and full project trees are withheld.
