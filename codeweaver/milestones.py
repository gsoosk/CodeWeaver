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

import re

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


def gate_string(cfg: Config, mid: str, skips: list[str] | None = None) -> str:
    """Render the cumulative gate for ``mid`` via ``cfg.gate_template``.

    Placeholders in ``gate_template``: ``{tests_or}`` (" or "-joined),
    ``{tests_space}`` (space-joined), ``{tests_csv}`` (comma-joined), ``{marker}``
    (this milestone's marker), and ``{skip_exclude}`` -- the deselection clause for
    deferred/known-failing tests (skip-on-give-up), rendered from
    ``cfg.skip_exclude_template``. Put ``{skip_exclude}`` INSIDE the selector so it
    composes correctly (e.g. pytest ``-k "{tests_or}{skip_exclude}"`` with
    ``skip_exclude_template = ' and not ({tests_or})'``). When there are no
    ``skips`` or no ``skip_exclude_template``, ``{skip_exclude}`` renders empty.
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
        skip_exclude=skip_exclusion(cfg, skips or []),
    )


def skip_tokens(cfg: Config, skips: list[str]) -> list[str]:
    """Normalise deferred test ids into selector tokens for ``skip_exclude_template``.

    A recorded skip is a test *id* as the validator reported it (e.g. a pytest node
    id ``tests/test_dom.py::test_x[case]``), but a selector clause usually needs a
    bare token (``-k`` only accepts identifier-ish words -- a malformed ``-k`` makes
    pytest error out and would fail the whole gate). ``cfg.skip_token_pattern`` is
    the runner-specific regex that extracts that token: group 1 when the pattern
    defines one, else the whole match. An id that does not match is DROPPED rather
    than emitted malformed. With no pattern configured, ids are used verbatim.
    """
    ids = [s for s in (skips or []) if s]
    if not cfg.skip_token_pattern:
        return list(dict.fromkeys(ids))
    try:
        pattern = re.compile(cfg.skip_token_pattern)
    except re.error as e:
        print(f"[codeweaver] warning: invalid skip_token_pattern "
              f"{cfg.skip_token_pattern!r}: {e}; using skip ids verbatim")
        return list(dict.fromkeys(ids))

    out: list[str] = []
    for s in ids:
        m = pattern.search(s)
        if not m:
            print(f"[codeweaver] warning: deferred test id {s!r} does not match "
                  "skip_token_pattern; it will NOT be deselected from the gate")
            continue
        tok = (m.group(1) if m.re.groups else m.group(0)).strip()
        if tok and tok not in out:
            out.append(tok)
    return out


def skip_exclusion(cfg: Config, skips: list[str]) -> str:
    """Render the deselection clause for deferred/known-failing tests from
    ``cfg.skip_exclude_template`` (placeholders {tests_or}/{tests_space}/{tests_csv}
    over the SKIP tokens), or "" when there are no skips / no template.

    The ids are first normalised into runner-safe selector tokens (see
    :func:`skip_tokens`)."""
    if not cfg.skip_exclude_template:
        return ""
    tokens = skip_tokens(cfg, skips or [])
    if not tokens:
        return ""
    return cfg.skip_exclude_template.format(
        tests_or=" or ".join(tokens),
        tests_space=" ".join(tokens),
        tests_csv=",".join(tokens),
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
