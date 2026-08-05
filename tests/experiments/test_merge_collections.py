from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.recodeagent import collect as COL
from experiments.recodeagent import merge_collections as MERGE


def _row(variant: str, project_id: str, value: int = 1) -> dict:
    return {
        "variant": variant,
        "project_id": project_id,
        "repetition": 0,
        "tool": "crust",
        "value": value,
    }


def _shard(root: Path, rows: list[dict], failures: list[dict] | None = None) -> None:
    root.mkdir()
    COL.write_raw_runs(rows, root)
    COL.write_failures(failures or [], root)


def test_merge_collections_writes_complete_deterministic_matrix(tmp_path: Path) -> None:
    manifest = {"projects": [{"id": "p1"}, {"id": "p2"}]}
    full = tmp_path / "full"
    base = tmp_path / "base"
    _shard(full, [_row("full", "p2"), _row("full", "p1")])
    _shard(base, [_row("baseagent-concat", "p1"), _row("baseagent-concat", "p2")])

    output = tmp_path / "merged"
    summary = MERGE.merge_collections(
        [base, full],
        output,
        manifest=manifest,
        variants=["full", "baseagent-concat"],
        repetitions=1,
        require_raw_complete=True,
    )

    assert summary["raw_rows"] == 4
    assert summary["complete"]
    rows = [
        json.loads(line)
        for line in (output / "raw_runs.jsonl").read_text().splitlines()
    ]
    assert [(row["variant"], row["project_id"]) for row in rows] == [
        ("full", "p1"),
        ("full", "p2"),
        ("baseagent-concat", "p1"),
        ("baseagent-concat", "p2"),
    ]


def test_merge_collections_rejects_missing_cell(tmp_path: Path) -> None:
    shard = tmp_path / "shard"
    _shard(shard, [_row("full", "p1")])
    with pytest.raises(ValueError, match="missing="):
        MERGE.merge_collections(
            [shard],
            tmp_path / "merged",
            manifest={"projects": [{"id": "p1"}, {"id": "p2"}]},
            variants=["full"],
            repetitions=1,
            require_raw_complete=False,
        )


def test_merge_collections_rejects_conflicting_duplicate(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _shard(first, [_row("full", "p1", 1)])
    _shard(second, [_row("full", "p1", 2)])
    with pytest.raises(ValueError, match="conflicting raw row"):
        MERGE.merge_collections(
            [first, second],
            tmp_path / "merged",
            manifest={"projects": [{"id": "p1"}]},
            variants=["full"],
            repetitions=1,
            require_raw_complete=False,
        )


def test_merge_collections_allows_explicit_later_evaluator_repair(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    repair = tmp_path / "repair"
    _shard(first, [_row("full", "p1", 1)])
    _shard(repair, [_row("full", "p1", 2)])

    output = tmp_path / "merged"
    summary = MERGE.merge_collections(
        [first, repair],
        output,
        manifest={"projects": [{"id": "p1"}]},
        variants=["full"],
        repetitions=1,
        require_raw_complete=True,
        replace_keys={("full", "p1", 0)},
    )

    row = json.loads((output / "raw_runs.jsonl").read_text().strip())
    assert row["value"] == 2
    assert summary["replaced_raw_keys"] == [["full", "p1", 0]]


def test_merge_collections_rejects_unused_replacement_key(tmp_path: Path) -> None:
    shard = tmp_path / "shard"
    _shard(shard, [_row("full", "p1", 1)])
    with pytest.raises(ValueError, match="not duplicated"):
        MERGE.merge_collections(
            [shard],
            tmp_path / "merged",
            manifest={"projects": [{"id": "p1"}]},
            variants=["full"],
            repetitions=1,
            require_raw_complete=True,
            replace_keys={("full", "p1", 0)},
        )


def test_parse_replace_key_uses_rightmost_separators() -> None:
    assert MERGE._parse_replace_key("full:oxidizer__demo:0") == (
        "full",
        "oxidizer__demo",
        0,
    )
    with pytest.raises(ValueError, match="invalid repetition"):
        MERGE._parse_replace_key("full:oxidizer__demo:nope")


def test_merge_collections_can_gate_unresolved_failures(tmp_path: Path) -> None:
    shard = tmp_path / "shard"
    failure = {
        "variant": "full",
        "project_id": "p1",
        "repetition": "0",
        "tool": "crust",
        "workspace_dir": "x",
        "reason": "not collected",
        "detected_at": "now",
    }
    _shard(shard, [], [failure])
    with pytest.raises(RuntimeError, match="unresolved"):
        MERGE.merge_collections(
            [shard],
            tmp_path / "merged",
            manifest={"projects": [{"id": "p1"}]},
            variants=["full"],
            repetitions=1,
            require_raw_complete=True,
        )


def test_merge_collections_repair_raw_row_resolves_prior_failure(
    tmp_path: Path,
) -> None:
    initial = tmp_path / "initial"
    repair = tmp_path / "repair"
    failure = {
        "variant": "full",
        "project_id": "p1",
        "repetition": "0",
        "tool": "crust",
        "workspace_dir": "x",
        "reason": "temporary evaluator failure",
        "detected_at": "now",
    }
    _shard(initial, [], [failure])
    _shard(repair, [_row("full", "p1")])
    summary = MERGE.merge_collections(
        [initial, repair],
        tmp_path / "merged",
        manifest={"projects": [{"id": "p1"}]},
        variants=["full"],
        repetitions=1,
        require_raw_complete=True,
    )
    assert summary["raw_rows"] == 1
    assert summary["unresolved_failures"] == 0
