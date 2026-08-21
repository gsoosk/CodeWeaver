# EvoC2Rust: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for EvoC2Rust and records the maximum scientifically defensible CodeWeaver comparison. Status: partial_existing_result. Three repetitions cover public Vivo-Bench; C2R-Bench and industrial projects are unreleased.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

100% incremental compilation, fill compilation, and fixed-test rate; mean SafeRate 30.92% (results/evoc2rust-codeweaver-comparison-2026-08-13).

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| evoc2rust | Table 4 | Vivo-Bench and unreleased C2R-Bench | ICompRate, AccRate-P/R, SafeRate | public_subset_existing_result |
| evoc2rust | Table 5 | Vivo-Bench modules and unreleased projects | FCompRate and TestRate | public_subset_existing_result |
| evoc2rust | Table 6 | paper ablation configurations | skeleton, mapping, repair ablations | reference_only_unreleased_inputs |
| evoc2rust | RQ4 figures | six industrial projects | scale and elapsed time | blocked_unreleased |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2508.04295v4 | https://arxiv.org/abs/2508.04295 | Vivo-Bench, C2R-Bench, six industrial projects | citation only | partial_existing_result | three repetitions cover public Vivo-Bench; C2R-Bench and industrial projects are unreleased | results/evoc2rust-codeweaver-comparison-2026-08-13 |
