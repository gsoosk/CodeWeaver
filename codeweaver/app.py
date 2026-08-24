"""The Burr application: wire the ReCodeAgent stages into a persisted, resumable
state machine with two nested loops -- the per-milestone repair loop (inner,
correctness) and the parity coverage loop (outer, completeness).

    analyze -> [scope] -> plan -> select_milestone -> translate -> validate -> [parity] -> terminal
                  ^                       ^                 ^          |            |
                  | parity gaps           | concluded &     | repair   |            | retry deferred
                  | (re-scope)            | more milestones | (budget) |            | (select_milestone)
                  +-----------------------+-----------------+----------+------------+

A milestone "concludes" when validate either passes it OR exhausts the repair
budget. With ``skip_on_give_up`` (default), give-up SKIPS the stuck milestone
(recorded in ``skipped`` + ``skips.json``, deselected from later gates) and the
loop advances; the parity verifier then gives each deferred test ONE retry
milestone. The run succeeds only when parity is complete (or, with parity off,
when every milestone passed). Set ``skip_on_give_up=false`` for the legacy
hard-fail-on-give-up behaviour.

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

from . import actions, config as C, state as S
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
                                 max_iter: int, max_parity_rounds: int) -> dict:
    """Bootstrap a NEW run from existing pipeline artifacts.

    Two entry points, both skipping analyze/scope/plan by marking them done:

    * ``milestone_id="Mx"`` -- enter the milestone loop at ``Mx``.
    * ``milestone_id=None`` -- PARITY entry: skip the milestone loop entirely and
      go straight to the parity verifier. The state sits on the LAST milestone and
      marks it passed/concluded, so the outer loop still works from there (gaps ->
      re-scope, or an appended retry milestone -> select_milestone advances cleanly).

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

    parity_entry = milestone_id is None
    if parity_entry:
        idx = len(ms) - 1                # sit on the last milestone, already concluded
    else:
        idx = next((i for i, m in enumerate(ms) if m.id == milestone_id), None)
        if idx is None:
            ids = ", ".join(m.id for m in ms)
            raise ValueError(
                f"milestone {milestone_id!r} is not in {cfg.milestones_path} (available: {ids})")

    st = S.initial_state(cfg, max_iter=max_iter)
    st.update({
        "milestone_idx": idx,
        "num_milestones": len(ms),
        "last_idx": len(ms) - 1,
        "max_parity_rounds": max_parity_rounds,
        "analysis_done": True,
        "milestones_done": True,
        "plan_done": True,
        # Parity entry: present the last milestone as already passed + concluded so
        # the graph's post-parity transitions behave exactly as in a normal run.
        "milestone_passed": parity_entry,
        "milestone_concluded": parity_entry,
        "last_agent": "pipeline-bootstrap",
    })
    return st


def build_application(cfg: Config, app_id: str, max_iter: int | None = None,
                      db_path: str | None = None, bootstrap_state: dict | None = None,
                      default_entrypoint: str = "analyze"):
    """Assemble the Burr application for a project config.

    * The ``scope`` (milestone-generator) stage is present when milestones are
      auto-generated OR when the parity loop is enabled (so it can be re-entered).
    * The ``parity`` stage is present when ``parity_check`` is on.
    On resume, any milestone matrix already written to disk is reloaded so state
    counts are correct.
    """
    C.set_active(cfg)
    max_iter = cfg.max_iter if max_iter is None else max_iter
    db_path = db_path or cfg.resolved_db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    include_parity = cfg.parity_check
    include_scope = cfg.auto_milestones or include_parity

    # Resume support: reload any matrix written by a prior process (initial scope,
    # a parity re-scope, or a deferred-test retry) so counts are right at startup.
    if include_scope and cfg.milestones_path.exists():
        cfg.load_generated_milestones()

    persister = SQLLitePersister.from_values(db_path=db_path, table_name="codeweaver_state")
    persister.initialize()

    actions_map = dict(
        analyze=actions.analyze,
        plan=actions.plan,
        select_milestone=actions.select_milestone,
        translate=actions.translate,
        validate=actions.validate,
        terminal=burr.core.Result("done", "history", "milestone_idx", "report",
                                   "skipped", "parity_round", "parity_complete",
                                   "parity_report"),
    )
    if include_scope:
        actions_map["scope"] = actions.scope
    if include_parity:
        actions_map["parity"] = actions.parity

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
        # milestone concluded (passed OR skipped after give-up) and more remain -> next
        ("validate", "select_milestone", expr("milestone_concluded and milestone_idx < last_idx")),
    ]
    if include_parity:
        # last milestone concluded -> run the parity (source-coverage) gate
        transitions.append(
            ("validate", "parity", expr("milestone_concluded and milestone_idx >= last_idx")))
        # parity appended a deferred-test retry milestone -> run it
        transitions.append(("parity", "select_milestone", expr("retry_pending")))
        # gaps found + budget left -> re-scope new milestones
        transitions.append(
            ("parity", "scope", expr("not parity_complete and parity_round < max_parity_rounds")))
        # complete (success) OR gaps + budget exhausted (fail) -> terminal
        transitions.append(("parity", "terminal", default))
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
            default_state=bootstrap_state or S.initial_state(cfg, max_iter=max_iter),
            default_entrypoint=default_entrypoint,
        )
        .with_state_persister(persister)
        .with_identifiers(app_id=app_id)
    )
    if tracker_enabled():
        builder = builder.with_tracker("local", project=cfg.slug)   # Burr telemetry UI
    return builder.build()
