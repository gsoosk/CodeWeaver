# &inator: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for &inator and records the maximum scientifically defensible CodeWeaver comparison. Status: not_comparable. Interface synthesis is not end-to-end project translation.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| and-inator | Interface grammar/type table | supported C/Rust type forms | ownership, borrowing, mutability, lifetimes | reference_only_not_comparable |
| and-inator | CRUST-Bench interface evaluation | CRUST-Bench C inputs/interfaces | interface correctness and precision | reference_only_not_comparable |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2604.17261 | https://arxiv.org/abs/2604.17261 | C-to-Rust interface translation | citation only | not_comparable | interface synthesis is not end-to-end project translation |  |
