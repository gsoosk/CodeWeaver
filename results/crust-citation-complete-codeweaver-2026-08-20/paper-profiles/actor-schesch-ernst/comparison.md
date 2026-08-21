# ACTOR (Schesch and Ernst): CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for ACTOR (Schesch and Ernst) and records the maximum scientifically defensible CodeWeaver comparison. Status: reference_87_and_measured_public_95_overlap. Paper values retain denominator 87, but the pinned results submodule contains 95 project directories and does not identify the paper's 13 exclusions; CodeWeaver's matching public 95 are reported separately.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

results/crust-bench-codeweaver-comparison-2026-08-14

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| actor-schesch-ernst | Figure 3 | 338 TRACTOR cases x 11 systems | compiles, passes, LoC, unsafe percent | exact_reference_public_artifact |
| actor-schesch-ernst | Figures 4-5 | failure classes and 382 output files | failure and unsafe root-cause taxonomy | exact_reference_public_artifact |
| actor-schesch-ernst | Figure 6 | 87 CRUST-Bench projects x systems/settings | builds, tests, LoC, unsafe percent | exact_reference_denominator_unresolved_separate_public_95_overlap |
| actor-schesch-ernst | Figure 7 | TRACTOR and two CRUST-Bench modes | prompt-sensitivity ablations | exact_reference_public_artifact |
| actor-schesch-ernst | Cost analysis | CRUST-Bench, TRACTOR and ablations | USD, minutes and per-kLoC cost | exact_reference_public_artifact |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| IEEE S&P 2026 | https://homes.cs.washington.edu/~mernst/pubs/c-to-rust-ieeesp2026-abstract.html | paper: 87 CRUST-Bench projects and 338 TRACTOR cases; public result artifact: 95 CRUST project directories | paper's 87-project exclusion set is not recoverable; separately labeled public-artifact 95-project overlap | reference_87_and_measured_public_95_overlap | paper values retain denominator 87, but the pinned results submodule contains 95 project directories and does not identify the paper's 13 exclusions; CodeWeaver's matching public 95 are reported separately | results/crust-bench-codeweaver-comparison-2026-08-14 |

## actor_schesch_figure6_crust

| system | setting | denominator | builds | tests | loc | unsafe_percent |
| --- | --- | --- | --- | --- | --- | --- |
| ACTOR Kiro | no benchmark tests | 87 | 82 | 56 | 43000 | 1 |
| C2Rust/Laertes/C2SaferRust/SmartC2Rust | no benchmark tests | 87 | 0 | 0 |  |  |
| GPT-5.4 | no benchmark tests | 87 | 82 | 50 | 57000 | 0 |
| Kimi K2.5 | no benchmark tests | 87 | 46 | 31 | 28000 | 0 |
| Gemini 3.1 Pro | no benchmark tests | 87 | 11 | 8 | 15000 | 0 |
| ACTOR Kiro | test repair | 87 | 87 | 82 | 52000 | 1 |
| ACTOR Claude | test repair | 87 | 85 | 75 | 45000 | 0 |
| ACTOR Codex | test repair | 87 | 87 | 81 | 48000 | 1 |
| GPT-5.4 | test repair | 87 | 79 | 64 | 58000 | 0 |
| Kimi K2.5 | test repair | 87 | 45 | 39 | 28000 | 0 |
| Gemini 3.1 Pro | test repair | 87 | 8 | 7 | 15000 | 0 |

## actor_schesch_figure3_tractor_totals

| system | compiles | passes | denominator | loc | unsafe_percent |
| --- | --- | --- | --- | --- | --- |
| ACTOR Kiro | 338 | 325 | 338 | 47000 | 50 |
| ACTOR Claude | 338 | 319 | 338 | 53000 | 53 |
| ACTOR Codex | 337 | 244 | 338 | 36000 | 39 |
| ACTOR Kiro no validation | 337 | 230 | 338 | 37000 | 50 |
| C2Rust | 205 | 204 | 338 | 87000 | 70 |
| Laertes | 202 | 201 | 338 | 88000 | 66 |
| C2SaferRust | 193 | 154 | 338 | 82000 | 59 |
| SmartC2Rust | 48 | 40 | 338 | 7000 | 2 |
| Kimi K2.5 | 157 | 118 | 338 | 25000 | 17 |
| GPT-5.4 | 189 | 154 | 338 | 28000 | 10 |
| Gemini 3.1 Pro | 186 | 156 | 338 | 24000 | 15 |

## actor_schesch_figure4_failures

| root_cause | count |
| --- | --- |
| undefined behavior | 3 |
| macros | 3 |
| configuration | 1 |
| input processing | 9 |
| underspecified | 2 |
| truncated output | 12 |

## actor_schesch_figure5_unsafe

| root_cause | count |
| --- | --- |
| C string/pointer conversion | 2194 |
| raw-pointer signatures/casts | 5957 |
| pointer arithmetic | 3931 |
| C ABI preservation | 1648 |
| ptr read/write/copy | 527 |
| FFI calls | 208 |
| mutable global | 116 |
| uninitialized structs | 70 |
| bridging raw pointers | 60 |
| function-pointer dispatch | 36 |
| other | 44 |

## actor_schesch_figure7_prompts

| configuration | tractor_passes | tractor_denominator | crust_no_tests_passes | crust_test_repair_passes | crust_denominator |
| --- | --- | --- | --- | --- | --- |
| ACTOR Claude | 319 | 338 | 56 | 75 | 87 |
| without subtask | 313 | 338 | 56 | 79 | 87 |
| without iteration | 249 | 338 | 31 | 73 | 87 |
| without features | 204 | 338 | 55 | 76 | 87 |
| minimal | 171 | 338 | 41 | 75 | 87 |

## actor_schesch_cost

| system | scope | cost_usd | minutes | cost_per_kloc_usd | minutes_per_kloc |
| --- | --- | --- | --- | --- | --- |
| ACTOR Kiro | CRUST-Bench | 67 |  | 1.57 | 19 |
| ACTOR Kiro | TRACTOR | 93 |  | 1.97 | 34 |
| ACTOR Kiro | largest P01 case | 3.61 | 76 |  |  |
| Claude Code | TRACTOR | 570 |  |  |  |
| all configurations | full ablation | 2900 |  |  |  |

## CodeWeaver public-artifact 95-project overlap

| system | public_artifact_projects | paper_projects | paper_membership_status | build_successes | test_successes | fixed_tests_passed | fixed_tests_expected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CodeWeaver repetition 1 | 95 | 87 | unresolved; not treated as the paper's 87-project slice | 95 | 56 | 425 | 564 |
| CodeWeaver repetition 2 | 95 | 87 | unresolved; not treated as the paper's 87-project slice | 95 | 55 | 433 | 564 |
| CodeWeaver repetition 3 | 95 | 87 | unresolved; not treated as the paper's 87-project slice | 95 | 54 | 403 | 564 |
