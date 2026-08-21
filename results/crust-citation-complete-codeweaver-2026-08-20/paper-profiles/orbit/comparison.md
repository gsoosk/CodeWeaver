# ORBIT: CodeWeaver evidence profile

## Abstract

This profile audits every empirical surface identified for ORBIT and records the maximum scientifically defensible CodeWeaver comparison. Status: measured_existing_slice. All 24 names map exactly to the retained 100-project campaign.

## Evidence boundary

Paper values and CodeWeaver measurements remain separate unless subject identity, revision, denominator, and fixed oracle are verified. Missing values are not converted to zeros.

## Existing result

No separate compatible CodeWeaver result package.

## Complete empirical-surface audit

| key | surface | denominator | metrics | status |
| --- | --- | --- | --- | --- |
| orbit | Table 1 | 7 prior/system rows | dataset, programs, projects above 1K LoC, median/mean LoC | exact_reference |
| orbit | Table 2 | 24 CRUST-Bench projects | LoC, functions, files, tests | exact_reference |
| orbit | Table 3 | 24 CRUST-Bench projects | C2Rust translation/build/test, CRUST-Bench reference build/test, ORBIT expert/generated build/test | exact_reference_and_codeweaver_slice |
| orbit | Table 4 | 24 CRUST-Bench projects | pointer dereferences, pointer arithmetic, unsafe LoC, unsafe percent, LoC for four systems | exact_reference |
| orbit | Table 5 | 13 TRACTOR programs | performance pass fraction, ORBIT result, vector pass rate | exact_reference |
| orbit | Table 6 | 3 CRUST-Bench programs x 4 ablations | function coverage, test coverage, build and test | exact_reference |

## Inclusion and execution decision

| paper_id | source_url | empirical_scope | crust_role | codeweaver_status | reason | existing_result |
| --- | --- | --- | --- | --- | --- | --- |
| arXiv:2604.12048 | https://arxiv.org/abs/2604.12048 | 24 named CRUST-Bench projects plus TRACTOR | exact named subset:24 | measured_existing_slice | all 24 names map exactly to the retained 100-project campaign |  |

## orbit_table1_scale

| system | dataset | programs | percent_over_1kloc | median_loc | mean_loc |
| --- | --- | --- | --- | --- | --- |
| RustMap | Rosetta Code, Bzip2 | 126 | ~1 | ~80 | ~145 |
| Syzygy | Zopfli, URL parser | 2 | 50 | 2700 | 2700 |
| EvoC2Rust | C2R-Bench, Vivo-Bench | 25 | ~8 | ~400 | ~600 |
| RustAssure | 5 C libraries | 5 | 20 | 405 | ~900 |
| SmartC2Rust | GitHub, prior studies | 21 | ~24 | 502 | ~1000 |
| VERT | TransCoder-IR | 534 | 0 | ~100 | ~120 |
| ORBIT | CRUST-Bench | 24 | 91.7 | 1354 | 1603 |

## orbit_table4_safety_summary

| system | scope | mean_unsafe_percent | zero_unsafe_projects | pointer_declarations | pointer_dereferences | note |
| --- | --- | --- | --- | --- | --- | --- |
| C2Rust | 15 compiling projects | 69.6 |  |  |  | range 20.4%-97.4% |
| CRUST-Bench | 11 compiling projects | 0.68 | 8 |  |  | nonzero: razz_simulation, lambda-calculus-eval, libm17 |
| ORBIT expert | 24 projects | 0.06 | 19 | 35 | 5 |  |
| ORBIT generated | 24 projects | 0.11 | 21 | 58 | 6 |  |

## orbit_table5_tractor

| kind | program | performers_passing | performers_total | orbit_result | vector_pass_percent |
| --- | --- | --- | --- | --- | --- |
| exec | 016_switch-arith | 3 | 6 | Pass | 100 |
| exec | 042_float_union | 3 | 6 | Pass | 100 |
| exec | 033_bitfield | 3 | 6 | Pass | 100 |
| exec | 030_int_underflow | 2 | 6 | Pass | 100 |
| exec | 002_stdin_echo | 3 | 6 | Partial | 75 |
| lib | read_scalefactors_lib | 3 | 6 | Pass | 100 |
| lib | 004_loop_lib | 2 | 6 | Pass | 100 |
| lib | read_side_info_lib | 4 | 6 | Pass | 100 |
| lib | wcscat_lib | 4 | 6 | Pass | 100 |
| lib | update_frame_header_lib | 4 | 6 | Pass | 100 |
| lib | 030_int_underflow_lib | 2 | 6 | Fail | 0 |
| lib | contrast_ratio_lib | 3 | 6 | Partial | 62.5 |
| lib | hex2bin_lib | 2 | 6 | Fail | 0 |

## orbit_table6_ablation

| project | configuration | function_coverage_percent | test_coverage_percent | build | test |
| --- | --- | --- | --- | --- | --- |
| CircularBuffer | base | 100 | 0 | True | True |
| CircularBuffer | without interface | 100 | 90.9 | True | True |
| CircularBuffer | without mapping | 100 |  | True | True |
| CircularBuffer | full | 100 |  | True | True |
| LTRE | base | 64.4 | 3.0 | True | True |
| LTRE | without interface | 82.2 | 12.2 | True | True |
| LTRE | without mapping | 93.3 |  | True | True |
| LTRE | full | 100 |  | True | False |
| libm17 | base | 84.1 | 0 | False | False |
| libm17 | without interface | 100 | 100 | True | True |
| libm17 | without mapping | 100 |  | True | True |
| libm17 | full | 100 |  | True | True |

## CodeWeaver exact 24-project summary

| system | projects | build_successes | test_successes | test_success_percent | fixed_tests_passed | fixed_tests_expected | fixed_test_rate_percent | protocol |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORBIT expert interfaces | 24 | 24 | 22 | 91.6666666667 |  |  |  | paper reference; apparent single run |
| ORBIT generated interfaces | 24 | 24 | 22 | 91.6666666667 |  |  |  | paper reference; apparent single run |
| CodeWeaver repetition 1 | 24 | 24 | 11 | 45.833333333333336 | 97 | 188 | 51.59574468085106 | CodeWeaver multi-stage, 5 repairs, 3 parity rounds |
| CodeWeaver repetition 2 | 24 | 24 | 11 | 45.833333333333336 | 95 | 188 | 50.53191489361702 | CodeWeaver multi-stage, 5 repairs, 3 parity rounds |
| CodeWeaver repetition 3 | 24 | 24 | 11 | 45.833333333333336 | 79 | 188 | 42.02127659574468 | CodeWeaver multi-stage, 5 repairs, 3 parity rounds |
