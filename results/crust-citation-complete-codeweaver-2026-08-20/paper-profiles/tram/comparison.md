# TRAM: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for TRAM and records the maximum scientifically defensible CodeWeaver comparison. Status: not_comparable. Validation method and language pair differ.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| tram | AlphaTrans benchmark evaluation | 10 Java projects / 17,874 fragments | translation and in-isolation mock validation | reference_only_partial_subject_overlap |
| tram | Validation mechanism evaluation | translated focal methods | return values and side-effect equivalence | reference_only_not_metric_aligned |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2511.21878 | https://arxiv.org/abs/2511.21878 | mock-based Java-to-Python in-isolation validation | citation only | not_comparable | validation method and language pair differ |  |
