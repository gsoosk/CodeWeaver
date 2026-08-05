"""analyze.py -- RQ1-RQ4 analysis over collect.py's raw_runs and
test_compare.py's test_comparisons outputs.

This module NEVER re-measures anything itself (collect.py/test_compare.py own
that): it only loads their already-written JSONL outputs, validates them
against schemas/completeness/provenance, computes aggregate statistics using
ONLY rows with ``run_status``/measurement statuses that indicate a real
measurement, and renders paper-style tables/figures:

  - ``table1_effectiveness.csv/pdf``   (RQ1: compilation success, developer
    test executed/pass/fail + TPR, translated/generated test counts,
    coverage before/after, per-function/milestone validation. The coverage
    pair is sourced from ``generated_test_projects`` (independent developer
    oracle before/after classified CodeWeaver-authored generated tests);
    ``standardized_coverage_*`` remains a separate official-harness
    diagnostic. ``tpr`` is the paper's headline metric and is sourced EXCLUSIVELY from
    ``validated_tests_pass_rate`` -- collect.py's post-hoc, independently
    validated developer-test oracle evaluation -- never from
    ``translated_tests_pass_rate`` (CodeWeaver's own self-graded translated
    tests, kept as a structurally separate column); ``tpr_source`` records
    which one actually backed ``tpr`` for full transparency. Per-function
    validation is likewise execution-based (``function_validation_*``),
    structurally distinct from the symbol/completeness
    ``function_translation_ratio`` column, which is never relabeled as
    validation)
  - ``table2_test_translation.csv/pdf`` (RQ2: translation rate, matching
    assertion-count rate, assertEqual equivalence, assertion-type match,
    embedding similarity, LoC/method-invocation counts -- reuses
    test_compare.py's own ``summarize_comparisons`` per tool, never
    reimplementing that aggregation)
  - ``figure7_ablation.pdf``          (RQ3: TPR + NC/TEC/SEC/LC/ALL
    trajectory-shape metrics per variant, with a paired delta of each
    ablation/baseagent variant's TPR against ``full`` -- Wilcoxon
    signed-rank via scipy when available and valid, else a stdlib
    bootstrap CI of the mean paired difference, else explicitly missing.
    Figure 7's TPR is sourced from the same independently validated
    ``validated_tests_pass_rate`` as Table 1, never from a variant's own
    translated/self-graded tests.)
  - ``figure8_cost_tools.pdf``        (RQ4: input/output tokens, premium
    requests, elapsed time, agent turns, tool invocations per variant.
    Dollar cost is ``Status.NOT_APPLICABLE`` unless a pricing conversion is
    explicitly supplied via ``--pricing-usd-per-premium-request`` --
    GitHub Copilot CLI usage has no built-in dollar API)
  - ``table_generated_tests.csv/pdf`` and ``table_function_validation.csv/pdf``
    (supporting breakdowns backing the RQ1/RQ2 headline tables;
    ``table_function_validation`` reports BOTH the symbol/completeness
    ``function_translation_ratio`` and, where available, execution-based
    ``function_validation_*``/``oracle_integrity`` per project)
  - ``paper_table1_side_by_side.csv``, ``paper_table2_side_by_side.csv``, and
    ``paper_tables_side_by_side.pdf`` (the exact printed paper table rows from
    the pinned official ``results.xlsx``, with measured CodeWeaver values in
    adjacent, source-distinct columns)

Paper reference numbers (``common.PAPER_REFERENCE_TOTALS``) are written to a
SEPARATE file (``table1_paper_reference.csv/pdf``) and a visually distinct
section of the combined table1 PDF -- never blended into a "measured" column,
per the harness's core requirement to keep the two sources structurally
separate.

If there is no measured data to analyze (an empty raw_runs.jsonl, or the file
doesn't exist yet), this module's behavior is controlled entirely by
``--on-empty``:

  - ``watermark`` (default): every artifact that would otherwise be empty is
    still written, but stamped with a literal, unmissable "NO MEASURED DATA"
    watermark (a red heading in the PDF; a leading marker row in the CSV) --
    this module never lets an empty result set silently masquerade as a
    completed analysis.
  - ``fail``: nothing is written and the process exits non-zero, for CI-style
    gating that wants a hard failure rather than a watermarked artifact.

Standard-library-first: all data loading, aggregation, and statistics use
only ``csv``/``json``/``statistics``/``random`` (stdlib). ``scipy`` (for
Wilcoxon) and ``reportlab``/``matplotlib`` (for PDF/figure rendering) are
optional, probed via ``common.optional_import`` and never assumed -- when
absent, this module still writes the full CSV/JSON data and a plain-text
``*.pdf.unavailable.txt`` sibling explaining why the PDF was skipped, rather
than failing outright or fabricating a plot.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import statistics
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent import paper_tables as PTables
from experiments.recodeagent import paper_test_compare as PTcmp
from experiments.recodeagent import test_compare as TCmp
from experiments.recodeagent.common import Measurement, Status, atomic_write_text, read_jsonl, utcnow_iso

SCHEMA_VERSION = 1
NO_MEASURED_DATA_TEXT = "NO MEASURED DATA"

# Paper reference denominator for function-level validation, EXCLUDING CRUST
# (CRUST validates at whole-crate granularity only -- see collect.py -- so it
# has no per-function denominator at all). This is a PAPER REFERENCE number,
# never a measured value, and never blended into any measured row/column
# (see table1_paper_reference_rows/compute_function_validation_table, the
# only two places it is surfaced). Provenance: INDEPENDENTLY VERIFIED in this
# harness's own investigation against the official results.xlsx cache (the
# same artifact common.PAPER_REFERENCE_TOTALS's own totals were checked
# against) -- 1,397 is the exact sum of that spreadsheet's "Exercised"
# (AMF - Not Exercised) column across exactly the Oxidizer + AlphaTrans +
# SKEL project rows (i.e. common.PAPER_REFERENCE_TOTALS["functions"] == 4583
# MINUS the four separate CRUST/"swe-agent crust-bench" rows' own
# contribution). It contextualizes this harness's newly measured
# function_validation_*/function_harness_tests_* execution counts (a
# DIFFERENT unit -- files/harness-tests executed, not per-function coverage)
# for the three tools those fields ever apply to; it is not asserted that
# our own counts should equal it.
FUNCTION_VALIDATION_DENOMINATOR_NON_CRUST = 1397


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_manifest(path: str | Path) -> dict[str, Any]:
    return C.read_json(path)


def load_raw_runs(path: str | Path) -> list[dict[str, Any]]:
    """Reads the JSONL form (never the CSV) so booleans/None/numbers keep
    their native Python types -- CSV would stringify everything, which risks
    silently corrupting this harness's core "missing is not zero" invariant."""
    return read_jsonl(path)


def load_test_comparisons(path: str | Path | None) -> list[dict[str, Any]] | None:
    """Returns None (not []) when the path is None or the file does not
    exist at all -- RQ2 data is optional at analysis time (a user may run
    analyze.py before ever invoking test_compare.py), and "no file" must be
    distinguished from "file exists but is empty"."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return read_jsonl(p)


def load_paper_test_projects(path: str | Path | None) -> list[dict[str, Any]] | None:
    """Load paper_test_compare.py's project-level CSV."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with p.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_generated_test_projects(path: str | Path | None) -> list[dict[str, Any]] | None:
    """Load generated-test CSV, restoring numeric types and empty cells to None."""
    rows = load_paper_test_projects(path)
    if rows is None:
        return None
    integer_fields = {
        "repetition", "generated_target_test_methods", "generated_tests_expected",
        "generated_tests_executed", "generated_tests_passed",
        "generated_tests_failed", "generated_tests_not_executed",
    }
    for row in rows:
        for field in integer_fields:
            value = row.get(field)
            row[field] = (
                None if value in (None, "") else int(float(value))
            )
        for field in (
            "generated_tests_pass_rate", "coverage_before", "coverage_after",
        ):
            value = row.get(field)
            row[field] = None if value in (None, "") else float(value)
    return rows


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #
def validate_rows_against_schema(rows: list[dict[str, Any]], schema_filename: str) -> dict[int, list[str]]:
    """Returns {row_index: [errors]} for every row that fails validation
    (empty dict overall means every row validated cleanly)."""
    schema = C.load_schema(schema_filename)
    errors_by_row: dict[int, list[str]] = {}
    for i, row in enumerate(rows):
        errs = C.validate_schema(row, schema)
        if errs:
            errors_by_row[i] = errs
    return errors_by_row


# --------------------------------------------------------------------------- #
# Completeness: does raw_runs (+failures) cover the FULL expected matrix?
# --------------------------------------------------------------------------- #
def compute_completeness(
    manifest: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    *,
    variants: list[str],
    project_ids: list[str] | None = None,
    repetitions: int = 1,
) -> dict[str, Any]:
    ids = project_ids if project_ids is not None else [p["id"] for p in manifest.get("projects", [])]
    expected = {(v, pid, rep) for v in variants for pid in ids for rep in range(repetitions)}
    measured = {(r.get("variant"), r.get("project_id"), r.get("repetition")) for r in raw_rows}
    missing = sorted(expected - measured)
    return {
        "expected_cells": len(expected),
        "measured_cells": len(expected & measured),
        "coverage_fraction": (len(expected & measured) / len(expected)) if expected else None,
        "missing_cells": [{"variant": v, "project_id": pid, "repetition": rep} for v, pid, rep in missing],
    }


def compute_project_row_completeness(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]] | None,
    *,
    variants: list[str],
    repetitions: int,
    project_ids: list[str] | None = None,
    tools: set[str] | None = None,
) -> dict[str, Any]:
    selected_ids = set(project_ids) if project_ids is not None else None
    ids = [
        str(project["id"])
        for project in manifest.get("projects", [])
        if (selected_ids is None or str(project["id"]) in selected_ids)
        and (tools is None or str(project.get("tool", "")).lower() in tools)
    ]
    expected = {
        (variant, project_id, repetition)
        for variant in variants
        for project_id in ids
        for repetition in range(repetitions)
    }
    keys = [
        (
            str(row.get("variant")),
            str(row.get("project_id")),
            int(row.get("repetition") or 0),
        )
        for row in (rows or [])
    ]
    observed = set(keys)
    missing = sorted(expected - observed)
    return {
        "expected_cells": len(expected),
        "observed_cells": len(expected & observed),
        "coverage_fraction": (len(expected & observed) / len(expected)) if expected else 1.0,
        "duplicate_rows": len(keys) - len(observed),
        "missing_cells": [
            {"variant": variant, "project_id": project_id, "repetition": repetition}
            for variant, project_id, repetition in missing
        ],
    }


# --------------------------------------------------------------------------- #
# Provenance consistency: are all measured runs comparable (same model etc.)?
# --------------------------------------------------------------------------- #
def check_provenance_consistency(raw_rows: list[dict[str, Any]]) -> dict[str, Any]:
    protocol_fields = [
        "model",
        "agent_timeout_seconds",
        "git_sha",
        "codeweaver_package_version",
    ]
    informational_fields = ["copilot_cli_version"]
    fields = protocol_fields + informational_fields
    distinct: dict[str, set[Any]] = {f: set() for f in fields}
    for r in raw_rows:
        for f in fields:
            v = r.get(f)
            if v is not None:
                distinct[f].add(v)
    return {
        "distinct_values": {f: sorted(str(v) for v in vs) for f, vs in distinct.items()},
        "protocol_fields": protocol_fields,
        "informational_fields": informational_fields,
        "consistent": all(len(distinct[f]) <= 1 for f in protocol_fields),
        "strictly_consistent": all(len(vs) <= 1 for vs in distinct.values()),
        "informational_drift": {
            f: sorted(str(v) for v in distinct[f])
            for f in informational_fields
            if len(distinct[f]) > 1
        },
    }


# --------------------------------------------------------------------------- #
# Statistics helpers (standard-library first)
# --------------------------------------------------------------------------- #
def _measured_values(rows: list[dict[str, Any]], field: str, status_field: str | None = None) -> list[float]:
    values: list[float] = []
    for r in rows:
        if status_field is not None and r.get(status_field) != Status.MEASURED:
            continue
        v = r.get(field)
        if v is None:
            continue
        values.append(v)
    return values


def mean_measurement(rows: list[dict[str, Any]], field: str, status_field: str | None = None) -> Measurement:
    """Doubles as a rate calculator for boolean-valued fields (True/False sum
    to 1/0 in Python), e.g. compilation success rate over ``build``."""
    values = _measured_values(rows, field, status_field)
    if not values:
        return Measurement.missing(f"no measured {field!r} values across {len(rows)} row(s)")
    return Measurement.ok(statistics.fmean(values))


def sum_measurement(rows: list[dict[str, Any]], field: str, status_field: str | None = None) -> Measurement:
    values = _measured_values(rows, field, status_field)
    if not values:
        return Measurement.missing(f"no measured {field!r} values across {len(rows)} row(s)")
    return Measurement.ok(sum(values))


def _token_sum(rows: list[dict[str, Any]], field: str, status_field: str) -> Measurement:
    """Use explicit per-direction status on new rows, legacy combined status
    on older collected rows."""
    selected_status = status_field if any(status_field in row for row in rows) else "tokens_status"
    return sum_measurement(rows, field, selected_status)


def paper_equivalent_pass_rate(
    rows: list[dict[str, Any]],
    passed_field: str, passed_status_field: str,
    expected_field: str, expected_status_field: str,
) -> Measurement:
    """The paper's own SUM-based (never a mean-of-per-row-rates) TPR
    aggregation across ``rows``: ``sum(passed) / sum(expected)``, where a
    row is included in BOTH sums whenever its own ``expected`` field is
    itself measured (a row with a non-measured ``passed`` -- e.g. the
    CodeWeaver target failed to build/import -- still contributes its full
    ``expected`` count to the denominator and a ZERO to the numerator,
    mirroring :func:`collect.compute_paper_pass_rate`'s own per-row
    0-substitution rule; it is never silently excluded as an undefined
    row). A naive per-project MEAN of already-computed per-row pass rates
    would NOT reproduce the paper's own weighted aggregate (its own worked
    example: a headline TPR of 1,822/2,107 across many projects) -- a
    project with many expected tests must count proportionally more than
    one with few, exactly like this sum-of-numerators/sum-of-denominators
    formula does."""
    total_expected = 0.0
    total_passed = 0.0
    n_rows = 0
    for r in rows:
        if r.get(expected_status_field) != Status.MEASURED:
            continue
        expected_value = r.get(expected_field)
        if expected_value is None:
            continue
        n_rows += 1
        total_expected += expected_value
        if r.get(passed_status_field) == Status.MEASURED and r.get(passed_field) is not None:
            total_passed += r.get(passed_field)
        # else: a non-measured `passed` contributes 0 to the numerator here,
        # per the paper's own methodology -- NOT an excluded row (its
        # `expected` count above still counts toward the denominator).
    if n_rows == 0:
        return Measurement.missing(f"no row has a measured {expected_field!r} across {len(rows)} row(s)")
    if total_expected == 0:
        return Measurement.na(f"sum of {expected_field!r} across {n_rows} measured row(s) is zero; "
                              "a pass rate is undefined")
    return Measurement.ok(total_passed / total_expected)


def bootstrap_ci(values: list[float], *, resamples: int = 2000, ci: float = 0.95,
                 seed: int = 12345) -> tuple[float, float] | None:
    """Deterministic (fixed-seed), stdlib-only percentile bootstrap CI of the
    mean. Returns None if there are too few values (<2) to resample meaningfully."""
    n = len(values)
    if n < 2:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        means.append(statistics.fmean(values[rng.randrange(n)] for _ in range(n)))
    means.sort()
    lo_idx = int((1 - ci) / 2 * resamples)
    hi_idx = min(int((1 + ci) / 2 * resamples), resamples - 1)
    return means[lo_idx], means[hi_idx]


def paired_delta_test(baseline: list[float], variant: list[float]) -> Measurement:
    """Wilcoxon signed-rank test (scipy, if installed and the differences
    are not degenerate) for a paired comparison; falls back to a stdlib
    bootstrap CI of the mean paired difference; explicitly missing (never
    fabricated) when there are fewer than 2 paired samples."""
    n = min(len(baseline), len(variant))
    if n < 2:
        return Measurement.missing(f"need >= 2 paired samples, got {n}")
    diffs = [v - b for b, v in zip(baseline, variant)]
    mean_delta = statistics.fmean(diffs)
    scipy_stats = C.optional_import("scipy.stats")
    if scipy_stats is not None and any(d != 0 for d in diffs):
        try:
            stat, p_value = scipy_stats.wilcoxon(baseline, variant)
            return Measurement.ok({"test": "wilcoxon", "statistic": float(stat), "p_value": float(p_value),
                                   "n_pairs": n, "mean_delta": mean_delta})
        except ValueError:
            pass   # degenerate input for scipy (e.g. all-zero diffs after ties) -- fall through
    ci = bootstrap_ci(diffs)
    if ci is None:
        return Measurement.missing("insufficient samples for a bootstrap CI")
    return Measurement.ok({"test": "bootstrap_ci_mean_delta", "ci_low": ci[0], "ci_high": ci[1],
                           "n_pairs": n, "mean_delta": mean_delta})


# --------------------------------------------------------------------------- #
# RQ1: table1_effectiveness
# --------------------------------------------------------------------------- #
def compute_table1_measured(
    raw_rows: list[dict[str, Any]],
    test_comparison_rows: list[dict[str, Any]] | None,
    manifest: dict[str, Any],
    *,
    variant: str = "full",
    repetition: int | None = 0,
    generated_test_project_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """One row per tool (plus an "ALL" aggregate row), for exactly ONE
    (variant, repetition) selection -- default the "full" variant's first/
    canonical repetition (the paper's headline effectiveness table reports a
    single run per project, never an ambiguous mixture of variants or a
    repetition-count-scaled sum). Both ``raw_rows`` AND
    ``test_comparison_rows`` are filtered to this SAME (variant, repetition)
    selection: test_compare.py output is keyed by (variant, project,
    repetition) exactly like a raw run, so without this filter a translated/
    generated-test count measured against e.g. the ``noanalyzer`` variant's
    (or a second repetition's) output could silently leak into what is
    supposed to be the ``full`` variant's headline row. Pass
    ``repetition=None`` to intentionally aggregate across every repetition of
    the given variant instead (only meaningful if the caller understands
    summed counts will then scale with repetition count)."""
    def _selected(r: dict[str, Any]) -> bool:
        return r.get("variant") == variant and (repetition is None or r.get("repetition") == repetition)

    variant_rows = [r for r in raw_rows if _selected(r)]
    tc_selected = [r for r in (test_comparison_rows or []) if _selected(r)]
    generated_selected = [
        r for r in (generated_test_project_rows or []) if _selected(r)
    ]
    # Distinguishes "test_compare.py was never run for this (variant,
    # repetition)" (True count fields stay None/missing) from "it was run and
    # genuinely found zero translated/generated tests for a given tool" (a
    # real, reportable 0) -- computed once, at the (variant, repetition)
    # granularity, not per no test_comparison_rows at all.
    tc_available_for_selection = test_comparison_rows is not None and bool(tc_selected)
    loc_by_project = {p["id"]: p.get("loc_source") for p in manifest.get("projects", [])}
    tool_by_project = {p["id"]: p.get("tool") for p in manifest.get("projects", [])}
    tools = sorted({r.get("tool", "") for r in variant_rows} | set(C.DATASET_SPECS.keys()))

    def _row_for(tool: str | None, trows: list[dict[str, Any]]) -> dict[str, Any]:
        tc_rows = [r for r in tc_selected if tool is None or r.get("tool") == tool]
        generated_rows = [
            r for r in generated_selected if tool is None or r.get("tool") == tool
        ]
        translated_count = sum(1 for r in tc_rows if r.get("test_origin") == "translated" and r.get("mapped"))
        generated_count = sum(1 for r in tc_rows if r.get("test_origin") == "generated")
        generated_expected_m = sum_measurement(
            generated_rows, "generated_tests_expected", "generated_tests_expected_status"
        )
        generated_executed_m = sum_measurement(
            generated_rows, "generated_tests_executed", "generated_tests_executed_status"
        )
        generated_passed_m = sum_measurement(
            generated_rows, "generated_tests_passed", "generated_tests_passed_status"
        )
        generated_failed_m = sum_measurement(
            generated_rows, "generated_tests_failed", "generated_tests_failed_status"
        )
        generated_not_executed_m = sum_measurement(
            generated_rows, "generated_tests_not_executed",
            "generated_tests_not_executed_status",
        )
        generated_pass_rate_m = paper_equivalent_pass_rate(
            generated_rows,
            "generated_tests_passed",
            "generated_tests_passed_status",
            "generated_tests_expected",
            "generated_tests_expected_status",
        )
        loc_total = sum(v for pid, v in loc_by_project.items() if v is not None
                       and (tool is None or tool_by_project.get(pid) == tool))
        milestones_passed_m = sum_measurement(trows, "milestones_passed", "milestones_passed_status")
        milestones_total_m = sum_measurement(trows, "milestones_total", "milestones_total_status")
        if milestones_passed_m.is_measured and milestones_total_m.is_measured and milestones_total_m.value > 0:
            milestone_pass_rate = Measurement.ok(milestones_passed_m.value / milestones_total_m.value)
        else:
            milestone_pass_rate = Measurement.missing("milestones_passed/milestones_total not both measured/nonzero")

        # translated_tests_* -- unambiguous aliases of dev_tests_*/dev_test_pass_rate
        # (CodeWeaver's OWN self-reported/self-graded developer tests). Kept
        # structurally separate from validated_tests_* below (the paper's
        # INDEPENDENTLY validated developer-test oracle) so this table can
        # never conflate the two, and so "tpr" (below) is unambiguous about
        # which one it actually reports. expected/not_executed are a
        # best-effort "where possible" analogue of validated_tests_expected/
        # not_executed; translated_tests_pass_rate keeps its EXISTING
        # executed-relative (mean-of-rates) formula unchanged (a documented
        # Scope note -- see dev_test_pass_rate/Figure 7 TPR sourcing).
        translated_tests_executed_m = sum_measurement(trows, "translated_tests_total",
                                                      "translated_tests_total_status")
        translated_tests_passed_m = sum_measurement(trows, "translated_tests_passed",
                                                    "translated_tests_passed_status")
        translated_tests_failed_m = sum_measurement(trows, "translated_tests_failed",
                                                    "translated_tests_failed_status")
        translated_tests_pass_rate_m = mean_measurement(trows, "translated_tests_pass_rate",
                                                        "translated_tests_pass_rate_status")
        translated_tests_expected_m = sum_measurement(trows, "translated_tests_expected",
                                                      "translated_tests_expected_status")
        translated_tests_not_executed_m = sum_measurement(trows, "translated_tests_not_executed",
                                                          "translated_tests_not_executed_status")
        # validated_tests_* -- the paper's INDEPENDENTLY validated developer-test
        # oracle (see collect.py's "POST-HOC INDEPENDENT EVALUATOR"). `expected`
        # is the FIXED, oracle-known denominator (e.g. the paper's own 2,107);
        # `executed` is whatever the test command actually ran (the paper's own
        # TE, e.g. 1,970) -- these two are DELIBERATELY summed separately, never
        # conflated, so a build/import failure that prevented execution never
        # masquerades as a smaller-but-still-successful denominator.
        validated_tests_expected_m = sum_measurement(trows, "validated_tests_expected",
                                                     "validated_tests_expected_status")
        validated_tests_executed_m = sum_measurement(trows, "validated_tests_executed",
                                                     "validated_tests_executed_status")
        validated_tests_passed_m = sum_measurement(trows, "validated_tests_passed", "validated_tests_passed_status")
        validated_tests_failed_m = sum_measurement(trows, "validated_tests_failed", "validated_tests_failed_status")
        validated_tests_not_executed_m = sum_measurement(trows, "validated_tests_not_executed",
                                                         "validated_tests_not_executed_status")
        # The paper's own TPR is passed/expected (a FIXED, oracle-known
        # denominator), NEVER passed/executed -- its own worked example
        # reports 1,822/2,107 despite only TE=1,970 tests actually executing.
        # A naive mean_measurement of already-computed per-row rates would
        # NOT reproduce this weighted aggregate -- see
        # paper_equivalent_pass_rate's own docstring for why a sum-based
        # formula is required instead.
        validated_tests_pass_rate_m = paper_equivalent_pass_rate(
            trows, "validated_tests_passed", "validated_tests_passed_status",
            "validated_tests_expected", "validated_tests_expected_status",
        )
        # tpr is the paper's headline "validated TPR" metric -- it MUST come
        # from the independently validated oracle (validated_tests_pass_rate),
        # never silently from translated/self-reported data. When no
        # validated measurement is available for this selection at all
        # (e.g. --reference-results-root was never supplied, or this tool/
        # selection genuinely has no independent oracle -- see collect.py),
        # tpr is explicitly missing; translated_tests_pass_rate above remains
        # available as its own, clearly-labeled, separate metric.
        if validated_tests_pass_rate_m.is_measured:
            tpr_m = validated_tests_pass_rate_m
            tpr_source = "validated"
        else:
            tpr_m = Measurement.missing(
                "validated_tests_pass_rate not measured for this (tool, variant, repetition) selection -- "
                "tpr is never silently sourced from translated/self-reported dev tests; see "
                "translated_tests_pass_rate for that separate, non-independently-validated metric"
            )
            tpr_source = "unavailable"

        function_validation_executed_m = sum_measurement(trows, "function_validation_total",
                                                         "function_validation_total_status")
        function_validation_passed_m = sum_measurement(trows, "function_validation_passed",
                                                       "function_validation_passed_status")
        function_validation_failed_m = sum_measurement(trows, "function_validation_failed",
                                                       "function_validation_failed_status")
        function_validation_expected_m = sum_measurement(trows, "function_validation_expected",
                                                         "function_validation_expected_status")
        function_validation_not_executed_m = sum_measurement(
            trows, "function_validation_not_executed", "function_validation_not_executed_status"
        )
        function_validation_pass_rate_m = mean_measurement(trows, "function_validation_pass_rate",
                                                           "function_validation_pass_rate_status")
        function_validation_paper_pass_rate_m = paper_equivalent_pass_rate(
            trows, "function_validation_passed", "function_validation_passed_status",
            "function_validation_expected", "function_validation_expected_status",
        )

        # function_harness_tests_* -- standardized GENERATED function/test-
        # harness execution evidence (Oxidizer/AlphaTrans/SKEL),
        # structurally separate from function_validation_* above (which
        # requires a reliable one-to-one per-function mapping neither tool is
        # known to have) -- see collect.py's "POST-HOC INDEPENDENT EVALUATOR".
        function_harness_tests_executed_m = sum_measurement(trows, "function_harness_tests_total",
                                                           "function_harness_tests_total_status")
        function_harness_tests_passed_m = sum_measurement(trows, "function_harness_tests_passed",
                                                         "function_harness_tests_passed_status")
        function_harness_tests_failed_m = sum_measurement(trows, "function_harness_tests_failed",
                                                         "function_harness_tests_failed_status")
        function_harness_tests_expected_m = sum_measurement(
            trows, "function_harness_tests_expected", "function_harness_tests_expected_status"
        )
        function_harness_tests_not_executed_m = sum_measurement(
            trows, "function_harness_tests_not_executed",
            "function_harness_tests_not_executed_status",
        )
        function_harness_tests_pass_rate_m = mean_measurement(trows, "function_harness_tests_pass_rate",
                                                             "function_harness_tests_pass_rate_status")
        function_harness_tests_paper_pass_rate_m = paper_equivalent_pass_rate(
            trows, "function_harness_tests_passed", "function_harness_tests_passed_status",
            "function_harness_tests_expected", "function_harness_tests_expected_status",
        )
        coverage_rows = generated_rows if generated_rows else trows
        coverage_source = (
            "generated_test_projects"
            if generated_rows else
            "raw_runs"
        )
        coverage_before_m = mean_measurement(
            coverage_rows, "coverage_before", "coverage_before_status"
        )
        coverage_after_m = mean_measurement(
            coverage_rows, "coverage_after", "coverage_after_status"
        )

        # oracle_integrity is categorical (CRUST only; every other tool is
        # not_applicable -- see collect.py), so it is summarized here as
        # plain counts, never averaged/faked as a rate: each count is a real,
        # always-well-defined fact (e.g. "0 mutated" is legitimate), unlike a
        # rate over a possibly-zero denominator.
        oracle_integrity_values = [r.get("oracle_integrity") for r in trows
                                  if r.get("oracle_integrity_status") == Status.MEASURED]
        oracle_integrity_pristine_count = sum(1 for v in oracle_integrity_values if v == "pristine")
        oracle_integrity_mutated_count = sum(1 for v in oracle_integrity_values if v == "mutated")
        oracle_integrity_not_copied_count = sum(1 for v in oracle_integrity_values if v == "not_copied")

        return {
            "source": "measured_codeweaver", "tool": tool or "ALL", "variant": variant,
            "repetition": repetition, "measured_run_count": len(trows),
            **mean_measurement(trows, "build", "build_status").flatten("compilation_success_rate"),
            **sum_measurement(
                trows, "project_pass_all", "project_pass_all_status"
            ).flatten("projects_pass_all"),
            **mean_measurement(
                trows, "project_pass_all", "project_pass_all_status"
            ).flatten("project_pass_all_rate"),
            **sum_measurement(trows, "dev_tests_total", "dev_tests_total_status").flatten("dev_tests_executed"),
            **sum_measurement(trows, "dev_tests_passed", "dev_tests_passed_status").flatten("dev_tests_passed"),
            **sum_measurement(trows, "dev_tests_failed", "dev_tests_failed_status").flatten("dev_tests_failed"),
            **translated_tests_executed_m.flatten("translated_tests_executed"),
            **translated_tests_passed_m.flatten("translated_tests_passed"),
            **translated_tests_failed_m.flatten("translated_tests_failed"),
            **translated_tests_pass_rate_m.flatten("translated_tests_pass_rate"),
            **translated_tests_expected_m.flatten("translated_tests_expected"),
            **translated_tests_not_executed_m.flatten("translated_tests_not_executed"),
            **validated_tests_expected_m.flatten("validated_tests_expected"),
            **validated_tests_executed_m.flatten("validated_tests_executed"),
            **validated_tests_passed_m.flatten("validated_tests_passed"),
            **validated_tests_failed_m.flatten("validated_tests_failed"),
            **validated_tests_not_executed_m.flatten("validated_tests_not_executed"),
            **validated_tests_pass_rate_m.flatten("validated_tests_pass_rate"),
            **tpr_m.flatten("tpr"),
            "tpr_source": tpr_source,
            "oracle_integrity_pristine_count": oracle_integrity_pristine_count,
            "oracle_integrity_mutated_count": oracle_integrity_mutated_count,
            "oracle_integrity_not_copied_count": oracle_integrity_not_copied_count,
            "translated_dev_tests_count": translated_count if tc_available_for_selection else None,
            "generated_tests_count": (
                generated_expected_m.value if generated_expected_m.is_measured
                else (generated_count if tc_available_for_selection else None)
            ),
            **generated_expected_m.flatten("generated_tests_expected"),
            **generated_executed_m.flatten("generated_tests_executed"),
            **generated_passed_m.flatten("generated_tests_passed"),
            **generated_failed_m.flatten("generated_tests_failed"),
            **generated_not_executed_m.flatten("generated_tests_not_executed"),
            **generated_pass_rate_m.flatten("generated_tests_pass_rate"),
            **coverage_before_m.flatten("coverage_before"),
            **coverage_after_m.flatten("coverage_after"),
            "coverage_source": coverage_source,
            **mean_measurement(
                trows,
                "standardized_coverage_before",
                "standardized_coverage_before_status",
            ).flatten("standardized_coverage_before"),
            **mean_measurement(
                trows,
                "standardized_coverage_after",
                "standardized_coverage_after_status",
            ).flatten("standardized_coverage_after"),
            **mean_measurement(trows, "function_translation_ratio",
                              "function_translation_ratio_status").flatten("function_translation_ratio"),
            **function_validation_executed_m.flatten("function_validation_executed"),
            **function_validation_passed_m.flatten("function_validation_passed"),
            **function_validation_failed_m.flatten("function_validation_failed"),
            **function_validation_expected_m.flatten("function_validation_expected"),
            **function_validation_not_executed_m.flatten("function_validation_not_executed"),
            **function_validation_pass_rate_m.flatten("function_validation_pass_rate"),
            **function_validation_paper_pass_rate_m.flatten("function_validation_paper_pass_rate"),
            **function_harness_tests_executed_m.flatten("function_harness_tests_executed"),
            **function_harness_tests_passed_m.flatten("function_harness_tests_passed"),
            **function_harness_tests_failed_m.flatten("function_harness_tests_failed"),
            **function_harness_tests_expected_m.flatten("function_harness_tests_expected"),
            **function_harness_tests_not_executed_m.flatten("function_harness_tests_not_executed"),
            **function_harness_tests_pass_rate_m.flatten("function_harness_tests_pass_rate"),
            **function_harness_tests_paper_pass_rate_m.flatten("function_harness_tests_paper_pass_rate"),
            **milestones_passed_m.flatten("milestones_passed_total"),
            **milestones_total_m.flatten("milestones_total_total"),
            **milestone_pass_rate.flatten("milestone_pass_rate"),
            "loc_source_total": loc_total,
        }

    rows = [_row_for(tool, [r for r in variant_rows if r.get("tool") == tool]) for tool in tools]
    rows.append(_row_for(None, variant_rows))
    return rows



def table1_paper_reference_rows() -> list[dict[str, Any]]:
    t = C.PAPER_REFERENCE_TOTALS
    by_tool = C.PAPER_REFERENCE_VALIDATED_TESTS_BY_TOOL
    return [{
        "source": "paper_reference", "tool": "ALL",
        "total_loc": t["total_loc"], "total_loc_precise": t.get("total_loc_precise"),
        "validated_tests": t["validated_tests"],
        # Per-tool breakdown of the "validated_tests" total immediately above
        # (see common.PAPER_REFERENCE_VALIDATED_TESTS_BY_TOOL's own provenance
        # comment) -- sums exactly to "validated_tests" (623 + 229 + 1181 + 74
        # == 2107). Purely paper-reference context for comparing against this
        # harness's own per-tool MEASURED validated_tests_* fields in
        # table1_effectiveness.csv when --reference-results-root was supplied;
        # never asserted as a target those measured counts must reproduce.
        "validated_tests_crust": by_tool["crust"],
        "validated_tests_oxidizer": by_tool["oxidizer"],
        "validated_tests_alphatrans": by_tool["alphatrans"],
        "validated_tests_skel": by_tool["skel"],
        # CRUST is excluded from this figure per the paper's own protocol (see PAPER_REFERENCE_TOTALS).
        "translated_tests_excluding_crust": t["translated_tests"], "functions": t["functions"],
        # Paper reference denominator for function_validation_*/function_harness_tests_*
        # (both of which are NEVER applicable/measured for CRUST -- see collect.py) --
        # independently verified in this module against the official results.xlsx cache:
        # the sum of its "Exercised" column across exactly the Oxidizer/AlphaTrans/SKEL
        # rows (i.e. `functions` above MINUS CRUST's own "Exercised" contribution). Kept
        # structurally separate from every measured row/column above -- never blended,
        # never implied to be a target our own harness's counts must reproduce (this
        # harness's function_harness_tests_*/function_validation_* measure EXECUTION
        # of specific generated-test/harness FILES, a different unit from the paper's
        # own per-function coverage-"Exercised" denominator).
        "function_validation_denominator_non_crust": FUNCTION_VALIDATION_DENOMINATOR_NON_CRUST,
    }]




# --------------------------------------------------------------------------- #
# RQ2: table2_test_translation -- reuses test_compare.py's own aggregation
# --------------------------------------------------------------------------- #
def compute_table2(test_comparison_rows: list[dict[str, Any]], *,
                   variant: str = "full", repetition: int | None = 0) -> list[dict[str, Any]]:
    """Aggregated per-tool RQ2 table for exactly ONE (variant, repetition)
    selection (see :func:`compute_table1_measured` for why this filter
    exists: test_comparison_rows spans every (variant, project, repetition)
    test_compare.py was run against, and without this filter a "full"-labeled
    table could silently include another variant's -- or another
    repetition's -- test mappings). Pass ``variant=None`` to intentionally
    aggregate across every variant/repetition instead."""
    selected = [r for r in test_comparison_rows
               if (variant is None or r.get("variant") == variant)
               and (repetition is None or r.get("repetition") == repetition)]
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for r in selected:
        by_tool.setdefault(r.get("tool", ""), []).append(r)
    rows = [{"tool": tool, **TCmp.summarize_comparisons(trows)} for tool, trows in sorted(by_tool.items())]
    rows.append({"tool": "ALL", **TCmp.summarize_comparisons(selected)})
    return rows


def _numeric(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _paper_table2_aggregate(
    rows: list[dict[str, Any]], *, tool: str, project: str,
) -> dict[str, Any]:
    def total(field: str) -> int:
        return int(sum(_numeric(row, field) or 0 for row in rows))

    def weighted(field: str, weight_field: str) -> float | None:
        pairs = [
            (_numeric(row, field), _numeric(row, weight_field))
            for row in rows
        ]
        usable = [(value, weight) for value, weight in pairs if value is not None and weight not in (None, 0)]
        if not usable:
            return None
        denominator = sum(weight for _value, weight in usable)
        return sum(value * weight for value, weight in usable) / denominator

    def percentage(good_field: str, total_field: str) -> float | None:
        denominator = total(total_field)
        return 100.0 * total(good_field) / denominator if denominator else None

    runtime_tests = total("paper_runtime_tests")
    mapped_runtime = total("mapped_runtime_cases")
    comparable = total("assert_equal_comparable")
    matching = total("assert_equal_matching")
    return {
        "tool": tool,
        "project": project,
        "tests": runtime_tests,
        "tests_translated": mapped_runtime,
        "tests_not_translated": runtime_tests - mapped_runtime,
        "assertion_count_matching_tests": total("assertion_count_runtime_matches"),
        "assertion_count_nonmatching_tests": total("assertion_count_runtime_mismatches"),
        "assert_equal_output_total": comparable,
        "assert_equal_output_matching": matching,
        "assert_equal_output_match_percent": 100.0 * matching / comparable if comparable else None,
        "assert_equal_type_match_percent": percentage("assert_equal_type_good", "assert_equal_type_total"),
        "assert_true_type_match_percent": percentage("assert_true_type_good", "assert_true_type_total"),
        "assert_false_type_match_percent": percentage("assert_false_type_good", "assert_false_type_total"),
        "other_type_match_percent": percentage("other_type_good", "other_type_total"),
        "avg_cosine_similarity": weighted("avg_cosine_similarity", "embedding_similarity_count"),
        "avg_source_loc": weighted("avg_source_loc", "both_ast_methods_found"),
        "avg_target_loc": weighted("avg_target_loc", "both_ast_methods_found"),
        "avg_source_method_calls": weighted("avg_source_method_calls", "both_ast_methods_found"),
        "avg_target_method_calls": weighted("avg_target_method_calls", "both_ast_methods_found"),
        "static_source_methods": total("static_source_methods"),
        "generated_target_test_methods": total("generated_target_test_methods"),
        "protocol": "official ReCodeAgent AST comparator + exact runtime weights",
    }


def compute_paper_table2(
    project_rows: list[dict[str, Any]], *, variant: str = "full",
    repetition: int | None = 0,
) -> list[dict[str, Any]]:
    """Paper-equivalent Table 2 from paper_test_compare.py output."""
    selected = [
        row for row in project_rows
        if row.get("variant") == variant
        and (repetition is None or int(row.get("repetition") or 0) == repetition)
    ]
    out: list[dict[str, Any]] = []
    for tool in PTcmp.LANGUAGE_FIELDS:
        tool_rows = [row for row in selected if row.get("tool") == tool]
        for row in sorted(tool_rows, key=lambda item: str(item.get("project") or "")):
            out.append(_paper_table2_aggregate(
                [row], tool=tool, project=str(row.get("project") or ""),
            ))
        if tool_rows:
            out.append(_paper_table2_aggregate(tool_rows, tool=tool, project="Total"))
    if selected:
        out.append(_paper_table2_aggregate(selected, tool="ALL", project="Total"))
    return out


def compute_paper_generated_tests_table(
    project_rows: list[dict[str, Any]], *, variant: str = "full",
    repetition: int | None = 0,
    generated_test_project_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    selected = [
        row for row in project_rows
        if row.get("variant") == variant
        and (repetition is None or int(row.get("repetition") or 0) == repetition)
    ]
    generated_selected = [
        row for row in (generated_test_project_rows or [])
        if row.get("variant") == variant
        and (repetition is None or int(row.get("repetition") or 0) == repetition)
    ]
    by_project = {str(row.get("project_id")): row for row in selected}
    execution_by_project = {
        str(row.get("project_id")): row for row in generated_selected
    }
    project_ids = sorted(
        set(by_project) | set(execution_by_project),
        key=lambda pid: (
            str((execution_by_project.get(pid) or by_project.get(pid) or {}).get("tool")),
            str((execution_by_project.get(pid) or by_project.get(pid) or {}).get("project")),
        ),
    )
    rows: list[dict[str, Any]] = []
    for project_id in project_ids:
        structural = by_project.get(project_id, {})
        execution = execution_by_project.get(project_id, {})
        row = {
            "project_id": project_id,
            "tool": execution.get("tool") or structural.get("tool"),
            "project": execution.get("project") or structural.get("project"),
            "translated_runtime_tests": (
                int(_numeric(structural, "mapped_runtime_cases") or 0)
                if structural else None
            ),
            "generated_target_test_methods": int(
                _numeric(execution or structural, "generated_target_test_methods") or 0
            ),
            "classification": (
                "target tests unmatched after one-to-one source inventory mapping; "
                "CRUST uses tests/binaries absent from its immutable scaffold"
            ),
        }
        for key in (
            "generated_tests_expected", "generated_tests_executed",
            "generated_tests_passed", "generated_tests_failed",
            "generated_tests_not_executed", "generated_tests_pass_rate",
            "coverage_before", "coverage_after",
        ):
            row[key] = _numeric(execution, key)
            row[f"{key}_status"] = execution.get(f"{key}_status")
            row[f"{key}_reason"] = execution.get(f"{key}_reason")
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# RQ3: figure7_ablation -- TPR + NC/TEC/SEC/LC/ALL per variant, paired vs full
# --------------------------------------------------------------------------- #
def compute_ablation_metrics(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for r in raw_rows:
        by_variant.setdefault(r.get("variant", ""), []).append(r)
    full_rows = by_variant.get("full", [])
    full_tpr_by_project = {
        r["project_id"]: r["validated_tests_pass_rate"] for r in full_rows
        if r.get("validated_tests_pass_rate_status") == Status.MEASURED
    }

    rows = []
    for variant in C.RUN_VARIANTS:
        vrows = by_variant.get(variant, [])
        sec_totals: dict[str, float] = {}
        sec_n = 0
        for r in vrows:
            raw_sec = r.get("sec_json")
            if not raw_sec:
                continue
            try:
                sec = json.loads(raw_sec)
            except (TypeError, ValueError):
                continue
            sec_n += 1
            for stage, count in sec.items():
                sec_totals[stage] = sec_totals.get(stage, 0) + count
        sec_means = {stage: total / sec_n for stage, total in sec_totals.items()} if sec_n else {}

        if variant == "full":
            delta = Measurement.na("baseline variant (full) has no delta against itself")
        else:
            paired_base, paired_var = [], []
            for r in vrows:
                pid = r.get("project_id")
                if pid in full_tpr_by_project and r.get("validated_tests_pass_rate_status") == Status.MEASURED:
                    paired_base.append(full_tpr_by_project[pid])
                    paired_var.append(r["validated_tests_pass_rate"])
            delta = paired_delta_test(paired_base, paired_var)

        rows.append({
            "variant": variant, "measured_run_count": len(vrows),
            **mean_measurement(
                vrows, "validated_tests_pass_rate", "validated_tests_pass_rate_status"
            ).flatten("tpr"),
            **mean_measurement(vrows, "nc").flatten("nc"),
            **mean_measurement(vrows, "tec").flatten("tec"),
            **mean_measurement(vrows, "lc").flatten("lc"),
            **mean_measurement(vrows, "all").flatten("all"),
            "sec_mean_json": json.dumps(sec_means, sort_keys=True),
            "tpr_delta_vs_full_status": delta.status, "tpr_delta_vs_full_reason": delta.reason,
            "tpr_delta_vs_full_json": json.dumps(delta.value) if delta.value is not None else "null",
        })
    return rows


def compute_ablation_metrics_by_tool(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Paper-layout Figure 7 data: every benchmark x ablation cell.

    Test validation uses the independent fixed oracle. Trajectory columns are
    explicitly CodeWeaver/Burr proxies, not claimed to be Graphectory values.
    """
    rows: list[dict[str, Any]] = []
    for tool in C.DATASET_SPECS:
        tool_rows = [row for row in raw_rows if row.get("tool") == tool]
        for variant in C.RUN_VARIANTS:
            vrows = [row for row in tool_rows if row.get("variant") == variant]
            loop_lengths = [
                float(row["tec"]) / max(float(row["lc"]), 1.0)
                for row in vrows
                if row.get("tec") is not None and row.get("lc") is not None
            ]
            average_loop_length = (
                Measurement.ok(statistics.fmean(loop_lengths))
                if loop_lengths
                else Measurement.missing("no measured TEC/LC proxy pairs")
            )
            tpr = paper_equivalent_pass_rate(
                vrows,
                "validated_tests_passed", "validated_tests_passed_status",
                "validated_tests_expected", "validated_tests_expected_status",
            )
            rows.append({
                "tool": tool,
                "variant": variant,
                "measured_run_count": len(vrows),
                **tpr.flatten("test_validation_rate"),
                **mean_measurement(vrows, "nc").flatten("nc_proxy"),
                **mean_measurement(vrows, "tec").flatten("tec_proxy"),
                **mean_measurement(vrows, "total_tool_invocations").flatten("sec_proxy"),
                **mean_measurement(vrows, "lc").flatten("lc_proxy"),
                **average_loop_length.flatten("average_loop_length_proxy"),
                "trajectory_semantics": (
                    "CodeWeaver Burr/Copilot event proxy; not exact Graphectory semantics"
                ),
            })
    return rows


# --------------------------------------------------------------------------- #
# RQ4: figure8_cost_tools -- tokens/credits/elapsed/turns/tool invocations
# --------------------------------------------------------------------------- #
def compute_cost_metrics(raw_rows: list[dict[str, Any]], *,
                        pricing_usd_per_premium_request: float | None = None) -> list[dict[str, Any]]:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for r in raw_rows:
        by_variant.setdefault(r.get("variant", ""), []).append(r)

    rows = []
    for variant in C.RUN_VARIANTS:
        vrows = by_variant.get(variant, [])
        premium_m = sum_measurement(vrows, "total_premium_requests")
        if pricing_usd_per_premium_request is not None and premium_m.is_measured:
            dollar_cost = Measurement.ok(premium_m.value * pricing_usd_per_premium_request)
        else:
            dollar_cost = Measurement.na(
                "no documented pricing conversion supplied (--pricing-usd-per-premium-request); "
                "GitHub Copilot CLI usage has no built-in dollar-cost API"
            )
        rows.append({
            "variant": variant, "measured_run_count": len(vrows),
            **_token_sum(vrows, "total_input_tokens", "input_tokens_status").flatten("total_input_tokens"),
            **_token_sum(vrows, "total_output_tokens", "output_tokens_status").flatten("total_output_tokens"),
            **premium_m.flatten("total_premium_requests"),
            **sum_measurement(vrows, "total_nano_aiu", "nano_aiu_status").flatten("total_nano_aiu"),
            **mean_measurement(vrows, "elapsed_seconds", "elapsed_seconds_status").flatten("elapsed_seconds_mean"),
            **sum_measurement(vrows, "total_session_duration_ms").flatten("total_session_duration_ms"),
            **sum_measurement(vrows, "total_assistant_turns").flatten("total_assistant_turns"),
            **sum_measurement(vrows, "total_tool_invocations").flatten("total_tool_invocations"),
            "tool_counts_json": json.dumps(_sum_tool_counts(vrows), sort_keys=True),
            **dollar_cost.flatten("dollar_cost_usd"),
        })
    return rows


def _sum_tool_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        raw = row.get("tool_counts_json")
        if not raw:
            continue
        try:
            counts = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(counts, dict):
            continue
        for name, count in counts.items():
            if isinstance(name, str) and isinstance(count, (int, float)):
                totals[name] = totals.get(name, 0) + int(count)
    return totals


def compute_cost_metrics_by_tool(
    raw_rows: list[dict[str, Any]], *, variant: str = "full",
    repetition: int | None = 0,
    pricing_usd_per_premium_request: float | None = None,
) -> list[dict[str, Any]]:
    """Paper-aligned Figure 8 aggregation: one row per benchmark tool."""
    selected = [
        row for row in raw_rows
        if row.get("variant") == variant
        and (repetition is None or row.get("repetition") == repetition)
    ]
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in selected:
        by_tool.setdefault(str(row.get("tool") or ""), []).append(row)
    rows: list[dict[str, Any]] = []
    for tool in C.DATASET_SPECS:
        trows = by_tool.get(tool, [])
        premium = sum_measurement(trows, "total_premium_requests")
        if pricing_usd_per_premium_request is not None and premium.is_measured:
            dollar_cost = Measurement.ok(premium.value * pricing_usd_per_premium_request)
        else:
            dollar_cost = Measurement.na(
                "no documented pricing conversion supplied; NanoAIU is reported as the "
                "measured Copilot compute-cost proxy"
            )
        rows.append({
            "tool": tool,
            "variant": variant,
            "measured_run_count": len(trows),
            **_token_sum(trows, "total_input_tokens", "input_tokens_status").flatten("total_input_tokens"),
            **_token_sum(trows, "total_output_tokens", "output_tokens_status").flatten("total_output_tokens"),
            **premium.flatten("total_premium_requests"),
            **sum_measurement(trows, "total_nano_aiu", "nano_aiu_status").flatten("total_nano_aiu"),
            **mean_measurement(trows, "elapsed_seconds", "elapsed_seconds_status").flatten("elapsed_seconds_mean"),
            **sum_measurement(trows, "total_assistant_turns").flatten("total_assistant_turns"),
            **sum_measurement(trows, "total_tool_invocations").flatten("total_tool_invocations"),
            "tool_counts_json": json.dumps(_sum_tool_counts(trows), sort_keys=True),
            **dollar_cost.flatten("dollar_cost_usd"),
        })
    return rows


# --------------------------------------------------------------------------- #
# Supporting tables
# --------------------------------------------------------------------------- #
def compute_generated_tests_table(test_comparison_rows: list[dict[str, Any]], *,
                                  variant: str = "full", repetition: int | None = 0) -> list[dict[str, Any]]:
    """Per-project translated/generated/missing test counts for exactly ONE
    (variant, repetition) selection (see :func:`compute_table1_measured`):
    grouping only by ``project_id`` without this filter would silently sum
    counts from different variants -- or different repetitions of the SAME
    variant -- into a single project entry, inflating every count whenever
    more than one variant/repetition has been measured for that project.
    Pass ``variant=None`` to intentionally aggregate across every variant/
    repetition instead."""
    selected = [r for r in test_comparison_rows
               if (variant is None or r.get("variant") == variant)
               and (repetition is None or r.get("repetition") == repetition)]
    by_project: dict[str, dict[str, Any]] = {}
    for r in selected:
        pid = r.get("project_id", "")
        entry = by_project.setdefault(pid, {"project_id": pid, "tool": r.get("tool", ""),
                                           "translated_count": 0, "generated_count": 0, "missing_count": 0})
        origin = r.get("test_origin")
        if origin == "translated":
            entry["translated_count"] += 1
        elif origin == "generated":
            entry["generated_count"] += 1
        elif not r.get("mapped"):
            entry["missing_count"] += 1
    return [by_project[pid] for pid in sorted(by_project)]


def compute_function_validation_table(raw_rows: list[dict[str, Any]], *,
                                      variant: str = "full",
                                      repetition: int | None = 0) -> list[dict[str, Any]]:
    """Per-project function/milestone validation for exactly ONE (variant,
    repetition) selection, matching table1/table2/generated-tests (see
    :func:`compute_table1_measured`). Pass ``repetition=None`` to
    intentionally aggregate across every repetition of the given variant.

    Reports THREE structurally distinct kinds of "function validation" per
    project, never conflated:

      - ``function_translation_ratio`` -- a symbol/stub COMPLETENESS ratio
        (target_function_count / source_function_count). This is NOT
        execution-based validation; it only says a same-named symbol exists.
      - ``function_validation_total/passed/failed/pass_rate`` -- an
        EXECUTION-based result from collect.py's post-hoc independent
        oracle, requiring a RELIABLE one-to-one per-function mapping
        (currently only available for Oxidizer, when
        ``--reference-results-root`` is supplied; ``Status.NOT_APPLICABLE``
        for CRUST and ``Status.UNAVAILABLE`` for AlphaTrans/SKEL, which have
        no such reliable mapping, and for Oxidizer without the reference
        root -- see collect.py's ``evaluate_independent_oracle``).
      - ``function_harness_tests_total/passed/failed/pass_rate`` -- standardized
        GENERATED harness execution for Oxidizer's ``*generated*.rs``,
        AlphaTrans's pinned ``agent_test/`` files, and SKEL's generated
        scripts. It is never inferred/relabeled as per-function validation.
        ``Status.NOT_APPLICABLE`` for CRUST and ``Status.UNAVAILABLE`` without
        the reference root.

    ``oracle_integrity`` (CRUST-only; ``not_applicable`` elsewhere) is also
    surfaced here so a mutated CRUST target-test tree is visible alongside
    its (still-pristine) function/milestone data."""
    rows = []
    for r in raw_rows:
        if r.get("variant") != variant:
            continue
        if repetition is not None and r.get("repetition") != repetition:
            continue
        rows.append({
            "project_id": r.get("project_id"), "tool": r.get("tool"),
            "source_function_count": r.get("source_function_count"),
            "target_function_count": r.get("target_function_count"),
            "target_function_count_status": r.get("target_function_count_status"),
            "function_translation_ratio": r.get("function_translation_ratio"),
            "function_translation_ratio_status": r.get("function_translation_ratio_status"),
            "function_validation_total": r.get("function_validation_total"),
            "function_validation_total_status": r.get("function_validation_total_status"),
            "function_validation_passed": r.get("function_validation_passed"),
            "function_validation_failed": r.get("function_validation_failed"),
            "function_validation_expected": r.get("function_validation_expected"),
            "function_validation_expected_status": r.get("function_validation_expected_status"),
            "function_validation_not_executed": r.get("function_validation_not_executed"),
            "function_validation_not_executed_status": r.get("function_validation_not_executed_status"),
            "function_validation_pass_rate": r.get("function_validation_pass_rate"),
            "function_validation_pass_rate_status": r.get("function_validation_pass_rate_status"),
            "function_validation_paper_pass_rate": r.get("function_validation_paper_pass_rate"),
            "function_validation_paper_pass_rate_status": r.get("function_validation_paper_pass_rate_status"),
            "function_harness_tests_total": r.get("function_harness_tests_total"),
            "function_harness_tests_total_status": r.get("function_harness_tests_total_status"),
            "function_harness_tests_passed": r.get("function_harness_tests_passed"),
            "function_harness_tests_failed": r.get("function_harness_tests_failed"),
            "function_harness_tests_pass_rate": r.get("function_harness_tests_pass_rate"),
            "function_harness_tests_pass_rate_status": r.get("function_harness_tests_pass_rate_status"),
            "oracle_integrity": r.get("oracle_integrity"),
            "oracle_integrity_status": r.get("oracle_integrity_status"),
            "milestones_passed": r.get("milestones_passed"), "milestones_total": r.get("milestones_total"),
            "milestone_granularity": r.get("milestone_granularity"),
        })
    return sorted(rows, key=lambda r: (r["tool"] or "", r["project_id"] or ""))



# --------------------------------------------------------------------------- #
# Rendering: CSV
# --------------------------------------------------------------------------- #
def _write_csv(rows: list[dict[str, Any]], columns: list[str], path: Path) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    atomic_write_text(path, buf.getvalue())


def _all_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                columns.append(k)
    return columns


def write_no_measured_data_csv(path: Path, columns: list[str], *, reason: str) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([NO_MEASURED_DATA_TEXT])
    writer.writerow(["reason", reason])
    writer.writerow(["generated_at", utcnow_iso()])
    if columns:
        writer.writerow(columns)
    atomic_write_text(path, buf.getvalue())


# --------------------------------------------------------------------------- #
# Rendering: PDF (reportlab for tables, matplotlib for bar-chart figures) --
# both optional; a plain-text sibling replaces a PDF that could not be built.
# --------------------------------------------------------------------------- #
def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_pdf_unavailable_notice(path: Path, *, title: str, why: str) -> None:
    atomic_write_text(Path(str(path) + ".unavailable.txt"),
                      f"{title}\n\nPDF not rendered: {why}. See the sibling .csv for the same data.\n")


def render_table_pdf(rows: list[dict[str, Any]], columns: list[str], *, title: str, path: Path,
                     subtitle: str = "") -> bool:
    reportlab = C.optional_import("reportlab")
    if reportlab is None:
        _write_pdf_unavailable_notice(path, title=title, why="reportlab is not installed in this environment")
        return False
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=landscape(letter))
    elements: list[Any] = [Paragraph(title, styles["Title"])]
    if subtitle:
        elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Spacer(1, 12))
    data = [columns] + [[_cell_text(r.get(c)) for c in columns] for r in rows]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
    ]))
    elements.append(table)
    doc.build(elements)
    return True


def render_watermark_pdf(path: Path, *, title: str, reason: str) -> bool:
    reportlab = C.optional_import("reportlab")
    if reportlab is None:
        _write_pdf_unavailable_notice(path, title=f"{NO_MEASURED_DATA_TEXT}: {title}",
                                      why="reportlab is not installed in this environment")
        return False
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    watermark_style = ParagraphStyle("watermark", parent=styles["Title"], fontSize=36, textColor=colors.red)
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    elements = [
        Paragraph(NO_MEASURED_DATA_TEXT, watermark_style), Spacer(1, 24),
        Paragraph(title, styles["Heading2"]), Spacer(1, 12),
        Paragraph(reason, styles["Normal"]), Spacer(1, 12),
        Paragraph(f"generated_at: {utcnow_iso()}", styles["Normal"]),
    ]
    doc.build(elements)
    return True


def _partition_series_for_plot(xs: list[float], values: list[float | None]) -> tuple[list[float], list[float], list[float]]:
    """Split one bar-chart series' plotted x-positions by whether the paired
    measurement is present. Returns ``(real_xs, real_ys, missing_xs)``.

    ``None`` entries (a measurement that was never collected -- e.g. an
    ablation variant for which a metric is not defined, or a run that has not
    completed yet) are NEVER coerced into a plotted ``0``: doing so would make
    "not measured" visually indistinguishable from "measured, and the value
    really was zero", which is exactly the kind of silent fabrication this
    harness must avoid. Missing entries are instead reported separately as
    ``missing_xs`` so the caller can render them as a distinct placeholder
    marker (see ``render_bar_figure_pdf``) rather than an ordinary data bar.

    This is a pure, matplotlib-free helper specifically so the "never coerce
    None to 0" invariant can be unit tested without requiring matplotlib to be
    installed."""
    real_xs: list[float] = []
    real_ys: list[float] = []
    missing_xs: list[float] = []
    for x, v in zip(xs, values):
        if v is None:
            missing_xs.append(x)
        else:
            real_xs.append(x)
            real_ys.append(float(v))
    return real_xs, real_ys, missing_xs


def _build_bar_figure(categories: list[str], series: dict[str, list[float | None]], *, title: str, ylabel: str):
    """Build (but do not save/close) the grouped-bar ``(fig, ax)`` used by
    ``render_bar_figure_pdf``. Split out so tests can inspect the resulting
    ``Axes`` (patches/text annotations) directly, without needing to parse a
    rendered PDF, to verify missing values are represented distinctly.

    Missing (``None``) measurements are rendered as a small hatched, unfilled
    placeholder bar annotated "N/A" -- never as an ordinary zero-height bar --
    per ``_partition_series_for_plot``'s contract."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    n_categories = max(len(categories), 1)
    n_series = max(len(series), 1)
    width = 0.8 / n_series
    fig, ax = plt.subplots(figsize=(max(8, n_categories * 1.4), 5))

    # Scale the missing-value placeholder marker to the real data range so it
    # is visible but obviously not an ordinary data bar; never 0 height (a 0
    # height placeholder would be as ambiguous as the bug this replaces).
    all_real_values = [v for values in series.values() for v in values if v is not None]
    marker_height = max((abs(v) for v in all_real_values), default=1.0) * 0.04 or 0.04

    any_missing = False
    for i, (label, values) in enumerate(series.items()):
        xs = [j + i * width for j in range(n_categories)]
        real_xs, real_ys, missing_xs = _partition_series_for_plot(xs, values)
        if real_xs:
            ax.bar(real_xs, real_ys, width=width, label=label)
        else:
            # Series has no real values at all; still register a legend entry
            # for it (an empty bar container), rather than silently plotting
            # nothing and nothing in the legend either.
            ax.bar([], [], width=width, label=label)
        for mx in missing_xs:
            any_missing = True
            ax.bar([mx], [marker_height], width=width, facecolor="none", edgecolor="#999999",
                  hatch="////", linewidth=0.8, zorder=3)
            ax.text(mx, marker_height, "N/A", ha="center", va="bottom", fontsize=6, color="#666666", rotation=90)

    ax.set_xticks([j + (n_series - 1) * width / 2 for j in range(n_categories)])
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    handles, labels = ax.get_legend_handles_labels()
    if any_missing:
        handles = handles + [Patch(facecolor="none", edgecolor="#999999", hatch="////")]
        labels = labels + ["N/A (not measured)"]
    if handles:
        ax.legend(handles, labels)
    return fig, ax


def render_bar_figure_pdf(categories: list[str], series: dict[str, list[float | None]], *, title: str,
                         ylabel: str, path: Path) -> bool:
    """Render a grouped bar chart (Figure 7/Figure 8 style). Missing
    measurements (``None`` entries in ``series``) are represented distinctly
    from real zero values via a hatched "N/A" placeholder marker -- see
    ``_build_bar_figure``/``_partition_series_for_plot`` -- instead of being
    silently coerced to a plotted ``0``."""
    mpl = C.optional_import("matplotlib")
    if mpl is None:
        _write_pdf_unavailable_notice(path, title=title, why="matplotlib is not installed in this environment")
        return False
    mpl.use("Agg")
    import matplotlib.pyplot as plt

    fig, _ax = _build_bar_figure(categories, series, title=title, ylabel=ylabel)
    fig.tight_layout()
    fig.savefig(str(path), format="pdf")
    plt.close(fig)
    return True


def render_figure7_pdf(rows: list[dict[str, Any]], path: Path) -> bool:
    """Render the paper's four benchmark panels plus trajectory heatmaps."""
    mpl = C.optional_import("matplotlib")
    if mpl is None:
        _write_pdf_unavailable_notice(path, title="Figure 7: Ablation", why="matplotlib is not installed")
        return False
    mpl.use("Agg")
    import matplotlib.pyplot as plt

    tools = list(C.DATASET_SPECS)
    variants = list(C.RUN_VARIANTS)
    labels = ["RA", "NoA", "NoP", "NoV", "BA-alpha", "BA-beta"]
    metrics = [
        ("nc_proxy", "NC"),
        ("tec_proxy", "TEC"),
        ("sec_proxy", "SEC"),
        ("lc_proxy", "LC"),
        ("average_loop_length_proxy", "ALL"),
    ]
    lookup = {(row["tool"], row["variant"]): row for row in rows}
    fig, axes = plt.subplots(
        2, 4, figsize=(15, 7.5),
        gridspec_kw={"height_ratios": [1.0, 1.35]},
        constrained_layout=True,
    )
    for col, tool in enumerate(tools):
        ax = axes[0][col]
        values = [
            lookup.get((tool, variant), {}).get("test_validation_rate")
            for variant in variants
        ]
        real_x, real_y, missing_x = _partition_series_for_plot(list(range(len(variants))), values)
        ax.bar(real_x, [100.0 * value for value in real_y], color="#4C78A8")
        for x in missing_x:
            ax.text(x, 3, "N/A", ha="center", va="bottom", rotation=90, fontsize=7)
        ax.set_ylim(0, 100)
        ax.set_title(C.DATASET_SPECS[tool]["label"])
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=7)
        if col == 0:
            ax.set_ylabel("Test validation (%)")

        heat_ax = axes[1][col]
        matrix = [
            [
                lookup.get((tool, variant), {}).get(field)
                if lookup.get((tool, variant), {}).get(field) is not None
                else float("nan")
                for field, _label in metrics
            ]
            for variant in variants
        ]
        image = heat_ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
        heat_ax.set_xticks(range(len(metrics)), [label for _field, label in metrics], fontsize=7)
        heat_ax.set_yticks(range(len(labels)), labels, fontsize=7)
        for y, row_values in enumerate(matrix):
            for x, value in enumerate(row_values):
                text = "N/A" if value != value else f"{value:.1f}"
                heat_ax.text(x, y, text, ha="center", va="center", fontsize=6)
        if col == 0:
            heat_ax.set_ylabel("CodeWeaver trajectory proxy")
        fig.colorbar(image, ax=heat_ax, fraction=0.046, pad=0.03)
    fig.suptitle(
        "Figure 7: Ablation effectiveness and trajectory proxies\n"
        "(Burr/Copilot event proxy; not exact Graphectory semantics)",
        fontsize=12,
    )
    fig.savefig(str(path), format="pdf")
    plt.close(fig)
    return True


def render_figure8_pdf(rows: list[dict[str, Any]], path: Path) -> bool:
    """Render token/cost/time/turn panels and the tool-usage heatmap."""
    mpl = C.optional_import("matplotlib")
    if mpl is None:
        _write_pdf_unavailable_notice(path, title="Figure 8: Cost and Tools", why="matplotlib is not installed")
        return False
    mpl.use("Agg")
    import matplotlib.pyplot as plt

    tools = [row.get("tool", "") for row in rows]
    labels = [C.DATASET_SPECS.get(tool, {}).get("label", tool) for tool in tools]
    fig = plt.figure(figsize=(12, 8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.35])
    token_ax = fig.add_subplot(grid[0, 0])
    operational_ax = fig.add_subplot(grid[0, 1])
    tool_ax = fig.add_subplot(grid[1, :])

    xs = list(range(len(rows)))
    width = 0.36
    input_tokens = [row.get("total_input_tokens") for row in rows]
    output_tokens = [row.get("total_output_tokens") for row in rows]
    for offset, values, label, color in (
        (-width / 2, input_tokens, "Input tokens", "#4C78A8"),
        (width / 2, output_tokens, "Output tokens", "#F58518"),
    ):
        for x, value in zip(xs, values):
            if value is None:
                token_ax.text(x + offset, 0, "N/A", rotation=90, ha="center", va="bottom", fontsize=7)
            else:
                token_ax.bar(x + offset, value, width=width, color=color)
        token_ax.bar([], [], color=color, label=label)
    token_ax.set_xticks(xs, labels, rotation=25, ha="right")
    token_ax.set_ylabel("Tokens")
    token_ax.legend(fontsize=8)
    token_ax.set_title("Token usage (input unavailable from Copilot CLI where marked N/A)")

    nano = [
        row.get("total_nano_aiu") / 1e9 if row.get("total_nano_aiu") is not None else None
        for row in rows
    ]
    minutes = [
        row.get("elapsed_seconds_mean") / 60.0 if row.get("elapsed_seconds_mean") is not None else None
        for row in rows
    ]
    turns = [row.get("total_assistant_turns") for row in rows]
    op_width = 0.24
    for index, (values, label, color) in enumerate((
        (nano, "NanoAIU / 1e9", "#54A24B"),
        (minutes, "Time / project (min)", "#E45756"),
        (turns, "Assistant turns", "#B279A2"),
    )):
        offset = (index - 1) * op_width
        for x, value in zip(xs, values):
            if value is None:
                operational_ax.text(x + offset, 0, "N/A", rotation=90, ha="center", va="bottom", fontsize=6)
            else:
                operational_ax.bar(x + offset, value, width=op_width, color=color)
        operational_ax.bar([], [], color=color, label=label)
    operational_ax.set_xticks(xs, labels, rotation=25, ha="right")
    operational_ax.set_title("Compute proxy, elapsed time, and turns")
    operational_ax.legend(fontsize=7)

    tool_names = sorted({
        name
        for row in rows
        for name in json.loads(row.get("tool_counts_json") or "{}")
    })
    matrix = [
        [json.loads(row.get("tool_counts_json") or "{}").get(name, 0) for name in tool_names]
        for row in rows
    ]
    if tool_names:
        image = tool_ax.imshow(matrix, aspect="auto", cmap="magma")
        tool_ax.set_xticks(range(len(tool_names)), tool_names, rotation=55, ha="right", fontsize=7)
        tool_ax.set_yticks(range(len(labels)), labels)
        fig.colorbar(image, ax=tool_ax, label="Invocations")
    else:
        tool_ax.text(0.5, 0.5, "Tool-name telemetry unavailable", ha="center", va="center")
        tool_ax.set_xticks([])
        tool_ax.set_yticks([])
    tool_ax.set_title("Tool usage by benchmark")
    fig.suptitle("Figure 8: Cost and tool usage analysis", fontsize=13)
    fig.savefig(str(path), format="pdf")
    plt.close(fig)
    return True


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run_analysis(
    *,
    manifest: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    test_comparison_rows: list[dict[str, Any]] | None,
    output_root: Path,
    variants: list[str],
    repetitions: int = 1,
    project_ids: list[str] | None = None,
    primary_variant: str = "full",
    primary_repetition: int | None = 0,
    on_empty: str = "watermark",
    pricing_usd_per_premium_request: float | None = None,
    paper_test_project_rows: list[dict[str, Any]] | None = None,
    generated_test_project_rows: list[dict[str, Any]] | None = None,
    paper_results_workbook: str | Path | None = None,
) -> dict[str, Any]:
    """Writes every table/figure artifact and returns a JSON-serializable
    summary (also written to ``analysis_provenance.json``). Raises
    :class:`AnalysisAborted` (writing nothing) when ``on_empty == "fail"``
    and ``raw_rows`` -- the required, non-optional data source that drives
    table1/figure7/figure8 -- has no measured data at all.

    ``test_comparison_rows`` (RQ2) is independently optional at the CLI level
    (``--test-comparisons`` may simply be omitted): its absence never trips
    ``--on-empty=fail`` on its own -- table2/table_generated_tests always get
    their own per-artifact watermark in that case, regardless of ``on_empty``,
    since "RQ2 was never run" is a different situation from "there is no
    measured data to analyze at all".

    Selection is explicit and unambiguous, never an accidental mixture:
      - ``project_ids`` (optional): restricts EVERY output (completeness,
        table1/2, figure7/8, supporting tables) to this project subset --
        applied once, up front, so every downstream computation sees the
        same restricted data.
      - ``primary_variant``/``primary_repetition``: table1, table2,
        table_generated_tests and table_function_validation each report
        exactly this ONE (variant, repetition) selection (default: the
        "full" variant's first/canonical repetition -- matching the paper's
        own single headline run per project). ``figure7_ablation`` and
        ``figure8_cost_tools`` are unaffected: they intentionally compare
        ALL of ``variants`` side by side, which is their entire purpose."""
    output_root = Path(output_root)

    if project_ids is not None:
        _pid_set = set(project_ids)
        raw_rows = [r for r in raw_rows if r.get("project_id") in _pid_set]
        if test_comparison_rows is not None:
            test_comparison_rows = [r for r in test_comparison_rows if r.get("project_id") in _pid_set]
        if paper_test_project_rows is not None:
            paper_test_project_rows = [
                r for r in paper_test_project_rows if r.get("project_id") in _pid_set
            ]
        if generated_test_project_rows is not None:
            generated_test_project_rows = [
                r for r in generated_test_project_rows if r.get("project_id") in _pid_set
            ]

    raw_has_data = len(raw_rows) > 0
    test_has_data = bool(test_comparison_rows)
    # table2/generated-tests must be watermarked when test_compare.py simply
    # never produced any row for the SPECIFIC (primary_variant,
    # primary_repetition) selection those two tables report, even if
    # test_comparison_rows has real data for some OTHER variant/repetition --
    # otherwise they would silently render an empty-but-"real" all-zero table
    # instead of an honest "not available for this selection" watermark.
    test_has_data_for_primary_selection = bool(test_comparison_rows) and any(
        r.get("variant") == primary_variant
        and (primary_repetition is None or r.get("repetition") == primary_repetition)
        for r in (test_comparison_rows or [])
    )
    paper_test_has_data_for_primary_selection = bool(paper_test_project_rows) and any(
        r.get("variant") == primary_variant
        and (primary_repetition is None or int(r.get("repetition") or 0) == primary_repetition)
        for r in (paper_test_project_rows or [])
    )

    if on_empty not in ("watermark", "fail"):
        raise ValueError(f"on_empty must be 'watermark' or 'fail', got {on_empty!r}")
    if on_empty == "fail" and not raw_has_data:
        raise AnalysisAborted(
            f"no measured raw_runs data available (raw_runs measured={raw_has_data}) and --on-empty=fail"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    schema_errors = validate_rows_against_schema(raw_rows, "raw_run.schema.json")
    generated_schema_errors = validate_rows_against_schema(
        generated_test_project_rows or [], "generated_test_project.schema.json"
    )
    completeness = compute_completeness(manifest, raw_rows, variants=variants, project_ids=project_ids,
                                       repetitions=repetitions)
    paper_test_completeness = compute_project_row_completeness(
        manifest,
        paper_test_project_rows,
        variants=[primary_variant],
        repetitions=(repetitions if primary_repetition is None else 1),
        project_ids=project_ids,
        tools={"oxidizer", "alphatrans", "skel"},
    )
    generated_test_completeness = compute_project_row_completeness(
        manifest,
        generated_test_project_rows,
        variants=[primary_variant],
        repetitions=(repetitions if primary_repetition is None else 1),
        project_ids=project_ids,
    )
    provenance_consistency = check_provenance_consistency(raw_rows)

    # --- table1_effectiveness (+ separate paper reference file) ---
    if raw_has_data:
        table1_rows = compute_table1_measured(raw_rows, test_comparison_rows, manifest,
                                              variant=primary_variant, repetition=primary_repetition,
                                              generated_test_project_rows=generated_test_project_rows)
        _write_csv(table1_rows, _all_columns(table1_rows), output_root / "table1_effectiveness.csv")
        render_table_pdf(table1_rows, _all_columns(table1_rows), title="Table 1: CodeWeaver Effectiveness (measured)",
                        path=output_root / "table1_effectiveness.pdf",
                        subtitle=f"Measured CodeWeaver data only, variant={primary_variant!r} repetition="
                                f"{primary_repetition!r} -- see table1_paper_reference.csv for the paper's own numbers.")
    else:
        table1_rows = []
        write_no_measured_data_csv(output_root / "table1_effectiveness.csv", [], reason="no raw_runs rows at all")
        render_watermark_pdf(output_root / "table1_effectiveness.pdf", title="Table 1: CodeWeaver Effectiveness",
                            reason="no raw_runs rows at all -- run.py/collect.py have not produced any measured runs yet")

    ref_rows = table1_paper_reference_rows()
    _write_csv(ref_rows, _all_columns(ref_rows), output_root / "table1_paper_reference.csv")
    render_table_pdf(ref_rows, _all_columns(ref_rows), title="Table 1 (paper reference numbers, NOT measured)",
                    subtitle="From the ReCodeAgent paper itself -- never blended with measured CodeWeaver data.",
                    path=output_root / "table1_paper_reference.pdf")

    # --- table2_test_translation ---
    if paper_test_has_data_for_primary_selection:
        table2_rows = compute_paper_table2(
            paper_test_project_rows or [],
            variant=primary_variant,
            repetition=primary_repetition,
        )
        _write_csv(table2_rows, _all_columns(table2_rows), output_root / "table2_test_translation.csv")
        render_table_pdf(table2_rows, _all_columns(table2_rows),
                        title="Table 2: Test Translation (official AST protocol, measured)",
                        path=output_root / "table2_test_translation.pdf",
                        subtitle=f"variant={primary_variant!r} repetition={primary_repetition!r}")
    elif test_has_data_for_primary_selection:
        table2_rows = compute_table2(test_comparison_rows or [], variant=primary_variant,
                                     repetition=primary_repetition)
        _write_csv(table2_rows, _all_columns(table2_rows), output_root / "table2_test_translation.csv")
        render_table_pdf(table2_rows, _all_columns(table2_rows),
                        title="Table 2: Test Translation (heuristic fallback, measured)",
                        path=output_root / "table2_test_translation.pdf",
                        subtitle="paper_test_compare.py output unavailable; this is not the final paper-equivalent table")
    else:
        table2_rows = []
        write_no_measured_data_csv(output_root / "table2_test_translation.csv", [],
                                  reason=f"no test_comparisons rows for variant={primary_variant!r} "
                                        f"repetition={primary_repetition!r} (test_compare.py has not been run "
                                        "for this selection, or produced none)")
        render_watermark_pdf(output_root / "table2_test_translation.pdf", title="Table 2: Test Translation (RQ2)",
                            reason=f"no test_comparisons rows for variant={primary_variant!r} "
                                  f"repetition={primary_repetition!r}")

    # --- exact paper Tables 1/2 with CodeWeaver values immediately beside them ---
    paper_comparison_reason = None
    if paper_results_workbook is None:
        paper_comparison_reason = (
            "official results.xlsx was not supplied via --paper-results-workbook"
        )
    elif primary_repetition is None:
        paper_comparison_reason = (
            "the exact paper comparison requires one explicit primary repetition"
        )
    elif not raw_has_data:
        paper_comparison_reason = "no raw_runs rows are available"
    elif not paper_test_has_data_for_primary_selection:
        paper_comparison_reason = (
            "paper_test_projects has no rows for the primary selection"
        )
    elif not generated_test_project_rows:
        paper_comparison_reason = "generated_test_projects rows are unavailable"

    if paper_comparison_reason is None:
        paper_comparison = PTables.build_artifacts(
            workbook_path=paper_results_workbook,
            manifest=manifest,
            raw_rows=raw_rows,
            paper_test_project_rows=paper_test_project_rows or [],
            generated_test_project_rows=generated_test_project_rows or [],
            output_root=output_root,
            variant=primary_variant,
            repetition=primary_repetition,
        )
    else:
        for filename in (
            "paper_table1_side_by_side.csv",
            "paper_table2_side_by_side.csv",
        ):
            write_no_measured_data_csv(
                output_root / filename,
                [],
                reason=paper_comparison_reason,
            )
        render_watermark_pdf(
            output_root / "paper_tables_side_by_side.pdf",
            title="Paper Tables 1 and 2 with CodeWeaver results",
            reason=paper_comparison_reason,
        )
        paper_comparison = {
            "schema_version": 1,
            "generated_at": utcnow_iso(),
            "available": False,
            "reason": paper_comparison_reason,
            "paper_table1_rows": 0,
            "paper_table2_rows": 0,
            "comparison_pdf": "paper_tables_side_by_side.pdf",
        }
        C.atomic_write_json(
            output_root / "paper_tables_side_by_side_provenance.json",
            paper_comparison,
        )

    # --- figure7_ablation ---
    if raw_has_data:
        figure7_rows = compute_ablation_metrics_by_tool(raw_rows)
        _write_csv(figure7_rows, _all_columns(figure7_rows), output_root / "figure7_ablation.csv")
        render_figure7_pdf(figure7_rows, output_root / "figure7_ablation.pdf")
    else:
        figure7_rows = []
        write_no_measured_data_csv(output_root / "figure7_ablation.csv", [], reason="no raw_runs rows at all")
        render_watermark_pdf(output_root / "figure7_ablation.pdf", title="Figure 7: Ablation",
                            reason="no raw_runs rows at all")

    # --- figure8_cost_tools ---
    if raw_has_data:
        figure8_rows = compute_cost_metrics_by_tool(
            raw_rows,
            variant=primary_variant,
            repetition=primary_repetition,
            pricing_usd_per_premium_request=pricing_usd_per_premium_request,
        )
        _write_csv(figure8_rows, _all_columns(figure8_rows), output_root / "figure8_cost_tools.csv")
        render_figure8_pdf(figure8_rows, output_root / "figure8_cost_tools.pdf")
    else:
        figure8_rows = []
        write_no_measured_data_csv(output_root / "figure8_cost_tools.csv", [], reason="no raw_runs rows at all")
        render_watermark_pdf(output_root / "figure8_cost_tools.pdf", title="Figure 8: Cost/Tool Use",
                            reason="no raw_runs rows at all")

    # --- supporting tables ---
    if paper_test_has_data_for_primary_selection:
        gen_rows = compute_paper_generated_tests_table(
            paper_test_project_rows or [], variant=primary_variant,
            repetition=primary_repetition,
            generated_test_project_rows=generated_test_project_rows,
        )
        _write_csv(gen_rows, _all_columns(gen_rows), output_root / "table_generated_tests.csv")
        render_table_pdf(gen_rows, _all_columns(gen_rows),
                        title="Supporting: Translated vs Generated Tests by Project",
                        path=output_root / "table_generated_tests.pdf",
                        subtitle="CodeWeaver-authored generated tests: discovery plus isolated execution")
    elif test_has_data_for_primary_selection:
        gen_rows = compute_generated_tests_table(test_comparison_rows or [], variant=primary_variant,
                                                 repetition=primary_repetition)
        _write_csv(gen_rows, _all_columns(gen_rows), output_root / "table_generated_tests.csv")
        render_table_pdf(gen_rows, _all_columns(gen_rows), title="Supporting: Translated vs Generated Tests by Project",
                        path=output_root / "table_generated_tests.pdf",
                        subtitle=f"variant={primary_variant!r} repetition={primary_repetition!r}")
    else:
        gen_rows = []
        write_no_measured_data_csv(output_root / "table_generated_tests.csv", [],
                                  reason=f"no test_comparisons rows for variant={primary_variant!r} "
                                        f"repetition={primary_repetition!r}")
        render_watermark_pdf(output_root / "table_generated_tests.pdf", title="Translated vs Generated Tests",
                            reason=f"no test_comparisons rows for variant={primary_variant!r} "
                                  f"repetition={primary_repetition!r}")

    if raw_has_data:
        fn_rows = compute_function_validation_table(raw_rows, variant=primary_variant, repetition=primary_repetition)
        _write_csv(fn_rows, _all_columns(fn_rows), output_root / "table_function_validation.csv")
        render_table_pdf(fn_rows, _all_columns(fn_rows), title="Supporting: Per-Function/Milestone Validation",
                        path=output_root / "table_function_validation.pdf")
    else:
        fn_rows = []
        write_no_measured_data_csv(output_root / "table_function_validation.csv", [], reason="no raw_runs rows at all")
        render_watermark_pdf(output_root / "table_function_validation.pdf", title="Per-Function/Milestone Validation",
                            reason="no raw_runs rows at all")

    summary = {
        "schema_version": SCHEMA_VERSION, "generated_at": utcnow_iso(),
        "raw_runs_row_count": len(raw_rows), "test_comparisons_row_count": len(test_comparison_rows or []),
        "paper_test_projects_row_count": len(paper_test_project_rows or []),
        "generated_test_projects_row_count": len(generated_test_project_rows or []),
        "raw_has_data": raw_has_data, "test_has_data": test_has_data,
        "project_ids": project_ids,
        "primary_variant": primary_variant, "primary_repetition": primary_repetition,
        "test_has_data_for_primary_selection": test_has_data_for_primary_selection,
        "paper_test_has_data_for_primary_selection": paper_test_has_data_for_primary_selection,
        "on_empty_mode": on_empty,
        "schema_validation_errors": {str(k): v for k, v in schema_errors.items()},
        "generated_test_schema_validation_errors": {
            str(k): v for k, v in generated_schema_errors.items()
        },
        "schema_valid": not schema_errors and not generated_schema_errors,
        "completeness": completeness,
        "paper_test_completeness": paper_test_completeness,
        "generated_test_completeness": generated_test_completeness,
        "provenance_consistency": provenance_consistency,
        "table1_row_count": len(table1_rows), "table2_row_count": len(table2_rows),
        "figure7_row_count": len(figure7_rows), "figure8_row_count": len(figure8_rows),
        "paper_tables_side_by_side_available": bool(
            paper_comparison.get("available")
        ),
        "paper_table1_side_by_side_row_count": int(
            paper_comparison.get("paper_table1_rows") or 0
        ),
        "paper_table2_side_by_side_row_count": int(
            paper_comparison.get("paper_table2_rows") or 0
        ),
    }
    C.atomic_write_json(output_root / "analysis_provenance.json", summary)
    return summary


class AnalysisAborted(Exception):
    """Raised when --on-empty=fail and at least one required artifact would
    have no measured data to analyze. Callers must not write partial output
    when this is raised (run_analysis raises it before writing anything)."""


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="analyze.py",
        description="RQ1-RQ4 analysis: tables/figures from collect.py + test_compare.py outputs.",
    )
    ap.add_argument("--manifest", required=True, help="path to manifest.json (from manifest.py)")
    ap.add_argument("--raw-runs", required=True, help="path to raw_runs.jsonl (from collect.py)")
    ap.add_argument("--test-comparisons", default=None,
                    help="path to test_comparisons.jsonl (from test_compare.py); optional")
    ap.add_argument("--paper-test-projects", default=None,
                    help="path to paper_test_projects.csv from paper_test_compare.py; preferred "
                         "paper-equivalent RQ2 input (the heuristic --test-comparisons is fallback only)")
    ap.add_argument("--generated-test-projects", default=None,
                    help="path to generated_test_projects.csv from paper_test_compare.py")
    ap.add_argument(
        "--paper-results-workbook",
        default=None,
        help="official pinned results.xlsx; required for the exact paper Tables 1/2 "
             "side-by-side CSV/PDF comparison",
    )
    ap.add_argument("--output-root", required=True, help="where tables/figures are written")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--variant", default="all", help="comma-separated variants, or 'all' (default); this is the "
                    "SPAN of variants considered for completeness/figure7/figure8 (which intentionally compare "
                    "all variants side by side) -- it does NOT select which single variant table1/table2/"
                    "table_generated_tests/table_function_validation report (see --primary-variant for that)")
    ap.add_argument("--project", default=None, help="comma-separated project ids (default: all in manifest); "
                    "restricts EVERY output (completeness, table1/2, figure7/8, supporting tables) to this subset")
    ap.add_argument("--repetitions", type=int, default=None, help="default: [protocol].repetitions")
    ap.add_argument("--primary-variant", default="full", help="the SINGLE variant reported by table1_effectiveness, "
                    "table2_test_translation, table_generated_tests and table_function_validation (default: "
                    "'full', matching the paper's own headline run). Must never be mixed with other variants in "
                    "those four artifacts; use --variant/figure7/figure8 to compare across variants instead.")
    ap.add_argument("--primary-repetition", default="0", help="the SINGLE repetition (0-based) reported by "
                    "table1_effectiveness, table2_test_translation, table_generated_tests and "
                    "table_function_validation (default: '0', the first/canonical repetition). Pass 'all' to "
                    "instead aggregate across every repetition of --primary-variant (explicit opt-in only).")
    ap.add_argument("--on-empty", choices=["watermark", "fail"], default="watermark",
                    help="behavior when there is no measured data: write a watermarked artifact (default) or fail")
    ap.add_argument("--pricing-usd-per-premium-request", type=float, default=None,
                    help="OPTIONAL documented USD-per-premium-request conversion; omit to keep dollar_cost_usd "
                        "not_applicable (GitHub Copilot CLI has no built-in dollar-cost API)")
    return ap


def _parse_variants(raw: str) -> list[str]:
    if raw == "all":
        return list(C.RUN_VARIANTS)
    variants = [v.strip() for v in raw.split(",") if v.strip()]
    for v in variants:
        if v not in C.RUN_VARIANTS:
            raise ValueError(f"unknown variant {v!r}; choose from {C.RUN_VARIANTS}")
    return variants


def _parse_primary_variant(raw: str) -> str:
    if raw not in C.RUN_VARIANTS:
        raise ValueError(f"unknown --primary-variant {raw!r}; choose from {C.RUN_VARIANTS}")
    return raw


def _parse_primary_repetition(raw: str) -> int | None:
    """``"all"`` (case-insensitive) means "aggregate across every repetition of
    --primary-variant" (``None``); anything else must be a non-negative int
    repetition index. This is a deliberate, explicit opt-in -- the default
    ("0") always selects exactly one repetition, never a silent mixture."""
    if raw.strip().lower() == "all":
        return None
    try:
        value = int(raw)
    except ValueError as e:
        raise ValueError(f"--primary-repetition must be an integer or 'all', got {raw!r}") from e
    if value < 0:
        raise ValueError(f"--primary-repetition must be >= 0 or 'all', got {raw!r}")
    return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from experiments.recodeagent import manifest as M
    cfg = M.load_experiment_config(args.config)
    manifest = load_manifest(args.manifest)
    raw_rows = load_raw_runs(args.raw_runs)
    test_comparison_rows = load_test_comparisons(args.test_comparisons)
    paper_test_project_rows = load_paper_test_projects(args.paper_test_projects)
    generated_test_project_rows = load_generated_test_projects(args.generated_test_projects)
    variants = _parse_variants(args.variant)
    project_ids = [p.strip() for p in args.project.split(",") if p.strip()] if args.project else None
    primary_variant = _parse_primary_variant(args.primary_variant)
    primary_repetition = _parse_primary_repetition(args.primary_repetition)
    repetitions = (args.repetitions if args.repetitions is not None
                  else int(cfg.get("protocol", {}).get("repetitions", 1)))

    try:
        summary = run_analysis(
            manifest=manifest, raw_rows=raw_rows, test_comparison_rows=test_comparison_rows,
            output_root=Path(args.output_root), variants=variants, repetitions=repetitions,
            project_ids=project_ids, primary_variant=primary_variant, primary_repetition=primary_repetition,
            on_empty=args.on_empty, pricing_usd_per_premium_request=args.pricing_usd_per_premium_request,
            paper_test_project_rows=paper_test_project_rows,
            generated_test_project_rows=generated_test_project_rows,
            paper_results_workbook=args.paper_results_workbook,
        )
    except AnalysisAborted as e:
        print(f"[analyze] ABORTED: {e}")
        return 1

    print(f"[analyze] raw_runs={summary['raw_runs_row_count']} row(s), "
         f"test_comparisons={summary['test_comparisons_row_count']} row(s), "
         f"paper_test_projects={summary['paper_test_projects_row_count']} row(s), "
         f"generated_test_projects={summary['generated_test_projects_row_count']} row(s)")
    print(f"[analyze] schema_valid={summary['schema_valid']} "
         f"completeness={summary['completeness']['coverage_fraction']}")
    print(f"[analyze] table1/2 + supporting tables report primary_variant={primary_variant!r} "
         f"primary_repetition={primary_repetition!r} (project_ids={project_ids})")
    print(f"[analyze] wrote tables/figures -> {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
