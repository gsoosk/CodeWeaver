# ReCodeAgent / CodeWeaver Reproducibility Report

## Completion Verdict

Status: COMPLETE
Coverage fraction (raw_runs / full requested matrix): 1.0

All completion criteria met.

## Manifest

118 / 118 projects discovered.

## Execution Coverage (raw_runs, by variant x tool)

| variant | tool | expected | measured | coverage_fraction |
| --- | --- | --- | --- | --- |
| full | alphatrans | 12 | 12 | 1.0000 |
| full | crust | 300 | 300 | 1.0000 |
| full | oxidizer | 18 | 18 | 1.0000 |
| full | skel | 24 | 24 | 1.0000 |

## Blockers (collect.py failures.csv)

No failures recorded (or failures.csv was not supplied).

## Blockers (test_compare.py comparison_failures.csv)

No failures recorded (or test_compare.py has not been run / comparison_failures.csv was not supplied).

## Analysis Availability

analyze.py has been run; table1_effectiveness/table2_test_translation/figure7_ablation/figure8_cost_tools are available in the analysis output root. The exact paper_table1_side_by_side.csv, paper_table2_side_by_side.csv, and paper_tables_side_by_side.pdf comparison artifacts are also available.

## Protocol and revision provenance

Frozen protocol fields: model, agent_timeout_seconds, codeweaver_package_version.
Protocol-consistent: True.
Strictly identical environment metadata: False.

Recorded informational revision drift (retained exactly and treated as a validity threat, not collapsed):
  - git_sha: 6 exact value(s): 3c6f1d63b5d9d868e6f9f3207e11619f944e51e8, 58ef7b06dff42ca4227d7998c0df620cf96bb5aa, 72529ee879e383df5ac5526cf2a2075a3a9c3d68, 8e7fc421b1e1597dafba55b60390512b5c8ffb38, aecaba9f4bb0b5e472cfd615e19bf9bb30d00fa7, e51a794bf90db676d177cee0e781a749f748acbd
  - copilot_cli_version: 6 exact value(s): GitHub Copilot CLI 1.0.79-3., GitHub Copilot CLI 1.0.79-4., GitHub Copilot CLI 1.0.79-5., GitHub Copilot CLI 1.0.79-6., GitHub Copilot CLI 1.0.79-7., GitHub Copilot CLI 1.0.79-9.

## Cross-System Comparison: Design and Tracks

Tracks:
  - fresh GPT-5.6 Sol CodeWeaver runs
  - released-artifact ReCodeAgent/prior replay
  - workbook-only published reference (non-replayed)

CodeWeaver GPT-5.6 Sol is not model-matched to the original systems/models. Released ReCodeAgent/prior outputs are post-hoc artifact replay measurements, not fresh runs. Results are cross-system observational comparisons.

Released SWE-agent CRUST targets are unavailable and were never fabricated. The optional workbook can appear only as the separate published_reference_non_replayed per-project compilation track.

Unavailable costs remain unavailable and are never treated as zero.

## Cross-System Comparison: Inventory and Completeness

| system | tool | repetition | expected | measured | unavailable | error | missing | accounted_missing | unaccounted_missing | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| codeweaver | crust | 0 | 100 | 100 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | oxidizer | 0 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | alphatrans | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | skel | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | crust | 1 | 100 | 100 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | oxidizer | 1 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | alphatrans | 1 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | skel | 1 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | crust | 2 | 100 | 100 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | oxidizer | 2 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | alphatrans | 2 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | measured |
| codeweaver | skel | 2 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | measured |
| recodeagent | crust | 0 | 100 | 99 | 0 | 0 | 1 | 1 | 0 | missing |
| recodeagent | oxidizer | 0 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | measured |
| recodeagent | alphatrans | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | measured |
| recodeagent | skel | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | measured |
| prior | crust | 0 | 100 | 0 | 100 | 0 | 0 | 0 | 0 | missing |
| prior | oxidizer | 0 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | measured |
| prior | alphatrans | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | measured |
| prior | skel | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | measured |

## Cross-System Comparison: CodeWeaver Three-Repetition All-Tools Summary

| metric | n | mean | sample_sd | ci_95_t | status | reason |
| --- | --- | --- | --- | --- | --- | --- |
| compilation_success | 3 | 1.0000 | 0.0000 | [1.0, 1.0] | measured |  |
| project_pass_all | 3 | 0.5141 | 0.0049 | [0.5019699075430806, 0.5262786800275407] | measured |  |
| validated_test_micro_pass_rate | 3 | 0.4252 | 0.0061 | [0.41019679772302653, 0.4403015411474053] | measured |  |
| validated_test_macro_pass_rate | 3 | 0.6326 | 0.0049 | [0.6204641186508332, 0.6447762184728173] | measured |  |

## Cross-System Comparison: Primary Rep-0 Paired All-Tools Results

| metric | n | cw_yes_rca_no_wins | rca_yes_cw_no_losses | cw_wins | rca_losses | ties | delta_percentage_points | mean_delta_percentage_points | exact_mcnemar_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| compilation_success | 117 | 37 | 0 |  |  | 80 | 31.6239 |  | 0.0000 |
| project_pass_all | 117 | 27 | 15 |  |  | 75 | 10.2564 |  | 0.0884 |
| validated_test_project_rate | 117 |  |  | 12 | 30 | 75 |  | -8.7477 |  |

## Cross-System Comparison: CRUST Three-System Overlap

Status: measured; triples: 99. 

| codeweaver_rep0 | recodeagent_replay | swe_agent_workbook | count | swe_agent_track |
| --- | --- | --- | --- | --- |
| False | False | False | 0 | published_reference_non_replayed |
| False | False | True | 0 | published_reference_non_replayed |
| False | True | False | 0 | published_reference_non_replayed |
| False | True | True | 0 | published_reference_non_replayed |
| True | False | False | 21 | published_reference_non_replayed |
| True | False | True | 16 | published_reference_non_replayed |
| True | True | False | 37 | published_reference_non_replayed |
| True | True | True | 25 | published_reference_non_replayed |

## Cross-System Comparison: Measured Cost/Correctness Frontier

Status: unavailable. fewer than two systems have genuinely measured, same-unit actual costs; missing replay costs were not mapped to zero

| system | track | cost_status | mean_actual_cost | n_cost_projects | cost_missing_projects | correctness_status | project_pass_all_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| codeweaver | measured | measured | 2537095697245.7627 | 118 | 0 | measured | 0.5169 |
| recodeagent | released_artifact_replay | unavailable |  | 0 | 117 | measured | 0.4188 |
| prior | released_artifact_replay | unavailable |  | 0 | 18 | measured | 0.1667 |

Missing or unavailable cost is not zero and is excluded from the measured frontier.
