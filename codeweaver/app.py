"""The Burr application: wire the ReCodeAgent stages into a persisted, resumable
state machine with the milestone x repair loop.

    analyze -> plan -> select_milestone -> translate -> validate
                            ^                              |
        (passed & more) ----+                             | repair (not passed & iter<max)
                            |                              v
                            +--------- validate --> translate
                                          |
                                 default (passed&last, or gave up) -> terminal

Build the app from a loaded :class:`~codeweaver.config.Config`; the config is
registered as the active one so the module-level ``@action`` functions can reach
it. Resume by reusing the same app-id (the SQLite persister continues).
"""
from __future__ import annotations

from pathlib import Path

import burr.core
from burr.core import ApplicationBuilder, default, expr
from burr.core.persistence import SQLLitePersister
from burr.tracking.client import LocalTrackingClient

from . import actions, config as C, state as S
from .config import Config


def _build_local_tracker(
    project: str, storage_dir: str | Path = "~/.burr"
) -> LocalTrackingClient:
    tracker = LocalTrackingClient(
        project=project, storage_dir=str(storage_dir)
    )
    # Burr uses a check-then-create sequence for this shared project directory.
    # Pre-creating it with exist_ok avoids races between parallel app launches.
    Path(tracker.storage_dir).mkdir(parents=True, exist_ok=True)
    return tracker


def build_application(cfg: Config, app_id: str, max_iter: int | None = None,
                      db_path: str | None = None):
    """Assemble the Burr application for a project config.

    Graph shape (nodes in brackets are conditional):

        analyze -> [scope] -> plan -> select_milestone -> translate -> validate
                      ^                       ^                            |
                      |  parity incomplete    |  repair (iter<max)         |
                      |                        +---------------------------+
                      |    all milestones pass -> [parity]
                      +---------------------------+ (parity incomplete & rounds left)
                                                  -> terminal (parity complete / gave up)

    * The ``scope`` (milestone-generator) stage is present when milestones are
      auto-generated OR when the parity loop is enabled (so it can be re-entered).
    * The ``parity`` stage is present when ``parity_check`` is on: after the last
      milestone passes it verifies the translation against the source; if
      incomplete it loops back to ``scope`` to schedule the gaps, bounded by
      ``max_parity_rounds``.
    On resume, any milestone matrix already written to disk is reloaded so the
    state counts are correct.
    """
    C.set_active(cfg)
    max_iter = cfg.max_iter if max_iter is None else max_iter
    db_path = db_path or cfg.resolved_db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    include_parity = cfg.parity_check
    include_scope = cfg.auto_milestones or include_parity

    # Resume support: reload any matrix written by a prior process (initial scope
    # or a parity round) so num_milestones/last_idx are right from the start.
    if include_scope and cfg.milestones_path.exists():
        cfg.load_generated_milestones()

    persister = SQLLitePersister.from_values(db_path=db_path, table_name="codeweaver_state")
    persister.initialize()
    tracker = _build_local_tracker(cfg.slug)

    actions_map = dict(
        analyze=actions.analyze,
        plan=actions.plan,
        select_milestone=actions.select_milestone,
        translate=actions.translate,
        validate=actions.validate,
        terminal=burr.core.Result("done", "history", "milestone_idx", "report",
                                   "parity_complete", "parity_report"),
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
        # repair the current milestone while it fails and there's budget
        ("validate", "translate", expr("not milestone_passed and iter_count < max_iter")),
        # advance to the next milestone once this one passes
        ("validate", "select_milestone", expr("milestone_passed and milestone_idx < last_idx")),
    ]
    if include_parity:
        # all milestones passed -> run the final parity check
        transitions.append(
            ("validate", "parity", expr("milestone_passed and milestone_idx >= last_idx"))
        )
        # parity found gaps and there are rounds left -> back to the milestone generator
        transitions.append(
            ("parity", "scope", expr("not parity_complete and parity_round < max_parity_rounds"))
        )
        # parity complete, or out of rounds -> done
        transitions.append(("parity", "terminal", default))
    # otherwise done: last milestone passed (parity off), or budget exhausted
    transitions.append(("validate", "terminal", default))

    return (
        ApplicationBuilder()
        .with_actions(**actions_map)
        .with_transitions(*transitions)
        .initialize_from(
            persister,
            resume_at_next_action=True,      # crash-resume: pick up where we left off
            default_state=S.initial_state(cfg, max_iter=max_iter),
            default_entrypoint="analyze",
        )
        .with_state_persister(persister)
        .with_identifiers(app_id=app_id)
        .with_tracker(tracker)   # Burr telemetry UI
        .build()
    )
