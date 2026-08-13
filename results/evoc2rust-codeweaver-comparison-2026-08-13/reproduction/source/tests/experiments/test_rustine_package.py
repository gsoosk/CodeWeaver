from __future__ import annotations

import json
from pathlib import Path

from experiments.rustine import common as C
from experiments.rustine.package import (
    REQUIRED_EVALUATION_FILES,
    REQUIRED_REPORT_FILES,
    _readme,
    _test_evidence,
    validate_completeness,
)
from experiments.rustine.evaluate import (
    GRABC_CONFIGURED_EXECUTION,
    GRABC_EVALUATION_EXECUTION,
)


def _complete_inputs(tmp_path: Path):
    runs_root = tmp_path / "runs"
    evaluation_root = tmp_path / "evaluation"
    report_root = tmp_path / "report"
    evaluation_root.mkdir()
    report_root.mkdir()
    rows = []
    for subject_id in range(1, 24):
        run_dir = runs_root / "full" / str(subject_id) / "rep0"
        run_dir.mkdir(parents=True)
        (run_dir / "recodeagent_run_state.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "app_id": f"full-{subject_id}-rep0",
                    "attempt": 1,
                    "provenance": {
                        "git_sha": {"status": "measured", "value": "abc123"},
                        "copilot_cli_version": {
                            "status": "measured",
                            "value": "Copilot CLI test",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        rows.append(
            {
                "subject_id": subject_id,
                "variant": "full",
                "repetition": 0,
                "run_completion": C.measurement(C.MEASURED, True),
                "contract_integrity": C.measurement(C.MEASURED, True),
                "contract_execution": {
                    "configured": (
                        GRABC_CONFIGURED_EXECUTION if subject_id == 6 else None
                    ),
                    "evaluated": (
                        GRABC_EVALUATION_EXECUTION if subject_id == 6 else None
                    ),
                    "override_applied": subject_id == 6,
                },
            }
        )
    for name in REQUIRED_EVALUATION_FILES:
        (evaluation_root / name).write_text("{}\n", encoding="utf-8")
    (evaluation_root / "evaluation.csv").write_text(
        "subject_id\n"
        + "".join(f"{subject_id}\n" for subject_id in range(1, 24)),
        encoding="utf-8",
    )
    for name in REQUIRED_REPORT_FILES:
        content = b"%PDF-test\n" if name.endswith(".pdf") else b"test\n"
        (report_root / name).write_bytes(content)
    for name, count in (
        ("validation.csv", 23),
        ("safety.csv", 23),
        ("statistics.csv", 2),
    ):
        (report_root / name).write_text(
            "value\n" + "".join(f"{index}\n" for index in range(count)),
            encoding="utf-8",
        )
    return (
        {
            "schema_version": 2,
            "rows": rows,
            "execution_overrides": {
                "schema_version": 1,
                "subjects_sha256": "test-subjects-sha",
                "overrides": [
                    {
                        "subject_id": 6,
                        "configured_value": GRABC_CONFIGURED_EXECUTION,
                        "evaluation_value": GRABC_EVALUATION_EXECUTION,
                        "reason": "test",
                    }
                ],
            },
            "provenance": {"harness_config_sha256": "test-subjects-sha"},
        },
        {
            "pdf_status": C.MEASURED,
            "summary_figure_pdf_status": C.MEASURED,
        },
        evaluation_root,
        report_root,
        runs_root,
    )


def test_complete_package_gate_requires_all_terminal_integrity_checked_rows(tmp_path):
    evaluation, manifest, evaluation_root, report_root, runs_root = _complete_inputs(
        tmp_path
    )
    result = validate_completeness(
        evaluation=evaluation,
        report_manifest=manifest,
        evaluation_root=evaluation_root,
        report_root=report_root,
        runs_root=runs_root,
    )
    assert result["complete"] is True
    assert result["terminal_runs"] == 23
    assert result["pdf_valid"] is True
    assert result["execution_override_valid"] is True


def test_package_gate_rejects_running_or_tampered_rows(tmp_path):
    evaluation, manifest, evaluation_root, report_root, runs_root = _complete_inputs(
        tmp_path
    )
    state_path = (
        runs_root / "full" / "7" / "rep0" / "recodeagent_run_state.json"
    )
    state_path.write_text('{"status": "running"}\n', encoding="utf-8")
    evaluation["rows"][8]["contract_integrity"] = C.measurement(
        C.MEASURED, False, "changed"
    )
    result = validate_completeness(
        evaluation=evaluation,
        report_manifest=manifest,
        evaluation_root=evaluation_root,
        report_root=report_root,
        runs_root=runs_root,
    )
    assert result["complete"] is False
    assert result["terminal_runs"] == 22
    assert result["contract_integrity_failures"] == [9]


def test_package_readme_points_to_exact_and_raw_outputs():
    text = _readme(
        {
            "paper": {"compilation_success": 23, "testable_subjects": 21},
            "codeweaver": {"compiled": 19, "fixed_contract_passed": 17},
        },
        {"terminal_runs": 23},
        {"file_count": 100, "parts": [{"path": "full.tar.gz.part-000"}]},
    )
    assert "report/comparison.pdf" in text
    assert "CodeWeaver compilations: 19/23" in text
    assert "CodeWeaver fixed-contract passes: 17/21 testable" in text
    assert "Raw archive reconstruction" in text


def test_junit_test_evidence_counts_passes(tmp_path):
    (tmp_path / "full-test-results.xml").write_text(
        '<testsuites><testsuite tests="20" errors="0" failures="0" '
        'skipped="3"/></testsuites>',
        encoding="utf-8",
    )
    (tmp_path / "test-environment-lock.txt").write_text(
        "pytest==9.0.2\n", encoding="utf-8"
    )
    evidence = _test_evidence(tmp_path)
    assert evidence["complete"] is True
    assert evidence["passed"] == 17
