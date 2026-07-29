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
    reads=["analysis_done", "parity_round"],
    writes=["num_milestones", "last_idx", "milestones_done", "last_agent"],
)
def scope(state, __tracer) -> dict:
    """Scoper Agent (milestone generator). Runs BETWEEN analyze and plan.

    Three modes:
      * declared milestones, first pass -> passthrough: keep the config's matrix
        (just persist it to the artifact so later parity rounds can extend it);
      * no declared milestones, first pass -> generate the initial matrix;
      * parity re-entry (parity_round > 0) -> the Parity Verifier found gaps;
        append NEW milestones for them, preserving the existing matrix.
    """
    cfg = C.active()
    incremental = state["parity_round"] > 0

    if not incremental and not cfg.auto_milestones:
        # Declared milestones: no LLM call. Persist so incremental rounds have a base.
        cfg.save_milestones()
        n = len(cfg.milestones)
        return state.update(
            num_milestones=n, last_idx=max(n - 1, 0),
            milestones_done=True, last_agent=state["last_agent"],
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
        last_agent="scoper",
    )


@action(
    reads=["parity_round", "max_parity_rounds"],
    writes=["parity_complete", "parity_report", "parity_round", "done", "last_agent"],
)
def parity(state, __tracer) -> dict:
    """Parity Verifier: after all milestones pass, compare the source with the
    translation and decide whether everything in scope has been translated. On
    completion the run finishes; otherwise the graph loops back to `scope` (the
    milestone generator) to schedule the gaps -- bounded by max_parity_rounds."""
    cfg = C.active()
    prompt = prompts.render("parity", cfg)
    res = _invoke(cfg, "parity", prompt)
    report = _read_json(cfg.parity_path)
    complete = bool(report.get("complete"))
    rnd = state["parity_round"] + 1
    _log_agent(__tracer, stage=f"parity:round{rnd}", prompt=prompt, result=res)
    if __tracer is not None:
        try:
            __tracer.log_attributes(parity_round=rnd, parity_complete=complete,
                                    parity_missing=report.get("missing", []))
        except Exception:
            pass
    return state.update(
        parity_complete=complete,
        parity_report=report,
        parity_round=rnd,
        done=complete,   # success == parity verified complete
        last_agent="parity",
    )


@action(
    reads=["milestone_idx", "milestone_passed"],
    writes=["milestone_idx", "iter_count", "milestone_passed"],
)
def select_milestone(state) -> dict:
    """Loop head: initialise (from plan) or advance (after a pass).

    On re-entry after a pass, advance to the next milestone; always reset the
    per-milestone repair counter and the passed flag.
    """
    idx = state["milestone_idx"]
    if state["milestone_passed"]:
        idx += 1
    return state.update(milestone_idx=idx, iter_count=0, milestone_passed=False)


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
    reads=["milestone_idx", "iter_count"],
    writes=["milestone_passed", "iter_count", "report", "history", "done", "last_agent"],
)
def validate(state, __tracer) -> dict:
    """Validator Agent: run unit + e2e layers; write the authoritative report."""
    cfg = C.active()
    m = S.current_milestone(cfg, state)
    runtime = prompts.validate_runtime(cfg, m)
    prompt = prompts.render("validate", cfg, **runtime)
    res = _invoke(cfg, "validator", prompt)
    report = _read_json(cfg.report_path)
    passed = bool(report.get("passed"))
    it = state["iter_count"] + 1
    # When parity is enabled, finishing the last milestone routes to the parity
    # stage (not terminal), so `done` stays False here; parity owns completion.
    done = passed and S.is_last_milestone(cfg, state) and not cfg.parity_check
    entry = {"milestone": m.id, "iter": it, "passed": passed}
    _log_agent(__tracer, stage=f"validate:{m.id}", prompt=prompt, result=res)
    if __tracer is not None:
        try:
            __tracer.log_attributes(milestone=m.id, milestone_passed=passed,
                                    report_tests=report.get("tests", {}),
                                    report_failures=report.get("failures", []))
        except Exception:
            pass
    return state.update(
        milestone_passed=passed,
        iter_count=it,
        report={} if passed else report,   # clear on pass so next milestone is fresh
        done=done,
        last_agent="validator",
    ).append(history=entry)
