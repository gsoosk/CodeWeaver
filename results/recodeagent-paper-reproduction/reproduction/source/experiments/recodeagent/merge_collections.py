"""Merge disjoint collect.py shards without re-evaluating completed runs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from experiments.recodeagent import collect as COL
from experiments.recodeagent import common as C


def _key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row["variant"]),
        str(row["project_id"]),
        int(row["repetition"]),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def merge_collections(
    input_roots: list[Path],
    output_root: Path,
    *,
    manifest: dict[str, Any],
    variants: list[str],
    repetitions: int,
    require_raw_complete: bool,
    replace_keys: set[tuple[str, str, int]] | None = None,
) -> dict[str, Any]:
    if not input_roots:
        raise ValueError("at least one input root is required")

    allowed_replacements = replace_keys or set()
    raw_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    failure_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    duplicate_raw_keys: set[tuple[str, str, int]] = set()
    replaced_raw_keys: set[tuple[str, str, int]] = set()
    for root in input_roots:
        raw_path = root / "raw_runs.jsonl"
        if not raw_path.is_file():
            raise FileNotFoundError(raw_path)
        for row in _read_jsonl(raw_path):
            key = _key(row)
            existing = raw_by_key.get(key)
            if existing is not None:
                duplicate_raw_keys.add(key)
                if existing != row:
                    if key not in allowed_replacements:
                        raise ValueError(f"conflicting raw row for {key}")
                    replaced_raw_keys.add(key)
            raw_by_key[key] = row
        for row in _read_csv(root / "failures.csv"):
            key = _key(row)
            existing = failure_by_key.get(key)
            if existing is not None and (
                existing.get("reason") != row.get("reason")
                or existing.get("workspace_dir") != row.get("workspace_dir")
            ):
                raise ValueError(f"conflicting failure row for {key}")
            failure_by_key[key] = row

    # A focused repair shard is expected to replace an unresolved row from
    # an earlier broad collection. A measured raw row is authoritative.
    for key in set(raw_by_key) & set(failure_by_key):
        del failure_by_key[key]

    project_ids = [str(row["id"]) for row in manifest.get("projects", [])]
    expected = {
        (variant, project_id, repetition)
        for variant in variants
        for project_id in project_ids
        for repetition in range(repetitions)
    }
    observed = set(raw_by_key) | set(failure_by_key)
    unused_replacements = sorted(allowed_replacements - duplicate_raw_keys)
    if unused_replacements:
        raise ValueError(
            "replacement key(s) were not duplicated across raw shards: "
            f"{unused_replacements[:10]}"
        )
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    if missing or unexpected:
        raise ValueError(
            f"collection shard key mismatch: missing={missing[:10]} "
            f"unexpected={unexpected[:10]}"
        )
    if require_raw_complete and failure_by_key:
        raise RuntimeError(
            f"{len(failure_by_key)} unresolved collection failure(s) remain"
        )

    variant_order = {variant: index for index, variant in enumerate(variants)}
    project_order = {project_id: index for index, project_id in enumerate(project_ids)}
    sort_key = lambda row: (
        variant_order[str(row["variant"])],
        project_order[str(row["project_id"])],
        int(row["repetition"]),
    )
    raw_rows = sorted(raw_by_key.values(), key=sort_key)
    failure_rows = sorted(failure_by_key.values(), key=sort_key)
    output_root.mkdir(parents=True, exist_ok=True)
    COL.write_raw_runs(raw_rows, output_root)
    COL.write_failures(failure_rows, output_root)
    summary = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "input_roots": [str(root) for root in input_roots],
        "variants": variants,
        "repetitions": repetitions,
        "expected_cells": len(expected),
        "raw_rows": len(raw_rows),
        "unresolved_failures": len(failure_rows),
        "complete": not failure_rows,
        "allowed_replacement_keys": [
            list(key) for key in sorted(allowed_replacements)
        ],
        "replaced_raw_keys": [
            list(key) for key in sorted(replaced_raw_keys)
        ],
    }
    C.atomic_write_json(output_root / "collection_merge_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge disjoint collect.py output shards with strict cell checks."
    )
    parser.add_argument("--input-root", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--variant", default="all")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--require-raw-complete", action="store_true")
    parser.add_argument(
        "--replace-key",
        action="append",
        default=[],
        metavar="VARIANT:PROJECT_ID:REPETITION",
        help=(
            "explicitly allow a later shard to replace one conflicting raw "
            "row; repeat for each audited evaluator repair"
        ),
    )
    return parser


def _parse_replace_key(value: str) -> tuple[str, str, int]:
    parts = value.rsplit(":", 2)
    if len(parts) != 3 or not parts[0] or not parts[1]:
        raise ValueError(
            f"invalid --replace-key {value!r}; expected VARIANT:PROJECT_ID:REPETITION"
        )
    try:
        repetition = int(parts[2])
    except ValueError as exc:
        raise ValueError(
            f"invalid repetition in --replace-key {value!r}"
        ) from exc
    return parts[0], parts[1], repetition


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    variants = (
        list(C.RUN_VARIANTS)
        if args.variant == "all"
        else [item.strip() for item in args.variant.split(",") if item.strip()]
    )
    unknown = sorted(set(variants) - set(C.RUN_VARIANTS))
    if unknown:
        raise ValueError(f"unknown variant(s): {unknown}")
    summary = merge_collections(
        [Path(path) for path in args.input_root],
        Path(args.output_root),
        manifest=C.read_json(args.manifest),
        variants=variants,
        repetitions=args.repetitions,
        require_raw_complete=args.require_raw_complete,
        replace_keys={_parse_replace_key(value) for value in args.replace_key},
    )
    print(
        f"[merge-collections] {summary['raw_rows']}/{summary['expected_cells']} "
        f"raw rows; {summary['unresolved_failures']} unresolved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
