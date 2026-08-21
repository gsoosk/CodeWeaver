# CodeWeaver comparison with the complete CRUST-Bench citation corpus

## Abstract

We reconciled all 30 Semantic Scholar citation records for CRUST-Bench into 19 unique migration-relevant works, eight tangential works, one out-of-scope work, and two duplicate records. Every in-scope work and every empirical surface found in its paper is inventoried. ORBIT's exact 24-project subset is newly evaluated from the frozen CodeWeaver three-repetition campaign, and ACToR's six-program absolute experiment is newly evaluated with a qualified 492-case hidden differential oracle over 18 CodeWeaver cells. Schesch/Ernst ACTOR's paper-87 values are separated from the pinned public artifact's 95 project directories. Other scores are reused only where subject identity and fixed contracts were already verified. Unreleased or metric-incompatible studies remain explicit blockers, never synthetic zeros or inferred wins.

## Census method

The primary citation graph was Semantic Scholar's complete 30-record edge list as of 2026-08-20, cross-checked against OpenAlex, arXiv, publisher pages, and artifact repositories. InariRoll was resolved as a Hayroll duplicate, and two title variants were resolved as one Schesch/Ernst ACTOR paper.

## Measurement rule

A CodeWeaver score is included only when the exact retained subject and a fixed independent oracle are available. Shared names without revision/hash equality, function-level validation metrics, interface inference, annotation synthesis, and terminal-agent task accuracy are not relabeled as repository pass-all.

## ORBIT result

ORBIT reports 22/24 test-successful projects in both interface modes. Across the same 24 named projects, CodeWeaver's three repetitions average 45.83% project pass-all. ORBIT is an apparent single run while CodeWeaver retains all three outcomes, so this is an exact-subject descriptive comparison rather than a controlled architecture ablation.

## ACToR absolute micro result

The pinned Li et al. artifact exposes six micro utilities, 15 seed tests per utility, and a separate fixed validation suite of 70, 100, 66, 84, 83, and 89 cases (492 total). Each C reference passed its own full contract before the validation files were kept outside all model-readable workspaces. Across 18 CodeWeaver cells, 14/18 passed every hidden case and 14/18 also contained no candidate-owned `unsafe` token or process delegation. Candidate binaries ran in a mount/PID-namespace chroot where reference and contract contents were masked by read-only empty mounts, Linux capabilities were cleared, and system executables were absent. All six compiling stub negative controls failed the full contract (1/492 cases passed), confirming that pass-all is non-vacuous. The public fixed contracts are included in the result package only after execution, with per-file checksums. A fully pre-model unauthenticated launcher attempt is archived as infrastructure evidence and excluded from all 18 measured cells. The shared fixed oracle supports a same-subject descriptive comparison, not a controlled ACToR architecture ablation: CodeWeaver uses its frozen five-repair, three-parity protocol, whereas the paper reports naive, collaborative, and ten-iteration ACToR configurations.

## ACTOR denominator boundary

Schesch and Ernst report Figure 6 over 87 CRUST-Bench projects, but the pinned public results submodule contains 95 CRUST project directories and does not encode the paper's 13-project exclusion set. The paper's 87-denominator values therefore remain exact references only. CodeWeaver outcomes over the independently verifiable 95-directory overlap are a separate table and are never labeled as a reproduction of Figure 6.

## Availability boundary

RustPrint, DepTrans, PtrTrans, RustAssure, and several adjacent systems do not expose the exact evaluated revisions and fixed contracts needed for leakage-safe execution. Li et al. ACToR's 57-program macro metric remains blocked because it is cross-testing against unreleased system-generated outputs/tests, while its six-program absolute experiment is measured here. Schesch/Ernst ACTOR's exact paper-87 membership remains unresolved. EvoC2Rust's C2R-Bench/industrial set and DepTrans's Huawei set are explicitly unreleased. The package records these blockers and the maximum public comparison for each paper.

## Prior-result audit

The five earlier paper packages now include a complete source-paper surface inventory, structured reference tables for previously omitted dataset/error/cost/ablation results, CodeWeaver cost and coverage telemetry, corrected version labels, and final-output Clippy analysis where executable.

## Per-paper publication profiles

The `paper-profiles/` directory contains one human-readable PDF, Markdown report, complete empirical-surface inventory, decision record, and available structured reference tables for each of the 20 included works. These profiles link compatible standalone CodeWeaver packages and retain blockers for incompatible surfaces.

## Citation reconciliation

| Population | Count | Disposition |
| --- | --- | --- |
| Semantic Scholar records | 30 | 19 unique in-scope + 8 tangential + 1 out-of-scope + 2 duplicates |
| Unique in-scope works | 19 | all included in the decision matrix |
| Tangential works | 8 | TACO retained because it evaluates CRUST-Bench |
| Duplicate index records | 2 | resolved to Hayroll and Schesch/Ernst ACTOR |

## Exact ORBIT 24-project comparison

| System | Build | Pass all | Fixed tests | Protocol |
| --- | --- | --- | --- | --- |
| ORBIT expert interfaces | 24/24 | 22/24 (91.67%) | not reported | paper reference; apparent single run |
| ORBIT generated interfaces | 24/24 | 22/24 (91.67%) | not reported | paper reference; apparent single run |
| CodeWeaver repetition 1 | 24/24 | 11/24 (45.83%) | 97/188 | CodeWeaver multi-stage, 5 repairs, 3 parity rounds |
| CodeWeaver repetition 2 | 24/24 | 11/24 (45.83%) | 95/188 | CodeWeaver multi-stage, 5 repairs, 3 parity rounds |
| CodeWeaver repetition 3 | 24/24 | 11/24 (45.83%) | 79/188 | CodeWeaver multi-stage, 5 repairs, 3 parity rounds |

## ORBIT per-subject outcomes

| Project | LoC | ORBIT expert | ORBIT generated | CW passing reps | CW fixed tests |
| --- | --- | --- | --- | --- | --- |
| CircularBuffer | 213 | pass | pass | 3/3 | 3/3 |
| Simple-Config | 719 | pass | pass | 3/3 | 21/21 |
| VaultSync | 1121 | pass | pass | 0/3 | 0/3 |
| mvptree | 1121 | pass | pass | 2/3 | 2/3 |
| razz_simulation | 1145 | pass | pass | 0/3 | 0/3 |
| Remimu | 1162 | pass | pass | 3/3 | 3/3 |
| libpgn | 1162 | fail | pass | 0/3 | 50/60 |
| LTRE | 1212 | pass | fail | 2/3 | 2/3 |
| lambda-calculus-eval | 1264 | pass | pass | 2/3 | 65/66 |
| jccc | 1310 | pass | pass | 3/3 | 12/12 |
| libpsbt | 1331 | pass | pass | 1/3 | 10/12 |
| mdb | 1340 | pass | pass | 3/3 | 12/12 |
| Genetic-neural-network-for-simple-control | 1367 | pass | pass | 0/3 | 0/69 |
| impcheck | 1397 | fail | pass | 0/3 | 0/18 |
| cfsm | 1446 | pass | pass | 0/3 | 0/3 |
| worsp | 1494 | pass | pass | 3/3 | 12/12 |
| libutf | 1525 | pass | pass | 0/3 | 0/33 |
| kairoCompiler | 1589 | pass | pass | 0/3 | 0/6 |
| fslib | 1958 | pass | pass | 0/3 | 38/162 |
| XOpt | 2113 | pass | pass | 3/3 | 6/6 |
| recordManager | 2400 | pass | pass | 3/3 | 9/9 |
| libm17 | 2901 | pass | pass | 0/3 | 12/21 |
| tisp | 3562 | pass | fail | 0/3 | 0/3 |
| Megalania | 3621 | pass | pass | 2/3 | 14/21 |

## Existing publication-ready CodeWeaver evidence

| Study | Scope | Headline | Result path |
| --- | --- | --- | --- |
| ReCodeAgent | 118 projects / four language pairs | full raw data, baselines, ablations, tables, figures, and PDF | results/recodeagent-gpt-5.6-sol-final-2026-08-11 |
| CRUST-Bench | 100 projects x 3 repetitions | 300/300 build; 165/300 pass all | results/crust-bench-codeweaver-comparison-2026-08-14 |
| SACTOR exact subset | 50 projects x 3 repetitions | 150/150 build; 92/150 pass all | results/sactor-codeweaver-comparison-2026-08-14 |
| Rustine | 23 projects x 1 repetition | 21/23 compile; 10/21 fixed-contract pass | results/rustine-codeweaver-comparison-2026-08-12 |
| EvoC2Rust public Vivo-Bench | 15 groups / 19 modules x 3 repetitions | 100% incremental compilation, fill compilation, and fixed-test rate; mean SafeRate 30.92% | results/evoc2rust-codeweaver-comparison-2026-08-13 |
| RepoTransBench historical slice | 3 projects x 3 repetitions | 9/9 independently build and pass all fixed tests | results/repotransbench-codeweaver-comparison-2026-08-14 |
| RustRepoTrans language slice | 3 tasks x 3 repetitions | 9/9 independently build and pass all fixed tests | results/rustrepotrans-codeweaver-comparison-2026-08-14 |

## Schesch/Ernst ACTOR public-artifact 95-project overlap

| System | Build | Pass all | Fixed tests | Boundary |
| --- | --- | --- | --- | --- |
| CodeWeaver repetition 1 | 95/95 | 56/95 | 425/564 | unresolved; not treated as the paper's 87-project slice |
| CodeWeaver repetition 2 | 95/95 | 55/95 | 433/564 | unresolved; not treated as the paper's 87-project slice |
| CodeWeaver repetition 3 | 95/95 | 54/95 | 403/564 | unresolved; not treated as the paper's 87-project slice |

## Li et al. ACToR six-program absolute hidden-oracle result

| Subject | Build | Pass all | Safe pass | Hidden tests | Test rate |
| --- | --- | --- | --- | --- | --- |
| csplit | 3/3 | 2/3 | 2/3 | 209/210 | 99.52% |
| expr | 3/3 | 2/3 | 2/3 | 200/300 | 66.67% |
| fmt | 3/3 | 3/3 | 3/3 | 198/198 | 100.00% |
| join | 3/3 | 2/3 | 2/3 | 250/252 | 99.21% |
| printf | 3/3 | 2/3 | 2/3 | 238/249 | 95.58% |
| test | 3/3 | 3/3 | 3/3 | 267/267 | 100.00% |
| ALL | 18/18 | 14/18 | 14/18 | 1362/1476 | 92.28% |

## Li et al. ACToR CodeWeaver execution telemetry

| Subject | Elapsed hours | Output tokens | AIU | Premium requests |
| --- | --- | --- | --- | --- |
| csplit | 4.17 | unavailable (unavailable) | 4909.659 | 49 |
| expr | 3.53 | unavailable (unavailable) | 4231.305 | 61 |
| fmt | 3.62 | unavailable (unavailable) | 2542.231 | 53 |
| join | 4.17 | unavailable (unavailable) | 3105.143 | 59 |
| printf | 4.17 | unavailable (unavailable) | 2609.613 | 55 |
| test | 3.36 | unavailable (unavailable) | 2367.341 | 60 |
| ALL | 23.02 | unavailable (unavailable) | 19765.291 | 337 |

## Li et al. ACToR published reference results

| Surface | Scope | System | Metric | Value | Uncertainty |
| --- | --- | --- | --- | --- | --- |
| micro evaluation | 6 utilities / 3 runs | ACToR Claude Code Sonnet 4.5 | hidden-test pass percent | 97.0 | SD 1.9 pp |
| micro evaluation | 6 utilities | naive Claude Code Sonnet 4.5 | hidden-test pass percent | 89.2 | not reported |
| micro evaluation | 6 utilities / 10 iterations | ACToR Claude Code Sonnet 4.5 | hidden-test pass percent | 98.2 | not reported |
| macro evaluation | 57 BSD utilities | coverage baseline | relative pass percent | 58.4 | not reported |
| macro evaluation | 57 BSD utilities | ACToR | relative pass percent | 95.1 | not reported |
| C2SaferRust augmentation | 7 executables | C2SaferRust | pass percent | 76.3 | not reported |
| C2SaferRust augmentation | 7 executables | C2SaferRust + ACToR | pass percent | 92.9 | not reported |
| cost | 57 BSD utilities | coverage baseline | USD | 808 | not reported |
| cost | 57 BSD utilities | ACToR | USD | 1634 | not reported |

## Complete inclusion and execution matrix

| Paper | Empirical scope | Status | Reason |
| --- | --- | --- | --- |
| ORBIT | 24 named CRUST-Bench projects plus TRACTOR | measured_existing_slice | all 24 names map exactly to the retained 100-project campaign |
| SACTOR | TransCoder-IR, CodeNet, 50 CRUST-Bench projects, libogg | exact_existing_result | three CodeWeaver repetitions on the exact 50-project subset |
| Rustine | 23 C repositories | exact_existing_result | leakage-safe CodeWeaver evaluation on all 23 released subjects |
| EvoC2Rust | Vivo-Bench, C2R-Bench, six industrial projects | partial_existing_result | three repetitions cover public Vivo-Bench; C2R-Bench and industrial projects are unreleased |
| RustPrint | eight repositories, 11K-84K LoC | public_artifact_new_run_required | CodeWikiBench's eight repositories are disjoint from retained CRUST-Bench tasks |
| ReCodeAgent | 118 repositories, four language pairs | exact_existing_result | complete 118-project CodeWeaver campaign and paper-style report |
| DepTrans | 145-instance benchmark and 15 Huawei projects | blocked | no exact public benchmark source and fixed oracle |
| PtrTrans | 16 Crown projects | public_artifact_license_restricted | Crown-16 is disjoint from CRUST-Bench and cannot be redistributed without a license |
| &inator | C-to-Rust interface translation | not_comparable | interface synthesis is not end-to-end project translation |
| RustAssure | five applications/libraries; differential symbolic validation | public_artifact_metric_mismatch | function-level KLEE equivalence is not CodeWeaver project pass-all |
| ACToR | 63 command-line C utilities | exact_micro_campaign_and_blocked_macro | the six-program absolute hidden oracle is executable and receives three leakage-safe CodeWeaver repetitions; the 57-program macro metric is relative cross-testing without released fixed outputs/tests |
| MatchFixAgent | translation validation and repair | not_comparable | validator/repair verdict metrics are not translator success metrics |
| LAC2R | GNU coreutils, Laertes, TRACTOR public tests | reference_only | eight subject names overlap the Rustine suite, but revisions/contracts are not proven identical |
| Fine-Tuning Qwen3-27B | SACTOR-framework function translation | not_comparable | function-level SACTOR evaluation is not a repository project oracle |
| Hayroll | macro and conditional-compilation wrapper translation | not_comparable | specialized preprocessing task has no shared end-to-end metric |
| CNnotator | memory-safety annotation synthesis | not_comparable | annotation synthesis is not repository translation |
| TRAM | mock-based Java-to-Python in-isolation validation | not_comparable | validation method and language pair differ |
| Formal Compositional Reasoning | formal compositional code-translation reasoning | not_comparable | methodology/position contribution lacks a compatible released project oracle |
| ACTOR (Schesch and Ernst) | paper: 87 CRUST-Bench projects and 338 TRACTOR cases; public result artifact: 95 CRUST project directories | reference_87_and_measured_public_95_overlap | paper values retain denominator 87, but the pinned results submodule contains 95 project directories and does not identify the paper's 13 exclusions; CodeWeaver's matching public 95 are reported separately |
| TACO | terminal-agent context compression over six benchmarks | reference_only | 47.00% to 48.05% terminal-task accuracy is not project pass-all |

## ACTOR CRUST-Bench reference (Figure 6)

| System | Setting | Build | Pass all | LoC | Unsafe |
| --- | --- | --- | --- | --- | --- |
| ACTOR Kiro | no benchmark tests | 82/87 | 56/87 | 43000 | 1% |
| C2Rust/Laertes/C2SaferRust/SmartC2Rust | no benchmark tests | 0/87 | 0/87 | not reported | not reported |
| GPT-5.4 | no benchmark tests | 82/87 | 50/87 | 57000 | 0% |
| Kimi K2.5 | no benchmark tests | 46/87 | 31/87 | 28000 | 0% |
| Gemini 3.1 Pro | no benchmark tests | 11/87 | 8/87 | 15000 | 0% |
| ACTOR Kiro | test repair | 87/87 | 82/87 | 52000 | 1% |
| ACTOR Claude | test repair | 85/87 | 75/87 | 45000 | 0% |
| ACTOR Codex | test repair | 87/87 | 81/87 | 48000 | 1% |
| GPT-5.4 | test repair | 79/87 | 64/87 | 58000 | 0% |
| Kimi K2.5 | test repair | 45/87 | 39/87 | 28000 | 0% |
| Gemini 3.1 Pro | test repair | 8/87 | 7/87 | 15000 | 0% |

## Public-artifact reference highlights

| Paper | Scope | System | Metric | Value |
| --- | --- | --- | --- | --- |
| RustPrint | 8 | RustPrint Kimi | compiled repositories | 8 |
| RustPrint | 8 | RustPrint GPT-5.4 | compiled repositories | 8 |
| RustPrint | 8 | Self-Repair | compiled repositories | 0 |
| RustPrint | 8 | EvoC2Rust | compiled repositories | 0 |
| RustPrint | 8 | C2Rust | compiled repositories | 8 |
| RustPrint | 8 | Claude Code | compiled repositories | 8 |
| RustPrint | 16 cells | RustPrint GPT-5.4 | aggregate cross-test TPR percent | 98.7 |
| RustPrint | 16 cells | RustPrint Kimi | aggregate cross-test TPR percent | 95.17 |
| RustPrint | 16 cells | Claude Code | aggregate cross-test TPR percent | 79.85 |
| RustPrint | 8 repositories | RustPrint Kimi | feature conservation percent | 93.26 |
| RustPrint | 8 repositories | RustPrint GPT-5.4 | feature conservation percent | 97.76 |
| RustPrint | 8 repositories | Claude Code Kimi | feature conservation percent | 52.52 |
| RustPrint | 8 repositories | Claude Code GPT-5.4 | feature conservation percent | 48.87 |
| RustPrint | 8 repositories | RustPrint Kimi | SafeRate A/F percent | 96.23/96.19 |
| RustPrint | 8 repositories | RustPrint GPT-5.4 | SafeRate A/F percent | 99.41/98.47 |
| PtrTrans | Crown-16 total | Crown | lint alerts | 6802 |
| PtrTrans | Crown-16 total | PR2 | lint alerts | 4135 |
| PtrTrans | Crown-16 total | PtrTrans | lint alerts | 349 |
| PtrTrans | Crown-16 total | Crown | unsafe usages | 141866 |
| PtrTrans | Crown-16 total | PR2 | unsafe usages | 134185 |
| PtrTrans | Crown-16 total | PtrTrans | unsafe usages | 85 |
| PtrTrans | small projects | FLOURINE | compiled/equivalent percent | 69.9/52.3 |
| PtrTrans | small projects | PtrTrans | compiled/equivalent percent | 98.3/81.6 |
| PtrTrans | large projects | FLOURINE | compiled/equivalent percent | 64.0/14.2 |
| PtrTrans | large projects | PtrTrans | compiled/equivalent percent | 85.9/67.9 |
| PtrTrans | small-10 average | PtrTrans_PS | compiled/equivalent percent | 89.3/59.5 |
| PtrTrans | small-10 average | PtrTrans_PU | compiled/equivalent percent | 84.6/52.9 |
| PtrTrans | small-10 average | PtrTrans_RA | compiled/equivalent percent | 87.9/61.9 |
| PtrTrans | small-10 average | PtrTrans_EC | compiled/equivalent percent | 66.0/50.8 |
| PtrTrans | small-10 average | PtrTrans | compiled/equivalent percent | 100/81.6 |

## Artifact map

- `data/`: normalized measurements and paper reference values.
- `data/paper-reference/`: structured references for omitted source-paper tables.
- `data/paper_surface_inventory.csv`: every source-paper evaluation surface and status.
- `report/comparison.pdf`: human-readable result paper.
- `report/figure.pdf` and `report/figure.svg`: publication figure.
- `metadata/`: provenance, availability, and checksums.
- `reproduction/`: commands and harness snapshot.
