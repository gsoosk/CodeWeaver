"""Tests for experiments/recodeagent/analyze.py: schema/completeness/provenance
validation, standard-library-first statistics helpers (mean/sum measurement,
bootstrap CI, paired Wilcoxon-or-bootstrap delta), the four RQ1/RQ2/RQ3/RQ4
table/figure compute functions plus two supporting tables, CSV/PDF rendering
(including graceful degradation when reportlab/matplotlib are unavailable),
the NO MEASURED DATA watermark path, full run_analysis orchestration (measured,
empty-data-watermark, and on_empty=fail-abort branches), and the CLI. No
network, LLM, or toolchain access anywhere in this file -- everything runs
against synthetic fixtures created on the fly, and reportlab/matplotlib (both
pre-installed in this sandbox) are exercised for real only where that's safe
and fast; unavailable-path behavior is verified via monkeypatched
``common.optional_import``.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from experiments.recodeagent import analyze as A
from experiments.recodeagent import common as C
from experiments.recodeagent.common import Measurement, Status


# --------------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------------- #
def _manifest(projects: list[tuple[str, str, int]]) -> dict:
    """projects: list of (project_id, tool, loc_source)."""
    return {"projects": [{"id": pid, "tool": tool, "loc_source": loc} for pid, tool, loc in projects]}


def _raw_row(**overrides) -> dict:
    """A schema-valid raw_run row with sensible measured defaults; override
    just the fields a given test cares about."""
    row = {
        "variant": "full", "project_id": "crust__a", "tool": "crust", "repetition": 0,
        "workspace_dir": "C:\\ws\\full\\crust__a\\0", "app_id": "app-1",
        "collected_at": C.utcnow_iso(), "run_status": "completed", "run_error": "",
        "run_started_at": None, "run_ended_at": None,
        "build": True, "build_status": Status.MEASURED, "build_reason": "",
        "project_pass_all": False, "project_pass_all_status": Status.MEASURED,
        "project_pass_all_reason": "",
        "dev_tests_total": 10, "dev_tests_total_status": Status.MEASURED, "dev_tests_total_reason": "",
        "dev_tests_passed": 8, "dev_tests_passed_status": Status.MEASURED, "dev_tests_passed_reason": "",
        "dev_tests_failed": 2, "dev_tests_failed_status": Status.MEASURED, "dev_tests_failed_reason": "",
        "dev_test_pass_rate": 0.8, "dev_test_pass_rate_status": Status.MEASURED, "dev_test_pass_rate_reason": "",
        # translated_tests_* mirrors dev_tests_*/dev_test_pass_rate above (a literal
        # alias collect.py always writes alongside it -- see collect_run()); NOT
        # set here: validated_tests_*/oracle_integrity/function_validation_* (the
        # post-hoc independently-validated oracle), which real collect.py output
        # only measures when --reference-results-root was supplied and a suitable
        # oracle actually exists -- tests that care about that opt in explicitly.
        "translated_tests_total": 10, "translated_tests_total_status": Status.MEASURED,
        "translated_tests_total_reason": "",
        "translated_tests_passed": 8, "translated_tests_passed_status": Status.MEASURED,
        "translated_tests_passed_reason": "",
        "translated_tests_failed": 2, "translated_tests_failed_status": Status.MEASURED,
        "translated_tests_failed_reason": "",
        "translated_tests_pass_rate": 0.8, "translated_tests_pass_rate_status": Status.MEASURED,
        "translated_tests_pass_rate_reason": "",
        "baseline_build": True, "baseline_build_status": Status.MEASURED,
        "coverage_before": 0.5, "coverage_before_status": Status.MEASURED, "coverage_before_reason": "",
        "coverage_after": 0.7, "coverage_after_status": Status.MEASURED, "coverage_after_reason": "",
        "target_function_count": 11, "target_function_count_status": Status.MEASURED,
        "target_test_count": 9, "source_function_count": 12,
        "function_translation_ratio": 0.9, "function_translation_ratio_status": Status.MEASURED,
        "function_translation_ratio_reason": "",
        "stub_marker_count": 0, "stub_marker_count_status": Status.MEASURED,
        "milestones_total": 5, "milestones_total_status": Status.MEASURED, "milestones_total_reason": "",
        "milestones_passed": 4, "milestones_passed_status": Status.MEASURED, "milestones_passed_reason": "",
        "milestone_granularity": "real",
        "trajectory_precision": "exact", "trajectory_reason": "", "nc": 3, "tec": 5, "lc": 2, "all": 10,
        "sec_json": json.dumps({"analyzer": 1, "translator": 3}),
        "elapsed_seconds": 120.0, "elapsed_seconds_status": Status.MEASURED, "elapsed_seconds_reason": "",
        "tool_invocations_precision": "exact", "total_tool_invocations": 15, "total_assistant_turns": 6,
        "total_premium_requests": 3, "total_session_duration_ms": 120000,
        "tokens_status": Status.MEASURED, "total_input_tokens": 5000, "total_output_tokens": 1200,
        "model": "claude-sonnet-4.5", "agent_timeout_seconds": 5000, "git_sha": "abc123",
        "codeweaver_package_version": "0.1.0", "copilot_cli_version": "1.2.3",
    }
    row.update(overrides)
    return row


def _tc_row(**overrides) -> dict:
    """A schema-valid test_comparison row (translated origin by default)."""
    row = {
        "project_id": "crust__a", "tool": "crust", "variant": "full", "repetition": 0,
        "source_test_name": "test_add", "source_test_file": "a.c", "mapped": True,
        "mapping_status": Status.MEASURED, "mapping_reason": "", "mapping_confidence": 0.95,
        "translated_test_name": "test_add", "translated_test_file": "a.rs", "test_origin": "translated",
        "assertion_count_source": 2, "assertion_count_translated": 2, "assertion_count_match": True,
        "assert_equal_expected_value_source": 5, "assert_equal_expected_value_translated": 5,
        "assert_equal_expected_value_equivalent": True, "assert_equal_value_type": "int",
        "assertion_type_source": "equal", "assertion_type_translated": "equal", "assertion_type_match": True,
        "embedding_cosine_similarity": None, "embedding_status": Status.UNAVAILABLE, "embedding_reason": "",
        "loc_source": 10, "loc_translated": 12,
        "method_invocation_count_source": 3, "method_invocation_count_translated": 3,
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def test_load_manifest_reads_json(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 100)])
    path = tmp_path / "manifest.json"
    C.atomic_write_json(path, manifest)
    assert A.load_manifest(path) == manifest


def test_load_raw_runs_reads_jsonl(tmp_path: Path):
    rows = [_raw_row(), _raw_row(project_id="crust__b")]
    path = tmp_path / "raw_runs.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    loaded = A.load_raw_runs(path)
    assert len(loaded) == 2
    assert loaded[0]["build"] is True   # native bool, not the string "True"


def test_load_test_comparisons_returns_none_for_none_path():
    assert A.load_test_comparisons(None) is None


def test_load_test_comparisons_returns_none_for_missing_file(tmp_path: Path):
    assert A.load_test_comparisons(tmp_path / "does_not_exist.jsonl") is None


def test_load_test_comparisons_returns_empty_list_for_empty_existing_file(tmp_path: Path):
    path = tmp_path / "test_comparisons.jsonl"
    path.write_text("", encoding="utf-8")
    assert A.load_test_comparisons(path) == []


def test_load_test_comparisons_reads_rows(tmp_path: Path):
    path = tmp_path / "test_comparisons.jsonl"
    path.write_text(json.dumps(_tc_row()) + "\n", encoding="utf-8")
    loaded = A.load_test_comparisons(path)
    assert len(loaded) == 1
    assert loaded[0]["mapped"] is True


def test_load_generated_test_projects_restores_numbers_and_csv_nulls(
    tmp_path: Path,
):
    path = tmp_path / "generated_test_projects.csv"
    fields = [
        "repetition",
        "generated_target_test_methods",
        "generated_tests_expected",
        "generated_tests_executed",
        "generated_tests_passed",
        "generated_tests_failed",
        "generated_tests_not_executed",
        "generated_tests_pass_rate",
        "coverage_before",
        "coverage_after",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "repetition": "0",
            "generated_target_test_methods": "2",
            "generated_tests_expected": "2",
            "generated_tests_executed": "2",
            "generated_tests_passed": "2",
            "generated_tests_failed": "0",
            "generated_tests_not_executed": "0",
            "generated_tests_pass_rate": "1.0",
            "coverage_before": "25.5",
            "coverage_after": "50.0",
        })
        writer.writerow({field: "" for field in fields})

    rows = A.load_generated_test_projects(path)

    assert rows is not None
    assert rows[0]["generated_tests_expected"] == 2
    assert rows[0]["generated_tests_pass_rate"] == 1.0
    assert rows[0]["coverage_before"] == 25.5
    assert all(rows[1][field] is None for field in fields)


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #
def test_validate_rows_against_schema_accepts_valid_raw_row():
    errors = A.validate_rows_against_schema([_raw_row()], "raw_run.schema.json")
    assert errors == {}


def test_validate_rows_against_schema_reports_missing_required_field():
    bad = _raw_row()
    del bad["workspace_dir"]
    errors = A.validate_rows_against_schema([bad], "raw_run.schema.json")
    assert 0 in errors
    assert any("workspace_dir" in e for e in errors[0])


def test_validate_rows_against_schema_reports_bad_enum_value():
    bad = _raw_row(milestone_granularity="not-a-real-granularity")
    errors = A.validate_rows_against_schema([bad], "raw_run.schema.json")
    assert 0 in errors


def test_validate_rows_against_schema_only_flags_bad_rows():
    errors = A.validate_rows_against_schema([_raw_row(), _raw_row(workspace_dir=None)], "raw_run.schema.json")
    assert 0 not in errors
    assert 1 in errors


def test_validate_rows_against_schema_accepts_valid_test_comparison_row():
    errors = A.validate_rows_against_schema([_tc_row()], "test_comparison.schema.json")
    assert errors == {}


def test_validate_rows_against_schema_accepts_generated_row_with_null_source():
    row = _tc_row(source_test_name=None, source_test_file=None, mapped=False,
                 mapping_status=Status.NOT_APPLICABLE, test_origin="generated")
    errors = A.validate_rows_against_schema([row], "test_comparison.schema.json")
    assert errors == {}


# --------------------------------------------------------------------------- #
# Completeness
# --------------------------------------------------------------------------- #
def test_compute_completeness_full_coverage():
    manifest = _manifest([("crust__a", "crust", 100), ("crust__b", "crust", 200)])
    rows = [_raw_row(project_id="crust__a"), _raw_row(project_id="crust__b")]
    report = A.compute_completeness(manifest, rows, variants=["full"], repetitions=1)
    assert report["expected_cells"] == 2
    assert report["measured_cells"] == 2
    assert report["coverage_fraction"] == 1.0
    assert report["missing_cells"] == []


def test_compute_completeness_partial_coverage_lists_missing_cells():
    manifest = _manifest([("crust__a", "crust", 100), ("crust__b", "crust", 200)])
    rows = [_raw_row(project_id="crust__a")]
    report = A.compute_completeness(manifest, rows, variants=["full"], repetitions=1)
    assert report["expected_cells"] == 2
    assert report["measured_cells"] == 1
    assert report["coverage_fraction"] == 0.5
    assert report["missing_cells"] == [{"variant": "full", "project_id": "crust__b", "repetition": 0}]


def test_compute_completeness_empty_manifest_reports_none_fraction():
    report = A.compute_completeness({"projects": []}, [], variants=["full"], repetitions=1)
    assert report["expected_cells"] == 0
    assert report["coverage_fraction"] is None


def test_compute_completeness_multiple_variants_and_repetitions():
    manifest = _manifest([("crust__a", "crust", 100)])
    rows = [_raw_row(project_id="crust__a", variant="full", repetition=0),
           _raw_row(project_id="crust__a", variant="full", repetition=1)]
    report = A.compute_completeness(manifest, rows, variants=["full", "noanalyzer"], repetitions=2)
    assert report["expected_cells"] == 4   # 2 variants * 1 project * 2 repetitions
    assert report["measured_cells"] == 2


def test_compute_project_row_completeness_filters_tools_and_detects_duplicates():
    manifest = _manifest([
        ("crust__a", "crust", 100),
        ("oxidizer__a", "oxidizer", 100),
    ])
    rows = [
        {"variant": "full", "project_id": "oxidizer__a", "repetition": 0},
        {"variant": "full", "project_id": "oxidizer__a", "repetition": 0},
    ]
    report = A.compute_project_row_completeness(
        manifest,
        rows,
        variants=["full"],
        repetitions=1,
        tools={"oxidizer"},
    )
    assert report["expected_cells"] == 1
    assert report["observed_cells"] == 1
    assert report["coverage_fraction"] == 1.0
    assert report["duplicate_rows"] == 1


# --------------------------------------------------------------------------- #
# Provenance consistency
# --------------------------------------------------------------------------- #
def test_check_provenance_consistency_all_consistent():
    rows = [_raw_row(), _raw_row(project_id="crust__b")]
    report = A.check_provenance_consistency(rows)
    assert report["consistent"] is True
    assert report["strictly_consistent"] is True
    assert report["informational_drift"] == {}
    assert report["distinct_values"]["model"] == ["claude-sonnet-4.5"]


def test_check_provenance_consistency_detects_mixed_models():
    rows = [_raw_row(model="claude-sonnet-4.5"), _raw_row(project_id="crust__b", model="gpt-4")]
    report = A.check_provenance_consistency(rows)
    assert report["consistent"] is False
    assert report["strictly_consistent"] is False
    assert sorted(report["distinct_values"]["model"]) == ["claude-sonnet-4.5", "gpt-4"]


def test_check_provenance_consistency_discloses_cli_version_drift():
    rows = [
        _raw_row(copilot_cli_version="1.0.77"),
        _raw_row(project_id="crust__b", copilot_cli_version="1.0.78"),
    ]
    report = A.check_provenance_consistency(rows)
    assert report["consistent"] is True
    assert report["strictly_consistent"] is False
    assert report["informational_drift"] == {
        "copilot_cli_version": ["1.0.77", "1.0.78"],
    }


def test_check_provenance_consistency_empty_rows_is_consistent():
    report = A.check_provenance_consistency([])
    assert report["consistent"] is True


def test_check_provenance_consistency_ignores_none_values():
    rows = [_raw_row(git_sha=None), _raw_row(project_id="crust__b", git_sha="abc123")]
    report = A.check_provenance_consistency(rows)
    assert report["distinct_values"]["git_sha"] == ["abc123"]
    assert report["consistent"] is True


# --------------------------------------------------------------------------- #
# mean_measurement / sum_measurement
# --------------------------------------------------------------------------- #
def test_mean_measurement_computes_mean_over_measured_rows():
    rows = [_raw_row(dev_test_pass_rate=0.8), _raw_row(dev_test_pass_rate=0.4)]
    m = A.mean_measurement(rows, "dev_test_pass_rate", "dev_test_pass_rate_status")
    assert m.is_measured
    assert m.value == pytest.approx(0.6)


def test_mean_measurement_skips_non_measured_rows():
    rows = [_raw_row(dev_test_pass_rate=0.8),
           _raw_row(dev_test_pass_rate=None, dev_test_pass_rate_status=Status.MISSING)]
    m = A.mean_measurement(rows, "dev_test_pass_rate", "dev_test_pass_rate_status")
    assert m.value == pytest.approx(0.8)   # only the measured row counted, never coerced to 0.4


def test_mean_measurement_all_missing_returns_missing_not_zero():
    rows = [_raw_row(dev_test_pass_rate=None, dev_test_pass_rate_status=Status.MISSING)]
    m = A.mean_measurement(rows, "dev_test_pass_rate", "dev_test_pass_rate_status")
    assert not m.is_measured
    assert m.value is None
    assert "no measured" in m.reason


def test_mean_measurement_empty_rows_is_missing():
    m = A.mean_measurement([], "dev_test_pass_rate", "dev_test_pass_rate_status")
    assert m.status == Status.MISSING


def test_mean_measurement_doubles_as_boolean_rate():
    rows = [_raw_row(build=True), _raw_row(build=True), _raw_row(build=False)]
    m = A.mean_measurement(rows, "build", "build_status")
    assert m.value == pytest.approx(2 / 3)


def test_mean_measurement_without_status_field_uses_none_check_only():
    rows = [{"nc": 3}, {"nc": None}, {"nc": 5}]
    m = A.mean_measurement(rows, "nc")
    assert m.value == pytest.approx(4.0)


def test_sum_measurement_sums_over_measured_rows():
    rows = [_raw_row(dev_tests_total=10), _raw_row(dev_tests_total=20)]
    m = A.sum_measurement(rows, "dev_tests_total", "dev_tests_total_status")
    assert m.value == 30


def test_sum_measurement_all_missing_returns_missing():
    m = A.sum_measurement([_raw_row(dev_tests_total=None, dev_tests_total_status=Status.MISSING)],
                         "dev_tests_total", "dev_tests_total_status")
    assert m.status == Status.MISSING


# --------------------------------------------------------------------------- #
# paper_equivalent_pass_rate: SUM-based (never mean-of-per-row-rates)
# aggregation -- the paper's own worked example is passed=1,822 over a FIXED
# expected=2,107 denominator despite only TE=1,970 tests actually executing;
# a naive mean of already-computed per-row pass rates would NOT reproduce
# this (a project with many expected tests must count proportionally more
# than one with few), which is the whole point of this helper existing
# instead of reusing mean_measurement.
# --------------------------------------------------------------------------- #
def test_paper_equivalent_pass_rate_matches_paper_worked_example():
    """Reproduces the paper's own reported TPR: passed=1,822 / expected=2,107
    (== 0.8648...), even though only TE=1,970 tests actually executed --
    i.e. the denominator is expected, never executed."""
    rows = [
        _raw_row(project_id="crust__a",
                 validated_tests_passed=1822, validated_tests_passed_status=Status.MEASURED,
                 validated_tests_expected=2107, validated_tests_expected_status=Status.MEASURED),
    ]
    m = A.paper_equivalent_pass_rate(
        rows, "validated_tests_passed", "validated_tests_passed_status",
        "validated_tests_expected", "validated_tests_expected_status",
    )
    assert m.is_measured
    assert m.value == pytest.approx(1822 / 2107)


def test_paper_equivalent_pass_rate_is_sum_based_not_mean_of_per_row_rates():
    """The defining regression: a naive MEAN of two projects' own pass rates
    (1.0 and 0.0) would give 0.5, but the paper's own weighted SUM-based
    formula must instead give 10/12 -- because project A's 10 expected tests
    outweigh project B's 2 expected tests. This is the correctness bug the
    expected/executed fix specifically targets."""
    rows = [
        _raw_row(project_id="crust__a",
                 validated_tests_passed=10, validated_tests_passed_status=Status.MEASURED,
                 validated_tests_expected=10, validated_tests_expected_status=Status.MEASURED,
                 validated_tests_pass_rate=1.0, validated_tests_pass_rate_status=Status.MEASURED),
        _raw_row(project_id="crust__b",
                 validated_tests_passed=0, validated_tests_passed_status=Status.MEASURED,
                 validated_tests_expected=2, validated_tests_expected_status=Status.MEASURED,
                 validated_tests_pass_rate=0.0, validated_tests_pass_rate_status=Status.MEASURED),
    ]
    m = A.paper_equivalent_pass_rate(
        rows, "validated_tests_passed", "validated_tests_passed_status",
        "validated_tests_expected", "validated_tests_expected_status",
    )
    assert m.is_measured
    assert m.value == pytest.approx(10 / 12)
    naive_mean = A.mean_measurement(rows, "validated_tests_pass_rate", "validated_tests_pass_rate_status")
    assert naive_mean.value == pytest.approx(0.5)      # the WRONG naive per-row mean, for contrast
    assert m.value != pytest.approx(naive_mean.value)  # the paper-equivalent (sum-based) result must differ


def test_paper_equivalent_pass_rate_build_failure_contributes_zero_numerator_full_denominator():
    """A row whose passed-count is Status.ERROR (a real build failure, never
    a fabricated measured 0) still contributes its FULL expected count to the
    denominator and a zero to the numerator -- exactly mirroring
    collect.compute_paper_pass_rate's own per-row 0-substitution rule at the
    aggregate level, and never silently excluding the failed row entirely."""
    rows = [
        _raw_row(project_id="crust__a",
                 validated_tests_passed=8, validated_tests_passed_status=Status.MEASURED,
                 validated_tests_expected=8, validated_tests_expected_status=Status.MEASURED),
        _raw_row(project_id="crust__b",
                 validated_tests_passed=None, validated_tests_passed_status=Status.ERROR,
                 validated_tests_expected=4, validated_tests_expected_status=Status.MEASURED),
    ]
    m = A.paper_equivalent_pass_rate(
        rows, "validated_tests_passed", "validated_tests_passed_status",
        "validated_tests_expected", "validated_tests_expected_status",
    )
    assert m.is_measured
    assert m.value == pytest.approx(8 / 12)   # 8 passed of (8 + 4) expected -- project b counts 0 passed, not excluded


def test_paper_equivalent_pass_rate_row_excluded_when_its_own_expected_not_measured():
    """Inclusion is gated by EXPECTED being measured (never by passed) --
    a row with no known oracle denominator at all must be excluded from both
    sums, not silently treated as a zero-expected contributor."""
    rows = [
        _raw_row(project_id="crust__a",
                 validated_tests_passed=5, validated_tests_passed_status=Status.MEASURED,
                 validated_tests_expected=5, validated_tests_expected_status=Status.MEASURED),
        _raw_row(project_id="oxidizer__b",
                 validated_tests_passed=None, validated_tests_passed_status=Status.UNAVAILABLE,
                 validated_tests_expected=None, validated_tests_expected_status=Status.UNAVAILABLE),
    ]
    m = A.paper_equivalent_pass_rate(
        rows, "validated_tests_passed", "validated_tests_passed_status",
        "validated_tests_expected", "validated_tests_expected_status",
    )
    assert m.is_measured
    assert m.value == pytest.approx(1.0)   # oxidizer__b entirely excluded, not counted as 0/0 or 5/5


def test_paper_equivalent_pass_rate_missing_when_no_row_has_measured_expected():
    rows = [_raw_row(project_id="crust__a",
                     validated_tests_passed=None, validated_tests_passed_status=Status.UNAVAILABLE,
                     validated_tests_expected=None, validated_tests_expected_status=Status.UNAVAILABLE)]
    m = A.paper_equivalent_pass_rate(
        rows, "validated_tests_passed", "validated_tests_passed_status",
        "validated_tests_expected", "validated_tests_expected_status",
    )
    assert not m.is_measured
    assert m.value is None


# --------------------------------------------------------------------------- #
# bootstrap_ci
# --------------------------------------------------------------------------- #
def test_bootstrap_ci_returns_none_for_fewer_than_two_values():
    assert A.bootstrap_ci([]) is None
    assert A.bootstrap_ci([1.0]) is None


def test_bootstrap_ci_is_deterministic_with_fixed_seed():
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    ci1 = A.bootstrap_ci(values, seed=42)
    ci2 = A.bootstrap_ci(values, seed=42)
    assert ci1 == ci2


def test_bootstrap_ci_brackets_the_sample_mean_reasonably():
    values = [1.0] * 20   # zero variance -- CI should collapse tightly around 1.0
    lo, hi = A.bootstrap_ci(values)
    assert lo == pytest.approx(1.0)
    assert hi == pytest.approx(1.0)


def test_bootstrap_ci_low_le_high():
    values = [0.1, 0.9, 0.5, 0.3, 0.7, 0.2, 0.95, 0.05]
    lo, hi = A.bootstrap_ci(values)
    assert lo <= hi


# --------------------------------------------------------------------------- #
# paired_delta_test
# --------------------------------------------------------------------------- #
def test_paired_delta_test_missing_for_fewer_than_two_pairs():
    m = A.paired_delta_test([0.5], [0.6])
    assert m.status == Status.MISSING
    assert "2" in m.reason


def test_paired_delta_test_missing_for_empty_input():
    m = A.paired_delta_test([], [])
    assert m.status == Status.MISSING


def test_paired_delta_test_uses_scipy_wilcoxon_when_available():
    scipy_stats = C.optional_import("scipy.stats")
    if scipy_stats is None:
        pytest.skip("scipy not installed in this environment")
    baseline = [0.9, 0.85, 0.95, 0.8, 0.9, 0.88]
    variant = [0.5, 0.4, 0.6, 0.3, 0.55, 0.45]
    m = A.paired_delta_test(baseline, variant)
    assert m.is_measured
    assert m.value["test"] == "wilcoxon"
    assert m.value["n_pairs"] == 6
    assert m.value["mean_delta"] < 0   # variant is uniformly worse than baseline


def test_paired_delta_test_falls_back_to_bootstrap_when_scipy_unavailable(monkeypatch):
    monkeypatch.setattr(A.C, "optional_import", lambda name: None)
    baseline = [0.9, 0.85, 0.95, 0.8]
    variant = [0.5, 0.4, 0.6, 0.3]
    m = A.paired_delta_test(baseline, variant)
    assert m.is_measured
    assert m.value["test"] == "bootstrap_ci_mean_delta"
    assert m.value["ci_low"] <= m.value["ci_high"]
    assert m.value["n_pairs"] == 4


def test_paired_delta_test_falls_back_to_bootstrap_for_degenerate_scipy_input(monkeypatch):
    """All-zero differences make scipy.stats.wilcoxon raise ValueError --
    verify the fallback engages rather than propagating the exception."""
    scipy_stats = C.optional_import("scipy.stats")
    if scipy_stats is None:
        pytest.skip("scipy not installed in this environment")
    baseline = [0.5, 0.5, 0.5, 0.5]
    variant = [0.5, 0.5, 0.5, 0.5]
    m = A.paired_delta_test(baseline, variant)
    assert m.is_measured
    assert m.value["test"] == "bootstrap_ci_mean_delta"
    assert m.value["mean_delta"] == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# RQ1: compute_table1_measured
# --------------------------------------------------------------------------- #
def test_compute_table1_measured_aggregates_measured_tool():
    manifest = _manifest([("crust__a", "crust", 1000), ("crust__b", "crust", 2000)])
    rows = [_raw_row(project_id="crust__a", variant="full"), _raw_row(project_id="crust__b", variant="full")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["measured_run_count"] == 2
    assert by_tool["crust"]["compilation_success_rate"] == pytest.approx(1.0)
    assert by_tool["crust"]["projects_pass_all"] == 0
    assert by_tool["crust"]["project_pass_all_rate"] == pytest.approx(0.0)
    # translated_tests_pass_rate (CodeWeaver's own self-graded tests) IS
    # aggregated from the fixture's default translated_tests_* fields...
    assert by_tool["crust"]["translated_tests_pass_rate"] == pytest.approx(0.8)
    # ...but `tpr` (the paper's headline, INDEPENDENTLY VALIDATED metric) must
    # NOT silently fall back to it: this fixture never measured
    # validated_tests_pass_rate, so tpr is explicitly missing, never 0.8.
    # This is an intentional semantics change (previously `tpr` was sourced
    # from dev_test_pass_rate/translated tests) -- see
    # test_compute_table1_measured_tpr_* below for the full contract.
    assert by_tool["crust"]["tpr"] is None
    assert by_tool["crust"]["tpr_status"] == Status.MISSING
    assert by_tool["crust"]["tpr_source"] == "unavailable"
    assert by_tool["crust"]["loc_source_total"] == 3000


def test_compute_table1_measured_reports_missing_not_zero_for_absent_tool():
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["oxidizer"]["measured_run_count"] == 0
    assert by_tool["oxidizer"]["tpr_status"] == Status.MISSING
    assert by_tool["oxidizer"]["tpr"] is None   # never fabricated as 0.0


def test_compute_table1_measured_includes_all_aggregate_row():
    manifest = _manifest([("crust__a", "crust", 1000), ("oxidizer__a", "oxidizer", 500)])
    rows = [_raw_row(project_id="crust__a", variant="full", tool="crust"),
           _raw_row(project_id="oxidizer__a", variant="full", tool="oxidizer")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    all_row = next(r for r in table1 if r["tool"] == "ALL")
    assert all_row["measured_run_count"] == 2
    assert all_row["loc_source_total"] == 1500


def test_compute_table1_measured_translated_generated_counts_null_without_test_comparisons():
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["translated_dev_tests_count"] is None
    assert by_tool["crust"]["generated_tests_count"] is None


def test_compute_table1_measured_translated_generated_counts_from_test_comparisons():
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    tc_rows = [_tc_row(test_origin="translated", mapped=True),
              _tc_row(test_origin="generated", mapped=False, source_test_name=None, source_test_file=None)]
    table1 = A.compute_table1_measured(rows, tc_rows, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["translated_dev_tests_count"] == 1
    assert by_tool["crust"]["generated_tests_count"] == 1


def test_compute_table1_uses_isolated_generated_test_execution():
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    generated_rows = [{
        "variant": "full",
        "repetition": 0,
        "project_id": "crust__a",
        "tool": "crust",
        "generated_tests_expected": 5,
        "generated_tests_expected_status": Status.MEASURED,
        "generated_tests_executed": 4,
        "generated_tests_executed_status": Status.MEASURED,
        "generated_tests_passed": 3,
        "generated_tests_passed_status": Status.MEASURED,
        "generated_tests_failed": 1,
        "generated_tests_failed_status": Status.MEASURED,
        "generated_tests_not_executed": 1,
        "generated_tests_not_executed_status": Status.MEASURED,
    }]
    table1 = A.compute_table1_measured(
        rows,
        None,
        manifest,
        variant="full",
        generated_test_project_rows=generated_rows,
    )
    crust = next(row for row in table1 if row["tool"] == "crust")
    assert crust["generated_tests_count"] == 5
    assert crust["generated_tests_executed"] == 4
    assert crust["generated_tests_passed"] == 3
    assert crust["generated_tests_failed"] == 1
    assert crust["generated_tests_not_executed"] == 1
    assert crust["generated_tests_pass_rate"] == pytest.approx(0.6)


def test_compute_table1_uses_generated_project_coverage_not_standardized_harness():
    manifest = _manifest([("skel__a", "skel", 1000)])
    rows = [_raw_row(
        project_id="skel__a",
        tool="skel",
        coverage_before=10.0,
        coverage_after=None,
        coverage_after_status=Status.UNAVAILABLE,
        standardized_coverage_before=20.0,
        standardized_coverage_before_status=Status.MEASURED,
        standardized_coverage_after=30.0,
        standardized_coverage_after_status=Status.MEASURED,
    )]
    generated_rows = [{
        "variant": "full",
        "repetition": 0,
        "project_id": "skel__a",
        "tool": "skel",
        "generated_tests_expected": 1,
        "generated_tests_expected_status": Status.MEASURED,
        "generated_tests_executed": 1,
        "generated_tests_executed_status": Status.MEASURED,
        "generated_tests_passed": 1,
        "generated_tests_passed_status": Status.MEASURED,
        "generated_tests_failed": 0,
        "generated_tests_failed_status": Status.MEASURED,
        "generated_tests_not_executed": 0,
        "generated_tests_not_executed_status": Status.MEASURED,
        "coverage_before": 40.0,
        "coverage_before_status": Status.MEASURED,
        "coverage_after": 75.0,
        "coverage_after_status": Status.MEASURED,
    }]

    table = A.compute_table1_measured(
        rows,
        None,
        manifest,
        generated_test_project_rows=generated_rows,
    )
    skel = next(row for row in table if row["tool"] == "skel")

    assert skel["coverage_before"] == pytest.approx(40.0)
    assert skel["coverage_after"] == pytest.approx(75.0)
    assert skel["coverage_source"] == "generated_test_projects"
    assert skel["standardized_coverage_before"] == pytest.approx(20.0)
    assert skel["standardized_coverage_after"] == pytest.approx(30.0)


def test_compute_table1_measured_only_includes_requested_variant():
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full"),
           _raw_row(project_id="crust__a", variant="noanalyzer")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["measured_run_count"] == 1


def test_compute_table1_measured_test_comparison_counts_exclude_other_variant():
    """Regression for review finding #4: test_comparison_rows from a
    DIFFERENT variant (e.g. noanalyzer) must never leak into the "full"
    variant's translated/generated test counts, even though both share the
    same tool/project_id."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    tc_rows = [_tc_row(test_origin="translated", mapped=True, variant="full", repetition=0),
              _tc_row(test_origin="translated", mapped=True, variant="noanalyzer", repetition=0),
              _tc_row(test_origin="generated", variant="noanalyzer", repetition=0)]
    table1 = A.compute_table1_measured(rows, tc_rows, manifest, variant="full", repetition=0)
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["translated_dev_tests_count"] == 1   # only the "full" row, not the noanalyzer ones
    assert by_tool["crust"]["generated_tests_count"] == 0        # measured-zero (test_compare DID run for "full")


def test_compute_table1_measured_test_comparison_counts_exclude_other_repetition():
    """Regression for review finding #4: a second repetition's test_compare
    rows must never be summed into repetition 0's counts."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full", repetition=0)]
    tc_rows = [_tc_row(test_origin="translated", mapped=True, variant="full", repetition=0),
              _tc_row(test_origin="translated", mapped=True, variant="full", repetition=1)]
    table1 = A.compute_table1_measured(rows, tc_rows, manifest, variant="full", repetition=0)
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["translated_dev_tests_count"] == 1


def test_compute_table1_measured_test_comparison_counts_none_when_only_other_selection_available():
    """test_comparison_rows has real data, but none of it matches the
    requested (variant, repetition) -- the correct output is None/missing,
    never a fabricated 0 (that would be a NEW missing-to-zero bug introduced
    by the variant/repetition filter itself)."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full", repetition=0)]
    tc_rows = [_tc_row(test_origin="translated", mapped=True, variant="noanalyzer", repetition=0)]
    table1 = A.compute_table1_measured(rows, tc_rows, manifest, variant="full", repetition=0)
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["translated_dev_tests_count"] is None
    assert by_tool["crust"]["generated_tests_count"] is None


def test_compute_table1_measured_milestone_pass_rate_computed_from_sums():
    manifest = _manifest([("crust__a", "crust", 1000), ("crust__b", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", milestones_passed=4, milestones_total=5),
           _raw_row(project_id="crust__b", milestones_passed=2, milestones_total=5)]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["milestone_pass_rate"] == pytest.approx(6 / 10)


# --------------------------------------------------------------------------- #
# RQ1: translated vs. independently VALIDATED tests -- tpr/tpr_source must
# never conflate the two (post-hoc evaluator extension regression tests).
# --------------------------------------------------------------------------- #
def test_compute_table1_measured_tpr_sourced_from_validated_when_available():
    """tpr must come from validated_tests_pass_rate (the paper's independent
    oracle), NOT translated_tests_pass_rate/dev_test_pass_rate, even when
    both are measured and differ."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full",
                     translated_tests_pass_rate=1.0, translated_tests_pass_rate_status=Status.MEASURED,
                     validated_tests_expected=8, validated_tests_expected_status=Status.MEASURED,
                     validated_tests_executed=8, validated_tests_executed_status=Status.MEASURED,
                     validated_tests_passed=6, validated_tests_passed_status=Status.MEASURED,
                     validated_tests_failed=2, validated_tests_failed_status=Status.MEASURED,
                     validated_tests_not_executed=0, validated_tests_not_executed_status=Status.MEASURED,
                     validated_tests_pass_rate=0.75, validated_tests_pass_rate_status=Status.MEASURED)]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    # translated looked "perfect" (1.0) but the independently validated oracle
    # found real failures (0.75) -- tpr must report the LATTER, never blended
    # or averaged with the former.
    assert by_tool["crust"]["translated_tests_pass_rate"] == pytest.approx(1.0)
    assert by_tool["crust"]["validated_tests_pass_rate"] == pytest.approx(0.75)
    assert by_tool["crust"]["tpr"] == pytest.approx(0.75)
    assert by_tool["crust"]["tpr_status"] == Status.MEASURED
    assert by_tool["crust"]["tpr_source"] == "validated"
    assert by_tool["crust"]["validated_tests_executed"] == 8
    assert by_tool["crust"]["validated_tests_passed"] == 6
    assert by_tool["crust"]["validated_tests_failed"] == 2


def test_compute_table1_measured_tpr_missing_when_validated_unavailable_never_falls_back():
    """When validated_tests_pass_rate is Status.UNAVAILABLE (e.g. no
    --reference-results-root was supplied to collect.py), tpr must be
    explicitly missing -- NEVER silently backfilled from
    translated_tests_pass_rate/dev_test_pass_rate, even though both of those
    remain fully measured in the same row."""
    manifest = _manifest([("oxidizer__a", "oxidizer", 1000)])
    rows = [_raw_row(project_id="oxidizer__a", tool="oxidizer", variant="full",
                     translated_tests_pass_rate=0.9, translated_tests_pass_rate_status=Status.MEASURED,
                     validated_tests_pass_rate=None, validated_tests_pass_rate_status=Status.UNAVAILABLE,
                     validated_tests_pass_rate_reason="--reference-results-root not supplied")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["oxidizer"]["translated_tests_pass_rate"] == pytest.approx(0.9)
    assert by_tool["oxidizer"]["tpr"] is None
    assert by_tool["oxidizer"]["tpr_status"] == Status.MISSING
    assert by_tool["oxidizer"]["tpr_source"] == "unavailable"


def test_compute_table1_measured_new_fields_exclude_other_variant_and_repetition():
    """The new validated_tests_*/oracle_integrity_*_count/function_validation_*
    aggregates must respect the SAME (variant, repetition) selection as every
    pre-existing field (review finding #4's contract), never blending in an
    ablation variant's or another repetition's independent-oracle results."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [
        _raw_row(project_id="crust__a", variant="full", repetition=0,
                 validated_tests_expected=5, validated_tests_expected_status=Status.MEASURED,
                 validated_tests_executed=5, validated_tests_executed_status=Status.MEASURED,
                 oracle_integrity="pristine", oracle_integrity_status=Status.MEASURED,
                 function_validation_total=3, function_validation_total_status=Status.MEASURED),
        _raw_row(project_id="crust__a", variant="noanalyzer", repetition=0,
                 validated_tests_expected=999, validated_tests_expected_status=Status.MEASURED,
                 validated_tests_executed=999, validated_tests_executed_status=Status.MEASURED,
                 oracle_integrity="mutated", oracle_integrity_status=Status.MEASURED,
                 function_validation_total=999, function_validation_total_status=Status.MEASURED),
        _raw_row(project_id="crust__a", variant="full", repetition=1,
                 validated_tests_expected=999, validated_tests_expected_status=Status.MEASURED,
                 validated_tests_executed=999, validated_tests_executed_status=Status.MEASURED,
                 oracle_integrity="not_copied", oracle_integrity_status=Status.MEASURED,
                 function_validation_total=999, function_validation_total_status=Status.MEASURED),
    ]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full", repetition=0)
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["validated_tests_executed"] == 5
    assert by_tool["crust"]["function_validation_executed"] == 3
    assert by_tool["crust"]["oracle_integrity_pristine_count"] == 1
    assert by_tool["crust"]["oracle_integrity_mutated_count"] == 0
    assert by_tool["crust"]["oracle_integrity_not_copied_count"] == 0


def test_compute_table1_measured_oracle_integrity_counts_exclude_not_applicable():
    """oracle_integrity is not_applicable for every tool except CRUST (see
    collect.py's evaluate_independent_oracle) -- those rows must be excluded
    from every count, never miscounted into one of the three real states."""
    manifest = _manifest([("crust__a", "crust", 1000), ("crust__b", "crust", 1000),
                          ("crust__c", "crust", 1000), ("crust__d", "crust", 1000)])
    rows = [
        _raw_row(project_id="crust__a", oracle_integrity="pristine", oracle_integrity_status=Status.MEASURED),
        _raw_row(project_id="crust__b", oracle_integrity="pristine", oracle_integrity_status=Status.MEASURED),
        _raw_row(project_id="crust__c", oracle_integrity="mutated", oracle_integrity_status=Status.MEASURED),
        _raw_row(project_id="crust__d", oracle_integrity=None, oracle_integrity_status=Status.NOT_APPLICABLE),
    ]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["crust"]["oracle_integrity_pristine_count"] == 2
    assert by_tool["crust"]["oracle_integrity_mutated_count"] == 1
    assert by_tool["crust"]["oracle_integrity_not_copied_count"] == 0


def test_compute_table1_measured_function_validation_distinct_from_translation_ratio():
    """function_validation_* (execution-based) and function_translation_ratio
    (symbol/completeness-based) must never be conflated -- both are reported,
    with clearly different values proving neither backfills the other."""
    manifest = _manifest([("oxidizer__a", "oxidizer", 1000)])
    rows = [_raw_row(project_id="oxidizer__a", tool="oxidizer", variant="full",
                     function_translation_ratio=1.0, function_translation_ratio_status=Status.MEASURED,
                     function_validation_total=4, function_validation_total_status=Status.MEASURED,
                     function_validation_passed=1, function_validation_passed_status=Status.MEASURED,
                     function_validation_failed=3, function_validation_failed_status=Status.MEASURED,
                     function_validation_pass_rate=0.25, function_validation_pass_rate_status=Status.MEASURED)]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["oxidizer"]["function_translation_ratio"] == pytest.approx(1.0)   # every symbol exists...
    assert by_tool["oxidizer"]["function_validation_pass_rate"] == pytest.approx(0.25)  # ...but most fail at runtime
    assert by_tool["oxidizer"]["function_validation_executed"] == 4
    assert by_tool["oxidizer"]["function_validation_passed"] == 1
    assert by_tool["oxidizer"]["function_validation_failed"] == 3


def test_compute_table1_measured_function_harness_tests_distinct_from_function_validation():
    """function_harness_tests_* (GENERATED function/test-harness EXECUTION
    evidence -- AlphaTrans's agent_test/, SKEL's javascript/*generated*.js)
    must be reported separately from function_validation_* (which requires a
    RELIABLE one-to-one per-function mapping neither tool has) -- exactly
    the real AlphaTrans/SKEL combination: function_validation_* unavailable,
    function_harness_tests_* measured, neither backfilling the other."""
    manifest = _manifest([("alphatrans__a", "alphatrans", 1000)])
    rows = [_raw_row(project_id="alphatrans__a", tool="alphatrans", variant="full",
                     function_validation_total=None, function_validation_total_status=Status.UNAVAILABLE,
                     function_validation_pass_rate=None, function_validation_pass_rate_status=Status.UNAVAILABLE,
                     function_harness_tests_total=6, function_harness_tests_total_status=Status.MEASURED,
                     function_harness_tests_passed=5, function_harness_tests_passed_status=Status.MEASURED,
                     function_harness_tests_failed=1, function_harness_tests_failed_status=Status.MEASURED,
                     function_harness_tests_pass_rate=5 / 6,
                     function_harness_tests_pass_rate_status=Status.MEASURED)]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["alphatrans"]["function_validation_executed"] is None
    assert by_tool["alphatrans"]["function_validation_executed_status"] == Status.MISSING
    assert by_tool["alphatrans"]["function_harness_tests_executed"] == 6
    assert by_tool["alphatrans"]["function_harness_tests_passed"] == 5
    assert by_tool["alphatrans"]["function_harness_tests_failed"] == 1
    assert by_tool["alphatrans"]["function_harness_tests_pass_rate"] == pytest.approx(5 / 6)


def test_compute_table1_measured_function_harness_tests_excludes_other_variant_and_repetition():
    """function_harness_tests_* must respect the SAME (variant, repetition)
    selection as every other new field (review finding #4's contract) --
    never blending in an ablation variant's or another repetition's
    function-harness execution evidence."""
    manifest = _manifest([("skel__a", "skel", 500)])
    rows = [
        _raw_row(project_id="skel__a", tool="skel", variant="full", repetition=0,
                 function_harness_tests_total=2, function_harness_tests_total_status=Status.MEASURED,
                 function_harness_tests_passed=2, function_harness_tests_passed_status=Status.MEASURED),
        _raw_row(project_id="skel__a", tool="skel", variant="noplanning", repetition=0,
                 function_harness_tests_total=999, function_harness_tests_total_status=Status.MEASURED,
                 function_harness_tests_passed=999, function_harness_tests_passed_status=Status.MEASURED),
        _raw_row(project_id="skel__a", tool="skel", variant="full", repetition=1,
                 function_harness_tests_total=999, function_harness_tests_total_status=Status.MEASURED,
                 function_harness_tests_passed=999, function_harness_tests_passed_status=Status.MEASURED),
    ]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full", repetition=0)
    by_tool = {r["tool"]: r for r in table1}
    assert by_tool["skel"]["function_harness_tests_executed"] == 2
    assert by_tool["skel"]["function_harness_tests_passed"] == 2


def test_table1_paper_reference_rows_includes_function_validation_denominator_non_crust():
    """The paper's 1,397 non-CRUST "Exercised" function count (independently
    verified against results.xlsx -- see analyze.py's
    FUNCTION_VALIDATION_DENOMINATOR_NON_CRUST provenance comment) must be
    surfaced on the paper_reference row, structurally separate from every
    measured_codeweaver row -- never blended, never implied to be a target
    this harness's own function_harness_tests_*/function_validation_* counts
    (a different unit: harness-test-file execution, not per-function
    coverage-"Exercised") must reproduce."""
    rows = A.table1_paper_reference_rows()
    assert len(rows) == 1
    assert rows[0]["function_validation_denominator_non_crust"] == 1397
    assert rows[0]["function_validation_denominator_non_crust"] == A.FUNCTION_VALIDATION_DENOMINATOR_NON_CRUST


def test_table1_paper_reference_rows_matches_common_constants():
    rows = A.table1_paper_reference_rows()
    assert len(rows) == 1
    assert rows[0]["source"] == "paper_reference"
    assert rows[0]["total_loc"] == C.PAPER_REFERENCE_TOTALS["total_loc"]
    assert rows[0]["translated_tests_excluding_crust"] == C.PAPER_REFERENCE_TOTALS["translated_tests"]
    assert rows[0]["functions"] == C.PAPER_REFERENCE_TOTALS["functions"]


def test_table1_paper_reference_rows_per_tool_validated_test_breakdown_sums_to_total():
    """The paper's exact validated-test denominator is 2,107 = 623 CRUST +
    229 Oxidizer + 1,181 AlphaTrans + 74 SKEL. table1_paper_reference_rows
    must surface this per-tool breakdown (never blended with any measured
    row) and it must sum exactly to the overall validated_tests total."""
    rows = A.table1_paper_reference_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["validated_tests_crust"] == 623
    assert row["validated_tests_oxidizer"] == 229
    assert row["validated_tests_alphatrans"] == 1181
    assert row["validated_tests_skel"] == 74
    per_tool_sum = (row["validated_tests_crust"] + row["validated_tests_oxidizer"]
                    + row["validated_tests_alphatrans"] + row["validated_tests_skel"])
    assert per_tool_sum == row["validated_tests"] == C.PAPER_REFERENCE_TOTALS["validated_tests"] == 2107
    # Non-CRUST tools' breakdown must also independently sum to the paper's
    # separately-reported "translated_tests" total (CRUST excluded by protocol).
    non_crust_sum = (row["validated_tests_oxidizer"] + row["validated_tests_alphatrans"]
                     + row["validated_tests_skel"])
    assert non_crust_sum == row["translated_tests_excluding_crust"] == C.PAPER_REFERENCE_TOTALS["translated_tests"]


def test_table1_paper_reference_rows_per_tool_breakdown_matches_common_constant_directly():
    rows = A.table1_paper_reference_rows()
    row = rows[0]
    for tool in ("crust", "oxidizer", "alphatrans", "skel"):
        assert row[f"validated_tests_{tool}"] == C.PAPER_REFERENCE_VALIDATED_TESTS_BY_TOOL[tool]


# --------------------------------------------------------------------------- #
# RQ2: compute_table2
# --------------------------------------------------------------------------- #
def test_compute_table2_delegates_to_summarize_comparisons_per_tool():
    rows = [_tc_row(tool="crust"), _tc_row(tool="crust", source_test_name="test_sub"),
           _tc_row(tool="oxidizer")]
    table2 = A.compute_table2(rows)
    by_tool = {r["tool"]: r for r in table2}
    assert by_tool["crust"]["total_source_tests"] == 2
    assert by_tool["oxidizer"]["total_source_tests"] == 1
    assert by_tool["ALL"]["total_source_tests"] == 3


def test_compute_table2_empty_input_still_has_all_row():
    table2 = A.compute_table2([])
    assert len(table2) == 1
    assert table2[0]["tool"] == "ALL"
    assert table2[0]["total_source_tests"] == 0


def test_compute_table2_excludes_other_variant_by_default():
    """Regression for review finding #4: compute_table2's grouping had ZERO
    variant/repetition filtering -- a mixed test_comparison_rows list must not
    let a "noanalyzer" row inflate the default ("full") table."""
    rows = [_tc_row(tool="crust", variant="full", repetition=0),
           _tc_row(tool="crust", variant="noanalyzer", repetition=0, source_test_name="test_other")]
    table2 = A.compute_table2(rows)   # default variant="full", repetition=0
    by_tool = {r["tool"]: r for r in table2}
    assert by_tool["crust"]["total_source_tests"] == 1
    assert by_tool["ALL"]["total_source_tests"] == 1


def test_compute_table2_excludes_other_repetition_by_default():
    rows = [_tc_row(tool="crust", variant="full", repetition=0),
           _tc_row(tool="crust", variant="full", repetition=1, source_test_name="test_other")]
    table2 = A.compute_table2(rows)   # default repetition=0
    by_tool = {r["tool"]: r for r in table2}
    assert by_tool["crust"]["total_source_tests"] == 1


def test_compute_table2_variant_none_aggregates_across_variants_explicitly():
    """variant=None is an explicit, deliberate opt-in to cross-variant
    aggregation -- distinct from the default single-selection behavior."""
    rows = [_tc_row(tool="crust", variant="full", repetition=0),
           _tc_row(tool="crust", variant="noanalyzer", repetition=0, source_test_name="test_other")]
    table2 = A.compute_table2(rows, variant=None, repetition=None)
    by_tool = {r["tool"]: r for r in table2}
    assert by_tool["crust"]["total_source_tests"] == 2


def test_compute_paper_table2_uses_runtime_denominator_and_weighted_metrics():
    rows = [{
        "variant": "full", "repetition": "0", "tool": "oxidizer",
        "project": "checkdigit", "paper_runtime_tests": "36",
        "mapped_runtime_cases": "35", "static_source_methods": "36",
        "assertion_count_runtime_matches": "34",
        "assertion_count_runtime_mismatches": "2",
        "assert_equal_comparable": "10", "assert_equal_matching": "9",
        "assert_equal_type_good": "8", "assert_equal_type_total": "10",
        "assert_true_type_good": "0", "assert_true_type_total": "0",
        "assert_false_type_good": "0", "assert_false_type_total": "0",
        "other_type_good": "0", "other_type_total": "0",
        "avg_cosine_similarity": "0.9", "embedding_similarity_count": "36",
        "both_ast_methods_found": "36", "avg_source_loc": "10",
        "avg_target_loc": "11", "avg_source_method_calls": "4",
        "avg_target_method_calls": "5", "generated_target_test_methods": "3",
    }]
    result = A.compute_paper_table2(rows)
    project = next(row for row in result if row["project"] == "checkdigit")
    assert project["tests"] == 36
    assert project["tests_translated"] == 35
    assert project["assertion_count_matching_tests"] == 34
    assert project["assert_equal_output_match_percent"] == pytest.approx(90)
    assert project["assert_equal_type_match_percent"] == pytest.approx(80)


# --------------------------------------------------------------------------- #
# RQ3: compute_ablation_metrics
# --------------------------------------------------------------------------- #
def test_compute_ablation_metrics_one_row_per_run_variant():
    rows = [_raw_row(variant="full"), _raw_row(variant="noanalyzer")]
    metrics = A.compute_ablation_metrics(rows)
    assert {r["variant"] for r in metrics} == set(C.RUN_VARIANTS)


def test_compute_ablation_metrics_full_variant_has_na_delta():
    rows = [_raw_row(variant="full")]
    metrics = A.compute_ablation_metrics(rows)
    full_row = next(r for r in metrics if r["variant"] == "full")
    assert full_row["tpr_delta_vs_full_status"] == Status.NOT_APPLICABLE


def test_compute_ablation_metrics_nonfull_variant_computes_paired_delta():
    rows = [
        _raw_row(variant="full", project_id="crust__a", validated_tests_pass_rate=0.9,
                 validated_tests_pass_rate_status=Status.MEASURED),
        _raw_row(variant="full", project_id="crust__b", validated_tests_pass_rate=0.8,
                 validated_tests_pass_rate_status=Status.MEASURED),
        _raw_row(variant="noanalyzer", project_id="crust__a", validated_tests_pass_rate=0.5,
                 validated_tests_pass_rate_status=Status.MEASURED),
        _raw_row(variant="noanalyzer", project_id="crust__b", validated_tests_pass_rate=0.4,
                 validated_tests_pass_rate_status=Status.MEASURED),
    ]
    metrics = A.compute_ablation_metrics(rows)
    noanalyzer_row = next(r for r in metrics if r["variant"] == "noanalyzer")
    assert noanalyzer_row["tpr_delta_vs_full_status"] == Status.MEASURED
    delta_payload = json.loads(noanalyzer_row["tpr_delta_vs_full_json"])
    assert delta_payload["n_pairs"] == 2
    assert delta_payload["mean_delta"] < 0


def test_compute_ablation_metrics_unmeasured_variant_reports_missing():
    rows = [_raw_row(variant="full")]
    metrics = A.compute_ablation_metrics(rows)
    novalidator_row = next(r for r in metrics if r["variant"] == "novalidator")
    assert novalidator_row["measured_run_count"] == 0
    assert novalidator_row["tpr_status"] == Status.MISSING
    assert novalidator_row["nc_status"] == Status.MISSING


def test_compute_ablation_metrics_sec_json_aggregates_stage_means():
    rows = [_raw_row(variant="full", sec_json=json.dumps({"analyzer": 2, "translator": 4})),
           _raw_row(variant="full", project_id="crust__b", sec_json=json.dumps({"analyzer": 4, "translator": 6}))]
    metrics = A.compute_ablation_metrics(rows)
    full_row = next(r for r in metrics if r["variant"] == "full")
    sec_means = json.loads(full_row["sec_mean_json"])
    assert sec_means["analyzer"] == pytest.approx(3.0)
    assert sec_means["translator"] == pytest.approx(5.0)


def test_compute_ablation_metrics_handles_malformed_sec_json_gracefully():
    rows = [_raw_row(variant="full", sec_json="not-json")]
    metrics = A.compute_ablation_metrics(rows)
    full_row = next(r for r in metrics if r["variant"] == "full")
    assert json.loads(full_row["sec_mean_json"]) == {}


# --------------------------------------------------------------------------- #
# RQ4: compute_cost_metrics
# --------------------------------------------------------------------------- #
def test_compute_cost_metrics_sums_tokens_and_invocations():
    rows = [_raw_row(variant="full", total_input_tokens=1000, total_output_tokens=200),
           _raw_row(variant="full", project_id="crust__b", total_input_tokens=2000, total_output_tokens=400)]
    metrics = A.compute_cost_metrics(rows)
    full_row = next(r for r in metrics if r["variant"] == "full")
    assert full_row["total_input_tokens"] == 3000
    assert full_row["total_output_tokens"] == 600


def test_compute_cost_metrics_dollar_cost_not_applicable_without_pricing():
    rows = [_raw_row(variant="full")]
    metrics = A.compute_cost_metrics(rows)
    full_row = next(r for r in metrics if r["variant"] == "full")
    assert full_row["dollar_cost_usd_status"] == Status.NOT_APPLICABLE
    assert full_row["dollar_cost_usd"] is None
    assert "pricing" in full_row["dollar_cost_usd_reason"]


def test_compute_cost_metrics_dollar_cost_measured_with_explicit_pricing():
    rows = [_raw_row(variant="full", total_premium_requests=10)]
    metrics = A.compute_cost_metrics(rows, pricing_usd_per_premium_request=0.04)
    full_row = next(r for r in metrics if r["variant"] == "full")
    assert full_row["dollar_cost_usd_status"] == Status.MEASURED
    assert full_row["dollar_cost_usd"] == pytest.approx(0.4)


def test_compute_cost_metrics_unmeasured_variant_all_missing():
    rows = [_raw_row(variant="full")]
    metrics = A.compute_cost_metrics(rows)
    novalidator_row = next(r for r in metrics if r["variant"] == "novalidator")
    assert novalidator_row["total_input_tokens_status"] == Status.MISSING
    assert novalidator_row["total_input_tokens"] is None


# --------------------------------------------------------------------------- #
# Supporting tables
# --------------------------------------------------------------------------- #
def test_compute_generated_tests_table_counts_by_project():
    rows = [_tc_row(project_id="crust__a", test_origin="translated"),
           _tc_row(project_id="crust__a", test_origin="generated", source_test_name=None, source_test_file=None),
           _tc_row(project_id="crust__a", mapped=False, test_origin=None, mapping_status=Status.MISSING)]
    table = A.compute_generated_tests_table(rows)
    assert len(table) == 1
    assert table[0]["translated_count"] == 1
    assert table[0]["generated_count"] == 1
    assert table[0]["missing_count"] == 1


def test_compute_generated_tests_table_empty_input():
    assert A.compute_generated_tests_table([]) == []


def test_compute_generated_tests_table_excludes_other_variant_for_same_project():
    """Regression for review finding #4 (the most severe instance): grouping
    by project_id alone -- with NO variant/repetition filter -- would
    silently SUM a "noanalyzer" run's counts into the same project's "full"
    entry. Each variant/repetition must contribute to its own entry only."""
    rows = [_tc_row(project_id="crust__a", test_origin="translated", variant="full", repetition=0),
           _tc_row(project_id="crust__a", test_origin="translated", variant="noanalyzer", repetition=0,
                  source_test_name="test_other")]
    table = A.compute_generated_tests_table(rows)   # default variant="full", repetition=0
    assert len(table) == 1
    assert table[0]["translated_count"] == 1   # not 2 -- the noanalyzer row must be excluded


def test_compute_generated_tests_table_excludes_other_repetition_for_same_project():
    rows = [_tc_row(project_id="crust__a", test_origin="translated", variant="full", repetition=0),
           _tc_row(project_id="crust__a", test_origin="translated", variant="full", repetition=1,
                  source_test_name="test_other")]
    table = A.compute_generated_tests_table(rows)   # default repetition=0
    assert len(table) == 1
    assert table[0]["translated_count"] == 1


def test_compute_function_validation_table_filters_by_variant_and_sorts():
    rows = [_raw_row(project_id="crust__b", tool="crust", variant="full"),
           _raw_row(project_id="crust__a", tool="crust", variant="full"),
           _raw_row(project_id="crust__c", tool="crust", variant="noanalyzer")]
    table = A.compute_function_validation_table(rows, variant="full")
    assert [r["project_id"] for r in table] == ["crust__a", "crust__b"]


def test_compute_function_validation_table_filters_by_repetition_by_default():
    """Regression for review finding #4: compute_function_validation_table
    filtered by variant but NOT by repetition -- a second repetition of the
    same variant/project must not double-count into the default (rep 0)
    selection."""
    rows = [_raw_row(project_id="crust__a", tool="crust", variant="full", repetition=0),
           _raw_row(project_id="crust__a", tool="crust", variant="full", repetition=1)]
    table = A.compute_function_validation_table(rows, variant="full")   # default repetition=0
    assert len(table) == 1


def test_compute_function_validation_table_includes_function_ratio_fields():
    rows = [_raw_row(function_translation_ratio=0.75)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["function_translation_ratio"] == pytest.approx(0.75)
    assert table[0]["source_function_count"] == 12


def test_compute_function_validation_table_includes_execution_based_and_oracle_integrity_fields():
    """Regression for the post-hoc evaluator extension: per-project
    function_validation_* (execution-based) and oracle_integrity must be
    surfaced here alongside (never merged into) function_translation_ratio
    (symbol/completeness)."""
    rows = [_raw_row(project_id="oxidizer__a", tool="oxidizer", function_translation_ratio=1.0,
                     function_validation_total=4, function_validation_total_status=Status.MEASURED,
                     function_validation_passed=3, function_validation_failed=1,
                     function_validation_pass_rate=0.75, function_validation_pass_rate_status=Status.MEASURED)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["function_translation_ratio"] == pytest.approx(1.0)
    assert table[0]["function_validation_total"] == 4
    assert table[0]["function_validation_passed"] == 3
    assert table[0]["function_validation_failed"] == 1
    assert table[0]["function_validation_pass_rate"] == pytest.approx(0.75)
    assert table[0]["function_validation_total_status"] == Status.MEASURED


def test_compute_function_validation_table_includes_function_harness_tests_fields():
    """Regression for the AlphaTrans agent_test/ + SKEL javascript/
    *generated*.js extension: per-project function_harness_tests_* (GENERATED
    function/test-harness EXECUTION evidence) must be surfaced here too,
    alongside function_translation_ratio and function_validation_*."""
    rows = [_raw_row(project_id="alphatrans__a", tool="alphatrans",
                     function_harness_tests_total=6, function_harness_tests_total_status=Status.MEASURED,
                     function_harness_tests_passed=5, function_harness_tests_failed=1,
                     function_harness_tests_pass_rate=5 / 6,
                     function_harness_tests_pass_rate_status=Status.MEASURED)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["function_harness_tests_total"] == 6
    assert table[0]["function_harness_tests_passed"] == 5
    assert table[0]["function_harness_tests_failed"] == 1
    assert table[0]["function_harness_tests_pass_rate"] == pytest.approx(5 / 6)
    assert table[0]["function_harness_tests_total_status"] == Status.MEASURED


def test_compute_function_validation_table_function_harness_tests_distinct_from_function_validation():
    """The real AlphaTrans/SKEL combination: function_validation_*
    unavailable (no reliable one-to-one per-function mapping) alongside a
    MEASURED function_harness_tests_* -- neither must backfill or overwrite
    the other in the per-project table."""
    rows = [_raw_row(project_id="skel__a", tool="skel",
                     function_validation_total=None, function_validation_total_status=Status.UNAVAILABLE,
                     function_harness_tests_total=2, function_harness_tests_total_status=Status.MEASURED,
                     function_harness_tests_passed=2, function_harness_tests_failed=0,
                     function_harness_tests_pass_rate=1.0, function_harness_tests_pass_rate_status=Status.MEASURED)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["function_validation_total"] is None
    assert table[0]["function_validation_total_status"] == Status.UNAVAILABLE
    assert table[0]["function_harness_tests_total"] == 2
    assert table[0]["function_harness_tests_pass_rate"] == pytest.approx(1.0)


def test_compute_function_validation_table_reports_oracle_integrity_per_project():
    rows = [_raw_row(project_id="crust__a", tool="crust", oracle_integrity="mutated",
                     oracle_integrity_status=Status.MEASURED)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["oracle_integrity"] == "mutated"
    assert table[0]["oracle_integrity_status"] == Status.MEASURED


def test_compute_function_validation_table_unavailable_not_zero_for_unmeasured_function_validation():
    """A project with no independent function-validation harness (e.g. no
    --reference-results-root, or AlphaTrans/SKEL/CRUST which have none at
    all) must show Status.UNAVAILABLE/NOT_APPLICABLE with a null value --
    never a fabricated 0."""
    rows = [_raw_row(project_id="alphatrans__a", tool="alphatrans",
                     function_validation_total=None, function_validation_total_status=Status.UNAVAILABLE,
                     function_validation_pass_rate=None,
                     function_validation_pass_rate_status=Status.UNAVAILABLE)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["function_validation_total"] is None
    assert table[0]["function_validation_total_status"] == Status.UNAVAILABLE
    assert table[0]["function_validation_pass_rate"] is None


def test_compute_function_validation_table_unavailable_not_zero_for_unmeasured_function_harness_tests():
    """Same unavailable-vs-zero contract as function_validation_* above, but
    for function_harness_tests_* -- e.g. no --reference-results-root was
    supplied, or (SKEL) no javascript/*generated*.js files resolved for this
    project: Status.UNAVAILABLE with a null value, never a fabricated 0."""
    rows = [_raw_row(project_id="skel__a", tool="skel",
                     function_harness_tests_total=None, function_harness_tests_total_status=Status.UNAVAILABLE,
                     function_harness_tests_pass_rate=None,
                     function_harness_tests_pass_rate_status=Status.UNAVAILABLE)]
    table = A.compute_function_validation_table(rows, variant="full")
    assert table[0]["function_harness_tests_total"] is None
    assert table[0]["function_harness_tests_total_status"] == Status.UNAVAILABLE
    assert table[0]["function_harness_tests_pass_rate"] is None


# --------------------------------------------------------------------------- #
# CSV writing helpers
# --------------------------------------------------------------------------- #
def test_all_columns_preserves_first_seen_order():
    rows = [{"b": 1, "a": 2}, {"c": 3, "a": 4}]
    assert A._all_columns(rows) == ["b", "a", "c"]


def test_write_csv_round_trips(tmp_path: Path):
    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    path = tmp_path / "out.csv"
    A._write_csv(rows, ["a", "b"], path)
    text = path.read_text(encoding="utf-8")
    assert "a,b" in text
    assert "1,x" in text


def test_write_no_measured_data_csv_contains_watermark(tmp_path: Path):
    path = tmp_path / "empty.csv"
    A.write_no_measured_data_csv(path, ["a", "b"], reason="nothing collected yet")
    text = path.read_text(encoding="utf-8")
    assert A.NO_MEASURED_DATA_TEXT in text
    assert "nothing collected yet" in text


# --------------------------------------------------------------------------- #
# PDF/figure rendering (reportlab/matplotlib installed in this sandbox; also
# verify graceful degradation via monkeypatched optional_import)
# --------------------------------------------------------------------------- #
def test_render_table_pdf_writes_real_pdf_when_reportlab_available(tmp_path: Path):
    if C.optional_import("reportlab") is None:
        pytest.skip("reportlab not installed in this environment")
    path = tmp_path / "table1.pdf"
    ok = A.render_table_pdf([{"a": 1, "b": 2}], ["a", "b"], title="Test Table", path=path)
    assert ok is True
    assert path.exists()
    assert path.stat().st_size > 0


def test_render_table_pdf_writes_placeholder_when_reportlab_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(A.C, "optional_import", lambda name: None)
    path = tmp_path / "table1.pdf"
    ok = A.render_table_pdf([{"a": 1}], ["a"], title="Test Table", path=path)
    assert ok is False
    assert not path.exists()
    notice = Path(str(path) + ".unavailable.txt")
    assert notice.exists()
    assert "reportlab" in notice.read_text(encoding="utf-8")


def test_render_watermark_pdf_writes_real_pdf_when_reportlab_available(tmp_path: Path):
    if C.optional_import("reportlab") is None:
        pytest.skip("reportlab not installed in this environment")
    path = tmp_path / "watermark.pdf"
    ok = A.render_watermark_pdf(path, title="Table 1", reason="no data yet")
    assert ok is True
    assert path.exists()


def test_render_watermark_pdf_placeholder_when_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(A.C, "optional_import", lambda name: None)
    path = tmp_path / "watermark.pdf"
    ok = A.render_watermark_pdf(path, title="Table 1", reason="no data yet")
    assert ok is False
    notice = Path(str(path) + ".unavailable.txt")
    assert notice.exists()
    assert A.NO_MEASURED_DATA_TEXT in notice.read_text(encoding="utf-8")


def test_render_bar_figure_pdf_writes_real_pdf_when_matplotlib_available(tmp_path: Path):
    if C.optional_import("matplotlib") is None:
        pytest.skip("matplotlib not installed in this environment")
    path = tmp_path / "figure7.pdf"
    ok = A.render_bar_figure_pdf(["full", "noanalyzer"], {"tpr": [0.8, 0.5]},
                                title="Figure 7", ylabel="TPR", path=path)
    assert ok is True
    assert path.exists()
    assert path.stat().st_size > 0


def test_render_bar_figure_pdf_placeholder_when_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(A.C, "optional_import", lambda name: None)
    path = tmp_path / "figure7.pdf"
    ok = A.render_bar_figure_pdf(["full"], {"tpr": [0.8]}, title="Figure 7", ylabel="TPR", path=path)
    assert ok is False
    notice = Path(str(path) + ".unavailable.txt")
    assert notice.exists()
    assert "matplotlib" in notice.read_text(encoding="utf-8")


def test_render_bar_figure_pdf_handles_empty_series(tmp_path: Path):
    if C.optional_import("matplotlib") is None:
        pytest.skip("matplotlib not installed in this environment")
    path = tmp_path / "figure7_empty.pdf"
    ok = A.render_bar_figure_pdf([], {}, title="Figure 7", ylabel="TPR", path=path)
    assert ok is True
    assert path.exists()


# --------------------------------------------------------------------------- #
# Regression: render_bar_figure_pdf must never coerce a missing (None)
# measurement into a plotted 0 -- "not measured" must stay visually distinct
# from "measured, and it really was zero" (review finding #5).
# --------------------------------------------------------------------------- #
def test_partition_series_for_plot_never_coerces_none_to_zero():
    """Pure, matplotlib-free helper: verifies the core invariant directly,
    without needing matplotlib installed."""
    real_xs, real_ys, missing_xs = A._partition_series_for_plot([0, 1, 2], [0.8, None, 0.0])
    assert real_xs == [0, 2]
    assert real_ys == [0.8, 0.0]   # a genuine measured 0.0 is kept as a real value
    assert missing_xs == [1]       # the None is reported separately, never folded into real_ys


def test_partition_series_for_plot_all_missing():
    real_xs, real_ys, missing_xs = A._partition_series_for_plot([0, 1], [None, None])
    assert real_xs == []
    assert real_ys == []
    assert missing_xs == [0, 1]


def test_partition_series_for_plot_all_real():
    real_xs, real_ys, missing_xs = A._partition_series_for_plot([0, 1], [1.0, 2.0])
    assert real_xs == [0, 1]
    assert real_ys == [1.0, 2.0]
    assert missing_xs == []


def test_build_bar_figure_missing_values_rendered_as_distinct_hatched_marker_not_zero_bar():
    """Regression for review finding #5: previously ``ys = [v if v is not
    None else 0 for v in values]`` coerced None to a real 0-height bar,
    indistinguishable from an actual zero measurement. Missing values must
    now be rendered as a distinct hatched placeholder with an "N/A" label,
    never as a plain bar of height 0."""
    if C.optional_import("matplotlib") is None:
        pytest.skip("matplotlib not installed in this environment")
    fig, ax = A._build_bar_figure(["full", "noanalyzer"], {"tpr": [0.8, None]}, title="t", ylabel="y")
    try:
        heights = [p.get_height() for p in ax.patches]
        hatches = [p.get_hatch() for p in ax.patches]
        # Exactly one ordinary (non-hatched) bar for the real 0.8 measurement...
        plain_bars = [h for h, hatch in zip(heights, hatches) if not hatch]
        assert plain_bars == [pytest.approx(0.8)]
        # ...and the missing entry is a distinctly-hatched marker, NOT a 0-height plain bar.
        hatched_bars = [h for h, hatch in zip(heights, hatches) if hatch]
        assert len(hatched_bars) == 1
        assert hatched_bars[0] != 0   # a nominal non-zero marker height, never a bare 0
        texts = [t.get_text() for t in ax.texts]
        assert "N/A" in texts
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_build_bar_figure_all_missing_series_still_gets_legend_entry_without_plotting_zero():
    if C.optional_import("matplotlib") is None:
        pytest.skip("matplotlib not installed in this environment")
    fig, ax = A._build_bar_figure(["full"], {"tpr": [0.8], "nc": [None]}, title="t", ylabel="y")
    try:
        legend = ax.get_legend()
        assert legend is not None
        labels = {t.get_text() for t in legend.get_texts()}
        assert "tpr" in labels
        assert "nc" in labels   # legend entry preserved even though nc has no real values at all
        assert "N/A (not measured)" in labels
        # No patch for the all-missing "nc" series should silently read as a plain 0-height bar.
        heights_and_hatches = [(p.get_height(), p.get_hatch()) for p in ax.patches]
        assert all(hatch or height != 0 for height, hatch in heights_and_hatches)
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_render_bar_figure_pdf_does_not_crash_with_none_values(tmp_path: Path):
    if C.optional_import("matplotlib") is None:
        pytest.skip("matplotlib not installed in this environment")
    path = tmp_path / "figure7_missing.pdf"
    ok = A.render_bar_figure_pdf(["full", "noanalyzer"], {"tpr": [0.8, None]},
                                title="Figure 7", ylabel="TPR", path=path)
    assert ok is True
    assert path.exists()
    assert path.stat().st_size > 0


# --------------------------------------------------------------------------- #
# run_analysis orchestration
# --------------------------------------------------------------------------- #
def test_run_analysis_measured_data_writes_real_tables(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    tc_rows = [_tc_row(project_id="crust__a")]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=rows, test_comparison_rows=tc_rows,
                             output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1)
    assert summary["raw_has_data"] is True
    assert summary["test_has_data"] is True
    assert (output_root / "table1_effectiveness.csv").exists()
    assert (output_root / "table1_paper_reference.csv").exists()
    assert (output_root / "table2_test_translation.csv").exists()
    assert (output_root / "figure7_ablation.csv").exists()
    assert (output_root / "figure8_cost_tools.csv").exists()
    assert (output_root / "table_generated_tests.csv").exists()
    assert (output_root / "table_function_validation.csv").exists()
    assert (output_root / "paper_table1_side_by_side.csv").exists()
    assert (output_root / "paper_table2_side_by_side.csv").exists()
    comparison_pdf = output_root / "paper_tables_side_by_side.pdf"
    assert comparison_pdf.exists() or Path(
        str(comparison_pdf) + ".unavailable.txt"
    ).exists()
    assert (output_root / "paper_tables_side_by_side_provenance.json").exists()
    assert (output_root / "analysis_provenance.json").exists()
    assert summary["paper_tables_side_by_side_available"] is False
    table1_text = (output_root / "table1_effectiveness.csv").read_text(encoding="utf-8")
    assert A.NO_MEASURED_DATA_TEXT not in table1_text


def test_run_analysis_paper_reference_never_blended_with_measured():
    """table1_paper_reference_rows must never appear inside the measured
    table1 rows list (kept in a structurally separate file/section)."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    table1 = A.compute_table1_measured(rows, None, manifest, variant="full")
    assert all(r["source"] == "measured_codeweaver" for r in table1)


def test_run_analysis_empty_data_watermarks_every_artifact(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 1000)])
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=[], test_comparison_rows=None,
                             output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1,
                             on_empty="watermark")
    assert summary["raw_has_data"] is False
    for name in ("table1_effectiveness.csv", "figure7_ablation.csv", "figure8_cost_tools.csv",
                "table2_test_translation.csv", "table_generated_tests.csv", "table_function_validation.csv",
                "paper_table1_side_by_side.csv", "paper_table2_side_by_side.csv"):
        text = (output_root / name).read_text(encoding="utf-8")
        assert A.NO_MEASURED_DATA_TEXT in text


def test_run_analysis_on_empty_fail_aborts_without_writing_anything(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 1000)])
    output_root = tmp_path / "analysis"
    with pytest.raises(A.AnalysisAborted):
        A.run_analysis(manifest=manifest, raw_rows=[], test_comparison_rows=None,
                       output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1, on_empty="fail")
    assert not output_root.exists()


def test_run_analysis_on_empty_fail_succeeds_when_raw_present_but_test_comparisons_absent(tmp_path: Path):
    """test_comparisons is independently optional -- its absence must not
    trip --on-empty=fail when raw_runs has real data."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=rows, test_comparison_rows=None,
                             output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1,
                             on_empty="fail")
    assert summary["raw_has_data"] is True
    assert summary["test_has_data"] is False
    table2_text = (output_root / "table2_test_translation.csv").read_text(encoding="utf-8")
    assert A.NO_MEASURED_DATA_TEXT in table2_text   # watermarked per-artifact, but the run itself succeeded
    table1_text = (output_root / "table1_effectiveness.csv").read_text(encoding="utf-8")
    assert A.NO_MEASURED_DATA_TEXT not in table1_text


def test_run_analysis_rejects_unknown_on_empty_value(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 1000)])
    with pytest.raises(ValueError):
        A.run_analysis(manifest=manifest, raw_rows=[], test_comparison_rows=None,
                       output_root=tmp_path / "analysis", variants=["full"], repetitions=1,
                       on_empty="explode")


def test_run_analysis_writes_schema_validation_errors_in_provenance(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 1000)])
    bad_row = _raw_row(project_id="crust__a", variant="full")
    del bad_row["workspace_dir"]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=[bad_row], test_comparison_rows=None,
                             output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1)
    assert summary["schema_valid"] is False
    assert "0" in summary["schema_validation_errors"]
    provenance = json.loads((output_root / "analysis_provenance.json").read_text(encoding="utf-8"))
    assert provenance["schema_valid"] is False


def test_run_analysis_completeness_reflects_manifest_and_rows(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust", 1000), ("crust__b", "crust", 500)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=rows, test_comparison_rows=None,
                             output_root=output_root, variants=["full"], repetitions=1)
    assert summary["completeness"]["expected_cells"] == 2
    assert summary["completeness"]["measured_cells"] == 1


def test_run_analysis_project_ids_filters_every_output(tmp_path: Path):
    """Regression for review finding #4: --project (project_ids) must apply
    to EVERY output (completeness, table1/2, supporting tables), not be a
    no-op. Filtering must happen once, up front, so every downstream
    computation sees the same restricted data."""
    manifest = _manifest([("crust__a", "crust", 1000), ("crust__b", "crust", 500)])
    rows = [_raw_row(project_id="crust__a", variant="full"), _raw_row(project_id="crust__b", variant="full")]
    tc_rows = [_tc_row(project_id="crust__a"), _tc_row(project_id="crust__b")]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=rows, test_comparison_rows=tc_rows,
                             output_root=output_root, variants=["full"], repetitions=1,
                             project_ids=["crust__a"])
    assert summary["raw_runs_row_count"] == 1
    assert summary["completeness"]["expected_cells"] == 1
    assert summary["project_ids"] == ["crust__a"]
    table1_text = (output_root / "table1_effectiveness.csv").read_text(encoding="utf-8")
    assert "measured_run_count" in table1_text
    gen_text = (output_root / "table_generated_tests.csv").read_text(encoding="utf-8")
    assert "crust__b" not in gen_text


def test_run_analysis_primary_variant_selects_single_table1_table2_row_set(tmp_path: Path):
    """Regression for review finding #4: table1/table2/supporting tables must
    report exactly ONE requested (primary_variant, primary_repetition), while
    figure7/figure8 -- whose entire purpose is comparing variants -- still
    span every variant in `variants`."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full", dev_tests_total=10),
           _raw_row(project_id="crust__a", variant="noanalyzer", dev_tests_total=999)]
    tc_rows = [_tc_row(project_id="crust__a", variant="full", test_origin="translated"),
              _tc_row(project_id="crust__a", variant="noanalyzer", test_origin="translated",
                     source_test_name="test_other")]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=rows, test_comparison_rows=tc_rows,
                             output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1,
                             primary_variant="noanalyzer", primary_repetition=0)
    assert summary["primary_variant"] == "noanalyzer"
    with (output_root / "table1_effectiveness.csv").open(newline="", encoding="utf-8") as f:
        table1_by_tool = {r["tool"]: r for r in csv.DictReader(f)}
    assert table1_by_tool["crust"]["dev_tests_executed"] == "999"   # noanalyzer's row, not full's "10"
    # figure7/figure8 intentionally still span every variant regardless of primary_variant.
    figure7_text = (output_root / "figure7_ablation.csv").read_text(encoding="utf-8")
    assert "noanalyzer" in figure7_text and "full" in figure7_text


def test_run_analysis_table2_watermarked_when_test_comparisons_only_cover_other_variant(tmp_path: Path):
    """Regression for review finding #4: test_comparison_rows has REAL data,
    but none of it matches the default primary selection (full, rep 0) --
    table2/table_generated_tests must be watermarked (not silently render an
    empty-but-real all-zero table) even though test_has_data (broad) is
    True."""
    manifest = _manifest([("crust__a", "crust", 1000)])
    rows = [_raw_row(project_id="crust__a", variant="full")]
    tc_rows = [_tc_row(project_id="crust__a", variant="noanalyzer", test_origin="translated")]
    output_root = tmp_path / "analysis"
    summary = A.run_analysis(manifest=manifest, raw_rows=rows, test_comparison_rows=tc_rows,
                             output_root=output_root, variants=list(C.RUN_VARIANTS), repetitions=1)
    assert summary["test_has_data"] is True
    assert summary["test_has_data_for_primary_selection"] is False
    table2_text = (output_root / "table2_test_translation.csv").read_text(encoding="utf-8")
    assert A.NO_MEASURED_DATA_TEXT in table2_text
    gen_text = (output_root / "table_generated_tests.csv").read_text(encoding="utf-8")
    assert A.NO_MEASURED_DATA_TEXT in gen_text


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_parse_variants_all_and_explicit_list():
    assert A._parse_variants("all") == list(C.RUN_VARIANTS)
    assert A._parse_variants("full,noanalyzer") == ["full", "noanalyzer"]


def test_parse_variants_rejects_unknown():
    with pytest.raises(ValueError):
        A._parse_variants("not-a-real-variant")


def test_parse_primary_variant_accepts_known_variant():
    assert A._parse_primary_variant("noanalyzer") == "noanalyzer"


def test_parse_primary_variant_rejects_unknown():
    with pytest.raises(ValueError):
        A._parse_primary_variant("not-a-real-variant")


def test_parse_primary_repetition_parses_int():
    assert A._parse_primary_repetition("0") == 0
    assert A._parse_primary_repetition("2") == 2


def test_parse_primary_repetition_all_means_none():
    assert A._parse_primary_repetition("all") is None
    assert A._parse_primary_repetition("ALL") is None


def test_parse_primary_repetition_rejects_invalid():
    with pytest.raises(ValueError):
        A._parse_primary_repetition("not-an-int")
    with pytest.raises(ValueError):
        A._parse_primary_repetition("-1")


def test_build_parser_defaults():
    args = A.build_parser().parse_args(["--manifest", "m.json", "--raw-runs", "r.jsonl", "--output-root", "o"])
    assert args.on_empty == "watermark"
    assert args.test_comparisons is None
    assert args.pricing_usd_per_premium_request is None
    assert args.primary_variant == "full"
    assert args.primary_repetition == "0"
    assert args.project is None
    assert args.paper_results_workbook is None


def test_cli_main_project_flag_filters_every_output(tmp_path: Path):
    """Regression for review finding #4: --project was parsed but never
    passed into run_analysis (a complete no-op). It must now actually
    restrict output."""
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust", 1000), ("crust__b", "crust", 500)]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text(
        "\n".join(json.dumps(_raw_row(project_id=pid, variant="full")) for pid in ("crust__a", "crust__b")) + "\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "analysis"
    rc = A.main([
        "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path),
        "--output-root", str(output_root), "--project", "crust__a",
    ])
    assert rc == 0
    provenance = json.loads((output_root / "analysis_provenance.json").read_text(encoding="utf-8"))
    assert provenance["project_ids"] == ["crust__a"]
    assert provenance["raw_runs_row_count"] == 1


def test_cli_main_primary_variant_and_repetition_flags_reach_run_analysis(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust", 1000)]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text(
        json.dumps(_raw_row(project_id="crust__a", variant="noanalyzer")) + "\n", encoding="utf-8",
    )
    output_root = tmp_path / "analysis"
    rc = A.main([
        "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path),
        "--output-root", str(output_root), "--primary-variant", "noanalyzer", "--primary-repetition", "all",
    ])
    assert rc == 0
    provenance = json.loads((output_root / "analysis_provenance.json").read_text(encoding="utf-8"))
    assert provenance["primary_variant"] == "noanalyzer"
    assert provenance["primary_repetition"] is None


def test_cli_main_rejects_unknown_primary_variant(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust", 1000)]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        A.main([
            "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path),
            "--output-root", str(tmp_path / "analysis"), "--primary-variant", "not-a-real-variant",
        ])


def test_cli_main_writes_artifacts_and_returns_zero(tmp_path: Path, capsys):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust", 1000)]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text(json.dumps(_raw_row(project_id="crust__a", variant="full")) + "\n", encoding="utf-8")
    output_root = tmp_path / "analysis"
    rc = A.main([
        "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path),
        "--output-root", str(output_root), "--variant", "all", "--repetitions", "1",
    ])
    assert rc == 0
    assert (output_root / "table1_effectiveness.csv").exists()
    out = capsys.readouterr().out
    assert "raw_runs=1" in out


def test_cli_main_returns_nonzero_on_empty_fail(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust", 1000)]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text("", encoding="utf-8")
    output_root = tmp_path / "analysis"
    rc = A.main([
        "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path),
        "--output-root", str(output_root), "--on-empty", "fail",
    ])
    assert rc == 1
    assert not output_root.exists()


def test_cli_main_accepts_pricing_flag(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust", 1000)]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text(
        json.dumps(_raw_row(project_id="crust__a", variant="full", total_premium_requests=10)) + "\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "analysis"
    rc = A.main([
        "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path),
        "--output-root", str(output_root), "--pricing-usd-per-premium-request", "0.04",
    ])
    assert rc == 0
    figure8_text = (output_root / "figure8_cost_tools.csv").read_text(encoding="utf-8")
    assert "0.4" in figure8_text
