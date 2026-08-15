from __future__ import annotations

import copy
import sys
import tarfile
from pathlib import Path

import pytest

from experiments.related_papers import config
from experiments.related_papers import report
from experiments.related_papers.common import run_command
from experiments.related_papers.package import (
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
    checksums = (root / "metadata" / "checksums.sha256").read_text(
        encoding="utf-8"
    )
    assert "report/comparison.pdf" in checksums
    assert "report/figure.svg" in checksums
