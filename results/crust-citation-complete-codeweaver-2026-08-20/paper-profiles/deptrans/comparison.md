# DepTrans: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for DepTrans and records the maximum scientifically defensible CodeWeaver comparison. Status: blocked. No exact public benchmark source and fixed oracle.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| deptrans | Benchmark statistics | 145 repository instances / 85K training samples | dependencies and project characteristics | blocked_unreleased |
| deptrans | Main comparison | 145 instances | 60.7% compilation and 43.5% computational accuracy | abstract_reference_only |
| deptrans | Huawei case study | 15 internal projects | successful builds | blocked_internal |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2604.02852 | https://arxiv.org/abs/2604.02852 | 145-instance benchmark and 15 Huawei projects | citation only | blocked | no exact public benchmark source and fixed oracle |  |

## blocked_aggregate_references

| paper | scope | metric | value | status |
| --- | --- | --- | --- | --- |
| DepTrans | 145 repository instances | compilation success percent | 60.7 | abstract aggregate; benchmark unreleased |
| DepTrans | 145 repository instances | computational accuracy percent | 43.5 | abstract aggregate; benchmark unreleased |
| DepTrans | 15 industrial projects | successful builds | 7 | internal Huawei subjects unreleased |
