"""Tests for experiments/recodeagent/report.py: data loading (optional-file
semantics), blocker-reason aggregation, variant x tool coverage breakdown,
the completion verdict (the one place this module may say "complete", and
only when every check passes), checksum/provenance JSON assembly, full
report orchestration/rendering, and the CLI (including --require-complete
exit-code gating). No network, LLM, or toolchain access -- everything runs
against synthetic fixtures created on the fly.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import report as RPT


# --------------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------------- #
def _manifest(projects: list[tuple[str, str]]) -> dict:
    return {"projects": [{"id": pid, "tool": tool, "loc_source": 10} for pid, tool in projects]}


def _full_manifest() -> dict:
    projects = ([(f"crust__{i}", "crust") for i in range(100)]
               + [(f"oxidizer__{i}", "oxidizer") for i in range(6)]
               + [(f"alphatrans__{i}", "alphatrans") for i in range(4)]
               + [(f"skel__{i}", "skel") for i in range(8)])
    return _manifest(projects)


def _write_failures_csv(path: Path, failures: list[dict]) -> None:
    columns = ["variant", "project_id", "tool", "repetition", "workspace_dir", "reason", "detected_at"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in failures:
            writer.writerow(row)


def _failure(**overrides) -> dict:
    row = {"variant": "full", "project_id": "crust__a", "tool": "crust", "repetition": 0,
          "workspace_dir": "x", "reason": "not_attempted: no run directory found", "detected_at": C.utcnow_iso()}
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def test_load_manifest_reads_json(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust")])
    path = tmp_path / "manifest.json"
    C.atomic_write_json(path, manifest)
    assert RPT.load_manifest(path) == manifest


def test_load_raw_runs_or_empty_none_path_returns_empty():
    assert RPT.load_raw_runs_or_empty(None) == []


def test_load_raw_runs_or_empty_missing_file_returns_empty(tmp_path: Path):
    assert RPT.load_raw_runs_or_empty(tmp_path / "nope.jsonl") == []


def test_load_raw_runs_or_empty_reads_rows(tmp_path: Path):
    path = tmp_path / "raw_runs.jsonl"
    path.write_text(json.dumps({"variant": "full", "project_id": "crust__a"}) + "\n", encoding="utf-8")
    rows = RPT.load_raw_runs_or_empty(path)
    assert len(rows) == 1


def test_load_analysis_provenance_none_path_returns_none():
    assert RPT.load_analysis_provenance(None) is None


def test_load_analysis_provenance_missing_file_returns_none(tmp_path: Path):
    assert RPT.load_analysis_provenance(tmp_path / "nope.json") is None


def test_load_analysis_provenance_reads_json(tmp_path: Path):
    path = tmp_path / "analysis_provenance.json"
    data = {"completeness": {"coverage_fraction": 1.0}}
    C.atomic_write_json(path, data)
    assert RPT.load_analysis_provenance(path) == data


def test_read_failures_csv_none_path_returns_empty():
    assert RPT.read_failures_csv(None) == []


def test_read_failures_csv_missing_file_returns_empty(tmp_path: Path):
    assert RPT.read_failures_csv(tmp_path / "nope.csv") == []


def test_read_failures_csv_reads_rows(tmp_path: Path):
    path = tmp_path / "failures.csv"
    _write_failures_csv(path, [_failure()])
    rows = RPT.read_failures_csv(path)
    assert len(rows) == 1
    assert rows[0]["reason"] == "not_attempted: no run directory found"


# --------------------------------------------------------------------------- #
# aggregate_blockers
# --------------------------------------------------------------------------- #
def test_aggregate_blockers_groups_by_category_prefix():
    failures = [_failure(reason="not_attempted: no run directory found"),
               _failure(reason="not_attempted: another detail"),
               _failure(reason="not_terminal: run status is 'running'")]
    blockers = RPT.aggregate_blockers(failures)
    by_cat = {b["category"]: b for b in blockers}
    assert by_cat["not_attempted"]["count"] == 2
    assert by_cat["not_terminal"]["count"] == 1


def test_aggregate_blockers_sorted_by_count_descending_then_alpha():
    failures = [_failure(reason="b_cat: x"), _failure(reason="a_cat: x"), _failure(reason="a_cat: y"),
               _failure(reason="a_cat: z")]
    blockers = RPT.aggregate_blockers(failures)
    assert [b["category"] for b in blockers] == ["a_cat", "b_cat"]


def test_aggregate_blockers_empty_input():
    assert RPT.aggregate_blockers([]) == []


def test_aggregate_blockers_handles_missing_or_blank_reason():
    failures = [_failure(reason=""), _failure(reason=None)]
    blockers = RPT.aggregate_blockers(failures)
    assert blockers == [{"category": "unknown", "count": 2, "example_reason": ""}]


def test_aggregate_blockers_keeps_first_example_reason_per_category():
    failures = [_failure(reason="cat: first detail"), _failure(reason="cat: second detail")]
    blockers = RPT.aggregate_blockers(failures)
    assert blockers[0]["example_reason"] == "cat: first detail"


# --------------------------------------------------------------------------- #
# compute_coverage_breakdown
# --------------------------------------------------------------------------- #
def test_compute_coverage_breakdown_expected_from_manifest():
    manifest = _manifest([("crust__a", "crust"), ("crust__b", "crust"), ("oxidizer__a", "oxidizer")])
    rows = [{"variant": "full", "project_id": "crust__a", "tool": "crust"}]
    breakdown = RPT.compute_coverage_breakdown(manifest, rows, variants=["full"], repetitions=1)
    by_tool = {r["tool"]: r for r in breakdown}
    assert by_tool["crust"]["expected"] == 2
    assert by_tool["crust"]["measured"] == 1
    assert by_tool["crust"]["coverage_fraction"] == pytest.approx(0.5)
    assert by_tool["oxidizer"]["expected"] == 1
    assert by_tool["oxidizer"]["measured"] == 0
    assert by_tool["oxidizer"]["coverage_fraction"] == pytest.approx(0.0)


def test_compute_coverage_breakdown_respects_repetitions():
    manifest = _manifest([("crust__a", "crust")])
    breakdown = RPT.compute_coverage_breakdown(manifest, [], variants=["full"], repetitions=3)
    assert breakdown[0]["expected"] == 3


def test_compute_coverage_breakdown_one_row_per_variant_x_tool():
    manifest = _manifest([("crust__a", "crust"), ("oxidizer__a", "oxidizer")])
    breakdown = RPT.compute_coverage_breakdown(manifest, [], variants=["full", "noanalyzer"], repetitions=1)
    assert len(breakdown) == 4   # 2 variants * 2 tools


def test_compute_coverage_breakdown_empty_manifest():
    assert RPT.compute_coverage_breakdown({"projects": []}, [], variants=["full"], repetitions=1) == []


# --------------------------------------------------------------------------- #
# compute_completion_verdict
# --------------------------------------------------------------------------- #
def test_compute_completion_verdict_no_analysis_provenance_is_incomplete():
    verdict = RPT.compute_completion_verdict(_full_manifest(), None)
    assert verdict["complete"] is False
    assert verdict["coverage_fraction"] is None
    assert any("analyze.py has not been run" in r for r in verdict["reasons"])


def test_compute_completion_verdict_wrong_project_count_is_incomplete():
    manifest = _manifest([("crust__a", "crust")])
    verdict = RPT.compute_completion_verdict(manifest, {"completeness": {"coverage_fraction": 1.0},
                                                        "schema_valid": True,
                                                        "provenance_consistency": {"consistent": True}})
    assert verdict["complete"] is False
    assert any("expected 118" in r for r in verdict["reasons"])


def test_compute_completion_verdict_full_coverage_schema_valid_consistent_is_complete():
    analysis_provenance = {
        "completeness": {"coverage_fraction": 1.0, "missing_cells": []},
        "paper_test_completeness": {"coverage_fraction": 1.0, "missing_cells": [], "duplicate_rows": 0},
        "generated_test_completeness": {"coverage_fraction": 1.0, "missing_cells": [], "duplicate_rows": 0},
        "schema_valid": True,
        "provenance_consistency": {"consistent": True},
        "paper_tables_side_by_side_available": True,
    }
    verdict = RPT.compute_completion_verdict(_full_manifest(), analysis_provenance)
    assert verdict["complete"] is True
    assert verdict["reasons"] == []
    assert verdict["coverage_fraction"] == 1.0


def test_compute_completion_verdict_partial_coverage_is_incomplete():
    analysis_provenance = {
        "completeness": {"coverage_fraction": 0.5, "missing_cells": [{"variant": "full", "project_id": "x"}]},
        "schema_valid": True,
        "provenance_consistency": {"consistent": True},
    }
    verdict = RPT.compute_completion_verdict(_full_manifest(), analysis_provenance)
    assert verdict["complete"] is False
    assert any("0.5" in r for r in verdict["reasons"])


def test_compute_completion_verdict_schema_invalid_is_incomplete():
    analysis_provenance = {
        "completeness": {"coverage_fraction": 1.0, "missing_cells": []},
        "schema_valid": False,
        "provenance_consistency": {"consistent": True},
    }
    verdict = RPT.compute_completion_verdict(_full_manifest(), analysis_provenance)
    assert verdict["complete"] is False
    assert any("schema validation" in r for r in verdict["reasons"])


def test_compute_completion_verdict_inconsistent_provenance_is_incomplete():
    analysis_provenance = {
        "completeness": {"coverage_fraction": 1.0, "missing_cells": []},
        "schema_valid": True,
        "provenance_consistency": {"consistent": False},
    }
    verdict = RPT.compute_completion_verdict(_full_manifest(), analysis_provenance)
    assert verdict["complete"] is False
    assert any("inconsistent" in r for r in verdict["reasons"])


# --------------------------------------------------------------------------- #
# Checksums / provenance JSON
# --------------------------------------------------------------------------- #
def test_compute_checksums_existing_file(tmp_path: Path):
    path = tmp_path / "f.txt"
    path.write_text("hello", encoding="utf-8")
    result = RPT.compute_checksums({"f": path})
    assert result["f"]["exists"] is True
    assert result["f"]["sha256"] == C.file_sha256(path)
    assert result["f"]["size_bytes"] == 5


def test_compute_checksums_missing_file(tmp_path: Path):
    result = RPT.compute_checksums({"f": tmp_path / "nope.txt"})
    assert result["f"]["exists"] is False
    assert result["f"]["sha256"] is None


def test_compute_checksums_none_path():
    result = RPT.compute_checksums({"f": None})
    assert result["f"] == {"path": None, "exists": False, "sha256": None}


def test_build_manifest_checksum_provenance_structure(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust")]))
    result = RPT.build_manifest_checksum_provenance(
        manifest_path=manifest_path, raw_runs_path=None, test_comparisons_path=None,
    )
    assert result["checksums"]["manifest"]["exists"] is True
    assert result["checksums"]["raw_runs"]["exists"] is False
    assert "report_generation_provenance" in result
    assert "note" in result


# --------------------------------------------------------------------------- #
# build_report / render_report_sections
# --------------------------------------------------------------------------- #
def test_build_report_assembles_all_pieces():
    manifest = _manifest([("crust__a", "crust")])
    data = RPT.build_report(manifest=manifest, analysis_provenance=None, failures=[_failure()],
                            comparison_failures=[], raw_rows=[], variants=["full"], repetitions=1)
    assert data["project_count"] == 1
    assert data["expected_total_projects"] == C.EXPECTED_TOTAL_PROJECTS
    assert data["analysis_available"] is False
    assert len(data["blockers"]) == 1
    assert data["verdict"]["complete"] is False


def test_render_report_sections_includes_all_headings():
    manifest = _manifest([("crust__a", "crust")])
    data = RPT.build_report(manifest=manifest, analysis_provenance=None, failures=[_failure()],
                            comparison_failures=[], raw_rows=[{"variant": "full", "project_id": "crust__a",
                                                              "tool": "crust"}],
                            variants=["full"], repetitions=1)
    sections = RPT.render_report_sections(data)
    headings = [s.heading for s in sections]
    assert "Completion Verdict" in headings
    assert "Manifest" in headings
    assert "Execution Coverage (raw_runs, by variant x tool)" in headings
    assert "Blockers (collect.py failures.csv)" in headings
    assert "Blockers (test_compare.py comparison_failures.csv)" in headings
    assert "Analysis Availability" in headings


def test_render_report_sections_shows_incomplete_status_text():
    manifest = _manifest([("crust__a", "crust")])
    data = RPT.build_report(manifest=manifest, analysis_provenance=None, failures=[], comparison_failures=[],
                            raw_rows=[], variants=["full"], repetitions=1)
    sections = RPT.render_report_sections(data)
    verdict_section = next(s for s in sections if s.heading == "Completion Verdict")
    assert "INCOMPLETE" in verdict_section.body
    assert "COMPLETE" not in verdict_section.body.replace("INCOMPLETE", "")


def test_render_report_sections_shows_complete_status_text():
    data = RPT.build_report(
        manifest=_full_manifest(),
        analysis_provenance={"completeness": {"coverage_fraction": 1.0, "missing_cells": []},
                            "paper_test_completeness": {
                                "coverage_fraction": 1.0, "missing_cells": [], "duplicate_rows": 0,
                            },
                            "generated_test_completeness": {
                                "coverage_fraction": 1.0, "missing_cells": [], "duplicate_rows": 0,
                            },
                            "schema_valid": True, "provenance_consistency": {"consistent": True},
                            "paper_tables_side_by_side_available": True},
        failures=[], comparison_failures=[], raw_rows=[], variants=["full"], repetitions=1,
    )
    sections = RPT.render_report_sections(data)
    verdict_section = next(s for s in sections if s.heading == "Completion Verdict")
    assert "Status: COMPLETE" in verdict_section.body
    assert "All completion criteria met." in verdict_section.body


# --------------------------------------------------------------------------- #
# write_report
# --------------------------------------------------------------------------- #
def test_write_report_creates_markdown_pdf_and_data_json(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust")])
    data = RPT.build_report(manifest=manifest, analysis_provenance=None, failures=[], comparison_failures=[],
                            raw_rows=[], variants=["full"], repetitions=1)
    output_root = tmp_path / "report_out"
    paths = RPT.write_report(data, output_root)
    assert paths["markdown"].exists()
    assert paths["pdf"].exists() or Path(str(paths["pdf"]) + ".unavailable.txt").exists()
    assert paths["data"].exists()
    written = json.loads(paths["data"].read_text(encoding="utf-8"))
    assert written["project_count"] == 1


def test_write_report_markdown_never_claims_complete_when_incomplete(tmp_path: Path):
    manifest = _manifest([("crust__a", "crust")])
    data = RPT.build_report(manifest=manifest, analysis_provenance=None, failures=[], comparison_failures=[],
                            raw_rows=[], variants=["full"], repetitions=1)
    paths = RPT.write_report(data, tmp_path / "out")
    text = paths["markdown"].read_text(encoding="utf-8")
    assert "Status: INCOMPLETE" in text


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_parse_variants_all_and_explicit_list():
    assert RPT._parse_variants("all") == list(C.RUN_VARIANTS)
    assert RPT._parse_variants("full,noanalyzer") == ["full", "noanalyzer"]


def test_parse_variants_rejects_unknown():
    with pytest.raises(ValueError):
        RPT._parse_variants("not-a-real-variant")


def test_build_parser_defaults():
    args = RPT.build_parser().parse_args(["--manifest", "m.json", "--output-root", "o"])
    assert args.require_complete is False
    assert args.raw_runs is None
    assert args.analysis_provenance is None


def test_cli_main_writes_all_artifacts_and_returns_zero_by_default(tmp_path: Path, capsys):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust")]))
    output_root = tmp_path / "report_out"
    rc = RPT.main(["--manifest", str(manifest_path), "--output-root", str(output_root)])
    assert rc == 0
    assert (output_root / "reproducibility_report.md").exists()
    assert (output_root / "manifest_checksum_provenance.json").exists()
    out = capsys.readouterr().out
    assert "verdict=INCOMPLETE" in out


def test_cli_main_require_complete_returns_nonzero_when_incomplete(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust")]))
    output_root = tmp_path / "report_out"
    rc = RPT.main(["--manifest", str(manifest_path), "--output-root", str(output_root), "--require-complete"])
    assert rc == 1
    # The report must still be written even though the exit code signals failure.
    assert (output_root / "reproducibility_report.md").exists()


def test_cli_main_require_complete_returns_zero_when_complete(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _full_manifest())
    analysis_provenance_path = tmp_path / "analysis_provenance.json"
    C.atomic_write_json(analysis_provenance_path, {
        "completeness": {"coverage_fraction": 1.0, "missing_cells": []},
        "paper_test_completeness": {"coverage_fraction": 1.0, "missing_cells": [], "duplicate_rows": 0},
        "generated_test_completeness": {
            "coverage_fraction": 1.0, "missing_cells": [], "duplicate_rows": 0,
        },
        "schema_valid": True, "provenance_consistency": {"consistent": True},
        "paper_tables_side_by_side_available": True,
    })
    output_root = tmp_path / "report_out"
    rc = RPT.main(["--manifest", str(manifest_path), "--output-root", str(output_root),
                  "--analysis-provenance", str(analysis_provenance_path), "--require-complete"])
    assert rc == 0


def test_cli_main_with_raw_runs_and_failures(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest([("crust__a", "crust"), ("crust__b", "crust")]))
    raw_runs_path = tmp_path / "raw_runs.jsonl"
    raw_runs_path.write_text(json.dumps({"variant": "full", "project_id": "crust__a", "tool": "crust"}) + "\n",
                            encoding="utf-8")
    failures_path = tmp_path / "failures.csv"
    _write_failures_csv(failures_path, [_failure(project_id="crust__b")])
    output_root = tmp_path / "report_out"
    rc = RPT.main([
        "--manifest", str(manifest_path), "--raw-runs", str(raw_runs_path), "--failures", str(failures_path),
        "--output-root", str(output_root), "--variant", "full",
    ])
    assert rc == 0
    text = (output_root / "reproducibility_report.md").read_text(encoding="utf-8")
    assert "not_attempted" in text
    assert "crust" in text
