# PtrTrans: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for PtrTrans and records the maximum scientifically defensible CodeWeaver comparison. Status: public_artifact_license_restricted. Crown-16 is disjoint from CRUST-Bench and cannot be redistributed without a license.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| ptrtrans | Tables 1-2 | 16 Crown projects | subject size and fuzz-test coverage | exact_reference_public_read_only |
| ptrtrans | Tables 3-4 | 16 Crown projects | lints, unsafe usage, compiled and equivalent functions | exact_reference_public_read_only |
| ptrtrans | Table 5 | 10 small Crown projects x 5 ablations | compiled and equivalent functions | exact_reference_public_read_only |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2510.10956 | https://arxiv.org/abs/2510.10956 | 16 Crown projects | citation only | public_artifact_license_restricted | Crown-16 is disjoint from CRUST-Bench and cannot be redistributed without a license |  |

## ptrtrans_reference

| surface | scope | system | metric | value |
| --- | --- | --- | --- | --- |
| Table 3 | Crown-16 total | Crown | lint alerts | 6802 |
| Table 3 | Crown-16 total | PR2 | lint alerts | 4135 |
| Table 3 | Crown-16 total | PtrTrans | lint alerts | 349 |
| Table 3 | Crown-16 total | Crown | unsafe usages | 141866 |
| Table 3 | Crown-16 total | PR2 | unsafe usages | 134185 |
| Table 3 | Crown-16 total | PtrTrans | unsafe usages | 85 |
| Table 4 | small projects | FLOURINE | compiled/equivalent percent | 69.9/52.3 |
| Table 4 | small projects | PtrTrans | compiled/equivalent percent | 98.3/81.6 |
| Table 4 | large projects | FLOURINE | compiled/equivalent percent | 64.0/14.2 |
| Table 4 | large projects | PtrTrans | compiled/equivalent percent | 85.9/67.9 |
| Table 5 | small-10 average | PtrTrans_PS | compiled/equivalent percent | 89.3/59.5 |
| Table 5 | small-10 average | PtrTrans_PU | compiled/equivalent percent | 84.6/52.9 |
| Table 5 | small-10 average | PtrTrans_RA | compiled/equivalent percent | 87.9/61.9 |
| Table 5 | small-10 average | PtrTrans_EC | compiled/equivalent percent | 66.0/50.8 |
| Table 5 | small-10 average | PtrTrans | compiled/equivalent percent | 100/81.6 |
