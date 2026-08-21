# ReCodeAgent: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for ReCodeAgent and records the maximum scientifically defensible CodeWeaver comparison. Status: exact_existing_result. Complete 118-project CodeWeaver campaign and paper-style report.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

full raw data, baselines, ablations, tables, figures, and PDF (results/recodeagent-gpt-5.6-sol-final-2026-08-11).

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| recodeagent | Full paper evaluation | 118 projects / 4 language pairs / 6 languages | build, project tests, generated tests, coverage, cost | exact_existing_result |
| recodeagent | Multi-agent ablation | paper ablation campaign | test-pass decrease without specialization | exact_existing_result |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2604.07341 | https://arxiv.org/abs/2604.07341 | 118 repositories, four language pairs | citation only | exact_existing_result | complete 118-project CodeWeaver campaign and paper-style report | results/recodeagent-gpt-5.6-sol-final-2026-08-11 |
