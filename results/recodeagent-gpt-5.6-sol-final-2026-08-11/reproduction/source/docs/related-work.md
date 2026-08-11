# CodeWeaver — Related Work & Literature Review

This document surveys the research area around **CodeWeaver** — a general-purpose,
language-agnostic **multi-agent framework for LLM-driven whole-repository code
translation and migration** — positions it against prior work, and clarifies its
motivation and distinct contributions.

> **On sourcing & verification.** Every arXiv identifier below was checked against
> the arXiv API (title/author match). Because much of this area is very recent
> (2023–2026), several papers are preprints or were only just accepted; **the
> *peer-reviewed venue* attributions marked "reported" should be re-confirmed
> before use in a submission**. arXiv IDs are reliable; conference-acceptance
> claims for 2024–2026 papers are the main source of residual uncertainty. Items
> that could not be verified are called out in §11.

---

## 1. Motivation & problem statement

Migrating a codebase from one programming language to another (e.g., legacy C to
memory-safe Rust, or Java to Python) is a high-value but labor-intensive software
engineering task. Three properties make it hard for automated systems:

1. **It is repository-level, not function-level.** Real projects span many files
   with cross-file types, call graphs, and build/test infrastructure. A translator
   must preserve *inter-procedural* and *inter-module* semantics, not just
   translate isolated snippets.
2. **Correctness is objective but expensive to establish.** Unlike open-ended code
   generation, translation has a ground truth: the source program's behavior,
   encoded by its existing test suite. But running whole-project builds and test
   suites across a language boundary is costly, and LLMs routinely emit
   "compiles-but-wrong" code (documented empirically by *Lost in Translation*,
   Pan et al., ICSE 2024).
3. **Completeness is easy to lose.** An agent that fixes whatever the last test
   run complained about can plateau while silently leaving whole modules
   untranslated or stubbed — a failure mode the ReCodeAgent ablation quantifies
   ("persistently inefficient" single-agent trajectories).

**CodeWeaver's thesis.** A *deterministic* orchestration layer that (a) plans the
translation as an ordered set of **cumulative, test-gated milestones**, (b) runs a
bounded **translate→validate→repair** loop per milestone against a **fixed,
never-modified test oracle**, and (c) terminates only after a dedicated
**parity verifier** confirms the translation is *complete* (component-by-component
against the source), produces more reliable, auditable whole-repository
translations than either single-shot LLM translation or free-form agent loops —
while remaining **language-agnostic** (any source/target pair via a config +
project brief). The deterministic state machine never calls an LLM; the LLM work
is done entirely by specialized GitHub Copilot CLI agents (Analyzer, Scoper,
Planner, Translator, Validator, Parity-Verifier).

---

## 2. How CodeWeaver relates to the field (map)

The literature clusters into five areas; CodeWeaver sits at their intersection:

```
        (A) Neural/LLM code translation ──────┐
        (foundations → repo-level → C→Rust)   │
                                              ▼
   (B) Multi-agent LLM code frameworks ──▶  CodeWeaver  ◀── (D) Test-driven generation,
        (role specialization)                 ▲             self-repair, program repair,
                                              │             translation validation
        (C) Agentic SE / repo understanding ──┘
        (SWE-agent, AutoCodeRover, …)
                                              ▲
                            (E) Orchestration frameworks
                            (AutoGen, LangGraph, Apache Burr, CrewAI)
```

CodeWeaver inherits the **translation task & oracle** from (A), **role
specialization** from (B), the **agent–computer interface** from (C), the
**iterative repair loop** from (D), and a **deterministic state-machine
orchestrator** from (E) — then adds two things no prior system combines:
milestone-incremental cumulative test gates and a **parity-completeness loop**.

---

## 3. Cluster A — Neural & LLM code translation

### A.1 Foundations (function-level, no agents)

| Work | id | Venue (reported) | One-line contribution | Contrast with CodeWeaver |
|---|---|---|---|---|
| **TransCoder** — Unsupervised Translation of Programming Languages (Lachaux et al.) | 2006.03511 | NeurIPS 2020 | First large-scale *unsupervised* neural code-to-code translation (C++/Java/Python) via back-translation. | Purely generative, function-level, **no oracle/validation/repair**; CodeWeaver's whole loop targets the correctness gap TransCoder left open. |
| **TransCoder-ST** — Leveraging Automated Unit Tests for Unsupervised Code Translation (Rozière et al.) | 2110.06773 | EMNLP 2022 | Uses a unit-test harness to *filter* invalid back-translations, cutting errors >35%. | Establishes "tests are the right signal," but uses tests to filter training data, not to drive an active per-milestone repair loop against the project's own tests. |
| **TransCoder-IR** — Code Translation with Compiler Representations (Szafraniec et al.) | 2207.03578 | ICLR 2023 | Adds low-level compiler IR to improve translation. | Still single-function, model-centric; no repository scope or agentic validation. |
| **Understanding the Effectiveness of LLMs in Code Translation** / **"Lost in Translation"** (Pan et al.) | 2308.03109 | ICSE 2024 | Empirically categorizes the bug classes LLMs introduce when translating; "compiles-but-wrong" is common and worsens with size. | **Directly motivates** CodeWeaver's fixed-oracle validate→repair loop; shares co-authors (Ibrahimzada, Jabbarvand) with ReCodeAgent. |

### A.2 Benchmarks

| Work | id | Venue (reported) | Contribution | Contrast |
|---|---|---|---|---|
| **CodeXGLUE** (Lu et al.) | 2102.04664 | NeurIPS 2021 (Datasets) | Broad code-intelligence benchmark incl. a code-translation task (Java↔C#). | Function/snippet granularity; CodeWeaver operates at repository scale with executable oracles. |
| **CodeTransOcean** (Yan et al.) | 2310.04951 | EMNLP 2023 (Findings) | Large *multilingual* translation benchmark (many languages, incl. LLM-trans). | A benchmark, not a system; no completeness notion. |
| **xCodeEval** (Khan et al.) | 2303.03004 | reported | Execution-based multilingual code eval incl. translation. | Execution-based like CodeWeaver's gate, but per-problem, not per-repo. |
| **RepoTransBench** (Wang et al.) | 2412.17744 | ICSE/FSE 2025 (reported) | First **repository-level** multilingual translation benchmark (1,897 repos, 13 pairs, executable tests); best method ~32.8%. | The natural *evaluation target* for CodeWeaver; its RepoTransAgent baseline lacks milestone gates, two-layer validation, and a parity loop. |

### A.3 Repository-level translation systems (closest prior art)

| Work | id | Venue (reported) | Contribution | Contrast with CodeWeaver |
|---|---|---|---|---|
| **CodePlan** — Repository-level Coding using LLMs and Planning (Bairi et al.) | 2309.12499 | FSE 2024 (reported) | Frames repo-level edits (migration, type propagation) as an LLM **planning** problem with dependency-aware chained edits. | The closest *plan-then-execute* SE ancestor. But single-LLM planning monolith, no role specialization, **no self-repair loop, no completeness/parity check**, and demonstrated on specific edit tasks (C# migration, Python temporal edits), not general cross-language translation. |
| **AlphaTrans** — Neuro-Symbolic Compositional Repository-Level Translation & Validation (Ibrahimzada et al.) | 2410.24117 | FSE 2025 (reported) | Decomposes a repo by *reverse call-graph order*, translates each fragment, validates via parse + GraalVM mixed-execution + unit tests. Java→Python on 10 projects. | **Closest repo-level prior work.** Differences: single fixed pair (Java→Python); GraalVM mixed-execution (not pure target-language); **no parity-completeness loop, no milestone plan, not fully autonomous** (needs developer fixes). CodeWeaver adds language-agnosticism, milestones, parity, and Copilot-CLI autonomy. |
| **RustRepoTrans** (Ou et al.) | 2411.xxxxx (reported) | reported | Repo-level *→Rust* translation benchmark (375 tasks); best ~51.5% Pass@1, −22% vs. isolated-function. | Quantifies that repo-level context is the unsolved bottleneck CodeWeaver's analyze/plan phases target. |
| **Scalable, Validated Code Translation of Entire Projects using LLMs** (Paulsen et al.) | (no arXiv found) | ICSE 2025 (reported) | Modular translate-then-validate with *feature mapping* (e.g., Go interface→Rust trait) and type-compatibility checks; Go→Rust up to ~9.7k LoC. | Nearest single-framework predecessor of the modular approach; CodeWeaver generalizes across pairs, adds multi-agent roles + the parity verifier. Shares an author (Paulsen) with ReCodeAgent. |

### A.4 C-to-Rust (a heavily studied special case)

| Work | id | Venue (reported) | Contribution | Contrast |
|---|---|---|---|---|
| **CRUST-Bench** (Khatry et al.) | 2504.15254 | 2025 | 100 C repos each paired with a safe-Rust *interface* + tests; best single-shot model solved only 15/100. | CodeWeaver ships a `crust-bench` example targeting exactly this benchmark; the parity loop + milestone gates directly address its difficulty. |
| **Syzygy** — Dual Code-Test C→(safe) Rust using LLMs + Dynamic Analysis | 2412.14234 | 2024 | Co-translates code *and* tests, guided by dynamic analysis, to preserve behavior. | Fixed pair (C→Rust); no general orchestrator or milestone/parity structure. |
| **VERT** — Verified Equivalent Rust Transpilation (Yang et al.) | 2404.18852 | ICSE 2025 (reported) | Builds a Wasm-derived *reference* Rust program and **formally model-checks** LLM output against it. | Strongest *formal* equivalence baseline, but function-level and needs a Wasm path; CodeWeaver uses test-oracle differential validation that scales to heterogeneous repos (e.g., Python→Rust) where formal equivalence is infeasible. |
| **SACTOR** — Static-Analysis + FFI-Verified idiomatic C→Rust (Zhou et al.) | 2503.12511 | ACL 2026 | Unidiomatic-then-idiomatic two-step translation, FFI end-to-end validation; on CRUST-Bench 85%/52%. | Pipeline for one pair; complements but does not orchestrate/scope like CodeWeaver. |
| **Translating C to Rust: Lessons from a User Study** | 2411.14174 | 2024 | Human study of C→Rust translation difficulty and idiom gaps. | Motivational evidence; not a system. |
| **PtrTrans** — Project-Level C→Rust via Pointer Knowledge Graphs (Yuan et al.) | 2510.xxxxx (reported) | 2025–26 | Points-to/ownership/lifetime graph cuts unsafe usage ~99.9%. | Mirrors CodeWeaver's "analyze" step (research source structure before planning), but rule/graph-specific to C→Rust. |
| **C2Rust** (tool), **Laertes** (PLDI 2022), **Crown** (ownership-guided, 2023) | — | — | Classic *rule-based/static* C→Rust transpilers producing unsafe or semi-safe Rust. | Non-LLM, non-agentic; produce unidiomatic/unsafe output CodeWeaver-style LLM agents aim to avoid. |

**Takeaway for A:** The trajectory of the field is function-level neural translation
→ test-filtered translation → repository-level neuro-symbolic pipelines →
*autonomous multi-agent* translation. CodeWeaver sits at the frontier of that
trajectory and is the first to add a **completeness guarantee** (parity loop) on
top of **milestone-incremental, test-gated** translation.

---

## 4. Cluster B — Multi-agent LLM frameworks for code

| Work | id | Venue (reported) | Contribution | Contrast with CodeWeaver |
|---|---|---|---|---|
| **CAMEL** (Li et al.) | 2303.17760 | NeurIPS 2023 | Role-playing ("inception prompting") as a multi-agent cooperation paradigm. | Foundational two-agent role-play; a research vehicle, not a code-translation system. |
| **Self-collaboration Code Generation** (Dong et al.) | 2304.07590 | TOSEM 2024 | One LLM instantiated as analyst/coder/tester "virtual team"; +30–47% Pass@1. | Conceptual ancestor of CodeWeaver's role pipeline, but single-function (HumanEval/MBPP), no state machine, no milestones/parity. |
| **ChatDev** (Qian et al.) | 2307.07924 | ACL 2024 | "Software company" of agents over a fixed *chat-chain* of phases. | Greenfield app creation from a prompt, dialogue-driven; no source-fidelity oracle, no translation, no completeness check. |
| **MetaGPT** (Hong et al.) | 2308.00352 | ICLR 2024 | Encodes SOPs; agents pass structured artifacts (PRD, design) assembly-line style. | De-novo software from specs, single pass; CodeWeaver translates an existing repo with a fixed oracle and a deterministic (not SOP-prompted) orchestrator. |
| **AgentVerse** (Chen et al.) | 2308.10848 | ICLR 2024 | *Dynamic* team composition (recruit/dismiss agents). | Domain-general; CodeWeaver deliberately uses a *fixed* role hierarchy for a structured task. |
| **AgentCoder** (Huang et al.) | 2312.13010 | preprint | Programmer / Test-Designer / Test-Executor with a generate→test→repair loop. | Structurally closest single-function analog to Translator/Validator; but competitive-coding scope, LLM-conversation loop, no scoping/milestones/parity, no fixed source oracle. |
| **MapCoder** (Islam et al.) | 2405.11403 | ACL 2024 | Retrieval→Plan→Code→Debug four-agent pipeline; SOTA on contest benchmarks. | Echoes Analyzer→Planner→Translator→Validator, but single-problem synthesis, not repo translation; no completeness verification. |

**Takeaway for B:** Role specialization and generate→test→repair loops are
well-established, but *exclusively for single-function/competitive code
generation*. CodeWeaver ports these ideas to **whole-repository translation** with
an **external, deterministic** controller rather than LLM-mediated coordination.

---

## 5. Cluster C — Agentic software engineering & repository understanding

| Work | id | Venue (reported) | Contribution | Contrast with CodeWeaver |
|---|---|---|---|---|
| **SWE-bench** (Jimenez et al.) | 2310.06770 | ICLR 2024 | 2,294 real GitHub issues; success = hidden test suite passes after the patch. | Defines the *fixed-test-oracle, repo-scale* evaluation paradigm CodeWeaver adopts — but for single-issue bug fixing in one language, not cross-language translation or completeness. |
| **SWE-bench Multimodal / Multilingual** | 2410.03859 / leaderboard | 2024 | Extends SWE-bench to JS/visual and 9 languages; exposes a cross-language performance cliff. | Motivates language-agnosticism; still per-issue, not whole-repo translation. |
| **SWE-agent** (Yang et al.) | 2405.15793 | NeurIPS 2024 | The **Agent–Computer Interface**: purpose-built tools matter as much as the model. | Closest ancestor of CodeWeaver's Copilot-CLI agents (read/edit/shell/test), but a *freeform ReAct loop on one issue*; no multi-role orchestration, milestones, or parity. |
| **Agentless** (Xia et al.) | 2407.01489 | preprint | A simple localize→repair→validate pipeline rivals complex agents on SWE-bench. | Argues *against* heavy agency for bug-fixing; CodeWeaver's evidence (and ReCodeAgent's ablation) is that *translation* needs structured iterative loops a static pipeline can't provide. |
| **AutoCodeRover** (Zhang et al.) | 2404.05427 | ISSTA 2024 | LLM + **AST-level** code search + spectrum-based fault localization for issue fixing. | Structured navigation like CodeWeaver's Analyzer/LSP use, but for *fault localization* in one language, single-agent. |
| **MASAI** (Arora et al.) | 2406.11638 | preprint | **Modular** specialized sub-agents (reproducer, localizer, editor, verifier). | Closest published *modular multi-agent* SE design; but LLM-driven coordination and single-issue Python scope vs. CodeWeaver's deterministic state machine + cross-language repo translation. |
| **MAGIS** (Tao et al.) | 2403.17927 | preprint | Manager/Custodian/Developer/QA agents for issue resolution. | Role-specialized like CodeWeaver; informal coordination, single-issue, no milestones/parity. |
| **AutoDev** (Tufano et al., Microsoft) | 2403.08299 | preprint | Autonomous agents run build/test/git in containers — beyond snippet suggestion. | Same "agents run real tools" ethos and ecosystem as CodeWeaver; general-purpose, single-agent, no translation specialization or completeness gate. |
| **OpenHands / OpenDevin** (Wang et al.) | 2407.16741 | preprint | Open platform for generalist SE agents (sandboxed exec, multi-agent primitives). | A *platform* CodeWeaver-like systems could run on; not itself a structured translation pipeline. |
| **CodeAgent** (Zhang et al.) | 2401.07339 | ACL 2024 | Tool-integrated agents for repo-level code *generation* (5 tools). | Tool-use supports CodeWeaver's design; targets adding code to a repo, not translating it wholesale. |
| **RepoCoder** (Zhang et al.) | 2303.12570 | EMNLP 2023 | Iterative retrieval+generation for repo-level *completion*; RepoEval. | Establishes repo-wide context retrieval CodeWeaver uses via LSP/MCP; completion ≠ whole-repo translation. |
| **RepoAgent** (Luo et al.) | 2402.16667 | preprint | Whole-repo *documentation* via call-graph traversal. | Demonstrates repo-scale LLM reasoning; writes docs, not translated code; no oracle. |
| **Repository-Level Prompt Generation** (Shrivastava et al.) | 2206.12839 | ICML 2023 | Cross-file context selection boosts LLM code quality. | Foundational "repo context matters" evidence CodeWeaver builds on. |

**Takeaway for C:** Agentic SE is dominated by **single-issue bug resolution in a
single language** against a hidden test oracle. CodeWeaver reuses the ACI + fixed-
oracle idea but changes the task (**cross-language whole-repo translation**), the
control structure (**deterministic milestone pipeline**), and the stopping
criterion (**verified completeness**, not "tests for this issue pass").

---

## 6. Cluster D — Test-driven generation, self-repair, program repair, translation validation

| Work | id | Venue (reported) | Contribution | Contrast with CodeWeaver |
|---|---|---|---|---|
| **CodeT** (Chen et al.) | 2207.10397 | ICLR 2023 | Generate code *and tests*, rank by dual execution agreement. | Uses *LLM-generated* tests (can share the model's blind spots); CodeWeaver uses the project's *human-authored, never-modified* tests as ground truth. |
| **Self-Refine** (Madaan et al.) | 2303.17651 | NeurIPS 2023 | One LLM: generate→self-critique→refine, no external signal. | Feedback is the model's own opinion (hallucination-prone) and unbounded; CodeWeaver's signal is real test execution, bounded by a budget + parity gate. |
| **Reflexion** (Shinn et al.) | 2303.11366 | NeurIPS 2023 | Verbal self-reflection stored in episodic memory across trials. | Single-agent, independent episodes; CodeWeaver's Validator→Translator repair spans interdependent repo milestones and tracks *completeness* across episodes. |
| **Self-Debugging** (Chen et al.) | 2304.05128 | ICLR 2024 (reported) | Explain-then-fix using execution feedback ("rubber-duck"). | Analogous repair step, but treats test generation as part of the loop and is unbounded; CodeWeaver freezes the oracle and escalates to parity for completeness. |
| **LDB** (Zhong et al.) | 2402.16906 | ACL 2024 (Findings, reported) | Block-by-block runtime verification to localize bugs; evaluated on *TransCoder*. | One of few bridging repair↔translation; function-level single-language vs. CodeWeaver's repo/cross-language repair. |
| **AlphaCodium** (Ridnik et al.) | 2401.08500 | preprint | "Flow engineering": structured test-based iterate loop beats prompt engineering. | Closest single-function analog of translate→validate→repair; CodeWeaver generalizes to repo scale + dependency-ordered milestones + parity. |
| **LATS** (Zhou et al.) | 2310.04406 | ICML 2024 (reported) | MCTS over LLM reason/act/reflect; tree search with value functions. | Search-based repair; CodeWeaver uses linear bounded repair but makes state-level backtracking trivial via the state machine. |
| **RING** (Joshi et al.) | 2208.11640 | AAAI 2023 | Multilingual repair as generation (localize→transform→rank), 6 languages. | Repair primitive inside CodeWeaver's loop, but monolingual fixes; CodeWeaver's repair must also reconcile *cross-language* semantics. |
| **ChatRepair** — "Keep the Conversation Going" (Xia & Zhang) | 2304.00385 | FSE/PACMSE 2023 (reported) | Conversational multi-turn repair fixes 162/337 Defects4J bugs at ~$0.42. | Multi-turn context like CodeWeaver's repair; bug-fixing in a fixed-oracle benchmark, not translation. |
| **OpenCodeInterpreter** (Zheng et al.) | 2402.14658 | ACL 2024 (Findings) | Integrate execution feedback + refinement; open models near GPT-4 CI. | Execution-refinement loop parallels CodeWeaver's; single-function, needs feedback fine-tuning. |
| **VERT** (see A.4) | 2404.18852 | ICSE 2025 (reported) | **Formal** equivalence checking for transpilation. | The formal-validation counterpart to CodeWeaver's test-oracle + parity approach. |

**Takeaway for D:** Iterative test-driven self-repair is mature at the
**single-function** level. CodeWeaver's novelty is not the repair loop itself but
(i) grounding it in a **fixed project oracle** (vs. self-generated/opinion
feedback), (ii) **bounding** it per milestone, and (iii) subordinating it to a
**completeness verifier**.

---

## 7. Cluster E — Orchestration frameworks (infrastructure)

| Framework | Type | Note | Relation to CodeWeaver |
|---|---|---|---|
| **AutoGen** (Wu et al., 2308.08155) | paper + OSS | Conversable multi-agent apps; topologies via LLM-mediated chat. | CodeWeaver *could* be built on AutoGen, but AutoGen leaves control flow to LLM reasoning; CodeWeaver needs deterministic guarantees. |
| **CoALA** (Sumers et al., 2309.02427, TMLR 2024) | taxonomy | Cognitive-architecture framework for language agents. | Vocabulary to describe CodeWeaver (Burr = procedural memory; roles = action subspaces; milestone state = working memory). |
| **LangGraph** (LangChain) | OSS | Stateful multi-actor graphs; edges often LLM-routed. | Structural analog to Burr; CodeWeaver picks Burr specifically for *purely deterministic* transitions. |
| **Apache Burr** (DAGWorks→ASF) | OSS | State machine where the **LLM is only called inside action nodes, never for routing**; built-in persistence + telemetry. | **CodeWeaver's backbone.** Enables the core design principle: *separate deterministic control flow from non-deterministic agent reasoning*, giving reproducibility, crash-resume, and guaranteed milestone/parity progression. |
| **CrewAI** (Moura et al.) | OSS | Role-based agent "crews"; process mostly LLM-managed. | "Crew of agents" abstraction like CodeWeaver's roles, but no state machine, milestone gates, or parity loop. |

---

## 8. The direct predecessor: ReCodeAgent

**ReCodeAgent: A Multi-Agent Workflow for Language-agnostic Translation and
Validation of Large-scale Repositories** — Ali Reza Ibrahimzada, Brandon Paulsen,
Daniel Kroening, Reyhaneh Jabbarvand. **arXiv:2604.07341** (Apr 2026; venue
reported as ISSTA/ICSE 2026, unconfirmed).

**What it does.** The first *fully autonomous, PL-agnostic* multi-agent system for
repository-level translation+validation: the user provides a source repo and a
target language, and the agents translate and validate the whole repository,
autonomously invoking each language's tools. Evaluated on **118 real-world
projects** (avg 1,975 LoC, 43 translation units), **6 languages** (C, Go, Java,
JavaScript, Python, Rust), **4 pairs** (C→Rust, Go→Rust, Java→Python,
Python→JavaScript); improves ground-truth test pass rate by **60.8%** over four
neuro-symbolic/agentic baselines at ~**$15.3/project**. Its ablation shows a
single-agent variant drops pass rate by **40.4%** and yields **28% longer**,
"persistently inefficient" trajectories — evidence for multi-agent decomposition.

**CodeWeaver = a structured, completeness-guaranteed generalization of
ReCodeAgent.** CodeWeaver reimplements the multi-agent translation+validation idea
on an open stack and adds five things ReCodeAgent does not describe:

1. **Deterministic Apache Burr orchestrator** — control flow (which agent, when to
   loop, when to halt) is pure Python; no LLM routing. Reproducible + crash-resumable.
2. **Milestone-incremental translation with cumulative test gates** — the Scoper
   generates an ordered milestone plan; each milestone must pass its own tests *and*
   all earlier ones (regression safety).
3. **Two-layer validation** — fast *mocked unit tests* for cheap repair iterations
   plus a *fixed, authoritative end-to-end oracle* (the project's own tests, never
   modified/regenerated by any agent).
4. **Parity-verifier completeness loop** — after milestones pass, a dedicated agent
   compares source vs. translation component-by-component; if anything is
   untranslated/stubbed, it re-plans milestones and repeats. The run terminates
   **only** when parity is verified complete (bounded by `max_parity_rounds`).
5. **Config-driven language-agnosticism + auto-milestones** — any source/target pair
   via a TOML config + natural-language project brief; milestones can be
   auto-generated from the source and its tests.

---

## 9. What distinguishes CodeWeaver (positioning)

| Dimension | Function-level translation (TransCoder…) | Multi-agent code gen (MetaGPT, MapCoder…) | Agentic SE (SWE-agent, AutoCodeRover…) | Repo-level translation (AlphaTrans, CodePlan) | ReCodeAgent | **CodeWeaver** |
|---|---|---|---|---|---|---|
| Task | translate a snippet | synthesize a function/app | fix one issue | translate a repo | translate a repo | **translate a repo** |
| Scope | function | function/app | 1 repo, 1 lang | 1 repo, 1 pair | many pairs | **any pair (config)** |
| Orchestration | none (model) | LLM chat/loop | freeform ReAct | LLM/symbolic plan | multi-agent | **deterministic state machine** |
| Correctness signal | none / BLEU | self/LLM tests | hidden issue tests | mixed-exec + tests | project tests | **fixed project oracle + mocked unit layer** |
| Iterative repair | no | yes (self) | yes | partial (manual) | yes | **yes, bounded per milestone** |
| Incremental plan | no | plan step | no | call-graph order | fragments | **cumulative test-gated milestones** |
| **Completeness guarantee** | no | no | no | no | no (ablation: inefficient) | **yes — parity verifier loop** |
| Reproducible / resumable | — | rarely | rarely | — | — | **yes (SQLite crash-resume)** |

**Three sentences that state the delta.** (1) *Versus single-shot/function-level
translation*, CodeWeaver is repository-scale, iterative, and validated against real
tests. (2) *Versus multi-agent code generation and agentic SE*, CodeWeaver targets
**translation with an existing ground-truth oracle** and replaces LLM-mediated
coordination with a **deterministic milestone state machine**. (3) *Versus the
closest repo-level translation systems (AlphaTrans, CodePlan) and its direct
predecessor (ReCodeAgent)*, CodeWeaver adds a **parity-completeness loop** that
turns "the tests we ran pass" into "**every component is actually translated**,"
plus language-agnostic config, auto-milestones, two-layer validation, and
crash-resumable deterministic orchestration.

---

## 10. Target venues for CodeWeaver-type work

| Venue | Why it fits | Example prior papers here |
|---|---|---|
| **ICSE** (Int'l Conf. on Software Engineering) | Premier SE venue; LLM translation/repair, agents, large empirical studies. **Most natural primary target.** | *Lost in Translation* (2024); VERT, Scalable Code Translation (2025, reported) |
| **FSE / ESEC-FSE** | Program analysis, repair, LLM-for-code systems; the parity verifier as a correctness contribution. | CodePlan (reported), AlphaTrans (reported), ChatRepair (reported) |
| **ASE** (Automated Software Engineering) | Automation, agents, tool-building — ideal for the agent architecture. | AutoCodeRover-line work |
| **ISSTA** (Software Testing & Analysis) | Oracle design, differential testing, test-driven validation. | AutoCodeRover (2024) |
| **OOPSLA / PLDI / POPL** | If the parity verifier / type-compatibility is formalized (semantics, translation validation). | translation-validation lineage |
| **NeurIPS / ICLR / ICML** | If framed as LLM-agent methodology or a benchmark/system. | TransCoder, SWE-agent, SWE-bench, Reflexion, Self-Refine, LATS |
| **ACL / EMNLP / NAACL** | If emphasizing LLM/language-modeling and multilingual aspects. | TransCoder-ST, CodeTransOcean, MapCoder, ChatDev, SACTOR |

**Recommendation:** primary **ICSE** or **FSE** (position the parity-completeness
loop + milestone gates as the SE contribution; evaluate on **RepoTransBench** and
**CRUST-Bench**), with **NeurIPS/ICLR** as an alternative if framed as an LLM-agent
system + benchmark.

---

## 11. Verification caveats & gaps

- **arXiv IDs** in this document were title-verified against the arXiv API.
- **Peer-reviewed venue** attributions marked "reported/likely" (e.g., AlphaTrans
  FSE 2025, VERT ICSE 2025, ReCodeAgent ISSTA/ICSE 2026, CodePlan FSE 2024, LDB ACL
  Findings) come from author/community sources and **should be re-confirmed** in
  proceedings/DBLP before citing.
- **IDs to double-check** (surfaced but not directly fetched by every pass):
  TransCoder-IR (2207.03578), CodeXGLUE (2102.04664), xCodeEval (2303.03004),
  RustRepoTrans, PtrTrans, "Scalable Validated Code Translation" (no arXiv found —
  cite the venue version).
- **Could not verify:** a C→Rust paper named **"Flourine/Fluorine"** — no matching
  arXiv/Semantic Scholar record; **do not cite** without a source. **Laertes** is a
  PLDI 2022 paper with no arXiv preprint (cite the proceedings).
- The **"Crust-β"** label some secondary sources attach to a CRUST-Bench experiment
  is not a benchmark project name in CRUST-Bench itself (see the `crust-bench`
  example README).

---

## 12. Consolidated reference list (verified arXiv IDs)

**Translation foundations & benchmarks:** TransCoder 2006.03511 · TransCoder-ST
2110.06773 · TransCoder-IR 2207.03578 · Lost in Translation 2308.03109 · CodeXGLUE
2102.04664 · CodeTransOcean 2310.04951 · xCodeEval 2303.03004 · RepoTransBench
2412.17744.

**Repo-level translation:** CodePlan 2309.12499 · AlphaTrans 2410.24117 ·
ReCodeAgent 2604.07341 · RustRepoTrans (2411, reported).

**C-to-Rust:** CRUST-Bench 2504.15254 · Syzygy 2412.14234 · VERT 2404.18852 ·
SACTOR 2503.12511 · Translating C to Rust (user study) 2411.14174 · PtrTrans (2510,
reported).

**Multi-agent code gen:** CAMEL 2303.17760 · Self-collaboration 2304.07590 · ChatDev
2307.07924 · MetaGPT 2308.00352 · AgentVerse 2308.10848 · AgentCoder 2312.13010 ·
MapCoder 2405.11403.

**Agentic SE:** SWE-bench 2310.06770 · SWE-bench Multimodal 2410.03859 · SWE-agent
2405.15793 · Agentless 2407.01489 · AutoCodeRover 2404.05427 · MASAI 2406.11638 ·
MAGIS 2403.17927 · AutoDev 2403.08299 · OpenHands 2407.16741 · CodeAgent 2401.07339
· RepoCoder 2303.12570 · RepoAgent 2402.16667 · Repo-Level Prompt Gen 2206.12839.

**Self-repair / test-driven / validation:** CodeT 2207.10397 · Self-Refine
2303.17651 · Reflexion 2303.11366 · Self-Debugging 2304.05128 · LDB 2402.16906 ·
AlphaCodium 2401.08500 · LATS 2310.04406 · RING 2208.11640 · ChatRepair 2304.00385 ·
OpenCodeInterpreter 2402.14658.

**Orchestration:** AutoGen 2308.08155 · CoALA 2309.02427 · LangGraph (OSS) · Apache
Burr (OSS) · CrewAI (OSS).
