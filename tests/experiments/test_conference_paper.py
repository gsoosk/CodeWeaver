from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.recodeagent import conference_paper as CP


def _report(*, complete: bool = True) -> dict:
    return {
        "project_count": 118,
        "verdict": {
            "complete": complete,
            "coverage_fraction": 1.0 if complete else 0.5,
            "reasons": [] if complete else ["matrix is incomplete"],
        },
    }


def _comparison() -> dict:
    primary = {
        "system": "codeweaver",
        "tool": "all",
        "repetition": 0,
        "metric": "project_pass_all",
        "status": "measured",
        "value": 0.5,
        "n_projects": 118,
        "excluded_projects": 0,
        "bootstrap": {"status": "measured", "ci_95": [0.4, 0.6]},
    }
    return {
        "protocol": {"configured_codeweaver_repetitions": 3},
        "inventory": [
            {
                "system": "codeweaver",
                "tool": "crust",
                "repetition": 0,
                "expected": 100,
                "measured": 100,
                "accounted_missing": 0,
                "unaccounted_missing": 0,
                "error": 0,
            },
            {
                "system": "codeweaver",
                "tool": "skel",
                "repetition": 0,
                "expected": 8,
                "measured": 8,
                "accounted_missing": 0,
                "unaccounted_missing": 0,
                "error": 0,
            },
        ],
        "inventory_completeness": {"unaccounted_missing": 0, "error": 0},
        "codeweaver_per_repetition_metrics": [primary],
        "codeweaver_repetition_summary": [
            {
                "system": "codeweaver",
                "tool": "all",
                "metric": "project_pass_all",
                "n": 3,
                "mean": 0.5,
                "sample_sd": 0.1,
                "ci_95_t": [0.25, 0.75],
                "status": "measured",
            }
        ],
        "primary_paired_comparisons": [
            {
                "tool": "all",
                "metric": "project_pass_all",
                "metric_kind": "binary",
                "n": 117,
                "cw_yes_rca_no_wins": 20,
                "rca_yes_cw_no_losses": 10,
                "ties": 87,
                "delta_percentage_points": 8.5,
                "exact_mcnemar_p_value": 0.1,
            }
        ],
        "crust_three_system_overlap": {
            "status": "unavailable",
            "n_triples": 0,
            "reason": "released artifacts unavailable",
        },
        "cost_correctness_frontier": {
            "status": "unavailable",
            "reason": "baseline cost unavailable",
        },
    }


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_inventory_is_aggregated_across_tools():
    rows = CP._inventory_totals(_comparison())
    assert rows == [["codeweaver", 0, 108, 108, 0, 0, 0]]


def test_latex_escaping_does_not_reescape_inserted_commands():
    escaped = CP._latex_escape(r"a_b\c%")
    assert escaped == r"a\_b\textbackslash{}c\%"


def test_generate_complete_conference_paper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report = _write_json(tmp_path / "report.json", _report())
    comparison = _write_json(tmp_path / "comparison.json", _comparison())
    analysis = _write_json(
        tmp_path / "analysis.json",
        {"paper_tables_side_by_side_available": True},
    )

    def render_pdf(title, sections, path):
        del title, sections
        Path(path).write_bytes(b"%PDF-1.4\n")
        return True

    monkeypatch.setattr(CP.RD, "render_pdf_report", render_pdf)
    result = CP.generate_conference_paper(
        report_data_path=report,
        system_comparison_path=comparison,
        analysis_provenance_path=analysis,
        output_root=tmp_path / "out",
        require_complete=True,
    )

    assert result["complete"] is True
    assert result["pdf"].read_bytes().startswith(b"%PDF-")
    assert "50.0%" in result["markdown"].read_text(encoding="utf-8")
    assert r"project\_pass\_all" in result["latex"].read_text(encoding="utf-8")
    provenance = json.loads(result["provenance"].read_text(encoding="utf-8"))
    assert set(provenance["inputs_sha256"]) == {
        "report_data",
        "system_comparison",
        "analysis_provenance",
    }


def test_require_complete_rejects_incomplete_report(tmp_path: Path):
    report = _write_json(tmp_path / "report.json", _report(complete=False))
    comparison = _write_json(tmp_path / "comparison.json", _comparison())
    analysis = _write_json(tmp_path / "analysis.json", {})

    with pytest.raises(RuntimeError, match="matrix is incomplete"):
        CP.generate_conference_paper(
            report_data_path=report,
            system_comparison_path=comparison,
            analysis_provenance_path=analysis,
            output_root=tmp_path / "out",
            require_complete=True,
        )
