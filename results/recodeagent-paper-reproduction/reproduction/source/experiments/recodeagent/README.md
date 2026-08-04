# ReCodeAgent Reproduction Harness for CodeWeaver

A self-contained, additive experiment harness that reproduces the protocol of
the ReCodeAgent paper (arXiv:2604.07341, official artifact commit
`3a178a6a99f34c76a37f732c0fd887dad279cf9f`, Zenodo record `21399688`) against
**CodeWeaver**, and independently measures the results. It lives entirely
under `experiments/recodeagent/` (this package) plus its tests under
`tests/experiments/`; the files in this package never modify CodeWeaver
core, existing docs, `pyproject.toml`, or any other file in this
repository. Separately, CodeWeaver core itself now carries exactly one
narrow, default-off, experiment-only instrumentation hook
(`CODEWEAVER_SKIP_STAGES`) that this harness's three stage-skip ablations
opt into via an environment variable so they can preserve CodeWeaver's
real Burr milestone/repair/parity graph -- see
[Integration assumptions and known limitations](#integration-assumptions-and-known-limitations),
item 3, for the exact mechanism and scope.

The harness drives CodeWeaver only through its **public** surface (the
`codeweaver` CLI, `codeweaver.config`/`codeweaver.prompts`/`codeweaver.copilot`
modules, and the `agents/*.agent.md` custom-agent profiles) and never edits,
monkeypatches, or vendors CodeWeaver's own source.

> **Nothing in this harness fabricates results.** Every number is either a
> real observation with recorded provenance, or an explicit
> `missing` / `unavailable` / `not_applicable` / `error` status — never a
> silent zero, a guessed value, or a claimed success. Paper-reported
> reference numbers and numbers this harness actually measures about
> CodeWeaver are kept in visually and structurally separate artifacts
> everywhere (file names, PDF sections, CSV columns) — they are never
> blended into one "results" column.

## Table of contents

- [Scope and non-goals](#scope-and-non-goals)
- [What is being reproduced](#what-is-being-reproduced)
- [Directory layout](#directory-layout)
- [Requirements](#requirements)
- [Quick start: exact end-to-end commands](#quick-start-exact-end-to-end-commands)
- [Stage reference](#stage-reference)
- [RQ -> artifact mapping](#rq---artifact-mapping)
- [Post-hoc independent evaluator](#post-hoc-independent-evaluator)
- [Honesty and provenance guarantees](#honesty-and-provenance-guarantees)
- [Testing this harness](#testing-this-harness)
- [Licensing and data provenance](#licensing-and-data-provenance)
- [Integration assumptions and known limitations](#integration-assumptions-and-known-limitations)
- [Troubleshooting](#troubleshooting)

## Scope and non-goals

This package, by construction:

- **Never installs dependencies.** `pandas`, `matplotlib`, `reportlab`,
  `scipy`, `sentence-transformers`, and `tree-sitter`/`tree-sitter-javascript`
  are all optional and probed defensively via `common.optional_import`; every
  stage still writes complete CSV/JSON output without them (only PDF/figure
  rendering, Qwen embedding similarity, and SKEL's AST-extracted independent
  validated-test evaluation degrade to an explicit `unavailable`
  status/placeholder file).
- **Never launches a real LLM run on its own.** Network access
  (`acquire.py --download`) and real CodeWeaver/Copilot invocations
  (`run.py --variant full`, or any ablation variant) only happen when a human
  operator explicitly runs those commands with those flags.
- **Never vendors third-party source.** The official artifact, prepared
  workspaces, run outputs, and every collected/analyzed artifact live under
  caller-supplied `--artifact-root` / `--workspace-root` / `--runs-root` /
  `--output-root` paths, which are expected to live **outside** this git
  repository (see [Licensing and data provenance](#licensing-and-data-provenance)).
- **Never mutates its inputs.** The original `--artifact-root` is read-only
  from `manifest.py` onward; `prepare.py` only ever writes *copies*; `run.py`
  clones a fresh per-run directory from the prepared template before
  invoking anything.
- **Never leaks ground-truth target implementations.** `prepare.py` actively
  scans generated configs/briefs to guarantee a ground-truth target
  implementation (when the artifact ships one) is never copied into a
  workspace or even mentioned as a string. The one documented exception,
  matching the paper's own protocol, is CRUST's provided Rust
  interface/test *scaffold* (a contract + tests, not a solution).
- **This package's own files never modify CodeWeaver core.** Only files
  under `experiments/recodeagent/` and `tests/experiments/` are part of
  this deliverable. CodeWeaver core (`codeweaver/config.py`,
  `codeweaver/actions.py`) separately carries one narrow, default-off,
  experiment-only instrumentation flag -- `CODEWEAVER_SKIP_STAGES`, an
  environment variable read only when explicitly set (valid values
  `analyze`/`plan`/`validate`; unioned with a config file's own
  `[execution].skip_stages`; an unknown value raises `ValueError`) -- that
  lets the three named stage-skip ablations (`noanalyzer`/`noplanning`/
  `novalidator`) deterministically omit exactly the Analyzer, Planner, or
  Validator role while every other part of the real Burr
  milestone/repair/parity graph, and all of CodeWeaver's ordinary
  (non-experiment) behavior, is fully preserved. See "Integration
  assumptions" item 3 below for the exact mechanism.
## What is being reproduced

| | |
|---|---|
| Paper | arXiv:2604.07341 ("ReCodeAgent") |
| Official artifact | Zenodo record `21399688`, commit `3a178a6a99f34c76a37f732c0fd887dad279cf9f` |
| Artifact files | `implementation.zip` (MD5 `a2151028151e0852ce4db060a22ac76a`), `results.xlsx` (MD5 `a404779f2dcd7ac44d43bf72f4e88b98`), `results.zip` (MD5 `5df332d2a1477ec30f719dd7d0ff2470`) |
| Artifact URLs | `https://zenodo.org/api/records/21399688/files/<filename>/content` |
| Paper and measured-run protocol | Claude Sonnet 4.5 (`claude-sonnet-4.5`), 5,000 sec/agent timeout |
| Benchmark size | 118 projects total |

Dataset breakdown (`common.DATASET_SPECS`, validated by `manifest.py`):

| Tool key | Label | Expected count | Source -> Target |
|---|---|---|---|
| `crust` | CRUST | 100 | C -> Rust |
| `oxidizer` | Oxidizer | 6 | Go -> Rust |
| `alphatrans` | AlphaTrans | 4 | Java -> Python |
| `skel` | SKEL | 8 | Python -> JavaScript |
| | **Total** | **118** | |

Paper-reported reference totals across all 118 projects (kept in a separate
artifact from anything measured; see `common.PAPER_REFERENCE_TOTALS`):
230,000 LoC, 2,107 validated tests, 1,484 translated tests (CRUST excluded
per the paper's own protocol), 4,583 functions. All four were independently
cross-checked read-only against the real official `results.xlsx` in a later
integration pass (never vendored into this repo): the precise LoC sum is
233,057 (230K is the paper's own rounded headline, kept alongside the
precise figure as `total_loc_precise`); validated/translated-test and
functions-exercised counts are exact matches to that spreadsheet's own
"total" row -- see `common.py`'s `PAPER_REFERENCE_TOTALS` comment for the
exact sheet/column citations. The 2,107 validated-test total's own per-tool
breakdown (`common.PAPER_REFERENCE_VALIDATED_TESTS_BY_TOOL`, surfaced as
`validated_tests_crust`/`_oxidizer`/`_alphatrans`/`_skel` columns on
`table1_paper_reference.csv`'s single row) is 623 CRUST + 229 Oxidizer +
1,181 AlphaTrans + 74 SKEL -- the non-CRUST three sum to the same 1,484
"translated_tests" total above, kept purely as paper-reference context
alongside this harness's own per-tool MEASURED `validated_tests_*` fields
(never blended, never asserted as a target those measured counts must
reproduce).

RQ3 ablation variants (`common.RUN_VARIANTS`): `full`, `noanalyzer`,
`noplanning`, `novalidator`, `baseagent-condensed`, `baseagent-concat`.

## Directory layout

```
experiments/recodeagent/
  __init__.py          package docstring + pipeline overview
  __main__.py           `python -m experiments.recodeagent` entry point
  cli.py                 unified <stage> dispatcher (thin; no argument duplication)
  common.py              shared stdlib-only infrastructure (see below)
  experiment.toml         pinned protocol: paper facts, artifact hashes, dataset adapters
  acquire.py              verify (+ optionally download/extract) the official artifact
  manifest.py             discover the 118 projects -> manifest.json/csv
  prepare.py              build isolated, leakage-safe per-project workspaces
  run.py                  execute the (variant x project x repetition) matrix
  collect.py              independently evaluate run.py's outputs -> raw_runs
  merge_collections.py    strictly combine disjoint collect.py shards
  test_compare.py         RQ2: source<->target developer-test comparison
  merge_paper_results.py  strictly combine disjoint paper/generated-test shards
  analyze.py               RQ1-RQ4 tables/figures from measured data only
  render.py               generic Markdown/PDF narrative-report primitives
  report.py               final reproducibility_report.{md,pdf} + provenance JSON
  package_results.py      final Git-ready data/PDF/provenance/raw-archive repository
  schemas/
    manifest.schema.json
    manifest_row.schema.json
    run_state.schema.json
    raw_run.schema.json
    test_comparison.schema.json
  conftest.py             pytest collection guard (excludes test_compare.py -- a
                          harness MODULE, not a test suite -- from discovery)

tests/experiments/
  conftest.py              adds repo root to sys.path for `import experiments...`
  test_common.py, test_acquire.py, test_manifest.py, test_prepare.py,
  test_run.py, test_collect.py, test_merge_collections.py,
  test_merge_paper_results.py,
  test_test_compare.py, test_analyze.py,
  test_render.py, test_report.py, test_package_results.py, test_cli.py
tests/test_copilot.py       core Copilot timeout/process-group regression
```

`common.py` provides, and every other module builds on:

- `Measurement` / `Status` (`measured` / `missing` / `unavailable` /
  `not_applicable` / `error`) -- the value type that keeps "we didn't measure
  this" distinct from "zero" or "success" everywhere in the harness.
- Protocol constants pinned to the paper (`DATASET_SPECS`, `RUN_VARIANTS`,
  `PAPER_REFERENCE_TOTALS`, `OFFICIAL_ARTIFACT_FILES`, ...).
- Hashing (`file_md5`, `file_sha256`) and atomic file writes (crash-safe --
  writes go to a temp file + atomic rename, so a killed process never leaves
  a torn/partial artifact).
- `run_argv` -- a safe subprocess runner: **always** an argument array, never
  a shell string; timeouts are first-class and always recorded.
- `collect_provenance()` -- git SHA, OS/hostname, Python version, CodeWeaver
  package version, best-effort per-language toolchain versions, and the
  Copilot CLI version.
- A tiny dependency-free JSON-schema-ish validator for `schemas/*.json`.
- `optional_import()` -- probes any module name (never raises, never fakes
  availability); used for `pandas`/`matplotlib`/`reportlab`/`scipy`/
  `sentence-transformers` (also summarized, unused elsewhere in this
  harness, by `optional_dependency_report()`) as well as directly for
  `scipy.stats` and `tree_sitter`/`tree_sitter_javascript` (SKEL's AST
  extraction, see [Post-hoc independent evaluator](#post-hoc-independent-evaluator)),
  neither of which is registered in that summary list.

## Requirements

- **Python 3.11+** (the harness uses stdlib `tomllib`, available since 3.11;
  all harness code is otherwise ordinary, portable, typed-where-practical
  Python with no compiled extensions of its own).
- **Target execution platform: Linux/WSL.** The official artifact is
  documented to contain member filenames with `*` in them, which are illegal
  in native Windows paths. `acquire.py --extract` **refuses to run on native
  Windows** (WSL correctly reports as Linux and is unaffected) and prints
  exactly which member(s) are unsafe, rather than silently mangling names.
  `manifest.py`, `prepare.py`, `analyze.py`, `report.py`, and the test suite
  are pure Python and portable to any OS; actually running `run.py`'s `full`
  variant or any of `collect.py`'s configured build/test/coverage commands
  additionally requires the real per-language toolchains (`cargo`/`rustc`,
  `python`, `node`/`npm`, a JDK) to be installed, which on this project is
  provisioned separately, under WSL.
- **Optional** for richer output, never required for correctness:
  `pandas`, `matplotlib`, `reportlab`, `scipy`, `sentence-transformers`,
  `openpyxl`, and `tree-sitter`/`tree-sitter-javascript`. Every stage's
  CSV/JSON output is complete without them; only PDF/figure rendering
  (falls back to a `*.pdf.unavailable.txt` sibling), Qwen embedding
  similarity (falls back to an explicit `unavailable` status), reading
  CRUST's paper-aligned expected-test-count directly from `results.xlsx`
  via `--crust-paper-expected-tests` (falls back to an explicit
  `unavailable` status/reason -- a `.json`/`.csv` reference-inventory file
  remains available without `openpyxl` at all), and SKEL's AST-extracted
  independent validated-test evaluation (falls back to an explicit
  `unavailable` status with a precise reason -- see
  [Post-hoc independent evaluator](#post-hoc-independent-evaluator))
  degrade gracefully.
- **GitHub Copilot CLI** (plus a configured model) is required only to
  execute a real `full`-variant or ablation run; it is not needed to run
  `manifest.py`, `prepare.py`, `analyze.py`, `report.py`, or the test suite.

## Quick start: exact end-to-end commands

Every stage is runnable either through the unified dispatcher

```bash
python -m experiments.recodeagent <stage> [stage-specific arguments...]
python -m experiments.recodeagent --help                 # lists all stages
python -m experiments.recodeagent <stage> --help          # that stage's own arguments
```

or by invoking a stage module directly (identical behavior; `cli.py` only
forwards argv, it defines no arguments of its own):

```bash
python -m experiments.recodeagent.<module> [arguments...]
```

The examples below use the dispatcher form and Linux/WSL-style paths (adjust
as needed). Run from the repository root, or set `PYTHONPATH` to it.

```bash
# 1) Verify (and, only when explicitly asked, download + extract) the
#    official artifact. Never runs on native Windows -- use WSL.
python -m experiments.recodeagent acquire \
  --artifact-root /data/recodeagent/artifact \
  --download --extract \
  --out /data/recodeagent/artifact/acquire_report.json

# 2) Deterministically discover the 118 projects. If dataset directory names
#    inside the real artifact differ from experiment.toml's guessed
#    `dir_candidates`, run with --probe first and adjust experiment.toml
#    (a config edit, never a code change).
python -m experiments.recodeagent manifest --probe \
  --artifact-root /data/recodeagent/artifact
python -m experiments.recodeagent manifest \
  --artifact-root /data/recodeagent/artifact \
  --output-root /data/recodeagent/manifest

# 3) Build isolated, leakage-safe per-project workspaces (codeweaver.toml +
#    brief.md + source/ + oracle/ [+ scaffold/ for CRUST]).
python -m experiments.recodeagent prepare \
  --manifest /data/recodeagent/manifest/manifest.json \
  --artifact-root /data/recodeagent/artifact \
  --workspace-root /data/recodeagent/workspaces

# 4) Execute the reproduction matrix. Repeat once per variant (or pass
#    --variant all). `full`, and the three stage-skip ablations
#    (noanalyzer/noplanning/novalidator), all invoke the REAL CodeWeaver CLI
#    (`python -m codeweaver run --config <config> --app-id <id>`) running
#    its real Burr milestone/repair/parity graph end to end; the three
#    ablations additionally set CODEWEAVER_SKIP_STAGES=analyze|plan|validate
#    so CodeWeaver core deterministically omits exactly that one role's real
#    work while every other stage/loop runs unchanged.
#    baseagent-condensed/baseagent-concat remain single-shot, harness-
#    authored one-agent prompts using the same model/budget (see
#    "Integration assumptions" below).
python -m experiments.recodeagent run \
  --manifest /data/recodeagent/manifest/manifest.json \
  --workspace-root /data/recodeagent/workspaces \
  --runs-root /data/recodeagent/runs \
  --variant full --jobs 4 \
  --out /data/recodeagent/runs/run_summary_full.json
python -m experiments.recodeagent run \
  --manifest /data/recodeagent/manifest/manifest.json \
  --workspace-root /data/recodeagent/workspaces \
  --runs-root /data/recodeagent/runs \
  --variant noanalyzer,noplanning,novalidator,baseagent-condensed,baseagent-concat \
  --jobs 4

# 5) Independently evaluate every run's outputs (never trusts an agent's own
#    self-report -- runs the project's configured build/test commands itself).
#    --reference-results-root (optional) additionally points at the official
#    RESULTS artifact's extracted tree (e.g. .../recodeagent-results/results)
#    so collect.py can ALSO run the paper's own independently validated
#    developer-test oracle (CRUST/Oxidizer/AlphaTrans always; SKEL when its
#    test_name_mapping.csv-listed tests are AST-extractable from
#    javascript/source.js) AND the reusable GENERATED function/test-harnesses
#    (Oxidizer's *generated*.rs, AlphaTrans's agent_test/, and SKEL's
#    javascript/*generated*.js) in a
#    temporary, post-hoc evaluation copy -- never inside a run's own
#    workspace, never before the run has finished.
#    Omit it and validated_tests_*/function_validation_*/
#    function_harness_tests_* are all reported Status.UNAVAILABLE, never
#    silently filled in from translated_tests_* (see "Post-hoc independent
#    evaluator").
#    --crust-paper-expected-tests (optional) additionally points at the
#    paper's own AUTHORITATIVE per-project CRUST expected-test-count (the
#    official results.xlsx's own "sweagent crust - tool test" sheet, or an
#    explicit JSON/CSV reference-inventory file) -- see "CRUST's
#    native-vs-paper-aligned expected-test-count" below. Omit it and CRUST's
#    validated_tests_expected falls back to a NATIVE, best-effort static
#    #[test]-attribute count (validated_tests_expected_native), never
#    silently presented as the paper's own figure.
python -m experiments.recodeagent collect \
  --manifest /data/recodeagent/manifest/manifest.json \
  --runs-root /data/recodeagent/runs \
  --output-root /data/recodeagent/results \
  --jobs 8 \
  --reference-results-root /data/recodeagent-results/results \
  --crust-paper-expected-tests /data/recodeagent-cache/results.xlsx

# 6) RQ2: map every source developer test to a translated target test.
python -m experiments.recodeagent test-compare \
  --manifest /data/recodeagent/manifest/manifest.json \
  --runs-root /data/recodeagent/runs \
  --output-root /data/recodeagent/results
python -m experiments.recodeagent.paper_test_compare \
  --manifest /data/recodeagent/manifest/manifest.json \
  --runs-root /data/recodeagent/runs \
  --output-root /data/recodeagent/results \
  --reference-results-root /data/recodeagent-results/results \
  --reference-implementation-root /data/recodeagent-official/ReCodeAgent \
  --variant full --embeddings

# 7) RQ1-RQ4 tables/figures, computed only from what steps 5-6 actually wrote.
#    `--variant` is the SPAN considered by figure7_ablation/figure8_cost_tools
#    and completeness (they intentionally compare all variants side by side);
#    `--primary-variant`/`--primary-repetition` select the SINGLE (variant,
#    repetition) that table1_effectiveness/table2_test_translation/
#    table_generated_tests/table_function_validation report -- shown here
#    explicitly (they also default to full/0) so the selection is never
#    ambiguous when --runs-root holds multiple variants and repetitions.
python -m experiments.recodeagent analyze \
  --manifest /data/recodeagent/manifest/manifest.json \
  --raw-runs /data/recodeagent/results/raw_runs.jsonl \
  --test-comparisons /data/recodeagent/results/test_comparisons.jsonl \
  --paper-test-projects /data/recodeagent/results/paper_test_projects.csv \
  --generated-test-projects /data/recodeagent/results/generated_test_projects.csv \
  --output-root /data/recodeagent/results/analysis \
  --variant all --primary-variant full --primary-repetition 0

# 8) Final reproducibility report -- always written, even with zero
#    measured data ("nothing has been run yet" is itself a valid report).
python -m experiments.recodeagent report \
  --manifest /data/recodeagent/manifest/manifest.json \
  --raw-runs /data/recodeagent/results/raw_runs.jsonl \
  --failures /data/recodeagent/results/failures.csv \
  --test-comparisons /data/recodeagent/results/test_comparisons.jsonl \
  --comparison-failures /data/recodeagent/results/test_comparison_failures.csv \
  --analysis-provenance /data/recodeagent/results/analysis/analysis_provenance.json \
  --output-root /data/recodeagent/results/report

# 9) Refuse incomplete results, then assemble the final local results
#    repository. Raw archives omit duplicated benchmark inputs and build
#    caches while retaining translated source, logs, state, and reports.
python -m experiments.recodeagent package \
  --manifest /data/recodeagent/manifest/manifest.json \
  --collected-root /data/recodeagent/results \
  --paper-test-root /data/recodeagent/results \
  --analysis-root /data/recodeagent/results/analysis \
  --report-root /data/recodeagent/results/report \
  --runs-root /data/recodeagent/runs \
  --infrastructure-failures-root /data/recodeagent/runs-infrastructure-failures \
  --output-root /data/codeweaver-recodeagent-results \
  --require-complete
```

`--require-complete` on `report.py` makes the process exit non-zero when the
completion verdict is `INCOMPLETE` (for CI-style gating) -- the report's
*wording* is always honest regardless of this flag.

## Stage reference

| Stage | Required inputs | Key outputs (under `--output-root`/`--workspace-root`/`--runs-root`) |
|---|---|---|
| `acquire` | `--artifact-root` | verified/extracted artifact files in place; optional JSON verification report |
| `manifest` | `--artifact-root` | `manifest.json`, `manifest.csv` |
| `prepare` | `--manifest`, `--artifact-root`, `--workspace-root` | `<workspace_root>/<project_id>/{codeweaver.toml,brief.md,source/,oracle/[,scaffold/]}` |
| `run` | `--manifest`, `--workspace-root`, `--runs-root` | `<runs_root>/<variant>/<project_id>/rep<N>/{recodeagent_run_state.json,recodeagent_calls.jsonl,cli.stdout.log,pipeline/...}` |
| `collect` | `--manifest`, `--runs-root`, `--output-root` (`--reference-results-root`, `--crust-paper-expected-tests` optional) | `raw_runs.jsonl`, `raw_runs.csv`, `failures.csv` |
| `merge-collections` | repeated `--input-root`, `--manifest`, `--output-root` | strictly deduplicated `raw_runs.{jsonl,csv}`, `failures.csv`, `collection_merge_summary.json` |
| `test-compare` | `--manifest`, `--runs-root`, `--output-root` | `test_comparisons.jsonl`, `test_comparisons.csv`, `test_comparison_failures.csv`, `test_comparison_summary.json` |
| `paper_test_compare` | official implementation/results + full run matrix | `paper_test_projects.csv`, `generated_test_projects.{csv,jsonl}` (isolated generated-test execution plus developer-only/developer+generated coverage), and failure/summary files |
| `merge-paper` | repeated disjoint paper-test output roots, manifest | merged paper/generated project rows and project-level evidence with strict completeness checks |
| `analyze` | `--manifest`, `--raw-runs`, `--output-root` plus paper/generated project CSVs for final output | `table1_effectiveness.{csv,pdf}`, `table1_paper_reference.{csv,pdf}`, `table2_test_translation.{csv,pdf}`, `figure7_ablation.{csv,pdf}`, `figure8_cost_tools.{csv,pdf}`, `table_generated_tests.{csv,pdf}`, `table_function_validation.{csv,pdf}`, `analysis_provenance.json` |
| `report` | `--manifest`, `--output-root` (everything else optional) | `reproducibility_report.md`, `reproducibility_report.pdf`, `reproducibility_report_data.json`, `manifest_checksum_provenance.json` |
| `package` | complete report plus manifest, collected/paper-test/analysis roots, and runs root | Git-ready result tree containing all normalized data/PDFs, source/provenance/checksums, and split filtered raw-run archives |

`run` treats `completed`, `failed`, and `timeout` states as terminal and
preserves them by default. This prevents a broad launcher restart from
silently replacing a genuine model failure or protocol timeout.
`--resume-running` is only for a cell confirmed orphaned after its launcher
died; `--retry-terminal` explicitly retries a failed/timeout cell while
retaining resumable Burr state; `--force` rematerializes and reruns any cell.
The reproduction workflow archives and removes an audited infrastructure
failure before its clean rerun instead of using these options on a genuine
experiment outcome.

`merge-collections` rejects conflicting duplicate raw rows by default.
When a later focused shard was produced solely to repair an audited
evaluator defect, repeat
`--replace-key VARIANT:PROJECT_ID:REPETITION` for each intended replacement.
Only explicitly named duplicated keys may differ; the later input wins and
both the allowlist and the rows actually changed are recorded in
`collection_merge_summary.json`. This is not a mechanism for replacing a
genuine model outcome.

Every stage accepts `--config <experiment.toml>` to override the bundled
default, and `run`/`collect`/`test-compare`/`analyze`/`report` accept
`--variant`/`--project`/`--repetitions` filters (see each stage's own
`--help` for the exact set, printed directly from that stage's real
`argparse` parser -- never duplicated or hand-copied here). `--project` on
`analyze` restricts EVERY output (completeness, table1/2, figure7/8,
supporting tables) to that project subset.

`analyze`'s `--variant` and `--primary-variant`/`--primary-repetition` are
deliberately two different knobs, never conflated: `--variant` (default
`all`) is the SPAN of variants shown side by side in `figure7_ablation`/
`figure8_cost_tools`/completeness, while `--primary-variant`/
`--primary-repetition` (default `full`/`0`) select the SINGLE (variant,
repetition) that `table1_effectiveness`/`table2_test_translation`/
`table_generated_tests`/`table_function_validation` report -- these four
artifacts never silently blend rows from other variants or repetitions.
Pass `--primary-repetition all` to instead aggregate across every repetition
of `--primary-variant` (explicit opt-in only, never the default).

## RQ -> artifact mapping

| RQ | Paper concept | Artifact(s) |
|---|---|---|
| RQ1 | Syntactic/compilation success; developer test executed/pass/fail + TPR; translated/generated tests; coverage before/after; per-function/milestone validation | `table1_effectiveness.{csv,pdf}` (measured) vs. `table1_paper_reference.{csv,pdf}` (paper's own reported totals -- always a separate file/section). `tpr`/per-function validation are sourced from the **independently validated** oracle. `coverage_before`/`coverage_after` are sourced from `generated_test_projects` and mean independent developer tests before/after adding only CodeWeaver-authored generated tests. The official ReCodeAgent generated harness remains separately labeled as `standardized_coverage_before`/`standardized_coverage_after`; it is never substituted for CodeWeaver's result. |
| RQ2 | Test translation rate, assertion-count match, `assertEqual` equivalence, assertion-type match, Qwen cosine similarity, LoC/method-invocation counts | `table2_test_translation.{csv,pdf}` (delegates to `test_compare.py`'s own `summarize_comparisons`), `table_generated_tests.{csv,pdf}` |
| RQ3 | Ablation variants' TPR + NC/TEC/SEC/LC/ALL trajectory metrics | `figure7_ablation.{csv,pdf}` (paired delta vs. `full` via Wilcoxon-or-bootstrap). Its `tpr` uses the same independently validated, passed/expected `validated_tests_pass_rate` as Table 1 for every variant; without the reference oracle it remains explicitly missing. |
| RQ4 | Tokens, premium requests/credits, elapsed time, agent turns, tool invocations, model/CLI/git/OS provenance | `figure8_cost_tools.{csv,pdf}` (`dollar_cost_usd` stays `not_applicable` unless `--pricing-usd-per-premium-request` is explicitly supplied -- GitHub Copilot CLI has no built-in dollar-cost API) |

## Post-hoc independent evaluator

`collect.py`'s ordinary `dev_tests_*` measurement (also exposed as
`translated_tests_*`, an unambiguous alias -- see below) runs each project's
own configured `unit_test_cmd` against whatever CodeWeaver itself produced
and translated into the target tree. That is **CodeWeaver's own
self-reported/self-graded translated test suite**, not the paper's
methodology: the paper's "TPR" (test pass rate) and per-function validation
numbers are measured against an **independently validated developer-test
oracle** that CodeWeaver never sees or edits. Conflating the two would let a
translation that only passes because it also rewrote its own tests look
identical, in this harness's own tables, to one validated against unmodified
ground truth. This section documents how that independent oracle is
obtained and evaluated, and the new fields it produces.

### `--reference-results-root`

An optional `collect.py`/`python -m experiments.recodeagent collect` flag
pointing at the **official RESULTS artifact's extracted tree** (the 42 GB
`results.zip`, not `implementation.zip`), whose relevant shape is:

```
<reference-results-root>/recodeagent_translations/data/tool_projects/<tool>/<project>/
```

(`<tool>` is one of `crust`/`oxidizer`/`alphatrans`/`skel`, matched case-
insensitively, same as the project id.) When omitted, every
`validated_tests_*`/`function_validation_*` field this section describes is
reported `Status.UNAVAILABLE` with an explicit reason -- **never** silently
computed from `translated_tests_*` instead. This tree is third-party
official-artifact data: exactly like `--artifact-root`'s `implementation.zip`
tree, it is never vendored into this repository, and this harness only ever
*reads* files from it into a **temporary** evaluation copy (see below) --
never into a run's own workspace, and never before that run's LLM
invocation has already reached a terminal state (`completed`/`failed`/
`timeout`).

### Per-tool independent-oracle adapters

| Tool | Independent oracle source | How it's evaluated |
|---|---|---|
| **CRUST** | The pristine `run_dir/scaffold/` crate CodeWeaver was given as its own immutable starting point (the paper's provided Rust interface + test contract) | `Cargo.toml`/`Cargo.lock`/`src/bin/**`/`tests/**` are restored from the pristine scaffold over a **temporary copy** of the run's produced target before running `cargo test` there -- the run's own (possibly agent-edited) copies of those contract paths are never trusted. Any detected "binary assertion harness" (a `src/bin/*.rs` file with **zero** `#[test]` attributes, e.g. the real `libfor` project's `src/bin/test.rs` -- a plain `fn main()` whose own process exit code IS the verdict, never discovered/run by `cargo test` at all) is additionally executed via `cargo run --bin <name>` and merged into the same executed/passed/failed counts -- see [CRUST's native-vs-paper-aligned expected-test-count](#crusts-native-vs-paper-aligned-expected-test-count) below. `oracle_integrity` separately hash-compares the run's own target copies of those SAME paths against the pristine scaffold (`pristine`/`mutated`/`not_copied`) so a mutated contract is visible without ever invalidating the pristine evaluation itself. Per-function validation is `not_applicable` -- the paper validates CRUST at whole-crate granularity only. |
| **Oxidizer** | `<reference-results-root>/.../oxidizer/<project>/rust/tests/*.rs` | Files matching `*_test.rs` (case-insensitive, excluding any name containing `generated`) are the developer-test oracle; other plain `.rs` files (same exclusion) are per-function validation harnesses; `*generated*.rs` files form the separate standardized generated-test harness. A plain file imported by a driver through `mod fixture;` is instead staged as fixture support and never counted or run as its own harness. Each integration binary is copied and run independently in a **temporary copy** of the run's target, preserving CodeWeaver's own `Cargo.toml`/`src/` untouched. A genuine public-API mismatch is a visible compile failure, except for purely idiomatic identifier naming (for example `NewLuhn` to `new_luhn`), which is conservatively derived from the target or rewritten from the run's Planner map. Reference `rust/src`/`Cargo.*`/any non-test file is never copied. |
| **AlphaTrans** | `<reference-results-root>/.../alphatrans/<project>/verified_test/` | The whole `verified_test/` directory (it may contain `conftest.py`/`__init__.py`/subdirectories, so it is copied as a tree, not a flat file list) replaces (never merges with) whatever `verified_test/` the run's own target copy already has, in a **temporary copy** of the target, then `python -m pytest -q verified_test` runs there. The reference's own Python implementation is never copied. This is the paper's **independent developer-test oracle** for AlphaTrans; see the next subsection for its separate, reusable `agent_test/` GENERATED function-harness adapter (`function_harness_tests_*`), which is never conflated with this one. |
| **SKEL** | `<reference-results-root>/.../skel/<project>/test_name_mapping.csv` + the same project's `javascript/source.js`, which embeds the reference implementation and translated tests together | **Every CSV row** is part of the paper's 74-test validated inventory; the `verified test` column records a prior system outcome and is not a selector. Each listed JavaScript test is AST-extracted only when all free identifiers resolve to builtins, safe Node imports, target exports, pinned inert fixtures, or provably pure literal data. Private executable reference helpers are never copied. The `.mjs` harness dynamically imports CodeWeaver's own `index.js`, works with CommonJS and ESM targets, and turns target-load failures into honest per-test failures. Missing dependencies/artifacts or a wholly blocked inventory is `Status.UNAVAILABLE`, never a fabricated zero. |

Every adapter reuses the same `evaluate_build`/`evaluate_tests` execution
and parsing path as the ordinary translated-test measurement (including a
new `pytest` output-format parser registered for AlphaTrans's independent
check, distinct from the `python_unittest` parser used for its own
`unit_test_cmd`) -- nothing about *how* a test command is run or parsed is
reimplemented, only *which* directory it is run against and *which* files
were placed there.

### Reusable GENERATED function/test-harness adapters (`function_harness_tests_*`)

The official RESULTS artifact ships reusable GENERATED target-language test
harnesses for Oxidizer, AlphaTrans, and SKEL. They are distinct from
Oxidizer's plain per-function harness and from every developer-test oracle.
To avoid dropping or mislabeling this evidence, it is reported under a
**separate, structurally distinct** field family, `function_harness_tests_*`
("standardized GENERATED function/test-harness EXECUTION evidence").
`function_validation_*` stays `Status.UNAVAILABLE` for AlphaTrans and SKEL,
and `function_harness_tests_*` is `Status.NOT_APPLICABLE` only for CRUST.

| Tool | Reference source | Selection rule | Execution |
|---|---|---|---|
| **Oxidizer** | `<reference-results-root>/.../oxidizer/<project>/rust/tests/` | Every `*.rs` file containing `generated` in its basename. | Each integration binary is staged and run independently with `cargo test --test <stem>`, so one uncompilable file does not hide the measurable files. |
| **AlphaTrans** | `<reference-results-root>/.../alphatrans/<project>/agent_test/` (nested `agent_test/python/...` + sibling `resources/` for `commons-cli`/`commons-csv`/`commons-validator`; flat `agent_test/...` for `commons-fileupload`) | The pinned paper inventory of generated `.py` files, plus required `__init__.py`/`conftest.py` and resource fixtures. Later `additional` files and plain translated `XxxTest.py` files are excluded. | Each pinned generated file runs independently under pytest, preserving partial execution when another file cannot collect. |
| **SKEL** | `<reference-results-root>/.../skel/<project>/javascript/` | Every `*.js` file whose basename contains `generated` (case-insensitive -- naming varies per project, e.g. `SKELTest_generated.js`, `SkelHeadTest_generated.js`, a project-specific `*FunctionsTest_generated.js`). The reference's own `source.js` and any internal-only helper (e.g. some projects' `tracer_skip.js`) are never selected. | Selected files are copied flat into a temporary copy of the run's own target (SKEL's `javascript/` layout is itself flat); CodeWeaver's own entry file (`index.js`) is additionally **copied** (never renamed/removed) to `source.js` so ordinary `require('./source.js')` calls resolve against CodeWeaver. Four official scripts instead inline reference implementations (`colorsys` utility/`_v`, `html` utilities, and `toml`'s `TomlTz` factory); those exact top-level declarations are removed with tree-sitter and rebound to CodeWeaver's target before execution. The untouched reference script is never run in those cases. `node <file>.js` is invoked once per selected file. When every script exits zero, `function_harness_tests_total/passed/failed` uses the paper's exact **306-case** SKEL inventory, not a file count. If any early-aborting script fails, case-level counts are `unavailable` rather than fabricated from file exits. |

`function_harness_tests_*` never assumes a reliable one-to-one per-function
mapping, so it must not be read as "N of M functions validated". Its fixed
`expected` inventory is exactly **1,704 non-CRUST cases** (Oxidizer 609,
AlphaTrans 789, SKEL 306); `not_executed` and paper-relative pass rate keep
blocked collection in the denominator. The paper's own per-function
"Exercised" denominator for the same three non-CRUST tools (Oxidizer +
AlphaTrans + SKEL) is **1,397** (independently re-derived in this repro from
the official `results.xlsx` cache: the sum of its "Exercised" column across
exactly those tools' rows, matching `PAPER_REFERENCE_TOTALS["functions"]`
(4,583) minus CRUST's own four-row contribution of 3,186) -- surfaced as
`table1_paper_reference.csv`'s `function_validation_denominator_non_crust`
column, in the separate `paper_reference` row/file, purely for context. It
is never used as a divisor for, or otherwise blended into, this harness's
own measured `function_harness_tests_*`/`function_validation_*` counts,
which measure generated tests/harnesses rather than the paper's own
per-function coverage instrumentation.

### CodeWeaver-authored generated tests and paper-equivalent coverage

`paper_test_compare.py` first maps the fixed source developer-test inventory
one-to-one onto each CodeWeaver target. Executable target tests left unmatched
are CodeWeaver-authored generated tests; CRUST instead uses Rust tests and
binaries absent from its immutable scaffold. The evaluator executes only
those classified tests and writes expected/executed/passed/failed/
not-executed plus `coverage_before` and `coverage_after` to
`generated_test_projects.{csv,jsonl}`.

Coverage uses the same independent developer oracle described above.
`coverage_before` runs that oracle alone; `coverage_after` unions it with only
the classified CodeWeaver-authored tests. Rust uses per-target
`cargo-tarpaulin` line unions and exact test selectors, Python accumulates
Coverage.py data from exact pytest node IDs, and JavaScript uses c8 over the
complete target JavaScript tree. The SKEL adapter suppresses evaluator-copy
top-level `test*()` runner calls and excludes test-function bodies from the
production-line denominator, preventing CodeWeaver's translated tests from
silently contaminating the independent baseline. All instrumentation occurs
in temporary copies.

`collect.py` separately runs the official ReCodeAgent generated harness for
cross-system diagnostics. Those numbers are named
`standardized_coverage_before`/`standardized_coverage_after`; non-CRUST raw
`coverage_after` remains explicitly unavailable until generated-test
classification runs. `analyze.py` uses the authoritative generated-project
coverage pair for Table 1 and preserves the standardized pair in separate
columns.

### Oxidizer's idiomatic-identifier-rewrite (compile failure vs. behavioral failure)

**Concrete, verified problem.** The official `oxidizer__checkdigit`
project's own validated Rust oracle test calls `NewLuhn()` (the
source-language spelling), while CodeWeaver's real Analyzer/Planner may
(correctly, per idiomatic Rust convention) expose the equivalent symbol as
`new_luhn` -- the Planner's own `plan.json` records this decision in its
`name_mapping` field. Compiling the pristine oracle test **verbatim**
against such a target then fails with an ordinary rustc "cannot find
function `NewLuhn` in this scope" error: a **real** compile failure, caused
**solely** by an idiomatic renaming choice, not a behavioral bug in the
translation. Naively reporting this as "0 passed, N failed" would silently
misrepresent an untested suite as a behaviorally-broken one.

Two independent, layered mitigations address this (neither depends on the
other, and both are scoped to Oxidizer's adapter alone -- see "Why
Oxidizer-only" below):

1. **Ideal: best-effort identifier rewrite.** `read_name_mapping(run_dir)`
   reads the run's own real `pipeline/plan.json`'s `name_mapping` field --
   the Planner's own structured, one-to-one source-symbol -> target-symbol
   map (confirmed authoritative by reading `codeweaver/prompts.py`'s `PLAN`
   template and `codeweaver/actions.py`'s `plan()` action; a `name_map` key
   is also accepted as a defensive fallback alias for an older,
   harness-internal placeholder spelling, tried only after `name_mapping`).
   Before a reference oracle/harness file is staged into the temporary
   evaluation copy, `rewrite_identifiers_with_name_mapping` rewrites every
   whole-token occurrence of a mapped SOURCE identifier found in a genuine
   **code** position to its recorded TARGET spelling -- `NewLuhn()` becomes
   `new_luhn()` -- so the oracle's own test **logic/assertions** still run,
   unmodified, against CodeWeaver's actual (idiomatically-renamed) public
   API. This never touches the reference file **on disk**; only the
   in-memory text staged into the ephemeral `tempfile.TemporaryDirectory()`
   copy is ever rewritten, and a file with zero eligible substitutions (or
   an empty/absent `name_mapping`) is still copied byte-for-byte via
   `shutil.copy2`, exactly as before this feature existed -- a strict,
   provable no-op for every run without this specific naming pattern.

   Rewriting is deliberately conservative: an exact source-string match
   always wins; a secondary, case/underscore-insensitive match (catching
   e.g. `NEW_LUHN`) is offered only for source keys whose normalized form
   isn't ambiguously shared (with a *different* recorded target) by some
   other exact key -- an ambiguous collision is dropped entirely rather
   than guessed. A hand-rolled, dependency-free Rust source/comment/
   literal-lexer (`rust_source_code_mask`; no new `tree-sitter-rust`
   dependency) ensures identifier-shaped substrings inside string/byte/raw
   string literals, char literals, line/block comments, **and Rust
   lifetimes** (`'a`, `'static`, `'de`, ...) are never rewritten -- e.g. a
   test asserting on a literal name string
   (`assert_eq!(names(), vec!["NewLuhn"])`) or a comment mentioning the old
   name survives untouched, and a `name_mapping` entry that happens to
   equal a common lifetime name (e.g. a single-letter symbol) can never
   corrupt every `'a` in the file. When at least one substitution is
   applied, the resulting Measurement's `reason` transparently records
   which source identifiers were rewritten, so a passing (or failing) run
   is never silently "helped" without a visible trace.

   Rust import syntax is adapted separately from call sites. Associated
   function mappings such as `NewHistogram -> NumericHistogram::new` import
   the owning type and rewrite the call, while required public traits are
   imported when rewritten methods are trait-provided. Out-of-line oracle
   fixture modules and their declared symbols are protected from target-API
   rewriting. Planner values that are prose rather than valid Rust
   identifiers/paths are ignored. This prevents both invalid imports and the
   concrete `gohistogram` false negative where local `mod test_data;` was
   previously confused with the target's `TEST_DATA` constant.

2. **Fallback (always active, independent of #1): an honest, non-fabricated
   compile-failure reason.** When a test command's output cannot be parsed
   as a recognized summary format at all -- overwhelmingly a compile/import
   failure, since a real, executed, *failing* assertion always **does**
   produce a parseable summary -- `evaluate_tests` now names the actual
   underlying error in its `Status.UNAVAILABLE` reason via
   `extract_compiler_error_snippet` (a tool-agnostic, best-effort extractor
   recognizing rustc's `error[Exxxx]:`/`error:` lines and Python/JS
   `XxxError:`/`XxxException:` lines, preferring the most specific/last
   such line over a bare `Traceback (most recent call last):` preamble),
   e.g. *"... likely a compile/import failure, not a behavioral test
   failure: error[E0425]: cannot find function `NewLuhn` in this scope"*.
   This was already true structurally before this change --
   `parse_cargo_test_output` returns `None` (never a fabricated `{"total":
   0, ...}`) on a compile error, so `total`/`passed`/`failed` were already
   `Status.UNAVAILABLE`, never a measured value -- this fallback only makes
   the *reason* concrete and actionable instead of a generic "output did
   not match a recognized format" message. `compute_not_executed` (see
   [Expected vs. executed](#expected-vs-executed-the-papers-tpr-denominator))
   already, independently, threads this reason verbatim into
   `validated_tests_not_executed` while leaving `failed` itself
   `Status.UNAVAILABLE` -- **never** a fabricated `Status.MEASURED` value
   equal to `expected`. A suite that never compiled is therefore always
   distinguishable, in the data itself, from one that compiled and
   genuinely failed every assertion: `not_executed == expected` (correct --
   literally none of them ran) while `failed.status != Status.MEASURED`
   (never coerced into a false "0 passed" or "all failed" verdict).

**Why Oxidizer-only.** This mechanism is wired through
`_adapt_rust_oracle_text` only for Oxidizer's independent-test and coverage
adapters, not CRUST or AlphaTrans/SKEL. CRUST's oracle is the **literal
interface/contract**
CodeWeaver was given as its own immutable starting point (`run_dir/
scaffold/`); a real naming mismatch there is a genuine contract violation,
not an idiomatic false negative, so rewriting it would hide a real defect.
AlphaTrans/SKEL are not extended in this pass (no verified naming-mismatch
evidence for them yet); the underlying utilities (`read_name_mapping`,
`build_identifier_rewrite_index`, `rewrite_identifiers_with_name_mapping`)
are written generically enough to extend later if similar evidence
surfaces.

### New/renamed fields (`raw_runs.csv`/`raw_runs.jsonl`, `schemas/raw_run.schema.json`)

| Field group | Meaning |
|---|---|
| `translated_tests_total/passed/failed/pass_rate[_status/_reason]` | Alias of the pre-existing `dev_tests_*`/`dev_test_pass_rate` (kept for compatibility, formula UNCHANGED: `passed/total`, i.e. relative to what actually ran) -- CodeWeaver's own translated, self-graded tests. Never the paper's TPR. |
| `translated_tests_expected/not_executed[_status/_reason]` | Best-effort "where possible" expected-vs-executed analogue for the translated family -- see [Expected vs. executed](#expected-vs-executed-the-papers-tpr-denominator) below. Reuses the existing static target-test discovery as `expected`; does **not** change `translated_tests_pass_rate`'s own formula above. |
| `validated_tests_expected/executed/passed/failed/not_executed/pass_rate[_status/_reason]` | The independently validated developer-test oracle described above. Renamed from `validated_tests_total` to `validated_tests_executed`, plus two NEW fields (`expected`, `not_executed`) and a redefined `pass_rate` -- see [Expected vs. executed](#expected-vs-executed-the-papers-tpr-denominator) below for the full rationale. `pass_rate` is the paper's TPR when measured. |
| `validated_tests_expected_native/_paper/_source[_status/_reason]` | CRUST-only: the two INPUTS `validated_tests_expected` above is reconciled from (a NATIVE static `#[test]`-attribute-plus-binary-harness count, and the paper's own AUTHORITATIVE per-project count from `--crust-paper-expected-tests`), plus `_source` (`"paper"`/`"native"`) recording which one won -- see [CRUST's native-vs-paper-aligned expected-test-count](#crusts-native-vs-paper-aligned-expected-test-count) below. `not_applicable` for every other tool. |
| `oracle_integrity[_status/_reason]` | CRUST-only: `pristine`/`mutated`/`not_copied` (`not_applicable` for every other tool -- only CRUST exposes an immutable-input scaffold to the translating agent at all). |
| `function_validation_total/passed/failed/pass_rate[_status/_reason]` | Execution-based per-function validation with a RELIABLE one-to-one function mapping (Oxidizer only, when `--reference-results-root` resolves harness files; `not_applicable` for CRUST; `unavailable` for AlphaTrans/SKEL -- see `function_harness_tests_*` below for their separate evidence). `pass_rate` remains the executed-relative diagnostic. Structurally distinct from the symbol-only `function_translation_ratio`. |
| `function_validation_expected/not_executed/paper_pass_rate[_status/_reason]` | Paper-aligned fixed denominator from Table 1's per-project `Exercised` column: exactly 1,397 functions across the 18 non-CRUST projects. `paper_pass_rate` is `passed/expected`; functions without a reliable executable adapter remain explicitly `not_executed` instead of disappearing. `not_applicable` for CRUST, which §4.2.3 excludes. |
| `function_harness_tests_total/passed/failed/pass_rate[_status/_reason]` | Standardized GENERATED harness execution for Oxidizer's `*generated*.rs`, AlphaTrans's pinned `agent_test/` files, and SKEL's `javascript/*generated*.js`. `not_applicable` for CRUST; `unavailable` without the reference artifact or when no matching files execute. Never relabeled as per-function validation. |
| `function_harness_tests_expected/not_executed/paper_pass_rate[_status/_reason]` | Fixed paper inventory (1,704 non-CRUST cases). `paper_pass_rate` is passed/expected; collection/build blocks remain explicit in `not_executed` rather than shrinking the denominator. |

`table1_effectiveness.csv/pdf`'s headline `tpr` column is sourced
**exclusively** from `validated_tests_pass_rate` when measured; a new
`tpr_source` column (`validated`/`unavailable`) records this explicitly, and
`tpr` is otherwise reported missing -- it is never silently backfilled from
`translated_tests_pass_rate`, which remains its own, separately-labeled
column in the same table. `table1_effectiveness.csv/pdf` also carries the
summed/averaged `function_harness_tests_*` alongside `function_validation_*`
(per selected tool and `ALL`), and `table1_paper_reference.csv` separately
carries the paper's own `function_validation_denominator_non_crust` (1,397)
reference figure -- never blended into the measured row.
`table_function_validation.csv/pdf` reports all THREE structurally distinct
kinds per project, side by side but never merged into one number:
`function_translation_ratio` (symbol/completeness),
`function_validation_*` (reliable per-function execution, Oxidizer only),
and `function_harness_tests_*` (GENERATED harness execution, AlphaTrans/SKEL
only), plus `oracle_integrity`.

### Expected vs. executed: the paper's TPR denominator

The paper's own TPR (test pass rate) is **passed validated developer tests
divided by the benchmark's known, FIXED validated-test denominator** --
e.g. the paper's own worked example reports **1,822/2,107** even though only
**TE=1,970** validated tests actually executed for that row (some of the
oracle's known tests never got a chance to run at all, most commonly
because the CodeWeaver-translated target failed to build/import). TPR is
therefore **passed/expected**, never **passed/executed** -- a subtly
different, and NOT interchangeable, denominator. This harness's own
`compute_paper_pass_rate`/`paper_equivalent_pass_rate` implement exactly
that distinction:

- **`validated_tests_expected`** is a STATIC, best-effort count taken from
  the independent oracle's OWN files alone (CRUST: `#[test]` attributes
  across the pristine scaffold's contract paths; Oxidizer: `#[test]`
  attributes across the reference `*_test.rs` oracle files; AlphaTrans: a
  static `ast`-based count of pytest-/unittest-style test functions across
  `verified_test/*.py`; SKEL: every row in `test_name_mapping.csv` (the
  `verified test` value is a prior-system result, not a selector) -- available
  **before and entirely independently** of any
  CodeWeaver translation/build attempt, so it stays measured even when the
  CodeWeaver target cannot compile/import at all.
- **`validated_tests_executed`** (renamed from `validated_tests_total`),
  **`_passed`**, **`_failed`** are the OUTCOME of actually running that
  oracle against the CodeWeaver-produced target -- unchanged behavior from
  before this fix, just renamed for clarity alongside the two new fields.
- **`validated_tests_not_executed`** = `max(0, expected - executed)`,
  clamped at `0` (never negative): a static, best-effort `expected` counter
  can occasionally under-count relative to what a real test runner reports
  as executed -- e.g. CRUST's whole-crate `cargo test` may also run the
  target's own embedded `#[test]`s beyond the restored scaffold contract's
  own tests. When `validated_tests_executed` itself is NOT measured (a
  build/import failure, timeout, or unparseable output), `not_executed`
  still reports a real, measured value equal to the FULL `expected` count
  -- literally none of them ran -- with a `reason` naming the real
  underlying failure verbatim, so a build failure is never silently
  relabeled as an ordinary "some tests were skipped" outcome.
- **`validated_tests_pass_rate`** = `validated_tests_passed /
  validated_tests_expected` (via `compute_paper_pass_rate`) -- **never**
  `passed/executed`. A build/import failure (`validated_tests_passed` is
  `Status.ERROR`/`Status.UNAVAILABLE`, never a fabricated measured `0`)
  still yields a real, measured `0.0`-numerator rate over the full expected
  denominator -- exactly mirroring the paper's own methodology that a
  project whose target never even built contributes zero passing tests, it
  is not excluded from the rate as an undefined row -- but the `reason`
  string always names the real underlying failure, so this is never
  mistaken for a genuine, executed, all-failing run. A `>100%` rate
  (`passed > expected`, e.g. the CRUST whole-crate edge case above) is
  deliberately **not** clamped -- it is left visible as an honest signal of
  a data-quality mismatch rather than silently masked.
- **`table1_effectiveness`'s own aggregate `validated_tests_pass_rate`**
  (and every `*_expected`/`*_not_executed` sum) is computed by a dedicated
  **SUM-based** `paper_equivalent_pass_rate` helper -- `sum(passed) /
  sum(expected)` across every included row whose own `expected` is
  measured -- **never** a mean of each row's own already-computed pass
  rate. This matters: a naive per-project mean would NOT reproduce the
  paper's own weighted aggregate (a project with many expected tests must
  count proportionally more than one with few) -- see
  `test_paper_equivalent_pass_rate_is_sum_based_not_mean_of_per_row_rates`
  in `tests/experiments/test_analyze.py` for a worked regression example.
- This passed/expected formula applies **uniformly to every variant**
  (`full` and every ablation/baseagent variant alike), since `collect_run`
  computes `validated_tests_pass_rate` identically regardless of `variant`
  -- it is not a `full`-only fix. `figure7_ablation.pdf` uses this same
  independently validated rate and never falls back to translated/self-
  graded tests; without `--reference-results-root` its TPR is missing.
- **Analogous, best-effort translated-family fields**:
  `translated_tests_expected`/`translated_tests_not_executed` reuse the
  existing static target-test discovery (`target_test_count`) as the
  "expected" denominator for CodeWeaver's own self-graded suite, computed
  the same way (`compute_not_executed`). `translated_tests_pass_rate`
  itself is **deliberately left unchanged** (still `passed/total`, i.e.
  relative to what actually ran) for backward compatibility -- only the two
  new fields were added alongside it, per this round's "where possible"
  scope (not a full parallel passed/expected rate for the translated
  family).
- `function_validation_expected/not_executed/paper_pass_rate` uses the
  paper's exact 1,397-function non-CRUST denominator. The generated
  `function_harness_tests_*` family remains separate because those test
  cases do not have a defensible one-to-one function mapping.

### CRUST's native-vs-paper-aligned expected-test-count

A naive, static `#[test]`-attribute count over a CRUST scaffold's own
contract paths (`validated_tests_expected_native`) is **known to disagree**
with the paper's own hand-curated bookkeeping for real projects, **in both
directions**, and one real project has **zero** regex-discoverable
`#[test]`s at all despite the paper counting one expected test for it:

- **`2dpartint`**: the paper's own denominator is **6**, but the scaffold's
  regex-discoverable `#[test]` count is **8** (native **over**-counts by 2).
- **`holdem-odds`**: paper **22** vs. native **24** (native over-counts by 2).
- **`libfor`**: paper expects **1**, but the scaffold has **zero**
  `#[test]`-annotated functions -- its sole oracle is
  `rust/src/bin/test.rs`, a **binary assertion harness**: a plain `fn
  main()` whose own process **exit code** is the test verdict. Plain
  `cargo test` never discovers or runs this file at all (it only executes
  `#[test]`-annotated functions, though it does compile every target --
  including `src/bin/*.rs` binaries -- as a side effect), so without the fix
  described here, `libfor` would silently report a measured **0** for both
  `validated_tests_expected` and `validated_tests_executed` -- never
  visibly wrong, just quietly incomplete.

Because the full, authoritative 100-project CRUST mapping is not shipped as
machine-readable data anywhere in this harness's own inputs (only these
three projects' exact figures are known from direct paper/artifact
inspection), this harness never hardcodes fabricated per-project numbers.
Instead, `validated_tests_expected` is reconciled from **two structurally
separate, independently-recorded inputs**:

- **`validated_tests_expected_native`** -- a static `#[test]`-attribute
  count across the pristine scaffold's own contract paths, **plus** one
  additional count for every detected binary assertion harness (a
  `src/bin/*.rs` file with **zero** `#[test]` attributes -- see
  `crust_binary_test_harnesses`). Always available (purely static, from
  files this harness already has unconditional read access to), but
  explicitly labeled `_native` so it is never mistaken for the paper's own
  figure.
- **`validated_tests_expected_paper`** -- the paper's own authoritative,
  hand-curated per-project count, read via the new `--crust-paper-expected-tests
  <path>` flag from either the official `results.xlsx`'s own `"sweagent
  crust - tool test"` worksheet (via the optional `openpyxl` dependency;
  sheet name matched case/whitespace-insensitively, columns matched
  best-effort by header name with a positional 0/1 fallback for a
  2-column sheet) or an explicit `.json` (`{"<project>": <count>, ...}`)
  or `.csv` (`project,expected_tests`) reference-inventory file.
  `Status.UNAVAILABLE` (never a silent 0/fallback) when the flag is
  omitted, the file can't be parsed, or the project isn't found in it.

`validated_tests_expected` itself is the **combination**
(`crust_combine_expected`): the paper-aligned figure is **always preferred**
when measured (it is the denominator the paper's own TPR is computed
against); the native count is only ever used as a **labeled fallback**
(`validated_tests_expected_source == "native"`) when no paper-aligned
figure is available. The two are **never** silently presented as equal --
`2dpartint`'s native `8` and paper `6` both remain independently visible in
`raw_runs.csv` even when `expected` itself resolves to `6`. When
`cargo test` itself produces a measured result (a real build succeeded),
any detected binary-harness oracle is additionally run via `cargo run
--quiet --manifest-path Cargo.toml --bin <name>` (overridable per-dataset
via `dataset_spec["binary_test_cmd_template"]`) and merged into
`validated_tests_executed`/`_passed`/`_failed` (`_merge_test_counts`); if
`cargo test` itself was **not** measured (a build/compile failure), the
binary-harness run is skipped entirely -- there is no clean build to run a
binary against, and attempting one would just duplicate the same
underlying failure. Omitting `--crust-paper-expected-tests` entirely is
always safe: `collect.py` prints an explicit `WARNING` to stderr only if a
*supplied* path could not be loaded, and every affected field degrades to
an honest `Status.UNAVAILABLE`/native-fallback rather than crashing or
silently fabricating the paper's own number.

### SKEL's independent validated-test AST extraction

Unlike CRUST/Oxidizer/AlphaTrans, the official RESULTS artifact ships **no
separate independent-oracle file tree** for SKEL at all -- `javascript/
source.js` embeds the reference implementation and its own translated
tests together in one file. Every `test_name_mapping.csv` row belongs to
the 74-test validated inventory; `verified test` records the prior system's
outcome and is not a selector. To surface these as a real, independently
executed developer-test oracle without ever copying `source.js` wholesale
(which would smuggle the entire reference implementation into a CodeWeaver
target directory) or inlining any of its private/helper code, this adapter:

1. Parses `source.js` with `tree-sitter-javascript` and, for every
   CSV-listed test name, locates its top-level `function`/`class`
   declaration and walks its body to collect every **free** (not locally
   bound by a parameter, destructuring pattern, `const`/`let`/`var`,
   `catch`, `for`-`of`/`for`-`in`, or nested function/class name)
   identifier it references -- including JS's `shorthand_property_identifier`
   object-literal-shorthand value position (`return {foo};`), a grammar
   node type distinct from a plain identifier that an early prototype of
   this adapter initially missed.
2. Classifies each free identifier into one of six resolutions, tried in
   this fixed priority order (the first match wins, so an established rule
   is never overridden by a newer one below it):
   1. **(a)/(b) safe builtin/require** -- a JS/Node builtin, or a safe
      Node-core `require` (`assert`/`util`) `source.js` itself declares.
   2. **(c) safe exported** -- one of `source.js`'s **own declared
      `module.exports` names**, recognized in both the `module.exports =
      {...}` object-literal form and the `module.exports.NAME = ...` /
      `exports.NAME = ...` member-assignment form (both forms occur in the
      real official artifact). `module.exports` names are treated as safe
      **because** they are the reference's own declared public surface, not
      because this adapter verifies CodeWeaver's target actually provides
      them -- a missing/renamed target export surfaces naturally as an
      honest runtime failure inside the generated harness's own
      `require()`/call-site try/catch (a real "public API mismatch"
      signal), never a silent skip.
   3. **(d) safe target-bound** -- the identifier is a genuine top-level
      declaration in `source.js` that is **not** one of `source.js`'s own
      `module.exports` names, but CodeWeaver's **own** target entry file
      (`index.js`) *independently* exports a symbol with that exact same
      name. This never copies one byte of `source.js`'s own declaration
      text -- it only widens which names may be *bound from CodeWeaver's
      own target* at harness-assembly time (the same binding mechanism as
      (c), just sourced from the target instead of the reference). This
      directly addresses projects like `heapq` where `source.js` declares
      **zero** `module.exports` names at all, so every listed test was
      previously blocked outright regardless of what it actually called --
      such a project is no longer a blanket "no oracle exists" case, only
      as good as whichever names CodeWeaver's own translation happens to
      independently export under the same identifier.
   4. **(e) safe literal expectation** -- the identifier is a
      *single-declarator* top-level `const`/`let`/`var` declaration whose
      value is a provably pure data literal (numbers, strings, booleans,
      `null`, substitution-free template strings, or arrays/objects built
      only from further pure literals with plain, non-computed,
      non-shorthand, non-spread, non-method keys). Its exact declaration
      statement text is spliced verbatim into the harness (before any test
      bodies that reference it) as an inert constant -- safe by
      construction because a pure literal references nothing external, so
      this never risks smuggling reference implementation *logic*, only
      inert expected-value data (e.g. an `EXPECTED_RESULT = [1, 2, 3];`
      fixture some tests compare against). Multi-declarator statements
      (`const a = 1, b = f();`) are excluded **entirely** from this rule
      (not just the impure declarator), because the enclosing statement's
      verbatim text would otherwise also carry the sibling declarator's
      unsafe initializer.
   5. **(f) pinned test support** -- a narrowly allowlisted fixture or
      assertion helper whose body was manually verified as test-only in the
      official corpus. No executable production helper is admitted.
   6. **blocking** -- anything else (almost always a private helper, e.g.
      real `bst`'s `_get_binary_search_tree` or `strsim`'s
      `input_shanghai`, that is neither exported by the reference nor
      independently re-exported by CodeWeaver's own target under the same
      name, nor a pure data literal). A test with even one blocking
      identifier is refused extraction outright; nothing about it is
      inlined or approximated.

   A more aggressive design was explicitly considered and rejected: general
   "test helper *function*" extraction via a transitive safety-closure
   (recursively allow copying a helper if *all* of its own free identifiers
   already resolve as safe). This remains deliberately **unsupported**: a
   genuinely private *production* helper (e.g. a real `_heappop_max`) that
   happens to only call JS builtins internally would be indistinguishable
   from a real test-only helper under such a closure rule -- the same
   reasoning that originally motivated blocking `heapq`-style tests at all.
   This residual gap is therefore a deliberate, narrow, honestly-documented
   boundary of the adapter, not a claim that "no independent oracle exists"
   for the affected tests -- rules (d)/(e) above already recover the
   specific, provably-safe sub-cases of that same historical blocker.
3. Assembles every extractable test's **verbatim** source text -- plus any
   rule-(e) literal-support declarations it depends on, spliced in *before*
   the test bodies -- into one synthetic Node.js harness that destructures
   only the needed identifiers from a guarded dynamic `import("./index.js")`
   in an `.mjs` harness (supporting both CommonJS and ESM targets). Existing
   top-level target declarations are exposed only in the temporary copy; a
   load failure is caught, not fatal, and fails
   every test with an informative message), monkey-patches `console.assert`
   (Node's own `console.assert` does not throw on a falsy condition, so a
   source-faithful `console.assert(...)` would otherwise silently no-op),
   and treats either a thrown exception or an exact `=== false` return
   value as a failed test (some real listed tests, e.g. `rbt`'s, signal
   failure only via their own return value, never a throw) -- printing a
   `# pass N` / `# fail M` summary this harness's existing Node TAP parser
   already recognizes. This harness is written into, and executed from, a
   **temporary copy** of the run's target; the run's own target tree is
   never touched.
4. Reports `Status.UNAVAILABLE` with a precise reason if `tree-sitter`/
   `tree-sitter-javascript` are not installed, `test_name_mapping.csv`/
   `javascript/source.js` cannot be resolved, or every CSV-listed test was
   blocked from extraction; a real `Status.MEASURED` `0` only if the CSV
   itself lists zero tests. When only *some* listed tests
   are extractable, `validated_tests_executed` (renamed from
   `validated_tests_total`) counts **only** the extractable subset (never
   the full CSV count) -- but `validated_tests_expected` always retains the
   FULL CSV row count regardless, so `validated_tests_not_executed`
   correctly reports the blocked tests as not executed rather than silently
   shrinking the denominator -- and a `reason` on the `executed` field names
   the excluded test(s).

The pinned official artifact contains 74 rows: `bst` 11, `colorsys` 2,
`heapq` 4, `html` 6, `mathgen` 3, `rbt` 10, `strsim` 19, and `toml` 19.
All 74 are safely extractable under the rules above. Runtime success still
depends entirely on each CodeWeaver target's own API and behavior; extraction
success is not counted as a passing test.

`figure7_ablation.pdf`/RQ3 uses the same independently validated,
passed/expected `validated_tests_pass_rate` as Table 1 for every variant.
It never falls back to a variant's translated/self-graded tests; without
the reference oracle its TPR is explicitly missing.

## Honesty and provenance guarantees

- **Measurement vs. zero.** Every count/rate in `raw_runs`/`test_comparisons`
  is paired with an explicit `*_status` field (`measured`/`missing`/
  `unavailable`/`not_applicable`/`error`) and, where relevant, a `*_reason`
  string. `analyze.py`'s aggregations only ever fold in rows whose status is
  `measured`; anything else is excluded from means/sums, never coerced to 0.
- **No measured data is still handled honestly.** `analyze.py --on-empty`
  controls what happens with zero measured rows: `watermark` (default)
  writes every artifact stamped with an unmissable "NO MEASURED DATA"
  marker (a red PDF heading; a leading CSV marker row); `fail` aborts and
  writes nothing, for CI-style hard gating.
- **The completion verdict is the one place allowed to say "complete."**
  `report.py` requires: exactly 118 manifest projects; complete raw matrix
  coverage; complete primary-selection paper-RQ2 and generated-test project
  rows with no duplicates; schema-valid rows (including generated coverage
  status fields); and consistent protocol-defining model, agent-timeout, Git,
  and CodeWeaver-package provenance. Exact Copilot CLI versions remain
  recorded and any version drift is reported separately as informational
  provenance, but patch-level CLI drift alone does not relabel an otherwise
  complete measured matrix as incomplete. Any failing protocol condition
  produces an explicit `INCOMPLETE` verdict with itemized reasons.
  `report.py` never refuses to run -- a report that honestly says "0/118
  measured, `analyze.py` was never run" is itself valid output.
- **Provenance is recorded per run, not assumed.** `common.collect_provenance()`
  records the model ID, agent timeout, git SHA, CodeWeaver package version,
  Copilot CLI version, Python version, OS/hostname, and best-effort
  toolchain versions for every measured row; `report.py`'s checksum/
  provenance JSON separately documents (and labels) that it describes the
  *report-rendering* machine, not the experiment-running machine.
- **Subprocess safety.** Every external command this harness runs (build,
  test, coverage, the real `codeweaver` CLI) goes through `common.run_argv`,
  which only ever accepts an argument array (never a shell string), so
  there is no shell-injection surface regardless of what a translated
  project's own filenames/config happen to contain. On POSIX, timed
  commands run in a new process session and the complete process group is
  terminated, so compiler/test descendants cannot retain captured pipes.
  CodeWeaver's separate Copilot CLI boundary applies the same process-group
  rule to the 5,000-second per-agent timeout, preventing a timed-out native
  Copilot child from continuing to edit a run after its wrapper exits.
- **Path safety.** `acquire.py`'s extraction rejects any archive member
  whose resolved path would escape the destination directory (zip-slip,
  absolute paths, drive letters, UNC paths) before writing anything.

## Testing this harness

```bash
# From the repository root:
python -m pytest tests/experiments/ -q
```

As of this delivery, all tests under `tests/experiments/` pass -- see the
final summary reported alongside this README for the exact count. No test
in this suite touches the network, an LLM, or a real per-language toolchain;
every test builds its own synthetic fixtures (manifests, run states,
raw-run rows, comparison rows, failure CSVs) in-process or in `tmp_path`.

Two notes:

- Run `pytest tests/experiments/`, not a bare `pytest` from the repository
  root: there is no root-level pytest configuration restricting discovery,
  and `experiments/recodeagent/test_compare.py` is a harness **module** (RQ2
  logic) whose filename happens to match pytest's default `test_*.py` glob.
  `experiments/recodeagent/conftest.py` (`collect_ignore = ["test_compare.py"]`)
  guards against accidentally collecting it as a test suite if pytest is
  ever invoked from a directory that would otherwise discover it.
- Tests that exercise optional-dependency behavior (PDF/figure rendering via
  `reportlab`/`matplotlib`, the scipy Wilcoxon path) run the **real** library
  when it is installed and separately verify the graceful-degradation path
  via `monkeypatch`-ing `common.optional_import` to simulate its absence --
  both branches are covered regardless of what happens to be installed in
  the environment the tests run in.

## Licensing and data provenance

- **This harness's own code** (everything under `experiments/recodeagent/`
  and `tests/experiments/`) is part of the CodeWeaver repository and
  licensed under the repository's own `LICENSE` (MIT).
- **The official ReCodeAgent artifact and its four benchmark datasets**
  (CRUST-Bench, Oxidizer, AlphaTrans, SKEL) are third-party research
  artifacts hosted on Zenodo (record `21399688`) under their own license
  terms, which this harness does not restate or relicense. Consult the
  Zenodo record and each dataset's own upstream repository for their
  license before redistributing anything derived from them.
- **No third-party source is vendored into this git repository.** `acquire.py`
  writes the verified/extracted artifact under a caller-supplied
  `--artifact-root` that is expected to live outside this repository (e.g.
  add it to a local, untracked directory); `prepare.py`/`run.py` likewise
  write workspaces/run outputs under caller-supplied roots, not under
  `experiments/recodeagent/`. The same applies to `--reference-results-root`
  (the official `results.zip` extracted tree, used only by `collect.py`'s
  post-hoc independent evaluator -- see
  [Post-hoc independent evaluator](#post-hoc-independent-evaluator)): it is
  never copied into this repository or into a run's own workspace, only read
  from at `collect` time into short-lived `tempfile.TemporaryDirectory()`
  evaluation copies that are deleted immediately after that evaluation
  completes.
- **CodeWeaver-measured outputs** (`raw_runs.*`, `test_comparisons.*`,
  `analysis_provenance.json`, the rendered tables/figures/report) describe
  *this harness's own measurements* of CodeWeaver's behavior and are
  distinct from the paper's own reported numbers; see
  [RQ -> artifact mapping](#rq---artifact-mapping) for exactly how the two
  are kept apart in every generated artifact.

## Integration assumptions and known limitations

Documented explicitly rather than silently assumed. This harness-building
sandbox still has no direct network access to Zenodo, so `acquire.py`'s own
download path remains unexercised here; however, a parent-provisioned copy
of the official artifact was made available read-only at a machine-specific
path in a later integration pass, and was used to calibrate/verify (never
vendor) the facts below:

1. **Dataset directory layout is verified against a real, extracted
   official artifact** (read-only inspection, not vendored into this repo).
   The 118 benchmark projects live one level below the extracted
   `implementation.zip` root, at `data/tool_projects/{crust,oxidizer,
   alphatrans,skel}/<project>/`. `manifest.py.resolve_project_root` tries
   `--artifact-root` itself first, then descends into
   `experiment.toml`'s `[artifact].project_root_subdir_candidates`
   (currently `["data/tool_projects", "data/projects"]` -- a relative,
   artifact-structure fact, never a machine-specific absolute path) looking
   for the first level containing at least one dataset directory. Verified
   end-to-end against the real artifact: pointing `--artifact-root` at
   either the extracted `implementation.zip` root *or* directly at
   `data/tool_projects` both discover exactly 100/6/4/8/118 projects with no
   count mismatch. Per-dataset `dir_candidates`/`source_subdir_candidates`/
   `scaffold_subdir_candidates`/`ground_truth_subdir_candidates` were
   likewise corrected against the real tree (e.g. CRUST's scaffold directory
   is literally named `rust/`, now first in its candidate list). If a future
   artifact revision ever renames things, `manifest.py --probe
   <artifact-root>` still prints the real top-level tree so candidates can
   be corrected via a **config edit**, not a code change.
2. **Source-vs-oracle test discovery (RQ2) -- verified: all four datasets
   nest developer tests *inside* the source tree, not a separate oracle
   directory.** CRUST's C tests live at `c/test/*_spec.c` (sibling of
   `c/src/`); Oxidizer's Go tests are `go/*_test.go` files alongside source
   (Go convention); AlphaTrans's Java tests live at `java/src/test/`; SKEL
   goes one step further and embeds `test_*`-prefixed functions directly
   inside `python/source.py` itself, alongside the algorithm. In every case
   `oracle_subdir_candidates` is therefore expected to resolve to `None` by
   design (not a bug) -- the tests are still discovered/counted/copied
   correctly because `source_rel_path` is copied and counted as a whole,
   nested tests included. `test_compare.py` discovers source developer tests
   from each project's `source/` tree for exactly this reason, consistent
   with `manifest.py`'s own `test_count_source`. SKEL's `javascript/
   translated.js` ground truth is verified solution-only (no test-shaped
   functions) -- translating `source.py`'s embedded tests into a new JS test
   file is exactly the RQ2 mapping this dataset exercises.
3. **Ablation implementation: `noanalyzer`/`noplanning`/`novalidator` now run
   the REAL Burr graph via CodeWeaver core's own `CODEWEAVER_SKIP_STAGES`
   instrumentation; only `baseagent-condensed`/`baseagent-concat` remain
   harness-driven single-shot prompts.** CodeWeaver core
   (`codeweaver/config.py`/`codeweaver/actions.py`) exposes exactly one
   narrow, default-off, experiment-only flag: a `CODEWEAVER_SKIP_STAGES`
   environment variable (comma-separated; valid values `analyze`/`plan`/
   `validate`; unioned with a config file's own `[execution].skip_stages`;
   an unknown value raises `ValueError`) that, when set, makes the
   corresponding stage's Burr action write a deterministic placeholder
   artifact (e.g. a placeholder `analysis.md`/`plan.json`/`report.json`)
   and continue the *same* graph instead of doing that role's real work --
   every other milestone/repair/parity/scope-re-entry behavior, and all of
   CodeWeaver's ordinary (non-experiment) behavior, is completely
   unaffected. `run.py.STAGE_SKIP_VARIANTS` maps `noanalyzer`/`noplanning`/
   `novalidator` to `analyze`/`plan`/`validate` respectively and, for
   exactly these three variants (same as `full`), invokes the real
   `python -m codeweaver run --config <config> --app-id <id>` CLI
   subprocess with that one environment variable set -- there is no
   separate harness-side staged driver for them any more (the old
   single-pass driver, `run.py.run_ablation_variant`, is retained but no
   longer called by anything, for auditability). One consequence is
   genuinely structural, not a simplification: `validate()`'s skip branch
   unconditionally marks each milestone "passed" (there is no verdict to
   fail), so `novalidator`'s `lc` (loop count) is always `0` by real
   construction (no repair loop can ever trigger without a validator
   verdict) -- not a harness shortcut. `collect.py` records each of that
   variant's per-milestone `passed` values as `missing` (an omitted
   validator attestation, i.e. `passed=None` in CodeWeaver's own printed
   history), never a fabricated `0`/`False`; the corresponding `validate`
   entry is likewise excluded from `nc`/`tec`/`sec` because it never did
   real work, only wrote a placeholder. `noanalyzer`/`noplanning` retain a
   fully real, independent validator, so their milestone loop can and does
   genuinely repeat/repair like `full`; their `lc` is measured, not
   hardcoded, and their own skipped stage (`analyze`/`plan` respectively)
   is likewise excluded from `nc`/`tec`/`sec`. `baseagent-condensed`/
   `baseagent-concat` are unaffected by any of this: they remain
   harness-authored, single-shot, one-agent prompts with no Burr graph at
   all (see item 4), so `lc` is still `0` for them by construction.
   Objective pass/fail (validated TPR) for every variant, including all
   five ablations, is always computed by `collect.py` actually running the
   project's configured build/test/oracle commands -- never by trusting an
   agent's self-report.
4. **`baseagent-condensed`/`baseagent-concat` prompts are harness-authored.**
   The paper's own exact condensed/concatenated prompt wording was not
   available in this sandbox. `run.py.build_condensed_prompt` /
   `build_concat_prompt` construct a reasonable one-agent-prompt equivalent
   from CodeWeaver's own existing per-stage prompt templates (same
   model/effort/timeout budget as the full pipeline), but are not a verbatim
   reproduction of the paper's own wording. Both variants' protocol was
   tightened to close a gap versus `full`'s real six-role graph:
   `build_concat_prompt` is a literal concatenation of **all six** of
   CodeWeaver's own role prompts -- Analyzer, Scoper, Planner, Translator,
   Validator, and Parity (not five) -- each rendered under its own
   `## Responsibility: <stage>` section header with this project's real
   context, so the single autonomous agent is handed every responsibility
   `full` would otherwise split across six separate calls, verbatim,
   with nothing dropped; `build_condensed_prompt` is a compact, freeform
   restatement of the same six responsibilities in prose rather than
   per-role sections, and now explicitly instructs the agent to, at the
   end, "compare the complete source and target component by component and
   close any remaining parity gaps" before declaring success -- i.e. a
   final parity self-check equivalent to what the dedicated Parity agent
   does in `full`, folded into the one prompt rather than dropped. Neither
   change adds a Burr graph, a second call, or any per-stage state to these
   two variants; both remain exactly one raw, single-shot `copilot` prompt
   (see item 5's `lc == 0` note and `test_run.py`'s
   `test_baseagent_concat_prompt_mentions_all_six_responsibilities` /
   `test_baseagent_condensed_prompt_mentions_final_parity_check`).
5. **Trajectory precision: `full` and the three stage-skip ablations share
   a documented lower bound for scope/parity re-entry counts;
   `baseagent-*` remain exact.** `collect.py.trajectory_from_full_pipeline`
   reconstructs NC/TEC/SEC/LC/ALL from the real CodeWeaver CLI subprocess's
   own captured stdout (`history`/`finished` summary lines) identically for
   `full`, `noanalyzer`, `noplanning`, and `novalidator` (all four now run
   the same real Burr graph, differing only in which one stage is skipped
   via `CODEWEAVER_SKIP_STAGES`); `translate`/`validate`/`lc` counts are
   exact, but `scope`/`parity` re-entry counts on an incomplete-parity
   loop-back are not independently observable from available artifacts and
   are reported as a `>=1` lower bound with an explicit
   `trajectory_precision="lower_bound"` (never silently exact). Whichever
   one stage a given ablation deliberately skipped is excluded from that
   run's `nc`/`tec`/`sec` (see item 3) and the reason is recorded in
   `trajectory_reason`; `raw_runs`' own `ablation_skipped_stage` column
   records which stage (if any) applied to that row. `baseagent-condensed`/
   `baseagent-concat` are the only variants still reconstructed from
   `recodeagent_calls.jsonl` (a complete call-by-call record this harness
   itself writes for its own single-shot driver), reported as
   `trajectory_precision="exact"`.
6. **NC/TEC/SEC/LC/ALL: the paper's own definitions are now known, but this
   harness's computation remains a deliberately simpler, non-equivalent
   proxy -- never compare the two numerically.** Verified against the
   official artifact's own `src/analysis/ablation.py` and its
   `results/ablation_study/graphectory_analysis/<variant>.<tool>.<project>*/
   trajectory_metrics.csv` outputs: the paper's `NC`/`TEC`/`SEC`/`LC`/`ALL`
   are short labels for `node_count`/`exec_edge_count`/`hier_edge_count`/
   `loop_count`/`avg_loop_length` -- five columns computed by a separate,
   unshipped "graphectory" tool that builds an actual graph of the agent's
   own interaction trace (tool-call nodes; sequential "exec" edges;
   hierarchical "hier" edges, e.g. parent/sub-agent invocation; cycle/loop
   detection over that graph) plus location-clustering and
   patch-success-streak fields not used by this harness at all. This
   harness's `collect.py.TrajectoryMetrics` computes something structurally
   simpler from CodeWeaver's own JSONL/CLI-stdout evidence, re-using the
   same five short names for continuity with the paper's RQ3 vocabulary:
   `NC` = number of distinct pipeline stages/roles that executed at least
   once; `TEC` = total count of stage executions across the whole run;
   `SEC` = a per-stage execution-count breakdown (JSON dict, not the paper's
   scalar hierarchical-edge count); `LC` = loop count, i.e. repair/repeat
   iterations beyond one pass per distinct milestone; `ALL` = total
   executions (currently identical to `TEC`, not the paper's average loop
   length). These are applied consistently across all variants so relative
   (paired) comparisons *within this harness's own measured data* remain
   meaningful, but they are **not a reimplementation of the paper's
   graphectory algorithm** and must never be plotted/compared cell-for-cell
   against the paper's own reference `ablation-study-effectiveness.csv` --
   `analyze.py`/`report.py` label these as CodeWeaver-measured proxy values
   for exactly this reason.
7. **Per-role JSONL log overwrite limits token/tool rollups for repair
   loops.** CodeWeaver core's own `log_dir` convention overwrites a role's
   log file on every call to that role; a repair loop's *earlier*
   iterations' tool/token counts are therefore unrecoverable after the fact
   for any variant whose milestone loop can genuinely repeat -- `full`, and
   now also `noanalyzer`/`noplanning` (their validator is real, so repair
   can trigger just like `full`). `novalidator` never repairs by
   construction (see item 3), so no repair-loop iterations are ever lost
   for it specifically. `collect.py` reports this limitation honestly via
   `tool_invocations_precision` rather than silently under/over-counting.
8. **Token field names are defensively probed, not guaranteed.**
   `common.summarize_copilot_events` only observes `premiumRequests`,
   `sessionDurationMs`, and `codeChanges.*` in CodeWeaver's own current
   Copilot CLI integration (`codeweaver/copilot.py`); no input/output token
   field has actually been *observed* there. Several plausible field-name
   variants (`inputTokens`/`input_tokens`/`promptTokens`/`prompt_tokens` and
   the output equivalents) are probed defensively in case a future CLI
   version adds them, but `total_input_tokens`/`total_output_tokens` report
   `Status.UNAVAILABLE` (never a fabricated `0`) when none are present.
9. **Coverage requires the provisioned language adapters.** The final
   protocol uses `cargo-tarpaulin`, Coverage.py, and c8 automatically; the
   generic `[datasets.*].coverage_cmd`/`coverage_format` fallback remains
   available but is not the paper-equivalent result. The paper's `C`/`C+`
   columns mean independent developer-test coverage before/after adding
   generated tests, not pre-translation scaffold coverage.
   `paper_test_compare.py` therefore computes the authoritative pair only
   after it classifies CodeWeaver-authored generated tests. Missing coverage
   tools, oracle assets, or unexecutable selectors are explicit
   `Status.UNAVAILABLE`/reason values. The official ReCodeAgent generated
   harness is retained only under the separately named
   `standardized_coverage_*` fields.
10. **Test/assertion extraction is a regex-based adapter, not a real
    parser.** `test_compare.py` (and `manifest.py`'s own LoC/test/function
    counters) use per-language regex heuristics across all six languages
    involved (C, Go, Java, Python, Rust, JavaScript) -- adequate for
    structural comparison at scale, not a substitute for AST-based parsing.
    Known limitations: a test's "body" is approximated as the span from its
    own definition to the next test definition (or EOF), which can include a
    little trailing shared non-test code; deeply nested-parenthesis
    assertion calls may truncate at the first heuristically-matched closing
    paren; and expected-value argument position for `assertEqual`-style
    calls follows each language's common convention but is not verified
    against every possible test-framework calling convention in the wild.
    Also note (verified): because CRUST/Oxidizer/AlphaTrans/SKEL all nest
    developer tests inside their source tree (see assumption 2),
    `manifest.py`'s `loc_source`/`test_count_source`/`function_count_source`
    are computed over that whole recursively-walked tree -- i.e. "source +
    its own nested tests", and `function_count_source` does not exclude
    test-prefixed functions from the function tally. Treat these as scale
    indicators, not a precise match to the paper's own LoC/function
    methodology (see `common.PAPER_REFERENCE_TOTALS` for the paper's own
    totals, kept clearly separate).
11. **CRUST scaffold copying is the one documented exception to
    "target trees are evaluator-only" -- verified.** Per the paper's own
    CRUST-Bench protocol, `prepare.py` may copy CRUST's provided Rust
    interface/test scaffold (a contract + tests, not a solution) into the
    workspace as `immutable_input`; confirmed against the real artifact that
    every one of CRUST's 100 `rust/` directories consists of a compilable
    Cargo project whose translatable function bodies are `unimplemented!()`
    stubs (a contract, not a leaked solution). Every other dataset's
    baseline/oracle/ground-truth tree remains evaluator-only and is never
    exposed to Copilot (verified for Oxidizer/AlphaTrans/SKEL: their target
    trees are full, complete reference implementations, correctly kept out
    of `scaffold_subdir_candidates` for all three).
12. **`figure7_ablation`/RQ3 and Table 1 share one TPR provenance.**
    `collect.py` runs the independent oracle for every variant, and
    `compute_ablation_metrics` uses only
    `validated_tests_pass_rate` (`passed/expected`). If the reference oracle
    was not supplied, Figure 7 reports missing TPR rather than falling back
    to translated/self-reported tests.
13. **`verified_test/`'s and `agent_test/`'s own `conftest.py` may resolve a
    relative path one level shallower than intended once copied a single
    directory-level deep into a temporary target copy -- a real,
    pre-existing characteristic, not newly introduced by the
    `agent_test/` extension.** Both reference `conftest.py` files compute a
    project-root-relative path via their own embedded parent-directory
    arithmetic (e.g. `Path(__file__).resolve().parents[3]`/
    `.parent.parent.parent`), written by the official artifact's own authors
    against ITS OWN original directory depth. When this harness copies
    `verified_test/` or `agent_test/` one level deep into
    `tmp_target/{verified_test,agent_test}/...` (see the adapter table
    above), that arithmetic can resolve one directory higher than the
    official artifact's own layout intended. This was deliberately **not**
    "fixed" by rewriting/patching the copied `conftest.py` (which would mean
    evaluating a file this harness silently edited, not the reference's own
    unmodified test harness) -- the `agent_test/` adapter instead mirrors
    the same wholesale-copy precedent `verified_test/` already established.
    Any resulting import/collection error surfaces as an honest, real
    recorded pytest failure (this harness's standard philosophy: record
    failures honestly rather than mask them), not a silently-passing or
    fabricated result. This was verified structurally (fixture-based unit
    tests confirm exactly which files are/are not copied) but **not**
    re-verified against a real `pytest` invocation in this sandbox; a real
    WSL run against the official artifact should treat any resulting
    collection error for these two suites as a known, honestly-recorded
    possibility to investigate, not evidence of a harness defect.
14. **SKEL's `validated_tests_*` AST extraction is a best-effort,
    conservative static analysis, not a general JavaScript interpreter --
    its reliability bar is "never wrong", not "never unavailable".** See
    [SKEL's independent validated-test AST extraction](#skels-independent-validated-test-ast-extraction)
    for the full mechanism, including resolution rules (d) (target-bound
    names) and (e) (pure-literal expectations) added in a later revision of
    this adapter. Four design points worth calling out explicitly: (a) rule
    (d) (safe target-bound identifiers) is the one place this adapter DOES
    consult CodeWeaver's own target -- but only that target's OWN
    independently declared exports (`index.js`'s own `module.exports`,
    read via the same static AST parse, never a live subprocess probe), so
    a target that doesn't actually provide a matching name simply fails
    that one test at harness-run time with an honest per-test message,
    exactly as rule (c) already did; (b) an earlier prototype considered
    recursively inlining a verified test's own private-helper calls rather
    than blocking the test outright, and was rejected after the real
    `heapq` fixture (whose `source.js` declares **zero** `module.exports`
    names) proved this would require inlining arbitrarily deep reference
    implementation logic -- this rejection **still stands** for genuine
    helper *functions* (a transitive safety-closure over a helper's own
    calls remains unsafe, since a private production helper that only
    calls builtins would be indistinguishable from a safe test helper), but
    rules (d)/(e) recover the specific, provably-safe sub-cases of that
    same `heapq`-style blocker (a target-independently-exported name, or a
    pure inert data literal) without ever inlining implementation logic;
    (c) real per-project extraction coverage observed against the official
    artifact during EARLIER development (rules (a)-(c) only, before this
    revision) ranged from 0/N (e.g. `heapq`, `colorsys`, `html`, `toml`) to
    10/10 (`rbt`) -- a genuine private-helper reference that resolves under
    none of (a)-(e) still cannot be safely extracted, and this harness
    would rather under-count `validated_tests_executed` (renamed from
    `validated_tests_total`; `validated_tests_expected` always retains the
    full CSV count regardless, so the shortfall is visible in
    `validated_tests_not_executed` rather than silently disappearing) than
    smuggle in reference implementation code to inflate it; (d) rule (d)'s
    actual effect on any specific project's coverage is run-dependent (it
    depends on what CodeWeaver's own translation happens to export under
    the exact blocking identifier's name) and was therefore deliberately
    NOT restated as a new guaranteed per-project number in the table above
    -- only unit-tested against synthetic fixtures modeling the real
    `heapq` no-`module.exports` shape. This was verified against the real
    official artifact (all 8 SKEL projects, rules (a)-(c) only) during
    EARLIER development of this adapter, reproducing the exact coverage
    figures in the table above, and against a real `node` execution of the
    generated harness (both throw-based and return-value-based pass/fail
    detection, and the `require()`-load-failure path) -- but this
    end-to-end `node` proof was a manual, one-off verification step, not
    itself a committed automated test (the automated suite instead
    exercises the same production code paths via injected fake command
    runners, consistent with how every other adapter in this harness is
    tested, never depending on a real Node.js/toolchain installation). Rules
    (d)/(e) themselves were similarly verified only via synthetic
    fixture-based unit tests plus an offline `tree-sitter-javascript`
    grammar probe (confirming exact node types/field names for unary
    numeric literals, array/object literals, shorthand vs. pair properties,
    template-string substitution, and `module.exports.NAME =`/
    `exports.NAME =` member-assignment forms) -- not re-run against the
    real official artifact end-to-end in this sandbox.
15. **The paper's TPR is `passed/expected`, not `passed/executed`, in both
    Table 1 and Figure 7.** See
    [Expected vs. executed](#expected-vs-executed-the-papers-tpr-denominator)
    for the full mechanism (`validated_tests_expected`/`_executed`/
    `_not_executed`, `compute_paper_pass_rate`, and the SUM-based
    `paper_equivalent_pass_rate` aggregation). Two scope points worth
    `collect_run` computes `validated_tests_pass_rate` identically for every
    variant, and `compute_ablation_metrics` consumes that field directly.
    The translated-test passed/executed rate remains separately available
    for diagnostics but never backs either paper-facing TPR.

16. **CRUST's own `validated_tests_expected` denominator is itself split
    into native-vs-paper-aligned inputs, plus a binary-assertion-harness
    execution fix.** A naive, static `#[test]`-attribute regex count over a
    CRUST scaffold (`validated_tests_expected_native`) is known to disagree
    with the paper's own hand-curated denominator for real projects, in
    both directions (`2dpartint`: paper 6 vs. native 8; `holdem-odds`: paper
    22 vs. native 24), and `libfor`'s sole oracle
    (`rust/src/bin/test.rs`) has **zero** `#[test]` attributes at all --
    it is a binary assertion harness (a plain `fn main()` whose own process
    exit code is the verdict), which plain `cargo test` never
    discovers/runs, so without this fix `libfor` would silently report a
    measured `0` rather than the paper's expected `1`. See
    [CRUST's native-vs-paper-aligned expected-test-count](#crusts-native-vs-paper-aligned-expected-test-count)
    for the full mechanism (`validated_tests_expected_native/_paper/_source`,
    `crust_binary_test_harnesses`/`crust_run_binary_test_harnesses`,
    `crust_combine_expected`, the new `--crust-paper-expected-tests` flag).
    The full, authoritative 100-project CRUST mapping is **not** shipped as
    machine-readable data in any input available to this harness in this
    sandbox -- only the three projects named above have publicly-known
    exact figures -- so this fix never hardcodes a fabricated per-project
    table; `--crust-paper-expected-tests` must be supplied (pointing at the
    real `results.xlsx` or an operator-curated reference file) to unlock the
    paper-aligned denominator at all, and every field degrades honestly
    (native fallback, or `Status.UNAVAILABLE`) when it is omitted.
17. **Oxidizer's idiomatic-identifier-rewrite is a best-effort,
    Oxidizer-only mitigation.** See
    [Oxidizer's idiomatic-identifier-rewrite](#oxidizers-idiomatic-identifier-rewrite-compile-failure-vs-behavioral-failure)
    for the full mechanism (`read_name_mapping`, `rust_source_code_mask`,
    `rewrite_identifiers_with_name_mapping`, `extract_compiler_error_snippet`).
    It is designed against the real CodeWeaver core's own `plan.json`
    `name_mapping` schema and is covered by synthetic regressions plus live
    official-artifact evaluation. In particular, the real
    `oxidizer__gohistogram` oracle's local `test_data.rs` fixture, associated
    constructors, and trait methods compile under the adapter, and
    cargo-tarpaulin measures its developer coverage. If a real run's
    `plan.json` never populates `name_mapping` (e.g.
    an older CodeWeaver version, or a project where the Planner used a
    different artifact shape), `read_name_mapping` returns `{}` and this
    mitigation is a strict no-op -- the fallback (an honest, non-fabricated
    compile-failure reason, never `failed == expected`) still applies
    unconditionally regardless.

## Troubleshooting

- **"acquire.py refuses to extract on this machine."** You are on native
  Windows. Use WSL (or any Linux environment) -- the official artifact's
  member filenames are documented to contain `*`, which native Windows
  cannot represent. `--force-native-windows` exists but is not recommended;
  it bypasses a real safety check, not a false positive.
- **"manifest.py reports a count mismatch (not exactly 100/6/4/8/118)."**
  Run `manifest.py --probe --artifact-root <root>` to print the real
  top-level directory tree. If `--artifact-root` points above
  `data/tool_projects` (or another nested nesting), `resolve_project_root`
  should already auto-descend into it (see
  [assumption 1](#integration-assumptions-and-known-limitations)); if the
  real tree still doesn't match, adjust `experiment.toml`'s
  `[datasets.*].dir_candidates` (and sub-path candidates) or
  `[artifact].project_root_subdir_candidates` accordingly -- a config edit,
  never a code change.
- **"CRUST's `validated_tests_expected`/TPR doesn't match the paper's own
  number for a project."** This is expected without
  `--crust-paper-expected-tests`: `validated_tests_expected_source` will
  read `native` (a best-effort static `#[test]`-attribute count, known to
  disagree with the paper in both directions for real projects -- see
  [CRUST's native-vs-paper-aligned expected-test-count](#crusts-native-vs-paper-aligned-expected-test-count)).
  Pass `--crust-paper-expected-tests <results.xlsx-or-json-or-csv>` to
  supply the paper's own authoritative per-project figure; check stderr for
  a `[collect] WARNING` line if the flag was supplied but not applied (a
  bad path, unreadable file, or unmatched sheet/columns).
- **"figure/PDF files are missing, only a `*.pdf.unavailable.txt` sibling
  exists."** `reportlab`/`matplotlib` are not installed in this
  environment; every stage still writes complete CSV/JSON data regardless.
  Install the optional dependency and re-run that stage to get real PDFs.
- **"`report.py` says INCOMPLETE even though I ran everything."** Check
  `reproducibility_report.md`'s "Completion Verdict" section -- it lists
  the exact itemized reason(s) (wrong project count, missing/partial
  `analysis_provenance.json`, a schema validation failure, or a provenance
  inconsistency). `report.py` never claims completion partially; every
  reason it prints is actionable on its own.
