"""Pytest collection guard for the experiments/recodeagent package.

`test_compare.py` is a harness MODULE (RQ2 test-comparison logic), not a test
suite -- but its filename matches pytest's default `test_*.py` discovery
glob. This repository has no root-level `pytest.ini` / `[tool.pytest.ini_options]`
`testpaths` restricting discovery to `tests/`, so invoking `pytest` from the
repository root would otherwise attempt to import and collect
`test_compare.py` as a test module. Exclude it (and guard against any future
harness module that happens to match `test_*.py`) explicitly so the harness
implementation package is never accidentally treated as a test suite.

The actual automated tests for this harness live under `tests/experiments/`
(see `tests/experiments/test_test_compare.py` for `test_compare.py`'s tests).
"""
from __future__ import annotations

collect_ignore = ["test_compare.py"]
