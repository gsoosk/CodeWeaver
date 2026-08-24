# CodeWeaver — Paper-Writing & Experiment Instructions

**Audience:** the research agent tasked with (a) running the experiments and
(b) writing the paper.
**Target venue:** SANER 2027 — Research Track (see §6).
**Status of the idea:** **already designed, already implemented, already partly
evaluated.** Your job is to *evaluate and write it up* — not to invent it.

---

## 0. Read this first — scope of your authority

> **CodeWeaver is our method. It is pre-existing work.**
> The design, architecture, agent roles, control loops, and mechanisms described in
> this repository were conceived and implemented **before** you were engaged. You are
> **not** a co-designer of the method.

**You MUST NOT:**

- invent, propose, or add new *method* components, stages, agents, loops, or
  mechanisms to CodeWeaver, and you must not present any such addition as part of
  the contribution;
- reframe, rename, or "improve" the core idea, its terminology, or its claimed
  novelty;
- describe the method as something you designed, or use language implying the
  method emerged from your work;
- silently change the pipeline semantics to make results look better;
- modify the framework source (`codeweaver/`, `agents/`) to alter behavior for the
  paper. Bug fixes required to *run* an experiment are allowed — but they must be
  reported to the maintainer and recorded in the artifact, never presented as a
  contribution.

**You MAY (and should):**

- design, run, and report **experiments**, baselines, ablations, and analyses;
- build **experiment harnesses**, benchmark adapters, metric collectors, and
  result-processing scripts (keep them under `experiments/`, results under
  `results/` — see §3);
- propose *additional* experiments beyond those specified here when they
  strengthen the paper, following the norms of similar papers (§4.4);
- write all paper prose, tables, and figures;
- point out weaknesses, negative results, and threats to validity — in fact you
  **must** (§5.3).

If you believe the method itself needs a change, **stop and report it**. Do not
implement it and do not write it into the paper.

---

## 1. The repository (authoritative source of the method)

| Field | Value |
|---|---|
| **Repository ID** | `gsoosk/CodeWeaver` |
| **HTTPS** | `https://github.com/gsoosk/CodeWeaver` |
| **SSH** | `git@github.com:gsoosk/CodeWeaver.git` |
| **Owner / author** | Farzad Habibi (`gsoosk`) |
| **License** | see `LICENSE` |

### Branches

| Branch | Contents |
|---|---|
| `main` | the CodeWeaver framework (stable) |
| `V2` | **current development head** — skip-on-give-up, deferred-test retry, partway-start flags, tolerant report parsing. Use this as the method under evaluation unless told otherwise. |
| `experiments` | experiment harnesses (`experiments/`) + published result packages (`results/`) |
| `recodeagent-paper-results` | the 118-project ReCodeAgent-style reproduction |

> ⚠️ **Double-blind warning.** The repository URL, owner name, and branch names
> **identify the authors**. They are given here for *your* use only. They must
> **never** appear in the submitted paper (see §6.3). Use an anonymized artifact
> link instead.

### Key files to read before writing a single word

| Path | Why it matters |
|---|---|
| `idea.md` | **The canonical description of the method and the evaluation plan.** Treat it as the specification. Do not contradict it. |
| `docs/architecture.md` | The Burr state graph, transitions, control loops, skip/retry semantics, partway-start entry points. |
| `docs/config.md` | The full `codeweaver.toml` reference — every knob you may vary in an ablation. |
| `docs/related-work.md` | ~60 verified related papers, clustered, with the positioning argument. Reuse this for §Related Work; verify every citation before use. |
| `agents/*.agent.md` | The six agent role prompts (analyzer, scoper, planner, translator, validator, parity). These *are* the method's agent definitions. |
| `codeweaver/` | The implementation: `config`, `milestones`, `prompts`, `copilot`, `state`, `actions`, `app`, `mock`, `cli`. |
| `examples/` | Runnable configs: `minimal`, `auto-milestones`, `xcvrd`, `crust-bench`, `commons-validator`. |
| `README.md` | Quick start, CLI surface. |

**Rule:** where this document and `idea.md` disagree about the *method*, `idea.md`
wins. Where they disagree about the *paper/venue*, this document wins.

---

## 2. One-paragraph description of the method (use this framing, do not drift)

CodeWeaver is a **general-purpose, configuration-driven, language-agnostic
multi-agent framework for whole-repository code translation**. A single
`codeweaver.toml` — not hard-coded prompts — describes the source/target
languages, the project brief, the build/test commands, the test-selector syntax,
and the milestone matrix. Six role-specialized agents (analyzer, scoper, planner,
translator, validator, parity verifier) are orchestrated by a **persisted,
resumable state machine** with **two nested control loops**: an inner
*per-milestone repair loop* (correctness) and an outer *parity loop*
(completeness). The run terminates successfully **only when an independent parity
verifier confirms the whole source repository has been translated** — not merely
when the tests that happened to run passed. A milestone that exhausts its repair
budget is **skipped rather than fatal**: its failing tests are deferred, deselected
from later gates, and given exactly one dedicated retry milestone before becoming a
permanent, explicitly reported skip.

The **contribution surface** to evaluate (per `idea.md` §2.3) is therefore:
config-driven language-agnosticism; the milestone-generating *scoper*; the
**completeness-terminated parity loop**; skip-on-give-up with bounded deferred-test
retry; and crash-resumable persisted orchestration.

---

## 3. What already exists — reuse it, do not redo it

The `experiments` branch already contains **substantial measured results** with a
strict honesty discipline (measured vs. paper-reference values never pooled;
leakage audits; unavailable surfaces marked `blocked`/`unavailable`, never zero).
**Inventory these first.** Re-running them is a waste of budget.

Result packages currently on `origin/experiments` under `results/`:

| Package | Scope |
|---|---|
| `recodeagent-gpt-5.6-sol-final-2026-08-11` | 118 projects / 4 language pairs (ReCodeAgent-style reproduction) |
| `crust-bench-codeweaver-comparison-2026-08-14` | CRUST-Bench, 100 projects × 3 reps |
| `sactor-codeweaver-comparison-2026-08-14` | SACTOR's exact 50-project CRUST subset × 3 |
| `rustine-codeweaver-comparison-2026-08-12` | Rustine, 23 C repositories |
| `evoc2rust-codeweaver-comparison-2026-08-13` | EvoC2Rust / Vivo-Bench, 19 modules × 3 |
| `alphatrans-codeweaver-comparison-2026-08-14` | AlphaTrans, 4 common Java→Python projects × 3 |
| `repotransbench-codeweaver-comparison-2026-08-14` | RepoTransBench historical slice × 3 |
| `rustrepotrans-codeweaver-comparison-2026-08-14` | RustRepoTrans leakage-safe slice × 3 |
| `crust-citation-complete-codeweaver-2026-08-20` | Full CRUST-Bench citation census (19 in-scope works); newly measured **ORBIT** (24 projects), **Li et al. ACToR** (6-program hidden oracle), **Schesch/Ernst ACTOR** (95-project overlap) |

Each package carries `data/`, `report/comparison.{md,pdf}`, `report/figure.*`,
`metadata/` (provenance + checksums), and `reproduction/` (commands + harness
snapshot). **Read every `report/comparison.md` before planning new runs.**

> The `experiments` branch is large. Fetch it blobless:
> `git fetch --filter=blob:none origin experiments`

**Your first deliverable is a gap analysis**: what the paper needs vs. what already
exists vs. what must still be run.

---

## 4. Experiments

### 4.1 Primary reference design — mirror this paper

**ReCodeAgent: A Multi-agent Workflow for Language-Agnostic Translation and
Validation of Large-Scale Repositories** — **arXiv:2604.07341**
(`https://arxiv.org/abs/2604.07341`).

This is CodeWeaver's **direct predecessor** and the closest comparable evaluation.
**Read it in full**, then **adopt its evaluation design to our method.** Its
reported setup, which you should mirror in structure:

- **Subjects:** 118 real-world projects, averaging ~1,975 LoC and ~43 translation
  units each, covering **6 programming languages across 4 PL pairs**.
- **Baselines:** four alternative **neuro-symbolic and agentic** approaches.
- **Headline effectiveness metric:** translation correctness measured as
  **test pass rate on ground-truth tests** (they report +60.8% over prior work).
- **Cost:** average **$15.3 per project** — report cost per project explicitly.
- **Process-centric analysis:** analyze **agent trajectories** for procedural
  efficiency, not just end outcomes.
- **Design-choice ablation:** **multi-agent vs. single-agent** (they report test
  pass rate dropping 40.4% and trajectories becoming 28% longer when collapsed to
  a single agent).

**Adopt, don't copy.** Map each of the above onto CodeWeaver's contribution
surface. Concretely:

| ReCodeAgent element | CodeWeaver adaptation |
|---|---|
| Language-agnosticism claim | Demonstrate via **config-only retargeting** — same framework, different `codeweaver.toml`, ≥4 PL pairs. Report exactly what changed per pair (config lines, not code). |
| Test pass rate on ground-truth tests | Same metric. Also report **build/compile rate** and **whole-project pass-all**, which our result packages already use. |
| Cost per project | Same. We additionally have AIU, premium requests, output tokens, wall-clock (already collected — see the telemetry tables in the result packages). |
| Process-centric trajectory analysis | Analyze our **persisted Burr state**: milestones attempted, repair iterations per milestone, give-ups, deferred-test retries, parity rounds. This is a natural fit and a differentiator. |
| Multi-agent vs single-agent ablation | Run it, **and** add the ablations that isolate *our* novelties (§4.3). |

### 4.2 Research questions (baseline set — refine, don't shrink)

Anchor the RQs on the contribution surface in §2. A workable set:

- **RQ1 (Effectiveness).** How does CodeWeaver compare to prior repository-level
  translation techniques on translation correctness (build rate, ground-truth test
  pass rate, whole-project pass-all)?
- **RQ2 (Language-agnosticism).** Can CodeWeaver retarget to a new language pair
  through configuration alone, and how does effectiveness hold across pairs?
- **RQ3 (Completeness).** Does the parity loop detect and repair untranslated
  functionality that test-passing alone would miss? *(This is our sharpest
  differentiator — quantify how much the parity loop adds beyond an all-tests-pass
  stopping rule.)*
- **RQ4 (Robustness / progress).** What does skip-on-give-up with bounded retry buy
  versus hard-failing? How often are deferred tests recovered vs. permanently
  skipped?
- **RQ5 (Ablations).** Which design choices matter — multi-agent vs. single-agent,
  parity on/off, scoper vs. declared milestones, skip-on-give-up on/off?
- **RQ6 (Cost & process efficiency).** Cost per project and per successful
  translation; trajectory-level procedural efficiency.

`idea.md` §5.1 has the authoritative RQ list — reconcile with it and keep its
intent. You may merge/split RQs to fit 10 pages.

### 4.3 Ablations (mandatory — these isolate our novelty)

At minimum, ablate each mechanism named in §2:

1. **`parity_check = false`** — terminate on all-tests-pass instead of verified
   completeness. Measures what the parity loop contributes.
2. **`skip_on_give_up = false`** — legacy hard-fail. Measures progress preservation.
3. **Declared milestones vs. auto-generated (scoper off/on).**
4. **Single-agent collapse** (ReCodeAgent's ablation, adapted).
5. **`max_iter` / `max_parity_rounds` sensitivity** — budget vs. outcome curves.

All of these are **configuration flags** (`docs/config.md`), so no method changes
are needed — that is itself a result worth stating.

### 4.4 Your own experiments — encouraged

Beyond the above you **may and should** add experiments you judge best for the
paper, following the conventions of comparable venues and papers (the CRUST-Bench,
SACTOR, ORBIT, AlphaTrans, RepoTransBench, RustRepoTrans, EvoC2Rust,
Rustine/ACToR lines already surveyed in `docs/related-work.md` and already
partially measured in §3). Good candidates:

- code-quality analyses of the output (linter/`clippy` density, `unsafe` usage,
  idiomaticity) — partly collected already;
- coverage before/after translation;
- failure taxonomy of unrecovered milestones and permanent skips;
- scalability vs. repository size / number of translation units;
- statistical treatment across repetitions (report variance/CIs, not just means).

**Constraint:** new *experiments* are welcome; new *method* is not (§0).

### 4.5 Experimental protocol (non-negotiable)

- **≥3 independent repetitions** per subject wherever budget allows; report mean ±
  spread (SD or CI), never a single cherry-picked run. Retain **all** terminal
  outcomes — **no best-of-N selection**.
- **Never pool measured values with paper-reported baseline values** in the same
  column. Keep "measured by us" and "reported by the original paper" visually and
  textually distinct — the existing result packages already do this; match it.
- **Leakage audits.** Hash and withhold any ground-truth target implementation
  before the model can see it; report byte-identical outputs as an observed
  property, not as proof of exposure.
- **Exact-subject comparisons only.** Do not compare across different subject sets,
  different denominators, or different units (function-level vs. project-level)
  without saying so explicitly in the table caption.
- **Unavailable ≠ zero.** Mark `blocked` / `unavailable` / `reference_only` and say
  why.
- **Pin everything:** model + version, reasoning effort, `max_iter`,
  `max_parity_rounds`, timeouts, toolchain versions, commit SHAs of subjects.
- **Record cost** (wall-clock, tokens/AIU, premium requests, USD estimate) for
  every campaign.

### 4.6 Running the pipeline

See `idea.md` §5.8 and `README.md`. Essentials:

```bash
codeweaver install-agents                                  # once
codeweaver check   --config <cfg>                          # offline mock smoke test (free)
codeweaver run     --config <cfg> --app-id <run> --max-iter 5
codeweaver run     --config <cfg> --app-id <run>           # resume: SAME app-id
codeweaver run     --config <cfg> --start-milestone M4     # enter partway
codeweaver run     --config <cfg> --start-parity           # re-grade at parity only
codeweaver milestones --config <cfg>                       # matrix + resolved gates
```

Always dry-run `codeweaver check` on a new benchmark config **before** spending
budget — it exercises the whole graph offline against mock agents.

---

## 5. The paper

### 5.1 Required structure (10 pages)

1. **Title + Abstract** — state the problem, the approach, and the *headline
   quantitative* result.
2. **Introduction** — motivation, the gap, contributions as an explicit bulleted
   list, and a forward pointer to results.
3. **Background / Motivating example** — a concrete repository-translation scenario
   that shows why test-passing ≠ complete translation.
4. **Approach** — CodeWeaver: the config-driven design, the six agents, the two
   nested loops, termination on verified completeness, skip/retry. Include the
   architecture figure. **Source of truth: `idea.md` + `docs/architecture.md`.**
5. **Experimental Setup** — subjects, baselines, metrics, protocol, RQs.
6. **Results** — one subsection per RQ, each opening with a one-sentence finding.
7. **Discussion** — what the numbers mean, when the approach fails, cost/benefit.
8. **Threats to Validity** — internal, external, construct, conclusion.
9. **Related Work** — from `docs/related-work.md` (verify every citation).
10. **Conclusion**
11. **Data Availability** — required by SANER (§6.4).
12. **References** (2 extra pages allowed).

### 5.2 Writing rules

- Every number in the text must be traceable to a file in `results/`. No number
  may be invented, rounded into a different claim, or carried over from memory.
- Report **negative and mixed results** plainly. The existing packages contain
  real weaknesses (e.g. large Java→Python repositories where all translations
  build but none pass every test; benchmarks where a specialized tool beats us).
  **Hiding these is a rejection risk and is not acceptable.** Discuss them.
- Distinguish *measured* from *cited* in every table.
- Do not overclaim language-agnosticism beyond the pairs actually evaluated.
- Prefer "CodeWeaver achieves X on benchmark B under protocol P" over
  "CodeWeaver is state of the art".
- Keep tables/figures self-contained (units, denominators, N, reps in the caption).

### 5.3 Honesty

Reviewers at SANER weight **soundness** and **verifiability** heavily. Every
limitation you disclose yourself is a limitation a reviewer cannot use against
you. Follow the discipline already established in the result packages.

---

## 6. Venue requirements — SANER 2027 Research Track

**CFP:** `https://conf.researchr.org/track/saner-2027/saner-2027-papers`

### 6.1 Dates

| Milestone | Date |
|---|---|
| **Abstract submission (mandatory)** | Mon 21 Sep 2026 |
| **Paper submission** | Fri 25 Sep 2026 |
| Notification | Tue 1 Dec 2026 |
| Camera-ready / author registration | Fri 8 Jan 2027 |

Submission via **EasyChair** (`saner2027`), Research Track. The abstract deadline
is **mandatory and earlier** than the paper deadline — plan backwards from
21 Sep 2026.

### 6.2 Format (violations = desk reject)

- IEEE Conference Proceedings format; LaTeX:
  `\documentclass[10pt,conference]{IEEEtran}` — **without** `compsoc` /
  `compsocconf`.
- Title 24pt, body 10pt.
- **Max 10 pages**, plus **up to 2 additional pages for references only**.
- PDF, English, full papers only.

### 6.3 Double-anonymous review (violations = desk reject)

SANER 2027 is **fully double-anonymous**. Therefore:

- **No author names or affiliations.**
- Refer to our own prior work in the **third person** ("We build on the work of…",
  not "our previous work"), or anonymize the reference itself
  ("[10] Anonymous Authors. Omitted per double-blind reviewing.") — and keep the
  paper self-contained without it.
- **Do not link to `github.com/gsoosk/CodeWeaver`** or any URL revealing the
  authors. Use an anonymized artifact (e.g. Zenodo/Figshare anonymous deposit, or
  an anonymized repository mirror), or state that the link will be provided in the
  camera-ready.
- Consider whether the project name itself is identifying; the CFP explicitly
  allows renaming for submission. **Flag this to the maintainer and get a
  decision** — do not rename unilaterally.
- No identifying acknowledgments.
- Preprint policy: do not post/update a non-anonymized version during the anonymity
  period (starts one month before the deadline).

### 6.4 Open science / Data Availability

Include a **"Data Availability"** section **after the Conclusion** that either
points to an anonymized artifact with access instructions, or explains why not.
Prefer a DOI-issuing service (Zenodo/Figshare) with anonymous deposit.

### 6.5 Scope compliance — read carefully

The CFP warns that papers involving AI/ML may be **desk-rejected** unless they
concern a software system as a whole (not just its AI component), consider
software evolution/maintenance artifacts, or target a novel context for a software
evolution/maintenance task — **and the paper must explicitly explain how it
addresses a software evolution/maintenance problem.**

**Action:** state this explicitly and early (Introduction). CodeWeaver is
squarely in scope — repository-level **migration/reengineering** of existing
software systems, i.e. *software reconstruction and migration*, *program
transformation*, and *software maintenance and evolution*. Frame it that way, and
align with the CFP's strategic themes **AI4SE** and **Agentic AI in Software
Engineering**.

### 6.6 GenAI policy

Follow the IEEE Submission & Peer Review Policy and the ACM Policy on Authorship
regarding generative-AI use. Disclose AI assistance where the policies require it.
AI tools are **not** authors.

---

## 7. Deliverables

1. **Gap analysis** — needed vs. existing vs. to-run (§3). *Deliver first.*
2. **Experiment plan** — subjects, baselines, RQ→experiment→table/figure mapping,
   budget estimate. *Get approval before large spends.*
3. **Executed experiments** — harnesses under `experiments/`, result packages under
   `results/` matching the existing structure (`data/`, `report/`, `metadata/`,
   `reproduction/`).
4. **Paper source** — LaTeX (IEEEtran, 10pt conference), compiling to ≤10 pages
   + ≤2 reference pages, fully anonymized.
5. **Camera-ready-quality figures/tables** — vector (PDF/SVG), legible at print
   size, self-contained captions.
6. **Anonymized artifact** for the Data Availability section.
7. **Traceability file** — every number in the paper → the file it came from.

---

## 8. Definition of done

- [ ] Every claim in the paper is backed by a file in `results/`.
- [ ] Measured vs. cited values are never pooled.
- [ ] ≥3 repetitions where budget allowed; variance reported.
- [ ] All ablations in §4.3 run and reported.
- [ ] Negative/mixed results reported and discussed, not buried.
- [ ] Method described exactly as implemented — **nothing invented, nothing added**.
- [ ] Paper ≤10 pages + ≤2 reference pages, IEEEtran 10pt conference.
- [ ] Fully anonymized; no repository URL, no author-identifying content.
- [ ] Data Availability section present, after the Conclusion.
- [ ] Explicit statement of the software evolution/maintenance problem addressed.
- [ ] Abstract registered by **21 Sep 2026**; paper submitted by **25 Sep 2026**.

---

## 9. Escalate to the maintainer (do not decide alone)

- Any perceived need to change the **method**.
- Renaming the tool for double-blind compliance.
- Dropping a benchmark, baseline, or ablation.
- Budget overruns, or a result that contradicts an existing published package.
- Any authorship, licensing, or artifact-release question.
