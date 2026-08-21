# Hayroll: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for Hayroll and records the maximum scientifically defensible CodeWeaver comparison. Status: not_comparable. Specialized preprocessing task has no shared end-to-end metric.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| hayroll | CRUST-Bench macro/config evaluation | paper-selected CRUST inputs | macro and conditional-compilation reconstruction | public_artifact_not_comparable |
| hayroll | LibmCS and zlib evaluation | two macro-heavy systems | translation and macro preservation | public_artifact_not_comparable |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| DOI 10.1145/3808276 | https://doi.org/10.1145/3808276 | macro and conditional-compilation wrapper translation | citation only | not_comparable | specialized preprocessing task has no shared end-to-end metric |  |
