# RustPrint: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for RustPrint and records the maximum scientifically defensible CodeWeaver comparison. Status: public_artifact_new_run_required. CodeWikiBench's eight repositories are disjoint from retained CRUST-Bench tasks.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| rustprint | Benchmark statistics | 8 repositories / 11K-84K LoC | repository size and documentation | reference_only |
| rustprint | Table 1 | 8 CodeWikiBench repositories x 5 systems | compilation | exact_reference_public_artifact |
| rustprint | Table 2 | 8 repositories x 2 cross-generated test suites | true-positive rate | exact_reference_public_artifact |
| rustprint | Figures 2 and 4 | 8 repositories x systems/backbones | feature preservation and SafeRate | exact_reference_public_artifact |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2605.14634 | https://arxiv.org/abs/2605.14634 | eight repositories, 11K-84K LoC | citation only | public_artifact_new_run_required | CodeWikiBench's eight repositories are disjoint from retained CRUST-Bench tasks |  |

## rustprint_reference

| surface | system | metric | value | denominator |
| --- | --- | --- | --- | --- |
| Table 1 | RustPrint Kimi | compiled repositories | 8 | 8 |
| Table 1 | RustPrint GPT-5.4 | compiled repositories | 8 | 8 |
| Table 1 | Self-Repair | compiled repositories | 0 | 8 |
| Table 1 | EvoC2Rust | compiled repositories | 0 | 8 |
| Table 1 | C2Rust | compiled repositories | 8 | 8 |
| Table 1 | Claude Code | compiled repositories | 8 | 8 |
| Table 2 | RustPrint GPT-5.4 | aggregate cross-test TPR percent | 98.7 | 16 cells |
| Table 2 | RustPrint Kimi | aggregate cross-test TPR percent | 95.17 | 16 cells |
| Table 2 | Claude Code | aggregate cross-test TPR percent | 79.85 | 16 cells |
| Figure 2 | RustPrint Kimi | feature conservation percent | 93.26 | 8 repositories |
| Figure 2 | RustPrint GPT-5.4 | feature conservation percent | 97.76 | 8 repositories |
| Figure 2 | Claude Code Kimi | feature conservation percent | 52.52 | 8 repositories |
| Figure 2 | Claude Code GPT-5.4 | feature conservation percent | 48.87 | 8 repositories |
| Figure 4 | RustPrint Kimi | SafeRate A/F percent | 96.23/96.19 | 8 repositories |
| Figure 4 | RustPrint GPT-5.4 | SafeRate A/F percent | 99.41/98.47 | 8 repositories |
