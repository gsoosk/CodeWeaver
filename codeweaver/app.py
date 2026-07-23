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

from . import actions, config as C, state as S
from .config import Config


def build_application(cfg: Config, app_id: str, max_iter: int | None = None,
                      db_path: str | None = None):
    """Assemble the Burr application for a project config."""
    C.set_active(cfg)
    max_iter = cfg.max_iter if max_iter is None else max_iter
    db_path = db_path or cfg.resolved_db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    persister = SQLLitePersister.from_values(db_path=db_path, table_name="codeweaver_state")
    persister.initialize()

    return (
        ApplicationBuilder()
        .with_actions(
            analyze=actions.analyze,
            plan=actions.plan,
            select_milestone=actions.select_milestone,
            translate=actions.translate,
            validate=actions.validate,
            terminal=burr.core.Result("done", "history", "milestone_idx", "report"),
        )
        .with_transitions(
            ("analyze", "plan"),
            ("plan", "select_milestone"),
            ("select_milestone", "translate"),
            ("translate", "validate"),
            # repair the current milestone while it fails and there's budget
            ("validate", "translate", expr("not milestone_passed and iter_count < max_iter")),
            # advance to the next milestone once this one passes
            ("validate", "select_milestone", expr("milestone_passed and milestone_idx < last_idx")),
            # otherwise done: last milestone passed, or budget exhausted
            ("validate", "terminal", default),
        )
        .initialize_from(
            persister,
            resume_at_next_action=True,      # crash-resume: pick up where we left off
            default_state=S.initial_state(cfg, max_iter=max_iter),
            default_entrypoint="analyze",
        )
        .with_state_persister(persister)
        .with_identifiers(app_id=app_id)
        .with_tracker("local", project=cfg.slug)   # Burr telemetry UI
        .build()
    )
