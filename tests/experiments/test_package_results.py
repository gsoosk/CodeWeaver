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
    (source / "codeweaver").mkdir()
    (source / "codeweaver" / "core.py").write_text("SOURCE")
    (source / "results").mkdir()
    (source / "results" / "package.pdf").write_bytes(b"%PDF-1.4\n")
    (source / "raw-run-archives").mkdir()
    (source / "raw-run-archives" / "full.tar.gz").write_bytes(b"archive")
    monkeypatch.setattr(
        PKG,
        "_run_git",
        lambda _root, _args: (
            "codeweaver/core.py\nresults/package.pdf\nraw-run-archives/full.tar.gz\n"
        ),
    )

    PKG._copy_repository_snapshot(source, destination)

    assert (destination / "tests" / "experiments" / "test_runner.py").read_text() == "HARNESS"
    assert (destination / "tests" / "test_copilot.py").read_text() == "CORE"
    assert (destination / "codeweaver" / "core.py").read_text() == "SOURCE"
    assert not (destination / "results").exists()
    assert not (destination / "raw-run-archives").exists()


def test_filtered_archive_and_split(tmp_path: Path) -> None:
    source = tmp_path / "runs"
    kept = source / "p" / "rep0" / "pipeline" / "target" / "src" / "lib.rs"
    kept.parent.mkdir(parents=True)
    kept.write_text("pub fn f() {}\n", encoding="utf-8")
    broken_link = kept.with_name("generated.rs")
    broken_link.symlink_to("missing.rs")
    dropped = source / "p" / "rep0" / "source" / "lib.c"
    dropped.parent.mkdir(parents=True)
    dropped.write_text("void f(void) {}\n", encoding="utf-8")

    archive, count = PKG.create_filtered_archive(
        source,
        tmp_path / "raw.tar.gz",
        arc_prefix="full",
    )
    assert count == 2
    with tarfile.open(archive, "r:gz") as handle:
        assert handle.getnames() == [
            "full/p/rep0/pipeline/target/src/generated.rs",
            "full/p/rep0/pipeline/target/src/lib.rs"
        ]
        link = handle.getmember(
            "full/p/rep0/pipeline/target/src/generated.rs"
        )
        assert link.issym()
        assert link.linkname == "missing.rs"

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


def _write_baseline_root(root: Path) -> None:
    root.mkdir(parents=True)
    for filename in PKG.REQUIRED_BASELINE_FILES:
        (root / filename).write_text("{}\n", encoding="utf-8")


def _write_system_comparison_root(
    root: Path,
    *,
    missing_file: str | None = None,
    unavailable: bool = True,
    accounted_missing: int | None = None,
    unaccounted_missing: int = 0,
) -> None:
    root.mkdir(parents=True)
    for filename in PKG.REQUIRED_SYSTEM_COMPARISON_FILES:
        if filename == missing_file:
            continue
        if filename.endswith(".json"):
            C.atomic_write_json(root / filename, {})
        else:
            (root / filename).write_text("column\nvalue\n", encoding="utf-8")
    if PKG.REQUIRED_SYSTEM_COMPARISON_PDF != missing_file:
        (root / PKG.REQUIRED_SYSTEM_COMPARISON_PDF).write_bytes(b"%PDF-1.4\n")
    inventory = {
        "expected": 118,
        "measured": 118,
        "unavailable": 100 if unavailable else 0,
        "error": 0,
        "missing": 0,
    }
    comparison_data: dict[str, object] = {
        "inventory": [inventory],
        "crust_three_system_overlap": {
            "status": "unavailable" if unavailable else "measured",
        },
    }
    if accounted_missing is not None:
        inventory["accounted_missing"] = accounted_missing
        inventory["unaccounted_missing"] = unaccounted_missing
        inventory["missing"] = accounted_missing + unaccounted_missing
        inventory["measured"] = 118 - inventory["missing"]
        comparison_data["inventory_completeness"] = {
            key: inventory[key]
            for key in (
                "expected", "measured", "unavailable", "error", "missing",
                "accounted_missing", "unaccounted_missing",
            )
        }
        comparison_data["inventory_completeness"]["all_expected_cells_accounted_for"] = (
            unaccounted_missing == 0
        )
    C.atomic_write_json(root / "system_comparison.json", comparison_data)
    C.atomic_write_json(root / "system_comparison_provenance.json", {"inputs_sha256": {}})


def _patch_package_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(PKG, "_run_git", lambda _root, _args: "")
    monkeypatch.setattr(
        PKG,
        "_copy_repository_snapshot",
        lambda _source, destination: (destination.mkdir(parents=True, exist_ok=True) or 0),
    )
    monkeypatch.setattr(
        PKG,
        "capture_environment",
        lambda metadata: (metadata / "python-environment-lock.txt").write_text(
            "example==1\n", encoding="utf-8"
        ),
    )


def test_run_git_normalizes_windows_line_endings(tmp_path: Path, monkeypatch):
    captured = {}

    def run_argv(argv, *, cwd):
        captured["argv"] = argv
        captured["cwd"] = cwd
        return C.ExecResult(
            argv=argv,
            returncode=0,
            stdout="",
            stderr="",
            duration_s=0.0,
            timed_out=False,
            started_at=C.utcnow_iso(),
            ended_at=C.utcnow_iso(),
            cwd=str(cwd),
        )

    monkeypatch.setattr(PKG.C, "run_argv", run_argv)

    assert PKG._run_git(tmp_path, ["status", "--short"]) == ""
    assert captured["argv"][:4] == [
        "git",
        "-c",
        "core.autocrlf=true",
        "--no-pager",
    ]


def _minimal_package_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Path]:
    inputs = {
        name: tmp_path / name
        for name in (
            "manifest.json", "collected", "paper-test", "analysis", "report",
            "runs", "source", "output",
        )
    }
    C.atomic_write_json(inputs["manifest.json"], {"projects": []})
    for name in ("collected", "paper-test", "runs", "source"):
        inputs[name].mkdir()
    _write_required_outputs(inputs["analysis"], inputs["report"], complete=True)
    _patch_package_side_effects(monkeypatch)
    return inputs


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

    _patch_package_side_effects(monkeypatch)
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


def test_package_results_full_only_copies_all_optional_publication_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = tmp_path / "manifest.json"
    collected = tmp_path / "collected"
    paper_test = tmp_path / "paper-test"
    analysis = tmp_path / "analysis"
    report = tmp_path / "report"
    runs = tmp_path / "runs"
    source = tmp_path / "source"
    for root in (collected, paper_test, source):
        root.mkdir()
    C.atomic_write_json(manifest, {"projects": []})
    (collected / "raw_runs.jsonl").write_text("{}\n", encoding="utf-8")
    (paper_test / "generated_test_projects.jsonl").write_text("{}\n", encoding="utf-8")
    _write_required_outputs(analysis, report, complete=True)
    run_file = runs / "full" / "project" / "rep0" / "pipeline" / "run_state.json"
    run_file.parent.mkdir(parents=True)
    run_file.write_text("{}\n", encoding="utf-8")

    recodeagent_baseline = tmp_path / "recodeagent-replay"
    prior_baseline = tmp_path / "prior-replay"
    _write_baseline_root(recodeagent_baseline)
    _write_baseline_root(prior_baseline)
    system_comparison = tmp_path / "system-comparison"
    _write_system_comparison_root(system_comparison)
    test_comparison = tmp_path / "test-comparison"
    test_comparison.mkdir()
    (test_comparison / "test_comparisons.jsonl").write_text("{}\n", encoding="utf-8")
    summaries = tmp_path / "summaries"
    logs = tmp_path / "logs"
    summaries.mkdir()
    logs.mkdir()
    (summaries / "campaign.json").write_text("{}\n", encoding="utf-8")
    (logs / "campaign.log").write_text("log\n", encoding="utf-8")
    _patch_package_side_effects(monkeypatch)

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
        variants=["full"],
        baseline_roots=[recodeagent_baseline, prior_baseline],
        system_comparison_root=system_comparison,
        test_comparison_root=test_comparison,
        campaign_metadata_roots=[summaries, logs],
    )

    assert [archive["variant"] for archive in package["run_archives"]] == ["full"]
    assert package["selected_variants"] == ["full"]
    assert package["system_comparison_completeness"]["status"] == (
        "complete_with_explicit_unavailability"
    )
    assert (output / "data" / "baselines" / "recodeagent-replay" / "baseline_raw_runs.jsonl").is_file()
    assert (output / "data" / "baselines" / "prior-replay" / "baseline_replay_provenance.json").is_file()
    assert (output / "results" / "system-comparison" / "system_comparison.pdf").is_file()
    assert (output / "data" / "test-comparisons" / "test_comparisons.jsonl").is_file()
    assert (output / "metadata" / "campaign" / "summaries" / "campaign.json").is_file()
    assert (output / "metadata" / "campaign" / "logs" / "campaign.log").is_file()
    manifest_data = C.read_json(output / "metadata" / "package_manifest.json")
    assert len(manifest_data["input_paths"]["baseline_roots"]) == 2
    assert len(manifest_data["input_paths"]["campaign_metadata_roots"]) == 2
    checksums = (output / "metadata" / "checksums.sha256").read_text(encoding="utf-8")
    assert "results/system-comparison/system_comparison.pdf" in checksums
    assert "data/baselines/recodeagent-replay/baseline_raw_runs.jsonl" in checksums
    assert "metadata/campaign/summaries/campaign.json" in checksums
    readme = (output / "README.md").read_text(encoding="utf-8")
    assert "the Full variant" in readme
    assert "6-variant" not in readme


def test_package_require_complete_accepts_accounted_missing_comparison_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _minimal_package_inputs(tmp_path, monkeypatch)
    comparison = tmp_path / "system-comparison"
    _write_system_comparison_root(
        comparison,
        unavailable=False,
        accounted_missing=1,
        unaccounted_missing=0,
    )

    package = PKG.package_results(
        manifest_path=inputs["manifest.json"],
        collected_root=inputs["collected"],
        paper_test_root=inputs["paper-test"],
        analysis_root=inputs["analysis"],
        report_root=inputs["report"],
        runs_root=inputs["runs"],
        output_root=inputs["output"],
        source_root=inputs["source"],
        require_complete=True,
        include_run_archives=False,
        max_part_bytes=100,
        system_comparison_root=comparison,
    )

    assert package["system_comparison_completeness"]["complete"] is True
    assert package["system_comparison_completeness"][
        "accounted_missing_artifact_cell_count"
    ] == 1


def test_package_require_complete_rejects_unaccounted_missing_comparison_cell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _minimal_package_inputs(tmp_path, monkeypatch)
    comparison = tmp_path / "system-comparison"
    _write_system_comparison_root(
        comparison,
        unavailable=False,
        accounted_missing=0,
        unaccounted_missing=1,
    )

    with pytest.raises(RuntimeError, match="unaccounted missing"):
        PKG.package_results(
            manifest_path=inputs["manifest.json"],
            collected_root=inputs["collected"],
            paper_test_root=inputs["paper-test"],
            analysis_root=inputs["analysis"],
            report_root=inputs["report"],
            runs_root=inputs["runs"],
            output_root=inputs["output"],
            source_root=inputs["source"],
            require_complete=True,
            include_run_archives=False,
            max_part_bytes=100,
            system_comparison_root=comparison,
        )


def test_comparison_completeness_verifies_legacy_missing_failure_evidence() -> None:
    completeness = PKG._system_comparison_completeness({
        "inventory": [{
            "expected": 1,
            "measured": 0,
            "unavailable": 0,
            "error": 0,
            "missing": 1,
            "failure_evidence_rows": 1,
            "conflicting_failure_evidence_rows": 0,
        }],
    })
    assert completeness["complete"] is True
    assert completeness["accounted_missing_artifact_cell_count"] == 1
    assert completeness["unaccounted_missing_artifact_cell_count"] == 0


def test_package_results_rejects_duplicate_baseline_destination_labels(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    report = tmp_path / "report"
    _write_required_outputs(analysis, report, complete=True)
    first = tmp_path / "one" / "same-label"
    second = tmp_path / "two" / "same label"
    _write_baseline_root(first)
    _write_baseline_root(second)
    with pytest.raises(ValueError, match="duplicate baseline destination label"):
        PKG.package_results(
            manifest_path=tmp_path / "manifest.json",
            collected_root=tmp_path / "collected",
            paper_test_root=tmp_path / "paper-test",
            analysis_root=analysis,
            report_root=report,
            runs_root=tmp_path / "runs",
            output_root=tmp_path / "output",
            source_root=tmp_path / "source",
            require_complete=False,
            include_run_archives=False,
            max_part_bytes=100,
            baseline_roots=[first, second],
        )


@pytest.mark.parametrize(
    "missing_file",
    [PKG.REQUIRED_SYSTEM_COMPARISON_PDF, "system_comparison_paired.csv"],
)
def test_package_results_rejects_missing_required_system_comparison_outputs(
    tmp_path: Path,
    missing_file: str,
) -> None:
    analysis = tmp_path / "analysis"
    report = tmp_path / "report"
    comparison = tmp_path / "system-comparison"
    _write_required_outputs(analysis, report, complete=True)
    _write_system_comparison_root(comparison, missing_file=missing_file)
    with pytest.raises(FileNotFoundError, match="system-comparison root is incomplete"):
        PKG.package_results(
            manifest_path=tmp_path / "manifest.json",
            collected_root=tmp_path / "collected",
            paper_test_root=tmp_path / "paper-test",
            analysis_root=analysis,
            report_root=report,
            runs_root=tmp_path / "runs",
            output_root=tmp_path / "output",
            source_root=tmp_path / "source",
            require_complete=False,
            include_run_archives=False,
            max_part_bytes=100,
            system_comparison_root=comparison,
        )


def test_package_results_rejects_campaign_run_tree(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    report = tmp_path / "report"
    campaign = tmp_path / "campaign"
    _write_required_outputs(analysis, report, complete=True)
    (campaign / "full" / "project" / "rep0").mkdir(parents=True)
    with pytest.raises(ValueError, match="run-variant directory"):
        PKG.package_results(
            manifest_path=tmp_path / "manifest.json",
            collected_root=tmp_path / "collected",
            paper_test_root=tmp_path / "paper-test",
            analysis_root=analysis,
            report_root=report,
            runs_root=tmp_path / "runs",
            output_root=tmp_path / "output",
            source_root=tmp_path / "source",
            require_complete=False,
            include_run_archives=False,
            max_part_bytes=100,
            campaign_metadata_roots=[campaign],
        )


def test_package_variant_parser_is_strict_and_backwards_compatible() -> None:
    assert PKG._parse_variants("all") == list(C.RUN_VARIANTS)
    assert PKG._parse_variants("full") == ["full"]
    with pytest.raises(ValueError, match="duplicates"):
        PKG._parse_variants("full,full")
    with pytest.raises(ValueError, match="unknown archive"):
        PKG._parse_variants("not-a-variant")


def test_package_parser_exposes_publication_integration_flags() -> None:
    args = PKG.build_parser().parse_args([
        "--manifest", "manifest.json",
        "--collected-root", "collected",
        "--paper-test-root", "paper-test",
        "--analysis-root", "analysis",
        "--report-root", "report",
        "--runs-root", "runs",
        "--output-root", "out",
        "--variant", "full",
        "--baseline-root", "baseline-a",
        "--baseline-root", "baseline-b",
        "--system-comparison-root", "comparison",
        "--test-comparison-root", "test-comparison",
        "--campaign-metadata-root", "summaries",
    ])
    assert args.variant == "full"
    assert args.baseline_root == ["baseline-a", "baseline-b"]
    assert args.system_comparison_root == "comparison"
    assert args.test_comparison_root == "test-comparison"
    assert args.campaign_metadata_root == ["summaries"]


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
