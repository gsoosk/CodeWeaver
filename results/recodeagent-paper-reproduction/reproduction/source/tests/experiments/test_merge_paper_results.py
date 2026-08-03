from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import merge_paper_results as MERGE
from experiments.recodeagent import paper_test_compare as PT


def _generated(project_id: str, tool: str) -> dict:
    return {
        "variant": "full",
        "repetition": 0,
        "project_id": project_id,
        "tool": tool,
        "project": project_id.split("__", 1)[-1],
        "generated_tests_expected": 1,
        "generated_tests_expected_status": "measured",
        "generated_tests_expected_reason": "",
        "generated_tests_executed": 1,
        "generated_tests_executed_status": "measured",
        "generated_tests_executed_reason": "",
        "generated_tests_passed": 1,
        "generated_tests_passed_status": "measured",
        "generated_tests_passed_reason": "",
        "coverage_before": 0.5,
        "coverage_before_status": "measured",
        "coverage_before_reason": "",
        "coverage_after": 0.6,
        "coverage_after_status": "measured",
        "coverage_after_reason": "",
    }


def _write_shard(
    root: Path,
    *,
    projects: list[dict],
    generated: list[dict],
    embedding: bool,
) -> None:
    root.mkdir()
    MERGE._write_csv(root / "paper_test_projects.csv", projects, PT.PROJECT_COLUMNS)
    MERGE._write_csv(root / "paper_test_failures.csv", [], PT.FAILURE_COLUMNS)
    MERGE._write_csv(
        root / "generated_test_projects.csv",
        generated,
        PT.GENERATED_PROJECT_COLUMNS,
    )
    MERGE._write_csv(root / "generated_test_failures.csv", [], PT.FAILURE_COLUMNS)
    C.atomic_write_text(
        root / "generated_test_projects.jsonl",
        "".join(json.dumps(row) + "\n" for row in generated),
    )
    C.atomic_write_json(
        root / "paper_test_summary.json",
        {
            "embedding_status": "measured" if embedding else "not_requested",
            "embedding_model": "Qwen/Qwen3-Embedding-0.6B" if embedding else None,
        },
    )


def test_merge_paper_results_combines_noncrust_and_crust_shards(
    tmp_path: Path,
) -> None:
    manifest = {
        "projects": [
            {"id": "oxidizer__checkdigit", "tool": "oxidizer"},
            {"id": "crust__example", "tool": "crust"},
        ]
    }
    paper_row = {
        "variant": "full",
        "repetition": 0,
        "project_id": "oxidizer__checkdigit",
        "tool": "oxidizer",
        "static_source_methods": 4,
        "paper_runtime_tests": 5,
        "mapped_runtime_cases": 3,
        "generated_target_test_methods": 1,
    }
    noncrust = tmp_path / "noncrust"
    crust = tmp_path / "crust"
    _write_shard(
        noncrust,
        projects=[paper_row],
        generated=[_generated("oxidizer__checkdigit", "oxidizer")],
        embedding=True,
    )
    _write_shard(
        crust,
        projects=[],
        generated=[_generated("crust__example", "crust")],
        embedding=False,
    )
    artifact = noncrust / "full" / "oxidizer__checkdigit" / "rep0" / "report.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")

    output = tmp_path / "merged"
    summary = MERGE.merge_paper_results(
        [noncrust, crust],
        output,
        manifest=manifest,
        variants=["full"],
        repetitions=1,
        require_complete=True,
    )

    assert summary["project_rows"] == 1
    assert summary["generated_test_project_rows"] == 2
    assert summary["complete"]
    assert summary["embedding_status"] == "measured"
    assert (
        output / "full" / "oxidizer__checkdigit" / "rep0" / "report.json"
    ).is_file()


def test_merge_paper_results_rejects_missing_generated_project(
    tmp_path: Path,
) -> None:
    shard = tmp_path / "shard"
    _write_shard(shard, projects=[], generated=[], embedding=False)
    with pytest.raises(ValueError, match="generated_missing"):
        MERGE.merge_paper_results(
            [shard],
            tmp_path / "merged",
            manifest={"projects": [{"id": "crust__example", "tool": "crust"}]},
            variants=["full"],
            repetitions=1,
            require_complete=False,
        )
