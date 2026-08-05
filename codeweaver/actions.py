"""Burr actions: the ReCodeAgent stages as deterministic nodes.

Each action either (a) invokes a Copilot custom agent via invoke_agent() and
reads the artifact it wrote to the pipeline dir, or (b) does pure bookkeeping
(select_milestone). No LLM logic lives here -- the agents own that. Everything
project-specific comes from the active :class:`~codeweaver.config.Config`.

Stage -> ReCodeAgent mapping:
  analyze           Analyzer agent (once): research source, design target
  plan              Planner agent (once): fragments, name mapping, skeleton, plan
  select_milestone  milestone loop head (advance / init)
  translate         Translator agent: implement / repair the current milestone
  validate          Validator agent: run unit + e2e layers, write the verdict
"""
from __future__ import annotations

import json
from pathlib import Path

from burr.core import action

from . import config as C
from . import milestones, prompts, state as S
from .config import Milestone
from .copilot import invoke_agent, is_mock, summary_from_events, transcript_from_events


def from_mock() -> bool:
    return is_mock()


def _fallback_milestones() -> list[Milestone]:
    """A minimal, generic two-milestone matrix used only if the scoper fails to
    produce a usable one (so a real run degrades gracefully instead of crashing)."""
    return [
        Milestone("M0", "Skeleton",
                  "Target compiles/links and the entrypoint runs; no functional tests yet.",
                  tests=[]),
        Milestone("M1", "Full port",
                  "Implement the full functionality and pass the entire test suite.",
                  tests=[]),
    ]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


# --- skips.json: known-failing tests deferred by skip-on-give-up -------------
# When a milestone exhausts its repair budget (give-up), the tests it could not
# make pass are recorded here so EVERY later milestone's cumulative gate can
# deselect them (via cfg.skip_exclude_template) -- otherwise the same failures
# would drag each later milestone back to max_iter. They are "fix later": the
# parity verifier gives them ONE dedicated retry milestone (re-enabled); if they
# still fail they are skipped permanently.
#   {"tests_to_skip": ["file::test", ...],   # currently deselected
#    "retried":       ["file::test", ...]}     # already got their one retry
def _load_skips_full() -> dict:
    data = _read_json(C.active().skips_path)
    if not isinstance(data, dict):
        data = {}

    def _clean(key):
        return [s for s in data.get(key, []) if isinstance(s, str) and s]

    return {"tests_to_skip": _clean("tests_to_skip"), "retried": _clean("retried")}


def _write_skips(data: dict) -> None:
    p = C.active().skips_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"tests_to_skip": data.get("tests_to_skip", []),
                             "retried": data.get("retried", [])}, indent=2),
                 encoding="utf-8")


def _load_skips() -> list[str]:
    """The actively-deselected tests (tests_to_skip)."""
    return _load_skips_full()["tests_to_skip"]


def _add_skips(test_ids: list[str]) -> list[str]:
    """Merge new test ids into tests_to_skip (dedup, order-preserving)."""
    data = _load_skips_full()
    cur = data["tests_to_skip"]
    seen = set(cur)
    for t in test_ids:
        if t and t not in seen:
            cur.append(t)
            seen.add(t)
    data["tests_to_skip"] = cur
    _write_skips(data)
    return cur


def _eligible_for_retry() -> list[str]:
    """Skipped tests that have NOT yet had their one retry milestone."""
    data = _load_skips_full()
    retried = set(data["retried"])
    return [t for t in data["tests_to_skip"] if t not in retried]


def _begin_retry(test_ids: list[str]) -> None:
    """Start a retry: mark tests retried (permanent record, never a 2nd retry) and
    REMOVE them from tests_to_skip so the retry milestone's gate re-enables them.
    If they fail again, the give-up path re-adds them -- now permanently."""
    data = _load_skips_full()
    ids = [t for t in test_ids if t]
    retried = data["retried"]
    for t in ids:
        if t not in retried:
            retried.append(t)
    keep = set(ids)
    data["tests_to_skip"] = [t for t in data["tests_to_skip"] if t not in keep]
    data["retried"] = retried
    _write_skips(data)


def _permanent_skips() -> list[str]:
    """Tests that were retried and STILL fail -> skipped forever."""
    data = _load_skips_full()
    retried = set(data["retried"])
    return [t for t in data["tests_to_skip"] if t in retried]


def _failing_test_ids(report: dict) -> list[str]:
    """Test ids from a report's failures (any layer), for the skip record."""
    out: list[str] = []
    for f in (report or {}).get("failures", []) or []:
        if isinstance(f, dict) and f.get("test"):
            t = str(f["test"])
            if t not in out:
                out.append(t)
    return out


def _log_agent(tracer, *, stage: str, prompt: str, result) -> dict:
    """Surface a Copilot invocation in the Burr UI (attributes panel)."""
    transcript = transcript_from_events(result.events)
    summary = summary_from_events(result.events)
    if tracer is not None:
        try:
            tracer.log_attributes(
                stage=stage,
                agent=result.agent,
                copilot_prompt=prompt,
                copilot_chat=transcript or (result.final_text or ""),
                final_text=result.final_text or "",
                files_modified=summary["files_modified"],
                lines_added=summary["lines_added"],
                lines_removed=summary["lines_removed"],
                premium_requests=summary["premium_requests"],
                returncode=result.returncode,
                duration_s=round(result.duration_s, 1),
                transcript_log=result.stdout_path or "",
            )
        except Exception as e:  # never let telemetry break the pipeline
            print(f"[codeweaver] warning: failed to log agent attributes: {e}")
    return summary


def _invoke(cfg, agent: str, prompt: str):
    cfg.pipeline_path.mkdir(parents=True, exist_ok=True)
    add_dirs = [str(p) for p in cfg.reference_paths]
    return invoke_agent(
        agent, prompt=prompt, cwd=cfg.root,
        add_dirs=add_dirs, log_dir=cfg.logs_path,
        extra_env=cfg.extra_env(), cfg=cfg,
    )


@action(reads=[], writes=["analysis_done", "last_agent"])
def analyze(state, __tracer) -> dict:
    """Analyzer Agent: research the source and design the target."""
    cfg = C.active()
    prompt = prompts.render("analyze", cfg)
    res = _invoke(cfg, "analyzer", prompt)
    _log_agent(__tracer, stage="analyze", prompt=prompt, result=res)
    return state.update(
        analysis_done=cfg.analysis_path.exists(),
        last_agent="analyzer",
    )


@action(reads=["analysis_done"], writes=["plan_done", "last_agent"])
def plan(state, __tracer) -> dict:
    """Planning Agent: fragments, name mapping, skeleton, milestone plan."""
    cfg = C.active()
    prompt = prompts.render("plan", cfg)
    res = _invoke(cfg, "planner", prompt)
    _log_agent(__tracer, stage="plan", prompt=prompt, result=res)
    return state.update(
        plan_done=cfg.plan_path.exists(),
        last_agent="planner",
    )


@action(
    reads=["analysis_done", "parity_round", "num_milestones"],
    writes=["num_milestones", "last_idx", "milestones_done", "milestone_idx",
            "milestone_passed", "milestone_concluded", "last_agent"],
)
def scope(state, __tracer) -> dict:
    """Scoper Agent (milestone generator). Runs BETWEEN analyze and plan.

    Three modes:
      * declared milestones, first pass -> passthrough: keep the config's matrix
        (just persist it to the artifact so later parity rounds can extend it);
      * no declared milestones, first pass -> generate the initial matrix;
      * parity re-entry (parity_round > 0) -> the Parity Verifier found gaps;
        append NEW milestones for them, preserving the existing matrix, and point
        the loop at the first newly-appended milestone.
    """
    cfg = C.active()
    incremental = state["parity_round"] > 0
    old_count = state["num_milestones"]

    if not incremental and not cfg.auto_milestones:
        # Declared milestones: no LLM call. Persist so incremental rounds have a base.
        cfg.save_milestones()
        n = len(cfg.milestones)
        return state.update(
            num_milestones=n, last_idx=max(n - 1, 0),
            milestones_done=True, milestone_idx=0,
            milestone_passed=False, milestone_concluded=False,
            last_agent=state["last_agent"],
        )

    runtime = prompts.scope_runtime(cfg, incremental=incremental)
    prompt = prompts.render("scope", cfg, **runtime)
    res = _invoke(cfg, "scoper", prompt)
    _log_agent(__tracer, stage=f"scope:{'incremental' if incremental else 'initial'}",
               prompt=prompt, result=res)
    n = cfg.load_generated_milestones()
    if n == 0 and not from_mock():
        # The scoper failed to produce a usable matrix; fall back so the run can
        # still proceed rather than crashing with an empty milestone list.
        cfg.milestones = _fallback_milestones()
        cfg.save_milestones()
        n = len(cfg.milestones)
    # On a re-scope, continue from the first newly-appended milestone (do not re-run
    # the ones already concluded); on the first pass, start at M0.
    first_pending = old_count if incremental else 0
    if first_pending >= n:                       # defensive clamp
        first_pending = max(0, n - 1)
    if __tracer is not None:
        try:
            __tracer.log_attributes(
                incremental=incremental,
                milestones_generated=n,
                milestone_ids=[m.id for m in cfg.milestones],
            )
        except Exception:
            pass
    return state.update(
        num_milestones=n,
        last_idx=max(n - 1, 0),
        milestones_done=n > 0,
        milestone_idx=first_pending,
        milestone_passed=False,
        milestone_concluded=False,
        last_agent="scoper",
    )


@action(
    reads=["parity_round", "max_parity_rounds", "num_milestones"],
    writes=["parity_complete", "parity_report", "parity_round", "done", "history",
            "last_agent", "retry_pending", "num_milestones", "last_idx",
            "milestone_idx", "milestone_passed", "milestone_concluded", "iter_count"],
)
def parity(state, __tracer) -> dict:
    """Parity Verifier: after all milestones conclude, compare source vs. translation
    and decide whether everything in scope is translated.

    It also revisits skips.json (tests earlier milestones gave up on): any skipped
    test that hasn't had its retry gets ONE dedicated retry milestone (re-enabled)
    and the graph loops back to run it. Otherwise: gaps + budget -> re-scope;
    complete -> done. Parity-budget-exhausted-with-gaps is a hard failure.
    """
    cfg = C.active()
    prompt = prompts.render("parity", cfg)
    res = _invoke(cfg, "parity", prompt)
    report = _read_json(cfg.parity_path)
    complete = bool(report.get("complete"))
    rnd = state["parity_round"] + 1

    # Give un-retried deferred tests ONE dedicated retry milestone.
    eligible = _eligible_for_retry()
    have_budget = state["parity_round"] < state["max_parity_rounds"]
    retry_pending = bool(eligible) and have_budget

    upd = dict(
        parity_complete=complete,
        parity_report=report,
        parity_round=rnd,
        last_agent="parity",
        retry_pending=retry_pending,
    )
    entry = {"milestone": "PARITY", "iter": rnd, "passed": complete}

    if retry_pending:
        # Append ONE retry milestone that re-enables the eligible skipped tests and
        # route the loop back to it. _begin_retry marks them retried (their one shot)
        # and un-defers them so the retry actually runs them.
        base = len(cfg.milestones)
        nid = f"M{base}"
        deps = [cfg.milestones[-1].id] if cfg.milestones else []
        retry_m = Milestone(
            nid, "Retry deferred tests",
            "Fix and re-enable the previously-skipped tests so they pass: "
            f"{json.dumps(eligible)}. Implement the functionality they exercise; they "
            "are re-enabled in this milestone's gate. If they still cannot pass, they "
            "are skipped permanently.",
            tests=[], origin="retry",
        )
        cfg.milestones = list(cfg.milestones) + [retry_m]
        cfg.save_milestones()
        _begin_retry(eligible)
        upd.update(
            num_milestones=base + 1,
            last_idx=base,
            milestone_idx=base,
            milestone_passed=False,
            milestone_concluded=False,
            iter_count=0,
            done=False,
        )
        entry["retry_for"] = eligible
    else:
        upd["done"] = complete   # success iff full source coverage

    _log_agent(__tracer, stage=f"parity:round{rnd}", prompt=prompt, result=res)
    if __tracer is not None:
        try:
            __tracer.log_attributes(parity_round=rnd, parity_complete=complete,
                                    parity_missing=report.get("missing", []),
                                    retry_pending=retry_pending,
                                    retry_tests=eligible if retry_pending else [],
                                    permanent_skips=_permanent_skips())
        except Exception:
            pass
    return state.update(**upd).append(history=entry)


@action(
    reads=["milestone_idx", "milestone_concluded"],
    writes=["milestone_idx", "iter_count", "milestone_passed", "milestone_concluded"],
)
def select_milestone(state) -> dict:
    """Loop head: initialise (from plan/scope) or advance (after a milestone concludes).

    A milestone "concludes" when validate either passes it OR exhausts the repair
    budget (give-up). In both cases we advance to the next milestone -- a stuck
    milestone is skipped rather than failing the run (its untranslated behaviour is
    caught by the parity verifier). On first entry (from plan, after a re-scope, or
    a parity retry) ``milestone_concluded`` is False, so we start the current
    milestone without advancing. Always reset the per-milestone counters/flags.
    """
    idx = state["milestone_idx"]
    if state["milestone_concluded"]:      # re-entered after this milestone concluded
        idx += 1
    return state.update(milestone_idx=idx, iter_count=0,
                        milestone_passed=False, milestone_concluded=False)


@action(reads=["milestone_idx", "iter_count", "report"], writes=["last_agent"])
def translate(state, __tracer) -> dict:
    """Translator Agent: implement the current milestone; repair if report != {}."""
    cfg = C.active()
    m = S.current_milestone(cfg, state)
    runtime = prompts.translate_runtime(cfg, m, state["report"] or {})
    prompt = prompts.render("translate", cfg, **runtime)
    res = _invoke(cfg, "translator", prompt)
    _log_agent(__tracer, stage=f"translate:{m.id}:{runtime['mode']}", prompt=prompt, result=res)
    return state.update(last_agent="translator")


@action(
    reads=["milestone_idx", "iter_count", "max_iter", "skipped"],
    writes=["milestone_passed", "milestone_concluded", "iter_count", "report",
            "history", "skipped", "done", "last_agent"],
)
def validate(state, __tracer) -> dict:
    """Validator Agent: run unit + e2e layers; write the authoritative report.

    A milestone "concludes" when it passes OR the repair budget is exhausted. With
    skip-on-give-up (default), give-up does NOT fail the run: the still-failing
    tests are recorded in skips.json (deselected from later milestones) and the loop
    advances; the parity verifier revisits skips.json and gives them one retry.
    """
    cfg = C.active()
    m = S.current_milestone(cfg, state)
    skips = _load_skips()
    runtime = prompts.validate_runtime(cfg, m, skips=skips)
    prompt = prompts.render("validate", cfg, **runtime)
    res = _invoke(cfg, "validator", prompt)
    report = _read_json(cfg.report_path)
    passed = bool(report.get("passed"))
    it = state["iter_count"] + 1

    # Give up when the budget is exhausted. With skip_on_give_up we still "conclude"
    # the milestone (advance/skip); otherwise give-up leaves it un-concluded so the
    # graph's default edge routes to terminal (hard fail, legacy behaviour).
    budget_out = (not passed) and (it >= state["max_iter"])
    gave_up = budget_out and cfg.skip_on_give_up
    concluded = passed or gave_up
    # done only in the parity-off case: success == the LAST milestone passed with no
    # skips outstanding. With parity on, parity owns completion.
    n_skipped = len(state["skipped"]) + (1 if gave_up else 0)
    done = (not cfg.parity_check) and passed and S.is_last_milestone(cfg, state) and n_skipped == 0

    entry = {"milestone": m.id, "iter": it, "passed": passed, "gave_up": gave_up}

    newly_skipped: list[str] = []
    if gave_up:
        newly_skipped = _failing_test_ids(report)
        if newly_skipped:
            _add_skips(newly_skipped)

    _log_agent(__tracer, stage=f"validate:{m.id}", prompt=prompt, result=res)
    if __tracer is not None:
        try:
            __tracer.log_attributes(milestone=m.id, milestone_passed=passed,
                                    gave_up=gave_up, deselected_tests=skips,
                                    newly_skipped_tests=newly_skipped,
                                    report_tests=report.get("tests", {}),
                                    report_failures=report.get("failures", []))
        except Exception:
            pass
    new = state.update(
        milestone_passed=passed,
        milestone_concluded=concluded,
        iter_count=it,
        report={} if passed else report,   # clear on pass so next milestone is fresh
        done=done,
        last_agent="validator",
    ).append(history=entry)
    if gave_up:
        new = new.append(skipped=m.id)     # record the skipped milestone for the verdict
    return new
