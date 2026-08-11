# CodeWeaver with GPT-5.6 Sol: A Reproducible Evaluation on the ReCodeAgent Benchmark

## Abstract

We evaluate CodeWeaver with GPT-5.6 Sol on the 118-project benchmark released with ReCodeAgent (arXiv:2604.07341). The protocol uses 3 repetitions; repetition 0 is preregistered as the primary comparison and repetitions 0--2 estimate variability. Every CodeWeaver output is evaluated by a fixed post-hoc oracle, while ReCodeAgent and prior systems are replayed from released artifacts. Artifact completeness status: COMPLETE. No best-of-three selection, unavailable artifact substitution, or success-shaped fallback is used.

## Evaluation design

Benchmark: 100 CRUST, 6 Oxidizer, 4 AlphaTrans, and 8 SKEL projects across C-to-Rust, Go-to-Rust, Java-to-Python, and Python-to-JavaScript. CodeWeaver runs use gpt-5.6-sol with maximum reasoning effort, five repair iterations, three parity rounds, and a 5,000-second agent timeout. Released baseline outputs are evaluated by the same normalized collector where artifacts exist. Three projects with nonterminating stress or FIFO-wait commands use the collector's 300-second per-command limit; the repair audit records that no completed normalized row was replaced. The fixed CRUST oracle runs only pristine binary/integration contracts and AST-removes target-authored inline Rust tests from a temporary copy. All 318 affected CodeWeaver cells and 117 available ReCodeAgent artifacts were re-evaluated after this isolation repair; original run outputs remain unchanged. Fixed-denominator rate credit is capped per project, affecting 13 primary-repetition project(s), while raw execution counts remain available. Rows retain 6 exact repository revisions and 6 Copilot CLI patch builds observed during campaign recovery. Model, timeout, and package-version protocol fields are invariant; the revision drift is retained in provenance and treated as a validity threat.

## Artifact completion and claim boundary

Status: COMPLETE
Coverage fraction: 1.0
Unaccounted system cells: 0
System error cells: 0

## Evidence inventory

| system | rep | expected | measured | accounted missing | unaccounted missing | error |
| --- | --- | --- | --- | --- | --- | --- |
| codeweaver | 0 | 118 | 118 | 0 | 0 | 0 |
| codeweaver | 1 | 118 | 118 | 0 | 0 | 0 |
| codeweaver | 2 | 118 | 118 | 0 | 0 | 0 |
| prior | 0 | 118 | 18 | 0 | 0 | 0 |
| recodeagent | 0 | 118 | 117 | 1 | 0 | 0 |

## RQ1: Primary CodeWeaver effectiveness (repetition 0)

| metric | n | value | 95% bootstrap CI | excluded | status |
| --- | --- | --- | --- | --- | --- |
| compilation_success | 118 | 100.0% | [100.0%, 100.0%] | 0 | measured |
| project_pass_all | 118 | 51.7% | [43.2%, 61.0%] | 0 | measured |
| validated_test_micro_pass_rate | 118 | 42.7% | [18.6%, 75.3%] | 0 | measured |
| validated_test_macro_pass_rate | 118 | 63.2% | [55.1%, 71.1%] | 0 | measured |

## RQ1: Three-repetition variability

| metric | n reps | mean | sample SD | 95% t CI | status |
| --- | --- | --- | --- | --- | --- |
| compilation_success | 3 | 100.0% | 0.0% | [100.0%, 100.0%] | measured |
| project_pass_all | 3 | 51.4% | 0.5% | [50.2%, 52.6%] | measured |
| validated_test_micro_pass_rate | 3 | 42.5% | 0.6% | [41.0%, 44.0%] | measured |
| validated_test_macro_pass_rate | 3 | 63.3% | 0.5% | [62.0%, 64.5%] | measured |

## RQ1: Primary paired comparison with ReCodeAgent

| metric | n | CW wins | RCA wins | ties | delta pp | p |
| --- | --- | --- | --- | --- | --- | --- |
| compilation_success | 117 | 37 | 0 | 80 | 31.6 | 0.0000 |
| project_pass_all | 117 | 27 | 15 | 75 | 10.3 | 0.0884 |
| validated_test_project_rate | 117 | 12 | 30 | 75 | -8.7 | 0.0453 |

## RQ2: Test translation and exact paper tables

The package includes project-level official-comparator evidence, heuristic per-test mappings, translated/generated-test summaries, and paper_tables_side_by_side.pdf. Paper and CodeWeaver values retain separate provenance/status fields. Exact-table availability: True.

## RQ3 and RQ4

The Full CodeWeaver protocol is the measured cross-system treatment. No missing CodeWeaver ablation is inferred from the ReCodeAgent paper. Cost, duration, token, premium-request, tool-use, and coverage evidence appear in figure8_cost_tools and the normalized raw rows. Measured cost/correctness frontier status: unavailable.

## CRUST three-system overlap

Status: measured; triples: 99. 

## Threats to validity

CodeWeaver and the released baselines are not model-matched fresh reruns; the comparison is observational at the system level. Released SWE-agent CRUST targets are unavailable, so workbook values are labeled published_reference_non_replayed and never treated as replayed artifacts. Missing and unavailable costs are not zero. The preregistered repetition prevents post-hoc run selection. Three independent evaluations required the documented 300-second command cap after unbounded stress or FIFO-wait tests did not terminate. The fixed CRUST oracle runs only pristine binary/integration contracts and AST-removes target-authored inline Rust tests from a temporary copy. All 318 affected CodeWeaver cells and 117 available ReCodeAgent artifacts were re-evaluated after this isolation repair; original run outputs remain unchanged. Fixed-denominator rate credit is capped per project, affecting 13 primary-repetition project(s), while raw execution counts remain available. Rows retain 6 exact repository revisions and 6 Copilot CLI patch builds observed during campaign recovery. Model, timeout, and package-version protocol fields are invariant; the revision drift is retained in provenance and treated as a validity threat.

## Artifact and reproducibility

The result tree contains normalized CSV/JSON/JSONL data, exact paper tables, figures, statistical tests, LaTeX, PDFs, source snapshot, filtered raw-run archives, infrastructure-failure audits, campaign metadata, and SHA-256 checksums. Official benchmark artifacts are referenced by pinned identifiers and checksums rather than redistributed.
