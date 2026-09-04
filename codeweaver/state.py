"""Typed-ish state helpers for the Burr application.

Burr's State is a dict-like, immutable object (``state.update(...)`` /
``state.append(...)``). We keep the schema in one place so actions and
transitions agree on key names.

State keys
----------
  milestone_idx    : int   index into cfg.milestones of the milestone in progress
  num_milestones   : int   total milestone count
  last_idx         : int   index of the final milestone
  iter_count       : int   translate->validate repair attempts on the CURRENT milestone
  max_iter         : int   repair budget per milestone
  milestone_passed : bool  did the last validate for this milestone pass?
  milestone_concluded : bool  did the current milestone conclude (passed OR gave up =
                              repair budget exhausted)? select_milestone advances when set.
  report           : dict  last validation report (parsed from <pipeline>/report.json)
  analysis_done    : bool  analyzer produced the analysis artifact
  plan_done        : bool  planner produced the plan artifact
  history          : list  append-only log of {milestone, iter, passed, gave_up}
  skipped          : list  milestone ids skipped after exhausting the repair budget
  retry_pending    : bool  parity appended a retry milestone for deferred skips -> re-run
  done             : bool  whole pipeline finished SUCCESSFULLY
  last_agent       : str   name of the most recently run agent

Optimize phase (phase 2 -- performance; skipped entirely when max_opt_rounds is 0)
----------------------------------------------------------------------------------
  opt_round        : int   1-based benchmark->optimize round in progress
  max_opt_rounds   : int   optimisation rounds to attempt (0 disables the phase)
  bench_scenarios  : str   space-separated scenario ids to focus on; "" = whole suite
  bench            : dict  the latest benchmark artifact, as read back
  bench_history    : list  per-round benchmark summary, so the trend is visible
  optimize         : dict  the latest optimizer change-set record
  opt_repairing    : bool  the appended post-optimisation milestone is in flight
  opt_done         : bool  the optimize phase has run; stops parity re-entering it
"""
from __future__ import annotations

from .config import Config


def initial_state(cfg: Config, max_iter: int = 5,
                  max_opt_rounds: int | None = None,
                  bench_scenarios: str | None = None) -> dict:
    opt_rounds = cfg.opt_rounds if max_opt_rounds is None else max_opt_rounds
    scenarios = cfg.optimize.scenarios if bench_scenarios is None else bench_scenarios
    return {
        "milestone_idx": 0,
        "num_milestones": len(cfg.milestones),
        "last_idx": len(cfg.milestones) - 1,
        "iter_count": 0,
        "max_iter": max_iter,
        "milestone_passed": False,
        "milestone_concluded": False,   # passed OR gave up (budget spent)
        "report": {},
        "analysis_done": False,
        "milestones_done": not cfg.auto_milestones,  # scope stage sets this when auto
        "plan_done": False,
        "history": [],
        "skipped": [],                  # milestone ids skipped after give-up
        # final parity loop
        "parity_round": 0,
        "max_parity_rounds": cfg.max_parity_rounds,
        "parity_complete": False,
        "parity_report": {},
        "retry_pending": False,         # parity appended a deferred-test retry milestone
        # optimize phase (off unless max_opt_rounds > 0)
        "opt_round": 1,
        "max_opt_rounds": opt_rounds,
        "bench_scenarios": " ".join((scenarios or "").replace(",", " ").split()),
        "bench": {},
        "bench_history": [],
        "optimize": {},
        "opt_repairing": False,
        "opt_done": False,
        "done": False,
        "last_agent": "",
    }


def current_milestone(cfg: Config, state):
    # Clamp defensively: the parity loop can grow the matrix between rounds, and a
    # re-entry must never index past the current list.
    idx = state["milestone_idx"]
    if not cfg.milestones:
        raise IndexError("no milestones available")
    idx = max(0, min(idx, len(cfg.milestones) - 1))
    return cfg.milestones[idx]


def is_last_milestone(cfg: Config, state) -> bool:
    return state["milestone_idx"] >= len(cfg.milestones) - 1
