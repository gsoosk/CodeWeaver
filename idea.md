# CodeWeaver — Project Idea & Evaluation Plan (for the research/experiment agent)

> **Purpose of this document.** This is a complete, self-contained brief for an
> autonomous research agent tasked with **running the experiments** that evaluate
> **CodeWeaver**. It describes (1) what CodeWeaver is and how it works, (2) its
> current implementation status, (3) how it is positioned against prior work, and
> (4) a concrete **evaluation plan** that mirrors the evaluation sections of the
> most relevant prior papers — **ReCodeAgent, AlphaTrans, RepoTransBench, and
> CRUST-Bench**.
>
> **Scope constraint (do not change the idea).** The CodeWeaver design below is
> **fixed**. Your job is **not** to redesign CodeWeaver or add features — it is to
> **evaluate the system as it exists** by designing/running experiments,
> collecting metrics, running baselines and ablations, and producing the tables,
> figures, and analysis that a paper's evaluation section needs. If something in
> the system appears missing for an experiment, **instrument or measure around
> it**; do not alter the core algorithm or add capabilities.

Repository: `github.com/gsoosk/CodeWeaver` (branch `main`). All paths below are
relative to the repo root unless stated otherwise.

---

## 1. What CodeWeaver is

**CodeWeaver is a general-purpose, language-agnostic multi-agent framework for
LLM-driven whole-repository code translation/migration.** Given a source
repository and a target language (plus a short project brief and validation
commands, all in a config file), CodeWeaver autonomously translates the entire
repository and validates it against the project's own tests, terminating only when
the translation is **verified complete**.

It is an open-stack **generalization of ReCodeAgent** (Ibrahimzada, Paulsen,
Kroening, Jabbarvand, arXiv:2604.07341), reimplemented on **GitHub Copilot CLI**
custom agents orchestrated by a deterministic **Apache Burr** state machine, and
extended with three things ReCodeAgent does not describe: milestone-incremental
test gates, a fixed two-layer validation oracle, and a **parity-completeness
loop**.

### 1.1 Core design principle

**Separate deterministic control flow from non-deterministic agent reasoning.**
The Burr state machine decides *which agent runs next, when to loop, and when to
halt* — this is pure Python and **never calls an LLM**. All reasoning and code
editing is done by six specialized Copilot-CLI agents invoked *inside* the state
machine's action nodes. This yields reproducibility, crash-resume, and guaranteed
milestone/parity progression regardless of noisy individual agent outputs.

---

## 2. How CodeWeaver works

### 2.1 The pipeline (Burr state graph)

```
analyze ─▶ scope ─▶ plan ─▶ select_milestone ─▶ translate ─▶ validate ─▶ parity ─▶ terminal
             ▲                     ▲                 ▲            │           │
             │ parity incomplete   │ next milestone  │ repair     │           │
             │ (append milestones) │ (passed & more) │ (fail &    ▼           ▼
             └─────────────────────┴─────────────────┴  iter<max) ┘   complete / out of rounds
```

Transitions (see `codeweaver/app.py`):
- `translate → validate` always.
- `validate → translate` when `not milestone_passed and iter_count < max_iter` (repair).
- `validate → select_milestone` when `milestone_passed and milestone_idx < last_idx` (advance).
- `validate → parity` when `milestone_passed and milestone_idx >= last_idx` (all milestones done).
- `parity → scope` when `not parity_complete and parity_round < max_parity_rounds` (re-plan gaps).
- `parity → terminal` when `parity_complete` or rounds exhausted.
- `validate → terminal` if the repair budget is exhausted (gave up).

### 2.2 The six agents (`agents/*.agent.md`)

| Agent | Role | Reads → Writes (files in the pipeline dir) |
|---|---|---|
| **Analyzer** | Research the source repo; design the target (structure, dependency→target-library mapping, unit-test strategy). | source → `analysis.md` |
| **Scoper** (milestone generator) | Decompose the port into an ordered, **cumulative** milestone matrix (skeleton → feature slices → golden). On a parity re-entry, **append** milestones for the reported gaps. | `analysis.md` / `parity.json` → `milestones.json` |
| **Planner** | Fragment extraction (translation units), one-to-one name mapping, a **compilable skeleton** with mock/test seams, a dependency-aware plan. | `analysis.md` → `plan.json` + skeleton on disk |
| **Translator** | Implement the current milestone's code + translate/add its unit tests; in **repair mode**, fix exactly the failures the Validator reported. | `plan.json` / `report.json` → working copy |
| **Validator** | Run the two validation layers; write the authoritative combined verdict (`passed` iff both layers pass) with per-failure repair hints. | runs `unit_test` + `validate` → `report.json` |
| **Parity Verifier** | Comprehensive component-by-component comparison of source vs. translation; decide COMPLETE/INCOMPLETE and list any untranslated/stubbed components with suggested milestones. | source + working copy → `parity.json` |

Agents run via `copilot -p <prompt> --agent NAME --model <model> --reasoning-effort
<effort> --allow-all --no-ask-user --output-format json`. Default model
`claude-opus-4.8`; per-agent effort: analyzer/scoper/planner/translator = `max`,
validator = `high`, parity = `max` (overridable via config or `CODEWEAVER_MODEL` /
`CODEWEAVER_EFFORT`).

### 2.3 Key mechanisms (the contribution surface to evaluate)

1. **Milestone-incremental translation with cumulative test gates.** Work is sliced
   into ordered milestones. A milestone's gate is **cumulative**: it must pass its
   own tests **and** every earlier milestone's tests (regression safety). Gates are
   rendered from a configurable `gate_template` (e.g. pytest `-k`, `cargo test
   <names>`, `python -m unittest <selectors>`).
2. **Two-layer validation.** A **fast, mocked unit-test layer** for cheap repair
   iterations, plus a **fixed, authoritative end-to-end oracle** (the project's own
   tests). The oracle is **never modified or regenerated** by any agent. A milestone
   passes only if **both** layers pass. (In simple projects the two commands may
   coincide, e.g. `cargo test`; the distinction is the *fixed-oracle* invariant.)
3. **Bounded translate→validate→repair loop.** Per-milestone repair is capped by
   `max_iter`; exhausting it "gives up" that milestone rather than looping forever.
4. **Parity-completeness loop.** After all milestones pass, the Parity Verifier
   checks the *whole* translation against the source. If incomplete, the Scoper
   appends milestones for the gaps and the pipeline repeats. **The run terminates
   successfully only when parity is verified complete** (bounded by
   `max_parity_rounds`). This converts "the tests we ran pass" into "**every
   component is translated**."
5. **Deterministic, crash-resumable orchestration.** State persists to SQLite after
   every action; re-running with the same `--app-id` resumes exactly where it
   stopped. Control-flow transitions are pure Python.

### 2.4 State schema (`codeweaver/state.py`)

`milestone_idx`, `num_milestones`, `last_idx`, `iter_count`, `max_iter`,
`milestone_passed`, `report`, `analysis_done`, `milestones_done`, `plan_done`,
`history` (append-only `{milestone, iter, passed}`), `parity_round`,
`max_parity_rounds`, `parity_complete`, `parity_report`, `done`, `last_agent`.
These are the **primary instrumentation source** for process/efficiency metrics
(see §5.4).

### 2.5 Configuration (`codeweaver.toml`)

A run is fully described by one config (TOML/JSON/YAML). Sections:
`[project]` (name/slug), `[translation]` (`source_language`, `target_language`,
`brief`/`brief_file`), `[paths]` (`source_dir`, `reference_dirs`,
`immutable_input`, `working_copy`, `pipeline_dir`, artifact names),
`[commands]` (`build_check`, `unit_test`, `validate` — shell commands the agents
run; support `{gate}`/`{milestone}`), `[validation]` (`gate_template`),
`[model]` (`default`, `effort_default`, per-agent `effort`),
`[execution]` (`max_iter`, `parity_check`, `max_parity_rounds`, `db_path`,
`agent_timeout`), and optional `[[milestones]]` (omit to auto-generate).
Full reference: `docs/config.md`.

---

## 3. Current implementation status

- **Package** `codeweaver/`: `config`, `milestones`, `prompts`, `copilot`, `state`,
  `actions`, `app`, `mock`, `cli`. CLI: `codeweaver run|check|milestones|
  install-agents|init`.
- **Agents** `agents/`: analyzer, scoper, planner, translator, validator, parity.
- **Offline mock harness** (`codeweaver check`, `CODEWEAVER_MOCK=1`): drives the
  full graph without Copilot; scriptable failures/crash/parity. Verifies happy
  path, repair loop, budget exhaustion, cross-process crash-resume, and the parity
  loop — all passing. **Use this to validate experiment harnesses cheaply before
  spending on real runs.**
- **Examples** (`examples/`), each with a config, brief, and setup where needed:
  - `minimal/` — tiny Python→Rust library (drives `codeweaver check`).
  - `auto-milestones/` — Python→Rust with no declared milestones (scope generates them).
  - `xcvrd/` — SONiC `xcvrd` daemon **Python→Rust** (thick PyO3 HAL + swss-common,
    DUT black-box oracle) — reproduces the original recodeAgent use case as config + brief.
  - `crust-bench/` — **C→safe-Rust** on CRUST-Bench (arXiv:2504.15254), **retargetable
    to any of the 100 projects** via `setup.ps1/.sh`; auto-milestones + parity; `cargo test` oracle.
  - `commons-validator/` — Apache Commons Validator `routines` **Java→Python**;
    auto-milestones + parity; translated `unittest` oracle.
- **Docs**: `README.md`, `docs/architecture.md`, `docs/config.md`,
  `docs/related-work.md` (the literature review).
- **Local datasets already staged** on the experiment machine:
  `~/Desktop/_cw_local/CRUST-bench` (extracted CBench + RBench),
  `~/Desktop/_cw_local/commons-validator`, `~/Desktop/_cw_local/HakiCC`.

**Toolchains present locally:** Python 3.12, Node 24, Rust/cargo 1.96. **Java/Go
are NOT installed** — experiments requiring a JDK/Go toolchain must install it or
run on a machine that has it.

---

## 4. Positioning vs. prior work (context for baselines)

Full survey: `docs/related-work.md`. The systems most relevant as **baselines /
comparison points**:

- **ReCodeAgent** (2604.07341) — *direct predecessor*; PL-agnostic multi-agent
  repo translation+validation. **Primary comparison.**
- **AlphaTrans** (2410.24117) — neuro-symbolic compositional Java→Python repo
  translation with reverse-call-graph ordering + multi-level validation.
- **RepoTransBench** (2412.17744) — repository-level multilingual translation
  **benchmark** (+ RepoTransAgent baseline).
- **CRUST-Bench** (2504.15254) — C→safe-Rust **benchmark** (interface + tests).
- **CodePlan** (2309.12499) — repo-level LLM planning for code edits/migration.
- Function/one-shot: **TransCoder** (2006.03511), **TransCoder-ST** (2110.06773).
- C→Rust point systems: **VERT** (2404.18852), **Syzygy** (2412.14234),
  **SACTOR** (2503.12511).
- Agentic-SE reference frame: **SWE-agent** (2405.15793), **Agentless** (2407.01489),
  **AutoCodeRover** (2404.05427), **MASAI** (2406.11638).

**CodeWeaver's evaluable novelties** (what the experiments must isolate):
(N1) fixed two-layer oracle; (N2) milestone-incremental cumulative test gates;
(N3) **parity-completeness loop**; (N4) deterministic Burr orchestration
(reproducibility/resume); (N5) config-driven language-agnosticism + auto-milestones.

---

## 5. Evaluation plan

This section mirrors the evaluation designs of the prior papers so results are
directly comparable. **Reproduce their metrics and protocols where possible.**

### 5.0 Reference evaluation designs to imitate

| Paper | Benchmark | Scale | Language pairs | Primary metrics | Notable protocol |
|---|---|---|---|---|---|
| **ReCodeAgent** | own 118 real-world projects | avg 1,975 LoC, 43 translation units/project | C→Rust, Go→Rust, Java→Python, Python→JavaScript (6 PLs) | **ground-truth test pass rate** (+60.8% vs. baselines); **cost $/project** (~$15.3); process/trajectory efficiency; **multi- vs single-agent ablation** (−40.4% pass, +28% trajectory length) | compares vs. 4 neuro-symbolic/agentic baselines; process-centric trajectory analysis |
| **AlphaTrans** | 10 real Java→Python projects | 836 classes, 8,575 methods, 2,719 tests | Java→Python | **syntactic correctness** (96.4%), **runtime correctness** (27.03%), **functional correctness** (25.14%); **avg time/project** (~34h) | 3-level validation: parse → GraalVM mixed-exec → unit tests; reverse call-graph fragment order |
| **RepoTransBench** | 1,897 repos | real-world, executable tests | 13 pairs | **success rate** (build+tests pass; best method ~32.8%) | dynamic→static much harder than static→dynamic; per-error-class analysis |
| **CRUST-Bench** | 100 C repos | interface + tests each | C→safe-Rust | **interface conformance** ∧ **compiles** ∧ **all tests pass** (best single-shot o1 = 15/100) | provides safe-Rust interface as spec; single-shot & self-repair settings |

Standard code-translation metric to adopt as the **primary** measure:
**Computational Accuracy (CA) / functional correctness = fraction of translation
units (and whole projects) whose translated code builds and passes the project's
ground-truth tests**, reported as **pass@1** (and pass@k if you run k samples).
De-emphasize BLEU/CodeBLEU (weak proxies), but you may report them for continuity.

### 5.1 Research questions

- **RQ1 (Effectiveness).** How does CodeWeaver compare to single-shot LLM
  translation and to SOTA agentic/neuro-symbolic systems (ReCodeAgent, AlphaTrans,
  RepoTransAgent) on **functional correctness** across language pairs and project
  sizes?
- **RQ2 (Completeness — the headline claim).** Does the **parity-completeness loop**
  measurably increase translation **completeness** (fraction of source components
  with a faithful, non-stub target counterpart) and reduce "silently-unfinished"
  ports, versus the same system with parity disabled and versus systems that lack
  such a check?
- **RQ3 (Component contributions).** How much does each mechanism (N1–N4) contribute?
  (Ablations in §5.5.)
- **RQ4 (Efficiency & cost).** What are the **cost ($), wall-clock time, #LLM calls,
  tokens**, and **trajectory efficiency** (repair iterations, parity rounds,
  milestones), and how do they trade off against correctness vs. baselines?
- **RQ5 (Generality).** How consistently does CodeWeaver perform across **many
  language pairs** and project scales (small libs → large multi-file repos)?
- **RQ6 (Reliability/reproducibility).** Does deterministic orchestration deliver
  **crash-resume correctness** and **low run-to-run variance** relative to
  free-form agent baselines?

### 5.2 Benchmarks / datasets

Run on the union below; prioritize the ones whose toolchains are available locally.

1. **CRUST-Bench** (C→Rust, 100 projects). Local: `~/Desktop/_cw_local/CRUST-bench`.
   Example harness ready: `examples/crust-bench` (`setup.ps1/.sh <project>`).
   Rust/cargo present → **runnable now**. Report per-project build+test pass and
   interface conformance (matches CRUST-Bench's own metric).
2. **RepoTransBench** (13 pairs, 1,897 repos). Clone
   `github.com/DeepSoftwareAnalytics/RepoTransBench`. Use its executable test
   harness for the ground-truth oracle. Sample a stratified subset (by pair and
   size) if full-scale is too costly; **report the sampling protocol**.
3. **AlphaTrans set** (10 Java→Python projects). Obtain from the AlphaTrans
   artifact/repo. Requires **JDK + GraalVM** (install). Enables a *head-to-head* on
   the exact projects AlphaTrans reports.
4. **ReCodeAgent set** (118 projects, 4 pairs). If the authors' artifact is
   available, use it for the **primary head-to-head**; otherwise compare against
   ReCodeAgent's **reported numbers** on the overlapping pairs and construct a
   comparable set from public repos following ReCodeAgent's selection criteria
   (compiles with standard toolchain, has tests, non-GUI, portable).
5. **CodeWeaver's own examples** as qualitative/case studies: `xcvrd`
   (Python→Rust systems daemon), `commons-validator` (Java→Python).

For each project record: language pair, LoC, #files, #translation units (functions/
methods/classes), #ground-truth tests, test coverage.

### 5.3 Baselines

- **B0 — Single-shot LLM translation.** Same model (`claude-opus-4.8`), whole repo
  (or file-by-file) translated in one pass, no iteration. Lower bound.
- **B1 — Single-agent agentic translation.** One general Copilot-CLI agent with the
  same tools/budget but **no role decomposition, no milestones, no parity** (this
  doubles as ablation A4). Mirrors ReCodeAgent's single-agent ablation.
- **B2 — ReCodeAgent.** Run the authors' artifact if available; else cite reported
  numbers on overlapping pairs. **Primary comparison.**
- **B3 — AlphaTrans.** On the 10 Java→Python projects (its home turf).
- **B4 — RepoTransAgent** (the baseline shipped with RepoTransBench).
- **B5 — C→Rust point systems** (VERT / Syzygy / SACTOR) on CRUST-Bench, via
  reported numbers or artifacts, for the C→Rust slice.
- **B6 — Agentless-style non-agentic pipeline** (localize→translate→validate),
  optional, as a "do you need agency?" control.

Hold **model, temperature/effort, and per-project budget fixed** across CodeWeaver
and the agentic baselines (B0/B1/B6) for fair comparison.

### 5.4 Metrics (collect all; map to RQs)

**Correctness (RQ1, RQ5):**
- **Functional correctness / CA**: % translation units and % whole projects that
  **build ∧ pass ground-truth tests** (pass@1; pass@k if k>1 runs). Primary.
- **Build/compile success rate** (separately from tests).
- **Interface conformance** (CRUST-Bench only): matches the provided safe-Rust interface.
- (Optional continuity) CodeBLEU / exact-match.

**Completeness (RQ2 — headline):**
- **Parity/completeness rate**: fraction of source components (functions, methods,
  classes/structs, public API) that have a **faithful, non-stub** target counterpart.
  Measure two ways for credibility: (a) CodeWeaver's own `parity.json`, and (b) an
  **independent** static check (count remaining `unimplemented!()`/`todo!()`/`pass`/
  `NotImplementedError`/empty bodies + a symbol-level source↔target diff), so the
  metric is not self-reported.
- **"Silently-unfinished" rate**: projects reported as done by a system whose
  translation still omits/stubs ≥1 in-scope component. Compare CodeWeaver
  (parity on) vs. baselines/ablations.

**Cost & efficiency (RQ4):**
- **$ per project** (Copilot premium requests / token cost), **#LLM calls**,
  **#tokens** (prompt+completion), **wall-clock time per project**.
- From state/telemetry: **#milestones**, **repair iterations per milestone**,
  **#parity rounds**, **total trajectory length** (agent invocations), and
  **give-up rate** (milestones that exhausted `max_iter`).

**Reliability (RQ6):**
- **Crash-resume correctness**: kill mid-run, resume with same `--app-id`, verify
  identical final state/outcome vs. an uninterrupted run.
- **Run-to-run variance**: std of correctness/cost across N≥3 seeds/runs; compare
  to a free-form single-agent baseline's variance.

Data sources: `pipeline/report.json`, `pipeline/parity.json`,
`pipeline/milestones.json`, Burr `history`/state (SQLite), Copilot `--output-format
json` usage events (files_modified, lines +/-, premium_requests, duration), and the
`pipeline/logs/*.jsonl` transcripts.

### 5.5 Ablations (RQ3) — isolate each novelty

Toggle **one** thing at a time; keep everything else fixed.

| Ablation | Change | Isolates |
|---|---|---|
| **A1 −parity** | `parity_check = false` | N3: value of the completeness loop (compare completeness & silently-unfinished rate vs. full system) |
| **A2 −milestones** | one milestone = whole repo (`[[milestones]]` = single "M0: full port") | N2: value of incremental cumulative gates |
| **A3 −two-layer** | run only the e2e oracle (drop the mocked unit layer), or only unit | N1: value of the fast layer (cost/iterations) & the fixed-oracle invariant |
| **A4 single-agent** | collapse roles into one agent (= B1) | N4/architecture: multi- vs single-agent (mirror ReCodeAgent's ablation) |
| **A5 −auto-milestones** | declared vs. scope-generated milestones | value of the Scoper |
| **A6 model/effort** | swap `default` model & `effort` (e.g. opus↔sonnet↔gpt-5; max↔high↔medium) | sensitivity to backbone model/effort |
| **A7 budgets** | vary `max_iter` ∈ {1,3,6}, `max_parity_rounds` ∈ {1,3,5} | sensitivity/robustness of the loops; cost-quality trade-off |

### 5.6 Experimental protocol

- **Model:** fix `claude-opus-4.8` (per-agent efforts as shipped) for main results;
  A6 varies it. Record exact model/version and CLI version.
- **Repetitions:** ≥3 runs per (system × benchmark-project) for variance; report
  **mean ± std** and **pass@1**. Use distinct `--app-id`s.
- **Budgets/caps:** set `agent_timeout` and a per-project wall-clock cap; record
  time-outs as failures. Keep `max_iter`/`max_parity_rounds` fixed for main results.
- **Isolation:** run each project in a clean working copy; never let the agent read
  the ground-truth target or modify the oracle tests (enforce via the read-only
  boundaries already in the briefs; **verify** no oracle files changed via git diff
  of the reference dirs after each run).
- **Statistics:** Wilcoxon signed-rank (paired, per-project) or bootstrap CIs for
  CodeWeaver vs. each baseline on correctness/completeness; report effect sizes.
- **Fairness:** identical model/effort/budget for all agentic systems; document any
  benchmark-specific setup (toolchain versions, container images).
- **Validate the harness cheaply first:** run everything end-to-end under
  `CODEWEAVER_MOCK=1` (`codeweaver check --config <cfg>`) to confirm metric
  collection, resume, and parity accounting before spending on real LLM runs.

### 5.7 Deliverables (tables & figures to produce)

1. **Main results table** — functional correctness (pass@1) per system × language
   pair, with cost and time columns (mirrors ReCodeAgent Table + AlphaTrans
   correctness levels + RepoTransBench success rate + CRUST-Bench pass count).
2. **Completeness table/figure** — parity/completeness rate & silently-unfinished
   rate: CodeWeaver (parity on) vs. A1 (parity off) vs. baselines. **This is the
   headline result for N3.**
3. **Ablation table** — A1–A7 deltas on correctness, completeness, cost, trajectory.
4. **Efficiency plots** — cost vs. correctness scatter (Pareto); trajectory length
   & repair iterations distributions; parity-rounds histogram.
5. **Scaling analysis** — correctness vs. project size (LoC / #translation units).
6. **Reliability results** — crash-resume equivalence; variance comparison.
7. **Qualitative case studies** — `xcvrd` and `commons-validator`: what milestones
   were generated, where repair/parity caught gaps, representative failures.
8. **Error taxonomy** — categorize failures (compile, type/ownership, semantic
   drift, missing component) à la *Lost in Translation* / RepoTransBench.

### 5.8 How to run CodeWeaver for a benchmark (operational)

```bash
# 0. (once) install agents
python -m codeweaver install-agents

# 1. Prepare a config for a benchmark project (examples ship setup scripts)
#    CRUST-Bench (C->Rust), runnable now:
cd examples/crust-bench && ./setup.ps1 -Project <proj> && cd ../..
#    Commons Validator (Java->Python):
cd examples/commons-validator && ./setup.ps1 && cd ../..
#    For a new benchmark: `codeweaver init` then edit codeweaver.toml (see docs/config.md).

# 2. Dry-run the orchestration offline (no cost) to validate the harness
python -m codeweaver check --config <path>/codeweaver.toml

# 3. Real run (records report.json, parity.json, milestones.json, logs, state)
python -m codeweaver run --config <path>/codeweaver.toml --app-id <system>-<proj>-<seed>

# 4. Resume test (RQ6): kill during a run, then re-run the SAME command; compare outcomes.

# 5. Collect metrics from pipeline/{report,parity,milestones}.json, the SQLite
#    state (history), and pipeline/logs/*.jsonl (Copilot usage: premium_requests,
#    duration, files_modified). Independently recompute completeness (§5.4).
```

For **baselines** B0/B1/B6, drive the same model via the Copilot CLI with a reduced
scaffold (single prompt / single agent / non-agentic pipeline) and the **same
oracle command** for scoring, so only the method differs.

### 5.9 Threats to validity (address in the write-up)

- **Benchmark leakage / model familiarity** with public repos → prefer recent/less
  common projects; note training-cutoff caveats.
- **Oracle quality** — ground-truth tests may under-specify behavior (cf. SWE-Bench+);
  report coverage and treat "tests pass" as necessary-not-sufficient.
- **Self-reported completeness** — always corroborate `parity.json` with the
  independent static completeness check (§5.4).
- **Cost/nondeterminism of LLMs** — fix model/effort, run multiple seeds, report
  variance; note CodeWeaver's *orchestration* is deterministic but agent outputs
  are not.
- **Toolchain availability** — JDK/Go/GraalVM must be installed for the relevant
  pairs; pin versions and use containers.
- **Fairness to baselines** — equalize model/budget; run baselines yourself where
  artifacts exist rather than only citing paper numbers.

---

## 6. Concrete task list for the research agent

1. **Reproduce the harness** end-to-end under `CODEWEAVER_MOCK=1` on all example
   configs; confirm metric extraction + resume accounting work.
2. **Stand up toolchains**: ensure Rust (present), install JDK (+GraalVM for
   AlphaTrans comparison), Node (present), Go if targeting Go pairs; containerize.
3. **CRUST-Bench (C→Rust)** — run CodeWeaver on all 100 (or a documented stratified
   subset); collect correctness + interface conformance + completeness + cost.
   Compare to CRUST-Bench reported single-shot and to SACTOR/VERT/Syzygy numbers.
4. **RepoTransBench** — run on a stratified subset across the 13 pairs; compare to
   RepoTransAgent; report success rate + error taxonomy.
5. **AlphaTrans set (Java→Python)** — head-to-head on the 10 projects; report the
   three correctness levels + time; compare to AlphaTrans.
6. **ReCodeAgent comparison** — if artifact available, head-to-head on the 4 pairs;
   else comparable-set construction + reported-number comparison. Reproduce the
   **multi- vs single-agent** ablation (A4/B1).
7. **Ablations A1–A7** on a fixed representative subset (≥15–20 projects spanning
   pairs/sizes).
8. **Reliability (RQ6)** — crash-resume equivalence + variance across ≥3 seeds.
9. **Analysis & artifacts** — produce all tables/figures in §5.7, the error
   taxonomy, and a reproducibility appendix (configs, app-ids, model/CLI versions,
   seeds, hardware, per-run logs).
10. **Write the evaluation section** structured around RQ1–RQ6, leading with the
    **completeness (parity) result** as the primary novelty, followed by
    effectiveness, ablations, efficiency, generality, and reliability.

---

## 7. Success criteria for the evaluation

The experiments should convincingly answer:
- **RQ2 first (the differentiator):** parity-on yields **higher completeness and a
  lower silently-unfinished rate** than parity-off and than baselines that lack a
  completeness check — with statistical support.
- **RQ1:** CodeWeaver is **competitive or better** on functional correctness vs.
  ReCodeAgent/AlphaTrans/single-shot across pairs, at a **documented cost**.
- **RQ3:** each novelty (N1–N4) shows a **measurable, isolated contribution**.
- **RQ4–RQ6:** cost/efficiency are reported transparently, generality holds across
  pairs/sizes, and deterministic orchestration delivers resume-correctness and
  lower variance.

Keep the CodeWeaver system **unchanged**; only instrument, measure, run baselines/
ablations by toggling existing config knobs (`parity_check`, `max_iter`,
`max_parity_rounds`, milestones declared vs. auto, model/effort), and report.
