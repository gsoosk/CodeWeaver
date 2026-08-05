"""Entry point for ``python -m experiments.recodeagent``.

Delegates to :mod:`experiments.recodeagent.cli`, which dispatches to the
individual stage modules (``acquire``, ``manifest``, ``prepare``, ``run``,
``collect``, ``merge-collections``, ``test-compare``, ``analyze``, ``report``,
``package``).
"""
from __future__ import annotations

from experiments.recodeagent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
