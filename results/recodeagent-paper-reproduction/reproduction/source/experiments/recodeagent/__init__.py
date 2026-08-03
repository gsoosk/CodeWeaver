"""ReCodeAgent-paper reproduction harness for CodeWeaver.

This package (``experiments/recodeagent``) is a self-contained, additive
experiment harness. It does not modify CodeWeaver core; it drives it (via its
public CLI / config / prompts / copilot modules) and independently measures the
results. See ``README.md`` in this directory for the full protocol, exact
commands, and provenance/licensing notes.

Pipeline stages (one module each, runnable standalone or via ``cli.py``):

    acquire      -> verify + extract the official ReCodeAgent artifact
    manifest     -> deterministically discover the 118 benchmark projects
    prepare      -> build isolated, leakage-safe per-project workspaces
    run          -> execute CodeWeaver (full pipeline or an RQ3 ablation variant)
    collect      -> ingest real run outputs into normalized raw_runs.csv/jsonl
    merge        -> strictly combine disjoint collection shards
    test_compare -> RQ2 source<->target developer-test comparison
    merge_paper  -> strictly combine disjoint paper-test/generated-test shards
    analyze      -> RQ1-RQ4 tables/figures from measured data only
    report       -> final reproducibility_report.{pdf,md}
    package      -> Git-ready data/PDF/provenance/raw-archive repository

Nothing in this package fabricates results: every measurement is either a real
observation (with provenance) or an explicit ``missing``/``unavailable``/``error``
status -- never a silent zero or fabricated success.
"""

from __future__ import annotations

__version__ = "0.1.0"
