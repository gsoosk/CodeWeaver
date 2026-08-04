from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import package_results as PKG


def test_meaningful_run_file_preserves_translation_but_drops_caches() -> None:
    assert PKG.meaningful_run_file(
        Path("crust__a/rep0/pipeline/target/src/lib.rs")
    )
    assert PKG.meaningful_run_file(
        Path("crust__a/rep0/pipeline/validator/report.json")
    )
    assert not PKG.meaningful_run_file(
        Path("crust__a/rep0/source/src/lib.c")
    )
    assert not PKG.meaningful_run_file(
        Path("crust__a/rep0/pipeline/target/target/debug/lib.rlib")
    )
    assert not PKG.meaningful_run_file(
        Path("crust__a/rep0/pipeline/target/node_modules/pkg/index.js")
    )
    assert not PKG.meaningful_run_file(
        Path("crust__a/rep0/pipeline/target/.coverage")
    )


def test_repository_snapshot_includes_complete_untracked_test_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "snapshot"
    (source / "experiments" / "recodeagent").mkdir(parents=True)
    (source / "experiments" / "recodeagent" / "runner.py").write_text("RUNNER")
    (source / "tests" / "experiments").mkdir(parents=True)
    (source / "tests" / "experiments" / "test_runner.py").write_text("HARNESS")
    (source / "tests" / "test_copilot.py").write_text("CORE")
    monkeypatch.setattr(PKG, "_run_git", lambda _root, _args: "")

    PKG._copy_repository_snapshot(source, destination)

    assert (destination / "tests" / "experiments" / "test_runner.py").read_text() == "HARNESS"
    assert (destination / "tests" / "test_copilot.py").read_text() == "CORE"


def test_filtered_archive_and_split(tmp_path: Path) -> None:
    source = tmp_path / "runs"
    kept = source / "p" / "rep0" / "pipeline" / "target" / "src" / "lib.rs"
    kept.parent.mkdir(parents=True)
    kept.write_text("pub fn f() {}\n", encoding="utf-8")
    dropped = source / "p" / "rep0" / "source" / "lib.c"
    dropped.parent.mkdir(parents=True)
    dropped.write_text("void f(void) {}\n", encoding="utf-8")

    archive, count = PKG.create_filtered_archive(
        source,
        tmp_path / "raw.tar.gz",
        arc_prefix="full",
    )
    assert count == 1
    with tarfile.open(archive, "r:gz") as handle:
        assert handle.getnames() == [
            "full/p/rep0/pipeline/target/src/lib.rs"
        ]

    parts = PKG.split_file(archive, max_part_bytes=5)
    assert len(parts) > 1
    assert not archive.exists()
    assert b"".join(part.read_bytes() for part in parts).startswith(b"\x1f\x8b")


def _write_required_outputs(analysis: Path, report: Path, *, complete: bool) -> None:
    analysis.mkdir()
    report.mkdir()
    for filename in PKG.REQUIRED_ANALYSIS_PDFS:
        (analysis / filename).write_bytes(b"%PDF-1.4\n")
    (analysis / "paper_table1_side_by_side.csv").write_text(
        "paper,codeweaver\n1,1\n", encoding="utf-8"
    )
    (analysis / "paper_table2_side_by_side.csv").write_text(
        "paper,codeweaver\n1,1\n", encoding="utf-8"
    )
    C.atomic_write_json(
        analysis / "paper_tables_side_by_side_provenance.json",
        {"available": True},
    )
    (analysis / "table1_effectiveness.csv").write_text("x\n1\n", encoding="utf-8")
    (report / "reproducibility_report.pdf").write_bytes(b"%PDF-1.4\n")
    C.atomic_write_json(
        report / "reproducibility_report_data.json",
        {"verdict": {"complete": complete, "reasons": [] if complete else ["missing"]}},
    )


def test_package_results_copies_data_provenance_and_archives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = tmp_path / "manifest.json"
    C.atomic_write_json(manifest, {"projects": []})
    collected = tmp_path / "collected"
    paper_test = tmp_path / "paper-test"
    analysis = tmp_path / "analysis"
    report = tmp_path / "report"
    runs = tmp_path / "runs"
    source = tmp_path / "source-repo"
    for root in (collected, paper_test, source):
        root.mkdir()
    (collected / "raw_runs.jsonl").write_text("{}\n", encoding="utf-8")
    (paper_test / "generated_test_projects.jsonl").write_text("{}\n", encoding="utf-8")
    _write_required_outputs(analysis, report, complete=True)
    for variant in C.RUN_VARIANTS:
        path = runs / variant / "project" / "rep0" / "pipeline" / "run_state.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    (runs / "run_summary_full.json").write_text("{}\n", encoding="utf-8")
    infrastructure = tmp_path / "infrastructure-failures"
    excluded_state = (
        infrastructure
        / "retry-auth"
        / "full"
        / "project"
        / "rep0"
        / "recodeagent_run_state.json"
    )
    excluded_state.parent.mkdir(parents=True)
    excluded_state.write_text('{"status":"failed"}\n', encoding="utf-8")

    monkeypatch.setattr(
        PKG,
        "_run_git",
        lambda _root, args: "" if args[0] != "ls-files" else "",
    )
    monkeypatch.setattr(
        PKG,
        "_copy_repository_snapshot",
        lambda _source, destination: (
            destination.mkdir(parents=True, exist_ok=True) or 0
        ),
    )
    monkeypatch.setattr(
        PKG,
        "capture_environment",
        lambda metadata: (metadata / "python-environment-lock.txt").write_text(
            "example==1\n", encoding="utf-8"
        ),
    )
    output = tmp_path / "final"
    package = PKG.package_results(
        manifest_path=manifest,
        collected_root=collected,
        paper_test_root=paper_test,
        analysis_root=analysis,
        report_root=report,
        runs_root=runs,
        output_root=output,
        source_root=source,
        require_complete=True,
        include_run_archives=True,
        max_part_bytes=1024 * 1024,
        infrastructure_failures_root=infrastructure,
    )

    assert package["completion_verdict"]["complete"]
    assert len(package["run_archives"]) == 6
    assert len(package["infrastructure_failure_archives"]) == 1
    assert (output / "data" / "collected" / "raw_runs.jsonl").is_file()
    assert (output / "results" / "analysis" / "table1_effectiveness.pdf").is_file()
    assert (output / "metadata" / "checksums.sha256").is_file()
    assert (output / "metadata" / "python-environment-lock.txt").is_file()
    assert (output / "metadata" / "run-summaries" / "run_summary_full.json").is_file()
    audit = json.loads(
        (output / "metadata" / "infrastructure_failure_audit.json").read_text()
    )
    assert audit["attempts"][0]["status"] == "failed"
    assert (output / "README.md").is_file()


def test_package_results_refuses_incomplete_verdict(
    tmp_path: Path,
) -> None:
    analysis = tmp_path / "analysis"
    report = tmp_path / "report"
    _write_required_outputs(analysis, report, complete=False)
    with pytest.raises(RuntimeError, match="incomplete reproduction"):
        PKG.package_results(
            manifest_path=tmp_path / "manifest.json",
            collected_root=tmp_path / "collected",
            paper_test_root=tmp_path / "paper-test",
            analysis_root=analysis,
            report_root=report,
            runs_root=tmp_path / "runs",
            output_root=tmp_path / "output",
            source_root=tmp_path / "source",
            require_complete=True,
            include_run_archives=False,
            max_part_bytes=100,
        )
