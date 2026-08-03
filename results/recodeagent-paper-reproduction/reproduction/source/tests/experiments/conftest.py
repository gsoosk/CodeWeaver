"""Pytest configuration for the ReCodeAgent harness test suite.

Ensures the repo root is on sys.path so tests can `import experiments.recodeagent...`
without requiring the harness to be installed as a package. No network, LLM, or
toolchain access is performed anywhere in this test tree -- everything runs
against synthetic fixtures created on the fly (see individual test modules).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
