#!/bin/bash
# check.sh - verify the DETERMINISTIC orchestrator offline (no live agents, no
# Copilot). Runs the four behaviours end-to-end against the mock agent for a
# given project config and prints a summary.
#
#   bash tools/check.sh [path/to/codeweaver.toml]
#
# Defaults to examples/minimal/codeweaver.toml. Thin wrapper over
# `codeweaver check --config <cfg>`.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"     # repo root
cd "$HERE"
CFG="${1:-examples/minimal/codeweaver.toml}"
PY="${PYTHON:-python}"

exec "$PY" -m codeweaver check --config "$CFG"
