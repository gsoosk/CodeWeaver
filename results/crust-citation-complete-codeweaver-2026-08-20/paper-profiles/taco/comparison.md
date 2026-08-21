# TACO: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for TACO and records the maximum scientifically defensible CodeWeaver comparison. Status: reference_only. 47.00% to 48.05% terminal-task accuracy is not project pass-all.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

results/crust-bench-codeweaver-comparison-2026-08-14

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| taco | Table 1 | 6 terminal-agent benchmarks | baseline/TACO accuracy and token consumption | exact_reference_not_metric_aligned |
| taco | Table 2 | TerminalBench 1.0/2.0 across about 9 models | terminal-agent performance | reference_only_not_metric_aligned |
| taco | Appendix ablations | terminal-agent benchmark runs | freeze rules, disable global evolution, best-of-K, compression overhead | reference_only_not_metric_aligned |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2604.19572 | https://arxiv.org/abs/2604.19572 | terminal-agent context compression over six benchmarks | CRUST-Bench terminal-task metric | reference_only | 47.00% to 48.05% terminal-task accuracy is not project pass-all | results/crust-bench-codeweaver-comparison-2026-08-14 |

## CRUST-Bench terminal-agent reference

| backbone | baseline_accuracy_percent | taco_accuracy_percent | accuracy_delta_pp | baseline_tokens_thousands | taco_tokens_thousands | token_reduction_percent | denominator | metric |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MiniMax-M2.5 | 47.0 | 48.05 | 1.05 | 163.53 | 134.97 | 17.5 | not stated in Table 1 | terminal-agent task accuracy |
