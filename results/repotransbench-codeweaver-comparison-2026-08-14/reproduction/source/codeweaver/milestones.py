"""Milestone helpers: turn a config's milestone matrix into cumulative gates.

A milestone's gate is CUMULATIVE -- it must pass its own ``tests`` AND every
earlier milestone's tests (regression safety). ``cumulative_tests`` accumulates
the selector tokens in order; ``gate_string`` renders them through the config's
``gate_template`` into the concrete string the validate command consumes.

The original recodeAgent hard-coded a pytest ``-k "a or b"`` gate; here the
template is configurable, so the same machinery drives any test selector syntax
(pytest ``-k``, ``go test -run``, ``cargo test <name>``, ctest ``-R``, ...).
"""
from __future__ import annotations

from .config import Config, Milestone


def index_of(cfg: Config, mid: str) -> int:
    for i, m in enumerate(cfg.milestones):
        if m.id == mid:
            return i
    raise KeyError(mid)


def by_id(cfg: Config, mid: str) -> Milestone:
    return cfg.milestones[index_of(cfg, mid)]


def is_last(cfg: Config, idx: int) -> bool:
    return idx >= len(cfg.milestones) - 1


def cumulative_tests(cfg: Config, mid: str) -> list[str]:
    """Ordered, de-duplicated selector tokens for a milestone's cumulative gate
    (every milestone from the first through ``mid``)."""
    idx = index_of(cfg, mid)
    tokens: list[str] = []
    for m in cfg.milestones[: idx + 1]:
        for t in m.tests:
            if t not in tokens:
                tokens.append(t)
    return tokens


def gate_string(cfg: Config, mid: str) -> str:
    """Render the cumulative gate for ``mid`` via ``cfg.gate_template``.

    Placeholders: ``{tests_or}`` (" or "-joined), ``{tests_space}`` (space-joined),
    ``{tests_csv}`` (comma-joined), ``{marker}`` (this milestone's marker).
    Returns "" when the milestone has no cumulative tests (e.g. a skeleton gate).
    """
    tokens = cumulative_tests(cfg, mid)
    if not tokens:
        return ""
    return cfg.gate_template.format(
        tests_or=" or ".join(tokens),
        tests_space=" ".join(tokens),
        tests_csv=",".join(tokens),
        marker=by_id(cfg, mid).marker,
    )


def matrix(cfg: Config) -> str:
    """Human-readable milestone matrix + resolved gates."""
    lines = []
    for m in cfg.milestones:
        gate = gate_string(cfg, m.id) or "(no test gate)"
        lines.append(f"{m.id}  {m.title}")
        lines.append(f"     goal: {m.goal}")
        lines.append(f"     gate: {gate}")
    return "\n".join(lines)
