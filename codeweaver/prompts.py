"""Default prompt templates for the four ReCodeAgent stages.

These encode the *methodology* generically; everything project-specific is
injected via ``{placeholders}`` filled from the :class:`~codeweaver.config.Config`
(most importantly ``{brief}`` -- the project's own knowledge) plus per-run values
(the current milestone + mode). A project may override any stage template under a
``[prompts]`` table in its config.

Available placeholders (see :func:`context`):
  source_language, target_language, brief,
  source_dir, reference_dirs, immutable_input, working_copy, pipeline_dir,
  analysis, plan, report,
  build_check, unit_test, validate,
  milestone_id, milestone_title, milestone_goal, mode, failures, gate
"""
from __future__ import annotations

import json
from typing import Any

from . import milestones
from .config import Config

# --------------------------------------------------------------------------- #
# Default templates
# --------------------------------------------------------------------------- #
ANALYZE = """\
You are the Analyzer. Research the {source_language} source at {source_dir} \
(including any behavioral unit tests it ships) and produce the authoritative \
target design for a {target_language} port. Consult the reference material at \
{reference_dirs} as read-only context.

PROJECT BRIEF (authoritative constraints for this port):
{brief}

Write ONE design document to {analysis} with three sections, mirroring the \
ReCodeAgent Analyzer:
  1. Source project research -- overview, structure, key components/interfaces, \
data models, error handling, and dependencies; survey the source's own unit \
tests and how they mock their boundaries.
  2. Third-party library analysis -- for each significant {source_language} \
dependency, recommend the idiomatic {target_language} counterpart, and state \
which needs are ALREADY met by provided scaffolding (do not reinvent those).
  3. Target project design -- a source->target structural mapping (preserve the \
package/module layout and identifier names where sensible), the module structure \
for the target project, the observable output/contract each milestone must \
reproduce, the error-handling and boundary strategy, and the UNIT-TEST strategy \
(mockable seams so translated tests run without live infrastructure), plus the \
milestone mapping.

Do NOT write any {target_language} implementation. Write only {analysis}. End \
by confirming {analysis} exists and summarizing the three sections.
"""

SCOPE = """\
You are the Scoper (milestone generator). Decompose this {source_language} -> \
{target_language} port into an ordered list of CUMULATIVE milestones, and write \
them to {milestones}.

PROJECT BRIEF:
{brief}

{scope_mode_note}Read the Analyzer's design at {analysis} (its milestone mapping \
is your primary input) and the {source_language} source at {source_dir}; consult \
the reference material at {reference_dirs} (e.g. the end-to-end test oracle) to \
learn which tests exist and how they are named. Then design a milestone plan that:
  - starts with a minimal "skeleton" milestone (compiles/links and the entrypoint \
runs; no functional tests yet),
  - adds ONE coherent slice of functionality per subsequent milestone, ordered \
bottom-up so each milestone depends only on earlier ones,
  - is CUMULATIVE: each milestone must pass its own tests AND every earlier \
milestone's, so list under `tests` ONLY the NEW test selectors that milestone \
adds (do not repeat earlier ones),
  - uses REAL test selector tokens that the validate command understands \
(e.g. test names/modules/tags that actually exist in the source's tests or the \
oracle) -- verify they exist; do not invent tests,
  - ends with a "golden"/conformance milestone that reproduces the full contract \
and passes the entire suite.

Write {milestones} as a JSON array (or an object with a top-level "milestones" \
array). Each entry: {{"id" (short, e.g. "M0","M1",...), "title", "goal" (what \
the target must do, concrete + testable), "tests" (array of NEW selector tokens; \
[] for a skeleton/smoke milestone), "marker" (optional extra selector, "" if \
unused)}}. Aim for a handful to a dozen milestones -- small enough to translate + \
validate in one repair loop each, large enough to be meaningful.

Write ONLY {milestones}. Do not write any implementation or plan. End by \
confirming {milestones} exists and listing the milestone ids + titles in order.
"""

# Inserted into SCOPE as {scope_mode_note}: empty on the first pass; on a parity
# re-entry it tells the scoper to APPEND milestones for the reported gaps only.
SCOPE_INCREMENTAL_NOTE = (
    "INCREMENTAL MODE (parity re-entry): {milestones} ALREADY contains the "
    "milestones completed so far -- preserve every existing entry and its id "
    "EXACTLY. The Parity Verifier found the translation INCOMPLETE; read its "
    "report at {parity} and APPEND new milestones ONLY for the untranslated / "
    "partial components it lists (its `missing` array), continuing the id sequence "
    "(if the last id is M4, add M5, M6, ...). Do not re-list or renumber completed "
    "milestones. Rewrite {milestones} as the FULL array (existing + appended).\n\n"
)

PARITY = """\
You are the Parity Verifier. Do a COMPREHENSIVE parity check between the original \
{source_language} source at {source_dir} and the final {target_language} \
translation in {work_target}, and decide whether EVERYTHING in scope has been \
translated. Write your verdict to {parity}.

PROJECT BRIEF:
{brief}

Compare the two sides component-by-component: modules/files, classes/types, \
functions/methods, the public API surface, and observable behaviors. For each \
source component, confirm there is a faithful {target_language} counterpart with \
equivalent behavior (not a stub, TODO, or partial implementation). Use the \
reference material at {reference_dirs} for the intended contract. IGNORE anything \
the brief marks as provided by scaffolding, intentionally reused from the source \
language, or explicitly out of scope -- those are not gaps.

Write {parity} as JSON: {{"complete": bool, "translated": ["component ..."], \
"missing": [{{"component","source_ref","reason","suggested_milestone"}}], \
"notes": "..."}}. Set "complete": true ONLY if every in-scope source component \
has a faithful translation. For each gap, name the concrete component, its source \
reference, why it is missing/partial, and a concrete `suggested_milestone` (title \
+ goal + the test selectors that would gate it) so the milestone generator can \
schedule it next.

You only READ and REPORT -- do not edit any code, tests, or scaffolding. End by \
stating COMPLETE or INCOMPLETE and, if incomplete, listing the gaps.
"""

PLAN = """\
You are the Planner. Turn the Analyzer's design into a granular, \
dependency-aware, executable plan and a COMPILABLE skeleton -- covering both the \
implementation (Part A) and its behavioral unit tests (Part B).

PROJECT BRIEF:
{brief}

{working_copy_instructions}Read the design at {analysis} and the \
{source_language} source at {source_dir}. Then:
  1. Fragment extraction -- list every translation unit as "file:fragment", in \
two groups: Part A (implementation) and Part B (the behavioral unit tests + mock \
helpers). Verify each fragment actually exists (grep / language server); flag \
missing ones. Mark each Part-B fragment translate-directly or needs-new-test.
  2. Name mapping -- a one-to-one map from source symbols to {target_language} \
counterparts, preserving names/conventions so the port is traceable.
  3. Skeleton -- generate a compilable module skeleton that mirrors the source \
layout, with STUBBED signatures (no real logic) plus the mock + unit-test seams \
(trait/interface for the mockable boundaries, a mock impl, and stub test \
modules). {build_verify}
  4. Implementation plan -- a bottom-up, dependency-aware plan for every \
milestone, each with its Part-A and Part-B steps and the tests that gate it.

Write the consolidated plan to {plan}. Stubs only -- no implementation logic \
(that is the Translator's job), but the skeleton MUST compile{unit_run_note}. \
End by confirming {plan} is written and the skeleton builds.
"""

TRANSLATE = """\
You are the Translator. Implement milestone {milestone_id} ({milestone_title}). \
Goal: {milestone_goal}
Mode: {mode}. {repair_clause}

PROJECT BRIEF:
{brief}

{work_location}Load context from {plan} (name mapping + this milestone's Part-A \
and Part-B steps) and {analysis} (design + mockable-seam strategy). Faithfully \
reproduce the {source_language} behavior from {source_dir}.

Part A -- replace stubs with real {target_language} logic for this milestone, in \
dependency order, reproducing the observable contract. Part B -- translate this \
milestone's behavioral unit tests and add new unit tests for the new code, \
running against the mock seams so they execute standalone.

Language adaptation: exceptions -> the target's error type, null -> option \
types, keep the program resilient. {build_verify} Iterate until the build and \
unit tests are clean. Never modify the immutable input, the end-to-end tests, or \
provided scaffolding. End by stating what you implemented/repaired (Part A + \
Part B) and confirming the build + unit tests pass.
"""

VALIDATE = """\
You are the Validator. Independently validate milestone {milestone_id} \
({milestone_title}) at two layers and write a single combined verdict to \
{report}. You only RUN tests and report -- never edit the implementation, the \
tests, or the scaffolding.

PROJECT BRIEF:
{brief}

Validate the {work_target}:
  1. Unit layer (fast, mocked): run `{unit_test}`. Record total/passed/failed and \
each failing test's name + assertion.
  2. End-to-end layer (authoritative oracle): run `{validate}`. Its cumulative \
gate for this milestone is {gate_desc}. A build failure counts as a validation \
failure.{skip_note}

Write {report} as JSON: {report_shape}. `passed` is true ONLY if BOTH layers \
fully pass. For each failing test give an actionable entry: the layer, the exact \
test id (so it can be recorded for deferral if this milestone is later skipped), \
the assertion essence, the likely output-contract or behavior at fault, and a \
repair hint naming the probable source fragment / target module. End by stating \
the per-layer pass/fail + counts, the combined verdict, and the top failures \
with repair hints.
"""

_REPORT_SHAPE = (
    '{"milestone","passed","tests":{"unit":{"total","passed","failed"},'
    '"e2e":{"total","passed","failed"}},"failures":[{"layer","test",'
    '"symptom","likely_cause","repair_hint"}]}'
)

# --------------------------------------------------------------------------- #
# Optimize phase (phase 2 -- performance). Only rendered when it is enabled.
# --------------------------------------------------------------------------- #
BENCHMARK = """\
You are the Benchmarker. Measure the performance of the {work_target}; do NOT \
change anything. You have no edit tool -- if a run fails, report the failure \
rather than working around it.

PROJECT BRIEF:
{brief}

Benchmark round {opt_round}. Run EXACTLY this command and let it finish:
    {benchmark_cmd}
{scenario_note}
Then read {bench} and VERIFY before reporting: it names the target you were \
asked to measure and was produced by this run; every scenario THAT WAS \
REQUESTED produced a record for each variant being compared; and none reports \
null, skipped, or an error field. Report a compact per-scenario summary with \
the comparison ratios, then state plainly whether the run is usable evidence.

Pass through any note or caveat the artifact carries on a scenario VERBATIM \
rather than deciding yourself whether it matters -- the Optimizer interprets \
the numbers, you report them.

Do not edit anything. Do not re-run a scenario until it gives a nicer number. \
Do not fill a missing or null value with an estimate, an earlier run's figure, \
or a plausible guess.
"""

OPTIMIZE = """\
You are the Optimizer. Improve the PERFORMANCE of the {work_target} without \
changing its observable behaviour. This is optimisation round {opt_round} of \
{max_opt_rounds}.

PROJECT BRIEF:
{brief}

{work_location}The translation is already CORRECT -- every milestone passed and \
the parity verifier confirmed full source coverage. Your job is to make it \
faster while keeping it correct.
{scenario_note}
EVIDENCE (read it before touching code): {bench} holds this round's \
measurements and {optimize_history} holds every previous round. Do not optimise \
from intuition -- if the numbers do not point at your idea, it is the wrong \
idea. Do not repeat an idea an earlier round already tried.

MAKE ONE SMALL FOCUSED CHANGE SET: one coherent idea, small enough that a later \
failure can be traced to it. Prefer, in order: (1) removing redundant work, \
(2) reducing I/O round trips, (3) avoiding needless copies/allocations, and \
only then (4) concurrency or build-profile changes, which are the easiest to \
get subtly wrong. "Rewrite the X subsystem" and "three unrelated tweaks" are \
bad rounds.

THE ONE RULE: do not change WHAT the code does, only HOW. The implementation is \
graded as a black box against the same tests the translation had to pass -- same \
inputs must produce the same observable outputs, in an order no observer can \
distinguish. A change that is faster BECAUSE it does less observable work is a \
behaviour change: reject it yourself. Read the surrounding code first -- the \
translation mirrors the source deliberately, and a construct that looks \
redundant may be preserving source behaviour.

ROUNDS ACCUMULATE: your change stays and the next round builds on it. The \
ENTIRE test suite runs once after the final round as a normal milestone, and \
anything it catches is REPAIRED there rather than thrown away -- so do not \
gamble on a change you cannot justify, but do not refuse a well-evidenced one \
for fear of a revert.

Before finishing, run `{unit_test}` and make sure it passes. This is the only \
automatic gate between rounds, so a broken tree here compounds into every later \
round. If your change breaks a unit test, fix the change or undo it -- do NOT \
weaken the test.

Then write {optimize_artifact} as JSON: {optimize_shape}. `files` must list \
EVERY file you touched (the pipeline records this as the change set, so an \
incomplete list makes a later regression untraceable). `rationale` must cite \
the numbers that motivated the change, and `expected_effect` is a prediction \
the next benchmark will check.

If there is no meaningful and safe change left, say so: write it with \
"title": "no further safe optimisation identified" and an honest explanation. A \
round that changes nothing is a legitimate result -- inventing a marginal change \
carries regression risk for no measured gain.
"""

_OPTIMIZE_SHAPE = (
    '{"round","title","files":[...],"rationale","expected_effect",'
    '"behaviour_risk","unit_tests","measured_before":{...}}'
)

DEFAULTS: dict[str, str] = {
    "scope": SCOPE,
    "analyze": ANALYZE,
    "plan": PLAN,
    "translate": TRANSLATE,
    "validate": VALIDATE,
    "parity": PARITY,
    "benchmark": BENCHMARK,
    "optimize": OPTIMIZE,
}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _fmt_paths(paths) -> str:
    return ", ".join(str(p) for p in paths) if paths else "(none)"


def context(cfg: Config, **runtime: Any) -> dict[str, str]:
    """Build the placeholder namespace for a stage template."""
    wc = cfg.working_copy_path
    imm = cfg.immutable_input_path

    # Conditional fragments so the same templates work with or without an
    # immutable-input / working-copy split.
    if wc is not None and imm is not None:
        working_copy_instructions = (
            f"First copy the immutable input {imm} to the working copy {wc} "
            f"(idempotent; never modify {imm}), then work ONLY in {wc}. "
        )
        work_location = f"Work ONLY in the working copy {wc} (never the immutable input {imm}). "
        work_target = f"working copy {wc}"
    elif wc is not None:
        working_copy_instructions = f"Work in {wc}. "
        work_location = f"Work in {wc}. "
        work_target = f"working copy {wc}"
    else:
        working_copy_instructions = ""
        work_location = ""
        work_target = "translated project"

    build_verify = ""
    unit_run_note = ""
    if cfg.build_check_cmd:
        build_verify = f"Verify it compiles with `{cfg.build_check_cmd}`."
    if cfg.unit_test_cmd:
        unit_run_note = f" and `{cfg.unit_test_cmd}` must run"

    ctx = {
        "source_language": cfg.source_language,
        "target_language": cfg.target_language,
        "brief": cfg.brief or "(none provided)",
        "source_dir": str(cfg.source_path),
        "reference_dirs": _fmt_paths(cfg.reference_paths),
        "immutable_input": str(imm) if imm else "(none)",
        "working_copy": str(wc) if wc else "(none)",
        "pipeline_dir": str(cfg.pipeline_path),
        "analysis": str(cfg.analysis_path),
        "plan": str(cfg.plan_path),
        "report": str(cfg.report_path),
        "milestones": str(cfg.milestones_path),
        "parity": str(cfg.parity_path),
        "build_check": cfg.build_check_cmd or "(no build command configured)",
        "unit_test": cfg.unit_test_cmd or "(no unit-test command configured)",
        "validate": cfg.validate_cmd or "(no validate command configured)",
        "working_copy_instructions": working_copy_instructions,
        "work_location": work_location,
        "work_target": work_target,
        "build_verify": build_verify,
        "unit_run_note": unit_run_note,
        "report_shape": _REPORT_SHAPE,
        "optimize_shape": _OPTIMIZE_SHAPE,
        "bench": str(cfg.bench_path),
        "optimize_artifact": str(cfg.optimize_path),
        "optimize_history": str(cfg.optimize_history_path),
        # runtime defaults (overridable via **runtime)
        "milestone_id": "",
        "milestone_title": "",
        "milestone_goal": "",
        "mode": "IMPLEMENT",
        "failures": "[]",
        "gate": "",
        "gate_desc": "",
        "repair_clause": "",
        "scope_mode_note": "",
        "skips": "[]",
        "skip_note": "",
        "opt_round": "",
        "max_opt_rounds": "",
        "benchmark_cmd": "",
        "scenario_note": "",
    }
    ctx.update({k: str(v) for k, v in runtime.items()})
    return ctx


def render(stage: str, cfg: Config, **runtime: Any) -> str:
    template = cfg.prompts.get(stage) or DEFAULTS[stage]
    return template.format(**context(cfg, **runtime))


def translate_runtime(cfg: Config, milestone, report: dict) -> dict[str, str]:
    """Build the translate-stage runtime placeholders (mode + repair clause)."""
    failures = (report or {}).get("failures") or []
    mode = "REPAIR" if failures else "IMPLEMENT"
    repair_clause = ""
    if mode == "REPAIR":
        repair_clause = (
            f"The Validator reported these failures: {json.dumps(failures)}. Do NOT "
            "patch blindly: first investigate WHY each fails -- re-read the failing "
            "tests to see what behavior/output they require, and decide whether each "
            "is a bug in the translated code OR functionality that was never "
            "translated (if so, port the missing source logic). Confirm ALL "
            "functionality this milestone's tests need is translated, then fix the "
            "root cause faithfully."
        )
    return {
        "milestone_id": milestone.id,
        "milestone_title": milestone.title,
        "milestone_goal": milestone.goal,
        "mode": mode,
        "failures": json.dumps(failures),
        "repair_clause": repair_clause,
    }


def validate_runtime(cfg: Config, milestone, skips: list[str] | None = None) -> dict[str, str]:
    skips = [s for s in (skips or []) if s]

    # A full_suite milestone (the one the optimize phase appends) gates on
    # EVERYTHING: the cumulative selector covers only tests some milestone listed,
    # but a performance change can regress anything -- including tests no milestone
    # ever claimed. Deferred skips are NOT deselected here either; a run that
    # silently omits them is not the conformance proof this milestone exists for.
    if getattr(milestone, "full_suite", False):
        return {
            "milestone_id": milestone.id,
            "milestone_title": milestone.title,
            "milestone_goal": milestone.goal,
            "gate": "",
            "gate_desc": "the ENTIRE test suite (no selector -- run everything)",
            "validate": cfg.full_suite_command(milestone.id),
            "skips": json.dumps(skips),
            "skip_note": (
                " NOTE: this milestone follows the optimize phase, where the code was "
                "changed for performance under only the unit tests. Run the WHOLE suite "
                "with no selector: every behaviour is in scope, including tests no "
                "milestone listed."
                + (f" The {len(skips)} test(s) deferred earlier ({json.dumps(skips)}) are "
                   "included here on purpose -- report them honestly rather than "
                   "deselecting them." if skips else "")
            ),
        }

    gate = milestones.gate_string(cfg, milestone.id, skips=skips)
    skip_note = ""
    if skips:
        excl = milestones.skip_exclusion(cfg, skips)
        skip_note = (
            f" NOTE: {len(skips)} test(s) are known-failing and DEFERRED by earlier "
            f"milestones (skip-on-give-up): {json.dumps(skips)}. "
            + (f"They are already deselected in the gate above ({excl}); "
               if excl else
               "Deselect them from your test selection; ")
            + "do NOT count them as failures and do NOT force-run them."
        )
    return {
        "milestone_id": milestone.id,
        "milestone_title": milestone.title,
        "milestone_goal": milestone.goal,
        "gate": gate,
        "gate_desc": gate or "(deploy/smoke only -- no test selector)",
        "skips": json.dumps(skips),
        "skip_note": skip_note,
    }


def scope_runtime(cfg: Config, incremental: bool) -> dict[str, str]:
    """Runtime placeholders for the scope stage. On a parity re-entry
    (``incremental``) the scoper is told to append milestones for the reported
    gaps only, preserving the existing matrix."""
    note = ""
    if incremental:
        note = SCOPE_INCREMENTAL_NOTE.format(
            milestones=str(cfg.milestones_path), parity=str(cfg.parity_path)
        )
    return {"scope_mode_note": note}


# --------------------------------------------------------------------------- #
# Optimize phase
# --------------------------------------------------------------------------- #
def _benchmark_focus(scenarios: list[str]) -> str:
    """Told to the BENCHMARKER: report exactly what was asked for."""
    if not scenarios:
        return ""
    ids = ", ".join(scenarios)
    return (
        f"\nThis run is SCOPED to {ids} ONLY -- the command above already says so. "
        "Do not add scenarios that were not asked for, and do not report the "
        "others as missing: they were deliberately not run.\n"
    )


def _optimize_focus(scenarios: list[str]) -> str:
    """Told to the OPTIMIZER: the same set, plus what scoping costs.

    Both halves resolve the set from one state key on purpose -- scoping one half
    would be worse than not scoping at all (optimising for a scenario nobody
    measured, or measuring one nobody is optimising).
    """
    if not scenarios:
        return ""
    ids = ", ".join(scenarios)
    return (
        f"\nFOCUS: this run targets {ids} ONLY. Those are the only scenarios being "
        "measured, so they are the only evidence you have and the only thing your "
        "change is judged on. Two consequences, stated outright: a change that helps "
        "something NOT in that set is unmeasured here, so you cannot claim it as a "
        "win and should not spend a round on it; and a change that speeds these up "
        "while plausibly slowing something outside the set is still a REGRESSION -- "
        "nothing in this run would catch it, which is exactly why you must not make "
        "it.\n"
    )


def benchmark_runtime(cfg: Config, opt_round: int,
                      scenarios: list[str] | None = None) -> dict[str, str]:
    scen = [s for s in (scenarios or []) if s]
    return {
        "opt_round": str(opt_round),
        "benchmark_cmd": cfg.benchmark_command(scen),
        "scenario_note": _benchmark_focus(scen),
    }


def optimize_runtime(cfg: Config, opt_round: int, max_opt_rounds: int,
                     scenarios: list[str] | None = None) -> dict[str, str]:
    scen = [s for s in (scenarios or []) if s]
    return {
        "opt_round": str(opt_round),
        "max_opt_rounds": str(max_opt_rounds),
        "scenario_note": _optimize_focus(scen),
    }
