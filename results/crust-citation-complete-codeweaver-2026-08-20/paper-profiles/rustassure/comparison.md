# RustAssure: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for RustAssure and records the maximum scientifically defensible CodeWeaver comparison. Status: public_artifact_metric_mismatch. Function-level KLEE equivalence is not CodeWeaver project pass-all.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| rustassure | Main differential-symbolic evaluation | 5 real applications/libraries | 89.8% function compilation and 69.9% symbolic-return equivalence | aggregate_reference_public_read_only |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2510.07604 | https://arxiv.org/abs/2510.07604 | five applications/libraries; differential symbolic validation | citation only | public_artifact_metric_mismatch | function-level KLEE equivalence is not CodeWeaver project pass-all |  |

## blocked_aggregate_references

| paper | scope | metric | value | status |
| --- | --- | --- | --- | --- |
| RustAssure | 5 applications/libraries | compilable functions percent | 89.8 | abstract aggregate; project-level comparison incompatible |
| RustAssure | 5 applications/libraries | symbolically equivalent returns percent | 69.9 | abstract aggregate; project-level comparison incompatible |
