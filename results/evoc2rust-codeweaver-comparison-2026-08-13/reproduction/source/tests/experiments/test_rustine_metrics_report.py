from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from experiments.rustine import common as C
from experiments.rustine import evaluate as rustine_evaluate
from experiments.rustine.config import load_subject_config
from experiments.rustine.evaluate import (
    evaluate_workspace,
    load_execution_overrides,
    run_workspace_stage,
)
from experiments.rustine.evaluator import (
    parse_llvm_cov_json,
    parse_newmetrics_output,
    production_module_paths,
)
from experiments.rustine.report import (
    _mcnemar_exact,
    _wilson_interval,
    aggregate_results,
    write_reports,
)


def test_metric_parsers_select_structured_production_values():
    newmetrics = """\
Pointer arithmetic: 7
Unsafe lines: 4
Unsafe calls: 5
Unsafe casts: 6
Total spans: 100
Unsafe ratio: 0.04
Raw pointer dereferences: 3
Raw pointer declarations: 2
"""
    assert parse_newmetrics_output(newmetrics) == [
        {
            "unsafe_lines": 4,
            "unsafe_calls": 5,
            "unsafe_type_casts": 6,
            "raw_pointer_dereferences": 3,
            "raw_pointer_declarations": 2,
            "pointer_arithmetic": 7,
        }
    ]
    llvm = {
        "data": [
            {
                "files": [
                    {
                        "filename": "/work/src/lib.rs",
                        "summary": {
                            "functions": {"count": 4, "covered": 3},
                            "lines": {"count": 20, "covered": 10},
                        },
                    },
                    {
                        "filename": "/work/src/test.rs",
                        "summary": {
                            "functions": {"count": 100, "covered": 100},
                            "lines": {"count": 100, "covered": 100},
                        },
                    },
                ]
            }
        ]
    }
    parsed = parse_llvm_cov_json(json.dumps(llvm), {"src/lib.rs"})
    assert parsed["function_percent"] == 75.0
    assert parsed["line_percent"] == 50.0


def test_production_paths_include_bins_and_path_qualified_modules(tmp_path):
    project = tmp_path / "project"
    (project / "src" / "nested").mkdir(parents=True)
    (project / "src" / "lib.rs").write_text(
        '#[path = "nested/engine.rs"]\npub(crate) mod engine;\n',
        encoding="utf-8",
    )
    (project / "src" / "nested" / "engine.rs").write_text("", encoding="utf-8")
    (project / "src" / "main.rs").write_text("", encoding="utf-8")
    (project / "src" / "test_main.rs").write_text("", encoding="utf-8")
    lock = {
        "files": ["src/test_main.rs"],
        "cargo": {
            "bins": [
                {"name": "app", "path": "src/main.rs"},
                {"name": "test", "path": "src/test_main.rs"},
            ]
        },
    }
    assert production_module_paths(project, lock) == {
        "src/lib.rs",
        "src/nested/engine.rs",
        "src/main.rs",
    }


def test_parallel_evaluation_preserves_subject_order(tmp_path, monkeypatch):
    config = load_subject_config()
    manifest = {
        "projects": [
            {"subject_id": subject_id} for subject_id in range(1, 24)
        ],
        "protocol": {"repetitions": 1},
    }

    executions = {}

    def fake_evaluate(subject, _manifest_row, **kwargs):
        executions[subject["id"]] = kwargs["contract_executions"]
        return {
            "subject_id": subject["id"],
            "workspace": str(kwargs["workspace"]),
        }

    monkeypatch.setattr(rustine_evaluate, "evaluate_workspace", fake_evaluate)
    overrides = load_execution_overrides()
    result = rustine_evaluate.evaluate_runs(
        config=config,
        manifest=manifest,
        runs_root=tmp_path,
        repetitions=1,
        max_workers=4,
        execution_overrides=overrides,
    )
    assert [row["subject_id"] for row in result["rows"]] == list(range(1, 24))
    assert executions[6] == [{"target": "grabc", "args": ["-v"], "stdin": None}]
    assert result["execution_overrides"] == overrides


def test_runtime_execution_overlay_preserves_legacy_contract(tmp_path, monkeypatch):
    workspace = tmp_path / "run"
    contract_dir = workspace / "oracle"
    contract_dir.mkdir(parents=True)
    contract_path = contract_dir / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "executions": [
                    {"target": "test_grabc", "args": ["-v"], "stdin": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    target = workspace / "pipeline" / "target"
    target.mkdir(parents=True)
    expected = [{"target": "grabc", "args": ["-v"], "stdin": None}]
    observed = []

    def fake_evaluate_stage(stage, *, target, contract_dir, timeout):
        observed.append(json.loads((contract_dir / "contract.json").read_text()))
        return {"stage": stage, "target": str(target), "timeout": timeout}

    monkeypatch.setattr(
        rustine_evaluate,
        "_load_workspace_evaluator",
        lambda _path: SimpleNamespace(evaluate_stage=fake_evaluate_stage),
    )
    result = run_workspace_stage(
        "test",
        workspace=workspace,
        target=target,
        contract_dir=contract_dir,
        timeout=7,
        contract_executions=expected,
        contract_execution_override=True,
    )

    assert result["stage"] == "test"
    assert observed[0]["executions"] == expected
    assert json.loads(contract_path.read_text(encoding="utf-8"))["executions"] == [
        {"target": "test_grabc", "args": ["-v"], "stdin": None}
    ]


def test_binary_statistics_are_exact_and_bounded():
    assert _mcnemar_exact(5, 0) == 0.0625
    assert _mcnemar_exact(0, 0) is None
    lower, upper = _wilson_interval(23, 23)
    assert round(lower, 1) == 85.7
    assert upper == 100.0


def _minimal_integrity_workspace(tmp_path: Path) -> tuple[Path, dict]:
    workspace = tmp_path / "run"
    oracle = workspace / "oracle"
    oracle.mkdir(parents=True)
    (oracle / "contract.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "subject_id": 8,
                "kind": "none",
                "files": [],
                "assets": [],
                "targets": [],
                "file_sha256": {},
                "cargo": {"package": {}, "dependencies": {}, "build_dependencies": {}, "bins": []},
                "modules": [],
            }
        ),
        encoding="utf-8",
    )
    evaluator_source = (
        Path(__file__).resolve().parents[2] / "experiments" / "rustine" / "evaluator.py"
    )
    shutil.copy2(evaluator_source, workspace / "immutable_evaluator.py")
    (workspace / "pipeline" / "target").mkdir(parents=True)
    (workspace / "pipeline" / "target" / "Cargo.toml").write_text(
        '[package]\nname="x"\nversion="0.1.0"\nedition="2021"\n',
        encoding="utf-8",
    )
    (workspace / "recodeagent_run_state.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "started_at": "2026-01-01T00:00:00+00:00",
                "ended_at": "2026-01-01T00:00:05+00:00",
            }
        ),
        encoding="utf-8",
    )
    manifest_row = {
        "contract_sha256": C.tree_sha256(oracle),
        "evaluator_sha256": C.file_sha256(workspace / "immutable_evaluator.py"),
    }
    return workspace, manifest_row


def test_unavailable_measurements_never_collapse_to_zero_or_success(tmp_path):
    workspace, manifest_row = _minimal_integrity_workspace(tmp_path)
    subject = load_subject_config()["subjects"][7]

    def fake_stage(stage, **_kwargs):
        if stage == "build":
            return {"measurement": C.measurement(C.MEASURED, True), "commands": []}
        if stage == "test":
            return {
                "measurement": C.measurement(C.NOT_APPLICABLE, reason="no tests"),
                "assertions": {
                    key: C.measurement(C.NOT_APPLICABLE, reason="no tests")
                    for key in ("executed", "passed", "failed")
                },
                "commands": [],
            }
        if stage == "coverage":
            return {
                "measurement": C.measurement(C.NOT_APPLICABLE, reason="no tests"),
                "commands": [],
            }
        return {
            "measurement": C.measurement(C.UNAVAILABLE, reason="tool absent"),
            "pointer_arithmetic": C.measurement(C.MEASURED, 7, "heuristic"),
            "commands": [],
        }

    row = evaluate_workspace(
        subject,
        manifest_row,
        workspace=workspace,
        variant="full",
        repetition=0,
        timeout=1,
        stage_runner=fake_stage,
    )
    assert row["fixed_contract_tests"]["status"] == C.NOT_APPLICABLE
    assert row["function_coverage_percent"]["value"] is None
    assert row["safety"]["pointer_arithmetic"]["value"] == 7
    assert row["safety"]["unsafe_lines"] == {
        "status": C.UNAVAILABLE,
        "value": None,
        "reason": "tool absent",
    }
    assert row["input_tokens"]["status"] == C.MISSING
    assert row["nano_aiu"]["status"] == C.MISSING
    assert row["premium_requests"]["status"] == C.MISSING


def _measured_qsort_row(config):
    subject = config["subjects"][0]
    return {
        "subject_id": 1,
        "subject": "qsort",
        "artifact_dir": "qsort",
        "loc": 27,
        "variant": "full",
        "repetition": 0,
        "paper_validation": subject["paper_validation"],
        "paper_safety": subject["paper_safety"],
        "run_completion": C.measurement(C.MEASURED, True),
        "contract_integrity": C.measurement(C.MEASURED, True),
        "compilation": C.measurement(C.MEASURED, True),
        "fixed_contract_tests": C.measurement(C.MEASURED, True),
        "function_coverage_percent": C.measurement(C.UNAVAILABLE, reason="tool absent"),
        "line_coverage_percent": C.measurement(C.UNAVAILABLE, reason="tool absent"),
        "assertions": {
            "executed": C.measurement(C.MEASURED, 21),
            "passed": C.measurement(C.MEASURED, 21),
            "failed": C.measurement(C.MEASURED, 0),
        },
        "safety": {
            field: C.measurement(C.UNAVAILABLE, reason="tool absent")
            for field in (
                "pointer_arithmetic",
                "raw_pointer_declarations",
                "raw_pointer_dereferences",
                "unsafe_lines",
                "unsafe_type_casts",
                "unsafe_calls",
            )
        },
    }


def test_aggregate_and_reports_keep_reference_and_measured_status_separate(
    tmp_path, monkeypatch
):
    config = load_subject_config()
    evaluation = {
        "rows": [_measured_qsort_row(config)],
        "protocol": config["protocol"],
        "provenance": {"test": True},
    }
    aggregate = aggregate_results(config, evaluation)
    assert aggregate["paper"]["assertions"]["executed"] == 1_221_192
    assert aggregate["paper"]["benchmark_test_function_coverage_percent"] == 74.7
    assert round(
        aggregate["paper"]["unweighted_subject_mean_function_coverage_percent"], 1
    ) == 68.4
    assert aggregate["codeweaver"]["compiled"] == 1
    assert aggregate["codeweaver"]["mean_function_coverage_percent"] is None
    assert aggregate["codeweaver"]["safety"]["unsafe_lines"]["sum"] is None

    monkeypatch.setattr(
        "experiments.recodeagent.render.render_pdf_report",
        lambda _title, _sections, path: False,
    )
    manifest = write_reports(config=config, evaluation=evaluation, output_dir=tmp_path)
    markdown = (tmp_path / "comparison.md").read_text(encoding="utf-8")
    assert "118-project ReCodeAgent matrix" in markdown
    assert "not directly comparable" in markdown
    assert "arxiv.org/abs/2511.20617" in markdown
    assert (tmp_path / "validation.csv").exists()
    assert (tmp_path / "safety.csv").exists()
    assert (tmp_path / "statistics.csv").exists()
    assert (tmp_path / "comparison.tex").exists()
    assert manifest["pdf_status"] == C.UNAVAILABLE
