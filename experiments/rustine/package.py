"""Build and verify the Git-ready Rustine comparison result package."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from experiments.recodeagent import package_results as PR
from experiments.rustine import common as C
from experiments.rustine.report import RUSTINE_ARTIFACT_REPOSITORY

EXPECTED_SUBJECT_IDS = set(range(1, 24))
TERMINAL_RUN_STATUSES = {"completed", "failed", "timeout"}
REQUIRED_EVALUATION_FILES = {"evaluation.json", "evaluation.csv"}
REQUIRED_REPORT_FILES = {
    "aggregate.json",
    "comparison.md",
    "comparison.pdf",
    "comparison.tex",
    "report_manifest.json",
    "safety.csv",
    "summary.csv",
    "summary_figure.pdf",
    "statistics.csv",
    "validation.csv",
}


def _copy_tree(source: Path, destination: Path) -> int:
    if not source.is_dir():
        raise FileNotFoundError(source)
    return PR._copy_tree(source, destination)


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    PR._copy_file(source, destination)


def _run_git(repository_root: Path, *args: str) -> str:
    return PR._run_git(repository_root, list(args)).strip()


def _state_inventory(runs_root: Path) -> list[dict[str, Any]]:
    rows = []
    for subject_id in sorted(EXPECTED_SUBJECT_IDS):
        state_path = (
            runs_root
            / "full"
            / str(subject_id)
            / "rep0"
            / "recodeagent_run_state.json"
        )
        if not state_path.is_file():
            rows.append(
                {
                    "subject_id": subject_id,
                    "state_path": str(state_path),
                    "status": "missing",
                    "error": "run state is absent",
                }
            )
            continue
        state = C.read_json(state_path)
        provenance = state.get("provenance") or {}
        rows.append(
            {
                "subject_id": subject_id,
                "state_path": str(state_path),
                "state_sha256": C.file_sha256(state_path),
                "status": state.get("status"),
                "app_id": state.get("app_id"),
                "attempt": state.get("attempt"),
                "started_at": state.get("started_at"),
                "ended_at": state.get("ended_at"),
                "returncode": state.get("returncode"),
                "error": state.get("error", ""),
                "codeweaver_git_sha": (
                    (provenance.get("git_sha") or {}).get("value")
                ),
                "copilot_cli_version": (
                    (provenance.get("copilot_cli_version") or {}).get("value")
                ),
            }
        )
    return rows


def validate_completeness(
    *,
    evaluation: dict[str, Any],
    report_manifest: dict[str, Any],
    evaluation_root: Path,
    report_root: Path,
    runs_root: Path,
) -> dict[str, Any]:
    rows = evaluation.get("rows")
    if not isinstance(rows, list):
        raise ValueError("evaluation rows are missing")
    keys = [
        (row.get("subject_id"), row.get("variant"), row.get("repetition"))
        for row in rows
    ]
    expected_keys = {(subject_id, "full", 0) for subject_id in EXPECTED_SUBJECT_IDS}
    actual_keys = set(keys)
    duplicate_keys = sorted(key for key in actual_keys if keys.count(key) > 1)
    missing_keys = sorted(expected_keys - actual_keys)
    extra_keys = sorted(actual_keys - expected_keys)

    states = _state_inventory(runs_root)
    execution_git_shas = sorted(
        {
            row["codeweaver_git_sha"]
            for row in states
            if row.get("codeweaver_git_sha")
        }
    )
    states_by_subject = {row["subject_id"]: row for row in states}
    nonterminal = [
        row for row in states if row.get("status") not in TERMINAL_RUN_STATUSES
    ]
    completion_mismatches = []
    for row in rows:
        subject_id = row.get("subject_id")
        state = states_by_subject.get(subject_id, {})
        metric = row.get("run_completion", {})
        expected = state.get("status") == "completed"
        if metric.get("status") != C.MEASURED or metric.get("value") is not expected:
            completion_mismatches.append(
                {
                    "subject_id": subject_id,
                    "run_status": state.get("status"),
                    "evaluation_run_completion": metric,
                }
            )
    integrity_failures = [
        row.get("subject_id")
        for row in rows
        if row.get("contract_integrity", {}).get("status") != C.MEASURED
        or row.get("contract_integrity", {}).get("value") is not True
    ]
    missing_evaluation_files = sorted(
        name for name in REQUIRED_EVALUATION_FILES if not (evaluation_root / name).is_file()
    )
    missing_report_files = sorted(
        name for name in REQUIRED_REPORT_FILES if not (report_root / name).is_file()
    )
    pdf_path = report_root / "comparison.pdf"
    pdf_valid = pdf_path.is_file() and pdf_path.read_bytes()[:5] == b"%PDF-"
    figure_path = report_root / "summary_figure.pdf"
    figure_pdf_valid = (
        figure_path.is_file() and figure_path.read_bytes()[:5] == b"%PDF-"
    )
    pdf_measured = report_manifest.get("pdf_status") == C.MEASURED
    figure_pdf_measured = (
        report_manifest.get("summary_figure_pdf_status") == C.MEASURED
    )
    evaluation_schema_valid = evaluation.get("schema_version") == 2

    def csv_rows(name: str) -> int | None:
        path = report_root / name
        if not path.is_file():
            return None
        with path.open(encoding="utf-8", newline="") as handle:
            return sum(1 for _ in csv.DictReader(handle))

    report_csv_rows = {
        "validation.csv": csv_rows("validation.csv"),
        "safety.csv": csv_rows("safety.csv"),
        "statistics.csv": csv_rows("statistics.csv"),
    }
    report_row_counts_valid = report_csv_rows == {
        "validation.csv": 23,
        "safety.csv": 23,
        "statistics.csv": 2,
    }
    evaluation_csv_path = evaluation_root / "evaluation.csv"
    if evaluation_csv_path.is_file():
        with evaluation_csv_path.open(encoding="utf-8", newline="") as handle:
            evaluation_csv_rows = sum(1 for _ in csv.DictReader(handle))
    else:
        evaluation_csv_rows = None
    evaluation_csv_rows_valid = evaluation_csv_rows == 23
    complete = not any(
        (
            duplicate_keys,
            missing_keys,
            extra_keys,
            nonterminal,
            completion_mismatches,
            integrity_failures,
            [] if len(execution_git_shas) == 1 else ["execution Git SHA drift"],
            missing_evaluation_files,
            missing_report_files,
            [] if evaluation_schema_valid else ["evaluation schema"],
            [] if report_row_counts_valid else ["report CSV row counts"],
            [] if evaluation_csv_rows_valid else ["evaluation CSV row count"],
        )
    ) and pdf_valid and pdf_measured and figure_pdf_valid and figure_pdf_measured
    return {
        "complete": complete,
        "expected_runs": 23,
        "evaluation_rows": len(rows),
        "evaluation_schema_valid": evaluation_schema_valid,
        "evaluation_csv_rows": evaluation_csv_rows,
        "evaluation_csv_rows_valid": evaluation_csv_rows_valid,
        "report_csv_rows": report_csv_rows,
        "report_row_counts_valid": report_row_counts_valid,
        "duplicate_keys": duplicate_keys,
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "terminal_runs": sum(
            row.get("status") in TERMINAL_RUN_STATUSES for row in states
        ),
        "run_status_counts": {
            status: sum(row.get("status") == status for row in states)
            for status in sorted(
                {str(row.get("status")) for row in states}
            )
        },
        "execution_git_shas": execution_git_shas,
        "execution_revision_consistent": len(execution_git_shas) == 1,
        "nonterminal_runs": nonterminal,
        "run_completion_mismatches": completion_mismatches,
        "contract_integrity_failures": integrity_failures,
        "missing_evaluation_files": missing_evaluation_files,
        "missing_report_files": missing_report_files,
        "pdf_status": report_manifest.get("pdf_status"),
        "pdf_valid": pdf_valid,
        "summary_figure_pdf_status": report_manifest.get(
            "summary_figure_pdf_status"
        ),
        "summary_figure_pdf_valid": figure_pdf_valid,
        "states": states,
    }


def _archive_record(
    source: Path,
    archive_path: Path,
    *,
    arc_prefix: str,
    max_part_bytes: int,
) -> dict[str, Any]:
    archive, file_count = PR.create_filtered_archive(
        source, archive_path, arc_prefix=arc_prefix
    )
    parts = PR.split_file(archive, max_part_bytes)
    return {
        "source": str(source),
        "file_count": file_count,
        "parts": [
            {
                "path": part.name,
                "bytes": part.stat().st_size,
                "sha256": C.file_sha256(part),
            }
            for part in parts
        ],
    }


def _copy_campaign_metadata(campaign_root: Path, destination: Path) -> int:
    count = 0
    paths = list(campaign_root.glob("*summary.json"))
    paths.extend(
        campaign_root / name
        for name in (
            "final-analysis-ready.json",
            "full-test-results.xml",
            "test-environment-lock.txt",
        )
    )
    for path in sorted(set(paths)):
        if path.is_file():
            _copy_file(path, destination / path.name)
            count += 1
    for name in ("pilot-evaluation",):
        source = campaign_root / name
        if source.is_dir():
            count += _copy_tree(source, destination / name)
    return count


def _source_provenance(repository_root: Path) -> dict[str, Any]:
    tracked_status = _run_git(
        repository_root, "status", "--short", "--untracked-files=no"
    )
    return {
        "git_commit": _run_git(repository_root, "rev-parse", "HEAD"),
        "git_branch": _run_git(repository_root, "branch", "--show-current"),
        "tracked_worktree_clean": not bool(tracked_status),
        "tracked_status": tracked_status.splitlines(),
        "repository": "https://github.com/gsoosk/CodeWeaver",
    }


def _test_evidence(campaign_root: Path) -> dict[str, Any]:
    path = campaign_root / "full-test-results.xml"
    lock = campaign_root / "test-environment-lock.txt"
    if not path.is_file() or not lock.is_file():
        return {
            "complete": False,
            "reason": "full-test-results.xml or test-environment-lock.txt is absent",
        }
    root = ET.parse(path).getroot()
    suite = root if root.tag.endswith("testsuite") else root.find("testsuite")
    if suite is None:
        return {"complete": False, "reason": "JUnit XML contains no testsuite"}
    totals = {
        field: int(suite.attrib.get(field, 0))
        for field in ("tests", "errors", "failures", "skipped")
    }
    totals["passed"] = (
        totals["tests"]
        - totals["errors"]
        - totals["failures"]
        - totals["skipped"]
    )
    return {
        "complete": totals["errors"] == 0 and totals["failures"] == 0,
        **totals,
        "junit_sha256": C.file_sha256(path),
        "environment_lock_sha256": C.file_sha256(lock),
    }


def _environment_lock(destination: Path, python_executable: str | Path) -> None:
    result = subprocess.run(
        [str(python_executable), "-m", "pip", "freeze"],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    text = result.stdout if result.returncode == 0 else (
        f"pip freeze unavailable: {result.stderr.strip()}\n"
    )
    C.atomic_write_text(destination, text)


def _readme(
    aggregate: dict[str, Any],
    completeness: dict[str, Any],
    raw_archive: dict[str, Any],
) -> str:
    codeweaver = aggregate["codeweaver"]
    paper = aggregate["paper"]
    part_names = [part["path"] for part in raw_archive["parts"]]
    return f"""# CodeWeaver - Rustine same-subject comparison

This package reports the leakage-aware 23-subject C-to-Rust comparison with
Rustine ([arXiv:2511.20617](https://arxiv.org/abs/2511.20617)). Rustine values
are the paper's published reference values; CodeWeaver values are independently
measured from the immutable disclosed contracts.

## Headline inventory

- Terminal CodeWeaver runs: {completeness['terminal_runs']}/23
- CodeWeaver compilations: {codeweaver['compiled']}/23
- CodeWeaver fixed-contract passes: {codeweaver['fixed_contract_passed']}/{paper['testable_subjects']} testable
- Rustine paper compilation reference: {paper['compilation_success']}/23
- Raw archive files: {raw_archive['file_count']}
- Raw archive parts: {len(part_names)}

The primary human-readable output is `report/comparison.pdf`, with the headline
chart in `report/summary_figure.pdf`. Exact companion tables are under
`report/`, normalized measurements under `data/evaluation/`, and
provenance/checksums under `metadata/`.

Verify all packaged bytes from the package root with:

```sh
sha256sum -c metadata/checksums.sha256
```

## Raw archive reconstruction

If multiple numbered parts are present, concatenate them in lexical order to
recover `full.tar.gz`, then extract it. On POSIX:

```sh
cat raw-run-archives/full.tar.gz.part-* > full.tar.gz
tar -xzf full.tar.gz
```

On PowerShell:

```powershell
$parts = Get-ChildItem raw-run-archives\\full.tar.gz.part-* | Sort-Object Name
$out = [IO.File]::Create('full.tar.gz')
try {{ foreach ($part in $parts) {{ $bytes = [IO.File]::ReadAllBytes($part); $out.Write($bytes) }} }}
finally {{ $out.Dispose() }}
tar -xzf full.tar.gz
```

No Rustine production translation is redistributed or exposed to CodeWeaver.
The [official artifact]({RUSTINE_ARTIFACT_REPOSITORY}) is identified by its
pinned commit in `reproduction/prepared_manifest.json`.
"""


def build_package(
    *,
    repository_root: Path,
    campaign_root: Path,
    workspace_root: Path,
    runs_root: Path,
    evaluation_root: Path,
    report_root: Path,
    output_root: Path,
    infrastructure_failures_root: Path | None = None,
    tool_binary: Path | None = None,
    artifact_license: Path | None = None,
    execution_python: Path | None = None,
    max_part_bytes: int = 90 * 1024 * 1024,
    require_complete: bool = False,
) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    evaluation = C.read_json(evaluation_root / "evaluation.json")
    report_manifest = C.read_json(report_root / "report_manifest.json")
    aggregate = C.read_json(report_root / "aggregate.json")
    completeness = validate_completeness(
        evaluation=evaluation,
        report_manifest=report_manifest,
        evaluation_root=evaluation_root,
        report_root=report_root,
        runs_root=runs_root,
    )
    source_provenance = _source_provenance(repository_root)
    test_evidence = _test_evidence(campaign_root)
    if require_complete and not completeness["complete"]:
        raise RuntimeError(
            "Rustine result set is incomplete: "
            + json.dumps(
                {
                    key: value
                    for key, value in completeness.items()
                    if key != "states" and value
                },
                sort_keys=True,
            )
        )
    if require_complete and not source_provenance["tracked_worktree_clean"]:
        raise RuntimeError("tracked repository files must be clean before final packaging")
    if require_complete and not test_evidence["complete"]:
        raise RuntimeError(f"full test evidence is incomplete: {test_evidence}")

    copied = {
        "evaluation": _copy_tree(evaluation_root, output_root / "data" / "evaluation"),
        "report": _copy_tree(report_root, output_root / "report"),
        "campaign_metadata": _copy_campaign_metadata(
            campaign_root, output_root / "metadata" / "campaign"
        ),
    }
    _copy_file(
        workspace_root / "manifest.json",
        output_root / "reproduction" / "prepared_manifest.json",
    )
    _copy_file(
        repository_root / "experiments" / "rustine" / "subjects.json",
        output_root / "reproduction" / "subjects.json",
    )
    _copy_file(
        repository_root / "experiments" / "rustine" / "experiment.toml",
        output_root / "reproduction" / "experiment.toml",
    )
    if artifact_license is not None:
        _copy_file(
            artifact_license,
            output_root / "reproduction" / "rustine-artifact-LICENSE",
        )

    copied["source_snapshot"] = PR._copy_repository_snapshot(
        repository_root, output_root / "reproduction" / "source"
    )
    C.atomic_write_json(
        output_root / "metadata" / "source_provenance.json", source_provenance
    )
    _environment_lock(
        output_root / "metadata" / "rendering-python-environment-lock.txt",
        sys.executable,
    )
    _environment_lock(
        output_root / "metadata" / "execution-python-environment-lock.txt",
        execution_python or Path(sys.executable),
    )

    raw_archive = _archive_record(
        runs_root / "full",
        output_root / "raw-run-archives" / "full.tar.gz",
        arc_prefix="full",
        max_part_bytes=max_part_bytes,
    )
    infrastructure_archives = []
    infrastructure_audit = []
    if infrastructure_failures_root is not None and infrastructure_failures_root.is_dir():
        infrastructure_audit = PR.infrastructure_failure_audit(
            infrastructure_failures_root
        )
        pre_model_markers = (
            "No module named codeweaver",
            "No module named 'burr'",
            "Missing plugin tracking",
        )
        for row in infrastructure_audit:
            state_path = infrastructure_failures_root / row["state_path"]
            run_dir = state_path.parent
            copilot_logs = (
                list((run_dir / "pipeline" / "logs").rglob("*.stdout.jsonl"))
                if (run_dir / "pipeline" / "logs").is_dir()
                else []
            )
            row["copilot_log_count"] = len(copilot_logs)
            row["classification"] = (
                "infrastructure_pre_model"
                if not copilot_logs
                and any(marker in str(row.get("error", "")) for marker in pre_model_markers)
                else "requires_manual_review"
            )
        if require_complete and any(
            row["classification"] != "infrastructure_pre_model"
            for row in infrastructure_audit
        ):
            raise RuntimeError(
                "an excluded infrastructure attempt lacks pre-model evidence"
            )
        for attempt in sorted(
            path for path in infrastructure_failures_root.iterdir() if path.is_dir()
        ):
            infrastructure_archives.append(
                {
                    "attempt": attempt.name,
                    **_archive_record(
                        attempt,
                        output_root
                        / "infrastructure-failure-archives"
                        / f"{attempt.name}.tar.gz",
                        arc_prefix=attempt.name,
                        max_part_bytes=max_part_bytes,
                    ),
                }
            )
        C.atomic_write_json(
            output_root / "metadata" / "infrastructure_failure_audit.json",
            infrastructure_audit,
        )

    tool = None
    if tool_binary is not None:
        _copy_file(
            tool_binary, output_root / "reproduction" / "tools" / tool_binary.name
        )
        tool = {
            "name": tool_binary.name,
            "sha256": C.file_sha256(tool_binary),
            "bytes": tool_binary.stat().st_size,
        }
    expected_tool_sha256 = evaluation.get("protocol", {}).get(
        "cargo_newmetrics_sha256"
    )
    if require_complete and (
        tool is None or tool["sha256"] != expected_tool_sha256
    ):
        raise RuntimeError(
            "cargo-newmetrics is absent or does not match the frozen protocol hash"
        )

    package_manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "paper": evaluation.get("paper"),
        "artifact": {
            **(evaluation.get("artifact") or {}),
            "repository": RUSTINE_ARTIFACT_REPOSITORY,
        },
        "protocol": evaluation.get("protocol"),
        "source_provenance": source_provenance,
        "test_evidence": test_evidence,
        "completeness": completeness,
        "copied_file_counts": copied,
        "raw_archive": raw_archive,
        "infrastructure_archives": infrastructure_archives,
        "infrastructure_failure_rows": len(infrastructure_audit),
        "tool": tool,
    }
    C.atomic_write_json(
        output_root / "metadata" / "package_manifest.json", package_manifest
    )
    C.atomic_write_text(
        output_root / "README.md",
        _readme(aggregate, completeness, raw_archive),
    )
    final_verification = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "verdict": "COMPLETE" if completeness["complete"] else "INCOMPLETE",
        "completeness": completeness,
        "comparison_pdf_sha256": C.file_sha256(output_root / "report" / "comparison.pdf"),
        "comparison_pdf_valid": (
            output_root / "report" / "comparison.pdf"
        ).read_bytes()[:5]
        == b"%PDF-",
        "summary_figure_pdf_sha256": C.file_sha256(
            output_root / "report" / "summary_figure.pdf"
        ),
        "summary_figure_pdf_valid": (
            output_root / "report" / "summary_figure.pdf"
        ).read_bytes()[:5]
        == b"%PDF-",
        "raw_archive_parts": len(raw_archive["parts"]),
        "raw_archive_files": raw_archive["file_count"],
        "source_commit": source_provenance["git_commit"],
        "test_evidence": test_evidence,
        "tool": tool,
    }
    C.atomic_write_json(
        output_root / "metadata" / "final_verification.json", final_verification
    )
    PR.write_checksums(output_root)
    return package_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--campaign-root", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--evaluation-root", required=True)
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--infrastructure-failures-root")
    parser.add_argument("--tool-binary")
    parser.add_argument("--artifact-license")
    parser.add_argument("--execution-python")
    parser.add_argument("--max-part-bytes", type=int, default=90 * 1024 * 1024)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_package(
        repository_root=Path(args.repository_root).resolve(),
        campaign_root=Path(args.campaign_root).resolve(),
        workspace_root=Path(args.workspace_root).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        evaluation_root=Path(args.evaluation_root).resolve(),
        report_root=Path(args.report_root).resolve(),
        output_root=Path(args.out).resolve(),
        infrastructure_failures_root=(
            Path(args.infrastructure_failures_root).resolve()
            if args.infrastructure_failures_root
            else None
        ),
        tool_binary=Path(args.tool_binary).resolve() if args.tool_binary else None,
        artifact_license=(
            Path(args.artifact_license).resolve() if args.artifact_license else None
        ),
        execution_python=(
            Path(args.execution_python).resolve() if args.execution_python else None
        ),
        max_part_bytes=args.max_part_bytes,
        require_complete=args.require_complete,
    )
    print(
        f"wrote Rustine result package under {Path(args.out).resolve()} "
        f"({manifest['completeness']['terminal_runs']}/23 terminal runs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
