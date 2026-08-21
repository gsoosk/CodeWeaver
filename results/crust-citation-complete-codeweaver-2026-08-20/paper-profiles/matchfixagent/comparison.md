# MatchFixAgent: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for MatchFixAgent and records the maximum scientifically defensible CodeWeaver comparison. Status: not_comparable. Validator/repair verdict metrics are not translator success metrics.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| matchfixagent | Validation evaluation | repository translation pairs | verdict coverage and agreement | reference_only_not_comparable |
| matchfixagent | Repair evaluation | inequivalent translation pairs | repair success versus baseline | reference_only_not_comparable |
| matchfixagent | Ablation | paper evaluation set | verdict accuracy and token use without analyses/test generation | reference_only_not_comparable |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2509.16187 | https://arxiv.org/abs/2509.16187 | translation validation and repair | citation only | not_comparable | validator/repair verdict metrics are not translator success metrics |  |
