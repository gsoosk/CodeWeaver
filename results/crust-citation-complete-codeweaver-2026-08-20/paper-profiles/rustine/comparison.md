# Rustine: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for Rustine and records the maximum scientifically defensible CodeWeaver comparison. Status: exact_existing_result. Leakage-safe CodeWeaver evaluation on all 23 released subjects.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

21/23 compile; 10/21 fixed-contract pass (results/rustine-codeweaver-comparison-2026-08-12).

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| rustine | Table 1 | 23 repositories | benchmark coverage | exact_existing_result |
| rustine | Table 2 | 23 repositories / 21 testable | compilation, function/line coverage, assertions | exact_existing_result |
| rustine | Table 3 | 23 repositories | pointer arithmetic, raw pointers, unsafe lines/casts/calls | exact_existing_result |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2511.20617 | https://arxiv.org/abs/2511.20617 | 23 C repositories | cites benchmark; own 23-project suite | exact_existing_result | leakage-safe CodeWeaver evaluation on all 23 released subjects | results/rustine-codeweaver-comparison-2026-08-12 |
