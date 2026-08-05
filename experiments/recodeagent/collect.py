"""collect.py -- ingest ONLY the actual outputs of a run.py execution and turn
them into normalized, honest per-run measurements.

For every (variant, project_id, repetition) combination this module:

  1. Reads the run's OWN persisted state (``recodeagent_run_state.json``,
     written atomically by run.py) verbatim -- it never re-derives or
     second-guesses run.py's own status.
  2. INDEPENDENTLY runs the project's configured build/unit-test commands
     against the run's OWN produced target tree (``pipeline/target``, i.e.
     ``codeweaver.toml``'s ``working_copy``) -- never trusts an agent's own
     self-reported success. Commands come from experiment.toml's per-dataset
     ``build_cmd``/``unit_test_cmd`` argument *arrays* (never the flattened
     shell-string form baked into the per-project codeweaver.toml, which
     exists only to be quoted into an agent prompt) so execution never goes
     through a shell.
  3. Parses whatever trajectory evidence the run actually produced:
       - ``full``, and the three stage-skip ablations ``noanalyzer``/
         ``noplanning``/``novalidator``: all four now run the identical
         real ``python -m codeweaver run`` CLI subprocess end to end
         (CodeWeaver core's own ``CODEWEAVER_SKIP_STAGES`` instrumentation
         -- see ``run.py.STAGE_SKIP_VARIANTS`` -- makes the three named
         ablations omit exactly one stage's real work while every other
         Burr milestone/repair/parity behavior is preserved), so all four
         are reconstructed the same way: the CLI subprocess's own stdout
         (captured by run.py to ``cli.stdout.log``) prints the exact
         per-milestone ``history`` Burr accumulated
         (``{milestone} iter={n} passed={bool|None}``) -- parsed here to
         reconstruct real loop/milestone counts. Per-agent JSONL logs under
         ``pipeline/logs/*.stdout.jsonl`` are also read for exact tool/token
         rollups. Current CodeWeaver writes one uniquely named transcript per
         invocation; legacy fixed role filenames are detected and reported as
         a ``lower_bound`` because earlier iterations may have been
         overwritten. Whichever
         one stage a given ablation skipped is EXCLUDED from ``nc``/``tec``/
         ``sec`` entirely (a skipped stage only wrote a placeholder, it
         never executed its real work) and ``novalidator``'s per-milestone
         ``passed`` (always ``None`` in the parsed history -- no validator
         attestation exists) is reported ``missing``, never a fabricated
         ``0``/``False``.
       - ``baseagent-condensed``/``baseagent-concat`` only: these remain
         harness-driven, single-shot, one-agent prompts with no Burr graph
         at all, so ``recodeagent_calls.jsonl`` (written by run.py itself)
         is their own exact, complete, call-by-call record (including a
         Copilot JSONL ``events_summary`` per call) -- reused verbatim, not
         re-derived.
  4. Runs an INDEPENDENT stub/completeness scan over the produced target
     tree (regex search for TODO/``unimplemented!()``/``NotImplementedError``/
     etc. markers) -- deliberately not trusting whatever the agent's own
     ``report.json`` claims.
  5. Measures independent-developer-test coverage where a dataset adapter is
     available.  For non-CRUST tools this module also records the official
     ReCodeAgent generated-harness result under the explicitly separate
     ``standardized_coverage_*`` family.  Paper-equivalent
     developer-plus-CodeWeaver-generated coverage is evaluated only after
     generated tests have been classified by ``paper_test_compare.py`` and is
     written to that stage's ``generated_test_projects`` artifact.  Missing
     tools or reports remain ``Status.UNAVAILABLE`` -- never a fabricated
     0%.

Every metric is a :class:`~experiments.recodeagent.common.Measurement` --
missing/unavailable/error is never coerced to 0 or success. Runs that have not
reached a terminal state (``pending``/``running``), or that could not even be
opened, are written to ``failures.csv`` and excluded from ``raw_runs.csv`` --
never zero-filled into the measured table.

Nothing here spawns a shell (:func:`experiments.recodeagent.common.run_argv`
only, or an injected fake in tests) and nothing here mutates a run directory
except by writing new ``*.collected.json`` sidecar files it itself owns.

POST-HOC INDEPENDENT EVALUATOR (translated vs. validated developer tests).
The measurements above (``dev_tests_*``/``dev_test_pass_rate``, aliased below
as ``translated_tests_*``) run the project's OWN configured test command
against the run's OWN produced target tree -- this is CodeWeaver's
*translated* developer-test suite, self-graded against whatever tests
happen to live in ``pipeline/target`` right now (which may itself be a
CodeWeaver-authored rewrite of the original developer tests, not the
paper's own oracle). The paper's RQ1 "validated developer tests" TPR is a
methodologically DIFFERENT measurement: the ORIGINAL, paper-authored
developer-test suite, run against the CodeWeaver translation, completely
independent of whatever CodeWeaver itself produced as "its own" tests. This
module adds a structurally separate ``validated_tests_*``/
``function_validation_*``/``oracle_integrity`` family of fields (see
``evaluate_independent_oracle`` below) computed as follows, per tool:

  - **CRUST**: the paper-provided scaffold (``run_dir/scaffold``, a pristine,
    never-mutated-by-this-harness copy materialized once by ``prepare.py``/
    ``run.py`` -- see their own docstrings) already IS the paper's test
    oracle (an interface + test CONTRACT with unimplemented bodies). This
    harness overlays that scaffold's own Cargo contract paths (manifest/
    lockfile, ``src/bin/**`` harness binaries, ``tests/`` if present) on top
    of a TEMPORARY copy of the run's produced target, then runs the exact
    same ``unit_test_cmd`` -- independent of whatever the agent's own
    ``pipeline/target`` happens to contain. Some scaffolds' ``src/bin/*.rs``
    files are "binary assertion harnesses" -- a plain ``fn main()`` with no
    ``#[test]`` attribute at all, whose own process exit code IS the test
    verdict (e.g. the real CRUST ``libfor`` project's ``src/bin/test.rs``)
    -- ``cargo test`` never discovers/runs these, so they are separately
    detected (``crust_binary_test_harnesses``) and executed one process at a
    time (``crust_run_binary_test_harnesses``, default ``cargo run --bin
    <name>``) and merged into the same executed/passed/failed counts.
    ``validated_tests_expected`` for CRUST is reconciled from TWO
    structurally separate sources -- see
    [CRUST's native-vs-paper-aligned expected-test-count](#crusts-native-vs-paper-aligned-expected-test-count)
    -- a NATIVE, static ``#[test]``-attribute (plus binary-harness) count
    over the scaffold alone (``validated_tests_expected_native``), and an
    optional, authoritative PAPER-ALIGNED count read from either the
    official ``results.xlsx``'s own ``"sweagent crust - tool test"`` sheet
    or an explicit reference-inventory file (``--crust-paper-expected-tests``,
    ``validated_tests_expected_paper``) -- the two are known to disagree in
    BOTH directions for real projects and are NEVER silently presented as
    equal; the paper-aligned figure is preferred when available
    (``validated_tests_expected_source`` records which one won).
    ``oracle_integrity`` separately hash-compares the scaffold's contract
    paths against the run's own (mutable) target copy to detect whether the
    agent obeyed CodeWeaver's own "never modify the immutable input" prompt
    instruction (a prompt-only convention, not filesystem-enforced -- see
    ``codeweaver/prompts.py``); a "mutated" verdict means self-reported
    target tests are untrustworthy, but the pristine-overlay evaluation
    above remains valid regardless. Per-function validation is
    ``Status.NOT_APPLICABLE`` for CRUST (the paper validates at whole-crate
    granularity only).
  - **Oxidizer/AlphaTrans**: the paper's own oracle is not shipped inside
    ``implementation.zip``'s per-project workspace at all -- it only exists
    inside the separately-acquired official RESULTS artifact, at
    ``<reference-results-root>/recodeagent_translations/data/tool_projects/
    {tool}/{project}``. When ``--reference-results-root`` is not supplied,
    or a project isn't found under it, these fields are ``Status.
    UNAVAILABLE`` with an explicit reason -- NEVER a silent fallback to the
    translated-test numbers above. Oxidizer classifies
    ``<ref>/rust/tests/*.rs`` into developer-test oracle files (``*_test.rs``)
    and per-function validation harness files (other plain ``.rs`` files);
    files containing "generated" are evaluated separately as the standardized
    generated-test harness described below.
    AlphaTrans copies only ``<ref>/verified_test/`` and runs
    ``python -m pytest -q verified_test``; no reusable PER-FUNCTION harness
    (a reliable one-to-one function mapping) is known for AlphaTrans, so its
    ``function_validation_*`` is always ``Status.UNAVAILABLE`` (a reason,
    not a fabricated symbol-ratio substitute -- that ratio remains a
    separate ``function_translation_ratio`` completeness metric, never
    relabeled as validation).
  - **SKEL**: no separate independent-oracle FILE TREE is shipped for this
    tool the way the other three each get one -- ``javascript/source.js``
    embeds BOTH the reference implementation AND its own translated test
    functions together as plain top-level declarations. When
    ``--reference-results-root`` is supplied, ``skel_validated_tests_eval``
    (see its own docstring, near ``skel_function_harness_eval`` below) uses
    ``tree-sitter``/``tree-sitter-javascript`` (an OPTIONAL dependency,
    probed via ``C.optional_import`` exactly like this module's other
    optional-library integrations -- never installed by this harness) to
    AST-extract ONLY each project test listed by ``test_name_mapping.csv``
    function bodies (never the rest of ``source.js``, never any private
    helper it references) into a synthetic harness that binds against
    CodeWeaver's OWN target exports, so ``validated_tests_*`` becomes a real
    ``Status.MEASURED`` result for SKEL wherever extraction succeeds.
    ``Status.UNAVAILABLE`` (with a precise reason, e.g. tree-sitter not
    installed, no CSV/``source.js`` resolved, or every verified test blocked
    by an unresolvable private-helper reference) remains the honest outcome
    otherwise -- never a silent fallback to the translated-test numbers. It
    likewise has no reliable PER-FUNCTION harness, so ``function_validation_*``
    is always ``Status.UNAVAILABLE`` too (see ``function_harness_tests_*``
    below for SKEL's separate GENERATED function-harness execution
    evidence, which remains structurally distinct from this AST-extracted
    developer-test oracle).

GENERATED function/test-harness EXECUTION EVIDENCE (``function_harness_tests_*``).
Oxidizer, AlphaTrans, and SKEL each ship a reusable, EXECUTABLE, GENERATED
target-language test harness in the official RESULTS artifact -- distinct from
both the developer-test oracle above AND from ``function_validation_*``
(which requires a reliable one-to-one per-function mapping neither tool is
known to have). This module reports that evidence as a structurally
SEPARATE ``function_harness_tests_total/passed/failed/pass_rate`` field
family (never blended into, or inferred as, ``function_validation_*``):

  - **Oxidizer**: each ``rust/tests/*generated*.rs`` integration-test binary
    is staged independently against CodeWeaver's target and run with
    ``cargo test --test <name>``. This remains separate from the plain
    non-generated per-function harness reported as ``function_validation_*``.
  - **AlphaTrans**: copies only ``<ref>/agent_test/`` files whose basename
    contains "generated" (case-insensitive; e.g. ``FooTest_generated.py``,
    ``FooGeneratedTest.py``), plus their ``conftest.py``/``__init__.py``
    support files and everything under an ``agent_test/resources/`` sibling
    directory (real project layouts nest these at varying depths -- see
    ``alphatrans_function_harness_files``) -- NEVER the official system's
    own plain, non-generated ``XxxTest.py`` files (a different metric) and
    NEVER the reference's Python production implementation under
    ``<ref>/python`` -- into a TEMPORARY copy of the CodeWeaver target,
    preserving relative structure, then runs
    ``python -m pytest -q agent_test``.
  - **SKEL**: copies only ``<ref>/javascript/*.js`` files whose basename
    contains "generated" (e.g. ``SKELTest_generated.js``, and some projects'
    additional ``*FunctionsTest_generated.js``) -- NEVER the reference's own
    ``source.js`` production implementation or any of its internal-only
    helpers (e.g. some projects' ``tracer_skip.js``) -- flat into a
    TEMPORARY copy of the CodeWeaver target, ADDITIONALLY copying
    CodeWeaver's own ``index.js`` entry file to an extra ``source.js`` alias
    (never renaming/removing the original) so the reference tests' own
    ``require('./source.js')`` calls resolve against CodeWeaver's actual
    translation. Four official scripts that inline reference implementations
    are AST-rewritten to remove those declarations and bind only to
    CodeWeaver's target. SKEL's generated tests are ad hoc scripts with no
    shared framework, so this adapter invokes ``node <file>.js`` once per
    selected file; after every script exits zero it reports the paper's exact
    306-case inventory, while an early-aborting failure leaves case-level
    counts unavailable rather than substituting a file count.
  - Where no exact per-function denominator can be established from these
    suites (AlphaTrans and SKEL), ``function_validation_*`` stays
    ``Status.UNAVAILABLE`` -- ``function_harness_tests_*`` exists precisely
    so this execution evidence is still reported instead of silently
    dropped. For reference (never blended with either field): the paper's
    own function-level denominator across its three non-CRUST tools
    (Oxidizer/AlphaTrans/SKEL; CRUST validates at whole-crate granularity
    only) is 1,397 functions -- independently verified in this harness's
    own ``C.PAPER_EXERCISED_FUNCTIONS_BY_PROJECT`` inventory, derived from
    the official ``results.xlsx`` "Exercised" column. It is emitted as
    ``function_validation_expected/not_executed/paper_pass_rate``.
  - **CRUST** validates at whole-crate granularity only, so
    ``function_harness_tests_*`` is ``Status.NOT_APPLICABLE`` for it.

All independent-oracle evaluation happens inside a fresh
``tempfile.TemporaryDirectory()`` (never inside ``run_dir``,
``--workspace-root``, or ``--reference-results-root`` -- those are only ever
READ from), auto-cleaned even on exception, and only ever reached from
``collect_run`` AFTER its own existing terminal-run-status gate (i.e. only
for a run whose LLM invocation has already finished) -- so reference assets
are never even opened, let alone copied, while an LLM run is in flight.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Mapping
from dataclasses import dataclass, field, replace as dataclass_replace
from pathlib import Path
from typing import Any, Callable

from experiments.recodeagent import common as C
from experiments.recodeagent import manifest as M
from experiments.recodeagent import prepare as P
from experiments.recodeagent import run as R
from experiments.recodeagent.common import (
    ExecResult,
    Measurement,
    Status,
    atomic_write_text,
    read_json_or,
    read_jsonl,
    run_argv,
    utcnow_iso,
)

COLLECTED_MARKER = "recodeagent_collected.json"

# --------------------------------------------------------------------------- #
# Command execution boundary -- injectable so tests never spawn a real
# toolchain (cargo/npm/node/python), mirroring run.py's Executor pattern.
# --------------------------------------------------------------------------- #
CommandRunner = Callable[..., ExecResult]  # (argv, *, cwd, timeout) -> ExecResult


def default_command_runner(argv: list[str], *, cwd, timeout=None) -> ExecResult:
    resolved = list(argv)
    if resolved and resolved[0] == "python":
        resolved[0] = sys.executable
    return run_argv(resolved, cwd=cwd, timeout=timeout)


def _tail(text: str | None, limit: int = 800) -> str:
    return (text or "").strip()[-limit:]


def copy_evaluation_tree(source: Path, destination: Path) -> None:
    """Copy stable target content while excluding runtime special files."""
    source_resolved = source.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            path = Path(directory) / name
            try:
                mode = path.lstat().st_mode
            except OSError:
                ignored.add(name)
                continue
            if (
                stat.S_ISFIFO(mode)
                or stat.S_ISSOCK(mode)
                or stat.S_ISCHR(mode)
                or stat.S_ISBLK(mode)
            ):
                ignored.add(name)
                continue
            if stat.S_ISLNK(mode):
                try:
                    target = Path(os.readlink(path))
                    resolved = (
                        target.resolve()
                        if target.is_absolute()
                        else (path.parent / target).resolve()
                    )
                    resolved.relative_to(source_resolved)
                    if not resolved.exists() or not (
                        resolved.is_file() or resolved.is_dir()
                    ):
                        ignored.add(name)
                except (OSError, ValueError):
                    ignored.add(name)
        return ignored

    shutil.copytree(source, destination, symlinks=True, ignore=ignore)


# --------------------------------------------------------------------------- #
# Developer-test output parsers (pure, unit-testable with fixture text).
# Returns None (never a fabricated {"total": 0, ...}) if the text doesn't
# contain a recognizable summary for that framework.
# --------------------------------------------------------------------------- #
def parse_cargo_test_output(stdout: str, stderr: str) -> dict[str, int] | None:
    """Sums every ``test result: ok|FAILED. N passed; M failed`` line (cargo
    prints one per test binary)."""
    text = f"{stdout}\n{stderr}"
    matches = re.findall(r"test result:\s*(?:ok|FAILED)\.\s*(\d+)\s*passed;\s*(\d+)\s*failed", text)
    if not matches:
        return None
    passed = sum(int(p) for p, _ in matches)
    failed = sum(int(f) for _, f in matches)
    return {"total": passed + failed, "passed": passed, "failed": failed}


def parse_python_unittest_output(stdout: str, stderr: str) -> dict[str, int] | None:
    """Parses Python ``unittest``'s ``Ran N tests ...`` / ``OK`` / ``FAILED
    (failures=X, errors=Y)`` summary block."""
    text = f"{stdout}\n{stderr}"
    m_ran = re.search(r"Ran (\d+) tests?\b", text)
    if not m_ran:
        return None
    total = int(m_ran.group(1))
    failed = 0
    m_fail = re.search(r"FAILED\s*\(([^)]*)\)", text)
    if m_fail:
        for part in m_fail.group(1).split(","):
            m = re.match(r"\s*(?:failures|errors)\s*=\s*(\d+)", part)
            if m:
                failed += int(m.group(1))
    return {"total": total, "passed": max(total - failed, 0), "failed": failed}


def parse_jest_output(stdout: str, stderr: str) -> dict[str, int] | None:
    """Parses Jest's default ``Tests: X failed, Y skipped, Z passed, N
    total`` summary line (failed/skipped clauses are optional)."""
    text = f"{stdout}\n{stderr}"
    m = re.search(
        r"Tests:\s*(?:(\d+)\s*failed,\s*)?(?:(\d+)\s*skipped,\s*)?(\d+)\s*passed,\s*(\d+)\s*total", text
    )
    if not m:
        return None
    failed = int(m.group(1) or 0)
    passed = int(m.group(3))
    total = int(m.group(4))
    return {"total": total, "passed": passed, "failed": failed}


def parse_node_tap_output(stdout: str, stderr: str) -> dict[str, int] | None:
    """Parses Node's built-in test runner TAP summary (``# pass N`` / ``# fail
    M``)."""
    text = f"{stdout}\n{stderr}"
    m_pass = re.search(r"#\s*pass\s+(\d+)", text)
    m_fail = re.search(r"#\s*fail\s+(\d+)", text)
    if not m_pass and not m_fail:
        return None
    passed = int(m_pass.group(1)) if m_pass else 0
    failed = int(m_fail.group(1)) if m_fail else 0
    return {"total": passed + failed, "passed": passed, "failed": failed}


_PYTEST_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed|xpassed)\b")


def parse_pytest_output(stdout: str, stderr: str) -> dict[str, int] | None:
    """Parses ``pytest``'s final summary line (e.g. ``5 passed, 2 failed in
    0.42s``, ``3 passed in 0.10s``, ``1 failed, 1 error in 0.05s`` -- errors
    are counted as failed, matching this harness's ``total=passed+failed``
    convention elsewhere; ``skipped``/``xfailed``/``xpassed`` are parsed but
    excluded from ``total``, matching how cargo's own ``ignored`` count is
    treated). Used by the AlphaTrans independent-oracle check
    (``python -m pytest -q verified_test``), distinct from the
    ``python_unittest`` parser used for AlphaTrans's OWN ``unittest
    discover``-based dev-test command. Returns None -- never a fabricated
    ``{"total": 0, ...}`` -- if no recognizable summary line is present at
    all (pytest not installed / a crash before any summary was printed)."""
    text = f"{stdout}\n{stderr}"
    m = re.search(r"^(.*\bin\s+[\d.]+\s*s.*)$", text, re.MULTILINE)
    if m is None:
        if re.search(r"\bno tests ran\b", text, re.IGNORECASE):
            return {"total": 0, "passed": 0, "failed": 0}
        return None
    counts: dict[str, int] = {}
    for digits, label in _PYTEST_COUNT_RE.findall(m.group(1)):
        counts[label] = counts.get(label, 0) + int(digits)
    if not counts:
        # Real pytest actually prints its own duration suffix on the "no
        # tests ran" line too (e.g. "no tests ran in 0.00s"), so that line
        # DOES match the "in [\d.]+s" summary regex above -- it must be
        # recognized here (inside the summary line itself), not only in the
        # `m is None` branch above, or this legitimate zero-tests-collected
        # case would be misreported as an unrecognized/unavailable format.
        if re.search(r"\bno tests ran\b", m.group(1), re.IGNORECASE):
            return {"total": 0, "passed": 0, "failed": 0}
        return None
    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
    return {"total": passed + failed, "passed": passed, "failed": failed}


TEST_OUTPUT_PARSERS: dict[str, Callable[[str, str], dict[str, int] | None]] = {
    "cargo_test": parse_cargo_test_output,
    "python_unittest": parse_python_unittest_output,
    "jest": parse_jest_output,
    "node_tap": parse_node_tap_output,
    "pytest": parse_pytest_output,
}

# tool key -> parser id (matches experiment.toml's unit_test_cmd per dataset).
# A dataset may override this via an explicit "test_output_format" key in its
# [datasets.<tool>] table; this is only the harness's own sensible default.
TOOL_TEST_PARSER_ID: dict[str, str] = {
    "crust": "cargo_test",
    "oxidizer": "cargo_test",
    "alphatrans": "python_unittest",
    "skel": "jest",
}


def parse_test_output(tool: str, stdout: str, stderr: str, *,
                      dataset_spec: dict[str, Any] | None = None) -> dict[str, int] | None:
    parser_id = (dataset_spec or {}).get("test_output_format") or TOOL_TEST_PARSER_ID.get(tool)
    parser = TEST_OUTPUT_PARSERS.get(parser_id) if parser_id else None
    if parser is None:
        return None
    return parser(stdout, stderr)


# Tool-agnostic, best-effort extraction of the most informative recognizable
# compiler/interpreter ERROR line from a test command's own stdout/stderr,
# used ONLY to make an otherwise-generic "output did not match a recognized
# summary format" Measurement.reason CONCRETE and actionable (almost always
# this means the reference/oracle files never compiled/imported at all, i.e.
# zero tests ever ran -- structurally distinct from a real, executed,
# failing assertion). Recognizes rustc/cargo's own ``error[E0425]: ...``/
# ``error: ...`` lines and any ``XxxError``/``XxxException`` line (covers
# Python's ImportError/ModuleNotFoundError/SyntaxError/AttributeError and
# JS's ReferenceError/TypeError/... without enumerating each one) as the
# SPECIFIC/informative pattern -- preferring the LAST such line found (a
# Python traceback's actual raised exception, or cargo's final summary
# error, is normally the most relevant single line, especially with
# multiple/chained errors). Only falls back to a bare ``Traceback (most
# recent call last):`` preamble line -- deliberately never preferred over a
# specific error line, since alone it names no actual error -- or, lacking
# even that, the LAST non-blank stderr (then stdout) line, when no specific
# pattern is recognized at all: still more actionable than nothing. Returns
# None (never raises, never fabricates) only when stdout AND stderr are both
# entirely blank.
_SPECIFIC_ERROR_LINE_RE = re.compile(
    r"^(?:error(?:\[[A-Za-z0-9]+\])?\s*:.*|.*\b[A-Z][A-Za-z0-9]*(?:Error|Exception)\b\s*:.*)$",
    re.MULTILINE,
)
_TRACEBACK_PREAMBLE_RE = re.compile(r"^.*\bTraceback \(most recent call last\):.*$", re.MULTILINE)


def extract_compiler_error_snippet(stdout: str, stderr: str, *, max_len: int = 300) -> str | None:
    combined = f"{stderr}\n{stdout}"
    specific = list(_SPECIFIC_ERROR_LINE_RE.finditer(combined))
    if specific:
        snippet = specific[-1].group(0).strip()
    else:
        preamble = _TRACEBACK_PREAMBLE_RE.search(combined)
        snippet = preamble.group(0).strip() if preamble else None
        if not snippet:
            for text in (stderr, stdout):
                for line in reversed(text.splitlines()):
                    if line.strip():
                        snippet = line.strip()
                        break
                if snippet:
                    break
    if not snippet:
        return None
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 3] + "..."
    return snippet


# AlphaTrans's independent-oracle command (see "POST-HOC INDEPENDENT
# EVALUATOR" above): the reference results tree's own ``verified_test/`` is
# copied into a temporary target copy and exercised with pytest specifically
# (NOT ``unittest discover``, which would also collect CodeWeaver's own
# self-authored tests elsewhere in the copied tree). Overridable per-call via
# an explicit ``pytest_cmd`` argument, never a new CLI flag.
ALPHATRANS_VERIFIED_TEST_CMD: tuple[str, ...] = ("python", "-m", "pytest", "-q", "verified_test")

# AlphaTrans's GENERATED function-harness test command -- runs pytest
# against exactly the copied-in ``agent_test/`` subtree (see
# ``alphatrans_function_harness_files``), structurally separate from
# ``ALPHATRANS_VERIFIED_TEST_CMD`` above (the independent developer-test
# oracle). Overridable per-call via an explicit ``pytest_cmd`` argument,
# never a new CLI flag.
ALPHATRANS_FUNCTION_HARNESS_TEST_CMD: tuple[str, ...] = ("python", "-m", "pytest", "-q", "agent_test")

# SKEL's own target entry file (see experiment.toml's [datasets.skel]
# build_cmd, "node --check index.js") vs. the reference results artifact's
# generated test files' own ``require('./source.js')``/``require('./source')``
# expectation (verified directly against the official RESULTS artifact --
# see README). This harness NEVER renames/removes CodeWeaver's own entry
# file; it additionally copies it, once, to this alias name inside a
# TEMPORARY evaluation copy only, so the reference's own generated tests
# resolve their import against CodeWeaver's actual translation instead of
# the (never-copied) reference implementation.
SKEL_TARGET_ENTRY_FILENAME = "index.js"
SKEL_REFERENCE_ENTRY_ALIAS = "source.js"


# --------------------------------------------------------------------------- #
# Coverage output parsers -- best-effort, optional. A dataset only gets
# coverage measured at all if its experiment.toml entry configures a
# `coverage_cmd` (argv list) AND a recognized `coverage_format`; by default
# none is configured (Status.UNAVAILABLE), since this sandbox cannot verify
# which coverage tool (if any) the real toolchain provides.
# --------------------------------------------------------------------------- #
def parse_coverage_py_json(text: str) -> float | None:
    """``coverage json`` output: ``{"totals": {"percent_covered": NN.N}}``."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    totals = data.get("totals") if isinstance(data, dict) else None
    pct = totals.get("percent_covered") if isinstance(totals, dict) else None
    return float(pct) if isinstance(pct, (int, float)) else None


def parse_tarpaulin_json(text: str) -> float | None:
    """``cargo tarpaulin --out Json``: a top-level ``"coverage"`` percentage."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    pct = data.get("coverage") if isinstance(data, dict) else None
    return float(pct) if isinstance(pct, (int, float)) else None


def parse_istanbul_summary_json(text: str) -> float | None:
    """nyc/istanbul's ``coverage-summary.json``: ``total.lines.pct``."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    total = data.get("total") if isinstance(data, dict) else None
    lines = total.get("lines") if isinstance(total, dict) else None
    pct = lines.get("pct") if isinstance(lines, dict) else None
    return float(pct) if isinstance(pct, (int, float)) else None


COVERAGE_PARSERS: dict[str, Callable[[str], float | None]] = {
    "coverage_py_json": parse_coverage_py_json,
    "tarpaulin_json": parse_tarpaulin_json,
    "istanbul_json_summary": parse_istanbul_summary_json,
}


def _tarpaulin_path_key(path_value: Any) -> str:
    if isinstance(path_value, list):
        return "/" + "/".join(str(part) for part in path_value if part)
    return str(path_value)


def _load_tarpaulin_line_report(path: Path) -> tuple[dict[str, set[int]], dict[str, int]] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    covered: dict[str, set[int]] = {}
    coverable: dict[str, int] = {}
    for file_row in data.get("files", []) if isinstance(data, dict) else []:
        if not isinstance(file_row, dict):
            continue
        key = _tarpaulin_path_key(file_row.get("path", ""))
        normalized = key.replace("\\", "/")
        if (
            "/src/bin/" in normalized
            or "/tests/" in normalized
            or normalized.endswith("/build.rs")
        ):
            continue
        lines = {
            int(trace["line"])
            for trace in file_row.get("traces", [])
            if (
                isinstance(trace, dict)
                and isinstance(trace.get("line"), int)
                and isinstance(trace.get("stats"), dict)
                and trace["stats"].get("Line", 0) > 0
            )
        }
        covered[key] = lines
        raw_coverable = file_row.get("coverable", 0)
        coverable[key] = int(raw_coverable) if isinstance(raw_coverable, (int, float)) else 0
    return covered, coverable


def _merge_tarpaulin_line_reports(
    paths: list[Path],
) -> tuple[dict[str, set[int]], dict[str, int]]:
    covered: dict[str, set[int]] = {}
    coverable: dict[str, int] = {}
    for path in paths:
        parsed = _load_tarpaulin_line_report(path)
        if parsed is None:
            continue
        report_covered, report_coverable = parsed
        for key, lines in report_covered.items():
            covered.setdefault(key, set()).update(lines)
        for key, count in report_coverable.items():
            coverable[key] = max(coverable.get(key, 0), count)
    return covered, coverable


def _rust_test_target_args(relative_path: str) -> tuple[str, ...]:
    path = Path(relative_path)
    parts = path.parts
    if parts and parts[0] == "tests":
        return ("--test", path.stem)
    if len(parts) >= 3 and parts[0] == "src" and parts[1] == "bin":
        return ("--bin", path.stem)
    return ("--lib",)


def _cargo_listed_test_names(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"(?m)^(.+?): test\s*$", text)
    ]


def _normalized_test_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _run_tarpaulin_target(
    target_dir: Path,
    *,
    target_args: tuple[str, ...],
    output_dir: Path,
    timeout: float | None,
    runner: CommandRunner,
    exact_test_name: str | None = None,
    test_args: list[str] | None = None,
    expected_test_count: int | None = None,
) -> tuple[Path | None, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    argv = [
        "cargo", "tarpaulin", *target_args, "--no-fail-fast",
        "-o", "Json", "--output-dir", str(output_dir), "--",
    ]
    if exact_test_name is not None:
        argv.extend([exact_test_name, "--exact"])
    elif test_args:
        argv.extend(test_args)
    argv.append("--test-threads=1")
    result = runner(argv, cwd=target_dir, timeout=timeout or 300)
    report = output_dir / "tarpaulin-report.json"
    if report.is_file():
        if expected_test_count is not None:
            parsed = parse_cargo_test_output(result.stdout, result.stderr)
            if parsed is None or int(parsed["total"]) != expected_test_count:
                observed = None if parsed is None else int(parsed["total"])
                return (
                    None,
                    f"tarpaulin test-count check failed: expected "
                    f"{expected_test_count}, observed {observed}",
                )
        return report, ""
    detail = "timed out" if result.timed_out else (
        result.error or _tail(result.stderr) or f"exit code {result.returncode}"
    )
    return None, detail


def _rust_generated_tarpaulin_reports(
    target_dir: Path,
    generated_tests: list[tuple[str, str]],
    *,
    output_root: Path,
    timeout: float | None,
    runner: CommandRunner,
) -> tuple[list[Path], list[str]]:
    """Run only classified CodeWeaver-authored Rust tests under tarpaulin."""
    reports: list[Path] = []
    errors: list[str] = []
    binary_tests = [
        (path, name.split(":", 1)[1])
        for path, name in generated_tests
        if name.startswith("__binary__:")
    ]
    regular_tests = [
        (path, name)
        for path, name in generated_tests
        if not name.startswith("__binary__:")
    ]

    for index, (path, binary_name) in enumerate(binary_tests):
        report, error = _run_tarpaulin_target(
            target_dir,
            target_args=("--bin", binary_name),
            output_dir=output_root / f"binary-{index}-{binary_name}",
            timeout=timeout,
            runner=runner,
        )
        if report is not None:
            reports.append(report)
        else:
            errors.append(f"{path}: {error}")

    grouped: dict[tuple[str, ...], list[tuple[str, str]]] = {}
    for path, name in regular_tests:
        grouped.setdefault(_rust_test_target_args(path), []).append((path, name))
    report_index = len(binary_tests)
    for target_args, items in sorted(grouped.items()):
        list_result = runner(
            ["cargo", "test", *target_args, "--", "--list"],
            cwd=target_dir,
            timeout=timeout,
        )
        listed = _cargo_listed_test_names(
            f"{list_result.stdout}\n{list_result.stderr}"
        )
        selected: dict[str, list[tuple[str, str]]] = {}
        for path, name in items:
            matches = [
                listed_name
                for listed_name in listed
                if _normalized_test_name(listed_name.rsplit("::", 1)[-1])
                == _normalized_test_name(name)
            ]
            if len(matches) != 1:
                detail = (
                    "not listed by cargo" if not matches
                    else f"ambiguous cargo test name ({len(matches)} matches)"
                )
                errors.append(f"{path}::{name}: {detail}")
                continue
            selected.setdefault(matches[0], []).append((path, name))
        if not selected:
            continue

        selected_names = sorted(selected)
        nonselected = [name for name in listed if name not in selected]
        grouped_output = output_root / f"group-{report_index}"
        skip_args: list[str] = []
        for name in nonselected:
            skip_args.extend(["--skip", name])
        report, error = _run_tarpaulin_target(
            target_dir,
            target_args=target_args,
            output_dir=grouped_output,
            timeout=timeout,
            runner=runner,
            test_args=skip_args,
            expected_test_count=len(selected_names),
        )
        report_index += 1
        if report is not None:
            reports.append(report)
            continue
        # A substring-based --skip may also suppress a selected test. Only
        # that count-mismatch case needs exact per-test fallbacks; a compile
        # failure with no report would simply repeat for every selector.
        if not (grouped_output / "tarpaulin-report.json").is_file():
            errors.append(
                f"{' '.join(target_args)} generated-test group: {error}"
            )
            continue
        for selected_name in selected_names:
            report, exact_error = _run_tarpaulin_target(
                target_dir,
                target_args=target_args,
                output_dir=output_root / f"test-{report_index}",
                timeout=timeout,
                runner=runner,
                exact_test_name=selected_name,
                expected_test_count=1,
            )
            report_index += 1
            if report is not None:
                reports.append(report)
            else:
                labels = ", ".join(
                    f"{path}::{name}" for path, name in selected[selected_name]
                )
                errors.append(f"{labels}: {exact_error}")
    return reports, errors


def crust_paper_coverage_pair(
    target_dir: Path,
    scaffold_dir: Path,
    *,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
    generated_tests: list[tuple[str, str]] | None = None,
) -> tuple[Measurement, Measurement]:
    """Paper-aligned CRUST line coverage using cargo-tarpaulin per binary.

    ``before`` is coverage from pristine scaffold developer-test binaries
    against CodeWeaver's implementation. ``after`` unions those reports with
    classified CodeWeaver-authored generated tests when ``generated_tests`` is
    supplied by :mod:`paper_test_compare`; the legacy no-argument path uses
    added ``src/bin`` binaries only. Existing developer binaries are restored
    from the scaffold in the temporary copy, so an agent-edited test never
    enters either coverage set.
    """
    target_bin = target_dir / "src" / "bin"
    scaffold_bin = scaffold_dir / "src" / "bin"
    if not target_dir.is_dir() or not scaffold_bin.is_dir():
        unavailable = Measurement.unavailable(
            "CRUST coverage requires a produced target and pristine scaffold/src/bin"
        )
        return unavailable, unavailable

    developer_names = sorted(p.name for p in scaffold_bin.glob("*.rs"))
    target_names = sorted(p.name for p in target_bin.glob("*.rs")) if target_bin.is_dir() else []
    generated_names = sorted(set(target_names) - set(developer_names))
    if not developer_names:
        unavailable = Measurement.unavailable("pristine CRUST scaffold has no src/bin/*.rs test binaries")
        return unavailable, unavailable

    with tempfile.TemporaryDirectory(prefix="recodeagent_crust_coverage_") as tmp:
        tmp_root = Path(tmp)
        tmp_target = tmp_root / "target"
        copy_evaluation_tree(target_dir, tmp_target)
        tmp_bin = tmp_target / "src" / "bin"
        tmp_bin.mkdir(parents=True, exist_ok=True)
        for source in scaffold_bin.glob("*.rs"):
            shutil.copy2(source, tmp_bin / source.name)

        def run_bins(names: list[str], group: str) -> tuple[list[Path], list[str]]:
            reports: list[Path] = []
            errors: list[str] = []
            for filename in names:
                binary = Path(filename).stem
                out_dir = tmp_root / "reports" / group / binary
                out_dir.mkdir(parents=True, exist_ok=True)
                result = runner(
                    [
                        "cargo", "tarpaulin", "--bin", binary, "--no-fail-fast",
                        "-o", "Json", "--output-dir", str(out_dir), "--", "--test-threads=1",
                    ],
                    cwd=tmp_target,
                    timeout=timeout or 300,
                )
                report = out_dir / "tarpaulin-report.json"
                if report.is_file():
                    reports.append(report)
                else:
                    detail = "timed out" if result.timed_out else (
                        result.error or _tail(result.stderr) or f"exit code {result.returncode}"
                    )
                    errors.append(f"{binary}: {detail}")
            return reports, errors

        developer_reports, developer_errors = run_bins(developer_names, "developer")
        if generated_tests is None:
            generated_reports, generated_errors = run_bins(generated_names, "generated")
            generated_description = (
                f"{len(generated_names)} CodeWeaver-added binary/binaries"
            )
        else:
            coverage_generated_tests: list[tuple[str, str]] = []
            for index, (relative_path, test_name) in enumerate(generated_tests):
                path = Path(relative_path)
                if (
                    not test_name.startswith("__binary__:")
                    and len(path.parts) >= 3
                    and path.parts[0] == "src"
                    and path.parts[1] == "bin"
                    and (target_dir / path).is_file()
                ):
                    # A translator may append generated #[test] functions to
                    # an existing pristine developer binary. The developer
                    # baseline above must restore that file, so preserve the
                    # translator's version under a new evaluator-only binary
                    # and select only the classified generated functions.
                    staged_relative = Path(
                        "src", "bin",
                        f"__codeweaver_generated_{index}_{path.name}",
                    )
                    shutil.copy2(
                        target_dir / path,
                        tmp_target / staged_relative,
                    )
                    coverage_generated_tests.append(
                        (staged_relative.as_posix(), test_name)
                    )
                else:
                    coverage_generated_tests.append(
                        (relative_path, test_name)
                    )
            generated_reports, generated_errors = _rust_generated_tarpaulin_reports(
                tmp_target,
                coverage_generated_tests,
                output_root=tmp_root / "reports" / "generated",
                timeout=timeout,
                runner=runner,
            )
            generated_description = (
                f"{len(generated_tests)} classified CodeWeaver-authored generated test(s)"
            )
        if not developer_reports:
            unavailable = Measurement.unavailable(
                "cargo-tarpaulin produced no developer-test reports"
                + (f": {developer_errors[:5]}" if developer_errors else "")
            )
            return unavailable, unavailable

        dev_covered, dev_coverable = _merge_tarpaulin_line_reports(developer_reports)
        gen_covered, gen_coverable = _merge_tarpaulin_line_reports(generated_reports)
        fair_coverable = dict(dev_coverable)
        for key, count in gen_coverable.items():
            fair_coverable[key] = max(fair_coverable.get(key, 0), count)
        denominator = sum(fair_coverable.values())
        if denominator <= 0:
            unavailable = Measurement.unavailable(
                "cargo-tarpaulin reports contained no coverable non-test lines"
            )
            return unavailable, unavailable

        dev_count = sum(len(lines) for lines in dev_covered.values())
        combined = {key: set(lines) for key, lines in dev_covered.items()}
        for key, lines in gen_covered.items():
            combined.setdefault(key, set()).update(lines)
        combined_count = sum(len(lines) for lines in combined.values())
        common_reason = (
            f"paper-aligned cargo-tarpaulin line union over {len(developer_names)} pristine developer "
            f"binary/binaries and {generated_description}; "
            f"coverable non-test lines={denominator}"
        )
        if developer_errors or generated_errors:
            common_reason += (
                f"; missing report(s): developer={developer_errors[:5]}, generated={generated_errors[:5]}"
            )
        return (
            Measurement(value=100.0 * dev_count / denominator, status=Status.MEASURED, reason=common_reason),
            Measurement(value=100.0 * combined_count / denominator, status=Status.MEASURED, reason=common_reason),
        )


# --------------------------------------------------------------------------- #
# Independent stub/completeness scan over the produced TARGET tree. Never
# trusts report.json / the agent's own claims.
# --------------------------------------------------------------------------- #
STUB_MARKER_PATTERNS: dict[str, list[str]] = {
    "Rust": [r"\btodo!\s*\(", r"\bunimplemented!\s*\(", r"\bunreachable!\s*\(\s*\"[^\"]*(?:todo|not.?impl)",
            r"//\s*TODO\b", r"//\s*FIXME\b"],
    "Python": [r"\bNotImplementedError\b", r"#\s*TODO\b", r"#\s*FIXME\b",
              r"^\s*raise\s+NotImplementedError", r"^\s*\.\.\.\s*$"],
    "JavaScript": [r"throw\s+new\s+Error\(\s*['\"](?:not implemented|TODO|unimplemented)",
                  r"//\s*TODO\b", r"//\s*FIXME\b", r"\bunimplemented\s*\(\s*\)"],
}
TARGET_LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "Rust": [".rs"], "Python": [".py"], "JavaScript": [".js", ".mjs", ".cjs"],
}


def scan_stub_markers(root: Path, target_language: str) -> Measurement:
    patterns = STUB_MARKER_PATTERNS.get(target_language)
    exts = TARGET_LANGUAGE_EXTENSIONS.get(target_language)
    if not patterns or not exts:
        return Measurement.unavailable(f"no stub-marker patterns defined for target language {target_language!r}")
    if not root.exists():
        return Measurement.missing(f"target tree {root} does not exist (nothing was produced)")
    compiled = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
    count = 0
    files_with_stubs: list[str] = []
    for path in M.iter_source_files(root, exts):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits = sum(len(c.findall(text)) for c in compiled)
        if hits:
            count += hits
            with contextlib.suppress(ValueError):
                files_with_stubs.append(str(path.relative_to(root)))
    return Measurement.ok({"stub_marker_count": count, "files_with_stubs": files_with_stubs})


# --------------------------------------------------------------------------- #
# Trajectory reconstruction
# --------------------------------------------------------------------------- #
@dataclass
class TrajectoryMetrics:
    """NC/TEC/SEC/LC/ALL -- harness-defined trajectory-shape metrics (the
    paper's RQ3 figure names these columns but does not define them in a way
    recoverable without the official artifact; see README "Integration
    assumptions"). ``precision`` distinguishes an exact, call-by-call record
    (``baseagent-condensed``/``baseagent-concat`` only) from a reconstruction
    from real-but-partial evidence (``full`` and the three stage-skip
    ablations ``noanalyzer``/``noplanning``/``novalidator``, whose per-agent
    JSONL logs get overwritten across repair iterations) from a total
    absence of evidence."""
    nc: int | None = None
    tec: int | None = None
    lc: int | None = None
    all_: int | None = None
    sec: dict[str, int] = field(default_factory=dict)
    precision: str = "unavailable"   # "exact" | "lower_bound" | "unavailable"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"nc": self.nc, "tec": self.tec, "lc": self.lc, "all": self.all_,
               "sec": dict(self.sec), "precision": self.precision, "reason": self.reason}


def trajectory_from_calls(calls: list[dict[str, Any]]) -> TrajectoryMetrics:
    """``baseagent-condensed``/``baseagent-concat`` only (the only variants
    still dispatched here -- ``full`` and the three stage-skip ablations now
    use :func:`trajectory_from_full_pipeline` instead, see this module's own
    docstring): ``recodeagent_calls.jsonl`` is an exact, complete,
    call-by-call record (run.py wrote every single call) -- no
    reconstruction needed.

    IMPORTANT (kept for backward compatibility with any pre-upgrade run
    directory still on disk -- the CURRENT run.py no longer writes
    ``kind="placeholder"`` calls for any variant, since noanalyzer/
    noplanning/novalidator are no longer driven by this code path at all):
    a ``kind="placeholder"`` call recorded that a stage was SKIPPED, not
    that it ran. Node count (``nc``) and the per-stage execution rollup
    (``sec``) must reflect stages that were actually EXECUTED; counting a
    placeholder's stage name as an executed node would silently inflate an
    ablation's trajectory shape with a node/edge that never really ran,
    defeating the entire point of measuring what the ablation skipped."""
    if not calls:
        return TrajectoryMetrics(precision="unavailable", reason="recodeagent_calls.jsonl is empty/missing")
    executed = [c for c in calls if c.get("kind") in ("invoke", "raw", "cli")]
    placeholder_stages = sorted({c.get("stage") for c in calls
                                if c.get("kind") == "placeholder" and c.get("stage")})
    stages_seen = {c.get("stage") for c in executed if c.get("stage")}
    sec: dict[str, int] = {}
    for c in executed:
        stage = c.get("stage") or "unknown"
        sec[stage] = sec.get(stage, 0) + 1
    tec = len(executed)
    reason = ("baseagent-condensed/baseagent-concat are single-shot, single-pass by design "
             "(no Burr graph at all -- see run.py); lc=0 reflects that, not an absence of "
             "looping in a real multi-milestone run")
    if placeholder_stages:
        reason += (f"; stage(s) {', '.join(placeholder_stages)} were deliberately skipped "
                  "(placeholder artifact injected) and are excluded from nc/tec/sec -- they "
                  "never executed")
    return TrajectoryMetrics(
        nc=len(stages_seen), tec=tec, lc=0, all_=tec, sec=sec, precision="exact", reason=reason,
    )


_HISTORY_LINE_RE = re.compile(r"^\s*(\S+)\s+iter=(\d+)\s+passed=(True|False|None)\s*$")
_FINISHED_LINE_RE = re.compile(r"finished at (\S+):\s*done=(True|False)\s*milestone_idx=(\d+)")


def parse_full_pipeline_stdout(text: str | None) -> dict[str, Any] | None:
    """Parses codeweaver.cli._cmd_run's own printed summary
    (``    {milestone}  iter={n}  passed={bool}`` history lines plus the
    ``finished at ...: done=... milestone_idx=...`` line) out of the real CLI
    subprocess's captured stdout (run.py's ``cli.stdout.log``). Returns None
    -- never a fabricated empty trajectory -- if neither marker is found."""
    if not text:
        return None
    history: list[dict[str, Any]] = []
    done: bool | None = None
    milestone_idx: int | None = None
    for line in text.splitlines():
        m = _HISTORY_LINE_RE.match(line)
        if m:
            passed = {"True": True, "False": False, "None": None}[m.group(3)]
            history.append({"milestone": m.group(1), "iter": int(m.group(2)), "passed": passed})
            continue
        m2 = _FINISHED_LINE_RE.search(line)
        if m2:
            done = m2.group(2) == "True"
            milestone_idx = int(m2.group(3))
    if not history and done is None:
        return None
    return {"history": history, "done": done, "milestone_idx": milestone_idx}


def trajectory_from_full_pipeline(
    cli_stdout: str | None, *, parity_ran: bool, skipped_stage: str | None = None,
) -> TrajectoryMetrics:
    """Reconstructs the real Burr trajectory from the CLI subprocess's own
    captured stdout. Used identically for the ``full`` variant AND the three
    stage-skip ablations (``noanalyzer``/``noplanning``/``novalidator``):
    since CodeWeaver core's own ``CODEWEAVER_SKIP_STAGES`` instrumentation
    (see ``run.py.STAGE_SKIP_VARIANTS``) makes all four run the identical
    real ``python -m codeweaver run`` CLI subprocess end to end, differing
    only in whether one stage (``analyze``/``plan``/``validate``) is
    deterministically replaced with a placeholder artifact, the same
    reconstruction applies to all of them. analyze/plan run exactly once
    each (a fixed Burr graph); translate/validate run once per ``history``
    entry; scope/parity's exact re-entry counts (on an incomplete-parity
    loop-back) are NOT independently recoverable from this evidence alone,
    so their counts are reported as a >=1 lower bound, not a fabricated
    exact value.

    ``skipped_stage`` (one of ``"analyze"``/``"plan"``/``"validate"``, or
    ``None`` for ``full``) identifies which single stage this run
    deliberately skipped. That stage's count is EXCLUDED from ``sec``/``nc``/
    ``tec`` entirely -- a deliberately skipped stage only ran a
    deterministic placeholder, never its real work, so it must never be
    counted as an executed node/edge. This mirrors
    :func:`trajectory_from_calls`'s existing exclusion of
    ``kind="placeholder"`` calls for exactly the same reason (see review
    finding: placeholders must never count as executed)."""
    parsed = parse_full_pipeline_stdout(cli_stdout)
    if parsed is None:
        return TrajectoryMetrics(
            precision="unavailable",
            reason="cli.stdout.log missing/unparseable -- codeweaver's own history/finished "
                   "summary lines were not found (older run predating this capture, or a crash "
                   "before any output was produced)",
        )
    history = parsed["history"]
    distinct_milestones = {h["milestone"] for h in history}
    lc = max(len(history) - len(distinct_milestones), 0)
    sec = {
        "analyze": 1, "plan": 1, "scope": 1,
        "translate": len(history), "validate": len(history),
        "parity": 1 if parity_ran else 0,
    }
    if skipped_stage:
        sec.pop(skipped_stage, None)
    tec = sum(sec.values())
    nc = sum(1 for v in sec.values() if v > 0)
    reason = ("translate/validate/lc are exact (derived from codeweaver's own printed history); "
             "scope/parity re-entry counts on an incomplete-parity loop-back are a >=1 lower "
             "bound (not independently observable from available artifacts)")
    if skipped_stage:
        reason += (
            f"; stage {skipped_stage!r} was deliberately skipped for this run via CodeWeaver "
            "core's CODEWEAVER_SKIP_STAGES (a placeholder artifact was written instead of real "
            "work) and is excluded from nc/tec/sec -- it never executed"
        )
    return TrajectoryMetrics(
        nc=nc, tec=tec, lc=lc, all_=tec, sec=sec, precision="lower_bound",
        reason=reason,
    )


def collect_jsonl_tool_rollup(logs_dir: Path) -> tuple[dict[str, Any], str]:
    """Rolls up tool/token/turn counts across every ``*.stdout.jsonl`` file in
    ``logs_dir``. Current transcripts have one unique filename per invocation,
    so their rollup is exact. A legacy ``<role>.stdout.jsonl`` filename marks
    the result as a lower bound because repeated calls overwrote that file."""
    if not logs_dir.exists():
        return {}, "unavailable"
    totals = {
        "tool_invocations": 0, "assistant_turns": 0, "premium_requests": 0,
        "nano_aiu": 0, "session_duration_ms": 0, "input_tokens": 0,
        "output_tokens": 0, "tool_counts": {},
    }
    any_input_tokens = False
    any_output_tokens = False
    any_nano_aiu = False
    any_file = False
    has_legacy_filename = False
    for log_file in sorted(logs_dir.glob("*.stdout.jsonl")):
        any_file = True
        if re.fullmatch(r"[^.]+\.stdout\.jsonl", log_file.name):
            has_legacy_filename = True
        events = C.parse_copilot_jsonl(log_file.read_text(encoding="utf-8", errors="replace"))
        summary = C.summarize_copilot_events(events)
        totals["tool_invocations"] += summary.tool_invocations
        totals["assistant_turns"] += summary.assistant_turns
        totals["premium_requests"] += summary.premium_requests or 0
        if summary.nano_aiu is not None:
            any_nano_aiu = True
            totals["nano_aiu"] += summary.nano_aiu
        totals["session_duration_ms"] += summary.session_duration_ms or 0
        for name, count in summary.tool_counts.items():
            totals["tool_counts"][name] = totals["tool_counts"].get(name, 0) + count
        if summary.tokens_status == Status.MEASURED:
            if summary.input_tokens is not None:
                any_input_tokens = True
                totals["input_tokens"] += summary.input_tokens
            if summary.output_tokens is not None:
                any_output_tokens = True
                totals["output_tokens"] += summary.output_tokens
    if not any_file:
        return {}, "unavailable"
    if not any_input_tokens:
        totals.pop("input_tokens", None)
    if not any_output_tokens:
        totals.pop("output_tokens", None)
    if not any_nano_aiu:
        totals.pop("nano_aiu", None)
    return totals, "lower_bound" if has_legacy_filename else "exact"


# --------------------------------------------------------------------------- #
# Build / test / coverage execution against the run's OWN produced target
# --------------------------------------------------------------------------- #
def evaluate_build(target_dir: Path, build_cmd: list[str], *, timeout: float | None,
                   runner: CommandRunner = default_command_runner) -> Measurement:
    if not build_cmd:
        return Measurement.na("no build_cmd configured for this dataset")
    if not target_dir.exists():
        return Measurement.missing(f"target tree {target_dir} does not exist (nothing was produced)")
    res = runner(build_cmd, cwd=target_dir, timeout=timeout)
    if res.timed_out:
        return Measurement(value=False, status=Status.ERROR, reason=f"build timed out after {timeout}s")
    if res.error:
        return Measurement(value=False, status=Status.ERROR, reason=res.error)
    return Measurement.ok(res.returncode == 0)


def evaluate_tests(target_dir: Path, test_cmd: list[str], tool: str, *, timeout: float | None,
                   dataset_spec: dict[str, Any] | None = None,
                   runner: CommandRunner = default_command_runner) -> dict[str, Measurement]:
    empty = {
        "total": Measurement.na("no unit_test_cmd configured for this dataset"),
        "passed": Measurement.na("no unit_test_cmd configured for this dataset"),
        "failed": Measurement.na("no unit_test_cmd configured for this dataset"),
    }
    if not test_cmd:
        return empty
    if not target_dir.exists():
        reason = f"target tree {target_dir} does not exist (nothing was produced)"
        return {k: Measurement.missing(reason) for k in ("total", "passed", "failed")}
    res = runner(test_cmd, cwd=target_dir, timeout=timeout)
    if res.timed_out:
        reason = f"unit test command timed out after {timeout}s"
        return {k: Measurement(value=None, status=Status.ERROR, reason=reason) for k in ("total", "passed", "failed")}
    if res.error:
        return {k: Measurement.error(res.error) for k in ("total", "passed", "failed")}
    parsed = parse_test_output(tool, res.stdout, res.stderr, dataset_spec=dataset_spec)
    if parsed is None:
        parser_id = (dataset_spec or {}).get("test_output_format") or TOOL_TEST_PARSER_ID.get(tool, "<none>")
        reason = (f"test command exited {res.returncode} but its output did not match a recognized "
                 f"'{parser_id}' summary format")
        detail = extract_compiler_error_snippet(res.stdout, res.stderr)
        if detail:
            # Almost always a compile/import failure (zero tests ever ran),
            # structurally distinct from a real, executed, FAILING assertion
            # -- naming the concrete error here (not just "unrecognized
            # format") is what lets a caller/reader tell the two apart, and
            # is threaded verbatim into validated_tests_not_executed's own
            # reason by compute_not_executed below.
            reason = f"{reason} -- likely a compile/import failure, not a behavioral test failure: {detail}"
        return {k: Measurement.unavailable(reason) for k in ("total", "passed", "failed")}
    return {
        "total": Measurement.ok(parsed["total"]),
        "passed": Measurement.ok(parsed["passed"]),
        "failed": Measurement.ok(parsed["failed"]),
    }


def compute_pass_rate(total: Measurement, passed: Measurement) -> Measurement:
    if not (total.is_measured and passed.is_measured):
        return Measurement.missing("total/passed test counts are not both measured")
    if total.value in (None, 0):
        return Measurement.na("zero developer tests executed; a pass rate is undefined")
    return Measurement.ok(passed.value / total.value)


# --------------------------------------------------------------------------- #
# expected (oracle-known, execution-independent) vs. executed (what the test
# command actually ran) -- see the paper's own Table 1/RQ3 methodology: TPR is
# passed / a FIXED, benchmark-known test-count denominator (e.g. 2,107 for
# validated developer tests), NOT passed / however many tests happened to
# execute this run (paper text: TE=1,970 tests executed, yet the reported
# ratio is 1,822/2,107 -- the 137-test gap is counted as "not executed" and
# contributes to the denominator with a ZERO numerator contribution, not an
# excluded/undefined row). "expected" must be knowable from a pristine,
# oracle-only source (a scaffold, a reference results tree, or a CSV) even
# when the CodeWeaver-translated target cannot compile/import at all -- see
# each tool's own ``*_validated_tests_expected``-style function below.
# --------------------------------------------------------------------------- #
def compute_not_executed(expected: Measurement, executed: Measurement) -> Measurement:
    """``max(0, expected - executed)``: how many of the oracle's KNOWN tests
    never got a chance to run at all -- e.g. because the CodeWeaver target
    failed to build/import (``executed`` then carries ``Status.ERROR``/
    ``Status.UNAVAILABLE``, never a fabricated measured ``0`` -- see
    ``evaluate_tests``), or because a test runner's own skip/ignore
    mechanism excluded some of the oracle's discovered tests even on an
    otherwise-successful build. Clamped at ``0`` (never negative): a static,
    best-effort ``expected`` counter can occasionally under-count relative
    to what a real test runner reports as executed (e.g. CRUST's whole-crate
    ``cargo test`` may also run the target's OWN embedded ``#[test]``s
    alongside the restored oracle contract's) -- when that happens, it is
    dishonest to claim a negative number of tests "never ran", so this
    reports 0 rather than a nonsensical negative count. Requires
    ``expected`` itself to be measured (the known, execution-independent
    denominator) -- propagates ``expected``'s own non-measured status/reason
    verbatim otherwise, never guessing. When ``executed`` is NOT measured (a
    build/import failure, timeout, or unparseable output), this returns a
    real ``Status.MEASURED`` value equal to the FULL ``expected`` count --
    literally none of them ran -- but the ``reason`` string always names
    ``executed``'s own status/reason verbatim, so a build failure is never
    silently relabeled as an ordinary "some tests were skipped" outcome."""
    if not expected.is_measured:
        reason = f"validated_tests_expected not measured: {expected.reason}" if expected.reason \
            else "validated_tests_expected not measured"
        return Measurement(value=None, status=expected.status, reason=reason)
    if executed.is_measured:
        return Measurement.ok(max(0, expected.value - executed.value))
    reason = (f"the executed-test count was not measured (status={executed.status!r}: "
             f"{executed.reason or 'no reason recorded'}); all {expected.value} expected test(s) are "
             "therefore counted as not executed, per the paper's own TPR methodology")
    return Measurement(value=expected.value, status=Status.MEASURED, reason=reason)


def compute_paper_pass_rate(expected: Measurement, passed: Measurement) -> Measurement:
    """The paper's own TPR formula: ``passed / expected`` -- a FIXED,
    oracle-known denominator -- NEVER ``passed / executed``
    (:func:`compute_pass_rate` above remains available separately for that
    executed-relative reading, e.g. as a diagnostic, but must never back
    Table 1's own headline ``tpr``). A non-measured ``passed`` (the
    underlying build/import failed, so it legitimately carries
    ``Status.ERROR``/``Status.UNAVAILABLE`` -- never a fabricated measured
    ``0``, see ``evaluate_tests``) is treated as a ZERO numerator
    contribution here, exactly like the paper's own methodology: a project
    whose target never even built contributes zero passing tests, it is not
    excluded from the rate as an undefined row -- but the ``reason`` string
    always names the underlying non-measured status/reason verbatim, so a
    build failure is never mistaken for a genuine, executed, all-failing
    run. Requires ``expected`` to be measured and non-zero; propagates
    ``expected``'s own non-measured status/reason verbatim otherwise."""
    if not expected.is_measured:
        reason = f"validated_tests_expected not measured: {expected.reason}" if expected.reason \
            else "validated_tests_expected not measured"
        return Measurement(value=None, status=expected.status, reason=reason)
    if expected.value in (None, 0):
        return Measurement.na("zero expected validated tests for this project; a pass rate is undefined")
    if passed.is_measured:
        return Measurement.ok(passed.value / expected.value)
    reason = (f"the passed-test count was not measured (status={passed.status!r}: "
             f"{passed.reason or 'no reason recorded'}); treated as 0 of {expected.value} expected test(s) "
             "per the paper's own TPR methodology (a build/import failure or a non-executed test contributes "
             "to the known denominator but never contributes a passing test)")
    return Measurement(value=0.0 / expected.value, status=Status.MEASURED, reason=reason)


def compute_project_pass_all(
    build: Measurement,
    expected: Measurement,
    passed: Measurement,
    failed: Measurement,
    not_executed: Measurement,
) -> Measurement:
    """Whether one translated project builds and passes its fixed oracle.

    The independent runner can also execute target-authored tests beyond the
    paper's static denominator (notably for CRUST), so ``passed`` may exceed
    ``expected``. Extra passing tests do not invalidate project success.
    """
    if not build.is_measured:
        return Measurement(value=None, status=build.status, reason=build.reason)
    if build.value is not True:
        return Measurement.ok(False)
    if not expected.is_measured:
        return Measurement(value=None, status=expected.status, reason=expected.reason)
    if expected.value in (None, 0):
        return Measurement.na("zero expected validated tests; project pass-all is undefined")
    if not passed.is_measured:
        return Measurement.ok(False)
    if not failed.is_measured or not not_executed.is_measured:
        return Measurement.unavailable(
            "validated failed/not-executed counts are not both measured"
        )
    return Measurement.ok(
        passed.value >= expected.value
        and failed.value == 0
        and not_executed.value == 0
    )


def evaluate_coverage(target_dir: Path, coverage_cmd: list[str], coverage_format: str | None, *,
                      timeout: float | None, runner: CommandRunner = default_command_runner) -> Measurement:
    if not coverage_cmd or not coverage_format:
        return Measurement.unavailable("no coverage_cmd/coverage_format configured for this dataset")
    if not target_dir.exists():
        return Measurement.missing(f"target tree {target_dir} does not exist (nothing was produced)")
    parser = COVERAGE_PARSERS.get(coverage_format)
    if parser is None:
        return Measurement.unavailable(f"unrecognized coverage_format {coverage_format!r}")
    res = runner(coverage_cmd, cwd=target_dir, timeout=timeout)
    if res.timed_out or res.error:
        return Measurement.error(res.error or f"coverage command timed out after {timeout}s")
    pct = parser(res.stdout)
    if pct is None:
        return Measurement.unavailable(f"coverage command output did not match '{coverage_format}' format")
    return Measurement.ok(pct)


# --------------------------------------------------------------------------- #
# Per-function / per-milestone validation (real for `full`, coarse otherwise)
# --------------------------------------------------------------------------- #
def target_function_counts(target_dir: Path, target_language: str) -> Measurement:
    exts = TARGET_LANGUAGE_EXTENSIONS.get(target_language)
    if not exts:
        return Measurement.unavailable(f"no function-counting pattern for target language {target_language!r}")
    if not target_dir.exists():
        return Measurement.missing(f"target tree {target_dir} does not exist (nothing was produced)")
    n = M.count_functions(target_dir, exts)
    return Measurement.ok(n) if n is not None else Measurement.missing("function counting failed")


def target_test_counts(target_dir: Path, target_language: str) -> Measurement:
    exts = TARGET_LANGUAGE_EXTENSIONS.get(target_language)
    if not exts:
        return Measurement.unavailable(f"no test-counting pattern for target language {target_language!r}")
    if not target_dir.exists():
        return Measurement.missing(f"target tree {target_dir} does not exist (nothing was produced)")
    n = M.count_tests(target_dir, exts)
    return Measurement.ok(n) if n is not None else Measurement.missing("test counting failed")


def milestone_validation(run_dir: Path, variant: str, cli_stdout: str | None,
                         final_call_ok: bool | None, *,
                         skipped_stage: str | None = None) -> dict[str, Any]:
    """Real per-milestone pass/fail for ``full`` AND the three stage-skip
    ablations (``noanalyzer``/``noplanning``/``novalidator``) -- all four
    reconstructed identically from codeweaver's own printed history, since
    CodeWeaver core's ``CODEWEAVER_SKIP_STAGES`` instrumentation makes all
    four run the same real Burr milestone/repair graph end to end (each
    milestone maps to a real, paper-meaningful function/behavior group). A
    coarse single-synthetic-milestone rollup is used only for
    ``baseagent-condensed``/``baseagent-concat``, which remain harness-
    driven single-shot prompts with no Burr graph at all.

    ``final_call_ok`` MUST come from a real (non-placeholder) validate/
    baseagent/full_pipeline call only -- the caller (collect_run) already
    filters out placeholder calls before computing it; it is only consulted
    for the baseagent-* branch below.

    ``skipped_stage`` (one of ``"analyze"``/``"plan"``/``"validate"``, or
    ``None``) identifies which stage this run deliberately skipped, for the
    ``real`` branch. CodeWeaver core's own ``validate()`` skip branch
    appends ``passed=None`` to EVERY milestone's history entry (never
    ``True``/``False``) because no genuine validator attestation exists for
    that milestone -- naively summing ``v is True`` would then report a
    MEASURED ``passed=0``, which misleadingly implies "every milestone was
    confirmed to fail" when the honest fact is "no verdict exists either
    way". So whenever every parsed history entry's ``passed`` is ``None``
    (checked directly from the parsed evidence itself, not merely inferred
    from ``skipped_stage == "validate"``, since ``passed=None`` is written
    by CodeWeaver core ONLY on that skip path), ``passed`` is reported
    ``missing``, never a fabricated ``0``; ``total`` remains genuinely
    measured (the milestones themselves did run). This is intentionally
    independent of collect.py's OWN objective build/unit-test measurement
    against the produced target tree (``evaluate_build``/``evaluate_tests``),
    which remains the harness's real, trustworthy pass/fail signal
    regardless of what any agent (or a skipped-stage placeholder) claims."""
    if variant == "full" or variant in R.STAGE_SKIP_VARIANTS:
        parsed = parse_full_pipeline_stdout(cli_stdout)
        if parsed is None:
            return {"total": Measurement.missing("no parsed history available"),
                   "passed": Measurement.missing("no parsed history available"),
                   "granularity": "real"}
        latest: dict[str, bool | None] = {}
        for h in parsed["history"]:
            latest[h["milestone"]] = h["passed"]
        total = len(latest)
        if total and all(v is None for v in latest.values()):
            stage_note = f" (validator was skipped via CODEWEAVER_SKIP_STAGES={skipped_stage!r})" \
                        if skipped_stage == "validate" else ""
            return {
                "total": Measurement.ok(total),
                "passed": Measurement.missing(
                    "every milestone's history entry has passed=None -- no genuine validator "
                    f"attestation exists for any milestone{stage_note}; this is NOT a confirmed "
                    "failure and must not be reported as passed=0"
                ),
                "granularity": "real",
            }
        passed = sum(1 for v in latest.values() if v is True)
        return {"total": Measurement.ok(total), "passed": Measurement.ok(passed), "granularity": "real"}
    # baseagent-condensed/baseagent-concat: one synthetic "FULL" milestone,
    # no Burr graph and therefore no repair loop.
    if final_call_ok is None:
        return {"total": Measurement.missing("no completed validate call recorded"),
               "passed": Measurement.missing("no completed validate call recorded"),
               "granularity": "single-synthetic"}
    return {"total": Measurement.ok(1), "passed": Measurement.ok(1 if final_call_ok else 0),
           "granularity": "single-synthetic"}


# --------------------------------------------------------------------------- #
# Per-run collection
# --------------------------------------------------------------------------- #
class CollectionSkip(Exception):
    """Raised internally to route a run to failures.csv with a reason,
    instead of writing a (partially fabricated) raw_runs row."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _target_dir(run_dir: Path) -> Path:
    return run_dir / "pipeline" / "target"


# --------------------------------------------------------------------------- #
# Independent (post-hoc) oracle evaluation -- see the "POST-HOC INDEPENDENT
# EVALUATOR" section of this module's docstring for the full per-tool
# rationale. Structurally separate from evaluate_build/evaluate_tests above:
# those measure CodeWeaver's own *translated* tests; everything below
# measures the paper's *independently validated* developer-test oracle
# (where one is actually available) and, where applicable, per-function
# validation. Nothing here is ever blended into dev_tests_*/translated_tests_*.
# --------------------------------------------------------------------------- #

# CRUST oracle-integrity/validated-test restore set: the subset of the
# pristine scaffold's own paths that constitute the paper's test CONTRACT
# (never the agent-fillable implementation itself) -- the Cargo manifest/
# lockfile, every file under src/bin/** (the paper's compiled test-harness
# binaries), and tests/** if the scaffold happens to ship one (a safety
# margin beyond the literal minimum, not an invented requirement).
CRUST_ORACLE_CONTRACT_TOP_LEVEL_FILES: tuple[str, ...] = ("Cargo.toml", "Cargo.lock")
CRUST_ORACLE_CONTRACT_DIRS: tuple[str, ...] = ("src/bin", "tests")

# A best-effort, STATIC (never-executed) count of Rust ``#[test]`` attributes
# -- used as the oracle-only ``validated_tests_expected`` denominator for
# both CRUST and Oxidizer (see ``crust_validated_tests_expected``/the
# Oxidizer branch of ``evaluate_independent_oracle``). Deliberately a plain
# regex over the pristine oracle source text, not a real Rust parser --
# consistent with this module's existing ``STUB_MARKER_PATTERNS`` precedent
# for "reasonably good, clearly best-effort" static source scanning. This
# count is knowable purely from files this harness already has unconditional
# read access to (a scaffold/reference tree that exists before, and
# independently of, any translation attempt), so it remains available even
# when the CodeWeaver-translated target cannot compile/import at all.
RUST_TEST_ATTRIBUTE_PATTERN = re.compile(r"#\s*\[\s*test\s*\]")

# CRUST's own workbook sheet (in the official ``results.xlsx``) holding the
# paper's AUTHORITATIVE, hand-curated per-project expected-test-count -- see
# ``read_crust_paper_expected_tests_xlsx``/README "CRUST's native-vs-paper-
# aligned expected-test-count". Matched case/whitespace-insensitively since
# the exact real capitalization in the workbook is not pinned by this code.
CRUST_PAPER_EXPECTED_SHEET_NAME = "sweagent crust - tool test"

# Default argv TEMPLATE (a single ``{bin_name}``-format placeholder) for
# executing a CRUST "binary assertion harness" -- a ``src/bin/*.rs`` file
# with zero ``#[test]`` attributes whose own process exit code IS the test
# verdict (see ``crust_binary_test_harnesses``/``crust_run_binary_test_harnesses``).
# Overridable per-dataset via ``dataset_spec["binary_test_cmd_template"]``
# (a list of argv strings, each independently ``.format(bin_name=...)``-ed)
# for scaffolds whose binary harness needs a different invocation style.
CRUST_BINARY_HARNESS_RUN_TEMPLATE: tuple[str, ...] = (
    "cargo", "run", "--quiet", "--manifest-path", "Cargo.toml", "--bin", "{bin_name}",
)


def count_rust_test_attributes(paths: list[Path]) -> int:
    """Sums ``RUST_TEST_ATTRIBUTE_PATTERN`` matches across every file in
    ``paths`` (read as UTF-8, best-effort). Unreadable files are skipped
    (not fatal) since this is a best-effort completeness count, not a
    build/execution step."""
    total = 0
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += len(RUST_TEST_ATTRIBUTE_PATTERN.findall(text))
    return total


def crust_binary_test_harnesses(scaffold_dir: Path) -> list[str]:
    """Detects CRUST "binary assertion harness" oracles: files directly
    under ``scaffold_dir/src/bin/*.rs`` that contain ZERO ``#[test]``
    attributes -- i.e. a plain ``fn main()`` whose own process exit code IS
    the test verdict (the real CRUST ``libfor`` project's
    ``src/bin/test.rs`` is exactly this shape), never discovered/run by
    plain ``cargo test`` at all (``cargo test`` only executes ``#[test]``-
    annotated functions, though it DOES compile every target -- including
    these binaries -- as a side effect, which is why
    :func:`crust_run_binary_test_harnesses` is safe to invoke immediately
    after a successful ``cargo test``). Returns the sorted list of Cargo
    ``--bin`` names (the file stem, e.g. ``"test"`` for ``test.rs``) --
    ``[]`` (never raises) if ``src/bin`` doesn't exist or every ``.rs``
    file there already has at least one ``#[test]`` (i.e. is a normal,
    regex-counted test file already reflected in
    ``crust_validated_tests_expected_native``, not a separate binary
    harness -- a file is one or the other, never double-counted)."""
    bin_dir = scaffold_dir / "src" / "bin"
    if not bin_dir.is_dir():
        return []
    names: list[str] = []
    for p in sorted(bin_dir.glob("*.rs")):
        if count_rust_test_attributes([p]) == 0:
            names.append(p.stem)
    return names


def _resolve_case_insensitive(parent: Path, name: str) -> Path | None:
    """Exact match first, then a case-insensitive scan of ``parent``'s
    immediate children -- mirrors the tolerance manifest.py already applies
    to the *other* (implementation.zip) artifact tree, kept local here since
    manifest.py itself is out of scope for this change."""
    exact = parent / name
    if exact.is_dir():
        return exact
    if not parent.is_dir():
        return None
    try:
        for child in parent.iterdir():
            if child.is_dir() and child.name.lower() == name.lower():
                return child
    except OSError:
        return None
    return None


def reference_project_dir(reference_results_root: Path | str | None, tool: str,
                          project: str | None) -> Path | None:
    """``<root>/recodeagent_translations/data/tool_projects/{tool}/{project}``
    -- the official RESULTS artifact's per-project reference tree (distinct
    from ``implementation.zip``'s own layout; see README "Post-hoc
    independent evaluator"). Returns None (never raises) when the root/tool/
    project isn't resolvable so callers can report ``Status.UNAVAILABLE``
    with an explicit reason instead of guessing."""
    if not reference_results_root or not project:
        return None
    base = Path(reference_results_root) / "recodeagent_translations" / "data" / "tool_projects"
    tool_dir = _resolve_case_insensitive(base, tool)
    if tool_dir is None:
        return None
    return _resolve_case_insensitive(tool_dir, project)


def crust_contract_relpaths(scaffold_dir: Path) -> list[str]:
    """POSIX-style paths, relative to ``scaffold_dir``, of every file this
    harness restores over a target copy for CRUST's independent-oracle
    evaluation (see ``CRUST_ORACLE_CONTRACT_TOP_LEVEL_FILES``/``_DIRS``)."""
    rel: list[str] = []
    for name in CRUST_ORACLE_CONTRACT_TOP_LEVEL_FILES:
        if (scaffold_dir / name).is_file():
            rel.append(name)
    for dirname in CRUST_ORACLE_CONTRACT_DIRS:
        d = scaffold_dir / dirname
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    rel.append(p.relative_to(scaffold_dir).as_posix())
    return rel


def crust_validated_tests_expected_native(scaffold_dir: Path) -> Measurement:
    """The NATIVE half of ``validated_tests_expected`` for CRUST: a static
    ``#[test]``-attribute count across the pristine scaffold's own ``.rs``
    contract paths (see ``crust_contract_relpaths``), PLUS one additional
    count for every detected "binary assertion harness"
    (``crust_binary_test_harnesses`` -- a ``src/bin/*.rs`` file with no
    ``#[test]`` attribute at all, e.g. the real CRUST ``libfor`` project's
    ``src/bin/test.rs``; never double-counted, since a binary-harness file
    by definition contributes zero to the regex count already).

    This is deliberately NOT the same thing as the paper's own authoritative
    per-project denominator (see ``read_crust_paper_expected_tests``/
    ``crust_paper_expected_lookup``/``crust_combine_expected``) -- naive
    static counting over the 100 real CRUST scaffolds is known to disagree
    with the paper's own bookkeeping in BOTH directions (e.g. the real
    ``2dpartint``/``holdem-odds`` projects' scaffolds have MORE regex-
    discoverable ``#[test]`` functions than the paper counts, while
    ``libfor``'s scaffold has FEWER because its lone oracle is a binary
    harness) -- so this function's result is exposed as
    ``validated_tests_expected_native`` and is only ever used as a
    (labeled) FALLBACK for ``validated_tests_expected`` when no paper-
    aligned figure is available (see ``crust_combine_expected``); it must
    never be silently presented as equal to the paper's own count.

    Available BEFORE and INDEPENDENTLY of any translation attempt (the
    scaffold is materialized once by prepare.py, never mutated by this
    harness), so it stays measured even when the CodeWeaver-translated
    implementation cannot compile at all (see ``compute_not_executed``/
    ``compute_paper_pass_rate``, which consume the COMBINED ``expected``
    value precisely so a build failure never silently zeroes out the TPR
    denominator)."""
    if not scaffold_dir.exists():
        return Measurement.na("no scaffold for this dataset (only CRUST ships one)")
    rel_paths = crust_contract_relpaths(scaffold_dir)
    rs_paths = [scaffold_dir / rel for rel in rel_paths if rel.endswith(".rs")]
    binary_harness_names = crust_binary_test_harnesses(scaffold_dir)
    if not rs_paths and not binary_harness_names:
        return Measurement.unavailable("scaffold has no .rs contract paths to count #[test] attributes in "
                                       "and no src/bin/*.rs binary assertion harnesses either")
    return Measurement.ok(count_rust_test_attributes(rs_paths) + len(binary_harness_names))


def crust_run_binary_test_harnesses(tmp_target: Path, binary_names: list[str], dataset_spec: dict[str, Any],
                                    *, timeout: float | None,
                                    runner: CommandRunner = default_command_runner) -> dict[str, Measurement]:
    """Executes every detected CRUST binary-assertion-harness oracle (see
    ``crust_binary_test_harnesses``) one process at a time against
    ``tmp_target`` -- each binary's own EXIT CODE is its test verdict (exit
    0 -> 1 passed, nonzero -> 1 failed), never anything ``cargo test``
    itself would discover. Returns the uniform ``{"total", "passed",
    "failed"}`` shape (the caller, ``crust_validated_tests_eval``, merges
    this with the plain ``cargo test`` result via ``_merge_test_counts`` and
    is responsible for the separate ``expected``/``not_executed`` keys).

    ``binary_names == []`` is a legitimately MEASURED "nothing to run" zero
    (not an error -- most CRUST projects have no binary-harness oracle at
    all). A spawn/timeout failure for one binary is recorded in ``reason``
    but does not stop the others from running (mirrors ``evaluate_tests``:
    the ``runner`` callable never raises, it reports failures via
    ``ExecResult.timed_out``/``.error``); if EVERY binary failed to even
    start (so no real pass/fail verdict was ever observed for any of them),
    the result is ``Status.ERROR`` rather than a fabricated 0/0."""
    if not binary_names:
        return {"total": Measurement.ok(0), "passed": Measurement.ok(0), "failed": Measurement.ok(0)}
    template = list(dataset_spec.get("binary_test_cmd_template", CRUST_BINARY_HARNESS_RUN_TEMPLATE))
    passed = 0
    failed = 0
    spawn_failures: list[str] = []
    for name in binary_names:
        argv = [part.format(bin_name=name) for part in template]
        result = runner(argv, cwd=tmp_target, timeout=timeout)
        if result.timed_out:
            spawn_failures.append(f"{name}: timed out after {timeout}s")
            continue
        if result.error:
            spawn_failures.append(f"{name}: {result.error}")
            continue
        if result.returncode == 0:
            passed += 1
        else:
            failed += 1
    total = passed + failed
    if not total and spawn_failures:
        error = Measurement.error(f"every binary assertion harness failed to run: {spawn_failures}")
        return {"total": error, "passed": error, "failed": error}
    reason = f"{len(spawn_failures)} binary harness(es) failed to run: {spawn_failures}" if spawn_failures else ""
    return {
        "total": Measurement(value=total, status=Status.MEASURED, reason=reason),
        "passed": Measurement(value=passed, status=Status.MEASURED, reason=reason),
        "failed": Measurement(value=failed, status=Status.MEASURED, reason=reason),
    }


def _merge_test_counts(a: dict[str, Measurement], b: dict[str, Measurement]) -> dict[str, Measurement]:
    """Sums two ``{"total", "passed", "failed"}`` Measurement dicts
    key-by-key (e.g. a plain ``cargo test`` result and a
    ``crust_run_binary_test_harnesses`` result) when BOTH sides are
    ``Status.MEASURED`` for that key. If either side is NOT measured for a
    given key, the merge for that key inherits THAT side's own non-measured
    Measurement verbatim (status, value, and reason) -- this deliberately
    never masks a real ``cargo test`` failure just because the binary-
    harness portion happened to be a clean "nothing to run" zero, and
    symmetrically never masks a binary-harness spawn error just because
    ``cargo test`` itself passed."""
    merged: dict[str, Measurement] = {}
    for key in ("total", "passed", "failed"):
        ma, mb = a[key], b[key]
        if ma.status == Status.MEASURED and mb.status == Status.MEASURED:
            merged[key] = Measurement.ok(ma.value + mb.value)
        elif ma.status != Status.MEASURED:
            merged[key] = ma
        else:
            merged[key] = mb
    return merged


def _normalize_lookup_key(text: str) -> str:
    """Case/whitespace-insensitive normalization for project-name lookups
    against externally supplied reference data (workbook/JSON/CSV project
    names may differ from this harness's own manifest ``project`` casing/
    spacing) -- mirrors the tolerance ``_resolve_case_insensitive`` already
    applies to directory names."""
    return " ".join(text.split()).strip().lower()


_CRUST_PROJECT_COLUMN_CANDIDATES = ("project", "project name", "tool test", "name", "crust project", "test")
_CRUST_COUNT_COLUMN_CANDIDATES = (
    "expected", "expected tests", "expected test count", "expected_tests", "# tests", "tests", "count", "n",
)


def _match_column(header: list[str], candidates: tuple[str, ...]) -> int | None:
    """Best-effort header match: normalized-equality against ``candidates``
    first, then a substring fallback. Returns ``None`` (never raises) if
    nothing matches so callers can fall back to positional (0/1) columns."""
    normalized = [_normalize_lookup_key(str(h)) for h in header]
    for cand in candidates:
        if cand in normalized:
            return normalized.index(cand)
    for i, h in enumerate(normalized):
        if any(cand in h for cand in candidates):
            return i
    return None


def read_crust_paper_expected_tests_xlsx(path: Path) -> tuple[dict[str, int] | None, str]:
    """Reads the paper's authoritative per-project CRUST expected-test-count
    from the official ``results.xlsx``'s own ``CRUST_PAPER_EXPECTED_SHEET_NAME``
    sheet. Uses the OPTIONAL ``openpyxl`` dependency (see
    ``common.optional_import``) -- returns ``(None, reason)`` (never raises)
    if it isn't installed, the sheet can't be found, or the columns can't be
    matched. The exact real column header names in the workbook are NOT
    pinned by this code (not verified against the real artifact in this
    sandbox); column matching is deliberately best-effort/tolerant (a small
    candidate-name list, falling back to positional columns 0/1 for a
    2-column sheet) rather than requiring an exact, possibly-wrong guess."""
    openpyxl = C.optional_import("openpyxl")
    if openpyxl is None:
        return None, "openpyxl is not installed in this environment (see requirements-analysis.txt)"
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - any malformed/unexpected workbook must not crash collection
        return None, f"failed to open {path}: {exc}"
    try:
        sheet_name = None
        target = _normalize_lookup_key(CRUST_PAPER_EXPECTED_SHEET_NAME)
        for name in wb.sheetnames:
            if _normalize_lookup_key(name) == target:
                sheet_name = name
                break
        if sheet_name is None:
            return None, f"no sheet named {CRUST_PAPER_EXPECTED_SHEET_NAME!r} found (have {wb.sheetnames})"
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
    except Exception as exc:  # noqa: BLE001 - any malformed/unexpected worksheet must not crash collection
        return None, f"failed to read sheet from {path}: {exc}"
    finally:
        wb.close()
    if not rows:
        return None, f"sheet {sheet_name!r} is empty"
    header = [str(c) if c is not None else "" for c in rows[0]]
    project_col = _match_column(header, _CRUST_PROJECT_COLUMN_CANDIDATES)
    count_col = _match_column(header, _CRUST_COUNT_COLUMN_CANDIDATES)
    if project_col is None and count_col is None and len(header) == 2:
        project_col, count_col = 0, 1
    if project_col is None or count_col is None:
        return None, f"could not identify project/count columns from header {header}"
    mapping: dict[str, int] = {}
    for row in rows[1:]:
        if project_col >= len(row) or count_col >= len(row):
            continue
        project, count = row[project_col], row[count_col]
        if project is None or count is None:
            continue
        try:
            mapping[_normalize_lookup_key(str(project))] = int(count)
        except (TypeError, ValueError):
            continue
    if not mapping:
        return None, f"sheet {sheet_name!r} yielded no usable project/count rows"
    return mapping, f"loaded from {path} sheet {sheet_name!r}"


def read_crust_paper_expected_tests_json(path: Path) -> tuple[dict[str, int] | None, str]:
    """Dependency-free reader for an explicit reference-inventory JSON file:
    a flat ``{"<project>": <int>, ...}`` object. Returns ``(None, reason)``
    (never raises) on any parse/shape problem."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"failed to read/parse {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"{path} does not contain a JSON object of {{project: count}}"
    mapping: dict[str, int] = {}
    for project, count in data.items():
        try:
            mapping[_normalize_lookup_key(str(project))] = int(count)
        except (TypeError, ValueError):
            continue
    if not mapping:
        return None, f"{path} yielded no usable project/count entries"
    return mapping, f"loaded from {path}"


def read_crust_paper_expected_tests_csv(path: Path) -> tuple[dict[str, int] | None, str]:
    """Dependency-free reader for an explicit reference-inventory CSV file
    (header e.g. ``project,expected_tests``, matched the same best-effort
    way as the xlsx reader, with the same positional 0/1 fallback for a
    2-column file). Returns ``(None, reason)`` (never raises) on any parse
    problem."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"failed to read {path}: {exc}"
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return None, f"{path} is empty"
    header = rows[0]
    project_col = _match_column(header, _CRUST_PROJECT_COLUMN_CANDIDATES)
    count_col = _match_column(header, _CRUST_COUNT_COLUMN_CANDIDATES)
    if project_col is None and count_col is None and len(header) == 2:
        project_col, count_col = 0, 1
    if project_col is None or count_col is None:
        return None, f"could not identify project/count columns from header {header}"
    mapping: dict[str, int] = {}
    for row in rows[1:]:
        if project_col >= len(row) or count_col >= len(row):
            continue
        project, count = row[project_col], row[count_col]
        if not project:
            continue
        try:
            mapping[_normalize_lookup_key(project)] = int(count)
        except (TypeError, ValueError):
            continue
    if not mapping:
        return None, f"{path} yielded no usable project/count rows"
    return mapping, f"loaded from {path}"


def read_crust_paper_expected_tests(path: Path | str) -> tuple[dict[str, int] | None, str]:
    """Dispatches to the format-specific reader by file extension
    (``.xlsx`` -> workbook reader, ``.json`` -> JSON reader, ``.csv``/
    anything else -> CSV reader) for ``--crust-paper-expected-tests``.
    Returns ``(None, reason)`` (never raises) for an unresolvable path or
    unrecognized extension."""
    p = Path(path)
    if not p.is_file():
        return None, f"{p} does not exist"
    suffix = p.suffix.lower()
    if suffix == ".xlsx":
        return read_crust_paper_expected_tests_xlsx(p)
    if suffix == ".json":
        return read_crust_paper_expected_tests_json(p)
    return read_crust_paper_expected_tests_csv(p)


def crust_paper_expected_lookup(mapping: dict[str, int] | None, project: str | None) -> Measurement:
    """Looks up ``project`` in the parsed paper-aligned mapping (see
    ``read_crust_paper_expected_tests``). ``Status.UNAVAILABLE`` (never a
    silent 0/fallback) if ``mapping`` is ``None``/empty (the
    ``--crust-paper-expected-tests`` flag was omitted or failed to parse) or
    ``project`` isn't a key in it -- this is a genuinely separate, optional
    input, distinct from the always-available native count."""
    if not mapping:
        return Measurement.unavailable("no --crust-paper-expected-tests mapping was supplied/parsed")
    if not project:
        return Measurement.unavailable("no project name available to look up in the paper-aligned mapping")
    key = _normalize_lookup_key(project)
    if key not in mapping:
        return Measurement.unavailable(f"project {project!r} not found in the paper-aligned mapping")
    return Measurement.ok(mapping[key])


def crust_combine_expected(native: Measurement, paper: Measurement) -> tuple[Measurement, Measurement]:
    """Combines the NATIVE (``crust_validated_tests_expected_native``) and
    PAPER-ALIGNED (``crust_paper_expected_lookup``) expected-test-counts
    into the single ``validated_tests_expected`` value CRUST actually
    reports, plus a ``validated_tests_expected_source`` label recording
    which one won. The paper-aligned figure is ALWAYS preferred when
    measured (it is the authoritative, hand-curated denominator the paper's
    own TPR is computed against -- naive static counting is known to
    disagree with it in both directions for real projects, see
    ``crust_validated_tests_expected_native``'s docstring); the native count
    is only ever used as a labeled FALLBACK when no paper-aligned figure is
    available. When NEITHER is measured, the combined ``expected`` inherits
    the NATIVE Measurement's own status/reason verbatim (with the paper
    lookup's reason appended parenthetically for a full audit trail) --
    deliberately so that already-covered "no scaffold"/"no contract paths"
    scenarios keep reporting the SAME status they always have, rather than
    regressing just because a new, independent, optional input also happens
    to be unavailable."""
    if paper.status == Status.MEASURED:
        return paper, Measurement.ok("paper")
    if native.status == Status.MEASURED:
        return native, Measurement.ok("native")
    combined_reason = native.reason
    if paper.reason:
        combined_reason = f"{combined_reason} (paper-aligned lookup also unavailable: {paper.reason})"
    inherited = Measurement(value=native.value, status=native.status, reason=combined_reason)
    return inherited, Measurement(value=None, status=native.status, reason=combined_reason)


def crust_oracle_integrity(scaffold_dir: Path, target_dir: Path) -> Measurement:
    """Hash-compares the pristine scaffold's own contract paths against the
    SAME relative paths inside the run's produced (mutable) target tree.
    ``"pristine"`` means the translating agent obeyed CodeWeaver's own
    working-copy-vs-immutable-input prompt instruction (a prompt-only
    convention -- see ``codeweaver/prompts.py`` -- not filesystem-enforced,
    which is exactly why this check exists); ``"mutated"`` means at least one
    contract path was altered (self-reported ``dev_tests_*``/
    ``translated_tests_*`` are then untrustworthy for this run, though the
    PRISTINE scaffold-overlay evaluation in
    :func:`crust_validated_tests_eval` remains valid regardless -- it never
    reads the target's own copy of these paths); ``"not_copied"`` means the
    target tree is missing a contract path entirely (e.g. a very early
    crash)."""
    if not scaffold_dir.exists():
        return Measurement.na("no scaffold for this dataset (only CRUST ships one)")
    rel_paths = crust_contract_relpaths(scaffold_dir)
    if not rel_paths:
        return Measurement.unavailable("scaffold has no recognizable Cargo contract paths to compare")
    if not target_dir.exists():
        return Measurement.missing("target tree does not exist (nothing was produced)")
    mutated: list[str] = []
    not_copied: list[str] = []
    for rel in rel_paths:
        dst = target_dir / rel
        if not dst.is_file():
            not_copied.append(rel)
            continue
        if C.file_sha256(scaffold_dir / rel) != C.file_sha256(dst):
            mutated.append(rel)
    if mutated:
        return Measurement(value="mutated", status=Status.MEASURED,
                           reason=f"{len(mutated)} contract path(s) differ from the pristine scaffold: "
                                  f"{mutated[:5]}")
    if not_copied:
        return Measurement(value="not_copied", status=Status.MEASURED,
                           reason=f"{len(not_copied)} contract path(s) missing from the target tree: "
                                  f"{not_copied[:5]}")
    return Measurement.ok("pristine")


def _finalize_validated_tests(
    raw: dict[str, Measurement], expected: Measurement, *,
    expected_native: Measurement | None = None,
    expected_paper: Measurement | None = None,
    expected_source: Measurement | None = None,
) -> dict[str, Measurement]:
    """Assembles the final, uniform EIGHT-key ``validated`` field family
    (``expected``, ``executed``, ``passed``, ``failed``, ``not_executed``,
    ``expected_native``, ``expected_paper``, ``expected_source``) used by
    every tool's independent-oracle adapter below, from an
    ``evaluate_tests``-shaped ``{"total", "passed", "failed"}`` result
    (renaming ``"total"`` -- whatever the test command actually ran -- to
    the paper's own "TE"/``executed`` vocabulary) plus the separately
    computed, oracle-only ``expected`` denominator (see e.g.
    ``crust_validated_tests_expected_native``/``crust_combine_expected``).
    ``not_executed`` honestly handles a build/import failure -- see
    ``compute_not_executed``.

    ``expected_native``/``expected_paper``/``expected_source`` are CRUST-
    specific (see ``crust_combine_expected``): every OTHER tool's call site
    below leaves them at their default, a single shared
    ``Status.NOT_APPLICABLE`` placeholder Measurement, since the native-vs-
    paper-aligned split is meaningless for a tool with only one oracle-
    derived denominator in the first place."""
    executed = raw["total"]
    default_na = Measurement.na(
        "the native-vs-paper-aligned expected-test-count distinction is CRUST-specific (see "
        "crust_combine_expected) -- this tool's validated_tests_expected already reflects its own single "
        "oracle-derived denominator"
    )
    return {
        "expected": expected,
        "executed": executed,
        "passed": raw["passed"],
        "failed": raw["failed"],
        "not_executed": compute_not_executed(expected, executed),
        "expected_native": expected_native if expected_native is not None else default_na,
        "expected_paper": expected_paper if expected_paper is not None else default_na,
        "expected_source": expected_source if expected_source is not None else default_na,
    }


def crust_validated_tests_eval(run_dir: Path, dataset_spec: dict[str, Any], *, timeout: float | None,
                               runner: CommandRunner = default_command_runner,
                               project: str | None = None,
                               crust_paper_expected_tests: dict[str, int] | None = None) -> dict[str, Measurement]:
    """CRUST's independently validated developer tests: restore the PRISTINE
    scaffold's own Cargo contract over a TEMPORARY copy of the run's produced
    target, then run the dataset's own ``unit_test_cmd`` there, PLUS any
    detected "binary assertion harness" oracles (``crust_binary_test_harnesses``
    / ``crust_run_binary_test_harnesses`` -- e.g. the real CRUST ``libfor``
    project's ``src/bin/test.rs``, which plain ``cargo test`` never
    discovers/runs at all, silently reporting 0 for that project unless
    this merge is performed). Deliberately never touches ``run_dir`` itself
    (the copy is made in a fresh ``tempfile.TemporaryDirectory()``) and
    never trusts whatever tests/contract the agent's own ``pipeline/target``
    currently contains -- unlike ``evaluate_tests`` above, which does
    exactly that for the (structurally separate) ``dev_tests_*``/
    ``translated_tests_*`` fields.

    Returns the uniform ``expected``/``executed``/``passed``/``failed``/
    ``not_executed``/``expected_native``/``expected_paper``/
    ``expected_source`` shape (see ``_finalize_validated_tests``).
    ``expected`` is the COMBINED denominator (see ``crust_combine_expected``):
    the paper-aligned, hand-curated count (``crust_paper_expected_lookup``
    against ``crust_paper_expected_tests``, e.g. parsed from the official
    ``results.xlsx``'s ``"sweagent crust - tool test"`` sheet via
    ``--crust-paper-expected-tests``) when available, else the NATIVE static
    ``#[test]``-attribute-plus-binary-harness count
    (``crust_validated_tests_expected_native``) -- the two are known to
    disagree in BOTH directions for real projects (e.g. the real
    ``2dpartint``/``holdem-odds`` projects' native counts OVERcount by 2
    each relative to the paper, while ``libfor``'s native count would
    UNDERcount by 1 without the binary-harness merge below) and are NEVER
    silently presented as equal; ``expected_source`` records which one won.
    All of ``expected``/``expected_native``/``expected_paper``/
    ``expected_source`` are computed from the scaffold (plus the optional,
    already-parsed ``crust_paper_expected_tests`` mapping) ALONE and stay
    measured even when the rest of this function reports a build failure
    below -- see ``compute_not_executed``/``compute_paper_pass_rate``."""
    scaffold_dir = run_dir / "scaffold"
    target_dir = _target_dir(run_dir)
    native = crust_validated_tests_expected_native(scaffold_dir)
    paper = crust_paper_expected_lookup(crust_paper_expected_tests, project)
    expected, source = crust_combine_expected(native, paper)
    expected_kwargs = {"expected_native": native, "expected_paper": paper, "expected_source": source}
    if not scaffold_dir.exists():
        na = Measurement.na("no scaffold for this dataset (only CRUST ships one)")
        return _finalize_validated_tests({"total": na, "passed": na, "failed": na}, expected, **expected_kwargs)
    if not target_dir.exists():
        missing = Measurement.missing("target tree does not exist (nothing was produced)")
        return _finalize_validated_tests({"total": missing, "passed": missing, "failed": missing}, expected,
                                         **expected_kwargs)
    rel_paths = crust_contract_relpaths(scaffold_dir)
    binary_harness_names = crust_binary_test_harnesses(scaffold_dir)
    if not rel_paths:
        unavailable = Measurement.unavailable("scaffold has no recognizable Cargo contract paths to restore")
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         expected, **expected_kwargs)
    with tempfile.TemporaryDirectory(prefix="recodeagent_crust_oracle_") as tmp:
        tmp_target = Path(tmp) / "target"
        copy_evaluation_tree(target_dir, tmp_target)
        for rel in rel_paths:
            dst = tmp_target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scaffold_dir / rel, dst)
        raw = evaluate_tests(tmp_target, list(dataset_spec.get("unit_test_cmd", [])), "crust",
                             timeout=timeout, dataset_spec=dataset_spec, runner=runner)
        # ``cargo test`` builds every target (including src/bin/*.rs) before
        # running any #[test], so if it produced a real (measured) result
        # the binaries have already compiled -- safe to attempt running
        # them now. If cargo test itself wasn't measured (e.g. it errored
        # before producing a parseable summary), skip this step entirely:
        # there is no "clean" build to run a binary harness against, and
        # attempting one would just duplicate the same underlying failure.
        if binary_harness_names and raw["total"].status == Status.MEASURED:
            binary_raw = crust_run_binary_test_harnesses(tmp_target, binary_harness_names, dataset_spec,
                                                         timeout=timeout, runner=runner)
            raw = _merge_test_counts(raw, binary_raw)
    return _finalize_validated_tests(raw, expected, **expected_kwargs)


# --------------------------------------------------------------------------- #
# Oracle identifier-rewrite (Oxidizer only) -- an OPTIONAL, best-effort layer
# that prevents a real, verified false-negative pattern from being
# misreported as a BEHAVIORAL test failure: CodeWeaver's own Analyzer/
# Planner may (correctly, per idiomatic Rust convention) expose a
# snake_case symbol -- e.g. ``new_luhn`` -- for a source-language symbol the
# official reference oracle test still calls by its ORIGINAL spelling --
# e.g. Go's ``NewLuhn`` (the concrete, verified ``oxidizer__checkdigit``
# case this section exists for). Compiling the PRISTINE reference oracle
# verbatim against such a target then fails with an ordinary "cannot find
# function/unresolved name" compiler error -- a real compile failure, but
# one caused SOLELY by an idiomatic renaming choice, not a behavioral bug.
#
# Two independent, layered mitigations (neither depends on the other):
#   1. IDEAL: if the real CodeWeaver Planner's own structured
#      ``plan.json["name_mapping"]`` (a one-to-one source-symbol ->
#      target-symbol map; see ``codeweaver/prompts.py``'s ``PLAN`` template
#      and ``codeweaver/actions.py``'s ``plan()`` action for the
#      authoritative field name/shape) is available for this run,
#      ``rewrite_identifiers_with_name_mapping`` rewrites ONLY genuine
#      identifier-shaped code tokens (never string/char literals or
#      comments -- see ``rust_source_code_mask``) in a TEMPORARY COPY of the
#      oracle file text, before it is ever written into the temp evaluation
#      tree, so the pristine oracle's own test LOGIC/assertions still run,
#      unmodified, against CodeWeaver's actual (idiomatically-renamed)
#      public API. The oracle file on disk under ``--reference-results-
#      root`` is never touched -- only the in-memory text staged into the
#      ``tempfile.TemporaryDirectory()`` copy is ever rewritten.
#   2. FALLBACK (always active, whether or not #1 applies/succeeds): when a
#      test command's output cannot be parsed as a recognized test-summary
#      format at all -- overwhelmingly a compile/import failure, since a
#      real, executed, FAILING assertion always DOES produce a parseable
#      summary -- ``evaluate_tests`` (see ``extract_compiler_error_snippet``)
#      surfaces the actual compiler-error text in its own
#      ``Status.UNAVAILABLE`` reason, and ``compute_not_executed`` (already,
#      independently correct -- see its own docstring) reports the FULL
#      expected count as ``not_executed`` while ``failed`` itself STAYS
#      ``Status.UNAVAILABLE`` -- NEVER a fabricated ``Status.MEASURED``
#      value equal to ``expected``. A suite that never compiled is therefore
#      always distinguishable, in the data itself, from one that compiled
#      and genuinely failed every assertion.
# --------------------------------------------------------------------------- #
def read_name_mapping(run_dir: Path) -> dict[str, str]:
    """Best-effort read of the REAL CodeWeaver Planner's own structured
    name-mapping artifact -- ``<run_dir>/pipeline/plan.json``'s top-level
    ``"name_mapping"`` key (confirmed authoritative by reading
    ``codeweaver/prompts.py``'s ``PLAN`` template -- Planner step 2, "a
    one-to-one map from source symbols to {target_language} counterparts" --
    and ``codeweaver/actions.py``'s real ``plan()`` action, whose own
    skip-stage placeholder JSON uses this exact key). Also accepts a
    ``"name_map"`` top-level key as a defensive fallback ALIAS (an older,
    harness-internal placeholder helper historically used this alternate
    spelling; trying ``"name_mapping"`` first costs nothing and never
    silently prefers the non-authoritative name when both happen to be
    present). Returns ``{}`` (never raises) when ``run_dir`` has no
    ``pipeline/plan.json``, the file is not valid JSON, is not a JSON
    object, or has neither key as a JSON object -- callers MUST treat an
    empty mapping as "no rewrite available", never as an error condition.
    Planner outputs commonly group mappings under ``types``/``functions``/
    ``methods``/``errors``/``test_functions``. Those dictionaries are
    recursively flattened; only string:string leaves survive."""
    data = read_json_or(Path(run_dir) / "pipeline" / "plan.json", None)
    if not isinstance(data, dict):
        return {}
    raw = data.get("name_mapping")
    if not isinstance(raw, dict):
        raw = data.get("name_map")
    if not isinstance(raw, dict):
        return {}
    flattened: dict[str, str] = {}

    def visit(value: Any) -> None:
        if not isinstance(value, dict):
            return
        for key, target in value.items():
            if isinstance(key, str) and isinstance(target, str):
                previous = flattened.get(key)
                if previous is None or previous == target:
                    flattened[key] = target
            elif isinstance(target, dict):
                visit(target)

    visit(raw)
    return flattened


def _normalize_identifier_for_matching(name: str) -> str:
    """Case/underscore-insensitive normalization used ONLY to offer a
    SECONDARY fallback match in ``build_identifier_rewrite_index`` (e.g.
    matching ``NewLuhn`` against a recorded ``new_luhn`` key or vice versa)
    -- never invents a spelling; the REWRITTEN text always uses the
    mapping's own recorded target string verbatim, never a
    normalized/reconstructed one."""
    return name.replace("_", "").lower()


def build_identifier_rewrite_index(name_mapping: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Expands a raw ``{source_symbol: target_symbol}`` mapping (as read by
    ``read_name_mapping``) into ``(exact, normalized)`` lookups for
    ``rewrite_identifiers_with_name_mapping``:

    - ``exact`` keeps every syntactically valid Rust identifier source key
      whose target is a syntactically valid Rust identifier/path. Free-form
      Planner descriptions are rejected rather than inserted into source.
    - ``normalized`` offers a SECONDARY, case/underscore-insensitive index
      (see ``_normalize_identifier_for_matching``) for source keys whose
      normalized form is not ambiguous -- i.e. not shared, with a DIFFERENT
      recorded target, by some other exact source key. An ambiguous
      normalized collision is dropped from ``normalized`` entirely rather
      than guessed, per the "exact/normalized, never invented" rule.

    No-op (identity) entries (``k == v``), non-string key/value pairs, and
    non-Rust spellings are skipped up front, since ``plan.json`` is an
    LLM-influenced artifact rather than a validated schema."""
    exact: dict[str, str] = {}
    for k, v in name_mapping.items():
        if (
            isinstance(k, str)
            and isinstance(v, str)
            and _IDENTIFIER_TOKEN_RE.fullmatch(k)
            and _RUST_IDENTIFIER_PATH_RE.fullmatch(v)
            and k != v
        ):
            exact[k] = v
    normalized: dict[str, str] = {}
    ambiguous: set[str] = set()
    for k, v in exact.items():
        nk = _normalize_identifier_for_matching(k)
        if not nk or nk == k:
            continue
        if nk in ambiguous:
            continue
        if nk in normalized and normalized[nk] != v:
            ambiguous.add(nk)
            del normalized[nk]
            continue
        normalized[nk] = v
    return exact, normalized


_HEX_DIGITS = "0123456789abcdefABCDEF"
_RUST_CHAR_ESCAPES = {"n", "t", "r", "\\", "'", '"', "0"}
_RUST_RAW_STRING_OPEN_RE = re.compile(r'(?P<byte>b)?r(?P<hashes>#*)"')
_IDENTIFIER_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_RUST_IDENTIFIER_PATH_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*"
)


def _match_rust_char_literal(text: str, i: int) -> int | None:
    """``text[i]`` must be ``'``. Returns the index just past a syntactically
    BOUNDED Rust char literal's closing ``'`` (covers a plain char ``'x'``,
    a simple escape ``'\\n'``/``'\\''``/``'\\\\'``/``'\\"'``/``'\\0'``, a
    byte escape ``'\\xNN'``, or a unicode escape ``'\\u{...}'`` with 1-6 hex
    digits), else ``None``. ``None`` almost always means ``text[i:]`` is
    actually a Rust LIFETIME (``'a``, ``'static``, ``'de``, ...) rather than
    a char literal -- a lifetime never has a bounded 1-char-or-escape body
    immediately followed by a closing ``'``, so this check safely tells the
    two apart without understanding Rust grammar beyond this one rule."""
    n = len(text)
    j = i + 1
    if j >= n:
        return None
    if text[j] == "\\":
        k = j + 1
        if k >= n:
            return None
        esc = text[k]
        if esc in _RUST_CHAR_ESCAPES:
            k += 1
        elif esc == "x" and k + 2 < n and text[k + 1] in _HEX_DIGITS and text[k + 2] in _HEX_DIGITS:
            k += 3
        elif esc == "u" and k + 1 < n and text[k + 1] == "{":
            close = text.find("}", k + 2)
            if close == -1 or close - (k + 2) > 6:
                return None
            k = close + 1
        else:
            return None
        return k + 1 if k < n and text[k] == "'" else None
    if text[j] == "'":
        return None  # an empty '' is not a valid Rust char literal.
    k = j + 1
    return k + 1 if k < n and text[k] == "'" else None


def rust_source_code_mask(text: str) -> list[bool]:
    """Per-character boolean mask over Rust source ``text``: ``True`` marks
    ordinary CODE (an identifier found here is a genuine rewrite candidate
    for ``rewrite_identifiers_with_name_mapping``); ``False`` marks a
    position inside a string/byte-string/raw-string literal, a char
    literal, a lifetime (``'a``, ``'static``, ``'de``, ...), or a
    line/block comment. An identifier-SHAPED substring in any of these
    positions must never be rewritten: doing so could silently corrupt a
    literal string a test asserts on (e.g.
    ``assert_eq!(names(), vec!["NewLuhn"])``), a comment, or -- if a
    name_mapping's SOURCE key happens to equal a lifetime name such as a
    common single-letter symbol -- every ``'a`` in the file. Deliberately
    hand-rolled (no new ``tree-sitter-rust`` dependency) -- this harness
    only ever needs a reliable "is this position safe to touch" boolean,
    not a full parse tree. Single forward pass, ``O(len(text))``; never
    raises on malformed/truncated input (an unterminated string/comment
    simply masks out the remainder of the file, which is always the SAFE
    direction -- under-rewriting, never over-rewriting)."""
    n = len(text)
    mask = [True] * n
    i = 0
    block_depth = 0
    while i < n:
        if block_depth > 0:
            if text.startswith("/*", i):
                block_depth += 1
                mask[i] = mask[i + 1] = False
                i += 2
                continue
            if text.startswith("*/", i):
                block_depth -= 1
                mask[i] = mask[i + 1] = False
                i += 2
                continue
            mask[i] = False
            i += 1
            continue
        if text.startswith("//", i):
            j = i
            while j < n and text[j] != "\n":
                mask[j] = False
                j += 1
            i = j
            continue
        if text.startswith("/*", i):
            block_depth = 1
            mask[i] = mask[i + 1] = False
            i += 2
            continue
        m = _RUST_RAW_STRING_OPEN_RE.match(text, i)
        if m:
            closer = '"' + m.group("hashes")
            start = m.end()
            end = text.find(closer, start)
            end_full = n if end == -1 else end + len(closer)
            for k in range(i, end_full):
                mask[k] = False
            i = end_full
            continue
        ch = text[i]
        if ch == '"' or (ch == "b" and i + 1 < n and text[i + 1] == '"'):
            quote_pos = i if ch == '"' else i + 1
            for k in range(i, quote_pos + 1):
                mask[k] = False
            j = quote_pos + 1
            while j < n:
                mask[j] = False
                if text[j] == "\\" and j + 1 < n:
                    mask[j + 1] = False
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            i = j
            continue
        if ch == "'":
            literal_end = _match_rust_char_literal(text, i)
            if literal_end is not None:
                for k in range(i, literal_end):
                    mask[k] = False
                i = literal_end
                continue
            # Not a bounded char literal -> a Rust LIFETIME (``'a``,
            # ``'static``, ``'de``, ...) or a stray quote. A lifetime's name
            # occupies ITS OWN namespace (never a name_mapping rewrite
            # target -- the source language has no analogous concept), so
            # exclude the apostrophe AND its following identifier-shaped
            # run from ever being treated as a rewrite candidate. Without
            # this, a name_mapping entry whose SOURCE key happened to equal
            # a common lifetime name (e.g. a single-letter symbol "a") would
            # otherwise silently corrupt every ``'a`` in the file -- caught
            # by this module's own regression test.
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            for k in range(i, j):
                mask[k] = False
            i = j
            continue
        i += 1
    return mask


def rewrite_identifiers_with_name_mapping(
    text: str,
    name_mapping: Mapping[str, str],
    *,
    protected_identifiers: set[str] | None = None,
) -> tuple[str, list[str]]:
    """Rewrites every whole-token occurrence of a ``name_mapping`` SOURCE
    identifier found in a genuine CODE position of Rust ``text`` (per
    ``rust_source_code_mask``) to its recorded TARGET spelling -- an exact
    source-string match always wins; a case/underscore-insensitive fallback
    (``build_identifier_rewrite_index``'s ``normalized`` index) additionally
    catches the concrete verified case (the official oracle's ``NewLuhn``
    vs. CodeWeaver's own idiomatic ``new_luhn``) without ever inventing a
    spelling -- the substituted text is always the mapping's own recorded
    target, verbatim. Only touches tokens found OUTSIDE any string/char
    literal or comment span, so a test asserting on a literal name string
    is never silently corrupted.

    Returns ``(text, [])`` UNCHANGED -- a true no-op, always safe to call --
    when ``name_mapping`` is empty or no eligible token is found in a code
    position. The second return value is the SORTED list of distinct
    source identifiers actually substituted, for transparent reporting
    (see ``_evaluate_with_replaced_subdir``'s reason annotation).

    Rust ``use`` statements are handled separately by
    ``rewrite_rust_use_paths`` and are therefore excluded here. Identifiers
    supplied through ``protected_identifiers`` are local oracle-fixture
    module/symbol names, not translated target API names, and are likewise
    never rewritten."""
    exact, normalized = build_identifier_rewrite_index(name_mapping)
    if not exact and not normalized:
        return text, []
    mask = rust_source_code_mask(text)
    for match in _RUST_USE_LINE_RE.finditer(text):
        for index in range(match.start(), match.end()):
            mask[index] = False
    protected = protected_identifiers or set()
    applied: set[str] = set()

    def _sub(m: re.Match[str]) -> str:
        tok = m.group(0)
        if not mask[m.start()] or tok in protected:
            return tok
        target = exact.get(tok)
        if target is None and tok[:1].isupper():
            target = normalized.get(_normalize_identifier_for_matching(tok))
        if target is None or target == tok:
            return tok
        applied.add(tok)
        return target

    new_text = _IDENTIFIER_TOKEN_RE.sub(_sub, text)
    return (new_text, sorted(applied)) if applied else (text, [])


def rewrite_rust_field_accesses(
    text: str,
    field_mapping: Mapping[str, str],
    *,
    protected_identifiers: set[str] | None = None,
) -> tuple[str, list[str]]:
    """Rewrite only identifiers in ``value.Field`` access positions."""
    exact, _ = build_identifier_rewrite_index(field_mapping)
    if not exact:
        return text, []
    mask = rust_source_code_mask(text)
    protected = protected_identifiers or set()
    applied: set[str] = set()
    pattern = re.compile(r"(?P<prefix>\.\s*)(?P<field>[A-Za-z_][A-Za-z0-9_]*)")

    def replacement(match: re.Match[str]) -> str:
        field = match.group("field")
        if (
            not mask[match.start("field")]
            or field in protected
            or re.match(r"\s*\(", text[match.end():])
            or (target := exact.get(field)) is None
        ):
            return match.group(0)
        applied.add(field)
        return match.group("prefix") + target

    rewritten = pattern.sub(replacement, text)
    return (rewritten, sorted(applied)) if applied else (text, [])


_RUST_OUT_OF_LINE_MODULE_RE = re.compile(
    r"\bmod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;"
)


def _rust_out_of_line_modules(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    mask = rust_source_code_mask(text)
    return {
        match.group(1)
        for match in _RUST_OUT_OF_LINE_MODULE_RE.finditer(text)
        if mask[match.start()]
    }


def oxidizer_reference_support_files(ref_project_dir: Path | None) -> list[Path]:
    """Return local Rust modules imported by integration-test drivers."""
    if ref_project_dir is None:
        return []
    tests_dir = ref_project_dir / "rust" / "tests"
    if not tests_dir.is_dir():
        return []
    candidates = sorted(tests_dir.glob("*.rs"))
    module_names: set[str] = set()
    for path in candidates:
        module_names.update(_rust_out_of_line_modules(path))
    return [path for path in candidates if path.stem in module_names]


def oxidizer_reference_support_identifiers(
    support_files: list[Path],
) -> set[str]:
    """Return fixture-local names that must not be treated as target APIs."""
    protected = {path.stem for path in support_files}
    for path in support_files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        mask = rust_source_code_mask(text)
        protected.update(
            match.group(1)
            for match in _RUST_DECLARED_IDENTIFIER_RE.finditer(text)
            if mask[match.start()]
        )
    return protected


def oxidizer_reference_test_files(ref_project_dir: Path | None) -> tuple[list[Path], list[Path]]:
    """Classifies ``<ref_project_dir>/rust/tests/*.rs`` into (developer-test
    ORACLE files, function-validation HARNESS files). ``*_test.rs`` (case-
    insensitive, excluding any name containing "generated") is the paper's
    own developer-test suite; other plain ``.rs`` files (same "generated"
    exclusion) are per-function validation harnesses; anything with
    "generated" in its name is excluded from BOTH -- a build artifact, not a
    hand-written oracle. Out-of-line fixture modules imported with
    ``mod fixture;`` are support files, not standalone harnesses, and are
    excluded from both lists. Returns ``([], [])`` (never raises) when
    ``ref_project_dir`` is None or has no ``rust/tests`` directory."""
    if ref_project_dir is None:
        return [], []
    tests_dir = ref_project_dir / "rust" / "tests"
    if not tests_dir.is_dir():
        return [], []
    support = set(oxidizer_reference_support_files(ref_project_dir))
    oracle: list[Path] = []
    harness: list[Path] = []
    for p in sorted(tests_dir.glob("*.rs")):
        if "generated" in p.name.lower() or p in support:
            continue
        if p.name.lower().endswith("_test.rs"):
            oracle.append(p)
        else:
            harness.append(p)
    return oracle, harness


def oxidizer_generated_test_files(ref_project_dir: Path | None) -> list[Path]:
    """Return the official generated Rust integration-test files."""
    if ref_project_dir is None:
        return []
    tests_dir = ref_project_dir / "rust" / "tests"
    if not tests_dir.is_dir():
        return []
    return sorted(
        path for path in tests_dir.glob("*.rs")
        if "generated" in path.name.lower()
    )


def oxidizer_reference_test_inventory(
    ref_project_dir: Path | None,
) -> dict[str, set[str]]:
    """Return the paper's curated Rust test names grouped by oracle filename."""
    if ref_project_dir is None:
        return {}
    path = ref_project_dir / "test_name_mapping.csv"
    if not path.is_file():
        return {}
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return {}
    inventory: dict[str, set[str]] = {}
    for row in rows:
        test_path = row.get("rust test path")
        test_name = row.get("rust test name")
        if not test_path or not test_name:
            continue
        inventory.setdefault(Path(test_path).name, set()).add(test_name)
    return inventory


_RUST_TEST_FUNCTION_RE = re.compile(
    r"(?m)^[ \t]*#\s*\[\s*test\s*\][^\n]*\n"
    r"(?:[ \t]*#\[[^\n]+\]\s*\n)*"
    r"[ \t]*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)[^{;]*"
)


def retain_named_rust_tests(text: str, allowed_names: set[str]) -> str:
    """Remove non-inventory ``#[test]`` functions while preserving helpers."""
    mask = rust_source_code_mask(text)
    removals: list[tuple[int, int]] = []
    for match in _RUST_TEST_FUNCTION_RE.finditer(text):
        if not mask[match.start()] or match.group(1) in allowed_names:
            continue
        open_brace = next(
            (index for index in range(match.end(), len(text))
             if text[index] == "{" and mask[index]),
            None,
        )
        if open_brace is None:
            continue
        depth = 0
        close_brace = None
        for index in range(open_brace, len(text)):
            if not mask[index]:
                continue
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    close_brace = index + 1
                    break
        if close_brace is not None:
            removals.append((match.start(), close_brace))
    for start, end in reversed(removals):
        text = text[:start] + text[end:]
    return text


def rust_target_symbol_paths(target_dir: Path) -> dict[str, str]:
    """Best-effort public Rust function -> module-path index for oracle imports."""
    src = target_dir / "src"
    paths: dict[str, str] = {}
    if not src.is_dir():
        return paths
    for file in sorted(src.rglob("*.rs")):
        rel = file.relative_to(src)
        module_parts = list(rel.with_suffix("").parts)
        if module_parts[-1] in {"lib", "mod", "main"}:
            module_parts = module_parts[:-1]
        module = "::".join(module_parts)
        text = file.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(
            r"(?m)^\s*pub\s+(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)", text
        ):
            paths.setdefault(match.group(1), module)
    lib = src / "lib.rs"
    if lib.is_file():
        text = lib.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(
            r"(?m)^\s*pub\s+use\s+[^;]*?(?:\{([^}]+)\}|::([A-Za-z_][A-Za-z0-9_]*))\s*;",
            text,
        ):
            names = (
                [part.strip().split(" as ")[-1] for part in match.group(1).split(",")]
                if match.group(1)
                else [match.group(2)]
            )
            for name in names:
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
                    paths[name] = ""
    return paths


def rust_target_method_traits(
    target_dir: Path,
    target_symbol_paths: Mapping[str, str],
) -> dict[str, str]:
    """Return unambiguous public trait-method -> import-path mappings."""
    src = target_dir / "src"
    if not src.is_dir():
        return {}
    candidates: dict[str, set[str]] = {}
    trait_re = re.compile(
        r"\bpub(?:\([^)]*\))?\s+trait\s+([A-Za-z_][A-Za-z0-9_]*)[^{]*\{"
    )
    method_re = re.compile(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*[<(]")
    for file in sorted(src.rglob("*.rs")):
        text = file.read_text(encoding="utf-8", errors="replace")
        mask = rust_source_code_mask(text)
        rel = file.relative_to(src)
        module_parts = list(rel.with_suffix("").parts)
        if module_parts[-1] in {"lib", "mod", "main"}:
            module_parts = module_parts[:-1]
        module = "::".join(module_parts)
        for trait_match in trait_re.finditer(text):
            if not mask[trait_match.start()]:
                continue
            open_brace = text.rfind("{", trait_match.start(), trait_match.end())
            depth = 0
            close_brace = None
            for index in range(open_brace, len(text)):
                if not mask[index]:
                    continue
                if text[index] == "{":
                    depth += 1
                elif text[index] == "}":
                    depth -= 1
                    if depth == 0:
                        close_brace = index
                        break
            if close_brace is None:
                continue
            trait_name = trait_match.group(1)
            trait_path = target_symbol_paths.get(trait_name)
            if trait_path is None:
                trait_path = f"{module}::{trait_name}" if module else trait_name
            else:
                trait_path = (
                    f"{trait_path}::{trait_name}" if trait_path else trait_name
                )
            for method_match in method_re.finditer(
                text, open_brace + 1, close_brace,
            ):
                if mask[method_match.start()]:
                    candidates.setdefault(method_match.group(1), set()).add(
                        trait_path,
                    )
    return {
        method: next(iter(paths))
        for method, paths in candidates.items()
        if len(paths) == 1
    }


_RUST_USE_LINE_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)use\s+(?P<crate>[A-Za-z_][A-Za-z0-9_]*)::"
    r"(?P<body>[^;]+);[ \t]*$"
)


def rewrite_rust_use_paths(
    text: str,
    name_mapping: Mapping[str, str],
    target_symbol_paths: Mapping[str, str],
    *,
    protected_identifiers: set[str] | None = None,
) -> str:
    """Retarget oracle ``use`` statements to CodeWeaver's actual module paths."""
    exact, _ = build_identifier_rewrite_index(name_mapping)
    protected = protected_identifiers or set()

    def mapped_import(source_path: str) -> str:
        source_name = source_path.rsplit("::", 1)[-1]
        target = exact.get(source_name)
        if source_name in protected:
            return source_path
        if target is None:
            if source_name not in target_symbol_paths:
                return source_path
            target = source_name
        target_parts = target.split("::")
        if len(target_parts) > 1:
            return target_parts[0]
        module = target_symbol_paths.get(target)
        return f"{module}::{target}" if module else target

    def replacement(match: re.Match[str]) -> str:
        indent = match.group("indent")
        crate = match.group("crate")
        body = match.group("body").strip()
        if crate in protected:
            return match.group(0)
        if body.startswith("{") and body.endswith("}"):
            inner = body[1:-1]
            if "{" in inner or "}" in inner:
                return match.group(0)
            items = [item.strip() for item in inner.split(",") if item.strip()]
        elif "{" in body or "}" in body:
            return match.group(0)
        else:
            items = [body]

        rewritten: list[str] = []
        for item in items:
            source_path, separator, alias = item.partition(" as ")
            imported = mapped_import(source_path.strip())
            if separator:
                imported = f"{imported} as {alias.strip()}"
            if imported not in rewritten:
                rewritten.append(imported)
        return "\n".join(f"{indent}use {crate}::{item};" for item in rewritten)

    return _RUST_USE_LINE_RE.sub(replacement, text)


def add_rust_trait_imports(
    text: str,
    name_mapping: Mapping[str, str],
    applied_identifiers: list[str],
    target_method_traits: Mapping[str, str],
    *,
    protected_identifiers: set[str] | None = None,
) -> str:
    """Import traits required by rewritten method-call syntax."""
    exact, _ = build_identifier_rewrite_index(name_mapping)
    required = {
        target_method_traits[target.rsplit("::", 1)[-1]]
        for source in applied_identifiers
        if (target := exact.get(source)) is not None
        and target.rsplit("::", 1)[-1] in target_method_traits
    }
    if not required:
        return text
    protected = protected_identifiers or set()
    use_matches = list(_RUST_USE_LINE_RE.finditer(text))
    crate = next(
        (
            match.group("crate")
            for match in use_matches
            if match.group("crate") not in protected
            and match.group("crate") not in {"std", "core", "alloc", "crate", "self", "super"}
        ),
        None,
    )
    if crate is None:
        return text
    existing = {
        identifier
        for match in use_matches
        for identifier in _IDENTIFIER_TOKEN_RE.findall(match.group("body"))
    }
    imports = [
        f"use {crate}::{trait_path};"
        for trait_path in sorted(required)
        if trait_path.rsplit("::", 1)[-1] not in existing
    ]
    return "\n".join([*imports, text]) if imports else text


_RUST_DECLARED_IDENTIFIER_RE = re.compile(
    r"\b(?:fn|struct|enum|trait|type|const|static)\s+([A-Za-z_][A-Za-z0-9_]*)"
)


def derive_rust_identifier_mapping(
    target_dir: Path,
    source_files: list[Path],
) -> dict[str, str]:
    """Derive unambiguous case/underscore-only API spelling adaptations."""
    target_by_normalized: dict[str, set[str]] = {}
    for path in sorted((target_dir / "src").rglob("*.rs")) if (target_dir / "src").is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        mask = rust_source_code_mask(text)
        for match in _RUST_DECLARED_IDENTIFIER_RE.finditer(text):
            if not mask[match.start()]:
                continue
            identifier = match.group(1)
            target_by_normalized.setdefault(
                _normalize_identifier_for_matching(identifier), set(),
            ).add(identifier)

    source_identifiers: set[str] = set()
    for path in source_files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        mask = rust_source_code_mask(text)
        source_identifiers.update(
            match.group(0)
            for match in _IDENTIFIER_TOKEN_RE.finditer(text)
            if mask[match.start()] and len(match.group(0)) > 1
        )

    derived: dict[str, str] = {}
    for source in source_identifiers:
        candidates = target_by_normalized.get(_normalize_identifier_for_matching(source), set())
        if len(candidates) == 1:
            target = next(iter(candidates))
            if target != source:
                derived[source] = target
    return derived


_RUST_PUBLIC_FIELD_RE = re.compile(
    r"\bpub(?:\([^)]*\))?\s+([A-Za-z_][A-Za-z0-9_]*)\s*:"
)
_RUST_FIELD_ACCESS_RE = re.compile(
    r"\.\s*([A-Za-z_][A-Za-z0-9_]*)"
)


def derive_rust_field_mapping(
    target_dir: Path,
    source_files: list[Path],
) -> dict[str, str]:
    """Derive unambiguous case/underscore-only public field adaptations."""
    target_by_normalized: dict[str, set[str]] = {}
    src = target_dir / "src"
    for path in sorted(src.rglob("*.rs")) if src.is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        mask = rust_source_code_mask(text)
        for match in _RUST_PUBLIC_FIELD_RE.finditer(text):
            if not mask[match.start()]:
                continue
            field = match.group(1)
            target_by_normalized.setdefault(
                _normalize_identifier_for_matching(field), set(),
            ).add(field)

    source_fields: set[str] = set()
    for path in source_files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        mask = rust_source_code_mask(text)
        source_fields.update(
            match.group(1)
            for match in _RUST_FIELD_ACCESS_RE.finditer(text)
            if mask[match.start(1)]
        )
    derived: dict[str, str] = {}
    for source in source_fields:
        candidates = target_by_normalized.get(
            _normalize_identifier_for_matching(source), set(),
        )
        if len(candidates) == 1:
            target = next(iter(candidates))
            if target != source:
                derived[source] = target
    return derived


def _adapt_rust_oracle_text(
    source_file: Path,
    *,
    name_mapping: Mapping[str, str] | None,
    target_symbol_paths: Mapping[str, str],
    target_method_traits: Mapping[str, str],
    allowed_test_names: set[str] | None,
    protected_identifiers: set[str] | None = None,
    target_field_mapping: Mapping[str, str] | None = None,
) -> tuple[str | None, list[str]]:
    """Return adapted text, or ``None`` when a byte copy is sufficient."""
    if not name_mapping and allowed_test_names is None:
        return None, []
    try:
        original = source_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, []
    new_text = original
    if allowed_test_names is not None:
        new_text = retain_named_rust_tests(new_text, allowed_test_names)
    applied: list[str] = []
    if name_mapping:
        new_text = rewrite_rust_use_paths(
            new_text,
            name_mapping,
            target_symbol_paths,
            protected_identifiers=protected_identifiers,
        )
        new_text, applied = rewrite_identifiers_with_name_mapping(
            new_text,
            name_mapping,
            protected_identifiers=protected_identifiers,
        )
        new_text, field_applied = rewrite_rust_field_accesses(
            new_text,
            target_field_mapping or {},
            protected_identifiers=protected_identifiers,
        )
        applied = sorted(set(applied) | set(field_applied))
        new_text = add_rust_trait_imports(
            new_text,
            name_mapping,
            applied,
            target_method_traits,
            protected_identifiers=protected_identifiers,
        )
    return (new_text, applied) if new_text != original or applied else (None, [])


def paper_runtime_tests_expected(
    tool: str, project: str | None, native_fallback: Measurement, *,
    official_artifact_verified: bool = False,
) -> Measurement:
    """Prefer the paper/workbook runtime denominator for non-CRUST projects."""
    if not official_artifact_verified:
        return native_fallback
    value = C.PAPER_RUNTIME_TESTS_BY_PROJECT.get((tool, project or ""))
    if value is None:
        return native_fallback
    return Measurement(
        value=value,
        status=Status.MEASURED,
        reason=(
            "paper-aligned runtime-case denominator; preserved separately from "
            "the static oracle-method count"
        ),
    )


def oxidizer_validated_tests_expected(
    oracle_files: list[Path], project: str | None = None, *,
    official_artifact_verified: bool = False,
) -> Measurement:
    """``validated_tests_expected`` for Oxidizer: a static ``#[test]`` count
    across the reference tree's own developer-test oracle files (the first
    element of ``oxidizer_reference_test_files``'s return value) -- read
    directly from ``--reference-results-root``, entirely independent of the
    CodeWeaver-translated target's own build/import status."""
    if not oracle_files:
        return Measurement.unavailable(
            "no reference developer-test oracle files resolved (missing --reference-results-root, project "
            "absent from the reference tree, or its rust/tests has no *_test.rs files)"
        )
    native = Measurement.ok(count_rust_test_attributes(oracle_files))
    return paper_runtime_tests_expected(
        "oxidizer", project, native,
        official_artifact_verified=official_artifact_verified,
    )


def alphatrans_verified_test_dir(ref_project_dir: Path | None) -> Path | None:
    """``<ref_project_dir>/verified_test`` if it exists, else None."""
    if ref_project_dir is None:
        return None
    d = ref_project_dir / "verified_test"
    return d if d.is_dir() else None


def count_python_test_functions(paths: list[Path]) -> int:
    """Best-effort STATIC count of pytest-/unittest-style test functions
    across ``paths`` (parsed via ``ast.parse`` -- source is never imported or
    executed): every ``def``/``async def`` (free function OR method, so this
    also counts ``unittest.TestCase`` methods) whose name starts with
    ``"test"``, matching both pytest's and unittest's own discovery
    convention. A file that fails to parse is skipped rather than raising --
    this denominator must stay computable even when other parts of a run are
    unhealthy; skipping only ever UNDER-counts, never fabricates a count."""
    count = 0
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                count += 1
    return count


def alphatrans_validated_tests_expected(verified_dir: Path | None) -> Measurement:
    """``validated_tests_expected`` for AlphaTrans: a static test-function
    count across the reference tree's own ``verified_test/*.py`` files (see
    ``count_python_test_functions``) -- read directly from
    ``--reference-results-root``, entirely independent of the CodeWeaver-
    translated target's own import/collection status."""
    if verified_dir is None:
        return Measurement.unavailable(
            "no verified_test/ resolved under --reference-results-root for this project (missing "
            "--reference-results-root, or this project is absent from the reference tree)"
        )
    py_files = sorted(verified_dir.rglob("*.py"))
    if not py_files:
        return Measurement.unavailable("verified_test/ has no .py files to count test functions in")
    native = Measurement.ok(count_python_test_functions(py_files))
    return paper_runtime_tests_expected(
        "alphatrans", verified_dir.parent.name, native,
        official_artifact_verified=(verified_dir.parent / "test_comparison_report.json").is_file(),
    )


def _evaluate_with_replaced_subdir(
    target_dir: Path, files: list[Path], subdir: str, tool: str, test_cmd: list[str], *,
    timeout: float | None, dataset_spec: dict[str, Any] | None = None,
    runner: CommandRunner = default_command_runner, tmp_prefix: str = "recodeagent_oracle_",
    name_mapping: Mapping[str, str] | None = None,
    rust_integration_tests_only: bool = False,
    allowed_rust_tests: Mapping[str, set[str]] | None = None,
    support_files: list[Path] | None = None,
) -> dict[str, Measurement]:
    """Copies ``target_dir`` into a fresh TEMPORARY directory, WIPES
    ``<tmp>/<subdir>/`` and repopulates it with EXACTLY ``files`` (flat copy,
    never merging in whatever the run's own ``<subdir>/`` already contained),
    then runs ``test_cmd`` there. Only ``files`` themselves are ever copied
    out of a reference tree -- never a reference implementation/Cargo/source
    file alongside them, so a genuine public-API mismatch between the
    CodeWeaver translation and the paper's own oracle tests surfaces as a
    real (not silently avoided) failure.

    ``name_mapping`` (optional; see ``read_name_mapping``) is Oxidizer's
    idiomatic-identifier-rewrite mitigation (see the "Oracle
    identifier-rewrite (Oxidizer only)" section above
    ``oxidizer_reference_test_files``): when truthy, each file's TEXT is
    passed through ``rewrite_identifiers_with_name_mapping`` before being
    staged into the temp tree -- a file with at least one eligible
    substitution is written pre-rewritten instead of byte-copied; the
    reference file ON DISK is never modified, only the in-memory copy. When
    ``name_mapping`` is empty/``None``, undecodable, or produces zero
    eligible substitutions for a given file, that file is still copied via
    ``shutil.copy2`` exactly as before -- byte-for-byte identical behavior,
    guaranteeing zero regression for callers that never pass this
    parameter (every non-Oxidizer adapter uses its own, separate copy
    logic and never calls this helper at all)."""
    if not target_dir.exists():
        missing = Measurement.missing("target tree does not exist (nothing was produced)")
        return {"total": missing, "passed": missing, "failed": missing}
    if not files:
        unavailable = Measurement.unavailable(
            "no reference test/harness files resolved to evaluate against (missing "
            "--reference-results-root, or this project/subdir is absent from the reference tree)"
        )
        return {"total": unavailable, "passed": unavailable, "failed": unavailable}
    support_files = support_files or []
    protected_identifiers = oxidizer_reference_support_identifiers(support_files)
    if tool == "oxidizer":
        derived_mapping = derive_rust_identifier_mapping(
            target_dir, [*files, *support_files],
        )
        derived_mapping.update(name_mapping or {})
        name_mapping = derived_mapping
    rewritten_files: list[str] = []
    rewritten_identifiers: set[str] = set()
    target_symbol_paths = rust_target_symbol_paths(target_dir) if name_mapping else {}
    target_method_traits = (
        rust_target_method_traits(target_dir, target_symbol_paths)
        if name_mapping else {}
    )
    target_field_mapping = derive_rust_field_mapping(
        target_dir, [*files, *support_files],
    )
    with tempfile.TemporaryDirectory(prefix=tmp_prefix) as tmp:
        tmp_target = Path(tmp) / "target"
        copy_evaluation_tree(target_dir, tmp_target)
        dest = tmp_target / subdir
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        for f in [*support_files, *files]:
            dst = dest / f.name
            allowed = (
                set(allowed_rust_tests.get(f.name, set()))
                if allowed_rust_tests is not None and f in files else None
            )
            adapted, applied = _adapt_rust_oracle_text(
                f,
                name_mapping=name_mapping,
                target_symbol_paths=target_symbol_paths,
                target_method_traits=target_method_traits,
                allowed_test_names=allowed,
                protected_identifiers=protected_identifiers,
                target_field_mapping=target_field_mapping,
            )
            if adapted is not None:
                dst.write_text(adapted, encoding="utf-8")
                if applied:
                    rewritten_files.append(f.name)
                    rewritten_identifiers.update(applied)
                continue
            shutil.copy2(f, dst)
        if rust_integration_tests_only:
            measured = {"total": 0, "passed": 0, "failed": 0}
            blocked: list[str] = []
            measured_files = 0
            for source_file in files:
                argv = [*test_cmd, "--test", source_file.stem]
                one = evaluate_tests(
                    tmp_target, argv, tool, timeout=timeout,
                    dataset_spec=dataset_spec, runner=runner,
                )
                if all(one[key].is_measured for key in ("total", "passed", "failed")):
                    measured_files += 1
                    for key in measured:
                        measured[key] += int(one[key].value)
                else:
                    blocked.append(f"{source_file.name}: {one['total'].reason}")
            if measured_files:
                reason = (
                    f"{len(blocked)} integration test binary/binaries did not compile or execute: "
                    + "; ".join(blocked[:5])
                ) if blocked else ""
                result = {
                    key: Measurement(value=value, status=Status.MEASURED, reason=reason)
                    for key, value in measured.items()
                }
            else:
                reason = (
                    "no independent Rust integration test binary compiled/executed: "
                    + "; ".join(blocked[:5])
                )
                unavailable = Measurement.unavailable(reason)
                result = {"total": unavailable, "passed": unavailable, "failed": unavailable}
        else:
            result = evaluate_tests(
                tmp_target, test_cmd, tool, timeout=timeout,
                dataset_spec=dataset_spec, runner=runner,
            )
    if rewritten_identifiers:
        note = (f"identifier rewrite applied to {len(rewritten_files)} reference file(s) using this run's "
               f"own Planner name_mapping ({', '.join(sorted(rewritten_identifiers))}) before evaluation -- "
               "prevents an idiomatic-renaming false negative from being misread as a behavioral failure")
        result = {
            key: dataclass_replace(m, reason=f"{m.reason} | {note}" if m.reason else note)
            for key, m in result.items()
        }
    return result


_PYTHON_EVAL_EXCLUDED_PARTS = frozenset({
    ".git", ".pytest_cache", "__pycache__", "agent_test", "build", "dist",
    "test", "tests", "verified_test",
})


def _python_module_name(relative_path: Path) -> str:
    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _camel_to_snake(name: str) -> str:
    first = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first).lower()


def _python_declared_symbols(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                symbols.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    symbols.add(target.id)
    return symbols


def _python_declared_attribute_aliases(path: Path) -> dict[str, str]:
    """Return declaration-only aliases such as ``Builder = CommandLine.Builder``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}

    def dotted_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = dotted_name(node.value)
            return f"{parent}.{node.attr}" if parent else None
        return None

    aliases: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = dotted_name(node.value)
        if isinstance(target, ast.Name) and value and "." in value:
            aliases[target.id] = value
    return aliases


def _target_python_module_index(
    target_dir: Path,
) -> tuple[dict[str, list[str]], dict[str, list[str]], list[str]]:
    """Index importable production modules without importing target code."""
    by_stem: dict[str, list[str]] = {}
    by_symbol: dict[str, list[str]] = {}
    production_parents: list[tuple[str, ...]] = []
    for path in sorted(target_dir.rglob("*.py")):
        rel = path.relative_to(target_dir)
        lowered = {part.lower() for part in rel.parts}
        if lowered & _PYTHON_EVAL_EXCLUDED_PARTS or path.name in {"conftest.py", "setup.py"}:
            continue
        module = _python_module_name(rel)
        if not module:
            continue
        production_parents.append(rel.parent.parts)
        if path.name != "__init__.py":
            by_stem.setdefault(path.stem.lower(), []).append(module)
        for symbol in _python_declared_symbols(path):
            by_symbol.setdefault(symbol, []).append(module)
    common_parts: tuple[str, ...] = ()
    if production_parents:
        common = list(production_parents[0])
        for parts in production_parents[1:]:
            prefix_length = 0
            for left, right in zip(common, parts, strict=False):
                if left != right:
                    break
                prefix_length += 1
            common = common[:prefix_length]
            if not common:
                break
        while common and not (target_dir.joinpath(*common) / "__init__.py").is_file():
            common.pop()
        common_parts = tuple(common)
    source_packages = [".".join(common_parts)] if common_parts else []
    return by_stem, by_symbol, source_packages


def _alphatrans_reference_production_files(ref_project_dir: Path) -> list[Path]:
    """Select reference module shapes only; implementation is never copied."""
    python_root = _resolve_case_insensitive(ref_project_dir, "python")
    if python_root is None:
        return []
    selected: list[Path] = []
    for path in sorted(python_root.rglob("*.py")):
        rel = path.relative_to(python_root)
        lowered = {part.lower() for part in rel.parts}
        if lowered & _PYTHON_EVAL_EXCLUDED_PARTS or path.name == "setup.py":
            continue
        # Real AlphaTrans production modules live in package trees. Avoid
        # replacing a target's own top-level module with a reference artifact.
        if len(rel.parts) < 2:
            continue
        selected.append(path)
    return selected


def _install_alphatrans_import_adapters(
    staged_target: Path,
    original_target: Path,
    ref_project_dir: Path,
) -> list[str]:
    """Recreate paper-test import paths while re-exporting CodeWeaver symbols."""
    by_stem, by_symbol, source_packages = _target_python_module_index(original_target)
    if not source_packages:
        return []
    python_root = _resolve_case_insensitive(ref_project_dir, "python")
    if python_root is None:
        return source_packages
    default_package = source_packages[0]
    for reference_file in _alphatrans_reference_production_files(ref_project_dir):
        rel = reference_file.relative_to(python_root)
        destination = staged_target / rel
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if reference_file.name == "__init__.py":
            destination.write_text(f"from {default_package} import *\n", encoding="utf-8")
            continue

        direct_modules = by_stem.get(_camel_to_snake(reference_file.stem), [])
        imports: list[str] = []
        if len(direct_modules) == 1:
            imports.append(f"from {direct_modules[0]} import *")
        else:
            for symbol in sorted(_python_declared_symbols(reference_file)):
                modules = by_symbol.get(symbol, [])
                if len(modules) == 1:
                    imports.append(f"from {modules[0]} import {symbol} as {symbol}")
        imports.extend(
            f"{alias} = {value}"
            for alias, value in _python_declared_attribute_aliases(reference_file).items()
        )
        if imports:
            destination.write_text("\n".join(dict.fromkeys(imports)) + "\n", encoding="utf-8")
    return source_packages


def _copy_alphatrans_test_support(staged_target: Path, ref_project_dir: Path) -> None:
    """Copy reference test helpers, never reference production modules."""
    python_root = _resolve_case_insensitive(ref_project_dir, "python")
    verified_root = alphatrans_verified_test_dir(ref_project_dir)
    if python_root is None:
        return
    for source in sorted(python_root.rglob("*")):
        if not source.is_file():
            continue
        rel = source.relative_to(python_root)
        lowered = tuple(part.lower() for part in rel.parts)
        if "test" not in lowered and "tests" not in lowered:
            continue
        support_suffix = rel
        if len(rel.parts) >= 3 and tuple(part.lower() for part in rel.parts[:3]) == (
            "src", "test", "python",
        ):
            support_suffix = Path(*rel.parts[3:])
        elif len(rel.parts) >= 2 and tuple(part.lower() for part in rel.parts[:2]) == (
            "src", "test",
        ):
            support_suffix = Path(*rel.parts[2:])
        elif rel.parts and rel.parts[0].lower() in {"test", "tests"}:
            support_suffix = Path(*rel.parts[1:])

        verified_counterpart = (
            verified_root / support_suffix if verified_root is not None else None
        )
        if verified_counterpart is not None and verified_counterpart.is_file() and source.suffix == ".py":
            module = _python_module_name(Path("verified_test") / support_suffix)
            content: str | None = f"from {module} import *\n"
        else:
            content = None
        destination = staged_target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            shutil.copy2(source, destination)
        else:
            destination.write_text(content, encoding="utf-8")
        # Some official helpers live at src/test/python/org/... but are
        # imported as src.test.org.... Mirror that package-only spelling.
        if len(rel.parts) >= 4 and tuple(part.lower() for part in rel.parts[:3]) == (
            "src", "test", "python",
        ):
            alias_destination = staged_target / Path("src", "test", *rel.parts[3:])
            alias_destination.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                shutil.copy2(source, alias_destination)
            else:
                alias_destination.write_text(content, encoding="utf-8")


@contextlib.contextmanager
def _staged_alphatrans_target(
    target_dir: Path,
    ref_project_dir: Path,
    *,
    include_verified: bool,
    include_generated: bool,
):
    """Yield an isolated target plus paper tests and API-layout adapters."""
    with tempfile.TemporaryDirectory(prefix="recodeagent_alphatrans_eval_") as tmp:
        staged_target = Path(tmp) / "target"
        copy_evaluation_tree(target_dir, staged_target)
        for dirname in ("verified_test", "agent_test"):
            stale = staged_target / dirname
            if stale.exists():
                shutil.rmtree(stale)

        if include_verified:
            verified_dir = alphatrans_verified_test_dir(ref_project_dir)
            if verified_dir is not None:
                shutil.copytree(verified_dir, staged_target / "verified_test")
        if include_generated:
            agent_test_dir = alphatrans_agent_test_dir(ref_project_dir)
            files = alphatrans_function_harness_files(agent_test_dir)
            if agent_test_dir is not None and files:
                destination = staged_target / "agent_test"
                destination.mkdir(parents=True, exist_ok=True)
                _copy_relative_files(agent_test_dir, files, destination)

        # AlphaTrans names translated developer tests ``*Test.py`` and most
        # generated tests ``*Test_generated.py``. Pytest's defaults discover
        # neither family consistently, so pin the artifact's intended class
        # and function conventions while retaining both filename shapes.
        (staged_target / "pytest.ini").write_text(
            "[pytest]\n"
            "python_files = test_*.py *Test.py *generated*.py\n"
            "python_classes = Test* *Test\n"
            "python_functions = test*\n"
            "pythonpath = . src/main/python\n",
            encoding="utf-8",
        )
        _copy_alphatrans_test_support(staged_target, ref_project_dir)
        source_packages = _install_alphatrans_import_adapters(
            staged_target, target_dir, ref_project_dir,
        )
        yield staged_target, source_packages


def alphatrans_validated_tests_eval(
    target_dir: Path, ref_project_dir: Path | None, *, timeout: float | None,
    runner: CommandRunner = default_command_runner, pytest_cmd: list[str] | None = None,
) -> dict[str, Measurement]:
    """AlphaTrans's independently validated developer tests: copy ONLY the
    reference results tree's ``verified_test/`` directory (never the
    reference's own Python implementation) into a TEMPORARY copy of the
    CodeWeaver-produced target, then run pytest against exactly that
    directory (``ALPHATRANS_VERIFIED_TEST_CMD`` by default, overridable via
    ``pytest_cmd``). Returns the uniform ``expected``/``executed``/
    ``passed``/``failed``/``not_executed`` shape (see
    ``_finalize_validated_tests``); ``expected``
    (``alphatrans_validated_tests_expected``) is computed from
    ``verified_test/`` alone and stays measured even when pytest itself
    cannot collect/import the target below."""
    verified_dir = alphatrans_verified_test_dir(ref_project_dir)
    expected = alphatrans_validated_tests_expected(verified_dir)
    if verified_dir is None:
        unavailable = Measurement.unavailable(
            "no verified_test/ resolved under --reference-results-root for this project (missing "
            "--reference-results-root, or this project is absent from the reference tree)"
        )
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         expected)
    if not target_dir.exists():
        missing = Measurement.missing("target tree does not exist (nothing was produced)")
        return _finalize_validated_tests({"total": missing, "passed": missing, "failed": missing}, expected)
    cmd = list(pytest_cmd) if pytest_cmd else list(ALPHATRANS_VERIFIED_TEST_CMD)
    assert ref_project_dir is not None
    with _staged_alphatrans_target(
        target_dir, ref_project_dir, include_verified=True, include_generated=False,
    ) as (staged_target, _):
        raw = evaluate_tests(staged_target, cmd, "alphatrans", timeout=timeout,
                             dataset_spec={"test_output_format": "pytest"}, runner=runner)
        return _finalize_validated_tests(raw, expected)


def _copy_relative_files(base_dir: Path, files: list[Path], dest: Path) -> None:
    """Copies each of ``files`` (assumed to live inside ``base_dir``) into
    ``dest``, preserving each file's path RELATIVE TO ``base_dir`` -- unlike
    ``_evaluate_with_replaced_subdir``'s flat by-basename copy (fine for
    Oxidizer's single-directory ``rust/tests/``), AlphaTrans's ``agent_test/``
    tree nests real files at varying depths (a ``python/`` subdir alongside a
    SIBLING ``resources/`` for some projects, no subdir at all for others --
    see ``alphatrans_function_harness_files``) and its own
    ``conftest.py``/package ``__init__.py`` machinery depends on that nesting
    being reproduced intact, not flattened into one directory."""
    for f in files:
        rel = f.relative_to(base_dir)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)


def alphatrans_agent_test_dir(ref_project_dir: Path | None) -> Path | None:
    """``<ref_project_dir>/agent_test`` if it exists, else None (case-
    insensitive, matching ``reference_project_dir``'s own tolerance)."""
    if ref_project_dir is None:
        return None
    return _resolve_case_insensitive(ref_project_dir, "agent_test")


def alphatrans_function_harness_files(agent_test_dir: Path | None) -> list[Path]:
    """Recursively selects, from ``<ref_project_dir>/agent_test`` (see
    ``alphatrans_agent_test_dir``), exactly the files the GENERATED
    function-harness adapter may copy: (a) every file under an immediate
    ``resources`` child directory (test fixtures/data, unconditionally --
    these are never production source), and (b) any ``.py`` file whose
    basename is ``__init__.py``/``conftest.py`` (case-insensitive) or
    contains "generated" anywhere in it (case-insensitive). Real project
    layouts nest these at varying depths -- e.g. directly under
    ``agent_test/`` for commons-fileupload, or under a ``python/`` subdir
    ALONGSIDE a sibling ``resources/`` for commons-cli/csv/validator -- so
    this is a single depth-agnostic recursive rule, never a path hardcoded
    to ``agent_test/python/...``. Every OTHER file is excluded -- in
    particular every plain ``XxxTest.py`` file with no "generated" in its
    name (the official system's OWN translated developer tests, a
    DIFFERENT metric from the generated function-harness this adapter
    measures) -- and the reference's Python PRODUCTION implementation under
    ``<ref_project_dir>/python`` is never even scanned, let alone copied
    (this function only ever walks inside ``agent_test_dir`` itself).
    Returns ``[]`` (never raises) when ``agent_test_dir`` is None."""
    if agent_test_dir is None:
        return []
    resources_dir = _resolve_case_insensitive(agent_test_dir, "resources")
    selected: list[Path] = []
    for p in sorted(agent_test_dir.rglob("*")):
        if not p.is_file():
            continue
        if resources_dir is not None and resources_dir in p.parents:
            selected.append(p)
            continue
        if p.suffix != ".py":
            continue
        name_lower = p.name.lower()
        if name_lower in ("__init__.py", "conftest.py") or "generated" in name_lower:
            selected.append(p)
    return selected


ALPHATRANS_GENERATED_FILES_BY_PROJECT: dict[str, frozenset[str]] = {
    "commons-cli": frozenset({
        "AlreadySelectedExceptionTest_generated.py", "AmbiguousOptionExceptionTest_generated.py",
        "BasicParserTest_generated.py", "CommandLineTest_generated.py",
        "DefaultParserTest_generated.py", "MissingArgumentExceptionTest_generated.py",
        "MissingOptionExceptionTest_generated.py", "OptionBuilderGeneratedTest.py",
        "OptionValidatorTest_generated.py", "ParseExceptionTest_generated.py",
        "ParserTest_generated.py", "PatternOptionBuilderTest_generated.py",
        "TypeHandlerTest_generated.py", "UnrecognizedOptionExceptionTest_generated.py",
    }),
    "commons-csv": frozenset({
        "BuilderTest_generated.py", "CSVBenchmarkTest_generated.py",
        "CSVFormatTest_generated.py", "CSVParserTest_generated.py",
        "CSVPerformanceTestClass_generated.py", "CSVRecordTest_generated.py",
        "ConstantsTest_generated.py", "DuplicateHeaderModeTest_generated.py",
        "QuoteModeTest_generated.py",
    }),
    "commons-fileupload": frozenset({
        "DefaultFileItemTest_generated.py", "ExceptionsTest_generated.py",
        "FileItemTest_generated.py", "FileUploadBaseTest_generated.py",
        "FileUploadTest_generated.py", "MultipartStreamTest_generated.py",
        "DiskFileItemFactoryTest_generated.py", "DiskFileItemTest_generated.py",
    }),
    "commons-validator": frozenset({
        "ArgTest_generated.py", "FormSetTest_generated.py",
        "GenericValidatorTest_generated.py", "ValidatorActionTest_generated.py",
    }),
}


def alphatrans_function_harness_eval(
    target_dir: Path, ref_project_dir: Path | None, *, timeout: float | None,
    runner: CommandRunner = default_command_runner, pytest_cmd: list[str] | None = None,
) -> dict[str, Measurement]:
    """AlphaTrans's GENERATED function-harness EXECUTION evidence --
    structurally DISTINCT from ``alphatrans_validated_tests_eval``'s
    independent developer-test oracle above, and from
    ``function_validation_*`` everywhere else in this module. Copies ONLY
    the reference results tree's ``agent_test/`` "generated"-named test
    files (plus their conftest/``__init__``/``resources`` support files --
    see ``alphatrans_function_harness_files``; the official Python
    PRODUCTION implementation and its plain, non-generated ``XxxTest.py``
    files are NEVER copied) into a TEMPORARY copy of the CodeWeaver-produced
    target, PRESERVING RELATIVE STRUCTURE (see ``_copy_relative_files``),
    then runs pytest against exactly that directory
    (``ALPHATRANS_FUNCTION_HARNESS_TEST_CMD`` by default, overridable via
    ``pytest_cmd``). This is execution-based EVIDENCE of how many generated
    harness tests pass/fail -- since AlphaTrans's generated tests are not
    known to have a reliable one-to-one per-function mapping, this is
    intentionally reported as ``function_harness_tests_*`` (a harness-test-
    count fact), never inferred/relabeled as a ``function_validation_*``
    per-function pass/fail count."""
    agent_test_dir = alphatrans_agent_test_dir(ref_project_dir)
    files = alphatrans_function_harness_files(agent_test_dir)
    if not files:
        unavailable = Measurement.unavailable(
            "no agent_test/ generated function-harness files resolved under --reference-results-root for "
            "this project (missing --reference-results-root, this project is absent from the reference "
            "tree, or it has no agent_test/ directory)"
        )
        return {"total": unavailable, "passed": unavailable, "failed": unavailable}
    if not target_dir.exists():
        missing = Measurement.missing("target tree does not exist (nothing was produced)")
        return {"total": missing, "passed": missing, "failed": missing}
    cmd = list(pytest_cmd) if pytest_cmd else list(ALPHATRANS_FUNCTION_HARNESS_TEST_CMD)
    assert ref_project_dir is not None
    project = ref_project_dir.name
    expected_files = ALPHATRANS_GENERATED_FILES_BY_PROJECT.get(project)
    official_exact = (
        expected_files is not None
        and expected_files.issubset({path.name for path in files})
        and (ref_project_dir / "test_comparison_report.json").is_file()
    )
    if official_exact:
        files = [path for path in files if path.name in expected_files]
    with _staged_alphatrans_target(
        target_dir, ref_project_dir, include_verified=False, include_generated=True,
    ) as (staged_target, _):
        if not official_exact:
            return evaluate_tests(staged_target, cmd, "alphatrans", timeout=timeout,
                                  dataset_spec={"test_output_format": "pytest"}, runner=runner)

        measured = {"total": 0, "passed": 0, "failed": 0}
        measured_files = 0
        blocked: list[str] = []
        command_prefix = cmd[:-1] if cmd and cmd[-1] == "agent_test" else cmd
        for source in files:
            relative = source.relative_to(agent_test_dir).as_posix()
            result = runner(
                [*command_prefix, f"agent_test/{relative}"],
                cwd=staged_target,
                timeout=timeout,
            )
            output = f"{result.stdout}\n{result.stderr}"
            if "ERROR collecting" in output or "Interrupted:" in output:
                blocked.append(f"{source.name}: pytest collection aborted")
                continue
            parsed = parse_test_output(
                "alphatrans", result.stdout, result.stderr,
                dataset_spec={"test_output_format": "pytest"},
            )
            if parsed is None:
                detail = "timed out" if result.timed_out else (
                    result.error or _tail(result.stderr) or f"exit code {result.returncode}"
                )
                blocked.append(f"{source.name}: {detail}")
                continue
            measured_files += 1
            for key in measured:
                measured[key] += int(parsed[key])
        if not measured_files:
            unavailable = Measurement.unavailable(
                "no official AlphaTrans generated test file collected/executed: "
                + "; ".join(blocked[:5])
            )
            return {"total": unavailable, "passed": unavailable, "failed": unavailable}
        reason = (
            f"{len(blocked)} of {len(files)} official generated test file(s) did not collect/execute: "
            + "; ".join(blocked[:5])
        ) if blocked else ""
        return {
            key: Measurement(value=value, status=Status.MEASURED, reason=reason)
            for key, value in measured.items()
        }


def _coverage_py_production_percentage(
    report_path: Path,
    *,
    included_roots: set[str] | None = None,
) -> float | None:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    covered = 0
    statements = 0
    excluded_roots = {"tests", "test", "verified_test", "agent_test"}
    for raw_path, row in (report.get("files", {}) if isinstance(report, dict) else {}).items():
        if not isinstance(raw_path, str) or not isinstance(row, dict):
            continue
        normalized = raw_path.replace("\\", "/").lstrip("./")
        parts = tuple(part for part in normalized.split("/") if part)
        if not parts or parts[0] in excluded_roots or parts[-1] in {"setup.py", "conftest.py"}:
            continue
        if included_roots and not any(part in included_roots for part in parts):
            continue
        if not normalized.endswith(".py"):
            continue
        summary = row.get("summary")
        if not isinstance(summary, dict):
            continue
        raw_covered = summary.get("covered_lines")
        raw_statements = summary.get("num_statements")
        if isinstance(raw_covered, (int, float)) and isinstance(raw_statements, (int, float)):
            covered += int(raw_covered)
            statements += int(raw_statements)
    return (100.0 * covered / statements) if statements > 0 else None


def alphatrans_paper_coverage_pair(
    target_dir: Path,
    ref_project_dir: Path | None,
    *,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Standardized line coverage using the official generated harness.

    This remains useful cross-system evidence, but it is not the
    paper-equivalent CodeWeaver-generated-test result.  The latter is
    produced by :func:`alphatrans_codeweaver_coverage_pair` after generated
    target tests have been independently classified.
    """
    verified_dir = alphatrans_verified_test_dir(ref_project_dir)
    agent_test_dir = alphatrans_agent_test_dir(ref_project_dir)
    generated_files = alphatrans_function_harness_files(agent_test_dir)
    if verified_dir is None or not target_dir.is_dir():
        unavailable = Measurement.unavailable(
            "AlphaTrans coverage requires CodeWeaver target plus reference verified_test/"
        )
        return unavailable, unavailable

    assert ref_project_dir is not None
    expected_files = ALPHATRANS_GENERATED_FILES_BY_PROJECT.get(ref_project_dir.name)
    if (
        expected_files is not None
        and expected_files.issubset({path.name for path in generated_files})
        and (ref_project_dir / "test_comparison_report.json").is_file()
    ):
        generated_files = [
            path for path in generated_files if path.name in expected_files
        ]
    generated_paths = (
        [
            f"agent_test/{path.relative_to(agent_test_dir).as_posix()}"
            for path in generated_files
        ]
        if agent_test_dir is not None else []
    )
    with _staged_alphatrans_target(
        target_dir, ref_project_dir, include_verified=True, include_generated=bool(generated_files),
    ) as (staged_target, source_packages):
        source_roots = {package.rsplit(".", 1)[-1] for package in source_packages}

        def run_coverage(label: str, pytest_paths: list[str]) -> tuple[float | None, str]:
            data_path = staged_target / f".coverage.{label}"
            json_path = staged_target / f"coverage-{label}.json"
            source_arg = [f"--source={','.join(source_packages)}"] if source_packages else []
            run_results: list[ExecResult] = []
            for index, pytest_path in enumerate(pytest_paths):
                append_arg = ["--append"] if index else []
                run_results.append(runner(
                    [
                        "python", "-m", "coverage", "run", f"--data-file={data_path}",
                        *append_arg, *source_arg, "-m", "pytest", "-q", pytest_path,
                    ],
                    cwd=staged_target,
                    timeout=timeout,
                ))
            json_result = runner(
                [
                    "python", "-m", "coverage", "json", f"--data-file={data_path}",
                    "-o", str(json_path),
                ],
                cwd=staged_target,
                timeout=timeout,
            )
            percentage = _coverage_py_production_percentage(
                json_path, included_roots=source_roots or None,
            )
            detail = (
                f"coverage run rc={[result.returncode for result in run_results]}, "
                f"coverage json rc={json_result.returncode}; "
                f"pytest paths={pytest_paths}"
            )
            return percentage, detail

        before_value, before_detail = run_coverage("developer", ["verified_test"])
        if generated_files:
            after_value, after_detail = run_coverage(
                "combined", ["verified_test", *generated_paths],
            )
        else:
            after_value, after_detail = before_value, (
                before_detail + "; no official generated harness files were available"
            )
        before = (
            Measurement(value=before_value, status=Status.MEASURED, reason=before_detail)
            if before_value is not None else
            Measurement.unavailable("Coverage.py produced no parseable production-line report: " + before_detail)
        )
        after = (
            Measurement(value=after_value, status=Status.MEASURED, reason=after_detail)
            if after_value is not None else
            Measurement.unavailable("Coverage.py produced no parseable production-line report: " + after_detail)
        )
        return before, after


def _pytest_collect_nodeids(text: str) -> list[str]:
    nodeids: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if ".py::" not in line or line.startswith(("ERROR ", "WARNING ")):
            continue
        nodeid = line.split(" ", 1)[0]
        if not nodeid.endswith(":"):
            nodeids.append(nodeid)
    return nodeids


def _select_python_generated_nodeids(
    target_dir: Path,
    generated_tests: list[tuple[str, str]],
    *,
    timeout: float | None,
    runner: CommandRunner,
) -> tuple[list[list[str]], list[str]]:
    grouped: dict[str, list[str]] = {}
    for path, name in generated_tests:
        grouped.setdefault(path, []).append(name)
    selected_groups: list[list[str]] = []
    blocked: list[str] = []
    for relative_path, names in sorted(grouped.items()):
        result = runner(
            ["python", "-m", "pytest", "--collect-only", "-q", relative_path],
            cwd=target_dir,
            timeout=timeout,
        )
        nodeids = _pytest_collect_nodeids(
            f"{result.stdout}\n{result.stderr}"
        )
        selected: list[str] = []
        normalized_path = relative_path.replace("\\", "/").lstrip("./")
        for name in names:
            matches = [
                nodeid
                for nodeid in nodeids
                if nodeid.split("::", 1)[0].replace("\\", "/").lstrip("./")
                == normalized_path
                and _normalized_test_name(
                    nodeid.rsplit("::", 1)[-1].split("[", 1)[0]
                )
                == _normalized_test_name(name)
            ]
            if matches:
                selected.extend(matches)
            else:
                blocked.append(f"{relative_path}::{name}: not collected")
        if selected:
            selected_groups.append(sorted(set(selected)))
        elif result.timed_out or result.error or result.returncode != 0:
            detail = "timed out" if result.timed_out else (
                result.error or _tail(result.stderr)
                or f"exit code {result.returncode}"
            )
            blocked.append(f"{relative_path}: {detail}")
    return selected_groups, blocked


def alphatrans_codeweaver_coverage_pair(
    target_dir: Path,
    ref_project_dir: Path | None,
    generated_tests: list[tuple[str, str]],
    *,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Coverage from the independent developer oracle, then that oracle plus
    only independently classified CodeWeaver-authored Python tests."""
    verified_dir = alphatrans_verified_test_dir(ref_project_dir)
    if verified_dir is None or not target_dir.is_dir():
        unavailable = Measurement.unavailable(
            "AlphaTrans CodeWeaver coverage requires a target plus reference verified_test/"
        )
        return unavailable, unavailable

    assert ref_project_dir is not None
    with _staged_alphatrans_target(
        target_dir,
        ref_project_dir,
        include_verified=True,
        include_generated=False,
    ) as (staged_target, source_packages):
        source_roots = {
            package.rsplit(".", 1)[-1] for package in source_packages
        }
        generated_groups, blocked = _select_python_generated_nodeids(
            staged_target,
            generated_tests,
            timeout=timeout,
            runner=runner,
        )

        def run_coverage(
            label: str,
            pytest_groups: list[list[str]],
        ) -> tuple[float | None, list[str]]:
            data_path = staged_target / f".coverage.codeweaver-{label}"
            json_path = staged_target / f"coverage-codeweaver-{label}.json"
            source_arg = (
                [f"--source={','.join(source_packages)}"]
                if source_packages else []
            )
            errors: list[str] = []
            for index, selectors in enumerate(pytest_groups):
                result = runner(
                    [
                        "python", "-m", "coverage", "run",
                        f"--data-file={data_path}",
                        *(["--append"] if index else []),
                        *source_arg,
                        "-m", "pytest", "-q", *selectors,
                    ],
                    cwd=staged_target,
                    timeout=timeout,
                )
                if result.timed_out or result.error:
                    detail = "timed out" if result.timed_out else result.error
                    errors.append(f"{selectors[0]}: {detail}")
            json_result = runner(
                [
                    "python", "-m", "coverage", "json",
                    f"--data-file={data_path}", "-o", str(json_path),
                ],
                cwd=staged_target,
                timeout=timeout,
            )
            if json_result.timed_out or json_result.error:
                errors.append(
                    "coverage json: "
                    + ("timed out" if json_result.timed_out else json_result.error)
                )
            return (
                _coverage_py_production_percentage(
                    json_path,
                    included_roots=source_roots or None,
                ),
                errors,
            )

        developer_group = [["verified_test"]]
        before_value, before_errors = run_coverage(
            "developer", developer_group,
        )
        after_value, after_errors = run_coverage(
            "combined", [*developer_group, *generated_groups],
        )
        reason = (
            "paper-equivalent Coverage.py production-line coverage over the "
            f"independent developer oracle and {len(generated_tests)} classified "
            "CodeWeaver-authored generated test method(s)"
        )
        if blocked:
            reason += f"; blocked generated selectors={blocked[:10]}"
        if before_errors or after_errors:
            reason += (
                f"; coverage process errors: developer={before_errors[:5]}, "
                f"combined={after_errors[:5]}"
            )
        before = (
            Measurement(value=before_value, status=Status.MEASURED, reason=reason)
            if before_value is not None else
            Measurement.unavailable(
                "Coverage.py produced no developer production-line report: "
                + reason
            )
        )
        after = (
            Measurement(value=after_value, status=Status.MEASURED, reason=reason)
            if after_value is not None else
            Measurement.unavailable(
                "Coverage.py produced no combined production-line report: "
                + reason
            )
        )
        return before, after


def oxidizer_paper_coverage_pair(
    target_dir: Path,
    ref_project_dir: Path | None,
    *,
    name_mapping: Mapping[str, str] | None,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Standardized tarpaulin union using the official generated harness."""
    oracle_files, _ = oxidizer_reference_test_files(ref_project_dir)
    generated_files = oxidizer_generated_test_files(ref_project_dir)
    support_files = oxidizer_reference_support_files(ref_project_dir)
    protected_identifiers = oxidizer_reference_support_identifiers(support_files)
    inventory = oxidizer_reference_test_inventory(ref_project_dir)
    if not target_dir.is_dir() or not oracle_files:
        unavailable = Measurement.unavailable(
            "Oxidizer coverage requires a CodeWeaver target and official developer-test oracle files"
        )
        return unavailable, unavailable

    with tempfile.TemporaryDirectory(prefix="recodeagent_oxidizer_coverage_") as tmp:
        tmp_root = Path(tmp)
        staged_target = tmp_root / "target"
        copy_evaluation_tree(target_dir, staged_target)
        staged_tests = staged_target / "tests"
        if staged_tests.exists():
            shutil.rmtree(staged_tests)
        staged_tests.mkdir(parents=True)
        effective_mapping = derive_rust_identifier_mapping(
            target_dir, [*oracle_files, *generated_files, *support_files],
        )
        effective_mapping.update(name_mapping or {})
        symbol_paths = rust_target_symbol_paths(target_dir) if effective_mapping else {}
        method_traits = (
            rust_target_method_traits(target_dir, symbol_paths)
            if effective_mapping else {}
        )
        field_mapping = derive_rust_field_mapping(
            target_dir, [*oracle_files, *generated_files, *support_files],
        )

        def stage(files: list[Path], *, curated: bool) -> None:
            for source in files:
                allowed = set(inventory.get(source.name, set())) if curated else None
                adapted, _ = _adapt_rust_oracle_text(
                    source,
                    name_mapping=effective_mapping,
                    target_symbol_paths=symbol_paths,
                    target_method_traits=method_traits,
                    allowed_test_names=allowed,
                    protected_identifiers=protected_identifiers,
                    target_field_mapping=field_mapping,
                )
                destination = staged_tests / source.name
                if adapted is None:
                    shutil.copy2(source, destination)
                else:
                    destination.write_text(adapted, encoding="utf-8")

        stage(support_files, curated=False)
        stage(oracle_files, curated=bool(inventory))
        stage(generated_files, curated=False)

        def run_files(files: list[Path], group: str) -> tuple[list[Path], list[str]]:
            reports: list[Path] = []
            errors: list[str] = []
            for source in files:
                test_name = source.stem
                out_dir = tmp_root / "reports" / group / test_name
                out_dir.mkdir(parents=True, exist_ok=True)
                result = runner(
                    [
                        "cargo", "tarpaulin", "--test", test_name, "--no-fail-fast",
                        "-o", "Json", "--output-dir", str(out_dir), "--", "--test-threads=1",
                    ],
                    cwd=staged_target,
                    timeout=timeout or 300,
                )
                report = out_dir / "tarpaulin-report.json"
                if report.is_file():
                    reports.append(report)
                else:
                    detail = "timed out" if result.timed_out else (
                        result.error or _tail(result.stderr) or f"exit code {result.returncode}"
                    )
                    errors.append(f"{source.name}: {detail}")
            return reports, errors

        developer_reports, developer_errors = run_files(oracle_files, "developer")
        generated_reports, generated_errors = run_files(generated_files, "generated")
        if not developer_reports:
            unavailable = Measurement.unavailable(
                "cargo-tarpaulin produced no Oxidizer developer-test reports"
                + (f": {developer_errors[:5]}" if developer_errors else "")
            )
            return unavailable, unavailable

        dev_covered, dev_coverable = _merge_tarpaulin_line_reports(developer_reports)
        gen_covered, gen_coverable = _merge_tarpaulin_line_reports(generated_reports)
        coverable = dict(dev_coverable)
        for key, count in gen_coverable.items():
            coverable[key] = max(coverable.get(key, 0), count)
        denominator = sum(coverable.values())
        if denominator <= 0:
            unavailable = Measurement.unavailable(
                "cargo-tarpaulin reports contained no coverable Oxidizer production lines"
            )
            return unavailable, unavailable

        combined = {key: set(lines) for key, lines in dev_covered.items()}
        for key, lines in gen_covered.items():
            combined.setdefault(key, set()).update(lines)
        reason = (
            f"standardized cargo-tarpaulin line union over {len(oracle_files)} official developer "
            f"file(s) and {len(generated_files)} official generated file(s); "
            f"coverable production lines={denominator}"
        )
        if developer_errors or generated_errors:
            reason += (
                f"; missing report(s): developer={developer_errors[:5]}, "
                f"generated={generated_errors[:5]}"
            )
        return (
            Measurement(
                value=100.0 * sum(map(len, dev_covered.values())) / denominator,
                status=Status.MEASURED,
                reason=reason,
            ),
            Measurement(
                value=100.0 * sum(map(len, combined.values())) / denominator,
                status=Status.MEASURED,
                reason=reason,
            ),
        )


def oxidizer_codeweaver_coverage_pair(
    target_dir: Path,
    ref_project_dir: Path | None,
    generated_tests: list[tuple[str, str]],
    *,
    name_mapping: Mapping[str, str] | None,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Coverage from the curated developer oracle plus classified
    CodeWeaver-authored Rust tests, without executing translated tests."""
    oracle_files, _ = oxidizer_reference_test_files(ref_project_dir)
    support_files = oxidizer_reference_support_files(ref_project_dir)
    protected_identifiers = oxidizer_reference_support_identifiers(support_files)
    inventory = oxidizer_reference_test_inventory(ref_project_dir)
    if not target_dir.is_dir() or not oracle_files:
        unavailable = Measurement.unavailable(
            "Oxidizer CodeWeaver coverage requires a target and official developer-test oracle"
        )
        return unavailable, unavailable

    with tempfile.TemporaryDirectory(
        prefix="recodeagent_oxidizer_codeweaver_coverage_"
    ) as tmp:
        tmp_root = Path(tmp)
        staged_target = tmp_root / "target"
        copy_evaluation_tree(target_dir, staged_target)
        staged_tests = staged_target / "tests"
        staged_tests.mkdir(parents=True, exist_ok=True)
        effective_mapping = derive_rust_identifier_mapping(
            target_dir, [*oracle_files, *support_files],
        )
        effective_mapping.update(name_mapping or {})
        symbol_paths = (
            rust_target_symbol_paths(target_dir) if effective_mapping else {}
        )
        method_traits = (
            rust_target_method_traits(target_dir, symbol_paths)
            if effective_mapping else {}
        )
        field_mapping = derive_rust_field_mapping(
            target_dir, [*oracle_files, *support_files],
        )

        developer_files: list[Path] = []
        for source in support_files:
            adapted, _ = _adapt_rust_oracle_text(
                source,
                name_mapping=effective_mapping,
                target_symbol_paths=symbol_paths,
                target_method_traits=method_traits,
                allowed_test_names=None,
                protected_identifiers=protected_identifiers,
                target_field_mapping=field_mapping,
            )
            destination = staged_tests / source.name
            if adapted is None:
                shutil.copy2(source, destination)
            else:
                destination.write_text(adapted, encoding="utf-8")
        for index, source in enumerate(oracle_files):
            allowed = set(inventory.get(source.name, set())) if inventory else None
            adapted, _ = _adapt_rust_oracle_text(
                source,
                name_mapping=effective_mapping,
                target_symbol_paths=symbol_paths,
                target_method_traits=method_traits,
                allowed_test_names=allowed,
                protected_identifiers=protected_identifiers,
                target_field_mapping=field_mapping,
            )
            destination = (
                staged_tests
                / f"__recodeagent_developer_{index}_{source.stem}.rs"
            )
            if adapted is None:
                shutil.copy2(source, destination)
            else:
                destination.write_text(adapted, encoding="utf-8")
            developer_files.append(destination)

        developer_reports: list[Path] = []
        developer_errors: list[str] = []
        for index, path in enumerate(developer_files):
            report, error = _run_tarpaulin_target(
                staged_target,
                target_args=("--test", path.stem),
                output_dir=tmp_root / "reports" / "developer" / str(index),
                timeout=timeout,
                runner=runner,
            )
            if report is not None:
                developer_reports.append(report)
            else:
                developer_errors.append(f"{path.name}: {error}")
        generated_reports, generated_errors = _rust_generated_tarpaulin_reports(
            staged_target,
            generated_tests,
            output_root=tmp_root / "reports" / "generated",
            timeout=timeout,
            runner=runner,
        )
        if not developer_reports:
            unavailable = Measurement.unavailable(
                "cargo-tarpaulin produced no Oxidizer developer-test reports"
                + (f": {developer_errors[:5]}" if developer_errors else "")
            )
            return unavailable, unavailable

        dev_covered, dev_coverable = _merge_tarpaulin_line_reports(
            developer_reports
        )
        gen_covered, gen_coverable = _merge_tarpaulin_line_reports(
            generated_reports
        )
        coverable = dict(dev_coverable)
        for key, count in gen_coverable.items():
            coverable[key] = max(coverable.get(key, 0), count)
        denominator = sum(coverable.values())
        if denominator <= 0:
            unavailable = Measurement.unavailable(
                "cargo-tarpaulin reports contained no coverable Oxidizer production lines"
            )
            return unavailable, unavailable

        combined = {key: set(lines) for key, lines in dev_covered.items()}
        for key, lines in gen_covered.items():
            combined.setdefault(key, set()).update(lines)
        reason = (
            "paper-equivalent cargo-tarpaulin line union over "
            f"{len(oracle_files)} curated developer file(s) and "
            f"{len(generated_tests)} classified CodeWeaver-authored generated test(s); "
            f"coverable production lines={denominator}"
        )
        if developer_errors or generated_errors:
            reason += (
                f"; missing report(s): developer={developer_errors[:5]}, "
                f"generated={generated_errors[:5]}"
            )
        return (
            Measurement(
                value=100.0 * sum(map(len, dev_covered.values())) / denominator,
                status=Status.MEASURED,
                reason=reason,
            ),
            Measurement(
                value=100.0 * sum(map(len, combined.values())) / denominator,
                status=Status.MEASURED,
                reason=reason,
            ),
        )


def skel_reference_javascript_dir(ref_project_dir: Path | None) -> Path | None:
    """``<ref_project_dir>/javascript`` if it exists, else None (case-
    insensitive, matching ``reference_project_dir``'s own tolerance)."""
    if ref_project_dir is None:
        return None
    return _resolve_case_insensitive(ref_project_dir, "javascript")


def skel_function_harness_files(javascript_dir: Path | None) -> list[Path]:
    """Selects, from ``<ref_project_dir>/javascript`` (see
    ``skel_reference_javascript_dir``), only the GENERATED function-test
    harness files this adapter may copy: every ``*.js`` file whose basename
    contains "generated" (case-insensitive) -- e.g. ``SKELTest_generated.js``,
    ``SkelHeadTest_generated.js``, or a project-specific
    ``*FunctionsTest_generated.js`` (real project layouts ship anywhere from
    one to a dozen of these). The reference's own production implementation
    (``source.js``) and any of its internal-only helper files (e.g. some
    projects' ``tracer_skip.js``) are NEVER selected -- even if a specific
    generated test happens to ``require()`` one of those helpers directly
    instead of ``source.js`` (a real, pre-existing dependency of that one
    reference test file on reference-only internals, not a harness defect);
    such a file is expected to fail honestly against CodeWeaver's own
    translation, exactly like a genuine public-API mismatch would.
    Non-recursive (SKEL's ``javascript/`` layout is itself flat). Returns
    ``[]`` (never raises) when ``javascript_dir`` is None."""
    if javascript_dir is None:
        return []
    return sorted(p for p in javascript_dir.glob("*.js") if "generated" in p.name.lower())


SKEL_GENERATED_CASES_BY_PROJECT: dict[str, int] = {
    "bst": 6,
    "colorsys": 46,
    "heapq": 11,
    "html": 13,
    "mathgen": 11,
    "rbt": 5,
    "strsim": 64,
    "toml": 150,
}

SKEL_GENERATED_FILES_BY_PROJECT: dict[str, frozenset[str]] = {
    "bst": frozenset({"SKELTest_generated.js"}),
    "colorsys": frozenset({"SkelHeadTest_generated.js", "_vTest_generated.js"}),
    "heapq": frozenset({"SkeletonInfrastructureTest_generated.js"}),
    "html": frozenset({"UtilityTest_generated.js"}),
    "mathgen": frozenset({"SkelUtilitiesTest_generated.js", "tracer_skipTest_generated.js"}),
    "rbt": frozenset({"RedBlackTreeTest_generated.js"}),
    "strsim": frozenset({
        "CosineTest_generated.js", "JaroWinklerTest_generated.js", "ModuleHelpersTest_generated.js",
        "SIFT4OptionsTest_generated.js", "ShingleBasedTest_generated.js",
    }),
    "toml": frozenset({
        "CommentValueTest_generated.js", "FileIOFunctionsTest_generated.js",
        "MarkerClassesTest_generated.js", "SerializationFunctionsTest_generated.js",
        "TomlDecodeErrorTest_generated.js", "TomlNumpyEncoderTest_generated.js",
        "TomlOrderedDecoderTest_generated.js", "TomlOrderedEncoderTest_generated.js",
        "TomlPathlibEncoderTest_generated.js", "TomlPreserveInlineDictEncoderTest_generated.js",
        "TomlTzTest_generated.js", "UtilityFunctionsTest_generated.js",
    }),
}

# Four official generated scripts embed the reference implementation instead
# of importing source.js. They must be rewritten before execution or they
# would validate the reference against itself rather than CodeWeaver's output.
SKEL_INLINE_GENERATED_BINDINGS: dict[tuple[str, str], dict[str, Any]] = {
    ("colorsys", "SkelHeadTest_generated.js"): {
        "remove": ("user_get_type", "user_check_type", "SkelClass"),
        "target": ("user_get_type", "user_check_type", "SkelClass"),
    },
    ("colorsys", "_vTest_generated.js"): {
        "remove": ("_v",),
        "target": ("_v",),
    },
    ("html", "UtilityTest_generated.js"): {
        "remove": ("user_get_type", "user_check_type", "SkelClass", "_replace_charref"),
        "target": ("user_get_type", "user_check_type", "SkelClass", "_replace_charref"),
    },
    ("toml", "TomlTzTest_generated.js"): {
        "remove": ("createTomlTz",),
        "target": ("TomlTz",),
        "aliases": {"createTomlTz": "() => __recodeagentTarget.TomlTz"},
    },
}


def skel_rewrite_inline_generated_harness(
    source_file: Path, *, project: str, target_filename: str = SKEL_TARGET_ENTRY_FILENAME,
) -> tuple[str | None, str]:
    """Remove known inline reference implementations from an official SKEL
    generated script and bind the same names to CodeWeaver's target instead.

    The replacement loader evaluates only the target file. Appending the
    binding-expression to the same Function body also makes private top-level
    declarations (for example colorsys ``_v``) observable without copying any
    reference implementation text into the harness.
    """
    spec = SKEL_INLINE_GENERATED_BINDINGS.get((project, source_file.name))
    try:
        original = source_file.read_bytes()
    except OSError as exc:
        return None, f"could not read generated harness: {exc}"
    if spec is None:
        return original.decode("utf-8", "replace"), ""

    parser = _skel_js_parser()
    if parser is None:
        return None, "tree-sitter JavaScript parser unavailable for safe inline-implementation removal"
    try:
        tree = parser.parse(original)
        declarations = _skel_top_level_declarations(tree.root_node, original)
    except Exception as exc:  # noqa: BLE001 - converted to an explicit unavailable measurement
        return None, f"could not parse generated harness for safe rewrite: {exc}"

    missing = [name for name in spec["remove"] if name not in declarations]
    if missing:
        return None, f"expected inline implementation declaration(s) not found: {missing}"

    ranges = sorted(
        ((declarations[name].start_byte, declarations[name].end_byte) for name in spec["remove"]),
        reverse=True,
    )
    rewritten = bytearray(original)
    for start, end in ranges:
        rewritten[start:end] = b""

    target_names = tuple(spec["target"])
    return_object = ", ".join(
        f'{json.dumps(name)}: (typeof {name} !== "undefined" ? {name} : module.exports[{json.dumps(name)}])'
        for name in target_names
    )
    direct_bindings = [
        f"const {name} = __recodeagentTarget[{json.dumps(name)}];"
        for name in target_names
        if name not in set((spec.get("aliases") or {}).keys())
    ]
    alias_bindings = [
        f"const {name} = {expression};"
        for name, expression in (spec.get("aliases") or {}).items()
    ]
    prelude = f"""
// ReCodeAgent reproduction: bind generated tests to CodeWeaver's target.
const __recodeagentTarget = (() => {{
    const __recodeagentFs = require('fs');
    const __recodeagentPath = require('path');
    let __recodeagentCode = __recodeagentFs.readFileSync(
        __recodeagentPath.join(__dirname, {json.dumps(target_filename)}), 'utf8'
    );
    __recodeagentCode = __recodeagentCode
        .replace(/^#!.*\\n/, '')
        .replace(
            /^\\s*import\\s+\\*\\s+as\\s+([A-Za-z_$][\\w$]*)\\s+from\\s+(['"][^'"]+['"])\\s*;?\\s*$/gm,
            'const $1 = require($2);'
        )
        .replace(/^\\s*export\\s*\\{{[\\s\\S]*?\\}};?\\s*$/gm, '')
        .replace(/^\\s*export\\s+(?=(?:async\\s+)?function|class|const|let|var)/gm, '')
        .replace(/^\\s*(?:test|run_all_tests)\\(\\);?\\s*$/gm, '');
    const __recodeagentModule = {{exports: {{}}}};
    return new Function(
        'module', 'exports', 'require', '__filename', '__dirname',
        __recodeagentCode + '\\n; return {{{return_object}}};'
    )(
        __recodeagentModule,
        __recodeagentModule.exports,
        require,
        __recodeagentPath.join(__dirname, {json.dumps(target_filename)}),
        __dirname
    );
}})();
{chr(10).join(direct_bindings + alias_bindings)}
"""
    text = rewritten.decode("utf-8", "replace")
    if text.startswith("#!"):
        first_line, separator, rest = text.partition("\n")
        text = first_line + separator + prelude + rest
    else:
        text = prelude + text
    return text, ""


def skel_function_harness_eval(
    target_dir: Path, ref_project_dir: Path | None, *, timeout: float | None,
    runner: CommandRunner = default_command_runner, node_cmd: str = "node",
) -> dict[str, Measurement]:
    """SKEL's GENERATED function-harness EXECUTION evidence. Copies ONLY the
    reference results tree's ``javascript/*generated*.js`` files (never
    ``source.js``/any non-test helper -- see ``skel_function_harness_files``)
    FLAT into a TEMPORARY copy of the CodeWeaver-produced target (SKEL's own
    ``javascript/`` layout is itself flat), additionally copying
    CodeWeaver's OWN ``index.js`` entry file to an extra
    ``SKEL_REFERENCE_ENTRY_ALIAS`` (``source.js``) file in that same
    directory -- WITHOUT renaming/removing the original ``index.js`` -- so
    the reference tests' own ``require('./source.js')``/``require('./source')``
    calls resolve against CodeWeaver's actual translation. SKEL's generated
    tests are ad hoc scripts with no shared test framework and no
    machine-parseable aggregate summary (a mix of ``throw``/
    ``process.exit(1)`` on failure and a bare ``console.log`` on success).
    It invokes ``node <file>.js`` once per selected file. For the eight real
    projects, ``total`` is the paper's exact generated-test CASE inventory
    (306 cases), not a file count. A successful exit proves every case in
    that project's scripts passed. If any script exits nonzero, case-level
    executed/pass/fail counts are explicitly unavailable because several
    scripts abort on their first failure and do not expose a parseable
    per-case result; the adapter never fabricates a file count as a case
    count. Synthetic/unknown projects retain a clearly-labeled file-count
    fallback for unit-test fixtures and future artifacts."""
    javascript_dir = skel_reference_javascript_dir(ref_project_dir)
    files = skel_function_harness_files(javascript_dir)
    if not files:
        unavailable = Measurement.unavailable(
            "no javascript/*generated*.js function-harness files resolved under --reference-results-root "
            "for this project (missing --reference-results-root, this project is absent from the "
            "reference tree, or it has no javascript/ directory)"
        )
        return {"total": unavailable, "passed": unavailable, "failed": unavailable}
    if not target_dir.exists():
        missing = Measurement.missing("target tree does not exist (nothing was produced)")
        return {"total": missing, "passed": missing, "failed": missing}
    with tempfile.TemporaryDirectory(prefix="recodeagent_skel_funcharness_") as tmp:
        tmp_target = Path(tmp) / "target"
        copy_evaluation_tree(target_dir, tmp_target)
        entry = tmp_target / SKEL_TARGET_ENTRY_FILENAME
        if entry.is_file():
            shutil.copy2(entry, tmp_target / SKEL_REFERENCE_ENTRY_ALIAS)
        rewrite_errors: list[str] = []
        project = ref_project_dir.name if ref_project_dir is not None else ""
        for f in files:
            rewritten, error = skel_rewrite_inline_generated_harness(f, project=project)
            if rewritten is None:
                rewrite_errors.append(f"{f.name}: {error}")
                continue
            C.atomic_write_text(tmp_target / f.name, rewritten)
        if rewrite_errors:
            unavailable = Measurement.unavailable(
                "safe generated-harness rewrite failed; no inline reference implementation was executed: "
                + "; ".join(rewrite_errors)
            )
            return {"total": unavailable, "passed": unavailable, "failed": unavailable}
        passed = 0
        failed = 0
        errors: list[str] = []
        for f in files:
            res = runner([node_cmd, f.name], cwd=tmp_target, timeout=timeout)
            ok = (not res.timed_out) and (not res.error) and (res.returncode == 0)
            if ok:
                passed += 1
            else:
                failed += 1
                detail = "timed out" if res.timed_out else (res.error or f"exit code {res.returncode}")
                errors.append(f"{f.name}: {detail}")
        expected_files = SKEL_GENERATED_FILES_BY_PROJECT.get(project)
        exact_cases = (
            SKEL_GENERATED_CASES_BY_PROJECT.get(project)
            if (
                expected_files is not None
                and {f.name for f in files} == expected_files
                and ref_project_dir is not None
                and (ref_project_dir / "test_comparison_report.json").is_file()
            )
            else None
        )
        if exact_cases is not None and failed:
            unavailable = Measurement.unavailable(
                f"{failed} of {len(files)} generated script(s) exited non-zero/errored; "
                "the scripts do not expose reliable per-case completion after an early abort, so case-level "
                f"executed/pass/fail counts over the fixed {exact_cases}-case inventory are unavailable: "
                f"{errors[:5]}"
            )
            return {"total": unavailable, "passed": unavailable, "failed": unavailable}
        if exact_cases is not None:
            return {
                "total": Measurement.ok(exact_cases),
                "passed": Measurement.ok(exact_cases),
                "failed": Measurement.ok(0),
            }
        reason = (
            "unknown/synthetic SKEL project: fallback unit is generated script files, not paper test cases"
            if not errors else
            f"{failed} of {len(files)} file(s) exited non-zero/errored: {errors[:5]}; "
            "unknown/synthetic project fallback unit is files"
        )
        return {
            "total": Measurement(value=len(files), status=Status.MEASURED, reason=reason),
            "passed": Measurement(value=passed, status=Status.MEASURED, reason=reason),
            "failed": Measurement(value=failed, status=Status.MEASURED, reason=reason),
        }


# --------------------------------------------------------------------------- #
# SKEL: AST-extracted independent VALIDATED developer tests.
#
# Unlike CRUST (a pristine scaffold)/Oxidizer (rust/tests/*.rs)/AlphaTrans
# (verified_test/), the official RESULTS artifact ships no separate
# independent-oracle FILE TREE for SKEL at all: its reference results only
# contain ``javascript/source.js``, which embeds BOTH the reference
# implementation AND its own translated test functions together as plain
# top-level ``function``/``class`` declarations, plus a per-project
# ``test_name_mapping.csv``. Every CSV row belongs to the paper's validated
# inventory (74 cases total); ``verified test`` records the prior system's
# outcome and is not a selector.
#
# This adapter AST-extracts (via ``tree-sitter``/``tree-sitter-javascript``,
# an OPTIONAL dependency probed via ``C.optional_import`` -- never installed
# by this harness) ONLY each listed test's own top-level function/class
# source text, verbatim -- never the rest of source.js, never any other
# declaration's body. A listed test is only actually extracted
# ("extractable") if EVERY free identifier its own body references resolves
# to one of:
#   (a) a known JS/Node global built-in (``SKEL_JS_GLOBAL_BUILTINS``);
#   (b) one of source.js's OWN top-level
#       ``const NAME = require("assert"|"util")`` bindings -- Node's OWN
#       standard library, never the reference's translated implementation
#       (``SKEL_SAFE_NODE_CORE_MODULES``);
#   (c) a name in source.js's OWN ``module.exports`` object literal -- i.e.
#       the reference's own DECLARED production API surface. Such a name is
#       bound in the synthetic harness from CodeWeaver's OWN target
#       ``require()`` (see ``SKEL_TARGET_ENTRY_FILENAME``), NEVER from
#       source.js's own definition -- so a genuine mismatch between the
#       CodeWeaver translation and the expected public API surfaces as an
#       honest per-test failure at harness-execution time, not a silent skip;
#   (d) a top-level ``function``/``class`` declaration in source.js that is
#       NOT itself part of (c) (source.js's own ``module.exports``), PROVIDED
#       CodeWeaver's OWN target entry file ALSO independently declares an
#       export with that exact same name (``target_export_names`` --
#       see ``_skel_read_module_export_names``). Some real SKEL fixtures
#       (e.g. heapq-style trees) ship a source.js with NO ``module.exports``
#       assignment at ALL, because the ORIGINAL script is self-contained and
#       its OWN tests simply call the sibling top-level implementation
#       function DIRECTLY by name -- (c) alone would then block virtually
#       every verified test in such a project. This is still SAFE, and
#       copies zero reference source text: it only WIDENS which target
#       identifiers a verified test may bind against (exactly the same
#       ``require(SKEL_TARGET_ENTRY_FILENAME).NAME`` binding mechanism as
#       (c)), gated on CodeWeaver's OWN target actually choosing to expose a
#       same-named symbol -- if it does not, extraction still blocks exactly
#       as before, so a private helper source.js never exports remains
#       private here too unless CodeWeaver's translation independently
#       decided otherwise (that is a real, visible translation-fidelity
#       question the executed test settles, never something this adapter
#       assumes);
#   (e) a top-level ``const``/``let``/``var NAME = <literal>`` declaration in
#       source.js whose initializer is a PROVABLY pure data literal --
#       nothing but numbers/strings/booleans/``null``/substitution-free
#       template strings, or arrays/objects built ONLY from other such pure
#       literals with plain (non-computed, non-spread, non-method,
#       non-shorthand) keys (``_skel_is_pure_literal_expression``). Such a
#       "literal-expectation" constant (e.g.
#       ``const EXPECTED = [1, 2, 3];``) is spliced into the harness
#       VERBATIM (``SkelExtractionOutcome.literal_support_lines``) rather
#       than requiring a target binding -- copying pure, self-contained DATA
#       can never leak reference IMPLEMENTATION logic (by construction it
#       references nothing else at all), unlike a helper FUNCTION.
#   (f) an explicitly pinned test-support function from
#       ``SKEL_SAFE_TEST_SUPPORT_FUNCTIONS``. These names were manually
#       verified as fixture/assertion helpers in the official test corpus;
#       executable production helpers are never admitted by this rule.
# ANY other free identifier -- most importantly, any OTHER top-level
# declaration in source.js that is neither (c)/(d)/(e) above (a genuinely
# private production helper, e.g. real bst fixtures' own
# ``_get_binary_search_tree``, or heapq-style ``_heappop_max``/
# ``_siftup_max`` that CodeWeaver's OWN target ALSO keeps unexported) --
# BLOCKS that one specific test, with a precise reason naming the
# unresolved identifier(s). This adapter never recursively inlines such
# helpers: a call-graph/"taint" analysis to decide whether a private helper
# FUNCTION is "test-only" (i.e. never reachable from anything exported) was
# evaluated and rejected, because real heapq fixtures have NO
# ``module.exports`` at all, so shared production internals like
# ``_heappop_max``/``_siftup_max`` cannot be reliably distinguished from
# genuinely test-only orchestration helpers by any static reachability
# check within that one file alone -- (d) resolves the specific,
# structurally-safe sub-case where CodeWeaver's OWN target independently
# re-exposes the same name (no reachability guess required, since it never
# copies source.js's own helper body at all), but a genuinely PRIVATE
# support-FUNCTION that CodeWeaver's target also does not export remains a
# deliberate, honestly-documented residual limitation -- a pending
# extension, not a claim that no oracle exists (the CSV/harness/aggregation
# machinery below is real and already extracts every project's builtin/
# require/export/target-export/literal-resolvable tests). It also never
# falls back to copying/inlining whole files or guessing.
#
# Aggregation is a real, honest three-way outcome, never a fabricated
# number:
#   - the CSV lists zero test names -> a real ``Status.MEASURED`` zero.
#   - the CSV lists >=1 names but EVERY one is blocked from
#     extraction -> ``Status.UNAVAILABLE``, reason names every blocked test.
#   - the CSV lists >=1 names and >=1 is extractable ->
#     ``Status.MEASURED``, but ``total`` is the EXTRACTABLE count (never the
#     full CSV count), with a reason noting any excluded tests -- reporting
#     the full CSV count instead would misleadingly imply full coverage.
# --------------------------------------------------------------------------- #

TREE_SITTER_MODULE_NAME = "tree_sitter"
TREE_SITTER_JAVASCRIPT_MODULE_NAME = "tree_sitter_javascript"

# JS/Node globals ANY verified test may freely reference without requiring
# anything from the target. Deliberately never grown to include anything
# that could plausibly BE a target export instead -- an incomplete list
# here only ever makes this adapter MORE conservative (blocks more tests),
# never less safe (it can never cause a private helper to be misresolved).
SKEL_JS_GLOBAL_BUILTINS: frozenset[str] = frozenset({
    "console", "Math", "JSON", "Array", "Object", "String", "Number", "Boolean",
    "Symbol", "Map", "Set", "WeakMap", "WeakSet", "Promise", "RegExp",
    "Error", "TypeError", "RangeError", "SyntaxError", "ReferenceError", "EvalError", "URIError",
    "parseInt", "parseFloat", "isNaN", "isFinite", "undefined", "NaN", "Infinity",
    "globalThis", "Function", "Date", "Reflect", "Proxy", "BigInt",
})

# A narrow allowlist of Node.js CORE (built into the runtime, no filesystem/
# network access) modules this adapter permits a verified test to depend on
# via source.js's OWN top-level ``const NAME = require("MODULE")`` -- e.g.
# real rbt fixtures' own ``const assert = require('assert');``. This is
# Node's standard library, never the reference's translated implementation,
# so replicating the identical require() call in the synthetic harness
# brings in no reference logic.
SKEL_SAFE_NODE_CORE_MODULES: frozenset[str] = frozenset({"assert", "util"})

SKEL_SAFE_TEST_SUPPORT_FUNCTIONS: dict[str, frozenset[str]] = {
    "bst": frozenset({"_get_binary_search_tree"}),
    "colorsys": frozenset({"assert_iter_almost_equal"}),
    "heapq": frozenset({
        "assert_equal", "assert_value_equal", "test_heapify_help_function",
        "test_heappush_help_function", "test_heappushpop_help_function",
        "test_heapreplace_help_function",
    }),
}

SKEL_VALIDATED_HARNESS_FILENAME = "__recodeagent_skel_validated_harness.mjs"


@dataclass
class SkelExtractedTest:
    """One verified SKEL test AST-extracted from the reference's
    ``javascript/source.js``: its exact top-level function/class source
    text (verbatim, nothing else) plus the free identifiers it references
    that must be bound from CodeWeaver's OWN target exports -- either
    source.js's own ``module.exports`` names, or a source.js top-level
    declaration CodeWeaver's OWN target independently ALSO exports under
    the same name (never source.js's private helpers) -- plus the names of
    any top-level "literal-expectation" constants (see
    ``SkelExtractionOutcome.literal_support_lines``) this test's body
    references, spliced verbatim rather than target-bound."""
    name: str
    source_text: str
    target_identifiers: tuple[str, ...]
    literal_support_names: tuple[str, ...] = ()


@dataclass
class SkelExtractionOutcome:
    """Result of statically classifying every CSV-listed SKEL test name
    against ``javascript/source.js``. ``extractable`` tests may safely be
    assembled into a synthetic harness (see
    ``skel_build_validated_harness_source``); ``blocked`` records, for
    every other listed test name, the precise reason extraction was
    refused -- never silently dropped. ``literal_support_lines`` is the
    deduplicated (by name, sorted), VERBATIM top-level ``const NAME =
    <pure literal>;`` declaration text for every "literal-expectation"
    constant referenced by >=1 extractable test (see this section's module
    docstring, resolution rule (e)) -- never a helper FUNCTION's body."""
    extractable: list[SkelExtractedTest] = field(default_factory=list)
    blocked: list[tuple[str, str]] = field(default_factory=list)
    safe_require_lines: tuple[str, ...] = ()
    literal_support_lines: tuple[str, ...] = ()
    test_support_lines: tuple[str, ...] = ()


def skel_parse_verified_test_names(csv_path: Path) -> list[str] | None:
    """Reads ``<ref_project_dir>/test_name_mapping.csv``'s own
    ``javascript test name`` column, returning exactly the names whose
    ``verified test`` column is ``"1"`` (order preserved; real files never
    repeat a name). Returns None -- never raises, and never an empty list
    used to mean two different things -- if the CSV is missing, unreadable,
    or lacks the expected columns, so callers can distinguish "no CSV at
    all" (``Status.UNAVAILABLE``) from "CSV present, genuinely zero verified
    tests" (a real ``Status.MEASURED`` zero)."""
    if not csv_path.is_file():
        return None
    try:
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            if "javascript test name" not in fieldnames or "verified test" not in fieldnames:
                return None
            return [
                row["javascript test name"].strip()
                for row in reader
                if (row.get("verified test") or "").strip() == "1"
                and (row.get("javascript test name") or "").strip()
            ]
    except (OSError, csv.Error, UnicodeDecodeError):
        return None


def skel_parse_validated_test_names(csv_path: Path) -> list[str] | None:
    """Return every fixed developer-test row in the SKEL mapping inventory.

    The ``verified test`` flag records whether SKEL's own translated test was
    semantically matched; it is an outcome, not a selector. The paper's
    validated-test denominator is all 74 rows, including every flag-0 row.
    """
    if not csv_path.is_file():
        return None
    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if "javascript test name" not in (reader.fieldnames or []):
                return None
            return [
                value
                for row in reader
                if (value := (row.get("javascript test name") or "").strip())
            ]
    except (OSError, csv.Error, UnicodeDecodeError):
        return None


def _skel_js_parser() -> Any:
    """Returns a ready ``tree_sitter.Parser`` for JavaScript, or None (never
    raises) if ``tree-sitter``/``tree-sitter-javascript`` are not installed
    or fail to initialize."""
    tree_sitter = C.optional_import(TREE_SITTER_MODULE_NAME)
    tsjs = C.optional_import(TREE_SITTER_JAVASCRIPT_MODULE_NAME)
    if tree_sitter is None or tsjs is None:
        return None
    try:
        language = tree_sitter.Language(tsjs.language())
        return tree_sitter.Parser(language)
    except Exception:  # noqa: BLE001 - a broken optional install must not crash collection
        return None


_PATTERN_BINDING_LEAF_TYPES = ("identifier", "shorthand_property_identifier_pattern")


def _skel_collect_pattern_identifiers(node: Any, src: bytes, out: set[str]) -> None:
    """Recursively collects every bound-variable NAME within a destructuring
    or parameter PATTERN node. Deliberately recurses ONLY into the BINDING
    side of a default-valued pattern (``assignment_pattern``'s ``left``,
    ``object_assignment_pattern``'s ``left``) -- never into the default
    VALUE expression itself, which is not a binding and may reference
    arbitrary outside identifiers that ``_skel_collect_free_identifiers``'s
    own whole-body walk must independently classify (treating it as a
    binding here would wrongly hide a genuine free reference inside a
    default value from that separate classification)."""
    if node is None:
        return
    if node.type in _PATTERN_BINDING_LEAF_TYPES:
        out.add(src[node.start_byte:node.end_byte].decode("utf-8", "replace"))
        return
    if node.type == "pair_pattern":
        _skel_collect_pattern_identifiers(node.child_by_field_name("value"), src, out)
        return
    if node.type in ("assignment_pattern", "object_assignment_pattern"):
        _skel_collect_pattern_identifiers(node.child_by_field_name("left"), src, out)
        return
    for child in node.children:
        _skel_collect_pattern_identifiers(child, src, out)


_FUNCTION_LIKE_TYPES = ("arrow_function", "function_declaration", "function_expression",
                       "generator_function_declaration", "method_definition")


def _skel_collect_local_bindings(node: Any, src: bytes, out: set[str]) -> None:
    """Recursively walks a function/class body collecting every name BOUND
    somewhere within it: parameters, ``const``/``let``/``var`` declarators,
    ``catch`` clauses, ``for``-``in``/``for``-``of`` bindings, and any
    NESTED function/class declaration's own name (so a test that defines and
    calls its own local helper is not wrongly treated as depending on an
    outside/target identifier). Used only to EXCLUDE genuinely-local names
    from the free-identifier scan below -- never, by itself, to decide
    extraction safety (an unrelated top-level source.js declaration is
    never treated as "local" just because this function fails to add it
    here)."""
    if node.type == "variable_declarator":
        _skel_collect_pattern_identifiers(node.child_by_field_name("name"), src, out)
    elif node.type == "catch_clause":
        param = node.child_by_field_name("parameter")
        if param is not None:
            _skel_collect_pattern_identifiers(param, src, out)
    elif node.type == "for_in_statement":
        left = node.child_by_field_name("left")
        if left is not None and left.type not in ("variable_declaration", "lexical_declaration"):
            _skel_collect_pattern_identifiers(left, src, out)
    if node.type in ("function_declaration", "generator_function_declaration", "class_declaration"):
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            out.add(src[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace"))
    if node.type in _FUNCTION_LIKE_TYPES:
        params = node.child_by_field_name("parameters")
        if params is not None:
            for c in params.children:
                _skel_collect_pattern_identifiers(c, src, out)
        single_param = node.child_by_field_name("parameter")
        if single_param is not None:
            _skel_collect_pattern_identifiers(single_param, src, out)
    for child in node.children:
        _skel_collect_local_bindings(child, src, out)


# Node types that represent a genuine variable/value REFERENCE in
# expression position -- "identifier" for ordinary references, PLUS
# "shorthand_property_identifier" for object-literal shorthand VALUE
# position (e.g. `return {foo};` means `{foo: foo}` -- `foo` there is a
# distinct grammar node type from plain "identifier", but is just as much a
# read of the outer `foo` binding, and must not be silently skipped/treated
# as automatically resolved).
_FREE_REFERENCE_TYPES = ("identifier", "shorthand_property_identifier")

# Node types whose OWN "name" field is a declaration (a binding site, e.g.
# `function foo() {}`'s own "foo"), never a reference to some OUTER "foo" --
# excluded from the free-identifier walk so a function/class never appears
# to reference its own name as an external dependency. (Property access --
# `obj.prop` / object-literal keys such as `pair`'s own `key` field -- gets
# its own distinct `property_identifier` node type in tree-sitter-javascript,
# which never matches `_FREE_REFERENCE_TYPES` in the first place, so no
# special-casing is required for those at all.)
_DECLARATION_NAME_PARENT_TYPES = ("function_declaration", "generator_function_declaration",
                                 "class_declaration", "variable_declarator", "catch_clause",
                                 "method_definition")


def _skel_collect_free_identifiers(func_node: Any, src: bytes) -> set[str]:
    """Every identifier-like reference (see ``_FREE_REFERENCE_TYPES``) the
    function/class BODY makes that is NOT itself a locally-bound name (see
    ``_skel_collect_local_bindings``) and is NOT merely a declaration's own
    name -- i.e. every external symbol the extracted test source actually
    depends on."""
    local_names: set[str] = set()
    _skel_collect_local_bindings(func_node, src, local_names)
    free: set[str] = set()

    def walk(node: Any) -> None:
        if node.type in _FREE_REFERENCE_TYPES:
            parent = node.parent
            if parent is not None and parent.type in _DECLARATION_NAME_PARENT_TYPES:
                if parent.child_by_field_name("name") is node:
                    return
            text = src[node.start_byte:node.end_byte].decode("utf-8", "replace")
            if text not in local_names:
                free.add(text)
            return
        for child in node.children:
            walk(child)

    walk(func_node)
    return free


def _skel_top_level_declarations(root: Any, src: bytes) -> dict[str, Any]:
    """Maps every top-level ``function``/``class`` declaration NAME (direct
    children of source.js's own ``program`` node) to its AST node."""
    out: dict[str, Any] = {}
    for child in root.children:
        if child.type in ("function_declaration", "generator_function_declaration", "class_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                out[src[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace")] = child
    return out


def _walk_nodes(node: Any):
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def _skel_module_exports_names(root: Any, src: bytes) -> set[str]:
    """The declared export names of ANY top-level JS file (source.js, OR --
    see ``_skel_read_module_export_names`` -- CodeWeaver's OWN target entry
    file) via either of two common CommonJS idioms: (1)
    ``module.exports = { ... }`` object-literal ASSIGNMENT (shorthand and/or
    explicit ``key: value`` properties), or (2) per-name member-assignment
    (``module.exports.NAME = ...`` / ``exports.NAME = ...``). For source.js,
    this is the reference's OWN DECLARED public surface, used only to
    decide whether a free identifier a verified test references represents
    genuine, translatable public API (safe to bind from CodeWeaver's OWN
    target exports) as opposed to one of source.js's private/test-only
    helpers (never inlined). This function never reads or reproduces any of
    these declarations' own bodies -- only their names."""
    names: set[str] = set()
    for child in root.children:
        if child.type == "export_statement":
            for node in _walk_nodes(child):
                if node.type == "export_specifier":
                    identifiers = [item for item in node.children if item.type == "identifier"]
                    if identifiers:
                        exported = identifiers[-1]
                        names.add(src[exported.start_byte:exported.end_byte].decode("utf-8", "replace"))
                elif node.type in (
                    "function_declaration", "generator_function_declaration", "class_declaration",
                ):
                    name_node = node.child_by_field_name("name")
                    if name_node is not None:
                        names.add(src[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace"))
                elif node.type == "variable_declarator":
                    name_node = node.child_by_field_name("name")
                    if name_node is not None:
                        _skel_collect_pattern_identifiers(name_node, src, names)
            continue
        if child.type != "expression_statement" or not child.children:
            continue
        expr = child.children[0]
        if expr.type != "assignment_expression":
            continue
        left = expr.child_by_field_name("left")
        right = expr.child_by_field_name("right")
        if left is None or right is None:
            continue
        left_text = src[left.start_byte:left.end_byte].decode("utf-8", "replace")
        if left_text == "module.exports" and right.type == "object":
            for prop in right.children:
                if prop.type == "shorthand_property_identifier":
                    names.add(src[prop.start_byte:prop.end_byte].decode("utf-8", "replace"))
                elif prop.type == "pair":
                    key = prop.child_by_field_name("key")
                    if key is not None:
                        names.add(src[key.start_byte:key.end_byte].decode("utf-8", "replace"))
            continue
        # Per-name member-assignment form: `module.exports.NAME = ...` /
        # `exports.NAME = ...` -- e.g. real SKEL fixtures without a single
        # combined object-literal export. `left`'s own "object" sub-field
        # reconstructs to exactly "module.exports" or "exports" for both.
        if left.type == "member_expression":
            obj = left.child_by_field_name("object")
            prop = left.child_by_field_name("property")
            if obj is None or prop is None or prop.type != "property_identifier":
                continue
            obj_text = src[obj.start_byte:obj.end_byte].decode("utf-8", "replace")
            if obj_text in ("module.exports", "exports"):
                names.add(src[prop.start_byte:prop.end_byte].decode("utf-8", "replace"))
    return names


def _skel_target_bindable_names(js_path: Path) -> frozenset[str]:
    """Return exports plus CodeWeaver target top-level declarations."""
    if not js_path.is_file():
        return frozenset()
    parser = _skel_js_parser()
    if parser is None:
        return frozenset()
    try:
        src = js_path.read_bytes()
        root = parser.parse(src).root_node
    except Exception:  # noqa: BLE001 - unavailable target metadata
        return frozenset()
    names = set(_skel_module_exports_names(root, src))
    names.update(_skel_top_level_declarations(root, src))
    for child in root.children:
        candidate = child
        if child.type == "export_statement":
            candidate = next(
                (node for node in child.children if node.type in (
                    "lexical_declaration", "variable_declaration",
                )),
                child,
            )
        if candidate.type not in ("lexical_declaration", "variable_declaration"):
            continue
        for declarator in candidate.children:
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            if name_node is not None:
                _skel_collect_pattern_identifiers(name_node, src, names)
    return frozenset(names)


def _skel_read_module_export_names(js_path: Path) -> frozenset[str]:
    """Best-effort listing of ANOTHER JS file's OWN declared
    ``module.exports``/``exports.NAME`` names (see
    ``_skel_module_exports_names``) -- used to read CodeWeaver's OWN target
    entry file's exports as an ADDITIONAL, purely ADDITIVE safe-resolution
    signal (see this section's module docstring, resolution rule (d)).
    Never raises and never treats absence as an error: if tree-sitter/
    tree-sitter-javascript are unavailable, ``js_path`` does not exist, or
    it fails to parse, this simply returns an EMPTY frozenset (no
    additional target-bound identifiers recognized) -- identical to this
    adapter's behavior before rule (d) existed, so a missing/unparseable
    target entry file can only ever make extraction fall back to being
    exactly as conservative as before, never crash, and never itself claim
    a build failure (``skel_validated_tests_eval``'s own later
    ``target_dir.exists()`` check and the harness's own
    ``__targetLoadError`` guard remain solely responsible for reporting
    that honestly)."""
    if not js_path.is_file():
        return frozenset()
    parser = _skel_js_parser()
    if parser is None:
        return frozenset()
    try:
        src = js_path.read_bytes()
        tree = parser.parse(src)
        return frozenset(_skel_module_exports_names(tree.root_node, src))
    except Exception:  # noqa: BLE001 - a broken/unreadable target file must not crash collection
        return frozenset()


def _suppress_skel_top_level_test_calls(js_path: Path) -> None:
    """Remove evaluator-only top-level ``test*()`` invocations.

    CodeWeaver targets commonly end with a translated-suite orchestrator such
    as ``test();``. Importing that module from an independent oracle would
    otherwise execute CodeWeaver's own translated tests as an uncounted side
    effect and contaminate both validation and coverage.
    """
    parser = _skel_js_parser()
    if parser is None or not js_path.is_file():
        return
    try:
        source = js_path.read_bytes()
        tree = parser.parse(source)
    except (OSError, ValueError):
        return
    ranges: list[tuple[int, int]] = []
    for statement in tree.root_node.named_children:
        if statement.type != "expression_statement" or not statement.named_children:
            continue
        expression = statement.named_children[0]
        if expression.type != "call_expression":
            continue
        function = expression.child_by_field_name("function")
        if function is None or function.type != "identifier":
            continue
        name = source[function.start_byte:function.end_byte].decode(
            "utf-8", "replace"
        )
        if name.lower().startswith("test"):
            ranges.append((statement.start_byte, statement.end_byte))
    if not ranges:
        return
    rewritten = bytearray(source)
    for start, end in ranges:
        for index in range(start, end):
            if rewritten[index] not in (10, 13):
                rewritten[index] = 32
    js_path.write_bytes(rewritten)


def _mark_skel_test_functions_ignored_for_coverage(js_path: Path) -> None:
    """Keep evaluator-callable test functions while excluding their own
    bodies from the production-line coverage denominator."""
    parser = _skel_js_parser()
    if parser is None or not js_path.is_file():
        return
    try:
        source = js_path.read_bytes()
        tree = parser.parse(source)
    except (OSError, ValueError):
        return
    ranges: list[tuple[int, int]] = []
    for node in tree.root_node.named_children:
        if node.type not in {
            "function_declaration", "generator_function_declaration",
        }:
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            continue
        name = source[name_node.start_byte:name_node.end_byte].decode(
            "utf-8", "replace"
        )
        if name.lower().startswith("test"):
            ranges.append((node.start_byte, node.end_byte))
    if not ranges:
        return
    rewritten = bytearray(source)
    for start, end in sorted(ranges, reverse=True):
        rewritten[end:end] = b"\n/* c8 ignore stop */"
        rewritten[start:start] = b"/* c8 ignore start */\n"
    js_path.write_bytes(rewritten)


def _instrument_skel_target_exports(js_path: Path, requested_names: set[str]) -> None:
    """Expose existing CodeWeaver declarations in an evaluator-only copy."""
    _suppress_skel_top_level_test_calls(js_path)
    bindable = set(_skel_target_bindable_names(js_path))
    already_exported = set(_skel_read_module_export_names(js_path))
    names = sorted(requested_names & bindable - already_exported)
    if not names:
        return
    text = js_path.read_text(encoding="utf-8")
    package_type_module = False
    package_path = js_path.parent / "package.json"
    if package_path.is_file():
        try:
            package_type_module = json.loads(package_path.read_text(encoding="utf-8")).get("type") == "module"
        except (OSError, json.JSONDecodeError):
            package_type_module = False
    esm_syntax = bool(re.search(r"(?m)^\s*(?:import\s|export\s)", text))
    if package_type_module or esm_syntax:
        addition = f"\nexport {{ {', '.join(names)} }};\n"
    else:
        properties = ", ".join(names)
        addition = f"\nmodule.exports = Object.assign(module.exports || {{}}, {{ {properties} }});\n"
    js_path.write_text(text + addition, encoding="utf-8")


# Node types representing a JS expression PROVABLY free of any identifier
# reference, function call, or other side effect -- i.e. pure, self-
# contained DATA. See ``_skel_is_pure_literal_expression``.
_PURE_LITERAL_LEAF_TYPES = ("number", "string", "true", "false", "null", "template_string")


def _skel_is_pure_literal_expression(node: Any) -> bool:
    """True iff ``node`` is a JS expression containing PROVABLY zero
    identifier references, function/method calls, or other executable
    logic -- a bare literal, or an array/object built ONLY from other such
    pure literals with plain (non-computed, non-spread, non-method,
    non-shorthand) properties. Used only to let a verified test safely
    reference a top-level "literal-expectation" ``const`` in source.js
    (e.g. ``const EXPECTED = [1, 2, 3];``) VERBATIM, without requiring
    anything from CodeWeaver's OWN target: copying pure DATA can never leak
    reference IMPLEMENTATION logic (by construction it contains no
    reference to anything else at all), unlike a helper FUNCTION
    (deliberately still never extracted -- see this section's module
    docstring)."""
    if node is None:
        return False
    if node.type in _PURE_LITERAL_LEAF_TYPES:
        if node.type == "template_string":
            return not any(c.type == "template_substitution" for c in node.children)
        return True
    if node.type == "parenthesized_expression":
        inner = [c for c in node.children if c.is_named]
        return len(inner) == 1 and _skel_is_pure_literal_expression(inner[0])
    if node.type == "unary_expression":
        # Any unary operator (``-``/``+``/``void``/``typeof``/...) applied
        # DIRECTLY to a bare number literal (e.g. ``-5``) is itself always
        # side-effect-free and reference-free, regardless of which operator.
        arg = node.child_by_field_name("argument")
        return arg is not None and arg.type == "number"
    if node.type == "array":
        return all(_skel_is_pure_literal_expression(c) for c in node.children if c.is_named)
    if node.type == "object":
        for prop in node.children:
            if not prop.is_named:
                continue
            if prop.type != "pair":
                return False   # shorthand/spread/method/computed properties are never "pure"
            key = prop.child_by_field_name("key")
            value = prop.child_by_field_name("value")
            if key is None or value is None or key.type not in ("property_identifier", "string", "number"):
                return False
            if not _skel_is_pure_literal_expression(value):
                return False
        return True
    return False


def _skel_top_level_literal_declarations(root: Any, src: bytes) -> dict[str, tuple[Any, Any]]:
    """Maps every top-level ``const``/``let``/``var NAME = <pure literal>;``
    declaration NAME (see ``_skel_is_pure_literal_expression``) to its own
    ``(declarator_node, enclosing_statement_node)`` pair -- restricted to a
    statement with EXACTLY ONE declarator, so that statement's own full
    verbatim text corresponds unambiguously to just this one name (a
    multi-declarator statement mixing a pure literal with a non-literal
    sibling, e.g. ``const a = 1, b = someCall();``, is excluded ENTIRELY --
    copying the whole statement text for ``a`` would otherwise also copy
    ``b``'s own non-literal/non-pure initializer). Used only to let a
    verified test safely reference a source.js "literal-expectation"
    constant without requiring anything from CodeWeaver's OWN target."""
    out: dict[str, tuple[Any, Any]] = {}
    for child in root.children:
        statement = child
        if child.type == "export_statement":
            child = next(
                (node for node in child.children if node.type in (
                    "lexical_declaration", "variable_declaration",
                )),
                child,
            )
            statement = child
        if child.type not in ("lexical_declaration", "variable_declaration"):
            continue
        declarators = [c for c in child.children if c.type == "variable_declarator"]
        if len(declarators) != 1:
            continue
        decl = declarators[0]
        name_node = decl.child_by_field_name("name")
        value_node = decl.child_by_field_name("value")
        if name_node is None or value_node is None or name_node.type != "identifier":
            continue
        if not _skel_is_pure_literal_expression(value_node):
            continue
        name = src[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace")
        out[name] = (decl, statement)
    return out


def _skel_safe_node_core_requires(root: Any, src: bytes) -> dict[str, str]:
    """Top-level ``const NAME = require("MODULE")`` bindings in source.js
    where MODULE is in ``SKEL_SAFE_NODE_CORE_MODULES`` -- e.g. real rbt
    fixtures' own ``const assert = require('assert');``. Returns
    ``{NAME: MODULE}``. Node's OWN standard library, never the reference's
    translated implementation, so an identical require() in the synthetic
    harness brings in no reference logic."""
    out: dict[str, str] = {}
    for child in root.children:
        if child.type not in ("lexical_declaration", "variable_declaration"):
            continue
        for decl in child.children:
            if decl.type != "variable_declarator":
                continue
            name_node = decl.child_by_field_name("name")
            value_node = decl.child_by_field_name("value")
            if name_node is None or value_node is None or name_node.type != "identifier":
                continue
            if value_node.type != "call_expression":
                continue
            fn = value_node.child_by_field_name("function")
            args = value_node.child_by_field_name("arguments")
            if fn is None or args is None:
                continue
            if src[fn.start_byte:fn.end_byte].decode("utf-8", "replace") != "require":
                continue
            string_args = [c for c in args.children if c.type == "string"]
            if len(string_args) != 1:
                continue
            module_name = src[string_args[0].start_byte:string_args[0].end_byte].decode(
                "utf-8", "replace").strip("'\"")
            if module_name in SKEL_SAFE_NODE_CORE_MODULES:
                out[src[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace")] = module_name
    return out


def _skel_local_literal_imports(
    root: Any,
    src: bytes,
    *,
    source_dir: Path,
) -> dict[str, str]:
    """Resolve local-module bindings only to their pure literal exports."""
    parser = _skel_js_parser()
    if parser is None:
        return {}
    resolved: dict[str, str] = {}
    object_values: dict[str, dict[str, str]] = {}

    def module_literal_values(module_name: str) -> dict[str, str]:
        if not module_name.startswith("./") or ".." in Path(module_name).parts:
            return {}
        module_path = source_dir / module_name
        if module_path.suffix == "":
            module_path = module_path.with_suffix(".js")
        try:
            module_src = module_path.read_bytes()
            module_root = parser.parse(module_src).root_node
        except OSError:
            return {}
        literal_decls = _skel_top_level_literal_declarations(module_root, module_src)
        exported = _skel_module_exports_names(module_root, module_src)
        return {
            name: module_src[value.start_byte:value.end_byte].decode("utf-8", "replace")
            for name, (decl, _statement) in literal_decls.items()
            if (
                name in exported
                and (value := decl.child_by_field_name("value")) is not None
            )
        }

    for child in root.children:
        if child.type not in ("lexical_declaration", "variable_declaration"):
            continue
        for decl in child.children:
            if decl.type != "variable_declarator":
                continue
            name_node = decl.child_by_field_name("name")
            value_node = decl.child_by_field_name("value")
            if name_node is None or value_node is None:
                continue
            if value_node.type != "call_expression":
                continue
            fn = value_node.child_by_field_name("function")
            args = value_node.child_by_field_name("arguments")
            if fn is None or args is None:
                continue
            if src[fn.start_byte:fn.end_byte].decode("utf-8", "replace") != "require":
                continue
            string_args = [item for item in args.children if item.type == "string"]
            if len(string_args) != 1:
                continue
            module_name = src[string_args[0].start_byte:string_args[0].end_byte].decode(
                "utf-8", "replace",
            ).strip("'\"")
            values = module_literal_values(module_name)
            if name_node.type == "object_pattern":
                requested: set[str] = set()
                _skel_collect_pattern_identifiers(name_node, src, requested)
                if requested and requested.issubset(values):
                    for name in requested:
                        resolved[name] = f"const {name} = {values[name]};"
            elif name_node.type == "identifier" and values:
                local_name = src[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace")
                object_values[local_name] = values
                properties = ", ".join(
                    f"{json.dumps(name)}: ({value})"
                    for name, value in sorted(values.items())
                )
                resolved[local_name] = f"const {local_name} = {{ {properties} }};"

    for child in root.children:
        if child.type != "import_statement":
            continue
        namespace = next(
            (node for node in _walk_nodes(child) if node.type == "namespace_import"),
            None,
        )
        module_node = next(
            (node for node in child.children if node.type == "string"),
            None,
        )
        if namespace is None or module_node is None:
            continue
        identifier = next(
            (node for node in namespace.children if node.type == "identifier"),
            None,
        )
        if identifier is None:
            continue
        local_name = src[identifier.start_byte:identifier.end_byte].decode("utf-8", "replace")
        module_name = src[module_node.start_byte:module_node.end_byte].decode(
            "utf-8", "replace",
        ).strip("'\"")
        values = module_literal_values(module_name)
        if not values:
            continue
        object_values[local_name] = values
        properties = ", ".join(
            f"{json.dumps(name)}: ({value})"
            for name, value in sorted(values.items())
        )
        resolved[local_name] = f"const {local_name} = {{ {properties} }};"

    # Resolve source.js aliases such as
    # ``_example_html = tool_functions._example_html`` to the helper's pure
    # literal value, without copying the helper module or any executable API.
    for child in root.children:
        if child.type != "expression_statement" or not child.children:
            continue
        expression = child.children[0]
        if expression.type != "assignment_expression":
            continue
        left = expression.child_by_field_name("left")
        right = expression.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier" or right.type != "member_expression":
            continue
        obj = right.child_by_field_name("object")
        prop = right.child_by_field_name("property")
        if obj is None or prop is None:
            continue
        object_name = src[obj.start_byte:obj.end_byte].decode("utf-8", "replace")
        property_name = src[prop.start_byte:prop.end_byte].decode("utf-8", "replace")
        value = object_values.get(object_name, {}).get(property_name)
        if value is not None:
            alias = src[left.start_byte:left.end_byte].decode("utf-8", "replace")
            resolved[alias] = f"const {alias} = {value};"
    return resolved


def skel_extract_verified_tests(
    source_js_path: Path, verified_names: list[str], *, target_export_names: frozenset[str] = frozenset(),
) -> SkelExtractionOutcome | None:
    """Statically classifies every CSV-listed SKEL test name against
    ``<ref_project_dir>/javascript/source.js`` -- see this section's leading
    module comment for the full extraction/blocking rule set. Returns None
    (never raises) if ``tree-sitter``/``tree-sitter-javascript`` are not
    importable or ``source.js`` cannot be read/parsed, so callers can report
    ``Status.UNAVAILABLE`` with an explicit reason. ``target_export_names``
    (see ``_skel_read_module_export_names``) is CodeWeaver's OWN target
    entry file's independently-declared export names -- an OPTIONAL,
    purely ADDITIVE signal (defaults to empty, identical to this function's
    behavior before resolution rule (d) existed) that can only ever WIDEN
    which source.js top-level production declarations a listed test may
    bind against, never narrow it."""
    parser = _skel_js_parser()
    if parser is None:
        return None
    if not source_js_path.is_file():
        return None
    try:
        src = source_js_path.read_bytes()
        tree = parser.parse(src)
    except Exception:  # noqa: BLE001 - a parser/runtime error must not crash collection
        return None
    root = tree.root_node
    top_level = _skel_top_level_declarations(root, src)
    exported = _skel_module_exports_names(root, src)
    safe_requires = _skel_safe_node_core_requires(root, src)
    literal_decls = _skel_top_level_literal_declarations(root, src)
    literal_texts = {n: src[stmt.start_byte:stmt.end_byte].decode("utf-8", "replace")
                    for n, (_decl, stmt) in literal_decls.items()}
    literal_texts.update(
        _skel_local_literal_imports(root, src, source_dir=source_js_path.parent)
    )
    project = source_js_path.parent.parent.name
    allowed_support = SKEL_SAFE_TEST_SUPPORT_FUNCTIONS.get(project, frozenset())
    support_cache: dict[
        str, tuple[bool, set[str], set[str], set[str], set[str], str]
    ] = {}

    def resolve_support(
        support_name: str,
        stack: frozenset[str] = frozenset(),
    ) -> tuple[bool, set[str], set[str], set[str], set[str], str]:
        if support_name in support_cache:
            return support_cache[support_name]
        if support_name in stack:
            return False, set(), set(), set(), set(), "cyclic test-support dependency"
        node = top_level.get(support_name)
        if support_name not in allowed_support or node is None:
            return False, set(), set(), set(), set(), "not an allowlisted test-support helper"
        targets: set[str] = set()
        literals: set[str] = set()
        requires: set[str] = set()
        supports = {support_name}
        unresolved: list[str] = []
        try:
            dependencies = _skel_collect_free_identifiers(node, src)
        except Exception as exc:  # noqa: BLE001 - explicit blocked result
            return False, set(), set(), set(), set(), f"AST analysis failed: {exc!r}"
        for identifier in sorted(dependencies):
            if identifier == support_name or identifier in SKEL_JS_GLOBAL_BUILTINS:
                continue
            if identifier in safe_requires:
                requires.add(identifier)
            elif identifier in exported:
                targets.add(identifier)
            elif identifier in top_level and identifier in target_export_names:
                targets.add(identifier)
            elif identifier in literal_texts:
                literals.add(identifier)
            elif identifier in allowed_support:
                nested = resolve_support(identifier, stack | {support_name})
                if not nested[0]:
                    unresolved.append(f"{identifier} ({nested[5]})")
                else:
                    targets.update(nested[1])
                    literals.update(nested[2])
                    requires.update(nested[3])
                    supports.update(nested[4])
            else:
                unresolved.append(identifier)
        result = (
            not unresolved,
            targets,
            literals,
            requires,
            supports,
            f"unresolved dependency/dependencies: {unresolved}" if unresolved else "",
        )
        support_cache[support_name] = result
        return result

    extractable: list[SkelExtractedTest] = []
    blocked: list[tuple[str, str]] = []
    used_require_names: set[str] = set()
    used_literal_names: set[str] = set()
    used_support_names: set[str] = set()
    for name in verified_names:
        node = top_level.get(name)
        declaration_name = name
        if node is None:
            normalized_matches = [
                candidate
                for candidate in top_level
                if _normalize_identifier_for_matching(candidate)
                == _normalize_identifier_for_matching(name)
            ]
            if len(normalized_matches) == 1:
                declaration_name = normalized_matches[0]
                node = top_level[declaration_name]
        if node is None:
            blocked.append((
                name,
                f"no matching top-level function/class declaration for javascript test name {name!r} "
                "was found in source.js",
            ))
            continue
        try:
            free = _skel_collect_free_identifiers(node, src)
        except Exception as e:  # noqa: BLE001 - one malformed test must not abort the whole project
            blocked.append((name, f"AST analysis of this test's body failed: {e!r}"))
            continue
        target_identifiers: list[str] = []
        literal_support: list[str] = []
        local_requires: set[str] = set()
        local_supports: set[str] = set()
        unresolved: list[str] = []
        for identifier in sorted(free):
            if identifier == declaration_name:
                continue
            if identifier in SKEL_JS_GLOBAL_BUILTINS:
                continue
            if identifier in safe_requires:
                local_requires.add(identifier)
                continue
            if identifier in exported:
                target_identifiers.append(identifier)
                continue
            # Resolution rule (d): a source.js top-level production
            # declaration NOT itself in source.js's own module.exports, but
            # which CodeWeaver's OWN target independently ALSO exports
            # under the same name -- see this section's module docstring.
            if identifier in top_level and identifier in target_export_names:
                target_identifiers.append(identifier)
                continue
            # Resolution rule (e): a provably pure "literal-expectation"
            # constant -- spliced verbatim, never target-bound.
            if identifier in literal_texts:
                literal_support.append(identifier)
                continue
            if identifier in allowed_support:
                support = resolve_support(identifier)
                if support[0]:
                    target_identifiers.extend(support[1])
                    literal_support.extend(support[2])
                    local_requires.update(support[3])
                    local_supports.update(support[4])
                else:
                    unresolved.append(f"{identifier} ({support[5]})")
                continue
            unresolved.append(identifier)
        if unresolved:
            blocked.append((
                name,
                f"references identifier(s) {unresolved} that are private/non-exported declarations in "
                "source.js (or otherwise unresolvable) -- extracting this test would require bringing in "
                "reference implementation/scaffolding code, which this adapter refuses to do",
            ))
            continue
        used_require_names.update(local_requires)
        used_literal_names.update(literal_support)
        used_support_names.update(local_supports)
        extractable.append(SkelExtractedTest(
            name=declaration_name,
            source_text=src[node.start_byte:node.end_byte].decode("utf-8", "replace"),
            target_identifiers=tuple(sorted(set(target_identifiers))),
            literal_support_names=tuple(sorted(set(literal_support))),
        ))
    require_lines = tuple(
        f'const {local_name} = require({json.dumps(safe_requires[local_name])});'
        for local_name in sorted(used_require_names)
    )
    literal_support_lines = tuple(literal_texts[n] for n in sorted(used_literal_names))
    test_support_lines = tuple(
        src[top_level[name].start_byte:top_level[name].end_byte].decode("utf-8", "replace")
        for name in sorted(used_support_names)
    )
    return SkelExtractionOutcome(
        extractable=extractable,
        blocked=blocked,
        safe_require_lines=require_lines,
        literal_support_lines=literal_support_lines,
        test_support_lines=test_support_lines,
    )


def skel_build_validated_harness_source(outcome: SkelExtractionOutcome) -> str:
    """Assembles a single, self-contained Node.js harness source file
    containing ONLY: (1) a guarded ``require()`` of CodeWeaver's OWN target
    entry file (``SKEL_TARGET_ENTRY_FILENAME``) -- a load failure (missing
    file, syntax error, ...) is caught so it shows up as an honest per-test
    FAIL rather than crashing the whole harness process before any summary
    is printed; (2) a destructuring of exactly the target-facing identifiers
    the extractable tests need; (3) any safe Node-core re-export lines; (4)
    any "literal-expectation" support declarations (verbatim, pure-data
    only -- see ``SkelExtractionOutcome.literal_support_lines``); (5) a
    ``console.assert`` monkeypatch (Node's OWN ``console.assert`` does NOT
    throw or affect the exit code on a falsy condition -- without this, a
    source-faithful ``console.assert(...)`` inside an extracted test would
    silently no-op instead of failing the test); and (6) the extracted
    tests' own verbatim source text, run in a loop that treats a thrown
    exception OR an explicit ``=== false`` return value as FAIL (some real
    verified tests, e.g. rbt fixtures, signal failure only via their own
    return value, never a throw), printing a ``# pass N`` / ``# fail M``
    TAP-style summary line ``parse_node_tap_output`` already recognizes.
    Never references or embeds any of source.js's own implementation text
    (production helper FUNCTION bodies are never copied -- see this
    section's module docstring)."""
    target_identifiers: set[str] = set()
    for test in outcome.extractable:
        target_identifiers.update(test.target_identifiers)
    lines: list[str] = [
        '"use strict";',
        'import { createRequire as __createRequire } from "node:module";',
        "const require = __createRequire(import.meta.url);",
        "// Auto-generated by CodeWeaver's ReCodeAgent harness.",
        "// Contains ONLY AST-extracted validated test function bodies listed",
        "// by test_name_mapping.csv -- never the",
        "// reference's source.js implementation or any of its private helpers.",
        "function __describeError(e) { return (e && e.message) ? e.message : String(e); }",
        "let __target = {};",
        "let __targetLoadError = null;",
        "try {",
        f'  const __loadedTarget = await import("./{SKEL_TARGET_ENTRY_FILENAME}");',
        "  const __defaultTarget = (__loadedTarget.default && typeof __loadedTarget.default === 'object')",
        "    ? __loadedTarget.default : {};",
        "  __target = { ...__defaultTarget, ...__loadedTarget };",
        "} catch (e) {",
        "  __targetLoadError = e;",
        "}",
        "if (!__target || typeof __target !== 'object') { __target = {}; }",
    ]
    if target_identifiers:
        destructure = ", ".join(sorted(target_identifiers))
        lines.append(f"const {{ {destructure} }} = __target;")
    lines.extend(outcome.safe_require_lines)
    lines.extend(outcome.literal_support_lines)
    lines.extend(outcome.test_support_lines)
    lines.extend([
        "console.assert = function (condition) {",
        "  if (!condition) {",
        "    const rest = Array.prototype.slice.call(arguments, 1);",
        "    throw new Error('console.assert failed' + (rest.length ? ': ' + rest.map(String).join(' ') : ''));",
        "  }",
        "};",
        "",
    ])
    for test in outcome.extractable:
        lines.append(test.source_text)
        lines.append("")
    entries = ", ".join(f"[{json.dumps(t.name)}, {t.name}]" for t in outcome.extractable)
    lines.extend([
        f"const __tests = [{entries}];",
        "let __passed = 0;",
        "let __failed = 0;",
        "for (const __entry of __tests) {",
        "  const __name = __entry[0];",
        "  const __fn = __entry[1];",
        "  try {",
        "    if (__targetLoadError) {",
        "      throw new Error('target module failed to load: ' + __describeError(__targetLoadError));",
        "    }",
        "    const __result = __fn();",
        "    if (__result === false) {",
        "      __failed += 1;",
        "      console.log('FAIL ' + __name + ': test function returned false');",
        "    } else {",
        "      __passed += 1;",
        "      console.log('PASS ' + __name);",
        "    }",
        "  } catch (__err) {",
        "    __failed += 1;",
        "    console.log('FAIL ' + __name + ': ' + __describeError(__err));",
        "  }",
        "}",
        "console.log('# pass ' + __passed);",
        "console.log('# fail ' + __failed);",
    ])
    return "\n".join(lines) + "\n"


def skel_validated_tests_eval(
    target_dir: Path, ref_project_dir: Path | None, *, timeout: float | None,
    runner: CommandRunner = default_command_runner, node_cmd: str = "node",
) -> dict[str, Measurement]:
    """SKEL's independently validated developer tests -- see this section's
    leading module comment for the full extraction/aggregation rationale.
    Returns ``Status.UNAVAILABLE`` (never a fabricated ``0``) if:
    ``ref_project_dir`` is None (no ``--reference-results-root``, or this
    project is absent from the reference tree), ``test_name_mapping.csv``/
    ``javascript/source.js`` cannot be resolved, ``tree-sitter``/
    ``tree-sitter-javascript`` are not installed, or every CSV-listed test
    name was blocked from extraction. If the CSV itself lists zero tests,
    that is a real ``Status.MEASURED`` zero, not unavailable.
    ``expected`` (see ``_finalize_validated_tests``) is ``len(validated_names)``
    -- the CSV's own fixed, oracle-known denominator -- computed as soon as
    the CSV parses, so it stays measured even when a LATER step (tree-sitter
    missing, extraction blocked, target build failure) prevents any test
    from actually executing."""
    if ref_project_dir is None:
        unavailable = Measurement.unavailable(
            "no reference project directory resolved under --reference-results-root for this project "
            "(missing --reference-results-root, or this project is absent from the reference tree)"
        )
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         unavailable)
    csv_path = ref_project_dir / "test_name_mapping.csv"
    validated_names = skel_parse_validated_test_names(csv_path)
    if validated_names is None:
        unavailable = Measurement.unavailable(
            f"{csv_path.name} not found under the reference project directory, unreadable, or missing the "
            "expected 'javascript test name' column"
        )
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         unavailable)
    expected = paper_runtime_tests_expected(
        "skel", ref_project_dir.name, Measurement.ok(len(validated_names)),
        official_artifact_verified=(ref_project_dir / "test_comparison_report.json").is_file(),
    )
    if not validated_names:
        zero = Measurement.ok(0)
        return _finalize_validated_tests({"total": zero, "passed": zero, "failed": zero}, expected)
    javascript_dir = skel_reference_javascript_dir(ref_project_dir)
    source_js = javascript_dir / "source.js" if javascript_dir is not None else None
    if source_js is None or not source_js.is_file():
        unavailable = Measurement.unavailable("javascript/source.js not found under the reference project directory")
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         expected)
    # Resolution rule (d) (see this section's module docstring): a
    # best-effort, purely ADDITIVE listing of CodeWeaver's OWN target
    # entry file's own declared exports. `target_dir` may not exist yet at
    # this point (checked further below) -- `_skel_read_module_export_names`
    # degrades gracefully (empty set) in that case, so this call is always
    # safe regardless of ordering.
    target_export_names = _skel_target_bindable_names(target_dir / SKEL_TARGET_ENTRY_FILENAME)
    outcome = skel_extract_verified_tests(source_js, validated_names, target_export_names=target_export_names)
    if outcome is None:
        unavailable = Measurement.unavailable(
            "tree-sitter/tree-sitter-javascript are not installed, or javascript/source.js could not be "
            "read/parsed -- AST extraction of validated tests is unavailable"
        )
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         expected)
    if not outcome.extractable:
        reasons = "; ".join(f"{n}: {r}" for n, r in outcome.blocked[:5])
        more = "" if len(outcome.blocked) <= 5 else f" (+{len(outcome.blocked) - 5} more)"
        unavailable = Measurement.unavailable(
            f"all {len(outcome.blocked)} CSV-listed test(s) were blocked from AST extraction: {reasons}{more}"
        )
        return _finalize_validated_tests({"total": unavailable, "passed": unavailable, "failed": unavailable},
                                         expected)
    if not target_dir.exists():
        missing = Measurement.missing("target tree does not exist (nothing was produced)")
        return _finalize_validated_tests({"total": missing, "passed": missing, "failed": missing}, expected)
    harness_source = skel_build_validated_harness_source(outcome)
    with tempfile.TemporaryDirectory(prefix="recodeagent_skel_validated_") as tmp:
        tmp_target = Path(tmp) / "target"
        copy_evaluation_tree(target_dir, tmp_target)
        required_target_names = {
            identifier
            for test in outcome.extractable
            for identifier in test.target_identifiers
        }
        _instrument_skel_target_exports(
            tmp_target / SKEL_TARGET_ENTRY_FILENAME, required_target_names,
        )
        (tmp_target / SKEL_VALIDATED_HARNESS_FILENAME).write_text(harness_source, encoding="utf-8")
        result = evaluate_tests(
            tmp_target, [node_cmd, SKEL_VALIDATED_HARNESS_FILENAME], "skel", timeout=timeout,
            dataset_spec={"test_output_format": "node_tap"}, runner=runner,
        )
    if outcome.blocked and result["total"].is_measured:
        reasons = "; ".join(f"{n}: {r}" for n, r in outcome.blocked[:5])
        more = "" if len(outcome.blocked) <= 5 else f" (+{len(outcome.blocked) - 5} more)"
        note = (f"{len(outcome.blocked)} of {len(validated_names)} CSV-listed test(s) were not independently "
               f"extractable and excluded from this run: {reasons}{more}")
        result = dict(result)
        result["total"] = Measurement(value=result["total"].value, status=Status.MEASURED, reason=note)
    return _finalize_validated_tests(result, expected)


_SKEL_SOURCE_REQUIRE_RE = re.compile(
    r"""require\(\s*(['"])\./source(?:\.js)?\1\s*\)"""
)


def skel_rewrite_generated_harness_for_coverage(
    source_file: Path,
    *,
    project: str,
) -> tuple[str | None, str]:
    """Rewrite one generated script as ESM while binding to the real index.js."""
    try:
        original = source_file.read_bytes()
    except OSError as exc:
        return None, f"could not read generated harness: {exc}"
    spec = SKEL_INLINE_GENERATED_BINDINGS.get((project, source_file.name))
    rewritten = bytearray(original)
    bindings: list[str] = []
    if spec is not None:
        parser = _skel_js_parser()
        if parser is None:
            return None, "tree-sitter JavaScript parser unavailable for safe inline-implementation removal"
        try:
            tree = parser.parse(original)
            declarations = _skel_top_level_declarations(tree.root_node, original)
        except Exception as exc:  # noqa: BLE001 - explicit unavailable result
            return None, f"could not parse generated harness for safe rewrite: {exc}"
        missing = [name for name in spec["remove"] if name not in declarations]
        if missing:
            return None, f"expected inline implementation declaration(s) not found: {missing}"
        ranges = sorted(
            ((declarations[name].start_byte, declarations[name].end_byte) for name in spec["remove"]),
            reverse=True,
        )
        for start, end in ranges:
            rewritten[start:end] = b""
        aliases = spec.get("aliases") or {}
        bindings.extend(
            f"const {name} = __recodeagentTarget[{json.dumps(name)}];"
            for name in spec["target"]
            if name not in aliases
        )
        bindings.extend(
            f"const {name} = {expression};"
            for name, expression in aliases.items()
        )

    prelude = "\n".join([
        'import { createRequire as __createRequire } from "node:module";',
        'import { fileURLToPath as __fileURLToPath } from "node:url";',
        'import { dirname as __pathDirname } from "node:path";',
        "const require = __createRequire(import.meta.url);",
        "const __filename = __fileURLToPath(import.meta.url);",
        "const __dirname = __pathDirname(__filename);",
        "const module = { exports: {} };",
        "const exports = module.exports;",
        f'const __recodeagentLoaded = await import("./{SKEL_TARGET_ENTRY_FILENAME}");',
        "const __recodeagentDefault = (__recodeagentLoaded.default "
        "&& typeof __recodeagentLoaded.default === 'object') ? __recodeagentLoaded.default : {};",
        "const __recodeagentTarget = { ...__recodeagentDefault, ...__recodeagentLoaded };",
        *bindings,
        "",
    ])
    text = _SKEL_SOURCE_REQUIRE_RE.sub(
        "__recodeagentTarget", rewritten.decode("utf-8", "replace"),
    )
    if text.startswith("#!"):
        first_line, separator, rest = text.partition("\n")
        text = first_line + separator + prelude + rest
    else:
        text = prelude + text
    return text, ""


def _skel_coverage_files(target_dir: Path) -> list[str]:
    return [
        path.relative_to(target_dir).as_posix()
        for path in sorted(target_dir.rglob("*"))
        if (
            path.is_file()
            and path.suffix.lower() in {".js", ".mjs", ".cjs"}
            and "node_modules" not in path.relative_to(target_dir).parts
            and not path.name.startswith("__recodeagent_")
            and not path.name.startswith("__codeweaver_generated_coverage_")
        )
    ]
def skel_paper_coverage_pair(
    target_dir: Path,
    ref_project_dir: Path | None,
    *,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Standardized c8 coverage using the official generated scripts."""
    if ref_project_dir is None or not target_dir.is_dir():
        unavailable = Measurement.unavailable(
            "SKEL coverage requires a CodeWeaver target and official reference project"
        )
        return unavailable, unavailable
    csv_path = ref_project_dir / "test_name_mapping.csv"
    verified_names = skel_parse_validated_test_names(csv_path)
    javascript_dir = skel_reference_javascript_dir(ref_project_dir)
    source_js = javascript_dir / "source.js" if javascript_dir is not None else None
    if verified_names is None or source_js is None or not source_js.is_file():
        unavailable = Measurement.unavailable(
            "SKEL coverage requires test_name_mapping.csv and javascript/source.js"
        )
        return unavailable, unavailable

    target_entry = target_dir / SKEL_TARGET_ENTRY_FILENAME
    export_names = _skel_target_bindable_names(target_entry)
    outcome = skel_extract_verified_tests(
        source_js, verified_names, target_export_names=export_names,
    )
    if outcome is None or not outcome.extractable:
        unavailable = Measurement.unavailable(
            "SKEL developer tests could not be safely AST-extracted for coverage"
        )
        return unavailable, unavailable
    generated_files = skel_function_harness_files(javascript_dir)
    coverage_files = _skel_coverage_files(target_dir)
    coverage_include_args = [f"--include={path}" for path in coverage_files]

    with tempfile.TemporaryDirectory(prefix="recodeagent_skel_coverage_") as tmp:
        root = Path(tmp)
        staged_target = root / "target"
        copy_evaluation_tree(target_dir, staged_target)
        for relative_path in coverage_files:
            _mark_skel_test_functions_ignored_for_coverage(
                staged_target / relative_path
            )
        required_target_names = {
            identifier
            for test in outcome.extractable
            for identifier in test.target_identifiers
        }
        _instrument_skel_target_exports(
            staged_target / SKEL_TARGET_ENTRY_FILENAME, required_target_names,
        )
        developer_harness = staged_target / SKEL_VALIDATED_HARNESS_FILENAME
        developer_harness.write_text(
            skel_build_validated_harness_source(outcome), encoding="utf-8",
        )

        rewrite_errors: list[str] = []
        project = ref_project_dir.name
        staged_generated: list[Path] = []
        for source in generated_files:
            rewritten, error = skel_rewrite_generated_harness_for_coverage(
                source, project=project,
            )
            if rewritten is None:
                rewrite_errors.append(f"{source.name}: {error}")
                continue
            destination = staged_target / f"{source.stem}.mjs"
            destination.write_text(rewritten, encoding="utf-8")
            staged_generated.append(destination)
        if rewrite_errors:
            unavailable = Measurement.unavailable(
                "safe SKEL generated-harness rewrite failed: " + "; ".join(rewrite_errors)
            )
            return unavailable, unavailable

        def run_group(
            label: str, scripts: list[Path],
        ) -> tuple[float | None, list[str]]:
            temp_dir = root / f"c8-{label}-tmp"
            report_dir = root / f"c8-{label}-report"
            errors: list[str] = []
            for index, script in enumerate(scripts):
                result = runner(
                    [
                        "c8", f"--clean={'true' if index == 0 else 'false'}",
                        f"--temp-directory={temp_dir}",
                        "--reporter=json-summary", f"--reports-dir={report_dir}",
                        *coverage_include_args,
                        "node", script.name,
                    ],
                    cwd=staged_target,
                    timeout=timeout,
                )
                if result.timed_out or result.error or result.returncode != 0:
                    detail = "timed out" if result.timed_out else (
                        result.error or _tail(result.stderr) or f"exit code {result.returncode}"
                    )
                    errors.append(f"{script.name}: {detail}")
            summary = report_dir / "coverage-summary.json"
            try:
                text = summary.read_text(encoding="utf-8")
            except OSError:
                return None, errors
            return parse_istanbul_summary_json(text), errors

        before_value, developer_errors = run_group("developer", [developer_harness])
        after_value, combined_errors = run_group(
            "combined", [developer_harness, *staged_generated],
        )
        reason = (
            f"standardized c8 line coverage over {len(outcome.extractable)} safely extracted "
            f"developer test(s) and {len(staged_generated)} official generated script(s)"
        )
        if outcome.blocked:
            reason += f"; {len(outcome.blocked)} developer test(s) were not safely extractable"
        if developer_errors or combined_errors:
            reason += (
                f"; non-zero coverage process(es): developer={developer_errors[:5]}, "
                f"combined={combined_errors[:5]}"
            )
        before = (
            Measurement(value=before_value, status=Status.MEASURED, reason=reason)
            if before_value is not None else
            Measurement.unavailable("c8 produced no developer coverage summary: " + reason)
        )
        after = (
            Measurement(value=after_value, status=Status.MEASURED, reason=reason)
            if after_value is not None else
            Measurement.unavailable("c8 produced no combined coverage summary: " + reason)
        )
        return before, after


def _javascript_module_type(target_dir: Path) -> str:
    package = target_dir / "package.json"
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "commonjs"
    return "module" if data.get("type") == "module" else "commonjs"


def _stage_codeweaver_javascript_coverage_harnesses(
    target_dir: Path,
    generated_tests: list[tuple[str, str]],
) -> tuple[list[Path], list[str]]:
    grouped: dict[str, list[str]] = {}
    for path, name in generated_tests:
        grouped.setdefault(path, []).append(name)
    module_type = _javascript_module_type(target_dir)
    harnesses: list[Path] = []
    blocked: list[str] = []
    for index, (relative_path, names) in enumerate(sorted(grouped.items())):
        invalid = [
            name for name in names
            if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name) is None
        ]
        if invalid:
            blocked.extend(
                f"{relative_path}::{name}: not a callable JavaScript identifier"
                for name in invalid
            )
            names = [name for name in names if name not in invalid]
        if not names:
            continue
        test_file = target_dir / relative_path
        _suppress_skel_top_level_test_calls(test_file)
        try:
            source = test_file.read_text(encoding="utf-8")
        except OSError as exc:
            blocked.append(f"{relative_path}: {exc}")
            continue
        aliases = [
            f"__codeweaver_generated_coverage_{index}_{item_index}"
            for item_index in range(len(names))
        ]
        if module_type == "module" or re.search(
            r"(?m)^\s*(?:import\s|export\s)", source
        ):
            exports = ", ".join(
                f"{name} as {alias}" for name, alias in zip(names, aliases)
            )
            source += f"\nexport {{ {exports} }};\n"
        else:
            source += "\n" + "\n".join(
                f"module.exports[{json.dumps(alias)}] = {name};"
                for name, alias in zip(names, aliases)
            ) + "\n"
        test_file.write_text(source, encoding="utf-8")

        harness = target_dir / f"__codeweaver_generated_coverage_{index}.mjs"
        entries = ", ".join(
            f"[{json.dumps(name)}, {json.dumps(alias)}]"
            for name, alias in zip(names, aliases)
        )
        import_path = "./" + Path(relative_path).as_posix()
        harness.write_text(
            "\n".join([
                f"const loaded = await import({json.dumps(import_path)});",
                "const target = { ...(loaded.default || {}), ...loaded };",
                f"const tests = [{entries}];",
                "for (const [name, alias] of tests) {",
                "  try {",
                "    const fn = target[alias];",
                "    if (typeof fn !== 'function') throw new Error('test function not exported');",
                "    await fn();",
                "  } catch (error) {",
                "    console.log('FAIL ' + name + ': ' + (error && error.message || error));",
                "  }",
                "}",
            ]) + "\n",
            encoding="utf-8",
        )
        harnesses.append(harness)
    return harnesses, blocked


def skel_codeweaver_coverage_pair(
    target_dir: Path,
    ref_project_dir: Path | None,
    generated_tests: list[tuple[str, str]],
    *,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Coverage from safely extracted developer tests plus only classified
    CodeWeaver-authored JavaScript tests."""
    if ref_project_dir is None or not target_dir.is_dir():
        unavailable = Measurement.unavailable(
            "SKEL CodeWeaver coverage requires a target and official reference project"
        )
        return unavailable, unavailable
    verified_names = skel_parse_validated_test_names(
        ref_project_dir / "test_name_mapping.csv"
    )
    javascript_dir = skel_reference_javascript_dir(ref_project_dir)
    source_js = javascript_dir / "source.js" if javascript_dir is not None else None
    if verified_names is None or source_js is None or not source_js.is_file():
        unavailable = Measurement.unavailable(
            "SKEL CodeWeaver coverage requires test_name_mapping.csv and javascript/source.js"
        )
        return unavailable, unavailable

    export_names = _skel_target_bindable_names(
        target_dir / SKEL_TARGET_ENTRY_FILENAME
    )
    outcome = skel_extract_verified_tests(
        source_js,
        verified_names,
        target_export_names=export_names,
    )
    if outcome is None or not outcome.extractable:
        unavailable = Measurement.unavailable(
            "SKEL developer tests could not be safely AST-extracted for coverage"
        )
        return unavailable, unavailable
    coverage_files = _skel_coverage_files(target_dir)
    coverage_include_args = [f"--include={path}" for path in coverage_files]

    with tempfile.TemporaryDirectory(
        prefix="recodeagent_skel_codeweaver_coverage_"
    ) as tmp:
        root = Path(tmp)
        staged_target = root / "target"
        copy_evaluation_tree(target_dir, staged_target)
        required_target_names = {
            identifier
            for test in outcome.extractable
            for identifier in test.target_identifiers
        }
        _instrument_skel_target_exports(
            staged_target / SKEL_TARGET_ENTRY_FILENAME,
            required_target_names,
        )
        developer_harness = staged_target / SKEL_VALIDATED_HARNESS_FILENAME
        developer_harness.write_text(
            skel_build_validated_harness_source(outcome),
            encoding="utf-8",
        )
        generated_harnesses, blocked = (
            _stage_codeweaver_javascript_coverage_harnesses(
                staged_target,
                generated_tests,
            )
        )
        for relative_path in coverage_files:
            _mark_skel_test_functions_ignored_for_coverage(
                staged_target / relative_path
            )

        def run_group(
            label: str,
            scripts: list[Path],
        ) -> tuple[float | None, list[str]]:
            temp_dir = root / f"c8-codeweaver-{label}-tmp"
            report_dir = root / f"c8-codeweaver-{label}-report"
            errors: list[str] = []
            for index, script in enumerate(scripts):
                result = runner(
                    [
                        "c8", f"--clean={'true' if index == 0 else 'false'}",
                        f"--temp-directory={temp_dir}",
                        "--reporter=json-summary",
                        f"--reports-dir={report_dir}",
                        *coverage_include_args,
                        "node", script.name,
                    ],
                    cwd=staged_target,
                    timeout=timeout,
                )
                if result.timed_out or result.error:
                    errors.append(
                        f"{script.name}: "
                        + ("timed out" if result.timed_out else result.error)
                    )
            summary = report_dir / "coverage-summary.json"
            try:
                text = summary.read_text(encoding="utf-8")
            except OSError:
                return None, errors
            return parse_istanbul_summary_json(text), errors

        before_value, before_errors = run_group(
            "developer", [developer_harness],
        )
        after_value, after_errors = run_group(
            "combined", [developer_harness, *generated_harnesses],
        )
        reason = (
            "paper-equivalent c8 line coverage over "
            f"{len(outcome.extractable)} safely extracted developer test(s) and "
            f"{len(generated_tests)} classified CodeWeaver-authored generated test(s)"
        )
        if outcome.blocked:
            reason += (
                f"; {len(outcome.blocked)} developer test(s) were not safely extractable"
            )
        if blocked:
            reason += f"; blocked generated selectors={blocked[:10]}"
        if before_errors or after_errors:
            reason += (
                f"; coverage process errors: developer={before_errors[:5]}, "
                f"combined={after_errors[:5]}"
            )
        before = (
            Measurement(value=before_value, status=Status.MEASURED, reason=reason)
            if before_value is not None else
            Measurement.unavailable(
                "c8 produced no developer coverage summary: " + reason
            )
        )
        after = (
            Measurement(value=after_value, status=Status.MEASURED, reason=reason)
            if after_value is not None else
            Measurement.unavailable(
                "c8 produced no combined coverage summary: " + reason
            )
        )
        return before, after


def codeweaver_generated_coverage_pair(
    tool: str,
    target_dir: Path,
    generated_tests: list[tuple[str, str]],
    *,
    ref_project_dir: Path | None = None,
    scaffold_dir: Path | None = None,
    name_mapping: Mapping[str, str] | None = None,
    timeout: float | None,
    runner: CommandRunner = default_command_runner,
) -> tuple[Measurement, Measurement]:
    """Dispatch the paper-equivalent developer-plus-CodeWeaver coverage
    adapter after generated-test classification."""
    if tool == "crust":
        if scaffold_dir is None:
            unavailable = Measurement.unavailable(
                "CRUST CodeWeaver coverage requires the pristine scaffold"
            )
            return unavailable, unavailable
        return crust_paper_coverage_pair(
            target_dir,
            scaffold_dir,
            timeout=timeout,
            runner=runner,
            generated_tests=generated_tests,
        )
    if tool == "oxidizer":
        return oxidizer_codeweaver_coverage_pair(
            target_dir,
            ref_project_dir,
            generated_tests,
            name_mapping=name_mapping,
            timeout=timeout,
            runner=runner,
        )
    if tool == "alphatrans":
        return alphatrans_codeweaver_coverage_pair(
            target_dir,
            ref_project_dir,
            generated_tests,
            timeout=timeout,
            runner=runner,
        )
    if tool == "skel":
        return skel_codeweaver_coverage_pair(
            target_dir,
            ref_project_dir,
            generated_tests,
            timeout=timeout,
            runner=runner,
        )
    unavailable = Measurement.unavailable(
        f"no CodeWeaver-generated coverage adapter for tool {tool!r}"
    )
    return unavailable, unavailable


@dataclass
class IndependentOracleResult:
    """The four structurally-separate outcomes of
    :func:`evaluate_independent_oracle`: ``validated`` (developer-test
    oracle pass/fail, keyed like ``evaluate_tests``'s return value),
    ``function_validation`` (same shape, EXECUTION-based per-function
    granularity where a reliable one-to-one function mapping is known --
    currently Oxidizer only), ``function_harness_tests`` (same shape,
    GENERATED function/test-harness EXECUTION evidence where a per-function
    mapping is NOT known to be reliable -- currently AlphaTrans's
    ``agent_test/`` and SKEL's ``javascript/*generated*.js``; see this
    module's "POST-HOC INDEPENDENT EVALUATOR" docstring section for why
    these two fields are never conflated), and ``oracle_integrity`` (a
    single Measurement; see :func:`crust_oracle_integrity`)."""
    validated: dict[str, Measurement]
    function_validation: dict[str, Measurement]
    function_harness_tests: dict[str, Measurement]
    oracle_integrity: Measurement


def evaluate_independent_oracle(
    tool: str, run_dir: Path, manifest_row: dict[str, Any] | None, dataset_spec: dict[str, Any],
    reference_results_root: Path | str | None, *, timeout: float | None,
    runner: CommandRunner = default_command_runner,
    crust_paper_expected_tests: dict[str, int] | None = None,
) -> IndependentOracleResult:
    """Dispatches to the tool-specific independent-oracle adapter (see this
    module's "POST-HOC INDEPENDENT EVALUATOR" docstring section for the
    full per-tool rationale). Never falls back to the translated/self-
    reported ``dev_tests_*`` measurement -- an unavailable oracle is always
    reported as ``Status.UNAVAILABLE``/``Status.NOT_APPLICABLE`` with an
    explicit reason, never silently substituted.

    ``crust_paper_expected_tests`` (optional, CRUST-only; see
    ``read_crust_paper_expected_tests``/``--crust-paper-expected-tests``) is
    the already-parsed paper-aligned ``{project: expected_test_count}``
    mapping, threaded straight through to ``crust_validated_tests_eval`` --
    parsed ONCE upfront by the CLI (see ``main()``), not per-run.

    Oxidizer additionally reads ``run_dir``'s own ``pipeline/plan.json``
    (see ``read_name_mapping``) and threads it into both
    ``_evaluate_with_replaced_subdir`` calls below as a best-effort
    idiomatic-identifier-rewrite mitigation -- see the "Oracle
    identifier-rewrite (Oxidizer only)" section above
    ``oxidizer_reference_test_files`` for the full rationale (the concrete
    verified ``oxidizer__checkdigit`` ``NewLuhn``/``new_luhn`` case)."""
    target_dir = _target_dir(run_dir)

    if tool == "crust":
        project = (manifest_row or {}).get("project")
        validated = crust_validated_tests_eval(run_dir, dataset_spec, timeout=timeout, runner=runner,
                                               project=project,
                                               crust_paper_expected_tests=crust_paper_expected_tests)
        oracle_integrity = crust_oracle_integrity(run_dir / "scaffold", target_dir)
        na = Measurement.na("per-function validation is not applicable for CRUST -- the paper validates "
                            "at whole-crate granularity only")
        harness_na = Measurement.na(
            "CRUST has no separate generated function/test-harness concept -- validation is whole-crate "
            "granularity only (see the 'validated' field above)"
        )
        return IndependentOracleResult(validated, {"total": na, "passed": na, "failed": na},
                                       {"total": harness_na, "passed": harness_na, "failed": harness_na},
                                       oracle_integrity)

    # Only CRUST exposes an immutable-input scaffold to the translating
    # agent at all, so only CRUST has a mutation-integrity check to run.
    oracle_integrity = Measurement.na(
        f"{tool} does not expose an independent oracle to the translating agent (no scaffold/immutable-input "
        "contract), so no mutation check applies -- only CRUST does"
    )

    if tool == "oxidizer":
        if reference_results_root is None:
            unavailable = Measurement.unavailable("--reference-results-root not supplied")
            empty = {"total": unavailable, "passed": unavailable, "failed": unavailable}
            validated = _finalize_validated_tests(dict(empty), unavailable)
            return IndependentOracleResult(validated, dict(empty), dict(empty), oracle_integrity)
        project = (manifest_row or {}).get("project")
        ref_dir = reference_project_dir(reference_results_root, tool, project)
        official_ref = bool(
            ref_dir and (ref_dir / "test_comparison_report.json").is_file()
        )
        oracle_files, harness_files = oxidizer_reference_test_files(ref_dir)
        support_files = oxidizer_reference_support_files(ref_dir)
        oracle_inventory = oxidizer_reference_test_inventory(ref_dir)
        expected = oxidizer_validated_tests_expected(
            oracle_files, project,
            official_artifact_verified=official_ref,
        )
        test_cmd = list(dataset_spec.get("unit_test_cmd", []))
        # Best-effort idiomatic-identifier-rewrite mitigation (see "Oracle
        # identifier-rewrite (Oxidizer only)" above oxidizer_reference_test_
        # files) -- read once per run, threaded into BOTH evaluations below
        # since either file set could suffer from the same false-negative
        # pattern; read_name_mapping returns {} (a true no-op) whenever
        # plan.json/name_mapping isn't available, so this is always safe to
        # pass through unconditionally.
        name_mapping = read_name_mapping(run_dir)
        validated_raw = _evaluate_with_replaced_subdir(
            target_dir, oracle_files, "tests", "oxidizer", test_cmd, timeout=timeout,
            dataset_spec=dataset_spec, runner=runner, tmp_prefix="recodeagent_oxidizer_validated_",
            name_mapping=name_mapping,
            rust_integration_tests_only=official_ref,
            allowed_rust_tests=(oracle_inventory or None) if official_ref else None,
            support_files=support_files,
        )
        validated = _finalize_validated_tests(validated_raw, expected)
        function_validation = _evaluate_with_replaced_subdir(
            target_dir, harness_files, "tests", "oxidizer", test_cmd, timeout=timeout,
            dataset_spec=dataset_spec, runner=runner, tmp_prefix="recodeagent_oxidizer_funcval_",
            name_mapping=name_mapping,
            rust_integration_tests_only=official_ref,
            support_files=support_files,
        )
        harness_result = _evaluate_with_replaced_subdir(
            target_dir, oxidizer_generated_test_files(ref_dir), "tests", "oxidizer",
            test_cmd, timeout=timeout, dataset_spec=dataset_spec, runner=runner,
            tmp_prefix="recodeagent_oxidizer_generated_",
            name_mapping=name_mapping,
            rust_integration_tests_only=True,
        )
        return IndependentOracleResult(validated, function_validation, harness_result, oracle_integrity)

    if tool == "alphatrans":
        fv_na = Measurement.unavailable(
            "no reusable per-function validation harness is known for AlphaTrans (see README) -- this is "
            "intentionally NOT the symbol/function translation ratio, which remains a separate completeness "
            "metric, never relabeled as validation. See function_harness_tests_* for GENERATED "
            "function/test-harness execution EVIDENCE instead (agent_test/), which does not assume a "
            "reliable one-to-one per-function mapping"
        )
        function_validation = {"total": fv_na, "passed": fv_na, "failed": fv_na}
        if reference_results_root is None:
            unavailable = Measurement.unavailable("--reference-results-root not supplied")
            validated = _finalize_validated_tests(
                {"total": unavailable, "passed": unavailable, "failed": unavailable}, unavailable)
            harness_result = {"total": unavailable, "passed": unavailable, "failed": unavailable}
            return IndependentOracleResult(validated, function_validation, harness_result, oracle_integrity)
        project = (manifest_row or {}).get("project")
        ref_dir = reference_project_dir(reference_results_root, tool, project)
        validated = alphatrans_validated_tests_eval(target_dir, ref_dir, timeout=timeout, runner=runner)
        harness_result = alphatrans_function_harness_eval(target_dir, ref_dir, timeout=timeout, runner=runner)
        return IndependentOracleResult(validated, function_validation, harness_result, oracle_integrity)

    if tool == "skel":
        # No separate independent-oracle FILE TREE is shipped for SKEL the
        # way the other three each get one -- javascript/source.js embeds
        # BOTH the reference implementation AND its own translated tests
        # together. skel_validated_tests_eval AST-extracts ONLY the
        # test_name_mapping.csv-verified test function bodies (never the
        # rest of source.js) and executes them against CodeWeaver's OWN
        # target exports -- see its own docstring, and this module's
        # "POST-HOC INDEPENDENT EVALUATOR" section, for the full
        # extraction/blocking rules. It stays Status.UNAVAILABLE with a
        # precise reason (never a fabricated 0) whenever
        # --reference-results-root is missing, the CSV/source.js can't be
        # resolved, tree-sitter is unavailable, or every verified test was
        # blocked. SKEL still has no reliable PER-FUNCTION harness, so
        # function_validation_* stays Status.UNAVAILABLE regardless -- see
        # function_harness_tests_* (javascript/*generated*.js) for SKEL's
        # separate GENERATED function-harness execution evidence, never
        # conflated with either field above.
        fv_na = Measurement.unavailable(
            "no reusable per-function validation harness is known for SKEL (see README) -- see "
            "function_harness_tests_* for GENERATED function/test-harness execution EVIDENCE instead "
            "(javascript/*generated*.js), which does not assume a reliable one-to-one per-function mapping"
        )
        function_validation = {"total": fv_na, "passed": fv_na, "failed": fv_na}
        if reference_results_root is None:
            unavailable = Measurement.unavailable("--reference-results-root not supplied")
            validated = _finalize_validated_tests(
                {"total": unavailable, "passed": unavailable, "failed": unavailable}, unavailable)
            harness_result = {"total": unavailable, "passed": unavailable, "failed": unavailable}
            return IndependentOracleResult(validated, function_validation, harness_result, oracle_integrity)
        project = (manifest_row or {}).get("project")
        ref_dir = reference_project_dir(reference_results_root, tool, project)
        validated = skel_validated_tests_eval(target_dir, ref_dir, timeout=timeout, runner=runner)
        harness_result = skel_function_harness_eval(target_dir, ref_dir, timeout=timeout, runner=runner)
        return IndependentOracleResult(validated, function_validation, harness_result, oracle_integrity)

    # any future/unrecognized tool: no independent target-language oracle is
    # present in either artifact at all -- see README.
    reason = f"no independent target-language oracle is available for tool {tool!r} (see README)"
    unavailable = Measurement.unavailable(reason)
    empty = {"total": unavailable, "passed": unavailable, "failed": unavailable}
    validated = _finalize_validated_tests(dict(empty), unavailable)
    return IndependentOracleResult(validated, dict(empty), dict(empty), oracle_integrity)


def collect_run(
    run_dir: Path,
    *,
    variant: str,
    project_id: str,
    tool: str,
    repetition: int,
    manifest_row: dict[str, Any] | None,
    dataset_spec: dict[str, Any],
    timeout: float | None = None,
    runner: CommandRunner = default_command_runner,
    reference_results_root: Path | str | None = None,
    crust_paper_expected_tests: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Collect ONE run's normalized measurements. Raises :class:`CollectionSkip`
    (never returns a fabricated row) when the run cannot be objectively
    evaluated yet (not attempted / not terminal / corrupt state).

    ``reference_results_root`` (optional) points at the official RESULTS
    artifact's extracted tree (see this module's "POST-HOC INDEPENDENT
    EVALUATOR" docstring section); when omitted, the resulting
    ``validated_tests_*``/``function_validation_*`` fields are
    ``Status.UNAVAILABLE`` for Oxidizer/AlphaTrans (CRUST's own oracle never
    needs it at all; SKEL has none regardless). Reference assets are only
    ever read AFTER this function's own terminal-run-status gate below, and
    only ever copied into a fresh ``tempfile.TemporaryDirectory()`` -- never
    into ``run_dir`` itself.

    ``crust_paper_expected_tests`` (optional, CRUST-only; see
    ``read_crust_paper_expected_tests``/``--crust-paper-expected-tests``) is
    the already-parsed paper-aligned per-project expected-test-count
    mapping; forwarded verbatim to ``evaluate_independent_oracle``. When
    omitted, CRUST's ``validated_tests_expected`` falls back to the NATIVE
    static count (``validated_tests_expected_native``) with
    ``validated_tests_expected_source == "native"`` -- never silently
    presented as the paper's own figure."""
    if not run_dir.exists():
        raise CollectionSkip("not_attempted: no run directory found")
    state = read_json_or(run_dir / R.STATE_FILENAME, None)
    if state is None:
        raise CollectionSkip("no_state_file: recodeagent_run_state.json missing or unparseable")
    run_status = state.get("status")
    if run_status not in ("completed", "failed", "timeout"):
        raise CollectionSkip(f"not_terminal: run status is {run_status!r} (has not finished)")

    target_dir = _target_dir(run_dir)
    target_language = (manifest_row or {}).get("target_language") or dataset_spec.get("target_language", "")
    source_function_count = (manifest_row or {}).get("function_count_source")

    build_measurement = evaluate_build(target_dir, dataset_spec.get("build_cmd", []),
                                       timeout=timeout, runner=runner)
    test_measurements = evaluate_tests(target_dir, dataset_spec.get("unit_test_cmd", []), tool,
                                      timeout=timeout, dataset_spec=dataset_spec, runner=runner)
    pass_rate = compute_pass_rate(test_measurements["total"], test_measurements["passed"])

    # Independent (post-hoc) oracle evaluation -- structurally separate from
    # test_measurements/pass_rate above (which are the *translated*, self-
    # reported tests). Only ever reached AFTER the terminal-status gate
    # above, i.e. only for a run whose LLM invocation has already finished.
    oracle_result = evaluate_independent_oracle(
        tool, run_dir, manifest_row, dataset_spec, reference_results_root,
        timeout=timeout, runner=runner, crust_paper_expected_tests=crust_paper_expected_tests,
    )
    validated_pass_rate = compute_paper_pass_rate(
        oracle_result.validated["expected"], oracle_result.validated["passed"]
    )
    project_pass_all = compute_project_pass_all(
        build_measurement,
        oracle_result.validated["expected"],
        oracle_result.validated["passed"],
        oracle_result.validated["failed"],
        oracle_result.validated["not_executed"],
    )
    project_name = (manifest_row or {}).get("project")
    if tool == "crust":
        function_validation_expected = Measurement.na(
            "the paper excludes CRUST from function-level validation"
        )
    else:
        expected_functions = C.PAPER_EXERCISED_FUNCTIONS_BY_PROJECT.get((tool, project_name))
        function_validation_expected = (
            Measurement.ok(expected_functions)
            if expected_functions is not None else
            Measurement.unavailable(
                f"no paper-aligned exercised-function inventory for {(tool, project_name)!r}"
            )
        )
    function_validation_not_executed = compute_not_executed(
        function_validation_expected, oracle_result.function_validation["total"]
    )
    function_validation_pass_rate = compute_pass_rate(
        oracle_result.function_validation["total"], oracle_result.function_validation["passed"]
    )
    function_validation_paper_pass_rate = compute_paper_pass_rate(
        function_validation_expected, oracle_result.function_validation["passed"]
    )
    function_harness_tests_pass_rate = compute_pass_rate(
        oracle_result.function_harness_tests["total"], oracle_result.function_harness_tests["passed"]
    )
    generated_harness_expected_value = C.PAPER_GENERATED_TESTS_BY_PROJECT_NON_CRUST.get(
        (tool, project_name)
    )
    if tool in {"oxidizer", "alphatrans", "skel"} and generated_harness_expected_value is not None:
        function_harness_tests_expected = Measurement(
            value=generated_harness_expected_value,
            status=Status.MEASURED,
            reason="paper-aligned fixed generated-test case inventory",
        )
    else:
        function_harness_tests_expected = Measurement.na(
            "the standardized generated-harness family is defined only for non-CRUST tools"
        )
    function_harness_tests_not_executed = compute_not_executed(
        function_harness_tests_expected, oracle_result.function_harness_tests["total"]
    )
    function_harness_tests_paper_pass_rate = compute_paper_pass_rate(
        function_harness_tests_expected, oracle_result.function_harness_tests["passed"]
    )

    # Build/test baseline for the only dataset that ships a pre-translation
    # target-language scaffold. Coverage "before" below has a different,
    # paper-specific meaning: independent developer tests before adding
    # generated tests.
    scaffold_dir = run_dir / "scaffold"
    if scaffold_dir.exists():
        baseline_build = evaluate_build(scaffold_dir, dataset_spec.get("build_cmd", []),
                                        timeout=timeout, runner=runner)
        baseline_tests = evaluate_tests(scaffold_dir, dataset_spec.get("unit_test_cmd", []), tool,
                                        timeout=timeout, dataset_spec=dataset_spec, runner=runner)
    else:
        na = Measurement.na("no pre-translation scaffold for this dataset (only CRUST ships one)")
        baseline_build = na
        baseline_tests = {"total": na, "passed": na, "failed": na}

    standardized_na = Measurement.na(
        "the standardized official generated-harness coverage family is defined only for "
        "Oxidizer, AlphaTrans, and SKEL"
    )
    if tool == "crust" and scaffold_dir.exists():
        coverage_before, coverage_after = crust_paper_coverage_pair(
            target_dir, scaffold_dir, timeout=timeout, runner=runner
        )
        standardized_coverage_before = standardized_na
        standardized_coverage_after = standardized_na
    elif tool in {"oxidizer", "alphatrans", "skel"} and reference_results_root is not None:
        coverage_ref_dir = reference_project_dir(
            Path(reference_results_root), tool, project_name
        )
        if tool == "oxidizer":
            standardized_coverage_before, standardized_coverage_after = oxidizer_paper_coverage_pair(
                target_dir,
                coverage_ref_dir,
                name_mapping=read_name_mapping(run_dir),
                timeout=timeout,
                runner=runner,
            )
        elif tool == "alphatrans":
            standardized_coverage_before, standardized_coverage_after = alphatrans_paper_coverage_pair(
                target_dir, coverage_ref_dir, timeout=timeout, runner=runner
            )
        else:
            standardized_coverage_before, standardized_coverage_after = skel_paper_coverage_pair(
                target_dir, coverage_ref_dir, timeout=timeout, runner=runner
            )
        coverage_before = Measurement(
            value=standardized_coverage_before.value,
            status=standardized_coverage_before.status,
            reason=(
                "independent developer-test baseline shared with the standardized "
                "official-harness coverage adapter; "
                + standardized_coverage_before.reason
            ),
        )
        coverage_after = Measurement.unavailable(
            "paper-equivalent coverage_after requires independently classified "
            "CodeWeaver-authored generated tests and is emitted by paper_test_compare.py "
            "in generated_test_projects; the official ReCodeAgent harness result is kept "
            "separately as standardized_coverage_after"
        )
    else:
        standardized_coverage_before = Measurement.unavailable(
            "standardized coverage requires --reference-results-root"
        )
        standardized_coverage_after = Measurement.unavailable(
            "standardized coverage requires --reference-results-root"
        )
        coverage_before = Measurement.unavailable(
            "paper-equivalent developer-test coverage requires --reference-results-root"
        )
        coverage_after = Measurement.unavailable(
            "paper-equivalent coverage_after is emitted by paper_test_compare.py after "
            "CodeWeaver-authored generated-test classification"
        )

    stub_measurement = scan_stub_markers(target_dir, target_language)
    target_functions = target_function_counts(target_dir, target_language)
    target_tests = target_test_counts(target_dir, target_language)
    # translated_tests_expected/not_executed: a best-effort, "where possible"
    # analogue of validated_tests_expected/not_executed above for the
    # (structurally separate) TRANSLATED test suite. target_tests is a
    # static discovered-test count (independent of whether the test command
    # itself could even run), so it plays the same "expected" role here that
    # the oracle-only counters play for validated_tests_expected --
    # deliberately NOT changing translated_tests_pass_rate's own existing
    # formula (see the module's documented Scope note on dev_test_pass_rate/
    # Figure 7 TPR sourcing).
    translated_tests_not_executed = compute_not_executed(target_tests, test_measurements["total"])
    if target_functions.is_measured and isinstance(source_function_count, int) and source_function_count > 0:
        function_ratio = Measurement.ok(target_functions.value / source_function_count)
    else:
        function_ratio = Measurement.missing("source and/or target function counts unavailable")

    calls = read_jsonl(run_dir / R.CALLS_FILENAME)
    final_validate_ok = None
    for c in reversed(calls):
        # A "placeholder" call (written only by the old, now-dead single-pass
        # ablation driver -- kept here only for backward compatibility with
        # any pre-upgrade run directory that might still be on disk) hard-
        # codes ok=True purely so a placeholder never masquerades as an
        # agent failure elsewhere in the pipeline -- it must NOT be read
        # here as "the validator passed". Skipping it means
        # milestone_validation() below correctly falls back to "missing"
        # (no real validate-stage evidence) instead of a fabricated
        # synthetic pass. For a current run of noanalyzer/noplanning/
        # novalidator (CodeWeaver core's CODEWEAVER_SKIP_STAGES, the real
        # Burr graph end to end), this loop instead matches the single
        # stage="full_pipeline"/kind="cli" call exactly like `full` does;
        # `final_validate_ok` is consulted only by milestone_validation's
        # baseagent-* branch below, since those three variants are now
        # dispatched to the real per-milestone-history branch instead.
        if c.get("stage") in ("validate", "baseagent", "full_pipeline") and c.get("kind") != "placeholder":
            final_validate_ok = bool(c.get("ok"))
            break

    cli_stdout = None
    cli_log = run_dir / "cli.stdout.log"
    if cli_log.exists():
        cli_stdout = cli_log.read_text(encoding="utf-8", errors="replace")

    # Ground truth for which stage (if any) this run deliberately skipped:
    # prefer run.py's own persisted state (it records exactly what it told
    # CodeWeaver core via CODEWEAVER_SKIP_STAGES for THIS run), falling back
    # to the static noanalyzer/noplanning/novalidator -> stage mapping for
    # any older run_state.json predating that field.
    skipped_stage = (state.get("ablation") or {}).get("skipped_stage") or R.STAGE_SKIP_VARIANTS.get(variant)

    if variant == "full" or variant in R.STAGE_SKIP_VARIANTS:
        # Both `full` and the three stage-skip ablations now run the
        # identical real `python -m codeweaver run` CLI subprocess end to
        # end (CodeWeaver core's CODEWEAVER_SKIP_STAGES instrumentation
        # deterministically omits exactly one stage's real work while every
        # other Burr milestone/repair/parity behavior is preserved) -- so
        # all four are reconstructed from the same real evidence, never from
        # the degenerate single-call recodeagent_calls.jsonl shape run.py
        # now writes for these variants (one "full_pipeline"/"cli" entry,
        # structurally identical to `full`'s own).
        trajectory = trajectory_from_full_pipeline(
            cli_stdout, parity_ran=(run_dir / "pipeline" / "parity.json").exists(),
            skipped_stage=skipped_stage,
        )
        tool_rollup, tool_precision = collect_jsonl_tool_rollup(run_dir / "pipeline" / "logs")
    else:
        # baseagent-condensed/baseagent-concat only: harness-driven,
        # single-shot one-agent prompts with no Burr graph at all --
        # recodeagent_calls.jsonl remains their own exact, complete,
        # call-by-call record.
        trajectory = trajectory_from_calls(calls)
        tool_rollup = {}
        for c in calls:
            summary = c.get("events_summary") or {}
            for key, default in (("tool_invocations", 0), ("assistant_turns", 0)):
                tool_rollup[key] = tool_rollup.get(key, 0) + int(summary.get(key) or default)
            for key in ("premium_requests", "session_duration_ms"):
                if summary.get(key) is not None:
                    tool_rollup[key] = tool_rollup.get(key, 0) + int(summary[key])
            if summary.get("tokens_status") == Status.MEASURED:
                for key in ("input_tokens", "output_tokens"):
                    if summary.get(key) is not None:
                        tool_rollup[key] = tool_rollup.get(key, 0) + int(summary[key])
        tool_precision = "exact" if calls else "unavailable"

    milestones = milestone_validation(run_dir, variant, cli_stdout, final_validate_ok,
                                      skipped_stage=skipped_stage)

    elapsed = Measurement.missing("started_at/ended_at not both recorded")
    started, ended = state.get("started_at"), state.get("ended_at")
    if started and ended:
        with contextlib.suppress(ValueError):
            elapsed = Measurement.ok(_iso_seconds_between(started, ended))

    provenance = state.get("provenance") or {}

    row: dict[str, Any] = {
        "variant": variant, "project_id": project_id, "tool": tool, "repetition": repetition,
        "workspace_dir": str(run_dir), "app_id": state.get("app_id"), "collected_at": utcnow_iso(),
        "run_status": run_status, "run_error": state.get("error", ""),
        "run_started_at": started, "run_ended_at": ended,
        "run_attempt": state.get("attempt"), "run_returncode": state.get("returncode"),
        **build_measurement.flatten("build"),
        **test_measurements["total"].flatten("dev_tests_total"),
        **test_measurements["passed"].flatten("dev_tests_passed"),
        **test_measurements["failed"].flatten("dev_tests_failed"),
        **pass_rate.flatten("dev_test_pass_rate"),
        # translated_tests_* are literal aliases of dev_tests_*/dev_test_pass_rate
        # above (same values, same run) -- an unambiguous name now that
        # validated_tests_* (the paper's independently validated developer
        # tests) exists as a STRUCTURALLY SEPARATE measurement below. Old
        # dev_tests_*/dev_test_pass_rate names are kept for compatibility.
        # translated_tests_expected/not_executed are a best-effort "where
        # possible" analogue of validated_tests_expected/not_executed (see
        # the comment above translated_tests_not_executed's computation);
        # translated_tests_pass_rate itself keeps its EXISTING executed-
        # relative formula unchanged (a documented Scope note -- see
        # dev_test_pass_rate/Figure 7 TPR sourcing).
        **test_measurements["total"].flatten("translated_tests_total"),
        **test_measurements["passed"].flatten("translated_tests_passed"),
        **test_measurements["failed"].flatten("translated_tests_failed"),
        **pass_rate.flatten("translated_tests_pass_rate"),
        **target_tests.flatten("translated_tests_expected"),
        **translated_tests_not_executed.flatten("translated_tests_not_executed"),
        # validated_tests_* -- the paper's INDEPENDENTLY validated developer
        # tests (see this module's "POST-HOC INDEPENDENT EVALUATOR"
        # docstring section). ``expected`` is a FIXED, oracle-known
        # denominator (available even when ``executed`` reports a build/
        # import failure); the paper's own TPR/pass-rate is passed/expected,
        # NOT passed/executed (the paper's own worked example: TPR reports
        # 1,822/2,107 despite only TE=1,970 tests actually executing) -- see
        # compute_paper_pass_rate/compute_not_executed.
        **oracle_result.validated["expected"].flatten("validated_tests_expected"),
        **oracle_result.validated["executed"].flatten("validated_tests_executed"),
        **oracle_result.validated["passed"].flatten("validated_tests_passed"),
        **oracle_result.validated["failed"].flatten("validated_tests_failed"),
        **oracle_result.validated["not_executed"].flatten("validated_tests_not_executed"),
        **validated_pass_rate.flatten("validated_tests_pass_rate"),
        **project_pass_all.flatten("project_pass_all"),
        # expected_native/_paper/_source -- CRUST's native-static-count-vs-
        # paper's-own-authoritative-count reconciliation (see
        # crust_combine_expected); a shared NOT_APPLICABLE placeholder for
        # every other tool, whose validated_tests_expected already reflects
        # a single, un-split oracle-derived denominator.
        **oracle_result.validated["expected_native"].flatten("validated_tests_expected_native"),
        **oracle_result.validated["expected_paper"].flatten("validated_tests_expected_paper"),
        **oracle_result.validated["expected_source"].flatten("validated_tests_expected_source"),
        **oracle_result.oracle_integrity.flatten("oracle_integrity"),
        **baseline_build.flatten("baseline_build"),
        **baseline_tests["total"].flatten("baseline_tests_total"),
        **baseline_tests["passed"].flatten("baseline_tests_passed"),
        **baseline_tests["failed"].flatten("baseline_tests_failed"),
        **coverage_before.flatten("coverage_before"),
        **coverage_after.flatten("coverage_after"),
        **standardized_coverage_before.flatten("standardized_coverage_before"),
        **standardized_coverage_after.flatten("standardized_coverage_after"),
        **target_functions.flatten("target_function_count"),
        **target_tests.flatten("target_test_count"),
        "source_function_count": source_function_count,
        **function_ratio.flatten("function_translation_ratio"),
        **oracle_result.function_validation["total"].flatten("function_validation_total"),
        **oracle_result.function_validation["passed"].flatten("function_validation_passed"),
        **oracle_result.function_validation["failed"].flatten("function_validation_failed"),
        **function_validation_expected.flatten("function_validation_expected"),
        **function_validation_not_executed.flatten("function_validation_not_executed"),
        **function_validation_pass_rate.flatten("function_validation_pass_rate"),
        **function_validation_paper_pass_rate.flatten("function_validation_paper_pass_rate"),
        # function_harness_tests_* -- standardized GENERATED harness execution
        # for Oxidizer/AlphaTrans/SKEL, separate from per-function validation.
        **oracle_result.function_harness_tests["total"].flatten("function_harness_tests_total"),
        **oracle_result.function_harness_tests["passed"].flatten("function_harness_tests_passed"),
        **oracle_result.function_harness_tests["failed"].flatten("function_harness_tests_failed"),
        **function_harness_tests_expected.flatten("function_harness_tests_expected"),
        **function_harness_tests_not_executed.flatten("function_harness_tests_not_executed"),
        **function_harness_tests_pass_rate.flatten("function_harness_tests_pass_rate"),
        **function_harness_tests_paper_pass_rate.flatten("function_harness_tests_paper_pass_rate"),
        **_stub_flatten(stub_measurement),
        "ablation_skipped_stage": skipped_stage,
        **milestones["total"].flatten("milestones_total"),
        **milestones["passed"].flatten("milestones_passed"),
        "milestone_granularity": milestones["granularity"],
        "trajectory_precision": trajectory.precision, "trajectory_reason": trajectory.reason,
        "nc": trajectory.nc, "tec": trajectory.tec, "lc": trajectory.lc, "all": trajectory.all_,
        "sec_json": json.dumps(trajectory.sec, sort_keys=True),
        **elapsed.flatten("elapsed_seconds"),
        "tool_invocations_precision": tool_precision,
        "total_tool_invocations": tool_rollup.get("tool_invocations"),
        "total_assistant_turns": tool_rollup.get("assistant_turns"),
        "total_premium_requests": tool_rollup.get("premium_requests"),
        "total_nano_aiu": tool_rollup.get("nano_aiu"),
        "total_session_duration_ms": tool_rollup.get("session_duration_ms"),
        "tool_counts_json": json.dumps(tool_rollup.get("tool_counts", {}), sort_keys=True),
        "total_input_tokens": tool_rollup.get("input_tokens"),
        "total_output_tokens": tool_rollup.get("output_tokens"),
        "input_tokens_status": (
            Status.MEASURED if "input_tokens" in tool_rollup else Status.UNAVAILABLE
        ),
        "output_tokens_status": (
            Status.MEASURED if "output_tokens" in tool_rollup else Status.UNAVAILABLE
        ),
        "nano_aiu_status": (
            Status.MEASURED if "nano_aiu" in tool_rollup else Status.UNAVAILABLE
        ),
        "tokens_status": Status.MEASURED if "input_tokens" in tool_rollup or "output_tokens" in tool_rollup
                        else Status.UNAVAILABLE,
        "model": (provenance.get("model") or {}).get("value"),
        "agent_timeout_seconds": (provenance.get("agent_timeout_seconds") or {}).get("value"),
        "git_sha": (provenance.get("git_sha") or {}).get("value"),
        "codeweaver_package_version": (provenance.get("codeweaver_package_version") or {}).get("value"),
        "copilot_cli_version": (provenance.get("copilot_cli_version") or {}).get("value"),
    }
    return row


def _stub_flatten(m: Measurement) -> dict[str, Any]:
    if m.is_measured:
        return {
            "stub_marker_count": m.value.get("stub_marker_count"),
            "stub_marker_count_status": m.status, "stub_marker_count_reason": m.reason,
            "stub_files_json": json.dumps(m.value.get("files_with_stubs", [])),
        }
    return {"stub_marker_count": None, "stub_marker_count_status": m.status,
           "stub_marker_count_reason": m.reason, "stub_files_json": json.dumps([])}


def _iso_seconds_between(start_iso: str, end_iso: str) -> float:
    import datetime as _dt
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    t0 = _dt.datetime.strptime(start_iso, fmt).replace(tzinfo=_dt.timezone.utc)
    t1 = _dt.datetime.strptime(end_iso, fmt).replace(tzinfo=_dt.timezone.utc)
    return (t1 - t0).total_seconds()


# --------------------------------------------------------------------------- #
# Matrix-wide collection
# --------------------------------------------------------------------------- #
def collect_all(
    runs_root: Path,
    manifest: dict[str, Any],
    *,
    variants: list[str],
    project_ids: list[str] | None = None,
    repetitions: int = 1,
    dataset_specs: dict[str, dict[str, Any]] | None = None,
    timeout: float | None = None,
    runner: CommandRunner = default_command_runner,
    reference_results_root: Path | str | None = None,
    crust_paper_expected_tests: dict[str, int] | None = None,
    max_workers: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Walks the FULL expected (variant, project, repetition) matrix (not just
    whatever happens to exist on disk) so a never-attempted job is reported in
    failures.csv rather than silently absent from both outputs.

    ``reference_results_root`` is forwarded verbatim to every
    :func:`collect_run` call (see its own docstring) -- optional, and only
    consulted for every non-CRUST independent-oracle/generated-harness
    evaluation.
    ``crust_paper_expected_tests`` (optional) is the already-parsed, paper-
    aligned per-project CRUST expected-test-count mapping (see
    ``read_crust_paper_expected_tests``/``--crust-paper-expected-tests``),
    likewise forwarded verbatim to every :func:`collect_run` call -- parsed
    ONCE by the CLI (see ``main()``), not per-run/per-project."""
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    dataset_specs = dataset_specs or {}
    rows_by_id = {r["id"]: r for r in manifest.get("projects", [])}
    ids = project_ids if project_ids is not None else list(rows_by_id.keys())

    jobs = [
        (variant, project_id, repetition)
        for variant in variants
        for project_id in ids
        for repetition in range(repetitions)
    ]

    def collect_job(job: tuple[str, str, int]) -> tuple[str, dict[str, Any]]:
        variant, project_id, repetition = job
        manifest_row = rows_by_id.get(project_id)
        tool = (manifest_row or {}).get("tool", "")
        spec = dataset_specs.get(tool, {})
        run_dir = R.run_dir_for(runs_root, variant, project_id, repetition)
        try:
            return "row", collect_run(
                run_dir, variant=variant, project_id=project_id, tool=tool,
                repetition=repetition, manifest_row=manifest_row, dataset_spec=spec,
                timeout=timeout, runner=runner, reference_results_root=reference_results_root,
                crust_paper_expected_tests=crust_paper_expected_tests,
            )
        except CollectionSkip as exc:
            reason = exc.reason
        except Exception as exc:  # noqa: BLE001 - one bad run must not abort the matrix
            reason = f"collection_error: {exc!r}"
        return "failure", {
            "variant": variant, "project_id": project_id, "tool": tool,
            "repetition": repetition, "workspace_dir": str(run_dir),
            "reason": reason, "detected_at": utcnow_iso(),
        }

    if max_workers > 1 and len(jobs) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            results = list(pool.map(collect_job, jobs))
    else:
        results = [collect_job(job) for job in jobs]
    for kind, result in results:
        (rows if kind == "row" else failures).append(result)
    return rows, failures


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
_RAW_RUNS_CSV_COLUMNS = [
    "variant", "project_id", "tool", "repetition", "workspace_dir", "app_id", "collected_at",
    "run_status", "run_error", "run_started_at", "run_ended_at", "run_attempt", "run_returncode",
    "build", "build_status", "build_reason",
    "dev_tests_total", "dev_tests_total_status", "dev_tests_total_reason",
    "dev_tests_passed", "dev_tests_passed_status", "dev_tests_passed_reason",
    "dev_tests_failed", "dev_tests_failed_status", "dev_tests_failed_reason",
    "dev_test_pass_rate", "dev_test_pass_rate_status", "dev_test_pass_rate_reason",
    # translated_tests_* -- unambiguous aliases of dev_tests_*/dev_test_pass_rate above
    # (kept for compatibility), now structurally distinct from validated_tests_* below.
    # expected/not_executed are a best-effort "where possible" analogue of
    # validated_tests_expected/not_executed; translated_tests_pass_rate keeps its
    # existing executed-relative formula (documented Scope note).
    "translated_tests_total", "translated_tests_total_status", "translated_tests_total_reason",
    "translated_tests_passed", "translated_tests_passed_status", "translated_tests_passed_reason",
    "translated_tests_failed", "translated_tests_failed_status", "translated_tests_failed_reason",
    "translated_tests_pass_rate", "translated_tests_pass_rate_status", "translated_tests_pass_rate_reason",
    "translated_tests_expected", "translated_tests_expected_status", "translated_tests_expected_reason",
    "translated_tests_not_executed", "translated_tests_not_executed_status",
    "translated_tests_not_executed_reason",
    # validated_tests_* -- the paper's INDEPENDENTLY validated developer-test oracle
    # (see collect.py's "POST-HOC INDEPENDENT EVALUATOR"), never the translated tests
    # above. ``expected`` is the FIXED, oracle-known denominator (e.g. the paper's own
    # 2,107); ``executed`` is whatever the test command actually ran this run (the
    # paper's own TE, e.g. 1,970); ``validated_tests_pass_rate`` is passed/expected
    # (the paper's own TPR, e.g. 1,822/2,107), NEVER passed/executed.
    "validated_tests_expected", "validated_tests_expected_status", "validated_tests_expected_reason",
    "validated_tests_executed", "validated_tests_executed_status", "validated_tests_executed_reason",
    "validated_tests_passed", "validated_tests_passed_status", "validated_tests_passed_reason",
    "validated_tests_failed", "validated_tests_failed_status", "validated_tests_failed_reason",
    "validated_tests_not_executed", "validated_tests_not_executed_status",
    "validated_tests_not_executed_reason",
    "validated_tests_pass_rate", "validated_tests_pass_rate_status", "validated_tests_pass_rate_reason",
    "project_pass_all", "project_pass_all_status", "project_pass_all_reason",
    # expected_native/_paper/_source -- CRUST's native-static-count-vs-
    # paper's-own-authoritative-count reconciliation (see collect.py's
    # crust_combine_expected). validated_tests_expected above is the
    # COMBINED value (paper-aligned preferred when available, else native);
    # these 3 columns keep BOTH inputs auditable and record which one won
    # ("paper"/"native") so the two are never silently presented as equal.
    # NOT_APPLICABLE for every non-CRUST tool.
    "validated_tests_expected_native", "validated_tests_expected_native_status",
    "validated_tests_expected_native_reason",
    "validated_tests_expected_paper", "validated_tests_expected_paper_status",
    "validated_tests_expected_paper_reason",
    "validated_tests_expected_source", "validated_tests_expected_source_status",
    "validated_tests_expected_source_reason",
    "oracle_integrity", "oracle_integrity_status", "oracle_integrity_reason",
    "baseline_build", "baseline_build_status", "baseline_build_reason",
    "baseline_tests_total", "baseline_tests_total_status", "baseline_tests_total_reason",
    "baseline_tests_passed", "baseline_tests_passed_status", "baseline_tests_passed_reason",
    "baseline_tests_failed", "baseline_tests_failed_status", "baseline_tests_failed_reason",
    "coverage_before", "coverage_before_status", "coverage_before_reason",
    "coverage_after", "coverage_after_status", "coverage_after_reason",
    # Cross-system diagnostic using ReCodeAgent's official generated harness,
    # never relabeled as CodeWeaver-authored generated-test coverage.
    "standardized_coverage_before", "standardized_coverage_before_status",
    "standardized_coverage_before_reason",
    "standardized_coverage_after", "standardized_coverage_after_status",
    "standardized_coverage_after_reason",
    "target_function_count", "target_function_count_status", "target_function_count_reason",
    "target_test_count", "target_test_count_status", "target_test_count_reason",
    "source_function_count",
    "function_translation_ratio", "function_translation_ratio_status", "function_translation_ratio_reason",
    # function_validation_* -- execution-based per-function validation (where an
    # adapter provides one); structurally distinct from the symbol/completeness
    # ratio above, which is NEVER relabeled as validation.
    "function_validation_total", "function_validation_total_status", "function_validation_total_reason",
    "function_validation_passed", "function_validation_passed_status", "function_validation_passed_reason",
    "function_validation_failed", "function_validation_failed_status", "function_validation_failed_reason",
    "function_validation_expected", "function_validation_expected_status", "function_validation_expected_reason",
    "function_validation_not_executed", "function_validation_not_executed_status",
    "function_validation_not_executed_reason",
    "function_validation_pass_rate", "function_validation_pass_rate_status", "function_validation_pass_rate_reason",
    "function_validation_paper_pass_rate", "function_validation_paper_pass_rate_status",
    "function_validation_paper_pass_rate_reason",
    # function_harness_tests_* -- standardized GENERATED harness execution for
    # Oxidizer/AlphaTrans/SKEL, structurally separate from per-function
    # validation above.
    "function_harness_tests_total", "function_harness_tests_total_status", "function_harness_tests_total_reason",
    "function_harness_tests_passed", "function_harness_tests_passed_status",
    "function_harness_tests_passed_reason",
    "function_harness_tests_failed", "function_harness_tests_failed_status",
    "function_harness_tests_failed_reason",
    "function_harness_tests_pass_rate", "function_harness_tests_pass_rate_status",
    "function_harness_tests_pass_rate_reason",
    "function_harness_tests_expected", "function_harness_tests_expected_status",
    "function_harness_tests_expected_reason",
    "function_harness_tests_not_executed", "function_harness_tests_not_executed_status",
    "function_harness_tests_not_executed_reason",
    "function_harness_tests_paper_pass_rate", "function_harness_tests_paper_pass_rate_status",
    "function_harness_tests_paper_pass_rate_reason",
    "stub_marker_count", "stub_marker_count_status", "stub_marker_count_reason", "stub_files_json",
    "ablation_skipped_stage",
    "milestones_total", "milestones_total_status", "milestones_total_reason",
    "milestones_passed", "milestones_passed_status", "milestones_passed_reason",
    "milestone_granularity",
    "trajectory_precision", "trajectory_reason", "nc", "tec", "lc", "all", "sec_json",
    "elapsed_seconds", "elapsed_seconds_status", "elapsed_seconds_reason",
    "tool_invocations_precision", "total_tool_invocations", "total_assistant_turns",
    "total_premium_requests", "total_nano_aiu", "nano_aiu_status",
    "total_session_duration_ms", "tool_counts_json",
    "tokens_status", "total_input_tokens", "input_tokens_status",
    "total_output_tokens", "output_tokens_status",
    "model", "agent_timeout_seconds", "git_sha", "codeweaver_package_version", "copilot_cli_version",
]
_FAILURES_CSV_COLUMNS = ["variant", "project_id", "tool", "repetition", "workspace_dir", "reason", "detected_at"]



def _write_csv(rows: list[dict[str, Any]], columns: list[str], path: Path) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    atomic_write_text(path, buf.getvalue())


def write_raw_runs(rows: list[dict[str, Any]], output_root: Path) -> tuple[Path, Path]:
    output_root = Path(output_root)
    json_path = output_root / "raw_runs.jsonl"
    csv_path = output_root / "raw_runs.csv"
    buf = io.StringIO()
    for row in rows:
        buf.write(json.dumps(row, default=str) + "\n")
    atomic_write_text(json_path, buf.getvalue())
    _write_csv(rows, _RAW_RUNS_CSV_COLUMNS, csv_path)
    return json_path, csv_path


def write_failures(failures: list[dict[str, Any]], output_root: Path) -> Path:
    csv_path = Path(output_root) / "failures.csv"
    _write_csv(failures, _FAILURES_CSV_COLUMNS, csv_path)
    return csv_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="collect.py",
        description="Independently evaluate run.py's outputs and write raw_runs.csv/jsonl + failures.csv.",
    )
    ap.add_argument("--manifest", required=True, help="path to manifest.json (from manifest.py)")
    ap.add_argument("--runs-root", required=True, help="the --out root run.py wrote runs under")
    ap.add_argument("--output-root", required=True, help="where raw_runs.csv/jsonl + failures.csv are written")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--variant", default="all", help="comma-separated variants, or 'all' (default)")
    ap.add_argument("--project", default=None, help="comma-separated project ids (default: all in manifest)")
    ap.add_argument("--repetitions", type=int, default=None, help="default: [protocol].repetitions")
    ap.add_argument("--timeout", type=float, default=None, help="per-command timeout in seconds (build/test/coverage)")
    ap.add_argument("--jobs", type=int, default=1, help="parallel independent collection workers")
    ap.add_argument("--reference-results-root", default=None,
                    help="official RESULTS artifact extraction root (shape: <root>/recodeagent_translations/"
                         "data/tool_projects/{tool}/{project}), used for the non-CRUST independent evaluators "
                         "and standardized generated harnesses. Never copied "
                         "into a run workspace; read-only, and only ever copied into a temporary directory "
                         "AFTER a run has already reached a terminal state. Omitting this flag leaves those "
                         "fields Status.UNAVAILABLE (never a silent fallback to translated-test numbers); "
                         "CRUST's own oracle (its pristine run_dir/scaffold) never needs this flag.")
    ap.add_argument("--crust-paper-expected-tests", default=None,
                    help="path to CRUST's paper-ALIGNED per-project expected-test-count reference: either the "
                         "official results.xlsx (read via the optional openpyxl dependency, from its own "
                         f"{CRUST_PAPER_EXPECTED_SHEET_NAME!r} sheet) or an explicit JSON ({{project: count}}) "
                         "or CSV (project,expected_tests) reference-inventory file. A naive static #[test]-"
                         "attribute count over a CRUST scaffold (validated_tests_expected_native) is known to "
                         "disagree with the paper's own bookkeeping in BOTH directions for real projects (e.g. "
                         "2dpartint/holdem-odds overcount, libfor undercounts because its oracle is a binary "
                         "assertion harness with no #[test] at all) -- omitting this flag leaves "
                         "validated_tests_expected on the native count, labeled "
                         "validated_tests_expected_source=native, never silently presented as the paper's own "
                         "figure.")
    return ap


def _parse_variants(raw: str) -> list[str]:
    if raw == "all":
        return list(C.RUN_VARIANTS)
    variants = [v.strip() for v in raw.split(",") if v.strip()]
    for v in variants:
        if v not in C.RUN_VARIANTS:
            raise ValueError(f"unknown variant {v!r}; choose from {C.RUN_VARIANTS}")
    return variants


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = P.load_experiment_config(args.config)
    manifest = C.read_json(args.manifest)
    variants = _parse_variants(args.variant)
    project_ids = args.project.split(",") if args.project else None
    repetitions = args.repetitions if args.repetitions is not None else int(cfg.get("protocol", {}).get("repetitions", 1))

    # Parsed ONCE upfront (not per-run/per-project) -- see
    # read_crust_paper_expected_tests's/collect_all's own docstrings.
    crust_paper_expected_tests: dict[str, int] | None = None
    if args.crust_paper_expected_tests:
        crust_paper_expected_tests, reason = read_crust_paper_expected_tests(args.crust_paper_expected_tests)
        if crust_paper_expected_tests is None:
            print(f"[collect] WARNING: --crust-paper-expected-tests could not be loaded ({reason}); CRUST's "
                 "validated_tests_expected will fall back to the native static count", file=sys.stderr)

    rows, failures = collect_all(
        Path(args.runs_root), manifest, variants=variants, project_ids=project_ids,
        repetitions=repetitions, dataset_specs=cfg.get("datasets", {}), timeout=args.timeout,
        reference_results_root=args.reference_results_root,
        crust_paper_expected_tests=crust_paper_expected_tests,
        max_workers=max(1, args.jobs),
    )
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = write_raw_runs(rows, output_root)
    failures_path = write_failures(failures, output_root)
    print(f"[collect] {len(rows)} measured run(s) -> {csv_path}")
    print(f"[collect] {len(failures)} unresolved run(s) -> {failures_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
