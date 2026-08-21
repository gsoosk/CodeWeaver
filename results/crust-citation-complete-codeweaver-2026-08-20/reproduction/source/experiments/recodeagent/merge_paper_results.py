"""Merge disjoint paper_test_compare.py project shards."""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent import paper_test_compare as PT


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    C.atomic_write_text(path, buffer.getvalue())


def _key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row["variant"]),
        str(row["project_id"]),
        int(row["repetition"]),
    )


def _merge_unique(
    rows: list[dict[str, Any]],
    *,
    label: str,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    merged: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = _key(row)
        existing = merged.get(key)
        if existing is not None and existing != row:
            raise ValueError(f"conflicting {label} row for {key}")
        merged[key] = row
    return merged


def _measured_sum(rows: list[dict[str, Any]], field: str) -> int:
    return sum(
        int(row[field])
        for row in rows
        if row.get(f"{field}_status") == C.Status.MEASURED
    )


def merge_paper_results(
    input_roots: list[Path],
    output_root: Path,
    *,
    manifest: dict[str, Any],
    variants: list[str],
    repetitions: int,
    require_complete: bool,
) -> dict[str, Any]:
    if not input_roots:
        raise ValueError("at least one input root is required")

    project_rows = _merge_unique(
        [
            row
            for root in input_roots
            for row in _read_csv(root / "paper_test_projects.csv")
        ],
        label="paper project",
    )
    generated_rows = _merge_unique(
        [
            row
            for root in input_roots
            for row in _read_jsonl(root / "generated_test_projects.jsonl")
        ],
        label="generated project",
    )
    paper_failures = _merge_unique(
        [
            row
            for root in input_roots
            for row in _read_csv(root / "paper_test_failures.csv")
        ],
        label="paper failure",
    )
    generated_failures = _merge_unique(
        [
            row
            for root in input_roots
            for row in _read_csv(root / "generated_test_failures.csv")
        ],
        label="generated failure",
    )
    for key in set(project_rows) & set(paper_failures):
        del paper_failures[key]
    for key in set(generated_rows) & set(generated_failures):
        del generated_failures[key]

    manifest_rows = list(manifest.get("projects", []))
    expected_generated = {
        (variant, str(row["id"]), repetition)
        for variant in variants
        for row in manifest_rows
        for repetition in range(repetitions)
    }
    expected_paper = {
        (variant, str(row["id"]), repetition)
        for variant in variants
        for row in manifest_rows
        if str(row.get("tool", "")).lower() != "crust"
        for repetition in range(repetitions)
    }
    paper_observed = set(project_rows) | set(paper_failures)
    generated_observed = set(generated_rows) | set(generated_failures)
    paper_missing = sorted(expected_paper - paper_observed)
    generated_missing = sorted(expected_generated - generated_observed)
    unexpected = sorted(
        (paper_observed - expected_paper)
        | (generated_observed - expected_generated)
    )
    if paper_missing or generated_missing or unexpected:
        raise ValueError(
            f"paper shard key mismatch: paper_missing={paper_missing[:10]} "
            f"generated_missing={generated_missing[:10]} "
            f"unexpected={unexpected[:10]}"
        )
    if require_complete and (paper_failures or generated_failures):
        raise RuntimeError(
            f"unresolved paper failures={len(paper_failures)} "
            f"generated failures={len(generated_failures)}"
        )

    variant_order = {variant: index for index, variant in enumerate(variants)}
    project_order = {
        str(row["id"]): index for index, row in enumerate(manifest_rows)
    }
    order = lambda row: (
        variant_order[str(row["variant"])],
        project_order[str(row["project_id"])],
        int(row["repetition"]),
    )
    projects = sorted(project_rows.values(), key=order)
    generated = sorted(generated_rows.values(), key=order)
    paper_failure_rows = sorted(paper_failures.values(), key=order)
    generated_failure_rows = sorted(generated_failures.values(), key=order)

    output_root.mkdir(parents=True, exist_ok=True)
    for root in input_roots:
        for variant in variants:
            source = root / variant
            if source.is_dir():
                shutil.copytree(
                    source,
                    output_root / variant,
                    dirs_exist_ok=True,
                )
    _write_csv(
        output_root / "paper_test_projects.csv",
        projects,
        PT.PROJECT_COLUMNS,
    )
    _write_csv(
        output_root / "paper_test_failures.csv",
        paper_failure_rows,
        PT.FAILURE_COLUMNS,
    )
    _write_csv(
        output_root / "generated_test_projects.csv",
        generated,
        PT.GENERATED_PROJECT_COLUMNS,
    )
    _write_csv(
        output_root / "generated_test_failures.csv",
        generated_failure_rows,
        PT.FAILURE_COLUMNS,
    )
    C.atomic_write_text(
        output_root / "generated_test_projects.jsonl",
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in generated),
    )

    input_summaries = [
        C.read_json(root / "paper_test_summary.json")
        for root in input_roots
        if (root / "paper_test_summary.json").is_file()
    ]
    embedding_models = sorted({
        str(summary["embedding_model"])
        for summary in input_summaries
        if summary.get("embedding_status") == "measured"
        and summary.get("embedding_model")
    })
    summary = {
        "schema_version": PT.SCHEMA_VERSION,
        "generated_at": C.utcnow_iso(),
        "protocol": "Merged ReCodeAgent RQ2 AST comparator and generated-test shards",
        "input_roots": [str(root) for root in input_roots],
        "crust_excluded": True,
        "project_rows": len(projects),
        "failures": len(paper_failure_rows),
        "expected_static_source_methods": sum(
            int(row["static_source_methods"]) for row in projects
        ),
        "observed_static_source_methods": sum(
            int(row["static_source_methods"]) for row in projects
        ),
        "expected_runtime_cases": sum(
            int(row["paper_runtime_tests"]) for row in projects
        ),
        "observed_runtime_cases": sum(
            int(row["paper_runtime_tests"]) for row in projects
        ),
        "mapped_runtime_cases": sum(
            int(row["mapped_runtime_cases"]) for row in projects
        ),
        "generated_target_test_methods": sum(
            int(row["generated_target_test_methods"]) for row in projects
        ),
        "generated_test_project_rows": len(generated),
        "generated_test_failures": len(generated_failure_rows),
        "codeweaver_generated_tests_expected": _measured_sum(
            generated, "generated_tests_expected"
        ),
        "codeweaver_generated_tests_executed": _measured_sum(
            generated, "generated_tests_executed"
        ),
        "codeweaver_generated_tests_passed": _measured_sum(
            generated, "generated_tests_passed"
        ),
        "coverage_before_measured_projects": sum(
            row.get("coverage_before_status") == C.Status.MEASURED
            for row in generated
        ),
        "coverage_after_measured_projects": sum(
            row.get("coverage_after_status") == C.Status.MEASURED
            for row in generated
        ),
        "embedding_model": embedding_models[0] if len(embedding_models) == 1 else None,
        "embedding_status": (
            "measured"
            if len(embedding_models) == 1 and len(projects) == len(expected_paper)
            else "partial_or_unavailable"
        ),
        "complete": not paper_failure_rows and not generated_failure_rows,
    }
    C.atomic_write_json(output_root / "paper_test_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge disjoint paper_test_compare.py shards."
    )
    parser.add_argument("--input-root", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    variants = [item.strip() for item in args.variant.split(",") if item.strip()]
    unknown = sorted(set(variants) - set(C.RUN_VARIANTS))
    if unknown:
        raise ValueError(f"unknown variant(s): {unknown}")
    summary = merge_paper_results(
        [Path(path) for path in args.input_root],
        Path(args.output_root),
        manifest=C.read_json(args.manifest),
        variants=variants,
        repetitions=args.repetitions,
        require_complete=args.require_complete,
    )
    print(
        f"[merge-paper] paper={summary['project_rows']} "
        f"generated={summary['generated_test_project_rows']} "
        f"failures={summary['failures'] + summary['generated_test_failures']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
