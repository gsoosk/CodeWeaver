"""The Burr application: wire the CodeWeaver stages into a persisted, resumable
state machine.

CodeWeaver runs TWO phases. Phase 1 (translation) makes the port correct; phase 2
(optimization) makes it fast. **Phase 2 is OFF by default** -- enable it with
``[optimization].enabled`` or ``--optimize``. When off, the graph below is exactly
the phase-1 graph: the optimize actions are not even registered.

  PHASE 1 -- translation (always)
    analyze -> [scope] -> plan -> select_milestone -> translate -> validate -> [parity] -> terminal
                  ^                       ^                ^          |           |
                  | parity gaps           | concluded &    | repair   |           | retry deferred
                  | (re-scope)            | more milestones| (budget) |           | (select_milestone)
                  +-----------------------+----------------+----------+-----------+

  PHASE 2 -- optimization (only when enabled; entered from parity)
    parity -> benchmark -> optimize -> benchmark -> ... (max_opt_rounds)
           -> opt_repair -> select_milestone -> translate <-> validate -> terminal

A milestone "concludes" when validate either passes it OR exhausts the repair
budget. With ``skip_on_give_up`` (default), give-up SKIPS the stuck milestone
(recorded in ``skipped`` + ``skips.json``, deselected from later gates) and the
loop advances; the parity verifier then gives each deferred test ONE retry
milestone. The run succeeds only when parity is complete (or, with parity off,
when every milestone passed). Set ``skip_on_give_up=false`` for the legacy
hard-fail-on-give-up behaviour.

Phase 2 is gated on ``parity_complete``: tuning a translation with known gaps
tunes code that is still going to change. It closes by appending ONE
``full_suite`` conformance milestone, so an optimisation regression is REPAIRED
through the normal repair loop rather than discarded (see ``optimize.py``).

Build the app from a loaded :class:`~codeweaver.config.Config`; the config is
registered as the active one so the module-level ``@action`` functions can reach
it. Resume by reusing the same app-id (the SQLite persister continues).
"""
from __future__ import annotations

import os
from pathlib import Path

import burr.core
from burr.core import ApplicationBuilder, default, expr
from burr.core.persistence import SQLLitePersister

from . import actions, config as C, optimize, state as S
from .config import Config


def tracker_enabled() -> bool:
    """The Burr telemetry tracker needs the optional 'tracking' extra (pydantic).
    Enable it when importable; otherwise run without telemetry rather than crash.
    Force off with CODEWEAVER_NO_TRACKER=1."""
    if os.environ.get("CODEWEAVER_NO_TRACKER") == "1":
        return False
    try:
        import burr.tracking.client  # noqa: F401  (triggers the extra's import chain)
        return True
    except Exception as e:  # ImportError from the plugin requirement, or anything else
        print("[codeweaver] telemetry tracker disabled (install 'apache-burr[tracking]' "
              f"to enable the Burr UI): {type(e).__name__}: {e}")
        return False


def state_from_existing_pipeline(cfg: Config, milestone_id: str | None,
                                 max_iter: int, max_parity_rounds: int,
                                 entry: str = "milestone",
                                 max_opt_rounds: int | None = None,
                                 bench_scenarios: str | None = None) -> dict:
    """Bootstrap a NEW run from existing pipeline artifacts.

    Three entry points, all skipping analyze/scope/plan by marking them done:

    * ``entry="milestone"`` -- enter the milestone loop at ``milestone_id``.
    * ``entry="parity"`` -- skip the milestone loop and go straight to the parity
      verifier.
    * ``entry="benchmark"`` -- skip the milestone loop AND parity and go straight
      to the OPTIMIZE phase. ``parity_complete`` is set because that is the flag
      the graph gates the phase on -- and it is the caller's ASSERTION, not a
      derived fact: pointed at an unfinished translation this optimises code that
      is still going to change, and only the appended full-suite milestone would
      catch it.

    For the two non-milestone entries the state sits on the LAST milestone and
    marks it passed/concluded, so the outer loop still works from there (gaps ->
    re-scope, or an appended retry/conformance milestone -> select_milestone
    advances cleanly).

    Requires the analysis, milestones, and plan artifacts (and the working copy,
    when the config declares one)."""
    required = [cfg.analysis_path, cfg.milestones_path, cfg.plan_path]
    wc = cfg.working_copy_path
    if wc is not None:
        required.append(wc)
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise ValueError(
            "cannot start from an existing pipeline; missing required artifact(s): "
            + ", ".join(missing))

    cfg.load_generated_milestones()
    ms = cfg.milestones
    if not ms:
        raise ValueError(f"no milestones found in {cfg.milestones_path}")

    past_loop = entry in ("parity", "benchmark")
    if past_loop:
        idx = len(ms) - 1                # sit on the last milestone, already concluded
    else:
        idx = next((i for i, m in enumerate(ms) if m.id == milestone_id), None)
        if idx is None:
            ids = ", ".join(m.id for m in ms)
            raise ValueError(
                f"milestone {milestone_id!r} is not in {cfg.milestones_path} (available: {ids})")

    st = S.initial_state(cfg, max_iter=max_iter, max_opt_rounds=max_opt_rounds,
                         bench_scenarios=bench_scenarios)
    st.update({
        "milestone_idx": idx,
        "num_milestones": len(ms),
        "last_idx": len(ms) - 1,
        "max_parity_rounds": max_parity_rounds,
        "analysis_done": True,
        "milestones_done": True,
        "plan_done": True,
        # Non-milestone entries: present the last milestone as already passed +
        # concluded so the graph's downstream transitions behave as in a normal run.
        "milestone_passed": past_loop,
        "milestone_concluded": past_loop,
        # Benchmark entry asserts parity is behind us -- that is the gate the
        # optimize phase is conditioned on.
        "parity_complete": entry == "benchmark",
        "last_agent": "pipeline-bootstrap",
    })
    return st


def build_application(cfg: Config, app_id: str, max_iter: int | None = None,
                      db_path: str | None = None, bootstrap_state: dict | None = None,
                      default_entrypoint: str = "analyze",
                      max_opt_rounds: int | None = None,
                      bench_scenarios: str | None = None):
    """Assemble the Burr application for a project config.

    * The ``scope`` (milestone-generator) stage is present when milestones are
      auto-generated OR when the parity loop is enabled (so it can be re-entered).
    * The ``parity`` stage is present when ``parity_check`` is on.
    * The OPTIMIZE phase (``benchmark``/``optimize``/``opt_repair``) is present
      only when it is enabled -- it is OFF by default, and when off the graph is
      byte-for-byte the phase-1 graph.
    On resume, any milestone matrix already written to disk is reloaded so state
    counts are correct.
    """
    C.set_active(cfg)
    max_iter = cfg.max_iter if max_iter is None else max_iter
    opt_rounds = cfg.opt_rounds if max_opt_rounds is None else max_opt_rounds
    db_path = db_path or cfg.resolved_db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    include_parity = cfg.parity_check
    include_scope = cfg.auto_milestones or include_parity
    # The optimize phase is gated on parity completing, so it needs the parity
    # stage to exist; without it there is nothing to assert the port is finished.
    include_optimize = opt_rounds > 0 and include_parity

    # Resume support: reload any matrix written by a prior process (initial scope,
    # a parity re-scope, a deferred-test retry, or the optimize conformance
    # milestone) so counts are right at startup.
    if include_scope and cfg.milestones_path.exists():
        cfg.load_generated_milestones()

    persister = SQLLitePersister.from_values(db_path=db_path, table_name="codeweaver_state")
    persister.initialize()

    result_keys = ["done", "history", "milestone_idx", "report", "skipped",
                   "parity_round", "parity_complete", "parity_report"]
    if include_optimize:
        result_keys += ["opt_round", "bench_history"]

    actions_map = dict(
        analyze=actions.analyze,
        plan=actions.plan,
        select_milestone=actions.select_milestone,
        translate=actions.translate,
        validate=actions.validate,
        terminal=burr.core.Result(*result_keys),
    )
    if include_scope:
        actions_map["scope"] = actions.scope
    if include_parity:
        actions_map["parity"] = actions.parity
    if include_optimize:
        actions_map["benchmark"] = optimize.benchmark
        actions_map["optimize"] = optimize.optimize
        actions_map["opt_repair"] = optimize.opt_repair

    # analyze -> [scope ->] plan
    head_transitions = (
        [("analyze", "scope"), ("scope", "plan")] if include_scope else [("analyze", "plan")]
    )
    transitions = [
        *head_transitions,
        ("plan", "select_milestone"),
        ("select_milestone", "translate"),
        ("translate", "validate"),
        # inner loop: repair the current milestone while it fails and there's budget
        ("validate", "translate", expr("not milestone_passed and iter_count < max_iter")),
    ]
    if include_optimize:
        # The post-optimisation conformance milestone is the LAST thing the run
        # does. Ordered BEFORE the two transitions below so it cannot fall through
        # to select_milestone (there is no next milestone) or back to parity
        # (which would re-enter the optimize phase and never terminate).
        transitions.append(("validate", "terminal", expr("opt_repairing")))
    transitions.append(
        # milestone concluded (passed OR skipped after give-up) and more remain -> next
        ("validate", "select_milestone", expr("milestone_concluded and milestone_idx < last_idx")))
    if include_parity:
        # last milestone concluded -> run the parity (source-coverage) gate
        transitions.append(
            ("validate", "parity", expr("milestone_concluded and milestone_idx >= last_idx")))
        # parity appended a deferred-test retry milestone -> run it
        transitions.append(("parity", "select_milestone", expr("retry_pending")))
        # gaps found + budget left -> re-scope new milestones
        transitions.append(
            ("parity", "scope", expr("not parity_complete and parity_round < max_parity_rounds")))
        if include_optimize:
            # PHASE 2. The translation is COMPLETE and correct -> make it faster.
            # Requires parity_complete: optimising a port with known gaps would tune
            # code that is still going to change. opt_done stops a second entry.
            transitions.append(
                ("parity", "benchmark",
                 expr("parity_complete and not opt_done and max_opt_rounds > 0")))
        # complete (success) OR gaps + budget exhausted (fail) -> terminal
        transitions.append(("parity", "terminal", default))
    if include_optimize:
        # measure -> change -> repeat, then hand the accumulated result to ONE
        # full-suite conformance milestone run through the normal repair loop.
        transitions.append(("benchmark", "optimize"))
        transitions.append(("optimize", "benchmark", expr("opt_round <= max_opt_rounds")))
        transitions.append(("optimize", "opt_repair", default))
        transitions.append(("opt_repair", "select_milestone"))
    # default: parity off & last milestone concluded -> terminal; OR give-up with
    # skip_on_give_up off (not concluded) -> terminal with done=False (hard fail).
    transitions.append(("validate", "terminal", default))

    builder = (
        ApplicationBuilder()
        .with_actions(**actions_map)
        .with_transitions(*transitions)
        .initialize_from(
            persister,
            resume_at_next_action=True,      # crash-resume: pick up where we left off
            default_state=bootstrap_state or S.initial_state(
                cfg, max_iter=max_iter, max_opt_rounds=opt_rounds,
                bench_scenarios=bench_scenarios),
            default_entrypoint=default_entrypoint,
        )
        .with_state_persister(persister)
        .with_identifiers(app_id=app_id)
    )
    if tracker_enabled():
        builder = builder.with_tracker("local", project=cfg.slug)   # Burr telemetry UI
    return builder.build()
