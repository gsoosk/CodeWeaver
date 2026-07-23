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
  report           : dict  last validation report (parsed from <pipeline>/report.json)
  analysis_done    : bool  analyzer produced the analysis artifact
  plan_done        : bool  planner produced the plan artifact
  history          : list  append-only log of {milestone, iter, passed}
  done             : bool  whole pipeline finished (all milestones green or gave up)
  last_agent       : str   name of the most recently run agent
"""
from __future__ import annotations

from .config import Config


def initial_state(cfg: Config, max_iter: int = 5) -> dict:
    return {
        "milestone_idx": 0,
        "num_milestones": len(cfg.milestones),
        "last_idx": len(cfg.milestones) - 1,
        "iter_count": 0,
        "max_iter": max_iter,
        "milestone_passed": False,
        "report": {},
        "analysis_done": False,
        "plan_done": False,
        "history": [],
        "done": False,
        "last_agent": "",
    }


def current_milestone(cfg: Config, state):
    return cfg.milestones[state["milestone_idx"]]


def is_last_milestone(cfg: Config, state) -> bool:
    return state["milestone_idx"] >= len(cfg.milestones) - 1
