# SACTOR: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for SACTOR and records the maximum scientifically defensible CodeWeaver comparison. Status: exact_existing_result. Three CodeWeaver repetitions on the exact 50-project subset.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

150/150 build; 92/150 pass all (results/sactor-codeweaver-comparison-2026-08-14).

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| sactor | Figures 2-3 | 100 TransCoder-IR + 100 CodeNet programs | success through six attempts and Clippy alerts | exact_existing_result |
| sactor | Tables 1-3 | two 100-program sets, CRUST-Bench-50, libogg-77 | unsafe code, translation success, lints and attempts | exact_existing_result |
| sactor | Tables 5-9 and Figure 8 | paper datasets, models and ablations | dataset, model, failure, cost, feedback and CRUST-Bench baseline comparisons | exact_existing_result |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2503.12511v3 | https://arxiv.org/abs/2503.12511 | TransCoder-IR, CodeNet, 50 CRUST-Bench projects, libogg | exact named subset:50 | exact_existing_result | three CodeWeaver repetitions on the exact 50-project subset | results/sactor-codeweaver-comparison-2026-08-14 |
