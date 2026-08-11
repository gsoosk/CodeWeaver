"""Focused tests for the self-contained released-artifact baseline replay."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from experiments.recodeagent import baseline_replay as BR
from experiments.recodeagent import common as C
from experiments.recodeagent import run as R
from experiments.recodeagent.common import Measurement, Status


def _row(tool: str, project: str) -> dict:
    languages = {
        "crust": ("C", "Rust"),
        "oxidizer": ("Go", "Rust"),
        "alphatrans": ("Java", "Python"),
        "skel": ("Python", "JavaScript"),
    }
    source, target = languages[tool]
    return {
        "id": f"{tool}__{project}",
        "tool": tool,
        "project": project,
        "source_language": source,
        "target_language": target,
        "function_count_source": 1,
    }


def _manifest(path: Path, rows: list[dict]) -> Path:
    C.atomic_write_json(
        path,
        {
            "counts_match_expected": True,
            "expected_total": len(rows),
            "projects": rows,
        },
    )
    return path


def _write(path: Path, text: str = "fixture\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _released_targets(
    implementation_root: Path,
    results_root: Path,
    rows: list[dict],
) -> None:
    for row in rows:
        tool = row["tool"]
        project = row["project"]
        impl_project = implementation_root / "data" / "tool_projects" / tool / project
        result_project = (
            results_root
            / "recodeagent_translations"
            / "data"
            / "tool_projects"
            / tool
            / project
        )
        if tool == "crust":
            _write(impl_project / "rust" / "Cargo.toml", "[package]\nname='stub'\n")
            _write(result_project / "rust" / "src" / "lib.rs", "pub fn translated() {}\n")
        elif tool == "oxidizer":
            _write(impl_project / "rust" / "src" / "lib.rs", "pub fn prior() {}\n")
            _write(result_project / "rust" / "src" / "lib.rs", "pub fn recode() {}\n")
        elif tool == "alphatrans":
            _write(impl_project / "python" / "prior.py", "VALUE = 'prior'\n")
            _write(result_project / "python" / "recode.py", "VALUE = 'recode'\n")
        else:
            _write(
                impl_project / "javascript" / "translated.js",
                "module.exports = {system: 'prior'};\n",
            )
            _write(
                result_project / "javascript" / "source.js",
                "module.exports = {system: 'recodeagent'};\n",
            )


def _environment_provenance() -> dict:
    return {
        "captured_at": C.utcnow_iso(),
        "model": Measurement.na("no LLM").to_dict(),
        "agent_timeout_seconds": Measurement.na("no agent").to_dict(),
        "git_sha": Measurement.ok("deadbeef").to_dict(),
        "codeweaver_package_version": Measurement.ok("test").to_dict(),
        "copilot_cli_version": Measurement.na("not probed in test").to_dict(),
        "python_version": Measurement.ok("3.test").to_dict(),
        "os": Measurement.ok("test-platform").to_dict(),
        "hostname": Measurement.ok("test-host").to_dict(),
        "toolchains": {"cargo": Measurement.ok("cargo test").to_dict()},
    }


def _base_collect_row(run_dir: Path, kwargs: dict) -> dict:
    return {
        "variant": kwargs["variant"],
        "project_id": kwargs["project_id"],
        "tool": kwargs["tool"],
        "repetition": kwargs["repetition"],
        "workspace_dir": str(run_dir),
        "collected_at": C.utcnow_iso(),
        "run_status": "completed",
        "build": False,
        "build_status": Status.ERROR,
        "build_reason": "fixture evaluator result",
    }


def test_resolves_all_four_released_target_families(tmp_path: Path):
    rows = [
        _row("crust", "c"),
        _row("oxidizer", "o"),
        _row("alphatrans", "a"),
        _row("skel", "s"),
    ]
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    _released_targets(implementation_root, results_root, rows)

    for row in rows:
        recode = BR.resolve_artifact_target(
            "recodeagent", row, implementation_root, results_root
        )
        assert recode.available
        assert recode.target_path is not None
        assert "recodeagent_translations" in str(recode.target_path)
        assert recode.paper_technique == "recodeagent"

    expected_prior = {
        "oxidizer": "oxidizer",
        "alphatrans": "alphatrans",
        "skel": "skel",
    }
    for row in rows[1:]:
        prior = BR.resolve_artifact_target(
            "prior", row, implementation_root, results_root
        )
        assert prior.available
        assert prior.paper_technique == expected_prior[row["tool"]]
        assert "recodeagent_translations" not in str(prior.target_path)


def test_prior_crust_is_unavailable_even_when_stub_scaffold_exists(tmp_path: Path):
    row = _row("crust", "impcheck")
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    _released_targets(implementation_root, results_root, [row])

    resolved = BR.resolve_artifact_target(
        "prior", row, implementation_root, results_root
    )
    assert not resolved.available
    assert resolved.failure_status == Status.UNAVAILABLE
    assert resolved.paper_technique == "swe-agent"
    assert resolved.target_path is None
    assert "stub scaffold" in resolved.reason


def test_missing_recodeagent_target_is_explicit_missing(tmp_path: Path):
    row = _row("oxidizer", "missing")
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    implementation_root.mkdir()
    results_root.mkdir()

    resolved = BR.resolve_artifact_target(
        "recodeagent", row, implementation_root, results_root
    )
    assert not resolved.available
    assert resolved.failure_status == Status.MISSING
    assert resolved.expected_target_path == (
        results_root
        / "recodeagent_translations"
        / "data"
        / "tool_projects"
        / "oxidizer"
        / "missing"
        / "rust"
    )
    assert "missing" in resolved.reason


def test_missing_recodeagent_target_writes_failure_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    row = _row("oxidizer", "missing")
    manifest_path = _manifest(tmp_path / "manifest.json", [row])
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    implementation_root.mkdir()
    results_root.mkdir()
    monkeypatch.setattr(
        BR.C, "collect_provenance", lambda **kwargs: _environment_provenance()
    )
    monkeypatch.setattr(
        BR.COL,
        "collect_run",
        lambda *args, **kwargs: pytest.fail("missing targets must not be collected"),
    )

    result = BR.replay_baselines(
        manifest_path=manifest_path,
        config_path=C.DEFAULT_EXPERIMENT_CONFIG,
        implementation_root=implementation_root,
        results_root=results_root,
        output_root=tmp_path / "output",
        systems=["recodeagent"],
    )

    assert result["rows"] == []
    assert result["failures"][0]["failure_status"] == Status.MISSING
    assert result["summary"]["expected"] == 1
    assert result["summary"]["failures"] == 1
    assert result["paths"]["jsonl"].read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    ("system", "source_name"),
    [("recodeagent", "source.js"), ("prior", "translated.js")],
)
def test_skel_entrypoint_adaptation_preserves_original(
    tmp_path: Path, system: str, source_name: str
):
    row = _row("skel", "bst")
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    _released_targets(implementation_root, results_root, [row])
    resolved = BR.resolve_artifact_target(
        system, row, implementation_root, results_root
    )
    assert resolved.target_path is not None
    source = resolved.target_path / source_name
    before = C.file_sha256(source)

    run_dir = tmp_path / "run"
    adaptations = BR.materialize_synthetic_run(
        resolved, run_dir, _environment_provenance()
    )

    assert (run_dir / "pipeline" / "target" / source_name).is_file()
    assert (run_dir / "pipeline" / "target" / "index.js").read_text(
        encoding="utf-8"
    ) == source.read_text(encoding="utf-8")
    assert C.file_sha256(source) == before
    assert adaptations[0]["preserved_original"] is True
    assert adaptations[0]["source"].endswith(source_name)


def test_replay_labels_systems_writes_complete_outputs_and_never_mutates_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    rows = [
        _row("crust", "c"),
        _row("oxidizer", "o"),
        _row("alphatrans", "a"),
        _row("skel", "s"),
    ]
    manifest_path = _manifest(tmp_path / "manifest.json", rows)
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    output_root = tmp_path / "output"
    _released_targets(implementation_root, results_root, rows)
    expected_path = _write(tmp_path / "results.xlsx", "paper-count-fixture\n")
    source_hashes = {
        str(path): C.file_sha256(path)
        for root in (implementation_root, results_root)
        for path in root.rglob("*")
        if path.is_file()
    }
    calls: list[dict] = []

    def fake_collect(run_dir: Path, **kwargs):
        calls.append({"run_dir": run_dir, **kwargs})
        state = C.read_json(run_dir / R.STATE_FILENAME)
        assert state["status"] == "completed"
        assert kwargs["variant"] == "full"
        assert kwargs["repetition"] == 0
        assert Path(kwargs["reference_results_root"]) == results_root
        if kwargs["tool"] == "crust":
            assert (run_dir / "scaffold" / "Cargo.toml").is_file()
        if kwargs["tool"] == "skel":
            assert (run_dir / "pipeline" / "target" / "index.js").is_file()
        _write(run_dir / "pipeline" / "target" / "evaluator-created.txt")
        return _base_collect_row(run_dir, kwargs)

    monkeypatch.setattr(BR.COL, "collect_run", fake_collect)
    monkeypatch.setattr(
        BR.COL,
        "read_crust_paper_expected_tests",
        lambda path: ({"c": 1}, ""),
    )
    monkeypatch.setattr(
        BR.C, "collect_provenance", lambda **kwargs: _environment_provenance()
    )

    result = BR.replay_baselines(
        manifest_path=manifest_path,
        config_path=C.DEFAULT_EXPERIMENT_CONFIG,
        implementation_root=implementation_root,
        results_root=results_root,
        output_root=output_root,
        systems=["recodeagent", "prior"],
        jobs=3,
        timeout=12.5,
        crust_paper_expected_path=expected_path,
    )

    assert len(calls) == 7
    assert len(result["rows"]) == 7
    assert len(result["failures"]) == 1
    assert {row["system"] for row in result["rows"]} == {"recodeagent", "prior"}
    assert {
        (row["system"], row["tool"], row["paper_technique"])
        for row in result["rows"]
    } >= {
        ("recodeagent", "crust", "recodeagent"),
        ("prior", "oxidizer", "oxidizer"),
        ("prior", "alphatrans", "alphatrans"),
        ("prior", "skel", "skel"),
    }
    assert all(row["build_status"] == Status.ERROR for row in result["rows"])
    assert all(row["build_reason"] == "fixture evaluator result" for row in result["rows"])
    assert all(Path(row["artifact_target_path"]).is_dir() for row in result["rows"])
    for replay_row in result["rows"]:
        adaptations = json.loads(replay_row["evaluator_adaptations_json"])
        if replay_row["tool"] == "skel":
            assert adaptations[0]["kind"] == "evaluator_entrypoint_copy"
        else:
            assert adaptations == []
    assert result["failures"][0]["failure_status"] == Status.UNAVAILABLE
    assert result["failures"][0]["paper_technique"] == "swe-agent"

    summary = result["summary"]
    assert summary["expected"] == 8
    assert summary["measured"] == 7
    assert summary["failures"] == 1
    assert summary["by_system"]["prior"]["by_tool"]["crust"] == {
        "expected": 1,
        "measured": 0,
        "failures": 1,
    }
    assert summary["swe_agent_outputs"]["available"] is False
    assert "unavailable" in summary["swe_agent_outputs"]["statement"].lower()

    expected_outputs = {
        "baseline_raw_runs.jsonl",
        "baseline_raw_runs.csv",
        "baseline_failures.csv",
        "baseline_replay_summary.json",
        "baseline_replay_provenance.json",
    }
    assert {path.name for path in output_root.iterdir()} == expected_outputs
    assert len(
        [
            json.loads(line)
            for line in (output_root / "baseline_raw_runs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
    ) == 7
    with open(output_root / "baseline_raw_runs.csv", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    assert header[:3] == ["system", "paper_technique", "variant"]

    provenance = C.read_json(output_root / "baseline_replay_provenance.json")
    assert provenance["fresh_llm_rerun"] is False
    assert provenance["roots"]["implementation_root"] == str(
        implementation_root.resolve()
    )
    assert provenance["roots"]["results_root"] == str(results_root.resolve())
    assert provenance["inputs"]["manifest"]["sha256"]
    assert provenance["inputs"]["config"]["sha256"]
    assert provenance["inputs"]["results_xlsx"]["sha256"] == C.file_sha256(
        expected_path
    )
    assert provenance["environment"]["toolchains"]

    after_hashes = {
        str(path): C.file_sha256(path)
        for root in (implementation_root, results_root)
        for path in root.rglob("*")
        if path.is_file()
    }
    assert after_hashes == source_hashes
    assert not (output_root / ".baseline_replay_tmp").exists()


def test_cli_parser_accepts_all_replay_inputs():
    parser = BR.build_parser()
    args = parser.parse_args(
        [
            "--manifest",
            "manifest.json",
            "--config",
            "experiment.toml",
            "--implementation-root",
            "implementation",
            "--results-root",
            "results",
            "--output-root",
            "output",
            "--system",
            "prior,recodeagent",
            "--jobs",
            "4",
            "--timeout",
            "30",
            "--crust-paper-expected-tests",
            "results.xlsx",
            "--keep-materialized-root",
            "materialized",
        ]
    )
    assert args.system == ["prior", "recodeagent"]
    assert args.jobs == 4
    assert args.timeout == 30
    assert args.crust_paper_expected_tests == "results.xlsx"
    assert args.keep_materialized_root == "materialized"

    defaults = parser.parse_args(
        [
            "--manifest",
            "manifest.json",
            "--implementation-root",
            "implementation",
            "--results-root",
            "results",
            "--output-root",
            "output",
        ]
    )
    assert defaults.system == ["recodeagent", "prior"]
    assert defaults.config == str(C.DEFAULT_EXPERIMENT_CONFIG)


def test_cli_parser_rejects_unknown_or_duplicate_systems():
    parser = BR.build_parser()
    base = [
        "--manifest",
        "manifest.json",
        "--implementation-root",
        "implementation",
        "--results-root",
        "results",
        "--output-root",
        "output",
    ]
    with pytest.raises(SystemExit):
        parser.parse_args([*base, "--system", "unknown"])
    with pytest.raises(SystemExit):
        parser.parse_args([*base, "--system", "prior,prior"])


def test_keep_materialized_root_refuses_ambiguous_or_official_locations(
    tmp_path: Path,
):
    implementation_root = tmp_path / "implementation"
    results_root = tmp_path / "results"
    output_root = tmp_path / "output"
    implementation_root.mkdir()
    results_root.mkdir()
    output_root.mkdir()

    ambiguous = tmp_path / "ambiguous"
    _write(ambiguous / "unrelated.txt")
    with pytest.raises(ValueError, match="non-empty"):
        BR.prepare_keep_materialized_root(
            ambiguous,
            implementation_root=implementation_root,
            results_root=results_root,
            output_root=output_root,
        )

    with pytest.raises(ValueError, match="overlap"):
        BR.prepare_keep_materialized_root(
            implementation_root / "debug",
            implementation_root=implementation_root,
            results_root=results_root,
            output_root=output_root,
        )
