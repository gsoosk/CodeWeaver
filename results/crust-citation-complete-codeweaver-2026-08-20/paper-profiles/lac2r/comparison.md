# LAC2R: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for LAC2R and records the maximum scientifically defensible CodeWeaver comparison. Status: reference_only. Eight subject names overlap the Rustine suite, but revisions/contracts are not proven identical.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

results/rustine-codeweaver-comparison-2026-08-12

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| lac2r | Table 2 | 7 GNU coreutils programs | safety ratio, compile/repair/test rates, queries, tokens, lints | reference_only |
| lac2r | Table 3 | 10 Laertes programs | safety ratio, compile/repair/test rates, queries, tokens, lints | reference_only_name_overlap_only |
| lac2r | Table 4 | 124 TRACTOR public programs | safety, compile/pass, lints, queries, tokens | reference_only |
| lac2r | Table 5 | coreutils | homogeneous versus heterogeneous LLM ablation | reference_only |
| lac2r | Figures 6-8 | three benchmark families | safety, compilation, idiomaticity | reference_only |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2505.15858 | https://arxiv.org/abs/2505.15858 | GNU coreutils, Laertes, TRACTOR public tests | citation only; no CRUST-Bench evaluation | reference_only | eight subject names overlap the Rustine suite, but revisions/contracts are not proven identical | results/rustine-codeweaver-comparison-2026-08-12 |

## CodeWeaver name-overlap audit

| lac2r_subject | rustine_subject | name_overlap | identity_status | codeweaver_compile | codeweaver_fixed_contract |
| --- | --- | --- | --- | --- | --- |
| bzip2 | bzip2 | True | name overlap only; revisions and contracts not proven identical | True | True |
| genann | genann | True | name overlap only; revisions and contracts not proven identical | True | False |
| lil |  | False | no retained Rustine subject |  |  |
| urlparser | urlparser | True | name overlap only; revisions and contracts not proven identical | True | True |
| grabc | grabc | True | name overlap only; revisions and contracts not proven identical | True | False |
| tulip-indicators | tulpindicator | True | name overlap only; revisions and contracts not proven identical | True | False |
| optipng |  | False | no retained Rustine subject |  |  |
| qsort | qsort | True | name overlap only; revisions and contracts not proven identical | True | True |
| snudown | snudown | True | name overlap only; revisions and contracts not proven identical | True |  |
| xzoom | xzoom | True | name overlap only; revisions and contracts not proven identical | True |  |
