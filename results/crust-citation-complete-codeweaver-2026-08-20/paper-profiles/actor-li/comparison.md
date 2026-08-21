# ACToR: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for ACToR and records the maximum scientifically defensible CodeWeaver comparison. Status: exact_micro_campaign_and_blocked_macro. The six-program absolute hidden oracle is executable and receives three leakage-safe CodeWeaver repetitions; the 57-program macro metric is relative cross-testing without released fixed outputs/tests.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

18/18 build; 14/18 pass all; 1362/1476 hidden cases passed (results/crust-citation-complete-codeweaver-2026-08-20/data/actor-li).

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| actor-li | Figures 2 and 4 | 6 micro + 57 BSD CLI utilities | hidden/differential-test pass by 7 configurations | exact_micro_codeweaver_campaign_and_reference_only_macro |
| actor-li | C2SaferRust augmentation | 7 standalone executables | differential-test pass | exact_reference_public_artifact |
| actor-li | Stability and cost ablations | 3 runs and iteration/test/seed configurations | mean, standard deviation, accuracy and cost | exact_reference_public_artifact |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2510.03879 | https://arxiv.org/abs/2510.03879 | 63 command-line C utilities | citation only | exact_micro_campaign_and_blocked_macro | the six-program absolute hidden oracle is executable and receives three leakage-safe CodeWeaver repetitions; the 57-program macro metric is relative cross-testing without released fixed outputs/tests | results/crust-citation-complete-codeweaver-2026-08-20/data/actor-li |

## actor_li_reference

| surface | scope | system | metric | value | uncertainty |
| --- | --- | --- | --- | --- | --- |
| micro evaluation | 6 utilities / 3 runs | ACToR Claude Code Sonnet 4.5 | hidden-test pass percent | 97.0 | SD 1.9 pp |
| micro evaluation | 6 utilities | naive Claude Code Sonnet 4.5 | hidden-test pass percent | 89.2 |  |
| micro evaluation | 6 utilities / 10 iterations | ACToR Claude Code Sonnet 4.5 | hidden-test pass percent | 98.2 |  |
| macro evaluation | 57 BSD utilities | coverage baseline | relative pass percent | 58.4 |  |
| macro evaluation | 57 BSD utilities | ACToR | relative pass percent | 95.1 |  |
| C2SaferRust augmentation | 7 executables | C2SaferRust | pass percent | 76.3 |  |
| C2SaferRust augmentation | 7 executables | C2SaferRust + ACToR | pass percent | 92.9 |  |
| cost | 57 BSD utilities | coverage baseline | USD | 808 |  |
| cost | 57 BSD utilities | ACToR | USD | 1634 |  |

## CodeWeaver six-program hidden-oracle result

| subject | cells | build | pass_all | safe_pass_all | hidden_tests | test_rate_percent |
| --- | --- | --- | --- | --- | --- | --- |
| csplit | 3 | 3/3 | 2/3 | 2/3 | 209/210 | 99.52% |
| expr | 3 | 3/3 | 2/3 | 2/3 | 200/300 | 66.67% |
| fmt | 3 | 3/3 | 3/3 | 3/3 | 198/198 | 100.00% |
| join | 3 | 3/3 | 2/3 | 2/3 | 250/252 | 99.21% |
| printf | 3 | 3/3 | 2/3 | 2/3 | 238/249 | 95.58% |
| test | 3 | 3/3 | 3/3 | 3/3 | 267/267 | 100.00% |
| ALL | 18 | 18/18 | 14/18 | 14/18 | 1362/1476 | 92.28% |

## CodeWeaver execution telemetry

| subject | elapsed_hours | aiu | premium_requests | output_tokens |
| --- | --- | --- | --- | --- |
| csplit | 4.17 | 4909.659 | 49 | unavailable |
| expr | 3.53 | 4231.305 | 61 | unavailable |
| fmt | 3.62 | 2542.231 | 53 | unavailable |
| join | 4.17 | 3105.143 | 59 | unavailable |
| printf | 4.17 | 2609.613 | 55 | unavailable |
| test | 3.36 | 2367.341 | 60 | unavailable |
| ALL | 23.02 | 19765.291 | 337 | unavailable |
