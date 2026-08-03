"""Unified CLI dispatcher for the ReCodeAgent-paper reproduction harness.

Usage::

    python -m experiments.recodeagent <stage> [stage-specific arguments...]
    python -m experiments.recodeagent --help
    python -m experiments.recodeagent <stage> --help

This module defines *no* experiment arguments of its own. Each stage
(``acquire``, ``manifest``, ``prepare``, ``run``, ``collect``,
``test-compare``, ``analyze``, ``report``, ``package``) owns its own ``build_parser()`` /
``main(argv)`` pair, which remains the single source of truth for that
stage's CLI surface -- this dispatcher only looks at ``argv[0]`` to decide
which stage module to import and forwards the rest of ``argv`` to it
unmodified. This avoids any duplication or drift between this file and the
per-stage argument definitions.

See ``README.md`` in this directory for the exact end-to-end sequence of
commands, provenance/licensing notes, and integration assumptions.
"""
from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence

#: Stage name (as typed on the command line) -> importable module path.
#: Order here is the recommended end-to-end execution order.
_STAGE_MODULES: dict[str, str] = {
    "acquire": "experiments.recodeagent.acquire",
    "manifest": "experiments.recodeagent.manifest",
    "prepare": "experiments.recodeagent.prepare",
    "run": "experiments.recodeagent.run",
    "collect": "experiments.recodeagent.collect",
    "merge-collections": "experiments.recodeagent.merge_collections",
    "test-compare": "experiments.recodeagent.test_compare",
    "paper-test-compare": "experiments.recodeagent.paper_test_compare",
    "merge-paper": "experiments.recodeagent.merge_paper_results",
    "analyze": "experiments.recodeagent.analyze",
    "report": "experiments.recodeagent.report",
    "package": "experiments.recodeagent.package_results",
}

#: One-line summaries shown in top-level --help. Kept in sync with each
#: stage module's own argparse `description=` by convention, not by import,
#: so this dispatcher never has to execute stage modules just to print help.
_STAGE_SUMMARIES: dict[str, str] = {
    "acquire": "Verify (and optionally download/extract) the official ReCodeAgent artifact.",
    "manifest": "Discover the 118 benchmark projects -> manifest.json/csv.",
    "prepare": "Build isolated, leakage-safe per-project CodeWeaver workspaces.",
    "run": "Execute the reproduction matrix (variant x project x repetition).",
    "collect": "Ingest run.py outputs -> raw_runs.csv/jsonl + failures.csv.",
    "merge-collections": "Strictly merge disjoint collect.py output shards.",
    "test-compare": "RQ2: map source<->target developer tests; write comparison metrics.",
    "paper-test-compare": "RQ2: run the pinned official AST comparator and exact paper inventory.",
    "merge-paper": "Strictly merge disjoint paper-test comparison shards.",
    "analyze": "RQ1-RQ4 tables/figures from collect.py + test_compare.py outputs only.",
    "report": "Final reproducibility_report.{pdf,md} + manifest/checksum/provenance JSON.",
    "package": "Build the final Git-ready results repository with data, PDFs, and raw archives.",
}

#: Alternate spellings a user might reasonably type, normalized before lookup.
_STAGE_ALIASES: dict[str, str] = {
    "test_compare": "test-compare",
}

_PROG = "python -m experiments.recodeagent"


def _print_top_level_help() -> None:
    width = max(len(name) for name in _STAGE_MODULES)
    lines = [
        "ReCodeAgent-paper reproduction harness for CodeWeaver.",
        "",
        f"usage: {_PROG} <stage> [stage-specific arguments...]",
        "",
        "Stages (recommended end-to-end order):",
    ]
    for name, module_path in _STAGE_MODULES.items():
        lines.append(f"  {name.ljust(width)}  {_STAGE_SUMMARIES[name]}")
        del module_path  # summaries are shown, not module paths
    lines += [
        "",
        f"Run '{_PROG} <stage> --help' to see that stage's own arguments.",
        "See README.md for exact commands, provenance, and licensing notes.",
        "Nothing in this harness fabricates results: missing data is reported",
        "as missing/unavailable/error, never as a silent zero or success.",
    ]
    print("\n".join(lines))


def _resolve_stage(raw_stage: str) -> str | None:
    stage = _STAGE_ALIASES.get(raw_stage, raw_stage)
    return stage if stage in _STAGE_MODULES else None


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw or raw[0] in ("-h", "--help"):
        _print_top_level_help()
        return 0
    stage = _resolve_stage(raw[0])
    if stage is None:
        print(f"{_PROG}: unknown stage {raw[0]!r}", file=sys.stderr)
        print(f"valid stages: {', '.join(_STAGE_MODULES)}", file=sys.stderr)
        return 2
    module = importlib.import_module(_STAGE_MODULES[stage])
    return int(module.main(raw[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
