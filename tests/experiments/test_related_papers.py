from __future__ import annotations

import copy
import json
import sys
import tarfile
from pathlib import Path

import pytest

from experiments.related_papers import config
from experiments.related_papers import actor_li
from experiments.related_papers import citation_catalog
from experiments.related_papers import citation_report
from experiments.related_papers import citer_reference_data
from experiments.related_papers import report
from experiments.related_papers.analysis import _diagnostics
from experiments.related_papers.common import run_command
from experiments.related_papers.package import (
    PAPER_RESULT_KEYS,
    _archive,
    _archive_valid,
    _related_run_file,
)
from experiments.related_papers.evaluate import (
    _parse_cargo_tests,
    _parse_surefire,
    _replace_stub,
    evaluate_repotransbench_run,
    extract_rust_function,
)
from experiments.related_papers.prepare import (
    _assert_target_absent,
    _replace_function_with_stub,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_frozen_protocol_and_subject_locks_reject_drift(monkeypatch):
    assert set(PAPER_RESULT_KEYS) == {
        "crust",
        "alphatrans",
        "sactor",
        "repotransbench",
        "rustrepotrans",
    }
    assert len(config.REPOTRANSBENCH_SUBJECTS) == 3
    assert sum(row["tests"] for row in config.REPOTRANSBENCH_SUBJECTS) == 37
    assert {row["source_language"] for row in config.RUSTREPOTRANS_SUBJECTS} == {
        "C",
        "Java",
        "Python",
    }
    drifted = copy.deepcopy(config.PROTOCOL)
    drifted["repetitions"] = 1
    monkeypatch.setattr(config, "PROTOCOL", drifted)
    with pytest.raises(ValueError, match="protocol drifted"):
        config.validate_config()


def test_citation_census_orbit_and_surface_locks():
    citation_catalog.validate_citation_catalog()
    assert len(citation_catalog.CITATION_RECORDS) == 30
    assert len(citation_catalog.INCLUSION_MATRIX) == 20
    assert len(citation_catalog.ORBIT_SUBJECTS) == 24
    assert sum(row["orbit_ext_test"] for row in citation_catalog.ORBIT_SUBJECTS) == 22
    assert {
        row["key"] for row in citation_catalog.CITER_SURFACES
    } == {row["key"] for row in citation_catalog.INCLUSION_MATRIX}
    citer_reference_data.validate_citer_reference_data()
    assert len(citer_reference_data.CITER_REFERENCE_TABLES) == 14


def test_orbit_exact_slice_keeps_three_independent_repetitions():
    orbit_ids = {row["project_id"] for row in citation_catalog.ORBIT_SUBJECTS}
    other_ids = [f"crust__other-{index}" for index in range(76)]
    rows = []
    for project_id in sorted(orbit_ids) + other_ids:
        for repetition in range(3):
            rows.append(
                {
                    "variant": "full",
                    "tool": "crust",
                    "project_id": project_id,
                    "repetition": str(repetition),
                    "build": "True",
                    "project_pass_all": str(repetition != 1),
                    "validated_tests_passed": "3",
                    "validated_tests_expected_paper": "2",
                }
            )
    subjects, summaries = citation_report._orbit_rows(rows)
    assert len(subjects) == 24
    assert len(summaries) == 5
    assert [row["test_successes"] for row in summaries[2:]] == [24, 0, 24]
    assert all(row["fixed_tests_passed"] == 48 for row in summaries[2:])
    assert all(row["codeweaver_pass_all_repetitions"] == 2 for row in subjects)


def test_actor_public_overlap_is_separate_from_unresolved_paper_87():
    missing = citation_catalog.ACTOR_PUBLIC_MISSING_PROJECT_IDS
    actor_ids = {f"crust__project-{index}" for index in range(95)}
    all_ids = actor_ids | missing
    rows = []
    for project_id in sorted(all_ids):
        for repetition in range(3):
            rows.append(
                {
                    "variant": "full",
                    "tool": "crust",
                    "project_id": project_id,
                    "repetition": str(repetition),
                    "build": "True",
                    "project_pass_all": str(repetition == 0),
                    "validated_tests_passed": "3",
                    "validated_tests_expected_paper": "2",
                }
            )
    projects, summaries = citation_report._actor_public_95_rows(rows)
    assert len(projects) == 95
    assert len(summaries) == 3
    assert all(row["paper_projects"] == 87 for row in summaries)
    assert all(row["public_artifact_projects"] == 95 for row in summaries)
    assert [row["test_successes"] for row in summaries] == [95, 0, 0]
    assert all(row["fixed_tests_passed"] == 190 for row in summaries)
    assert not missing & {row["project_id"] for row in projects}


def test_actor_li_subject_locks_parser_and_leakage_safe_preparation(
    tmp_path, monkeypatch
):
    artifact = tmp_path / "actor"
    _write(artifact / "LICENSE", "MIT\n")
    for subject in actor_li.SUBJECTS:
        name = subject["name"]
        visible = artifact / "projects_input" / name
        validation = artifact / "validation_tests" / name
        for root in (visible, validation):
            _write(root / f"{name}.c", "int main(void) { return 0; }\n")
            _write(root / "Makefile", "all:\n\t@true\n")
            _write(root / "norm_rules.jsonl", '{"pattern":"x","replacement":"x"}\n')
            _write(root / "testcmp.sh", "#!/bin/bash\r\nexit 0\r\n")
        _write(
            visible / "tests00.jsonl",
            "".join('{"name":"seed"}\n' for _ in range(subject["visible_tests"])),
        )
        _write(
            validation / "tests00.jsonl",
            "".join(
                '{"name":"hidden"}\n'
                for _ in range(subject["validation_tests"])
            ),
        )
    monkeypatch.setattr(actor_li, "_verify_clean_artifact", lambda *_args: None)
    workspace_root = tmp_path / "workspaces"
    manifest = actor_li.prepare_campaign(
        artifact_root=artifact,
        workspace_root=workspace_root,
    )
    assert len(manifest["projects"]) == 6
    assert sum(row["validation_tests"] for row in manifest["projects"]) == 492
    assert len(actor_li.MACRO_SUBJECTS) == 57
    for row in manifest["projects"]:
        workspace = workspace_root / row["id"]
        prepared = json.loads((workspace / "prepared.json").read_text())
        assert prepared["validation_contract_excluded"] is True
        assert not list(workspace.rglob("tests01.jsonl"))
        script = (
            workspace / "scaffold" / "seed_oracle" / "testcmp.sh"
        ).read_bytes()
        assert b"\r\n" not in script
    assert actor_li._parse_test_output(
        "Loaded 70 tests total\nResults: 69 passed, 1 failed out of 70 tests\n"
    ) == {"loaded": 70, "passed": 69, "failed": 1, "total": 70}


def test_telemetry_and_clippy_json_are_derived_without_fabricated_inputs():
    telemetry = report._telemetry_summaries(
        [
            {
                "repetition": "0",
                "elapsed_seconds": "120",
                "total_output_tokens": "1000",
                "total_nano_aiu": "2000000000",
                "total_assistant_turns": "3",
                "total_tool_invocations": "4",
                "total_premium_requests": "1",
            },
            {
                "repetition": "0",
                "elapsed_seconds": "180",
                "total_output_tokens": "2000",
                "total_nano_aiu": "3000000000",
                "total_assistant_turns": "5",
                "total_tool_invocations": "6",
                "total_premium_requests": "1",
            },
        ]
    )
    assert telemetry[-1]["elapsed_hours"] == pytest.approx(1 / 12)
    assert telemetry[-1]["output_tokens"] == 3000
    assert telemetry[-1]["output_token_status"] == "measured"
    assert telemetry[-1]["aiu"] == 5
    assert telemetry[-1]["input_tokens"] is None
    assert telemetry[-1]["input_token_status"] == "unavailable"

    event = {
        "reason": "compiler-message",
        "message": {
            "level": "warning",
            "message": "use is_empty",
            "code": {"code": "clippy::len_zero"},
            "spans": [
                {
                    "is_primary": True,
                    "file_name": "src/lib.rs",
                    "line_start": 7,
                }
            ],
        },
    }
    output = "\n".join([str(event), json.dumps(event), json.dumps(event)])
    diagnostics = _diagnostics(output)
    assert diagnostics == [
        {
            "level": "warning",
            "code": "clippy::len_zero",
            "message": "use is_empty",
            "file": "src/lib.rs",
            "line": 7,
        }
    ]


def test_actor_li_candidate_copy_rejects_links_native_code_and_delegation(
    tmp_path,
):
    run = tmp_path / "run"
    candidate = run / "pipeline" / "target"
    _write(candidate / "Cargo.toml", "[package]\nname='candidate'\nversion='0.1.0'\n")
    _write(candidate / "src" / "main.rs", "fn main() {}\n")
    _write(candidate / ".cargo" / "config.toml", "[build]\ntarget-dir='.'\n")
    _write(candidate / "seed_oracle" / "subject.c", "int main(void) { return 0; }\n")
    _write(candidate / "target" / "release" / "subject", "binary\n")
    (candidate / "release").symlink_to("target/release", target_is_directory=True)
    actor_li._validate_candidate_root(candidate, run)
    copied = tmp_path / "copied"
    actor_li._copy_candidate_payload(candidate, copied)
    assert (copied / "src" / "main.rs").is_file()
    assert not (copied / "seed_oracle").exists()
    assert not (copied / "target").exists()
    assert not (copied / "release").exists()
    assert not (copied / ".cargo").exists()

    _write(
        candidate / "tests" / "cli.rs",
        "fn test_cli() { std::process::Command::new(\"candidate\").status(); }\n",
    )
    assert actor_li._rust_source_metrics(candidate)[2] == 0
    _write(
        candidate / "src" / "main.rs",
        "fn main() { std::process::Command::new(\"subject\").status(); }\n",
    )
    assert actor_li._rust_source_metrics(candidate)[2] > 0
    _write(candidate / "native.c", "int main(void) { return 0; }\n")
    with pytest.raises(ValueError, match="native artifact"):
        actor_li._validate_candidate_root(candidate, run)

    linked_root = run / "linked"
    linked_root.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="root symlink"):
        actor_li._validate_candidate_root(linked_root, run)


def test_actor_li_campaign_seal_requires_terminal_immutable_matrix(tmp_path):
    runs = tmp_path / "runs"
    for subject in actor_li.SUBJECTS:
        for repetition in range(3):
            _write(
                runs
                / "full"
                / actor_li._subject_id(subject["name"])
                / f"rep{repetition}"
                / "recodeagent_run_state.json",
                '{"status":"completed"}\n',
            )
    output = tmp_path / "evaluation"
    seal = actor_li._seal_terminal_matrix(
        runs_root=runs,
        output_root=output,
        repetitions=3,
    )
    assert seal["cell_count"] == 18
    state = (
        runs
        / "full"
        / actor_li._subject_id("csplit")
        / "rep0"
        / "recodeagent_run_state.json"
    )
    _write(state, '{"status":"failed"}\n')
    with pytest.raises(RuntimeError, match="changed after"):
        actor_li._seal_terminal_matrix(
            runs_root=runs,
            output_root=output,
            repetitions=3,
        )


def _synthetic_actor_li_evaluation(root: Path) -> None:
    raw_rows = []
    qualification_rows = []
    control_rows = []
    manifest_rows = []
    seal_rows = []
    aggregate_rows = []
    for subject, expected in citation_report.ACTOR_LI_DENOMINATORS.items():
        contract = root / "oracle-contracts" / subject / "tests00.jsonl"
        _write(contract, '{"name":"fixed"}\n')
        tree_hash = citation_report._tree_sha256(contract.parent)
        manifest_rows.append(
            {
                "subject": subject,
                "relative_path": f"{subject}/tests00.jsonl",
                "bytes": contract.stat().st_size,
                "sha256": citation_report.C.sha256_file(contract),
                "artifact_tree_sha256": tree_hash,
            }
        )
        qualification_rows.append(
            {
                "subject": subject,
                "expected_tests": expected,
                "loaded": expected,
                "passed": expected,
                "failed": 0,
                "total": expected,
                "qualified": True,
                "candidate_runtime_isolated": True,
            }
        )
        control_rows.append(
            {
                "subject": subject,
                "expected_tests": expected,
                "loaded": expected,
                "passed": 0,
                "failed": expected,
                "total": expected,
                "discriminating": True,
                "candidate_runtime_isolated": True,
            }
        )
        aggregate_rows.append(
            {
                "subject": subject,
                "cells": 3,
                "measured_cells": 3,
                "build_cells": 0,
                "pass_all_cells": 0,
                "safe_cells": 0,
                "self_contained_cells": 0,
                "safe_pass_all_cells": 0,
                "tests_passed": 0,
                "tests_expected": expected * 3,
                "test_rate_percent": 0.0,
                **{
                    field: value
                    for metric in (
                        "elapsed_seconds",
                        "output_tokens",
                        "nano_aiu",
                        "premium_requests",
                    )
                    for field, value in (
                        (metric, ""),
                        (f"{metric}_status", "unavailable"),
                        (f"{metric}_measured_cells", 0),
                    )
                },
            }
        )
        for repetition in range(3):
            raw_rows.append(
                {
                    "subject_id": f"actor-li__{subject}",
                    "subject": subject,
                    "repetition": repetition,
                    "run_status": "failed",
                    "evaluation_status": "measured",
                    "candidate_status": "missing_candidate",
                    "expected_tests": expected,
                    "tests_loaded": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "tests_not_executed": expected,
                    "build": False,
                    "pass_all": False,
                    "safe_rust": False,
                    "self_contained": False,
                    "safe_pass_all": False,
                    "unsafe_tokens": 0,
                    "delegation_tokens": 0,
                    "rust_source_files": 0,
                    "contract_integrity": True,
                    "candidate_runtime_isolated": False,
                }
            )
            seal_rows.append(
                {
                    "subject_id": f"actor-li__{subject}",
                    "repetition": repetition,
                    "status": "failed",
                    "state_sha256": "a" * 64,
                }
            )
    citation_report._write_csv(root / "raw_runs.csv", raw_rows)
    _write(
        root / "raw_runs.jsonl",
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in raw_rows),
    )
    all_aggregate = {
        "subject": "ALL",
        "cells": 18,
        "measured_cells": 18,
        "build_cells": 0,
        "pass_all_cells": 0,
        "safe_cells": 0,
        "self_contained_cells": 0,
        "safe_pass_all_cells": 0,
        "tests_passed": 0,
        "tests_expected": 1476,
        "test_rate_percent": 0.0,
        **{
            field: value
            for metric in (
                "elapsed_seconds",
                "output_tokens",
                "nano_aiu",
                "premium_requests",
            )
            for field, value in (
                (metric, ""),
                (f"{metric}_status", "unavailable"),
                (f"{metric}_measured_cells", 0),
            )
        },
    }
    aggregate_rows.append(all_aggregate)
    citation_report._write_csv(root / "aggregate.csv", aggregate_rows)
    citation_report._write_csv(
        root / "oracle-qualification" / "qualification.csv",
        qualification_rows,
    )
    citation_report.C.atomic_write_json(
        root / "oracle-qualification" / "summary.json",
        {
            "status": "passed",
            "subjects": 6,
            "expected_tests": 492,
            "passed_tests": 492,
        },
    )
    citation_report._write_csv(root / "negative_controls.csv", control_rows)
    citation_report._write_csv(
        root / "oracle_contract_manifest.csv",
        manifest_rows,
    )
    citation_report.C.atomic_write_json(
        root / "campaign-seal.json",
        {"cell_count": 18, "cells": seal_rows},
    )
    citation_report.C.atomic_write_json(
        root / "macro_experiment_status.json",
        {
            "status": "blocked_reference_only",
            "subject_count": 57,
            "subjects": list(actor_li.MACRO_SUBJECTS),
        },
    )
    citation_report.C.atomic_write_json(
        root / "summary.json",
        {
            "rows": 18,
            "expected_rows": 18,
            "measured": 18,
            "build_passed": 0,
            "pass_all": 0,
            "safe_rust": 0,
            "self_contained": 0,
            "safe_pass_all": 0,
            "tests_passed": 0,
            "tests_expected": 1476,
            "oracle_qualification": "passed",
            "negative_control_subjects": 6,
            "negative_control_discriminating_subjects": 6,
            "negative_control_tests_passed": 0,
            "negative_control_tests_expected": 492,
            "published_oracle_contract_files": 6,
            "published_oracle_contract_subjects": 6,
            "sealed_cells": 18,
            "candidate_runtime_isolation": (
                "mount-pid-namespace-chroot-no-capabilities"
            ),
            "complete": True,
            "aggregate": all_aggregate,
        },
    )


def test_actor_li_publication_recomputes_evidence_and_rejects_tampering(
    tmp_path,
):
    evaluation = tmp_path / "evaluation"
    _synthetic_actor_li_evaluation(evaluation)
    summary, aggregates = citation_report._validate_actor_li_evaluation(
        evaluation
    )
    assert summary["complete"] is True
    assert len(aggregates) == 7
    contract = evaluation / "oracle-contracts" / "expr" / "tests00.jsonl"
    _write(contract, '{"name":"tampered"}\n')
    with pytest.raises(ValueError, match="hash mismatch"):
        citation_report._validate_actor_li_evaluation(evaluation)


def test_golden_rust_body_is_replaced_and_leakage_is_rejected(tmp_path):
    target = """\
impl Big {
    pub fn set(&mut self, value: isize) {
        self.w[0] = value as Chunk;
    }
}
"""
    path = tmp_path / "workspace" / "scaffold" / "src" / "big.rs"
    _write(path, target)
    golden = """\
pub fn set(&mut self, value: isize) {
        self.w[0] = value as Chunk;
    }"""
    _replace_function_with_stub(
        path,
        golden,
        "pub fn set(&mut self, value: isize)",
    )
    replaced = path.read_text(encoding="utf-8")
    assert "RustRepoTrans translation required" in replaced
    assert "self.w[0] = value as Chunk" not in replaced
    _assert_target_absent(tmp_path / "workspace", golden)

    _write(tmp_path / "workspace" / "source" / "leak.txt", golden)
    with pytest.raises(ValueError, match="golden target leaked"):
        _assert_target_absent(tmp_path / "workspace", golden)


def test_rust_function_extraction_and_pristine_stub_replacement(tmp_path):
    candidate = r'''
impl Big {
    pub fn set(&mut self, value: isize) {
        let literal = "a } brace";
        /* nested { comment } */
        if value > 0 {
            self.w[0] = value as Chunk;
        }
    }
}
'''
    signature = "pub fn set(&mut self, value: isize)"
    extracted = extract_rust_function(candidate, signature)
    assert extracted.startswith("pub fn set")
    assert extracted.endswith("}")
    assert "self.w[0]" in extracted

    path = tmp_path / "src" / "big.rs"
    _write(
        path,
        """\
impl Big {
    pub fn set(&mut self, value: isize) {
        panic!("RustRepoTrans translation required")
    }
}
""",
    )
    _replace_stub(path, signature, extracted)
    content = path.read_text(encoding="utf-8")
    assert "RustRepoTrans translation required" not in content
    assert "self.w[0]" in content


def test_java_and_rust_test_output_parsers(tmp_path):
    _write(
        tmp_path / "target" / "surefire-reports" / "TEST-a.xml",
        '<testsuite tests="7" failures="1" errors="1" skipped="1"/>',
    )
    java = _parse_surefire(tmp_path)
    assert java == {
        "total": 7,
        "passed": 4,
        "failed": 1,
        "errors": 1,
        "skipped": 1,
        "modules_total": 1,
        "modules_passed": 0,
    }
    rust = _parse_cargo_tests(
        "test result: ok. 6 passed; 0 failed; 1 ignored; 0 measured; "
        "2 filtered out\n"
        "test result: FAILED. 3 passed; 2 failed; 0 ignored; 0 measured; "
        "0 filtered out\n"
    )
    assert rust == {
        "total": 12,
        "passed": 9,
        "failed": 2,
        "ignored": 1,
        "measured": 0,
        "filtered_out": 2,
    }


def test_raw_archive_filter_keeps_evidence_but_withholds_inputs_and_projects():
    assert _related_run_file(Path("full/subject/rep0/recodeagent_run_state.json"))
    assert _related_run_file(Path("full/subject/rep0/pipeline/analysis.md"))
    assert not _related_run_file(Path("full/subject/rep0/source/source.py"))
    assert not _related_run_file(Path("full/subject/rep0/scaffold/pom.xml"))
    assert not _related_run_file(
        Path("full/subject/rep0/pipeline/target/src/main.java")
    )
    assert not _related_run_file(Path("full/subject/rep0/pipeline/burr.db"))


def test_filtered_raw_archive_is_complete_and_excludes_withheld_trees(tmp_path):
    runs = tmp_path / "runs"
    _write(runs / "full/s/rep0/recodeagent_run_state.json", "{}\n")
    _write(runs / "full/s/rep0/pipeline/analysis.md", "analysis\n")
    _write(runs / "full/s/rep0/source/input.py", "secret input\n")
    _write(runs / "full/s/rep0/scaffold/tests.java", "withheld tests\n")
    _write(runs / "full/s/rep0/pipeline/target/main.java", "generated\n")
    _write(runs / "full/s/rep0/pipeline/burr.db", "database\n")
    result = tmp_path / "result"
    inventory = _archive(
        runs,
        result / "raw-run-archives" / "full.tar.gz",
        prefix="runs",
        max_part_bytes=1_000_000,
        predicate=_related_run_file,
    )
    inventory["withheld_scaffold_files"] = 1
    with tarfile.open(
        result / "raw-run-archives" / "full.tar.gz", "r:gz"
    ) as archive:
        names = set(archive.getnames())
    assert "runs/full/s/rep0/recodeagent_run_state.json" in names
    assert "runs/full/s/rep0/pipeline/analysis.md" in names
    assert not any("/source/" in name for name in names)
    assert not any("/scaffold/" in name for name in names)
    assert not any("/pipeline/target/" in name for name in names)
    assert not any(name.endswith("burr.db") for name in names)
    assert _archive_valid(result, {"raw_runs": inventory})


def test_terminal_malformed_candidate_is_a_measured_zero(tmp_path):
    subject = config.REPOTRANSBENCH_SUBJECTS[0]
    run = tmp_path / "runs" / "full" / subject["id"] / "rep0"
    _write(run / "recodeagent_run_state.json", '{"status":"failed"}\n')
    row = evaluate_repotransbench_run(
        subject,
        repetition=0,
        workspace_root=tmp_path / "workspaces",
        runs_root=tmp_path / "runs",
        output_root=tmp_path / "evaluation",
    )
    assert row["evaluation_status"] == "measured"
    assert row["candidate_status"] == "missing_candidate"
    assert row["pass_all"] is False
    assert row["tests_not_executed"] == subject["tests"]


def test_command_timeout_returns_text_diagnostics(tmp_path):
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(1)"],
        cwd=tmp_path,
        timeout=0.01,
    )
    assert result["timed_out"] is True
    assert result["returncode"] == 124
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)


def test_report_artifact_contains_tables_figures_pdfs_and_checksums(
    tmp_path, monkeypatch
):
    def fake_pdf(path, **_kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4\n%%EOF\n")

    def fake_figure(pdf_path, svg_path, **_kwargs):
        fake_pdf(pdf_path)
        _write(svg_path, "<svg xmlns=\"http://www.w3.org/2000/svg\"/>\n")

    monkeypatch.setattr(report, "_render_pdf", fake_pdf)
    monkeypatch.setattr(report, "_render_figure", fake_figure)
    root = tmp_path / "artifact"
    report._write_report_files(
        root,
        key="crust",
        abstract="Synthetic report.",
        sections=[("Scope", "Synthetic measured scope.")],
        tables=[("Results", ["System", "Rate"], [["CodeWeaver", "100%"]])],
        figure=(["Run 1"], [("Pass", [100.0], "#4c78a8")]),
        provenance={"synthetic": True},
        availability=[
            {
                "surface": "synthetic",
                "status": "measured",
                "reason": "unit test",
                "measurement_track": "synthetic",
            }
        ],
    )
    assert (root / "report" / "comparison.pdf").read_bytes().startswith(b"%PDF")
    assert (root / "report" / "figure.pdf").read_bytes().startswith(b"%PDF")
    assert "| CodeWeaver | 100% |" in (
        root / "report" / "comparison.md"
    ).read_text(encoding="utf-8")
    assert (root / "licenses" / "CodeWeaver-MIT.txt").is_file()
    provenance = json.loads(
        (root / "metadata" / "source_provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(provenance["codeweaver_source"]["snapshot_tree_sha256"]) == 64
    assert provenance["codeweaver_source"]["snapshot_files"] > 0
    assert provenance["codeweaver_source"]["base_git_commit"]
    checksums = (root / "metadata" / "checksums.sha256").read_text(
        encoding="utf-8"
    )
    assert "report/comparison.pdf" in checksums
    assert "report/figure.svg" in checksums
