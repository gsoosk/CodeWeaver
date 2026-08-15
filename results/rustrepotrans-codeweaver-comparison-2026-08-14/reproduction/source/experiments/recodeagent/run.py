"""run.py -- resumable/idempotent execution driver for the ReCodeAgent
reproduction matrix: every (variant, project_id, repetition) combination.

Variants (see common.RUN_VARIANTS, exactly the paper's RQ3 matrix):
  full                  the REAL CodeWeaver pipeline, invoked as
                        ``python -m codeweaver run --config <config> --app-id <id>``
                        (a subprocess -- the full Burr graph, milestone loop,
                        and parity loop run exactly as they would for any other
                        CodeWeaver project; genuinely resumable via Burr's own
                        SQLite persister + a stable --app-id).
  noanalyzer            the full persisted CodeWeaver graph with exactly the
  noplanning            named agent stage deterministically omitted and a
  novalidator           clearly labeled placeholder artifact written in its
                        place. Milestone, repair, and parity behavior otherwise
                        remains identical to ``full``.
  baseagent-condensed   ONE autonomous copilot call (no ``--agent``, no stage
  baseagent-concat      decomposition), same model/effort/timeout budget as
                        the full pipeline's defaults.

The three named stage ablations are implemented by the default-off
``CODEWEAVER_SKIP_STAGES`` experiment hook in CodeWeaver's public CLI
subprocess. They therefore use the same Burr graph and SQLite crash-resume
semantics as ``full``. Base-agent variants remain one-shot and are always
cleanly rematerialized after an interrupted or failed attempt.

Safety: every subprocess invocation goes through common.run_argv (argument
arrays only) or codeweaver.copilot.invoke_agent (which itself never uses a
shell). The sole core hook used by the named ablations is default-off and
does not alter ordinary CodeWeaver runs.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from experiments.recodeagent import common as C
from experiments.recodeagent import prepare as P
from experiments.recodeagent.common import (
    ExecResult,
    Status,
    atomic_write_json,
    collect_provenance,
    read_json_or,
    run_argv,
    slugify,
    summarize_copilot_events,
    utcnow_iso,
)

STATE_FILENAME = "recodeagent_run_state.json"
CALLS_FILENAME = "recodeagent_calls.jsonl"

STAGE_TO_AGENT = {
    "analyze": "analyzer", "scope": "scoper", "plan": "planner",
    "translate": "translator", "validate": "validator",
}
# The three named single-stage-skip ablations from the paper's RQ3 matrix.
STAGE_SKIP_VARIANTS = {"noanalyzer": "analyze", "noplanning": "plan", "novalidator": "validate"}
BASEAGENT_VARIANTS = {"baseagent-condensed", "baseagent-concat"}


# --------------------------------------------------------------------------- #
# Deterministic naming
# --------------------------------------------------------------------------- #
def run_dir_for(runs_root: str | Path, variant: str, project_id: str, repetition: int) -> Path:
    return Path(runs_root) / variant / project_id / f"rep{repetition}"


def app_id_for(variant: str, project_id: str, repetition: int) -> str:
    return slugify(f"{variant}-{project_id}-rep{repetition}")[:60]


# --------------------------------------------------------------------------- #
# Run state: atomic, resumable, idempotent
# --------------------------------------------------------------------------- #
def state_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / STATE_FILENAME


def load_run_state(run_dir: str | Path) -> dict[str, Any] | None:
    return read_json_or(state_path(run_dir), None)


def save_run_state(run_dir: str | Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utcnow_iso()
    atomic_write_json(state_path(run_dir), state)


def new_run_state(variant: str, project_id: str, repetition: int, run_dir: Path) -> dict[str, Any]:
    now = utcnow_iso()
    return {
        "variant": variant, "project_id": project_id, "repetition": repetition,
        "status": "pending", "app_id": app_id_for(variant, project_id, repetition),
        "workspace_dir": str(run_dir), "argv": None, "returncode": None, "attempt": 0,
        "created_at": now, "updated_at": now, "started_at": None, "ended_at": None,
        "timeout_seconds": None, "error": "", "provenance": {},
    }


# --------------------------------------------------------------------------- #
# Agent-call result record (uniform across full/ablation/baseagent)
# --------------------------------------------------------------------------- #
@dataclass
class AgentCallResult:
    stage: str
    kind: str                      # "invoke" | "placeholder" | "raw" | "cli"
    agent: str | None
    ok: bool
    returncode: int | None
    duration_s: float
    timed_out: bool = False
    model: str | None = None
    effort: str | None = None
    prompt_chars: int = 0
    stdout_path: str | None = None
    events_summary: dict[str, Any] | None = None
    error: str = ""
    started_at: str = ""
    ended_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _agent_call_from_agent_result(stage: str, agent: str, prompt: str, model: str, effort: str,
                                  result: Any, started_at: str) -> AgentCallResult:
    """Wrap codeweaver.copilot.AgentResult (or an equivalent fake used in
    tests) into our uniform AgentCallResult."""
    timed_out = result.returncode == 124
    summary = summarize_copilot_events(result.events or [])
    return AgentCallResult(
        stage=stage, kind="invoke", agent=agent, ok=bool(result.ok) and not timed_out,
        returncode=result.returncode, duration_s=result.duration_s, timed_out=timed_out,
        model=model, effort=effort, prompt_chars=len(prompt), stdout_path=result.stdout_path,
        events_summary=summary.to_dict(), started_at=started_at, ended_at=utcnow_iso(),
    )


def _agent_call_placeholder(stage: str, reason: str) -> AgentCallResult:
    now = utcnow_iso()
    return AgentCallResult(stage=stage, kind="placeholder", agent=None, ok=True, returncode=None,
                           duration_s=0.0, error="", started_at=now, ended_at=now,
                           events_summary={"placeholder_reason": reason})


def write_calls_jsonl(run_dir: str | Path, calls: list[AgentCallResult]) -> Path:
    path = Path(run_dir) / CALLS_FILENAME
    if path.exists():
        path.unlink()
    for call in calls:
        C.append_jsonl(path, call.to_dict())
    return path


# --------------------------------------------------------------------------- #
# Executor: the ONLY boundary that actually spawns a process. Tests inject a
# fake Executor so no test ever shells out to `copilot`/`codeweaver`/a real
# toolchain -- see tests/experiments/test_run.py.
# --------------------------------------------------------------------------- #
def _real_run_cli(argv: list[str], *, cwd, timeout, env=None) -> ExecResult:
    return run_argv(argv, cwd=cwd, timeout=timeout, env=env)


def _real_run_agent(agent_name: str, prompt: str, *, cwd, model, effort, add_dirs, timeout,
                    log_dir, cfg, extra_env=None):
    from codeweaver.copilot import invoke_agent  # local import: never touch codeweaver at module load
    return invoke_agent(agent_name, prompt, cwd=cwd, model=model, effort=effort, add_dirs=add_dirs,
                        timeout=timeout, log_dir=log_dir, extra_env=extra_env, cfg=cfg)


def build_raw_copilot_argv(prompt: str, *, model: str, effort: str) -> list[str]:
    """Argv for a no-``--agent`` Copilot invocation (baseagent-* variants).
    Mirrors codeweaver.copilot.invoke_agent's own argv construction (same
    flags/budget) minus ``--agent`` -- that omission IS the ablation."""
    return [
        "copilot", "-p", prompt, "--model", model, "--reasoning-effort", effort,
        "--allow-all", "--no-ask-user", "--output-format", "json", "--no-color",
    ]


def _real_run_raw(prompt: str, *, cwd, model: str, effort: str, timeout, log_dir, env=None) -> ExecResult:
    argv = build_raw_copilot_argv(prompt, model=model, effort=effort)
    return run_argv(argv, cwd=cwd, timeout=timeout, env=env)


@dataclass
class Executor:
    run_cli: Callable[..., ExecResult] = _real_run_cli
    run_agent: Callable[..., Any] = _real_run_agent
    run_raw: Callable[..., ExecResult] = _real_run_raw


# --------------------------------------------------------------------------- #
# Full variant: real CodeWeaver CLI subprocess
# --------------------------------------------------------------------------- #
def build_full_argv(config_path: str | Path, app_id: str) -> list[str]:
    """``python -m codeweaver run --config <config> --app-id <id>`` -- the
    exact existing CodeWeaver CLI entry point, never ``--mock``."""
    return [sys.executable, "-m", "codeweaver", "run", "--config", str(config_path), "--app-id", app_id]


def run_full_variant(config_path: Path, app_id: str, run_dir: Path, *, executor: Executor,
                     timeout: float | None, env: dict[str, str] | None = None
                     ) -> tuple[list[AgentCallResult], ExecResult]:
    argv = build_full_argv(config_path, app_id)
    started = utcnow_iso()
    child_env = ({**os.environ, **env} if env is not None else None)
    exec_result = executor.run_cli(argv, cwd=run_dir, timeout=timeout, env=child_env)
    call = AgentCallResult(
        stage="full_pipeline", kind="cli", agent=None, ok=exec_result.ok,
        returncode=exec_result.returncode, duration_s=exec_result.duration_s,
        timed_out=exec_result.timed_out, prompt_chars=0, started_at=started,
        ended_at=exec_result.ended_at, error=exec_result.error,
    )
    return [call], exec_result


# --------------------------------------------------------------------------- #
# Placeholder artifacts for skipped ablation stages
# --------------------------------------------------------------------------- #
def placeholder_analysis_md(cfg) -> str:
    return (
        "# PLACEHOLDER ANALYSIS (ablation: noanalyzer)\n\n"
        "This artifact was injected by the ReCodeAgent reproduction harness because "
        "the `noanalyzer` ablation variant skips the Analyzer stage entirely. No "
        "design research was performed for this run.\n\n"
        f"- Source: `{cfg.source_dir}`\n- Target language: {cfg.target_language}\n"
        "- Downstream stages must derive the design directly from the source and brief.\n"
    )


def placeholder_plan_json(cfg) -> str:
    import json
    return json.dumps({
        "placeholder": True,
        "reason": "noplanning ablation: planner stage skipped by the ReCodeAgent reproduction harness",
        "fragments": [], "name_map": {},
        "note": "No skeleton or name-map was generated; the translator must derive its own plan "
               "from the analysis and source directly.",
    }, indent=2) + "\n"


def placeholder_report_json(milestone_id: str) -> str:
    import json
    return json.dumps({
        "milestone": milestone_id, "passed": None,
        "placeholder": True,
        "reason": "novalidator ablation: validator stage skipped by the ReCodeAgent reproduction "
                 "harness (no agent-mediated repair loop). Pass/fail is determined objectively by "
                 "collect.py running the project's configured build/unit-test/validate commands "
                 "once against the translator's single-pass output.",
        "tests": {"unit": {"total": None, "passed": None, "failed": None},
                 "e2e": {"total": None, "passed": None, "failed": None}},
        "failures": [],
    }, indent=2) + "\n"


# --------------------------------------------------------------------------- #
# Baseagent prompts (harness-authored -- the paper's own condensed wording is
# not available in this sandbox; documented as an integration assumption)
# --------------------------------------------------------------------------- #
def build_condensed_prompt(cfg) -> str:
    from codeweaver import prompts as cw_prompts
    ctx = cw_prompts.context(cfg)
    return (
        f"You are an autonomous coding agent. Translate the {ctx['source_language']} project at "
        f"{ctx['source_dir']} into idiomatic {ctx['target_language']}, end to end, entirely on your "
        f"own: research the source, design the target, implement it, translate its behavioral unit "
        f"tests (and add new ones as needed), and validate your work by running "
        f"`{ctx['build_check']}`, `{ctx['unit_test']}` and `{ctx['validate']}` yourself until they "
        f"pass. Finally compare the complete source and target component by component and close "
        f"any remaining parity gaps. Consult reference material at {ctx['reference_dirs']} as "
        f"read-only context.\n\n"
        f"PROJECT BRIEF:\n{ctx['brief']}\n\n"
        f"{ctx['working_copy_instructions']}Never modify the source, any immutable input, or "
        f"provided scaffolding/tests. Do not fabricate a passing result -- only report success "
        f"backed by actual command output. When done, summarize what you implemented and confirm "
        f"the build and tests pass."
    )


def build_concat_prompt(cfg) -> str:
    """Literal concatenation of all six CodeWeaver role prompts, each rendered
    with this project's own context, under clear section headers -- one
    autonomous prompt with no role/agent decomposition."""
    from codeweaver import prompts as cw_prompts

    sections = []
    for stage in ("analyze", "scope", "plan"):
        sections.append(f"## Responsibility: {stage}\n{cw_prompts.render(stage, cfg)}")
    sections.append(
        "## Responsibility: translate\n"
        + cw_prompts.render("translate", cfg, **cw_prompts.translate_runtime(cfg, _full_milestone(), {}))
    )
    sections.append(
        "## Responsibility: validate\n"
        + cw_prompts.render("validate", cfg, **_validate_runtime_for_full(cfg))
    )
    sections.append("## Responsibility: parity\n" + cw_prompts.render("parity", cfg))
    return (
        "You are a single autonomous coding agent responsible for ALL of the following "
        "translation-pipeline responsibilities yourself, in order, without any other agent's help:\n\n"
        + "\n\n".join(sections)
    )


def _full_milestone():
    from codeweaver.config import Milestone
    return Milestone(id="FULL", title="Full translation",
                     goal="Translate and validate the entire project end-to-end.", tests=[], marker="")


def _validate_runtime_for_full(cfg) -> dict[str, str]:
    from codeweaver import milestones as cw_milestones
    m = _full_milestone()
    gate = ""
    if cfg.milestones:
        gate = cw_milestones.gate_string(cfg, cfg.milestones[-1].id)
    return {"milestone_id": m.id, "milestone_title": m.title, "milestone_goal": m.goal,
           "gate": gate, "gate_desc": gate or "(full-suite gate)"}


# --------------------------------------------------------------------------- #
# Ablation single-pass staged driver
# --------------------------------------------------------------------------- #
def _invoke_stage(executor: Executor, cfg, stage: str, prompt: str, *, timeout: float | None,
                  model: str | None = None, effort: str | None = None) -> AgentCallResult:
    agent_name = STAGE_TO_AGENT[stage]
    cfg.pipeline_path.mkdir(parents=True, exist_ok=True)
    add_dirs = [str(p) for p in cfg.reference_paths]
    started = utcnow_iso()
    result = executor.run_agent(
        agent_name, prompt, cwd=cfg.root, model=model or cfg.model.default,
        effort=effort or cfg.model.effort_for(agent_name), add_dirs=add_dirs, timeout=timeout,
        log_dir=cfg.logs_path, cfg=cfg, extra_env=cfg.extra_env(),
    )
    return _agent_call_from_agent_result(stage, agent_name, prompt, model or cfg.model.default,
                                         effort or cfg.model.effort_for(agent_name), result, started)


def run_ablation_variant(variant: str, cfg, *, executor: Executor,
                         timeout: float | None) -> list[AgentCallResult]:
    from codeweaver import prompts as cw_prompts

    skip_stage = STAGE_SKIP_VARIANTS.get(variant)
    calls: list[AgentCallResult] = []

    # 1. analyze
    if skip_stage == "analyze":
        C.atomic_write_text(cfg.analysis_path, placeholder_analysis_md(cfg))
        calls.append(_agent_call_placeholder("analyze", "noanalyzer ablation: analyzer stage skipped"))
    else:
        calls.append(_invoke_stage(executor, cfg, "analyze", cw_prompts.render("analyze", cfg), timeout=timeout))

    # 2. scope (always run for these three named ablations -- not itself a
    #    named ablation target; produces the milestone matrix used only to
    #    compute a whole-suite validate gate below).
    calls.append(_invoke_stage(executor, cfg, "scope",
                               cw_prompts.render("scope", cfg, **cw_prompts.scope_runtime(cfg, False)),
                               timeout=timeout))
    cfg.load_generated_milestones()

    # 3. plan
    if skip_stage == "plan":
        C.atomic_write_text(cfg.plan_path, placeholder_plan_json(cfg))
        calls.append(_agent_call_placeholder("plan", "noplanning ablation: planner stage skipped"))
    else:
        calls.append(_invoke_stage(executor, cfg, "plan", cw_prompts.render("plan", cfg), timeout=timeout))

    # 4. translate (single pass over the whole project as one "FULL" milestone
    #    -- see module docstring for why there is no per-milestone repair loop)
    milestone = _full_milestone()
    translate_runtime = cw_prompts.translate_runtime(cfg, milestone, {})
    calls.append(_invoke_stage(executor, cfg, "translate",
                               cw_prompts.render("translate", cfg, **translate_runtime), timeout=timeout))

    # 5. validate
    if skip_stage == "validate":
        C.atomic_write_text(cfg.report_path, placeholder_report_json(milestone.id))
        calls.append(_agent_call_placeholder("validate", "novalidator ablation: validator stage skipped"))
    else:
        calls.append(_invoke_stage(executor, cfg, "validate",
                                   cw_prompts.render("validate", cfg, **_validate_runtime_for_full(cfg)),
                                   timeout=timeout))
    return calls


def run_baseagent_variant(variant: str, cfg, *, executor: Executor, timeout: float | None) -> list[AgentCallResult]:
    prompt = build_condensed_prompt(cfg) if variant == "baseagent-condensed" else build_concat_prompt(cfg)
    cfg.pipeline_path.mkdir(parents=True, exist_ok=True)
    log_dir = cfg.logs_path
    started = utcnow_iso()
    exec_result = executor.run_raw(prompt, cwd=cfg.root, model=cfg.model.default,
                                   effort=cfg.model.effort_default, timeout=timeout, log_dir=log_dir,
                                   env=None)
    events = C.parse_copilot_jsonl(exec_result.stdout)
    summary = summarize_copilot_events(events)
    stdout_path = None
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        stdout_path = str(Path(log_dir) / "baseagent.stdout.jsonl")
        C.atomic_write_text(stdout_path, exec_result.stdout)
        C.atomic_write_text(Path(log_dir) / "baseagent.stderr.log", exec_result.stderr)
    error = (
        exec_result.error
        or _copilot_event_error(events)
        or _tail(exec_result.stderr)
        or _tail(exec_result.stdout)
        or (f"copilot CLI exited with returncode={exec_result.returncode}" if not exec_result.ok else "")
    )
    call = AgentCallResult(
        stage="baseagent", kind="raw", agent=None, ok=exec_result.ok,
        returncode=exec_result.returncode, duration_s=exec_result.duration_s,
        timed_out=exec_result.timed_out, model=cfg.model.default, effort=cfg.model.effort_default,
        prompt_chars=len(prompt), stdout_path=stdout_path, events_summary=summary.to_dict(),
        error=error, started_at=started, ended_at=exec_result.ended_at,
    )
    return [call]


# --------------------------------------------------------------------------- #
# Dry-run planning (pure: reads the already-prepared config, executes nothing)
# --------------------------------------------------------------------------- #
def describe_plan(variant: str, prepared_config_path: Path, app_id: str) -> dict[str, Any]:
    from codeweaver import config as cw_config

    cfg = cw_config.load(prepared_config_path)
    if variant == "full" or variant in STAGE_SKIP_VARIANTS:
        plan = {"variant": variant, "kind": "cli",
                "argv": build_full_argv(prepared_config_path, app_id)}
        if variant in STAGE_SKIP_VARIANTS:
            plan["skip_stage"] = STAGE_SKIP_VARIANTS[variant]
            plan["execution_mode"] = "full_burr_graph"
        return plan
    if variant in BASEAGENT_VARIANTS:
        prompt = build_condensed_prompt(cfg) if variant == "baseagent-condensed" else build_concat_prompt(cfg)
        return {"variant": variant, "kind": "raw", "stages": ["baseagent"], "prompt_chars": len(prompt),
               "model": cfg.model.default, "effort": cfg.model.effort_default}
    raise ValueError(f"unsupported variant: {variant}")


# --------------------------------------------------------------------------- #
# Timeout resolution
# --------------------------------------------------------------------------- #
def resolve_agent_timeout(cli_timeout: float | None, protocol: dict[str, Any]) -> float | None:
    if cli_timeout is not None:
        return cli_timeout
    return float(protocol.get("agent_timeout_seconds", 5000))


def _tail(text: str | None, n: int = 800) -> str:
    """Last ``n`` characters of ``text`` (for a compact-but-actionable error
    message), or "" if there's nothing to show."""
    if not text:
        return ""
    text = text.strip()
    return text[-n:] if len(text) > n else text


def _copilot_event_error(events: list[dict[str, Any]]) -> str:
    """Return the last actionable Copilot error instead of a result-JSON tail."""
    for event in reversed(events):
        data = event.get("data") or {}
        if event.get("type") == "session.error" and data.get("message"):
            return str(data["message"])
        if event.get("type") == "model.call_failure" and data.get("errorMessage"):
            return str(data["errorMessage"]).strip('"')
    return ""


# --------------------------------------------------------------------------- #
# Top-level per-job orchestration
# --------------------------------------------------------------------------- #
def run_one(
    variant: str,
    project_id: str,
    repetition: int,
    *,
    workspace_root: Path,
    runs_root: Path,
    protocol: dict[str, Any],
    executor: Executor | None = None,
    timeout: float | None = None,
    dry_run: bool = False,
    force: bool = False,
    resume_running: bool = False,
    retry_terminal: bool = False,
) -> dict[str, Any]:
    executor = executor or Executor()
    prepared_dir = Path(workspace_root) / project_id
    prepared_config = prepared_dir / "codeweaver.toml"
    run_dir = run_dir_for(runs_root, variant, project_id, repetition)

    existing = load_run_state(run_dir)
    if existing and existing.get("reservation") and not force:
        return {
            **existing,
            "skipped": True,
            "skip_reason": "reserved for disjoint shard",
        }
    if existing and existing.get("status") == "completed" and not force:
        return {**existing, "skipped": True, "skip_reason": "already completed"}
    if (
        existing
        and existing.get("status") in {"failed", "timeout"}
        and not (force or retry_terminal)
    ):
        return {
            **existing,
            "skipped": True,
            "skip_reason": f"already {existing['status']}",
        }
    if existing and existing.get("status") == "running" and not (force or resume_running):
        return {**existing, "skipped": True, "skip_reason": "already running"}

    app_id = (existing or {}).get("app_id") or app_id_for(variant, project_id, repetition)

    if dry_run:
        if not prepared_config.exists():
            return {"variant": variant, "project_id": project_id, "repetition": repetition,
                   "status": "dry_run", "error": f"not prepared: {prepared_config} missing"}
        plan = describe_plan(variant, prepared_config, app_id)
        return {"variant": variant, "project_id": project_id, "repetition": repetition,
               "workspace_dir": str(run_dir), "app_id": app_id, "status": "dry_run", "plan": plan}

    if not prepared_config.exists():
        raise FileNotFoundError(
            f"project {project_id!r} is not prepared (missing {prepared_config}); run prepare.py first"
        )

    state = existing or new_run_state(variant, project_id, repetition, run_dir)
    state["app_id"] = app_id
    state["attempt"] = int(state.get("attempt", 0)) + 1
    state["status"] = "running"
    state["started_at"] = utcnow_iso()
    state["ended_at"] = None
    state["timeout_seconds"] = timeout
    state["error"] = ""
    state["returncode"] = None
    state["num_calls"] = 0
    agent_timeout = resolve_agent_timeout(timeout, protocol)
    state["provenance"] = collect_provenance(model=protocol.get("model"), agent_timeout=agent_timeout,
                                            probe_toolchains=False)

    # Contamination guard: a previously-materialized run_dir explicitly
    # retried after a failed, timed-out, or interrupted attempt must never be
    # silently reused for one-shot base-agent variants. The full
    # pipeline and named stage ablations all have genuine cross-process
    # resumability through CodeWeaver's Burr SQLite persister keyed on a stable
    # --app-id. If a base-agent attempt already wrote partial output into
    # pipeline/ or
    # working_copy/ (analysis.md, plan.json, milestones.json, partially
    # translated files, a stale calls.jsonl, ...), silently retrying on top of
    # that dirty state risks a later stage misreading stray leftovers as its
    # own prior progress, corrupting both the translation and every
    # trajectory/tool/token metric this harness measures downstream. So for
    # those variants a dirty existing state forces a full clean rematerialize
    # (wipe run_dir, fresh copy from the pristine prepared_dir template) even
    # when the caller did not pass --force.
    is_dirty_retry = bool(existing) and existing.get("status") != "completed"
    resumable_variants = {"full", *STAGE_SKIP_VARIANTS}
    force_rematerialize = force or (variant not in resumable_variants and is_dirty_retry)

    P.materialize_run(prepared_dir, run_dir, force=force_rematerialize)
    save_run_state(run_dir, state)  # mark "running" BEFORE any subprocess -- a crash is then observable

    try:
        if variant == "full" or variant in STAGE_SKIP_VARIANTS:
            # Pin the hook explicitly so an ambient developer environment
            # cannot accidentally turn a measured ``full`` run into an ablation.
            child_env = {
                "CODEWEAVER_SKIP_STAGES": "",
                "CODEWEAVER_ABLATION_VARIANT": "",
            }
            if variant in STAGE_SKIP_VARIANTS:
                skipped_stage = STAGE_SKIP_VARIANTS[variant]
                child_env["CODEWEAVER_SKIP_STAGES"] = skipped_stage
                child_env["CODEWEAVER_ABLATION_VARIANT"] = variant
                state["ablation"] = {
                    "skipped_stage": skipped_stage,
                    "execution_mode": "full_burr_graph",
                }
            calls, exec_result = run_full_variant(run_dir / "codeweaver.toml", app_id, run_dir,
                                                  executor=executor, timeout=timeout, env=child_env)
            state["argv"] = exec_result.argv
            state["returncode"] = exec_result.returncode
            timed_out = exec_result.timed_out
            ok = exec_result.ok
            # Persist the CLI subprocess's own stdout/stderr so collect.py can
            # give failures.csv a real reason instead of just a returncode --
            # codeweaver's own per-agent JSONL logs (pipeline/logs/*.stdout.jsonl)
            # cover *what the agents said*; this covers the CLI wrapper itself.
            with contextlib.suppress(OSError):
                C.atomic_write_text(run_dir / "cli.stdout.log", exec_result.stdout)
                C.atomic_write_text(run_dir / "cli.stderr.log", exec_result.stderr)
            if not ok and not state["error"]:
                state["error"] = (
                    exec_result.error or _tail(exec_result.stderr) or _tail(exec_result.stdout)
                    or f"codeweaver CLI exited with returncode={exec_result.returncode}"
                )
        else:
            from codeweaver import config as cw_config
            run_cfg = cw_config.load(run_dir / "codeweaver.toml")
            calls = run_baseagent_variant(variant, run_cfg, executor=executor, timeout=agent_timeout)
            timed_out = any(c.timed_out for c in calls)
            ok = all(c.ok for c in calls)
            state["returncode"] = 0 if ok else 1

        write_calls_jsonl(run_dir, calls)
        state["num_calls"] = len(calls)
        if not ok and not state["error"]:
            state["error"] = next(
                (c.error for c in calls if not c.ok and c.error),
                f"experiment subprocess exited with returncode={state['returncode']}",
            )
        state["status"] = "timeout" if timed_out else ("completed" if ok else "failed")
    except Exception as e:  # noqa: BLE001 - orchestration failures must be recorded, never raised past run_one
        state["status"] = "failed"
        state["error"] = repr(e)
    state["ended_at"] = utcnow_iso()
    save_run_state(run_dir, state)
    return state


# --------------------------------------------------------------------------- #
# Matrix selection + parallel execution
# --------------------------------------------------------------------------- #
def select_project_ids(manifest: dict[str, Any], *, project_ids: set[str] | None = None,
                       tools: set[str] | None = None) -> list[str]:
    out = []
    for row in manifest["projects"]:
        if project_ids is not None and row["id"] not in project_ids:
            continue
        if tools is not None and row["tool"] not in tools:
            continue
        out.append(row["id"])
    return out


def build_job_list(variants: list[str], project_ids: list[str], repetitions: int) -> list[tuple[str, str, int]]:
    return [(v, p, r) for v in variants for p in project_ids for r in range(repetitions)]


def run_matrix(
    jobs: list[tuple[str, str, int]],
    *,
    workspace_root: Path,
    runs_root: Path,
    protocol: dict[str, Any],
    executor: Executor | None = None,
    timeout: float | None = None,
    dry_run: bool = False,
    force: bool = False,
    resume_running: bool = False,
    retry_terminal: bool = False,
    max_workers: int = 1,
) -> list[dict[str, Any]]:
    def _one(job):
        variant, project_id, repetition = job
        return run_one(variant, project_id, repetition, workspace_root=workspace_root, runs_root=runs_root,
                       protocol=protocol, executor=executor, timeout=timeout, dry_run=dry_run, force=force,
                       resume_running=resume_running, retry_terminal=retry_terminal)

    if max_workers <= 1 or len(jobs) <= 1:
        return [_one(j) for j in jobs]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_one, jobs))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="run.py",
        description="Resumable/idempotent execution of the ReCodeAgent reproduction matrix "
                    "(variant x project x repetition).",
    )
    ap.add_argument("--manifest", required=True, help="path to manifest.json")
    ap.add_argument("--workspace-root", required=True, help="prepared per-project workspaces (prepare.py output)")
    ap.add_argument("--runs-root", required=True, help="where per-run directories are materialized")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--variant", default="full", help="comma-separated variants, or 'all' "
                    f"(choices: {', '.join(C.RUN_VARIANTS)})")
    ap.add_argument("--project", default="all", help="comma-separated project ids, or 'all'")
    ap.add_argument("--tool", default=None, help="comma-separated tool keys to filter by")
    ap.add_argument("--repetitions", type=int, default=None, help="default: [protocol].repetitions")
    ap.add_argument("--jobs", type=int, default=1, help="parallel worker threads")
    ap.add_argument("--timeout", type=float, default=None, help="per-agent-call timeout override (seconds)")
    ap.add_argument("--dry-run", action="store_true", help="print the planned argv/stages; execute nothing")
    ap.add_argument("--force", action="store_true", help="redo even if already completed / re-materialize")
    ap.add_argument("--resume-running", action="store_true",
                    help="resume cells left in running state by a confirmed-dead prior launcher")
    ap.add_argument(
        "--retry-terminal",
        action="store_true",
        help="explicitly retry failed/timeout cells; terminal outcomes are preserved by default",
    )
    ap.add_argument("--out", default=None, help="write a JSON summary of this invocation's job results")
    return ap


def _parse_variants(raw: str) -> list[str]:
    if raw.strip().lower() == "all":
        return list(C.RUN_VARIANTS)
    variants = [v.strip() for v in raw.split(",") if v.strip()]
    unknown = [v for v in variants if v not in C.RUN_VARIANTS]
    if unknown:
        raise ValueError(f"unknown variant(s): {unknown} (choices: {C.RUN_VARIANTS})")
    return variants


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = P.load_experiment_config(args.config)
    protocol = cfg.get("protocol", {})
    manifest = C.read_json(args.manifest)

    variants = _parse_variants(args.variant)
    project_ids = None if args.project.strip().lower() == "all" else set(args.project.split(","))
    tools = set(args.tool.split(",")) if args.tool else None
    selected = select_project_ids(manifest, project_ids=project_ids, tools=tools)
    repetitions = args.repetitions if args.repetitions is not None else int(protocol.get("repetitions", 1))

    jobs = build_job_list(variants, selected, repetitions)
    print(f"[run] {len(jobs)} job(s): variants={variants} projects={len(selected)} repetitions={repetitions}")

    results = run_matrix(jobs, workspace_root=Path(args.workspace_root), runs_root=Path(args.runs_root),
                         protocol=protocol, timeout=args.timeout, dry_run=args.dry_run, force=args.force,
                         resume_running=args.resume_running,
                         retry_terminal=args.retry_terminal,
                         max_workers=max(1, args.jobs))

    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
    print(f"[run] done: {by_status}")

    if args.out:
        atomic_write_json(args.out, {"generated_at": utcnow_iso(), "jobs": len(jobs),
                                     "by_status": by_status, "results": results})
        print(f"[run] wrote {args.out}")
    return 0 if all(r.get("status") in ("completed", "dry_run") or r.get("skipped") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
