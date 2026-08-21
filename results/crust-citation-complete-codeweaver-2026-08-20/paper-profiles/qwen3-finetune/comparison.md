# Fine-Tuning Qwen3-27B: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for Fine-Tuning Qwen3-27B and records the maximum scientifically defensible CodeWeaver comparison. Status: not_comparable. Function-level SACTOR evaluation is not a repository project oracle.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

results/sactor-codeweaver-comparison-2026-08-14

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| qwen3-finetune | C2Rust main result | 200 CodeNet programs / 5 seeds | six-attempt success mean, standard deviation, bootstrap CI | public_artifact_reference_not_crust |
| qwen3-finetune | Baseline comparison | 200 CodeNet programs | Qwen base, MiniMax, GLM, Claude success | public_artifact_reference_not_crust |
| qwen3-finetune | SWE-bench Verified | SWE-bench Verified | Pass@1 | public_artifact_reference_not_comparable |
| qwen3-finetune | Training curriculum | three stages | examples, epochs, learning rates, sequence length and hardware | public_artifact_reference |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2608.13681 | https://arxiv.org/abs/2608.13681 | SACTOR-framework function translation | citation only | not_comparable | function-level SACTOR evaluation is not a repository project oracle | results/sactor-codeweaver-comparison-2026-08-14 |
