"""Focused synthetic tests for the cross-system comparison stage."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from experiments.recodeagent import system_compare as SC
from experiments.recodeagent import common as C


def _manifest(path: Path) -> Path:
    projects = [
        {"id": "crust__alpha", "tool": "crust", "project": "alpha"},
        {"id": "oxidizer__beta", "tool": "oxidizer", "project": "beta"},
    ]
    C.atomic_write_json(path, {"projects": projects, "expected_total": 2})
    return path


def _row(
    project_id: str,
    tool: str,
    repetition: int,
    *,
    build: bool,
    pass_all: bool,
    passed: int,
    expected: int = 10,
    cost: float | None = None,
    system: str | None = None,
) -> dict:
    row = {
        "variant": "full",
        "project_id": project_id,
        "tool": tool,
        "repetition": repetition,
        "build": build,
        "build_status": "measured",
        "project_pass_all": pass_all,
        "project_pass_all_status": "measured",
        "validated_tests_expected": expected,
        "validated_tests_expected_status": "measured",
        "validated_tests_passed": passed,
        "validated_tests_passed_status": "measured",
        "validated_tests_pass_rate": passed / expected,
        "validated_tests_pass_rate_status": "measured",
        "total_nano_aiu": cost,
        "nano_aiu_status": "measured" if cost is not None else "unavailable",
    }
    if system is not None:
        row["system"] = system
    return row


def _jsonl(path: Path, rows: list[dict]) -> Path:
    C.atomic_write_text(path, "".join(json.dumps(row) + "\n" for row in rows))
    return path


def test_t_summary_has_sample_sd_and_exact_three_repetition_t_interval():
    summary = SC.t_summary([0.1, 0.2, 0.3])
    assert summary["status"] == C.Status.MEASURED
    assert summary["n"] == 3
    assert summary["mean"] == pytest.approx(0.2)
    assert summary["sample_sd"] == pytest.approx(0.1)
    assert summary["ci_95_t"] == pytest.approx([-0.04841377, 0.44841377])

    single = SC.t_summary([0.2])
    assert single["sample_sd"] is None
    assert single["variability_status"] == C.Status.MISSING


def test_paired_binary_exact_edges_and_bootstrap_are_deterministic():
    assert SC.exact_mcnemar_p_value(0, 0) == 1.0
    assert SC.exact_mcnemar_p_value(2, 0) == 0.5
    assert SC.exact_mcnemar_p_value(1, 1) == 1.0

    first = SC.bootstrap_mean_ci([0.0, 1.0, 1.0], resamples=200, seed=9)
    second = SC.bootstrap_mean_ci([0.0, 1.0, 1.0], resamples=200, seed=9)
    assert first == second

    paired = SC.paired_binary_stats(
        [True, True, False, False], [False, True, True, False], resamples=200, seed=7
    )
    assert paired["n"] == 4
    assert paired["cw_yes_rca_no_wins"] == 1
    assert paired["rca_yes_cw_no_losses"] == 1
    assert paired["ties"] == 2
    assert paired["exact_mcnemar_p_value"] == 1.0
    assert paired["paired_bootstrap_ci_percentage_points"] is not None


def test_malformed_success_shaped_boolean_is_not_coerced():
    with pytest.raises(ValueError, match="success-shaped"):
        SC._strict_bool("success", field="build")
    with pytest.raises(ValueError, match="numeric flags"):
        SC._strict_bool("1", field="build")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, False), (1, True), (0.0, False), (1.0, True), ("0", False), ("1.0", True)],
)
def test_workbook_binary_parser_accepts_excel_numeric_zero_one(value, expected):
    assert SC._workbook_binary_outcome(value) is expected


@pytest.mark.parametrize("value", [True, False, 0.5, float("nan"), 2, "success"])
def test_workbook_binary_parser_rejects_non_binary_or_success_shaped_values(value):
    with pytest.raises(ValueError):
        SC._workbook_binary_outcome(value)


def test_compare_writes_artifacts_retains_failures_and_never_zero_fills_costs(tmp_path: Path):
    manifest = _manifest(tmp_path / "manifest.json")
    codeweaver = []
    for repetition in range(3):
        codeweaver.extend([
            _row("crust__alpha", "crust", repetition, build=True, pass_all=True,
                 passed=10, cost=2.0 + repetition),
            _row("oxidizer__beta", "oxidizer", repetition, build=True, pass_all=False,
                 passed=7, cost=3.0 + repetition),
        ])
    baseline = [
        _row("crust__alpha", "crust", 0, build=False, pass_all=False, passed=0,
             system="recodeagent"),
        _row("oxidizer__beta", "oxidizer", 0, build=True, pass_all=True, passed=8,
             system="recodeagent"),
    ]
    baseline_failures = [
        {
            "system": "prior", "variant": "full", "project_id": "crust__alpha",
            "tool": "crust", "repetition": 0, "failure_status": "unavailable",
            "reason": "released SWE-agent output unavailable",
        }
    ]
    result = SC.compare_systems(
        codeweaver_raw_path=_jsonl(tmp_path / "cw.jsonl", codeweaver),
        baseline_raw_path=_jsonl(tmp_path / "baseline.jsonl", baseline),
        baseline_failures_path=_jsonl(tmp_path / "baseline-failures.jsonl", baseline_failures),
        manifest_path=manifest,
        output_root=tmp_path / "out",
        resamples=200,
    )

    assert result["data"]["crust_three_system_overlap"]["status"] == C.Status.UNAVAILABLE
    assert "not supplied" in result["data"]["crust_three_system_overlap"]["reason"]
    prior_crust = next(
        row for row in result["data"]["inventory"]
        if row["system"] == "prior" and row["tool"] == "crust" and row["repetition"] == 0
    )
    assert prior_crust["unavailable"] == 1
    assert result["data"]["input_row_accounting"]["failure_rows_retained"] == 1

    frontier = {row["system"]: row for row in result["data"]["cost_correctness_frontier"]["rows"]}
    assert frontier["recodeagent"]["cost_status"] == C.Status.UNAVAILABLE
    assert frontier["recodeagent"]["mean_actual_cost"] is None
    assert result["data"]["cost_correctness_frontier"]["status"] == C.Status.UNAVAILABLE

    for key in ("analysis_json", "inventory_csv", "metrics_csv", "paired_csv", "latex", "provenance"):
        assert result["paths"][key].is_file()
    assert result["paths"]["pdf"].is_file() or Path(str(result["paths"]["pdf"]) + ".unavailable.txt").is_file()
    with result["paths"]["failure_evidence_csv"].open(encoding="utf-8", newline="") as handle:
        evidence = list(csv.DictReader(handle))
    assert evidence[0]["reason"] == "released SWE-agent output unavailable"


def test_inventory_separates_explicit_missing_failure_from_unaccounted_cell(tmp_path: Path):
    manifest = _manifest(tmp_path / "manifest.json")
    explicit_missing = [{
        "system": "prior", "variant": "full", "project_id": "crust__alpha",
        "tool": "crust", "repetition": 0, "failure_status": "missing",
        "reason": "released artifact absent",
    }]
    result = SC.compare_systems(
        codeweaver_raw_path=_jsonl(tmp_path / "cw.jsonl", []),
        baseline_raw_path=_jsonl(tmp_path / "baseline.jsonl", []),
        baseline_failures_path=_jsonl(tmp_path / "failures.jsonl", explicit_missing),
        manifest_path=manifest,
        output_root=tmp_path / "out",
        resamples=100,
    )
    prior_crust = next(
        row for row in result["data"]["inventory"]
        if row["system"] == "prior" and row["tool"] == "crust" and row["repetition"] == 0
    )
    prior_oxidizer = next(
        row for row in result["data"]["inventory"]
        if row["system"] == "prior" and row["tool"] == "oxidizer" and row["repetition"] == 0
    )
    assert prior_crust["missing"] == 1
    assert prior_crust["accounted_missing"] == 1
    assert prior_crust["unaccounted_missing"] == 0
    assert prior_crust["all_expected_cells_accounted_for"] is True
    assert prior_oxidizer["missing"] == 1
    assert prior_oxidizer["accounted_missing"] == 0
    assert prior_oxidizer["unaccounted_missing"] == 1
    assert prior_oxidizer["all_expected_cells_accounted_for"] is False
    completeness = result["data"]["inventory_completeness"]
    assert completeness["accounted_missing"] >= 1
    assert completeness["unaccounted_missing"] >= 1
    assert completeness["all_expected_cells_accounted_for"] is False


def test_duplicate_system_project_repetition_key_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path / "manifest.json")
    duplicate = [
        _row("crust__alpha", "crust", 0, build=True, pass_all=True, passed=10),
        _row("crust__alpha", "crust", 0, build=False, pass_all=False, passed=0),
    ]
    with pytest.raises(ValueError, match="duplicate normalized raw-run key"):
        SC.compare_systems(
            codeweaver_raw_path=_jsonl(tmp_path / "cw.jsonl", duplicate),
            baseline_raw_path=_jsonl(tmp_path / "baseline.jsonl", []),
            manifest_path=manifest,
            output_root=tmp_path / "out",
            resamples=100,
        )


def test_disjoint_baseline_inputs_and_failures_are_unioned_and_hashed(tmp_path: Path):
    manifest = _manifest(tmp_path / "manifest.json")
    codeweaver = [
        _row("crust__alpha", "crust", repetition, build=True, pass_all=True, passed=10)
        for repetition in range(3)
    ]
    recodeagent = _jsonl(
        tmp_path / "recodeagent.jsonl",
        [_row("crust__alpha", "crust", 0, build=True, pass_all=True, passed=9, system="recodeagent")],
    )
    prior = _jsonl(
        tmp_path / "prior.jsonl",
        [_row("oxidizer__beta", "oxidizer", 0, build=False, pass_all=False, passed=0, system="prior")],
    )
    first_failures = _jsonl(
        tmp_path / "first-failures.jsonl",
        [{"system": "prior", "variant": "full", "project_id": "crust__alpha",
          "tool": "crust", "repetition": 0, "failure_status": "unavailable", "reason": "absent"}],
    )
    second_failures = _jsonl(
        tmp_path / "second-failures.jsonl",
        [{"system": "recodeagent", "variant": "full", "project_id": "oxidizer__beta",
          "tool": "oxidizer", "repetition": 0, "failure_status": "missing", "reason": "absent"}],
    )
    result = SC.compare_systems(
        codeweaver_raw_path=_jsonl(tmp_path / "cw.jsonl", codeweaver),
        baseline_raw_path=[recodeagent, prior],
        baseline_failures_path=[first_failures, second_failures],
        manifest_path=manifest,
        output_root=tmp_path / "out",
        resamples=100,
    )
    assert result["data"]["input_row_accounting"]["baseline_raw_input_count"] == 2
    assert result["data"]["input_row_accounting"]["baseline_failure_input_count"] == 2
    assert result["data"]["input_row_accounting"]["baseline_raw_selected"] == 2
    assert result["data"]["input_row_accounting"]["failure_rows_retained"] == 2
    hashes = result["provenance"]["inputs_sha256"]
    assert len(hashes["baseline_raw"]) == 2
    assert len(hashes["baseline_failures"]) == 2
    assert all(entry["sha256"] for entry in hashes["baseline_raw"])


def test_cross_file_baseline_duplicate_key_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path / "manifest.json")
    duplicate = _row(
        "crust__alpha", "crust", 0, build=True, pass_all=True, passed=10, system="recodeagent"
    )
    with pytest.raises(ValueError, match="duplicate system/project/repetition key"):
        SC.compare_systems(
            codeweaver_raw_path=_jsonl(tmp_path / "cw.jsonl", []),
            baseline_raw_path=[
                _jsonl(tmp_path / "one.jsonl", [duplicate]),
                _jsonl(tmp_path / "two.jsonl", [duplicate]),
            ],
            manifest_path=manifest,
            output_root=tmp_path / "out",
            resamples=100,
        )


def test_cli_accepts_repeated_disjoint_baseline_flags():
    args = SC.build_parser().parse_args([
        "--codeweaver-raw", "cw.jsonl",
        "--baseline-raw", "recodeagent.jsonl",
        "--baseline-raw", "prior.jsonl",
        "--baseline-failures", "recodeagent-failures.csv",
        "--baseline-failures", "prior-failures.csv",
        "--manifest", "manifest.json",
        "--output-root", "out",
    ])
    assert args.baseline_raw == ["recodeagent.jsonl", "prior.jsonl"]
    assert args.baseline_failures == ["recodeagent-failures.csv", "prior-failures.csv"]


def test_swe_agent_overlap_is_unavailable_without_authoritative_workbook():
    crust = [
        {"id": f"crust__p{index}", "tool": "crust", "project": f"p{index}"}
        for index in range(100)
    ]
    result = SC.extract_swe_agent_workbook_outcomes(None, crust)
    assert result["status"] == C.Status.UNAVAILABLE
    assert result["outcomes"] == {}
    assert "not supplied" in result["reason"]
