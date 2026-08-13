from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from experiments.evoc2rust import common as C
from experiments.evoc2rust.config import load_config, validate_config
from experiments.evoc2rust.evaluator import (
    materialize_evaluation_copy,
    unsafe_line_metrics,
)
from experiments.evoc2rust.package import (
    REQUIRED_EVALUATION_FILES,
    REQUIRED_REPORT_FILES,
    validate_completeness,
)
from experiments.evoc2rust.prepare import (
    active_test_functions,
    strip_function_bodies,
)
from experiments.evoc2rust.report import (
    aggregate_results,
    render_latex,
    table4_rows,
    table5_rows,
    write_reports,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_frozen_config_covers_public_benchmark_and_paper_tables():
    config = load_config()
    assert len(config["subjects"]) == 15
    assert sum(len(row["modules"]) for row in config["subjects"]) == 19
    assert sum(len(row["test_functions"]) for row in config["subjects"]) == 125
    assert sum(row["c_assertions"] for row in config["subjects"]) == 637
    assert len(config["paper"]["table4_rows"]) == 20
    assert len(config["paper"]["table5_c2r_rows"]) == 14
    assert len(config["paper"]["table6_rows"]) == 5

    changed = copy.deepcopy(config)
    changed["protocol"]["repetitions"] = 1
    with pytest.raises(ValueError, match="protocol drifted"):
        validate_config(changed)


def test_active_test_parser_ignores_commented_out_entries(tmp_path):
    source = tmp_path / "test/example.c"
    _write(
        source,
        """
void test_one(void) {}
void test_disabled(void) {}
static UnitTestFunction tests[] = {
    test_one,
    /* test_disabled, */
    NULL
};
""",
    )
    assert active_test_functions(tmp_path, "test/example.c") == ["test_one"]


def test_body_stripping_removes_nested_implementations_only():
    source = r'''
pub unsafe extern "C" fn alpha(value: i32) -> i32 {
    let brace = "}";
    if value > 0 { return value + 7; }
    0
}
extern "C" {
    pub fn external(value: i32) -> i32;
}
pub fn beta() {
    /* ignored { } */
    alpha(4);
}
'''
    stripped, count = strip_function_bodies(source)
    assert count == 2
    assert stripped.count("CodeWeaver must implement this function") == 2
    assert "value + 7" not in stripped
    assert "pub fn external(value: i32) -> i32;" in stripped


def _synthetic_contract(root: Path) -> Path:
    contract = root / "oracle"
    _write(contract / "tests/alloc_testing.rs", "pub unsafe fn alloc_test_set_limit(_: i32) {}\npub unsafe fn alloc_test_get_allocated() -> usize { 0 }\n")
    _write(contract / "tests/framework.rs", "")
    _write(
        contract / "tests/fixed_test.rs",
        "unsafe extern \"C\" fn test_private() {}\n",
    )
    _write(contract / "Cargo.lock", "# synthetic lock\n")
    files = [
        path.relative_to(contract).as_posix()
        for path in contract.rglob("*")
        if path.is_file()
    ]
    lock = {
        "schema_version": 1,
        "subject_id": 1,
        "subject_name": "synthetic",
        "crate_name": "vivo_subject_01",
        "modules": ["sample"],
        "support_modules": [],
        "test_module": "test_sample",
        "test_functions": ["test_private"],
        "c_assertions": 1,
        "loc_source": 1,
        "rust_toolchain": "nightly-2025-09-15",
        "cc_version": "1.4.2",
        "file_sha256": {
            relative: C.file_sha256(contract / relative)
            for relative in files
        },
    }
    C.atomic_write_json(contract / "contract.json", lock)
    return contract


def test_evaluator_restores_lock_and_private_test_dispatch(tmp_path):
    contract = _synthetic_contract(tmp_path)
    target = tmp_path / "target"
    _write(
        target / "src/production/sample.rs",
        '#[no_mangle]\npub extern "C" fn sample() {}\n',
    )
    _write(target / "Cargo.toml", '[package]\nname="tampered"\n')
    _write(target / "src/lib.rs", "pub mod bypass;\n")
    scratch, project, lock = materialize_evaluation_copy(target, contract)
    try:
        assert lock["crate_name"] == "vivo_subject_01"
        assert 'name = "vivo_subject_01"' in (
            project / "Cargo.toml"
        ).read_text(encoding="utf-8")
        assert (project / "Cargo.lock").read_text() == "# synthetic lock\n"
        fixed = (project / "src/oracle/fixed_test.rs").read_text()
        assert "__codeweaver_fixed_test_dispatch" in fixed
        assert '"test_private" => test_private()' in fixed
    finally:
        shutil.rmtree(scratch)


def test_evaluator_rejects_candidate_symlinks(tmp_path):
    contract = _synthetic_contract(tmp_path)
    target = tmp_path / "target"
    source = tmp_path / "outside.rs"
    _write(source, "pub fn sample() {}\n")
    (target / "src/production").mkdir(parents=True)
    try:
        (target / "src/production/sample.rs").symlink_to(source)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    with pytest.raises(ValueError, match="symbolic links"):
        materialize_evaluation_copy(target, contract)


def test_safe_rate_counts_only_unsafe_code_scopes(tmp_path):
    path = tmp_path / "sample.rs"
    _write(
        path,
        """
// unsafe { comment only }
pub fn safe() {
    let text = "unsafe { string only }";
}
pub unsafe extern "C" fn dangerous() {
    let value = 1;
}
pub fn adapter() {
    unsafe {
        dangerous();
    }
}
""",
    )
    value = unsafe_line_metrics([path])
    assert value["total_lines"] > value["unsafe_lines"] > 0
    assert value["unsafe_functions"] == 1
    assert value["unsafe_blocks"] == 1
    assert 0 < value["safe_rate_percent"] < 100


def _evaluation_fixture() -> tuple[dict, dict]:
    config = load_config()
    rows = []
    integrations = []
    for repetition in range(3):
        for subject in config["subjects"]:
            total_lines = 100 * len(subject["modules"])
            rows.append(
                {
                    "subject_id": subject["id"],
                    "subject": subject["name"],
                    "modules": subject["modules"],
                    "module_count": len(subject["modules"]),
                    "test_count": len(subject["test_functions"]),
                    "repetition": repetition,
                    "pipeline_status": "completed",
                    "terminal_run": C.measurement(C.MEASURED, True),
                    "contract_integrity": C.measurement(C.MEASURED, True),
                    "compilation": C.measurement(C.MEASURED, True),
                    "fixed_contract_tests": C.measurement(C.MEASURED, True),
                    "fixed_tests": {
                        "expected": len(subject["test_functions"]),
                        "executed": len(subject["test_functions"]),
                        "passed": len(subject["test_functions"]),
                        "failed": 0,
                        "not_executed": 0,
                    },
                    "fixed_test_results": [
                        {
                            "name": name,
                            "passed": True,
                            "returncode": 0,
                            "timed_out": False,
                        }
                        for name in subject["test_functions"]
                    ],
                    "safety": C.measurement(
                        C.MEASURED,
                        {
                            "total_lines": total_lines,
                            "safe_lines": 90 * len(subject["modules"]),
                            "unsafe_lines": 10 * len(subject["modules"]),
                            "safe_rate_percent": 90.0,
                        },
                    ),
                    "elapsed_seconds": C.measurement(C.MEASURED, 10.0),
                    "output_tokens": C.measurement(C.MEASURED, 100),
                    "nano_aiu": C.measurement(C.MEASURED, 200),
                    "premium_requests": C.measurement(C.MEASURED, 1),
                }
            )
        integrations.append(
            {
                "repetition": repetition,
                "module_denominator": 19,
                "accepted_module_count": 19,
                "accepted_modules": [],
                "incremental_compilation_percent": 100.0,
                "steps": [],
            }
        )
    return config, {
        "schema_version": 1,
        "protocol": {**config["protocol"], "evaluated_repetitions": 3},
        "rows": rows,
        "integration": integrations,
        "provenance": {"test": True},
    }


def test_report_aggregates_three_repetitions_and_writes_tables(
    tmp_path, monkeypatch
):
    config, evaluation = _evaluation_fixture()
    aggregate = aggregate_results(evaluation)
    assert aggregate["runs_observed"] == 45
    assert aggregate["distributions"]["fill_compilation_percent"]["mean"] == 100
    assert aggregate["distributions"]["test_rate_percent"]["mean"] == 100
    assert aggregate["distributions"]["safe_rate_percent"]["mean"] == 90

    def fake_report(_title, _sections, path):
        path.write_bytes(b"%PDF-test\n")
        return True

    def fake_figure(_config_or_aggregate, _aggregate_or_path, path=None):
        destination = path or _aggregate_or_path
        destination.write_bytes(b"%PDF-test\n")
        return True

    monkeypatch.setattr(
        "experiments.evoc2rust.report.RD.render_pdf_report", fake_report
    )
    monkeypatch.setattr(
        "experiments.evoc2rust.report.render_summary_figure", fake_figure
    )
    monkeypatch.setattr(
        "experiments.evoc2rust.report.render_repetition_figure",
        lambda _aggregate, path: (path.write_bytes(b"%PDF-test\n") or True),
    )
    manifest = write_reports(
        config=config, evaluation=evaluation, output_dir=tmp_path
    )
    assert manifest["pdf_status"] == C.MEASURED
    assert sum(1 for _ in csv_rows(tmp_path / "table4_extended.csv")) == 24
    assert sum(1 for _ in csv_rows(tmp_path / "table5_extended.csv")) == 20
    assert "113 Vivo-Bench" in (tmp_path / "comparison.md").read_text()


def test_report_latex_tables_declare_their_exact_column_counts():
    config, evaluation = _evaluation_fixture()
    aggregate = aggregate_results(evaluation)
    repetitions = aggregate["repetitions"]
    latex = render_latex(
        config,
        aggregate,
        table4_rows(config, repetitions, aggregate),
        table5_rows(config, repetitions, aggregate),
    )
    assert r"\begin{tabular}{llrrr}" in latex
    assert r"\begin{tabular}{llrr}" in latex
    assert r"\begin{tabular}{rrrrr}" in latex


def csv_rows(path: Path):
    import csv

    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def test_package_completeness_gate_checks_all_45_terminal_runs(tmp_path):
    config, evaluation = _evaluation_fixture()
    runs = tmp_path / "runs"
    for row in evaluation["rows"]:
        run = (
            runs
            / "full"
            / str(row["subject_id"])
            / f"rep{row['repetition']}"
        )
        run.mkdir(parents=True)
        _write(
            run / "recodeagent_run_state.json",
            json.dumps(
                {
                    "status": "completed",
                    "provenance": {
                        "git_sha": {"value": "abc123"},
                        "copilot_cli_version": {"value": "test"},
                    },
                }
            ),
        )
    evaluation_root = tmp_path / "evaluation"
    report_root = tmp_path / "report"
    evaluation_root.mkdir()
    report_root.mkdir()
    C.atomic_write_json(evaluation_root / "evaluation.json", evaluation)
    for name in REQUIRED_EVALUATION_FILES - {"evaluation.json"}:
        count = 45 if name == "evaluation.csv" else 3
        _write(
            evaluation_root / name,
            "value\n" + "".join(f"{index}\n" for index in range(count)),
        )
    counts = {
        "module_results.csv": 45,
        "repetition_metrics.csv": 3,
        "integration_steps.csv": 45,
        "table4_extended.csv": 24,
        "table5_extended.csv": 20,
        "table6_reference.csv": 5,
        "availability.csv": 7,
    }
    for name in REQUIRED_REPORT_FILES:
        if name.endswith(".pdf"):
            (report_root / name).write_bytes(b"%PDF-test\n")
        elif name in counts:
            _write(
                report_root / name,
                "value\n"
                + "".join(f"{index}\n" for index in range(counts[name])),
            )
        else:
            _write(report_root / name, "{}\n")
    prepared = {
        "counts_match_expected": True,
        "counts": {"groups": 15, "modules": 19, "tests": 125},
        "calibration": {
            "original_c": {"ctest_passed": True, "ctest_total": 17},
            "active_test_arrays": {
                "verified": True,
                "active_test_count": 125,
            },
            "translated_rust_contracts": {
                "all_contracts_calibrated": True,
                "expected_tests": 125,
                "original_c_tests_passed": 125,
                "c2rust_diagnostic_tests_passed": 125,
                "stripped_scaffold_tests_passed": 0,
                "ground_truth_retained": False,
            },
        },
    }
    report_manifest = {
        "pdf_status": C.MEASURED,
        "summary_figure_pdf_status": C.MEASURED,
        "repetitions_figure_pdf_status": C.MEASURED,
    }
    complete = validate_completeness(
        evaluation=evaluation,
        prepared_manifest=prepared,
        report_manifest=report_manifest,
        evaluation_root=evaluation_root,
        report_root=report_root,
        runs_root=runs,
    )
    assert complete["complete"] is True
    state = runs / "full/4/rep2/recodeagent_run_state.json"
    _write(state, '{"status": "running"}\n')
    incomplete = validate_completeness(
        evaluation=evaluation,
        prepared_manifest=prepared,
        report_manifest=report_manifest,
        evaluation_root=evaluation_root,
        report_root=report_root,
        runs_root=runs,
    )
    assert incomplete["complete"] is False
    assert incomplete["terminal_runs"] == 44
