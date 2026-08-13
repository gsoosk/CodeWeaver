"""Build and verify the Git-ready EvoC2Rust comparison result package."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from experiments.evoc2rust import common as C
from experiments.recodeagent import package_results as PR

EXPECTED_KEYS = {
    (subject_id, repetition)
    for repetition in range(3)
    for subject_id in range(1, 16)
}
TERMINAL_STATUSES = {"completed", "failed", "timeout"}
REQUIRED_EVALUATION_FILES = {
    "evaluation.json",
    "evaluation.csv",
    "integration.csv",
}
REQUIRED_REPORT_FILES = {
    "aggregate.json",
    "availability.csv",
    "comparison.md",
    "comparison.pdf",
    "comparison.tex",
    "fixed_tests.csv",
    "integration_steps.csv",
    "module_results.csv",
    "repetition_metrics.csv",
    "repetitions_figure.pdf",
    "report_manifest.json",
    "summary_figure.pdf",
    "table4_extended.csv",
    "table5_extended.csv",
    "table6_reference.csv",
}


def _csv_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _state_inventory(runs_root: Path) -> list[dict[str, Any]]:
    rows = []
    for subject_id, repetition in sorted(EXPECTED_KEYS):
        path = (
            runs_root
            / "full"
            / str(subject_id)
            / f"rep{repetition}"
            / "recodeagent_run_state.json"
        )
        if not path.is_file():
            rows.append(
                {
                    "subject_id": subject_id,
                    "repetition": repetition,
                    "status": "missing",
                    "state_path": str(path),
                    "error": "run state is absent",
                }
            )
            continue
        state = C.read_json(path)
        provenance = state.get("provenance") or {}
        rows.append(
            {
                "subject_id": subject_id,
                "repetition": repetition,
                "status": state.get("status"),
                "state_path": str(path),
                "state_sha256": C.file_sha256(path),
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
    prepared_manifest: dict[str, Any],
    report_manifest: dict[str, Any],
    evaluation_root: Path,
    report_root: Path,
    runs_root: Path,
) -> dict[str, Any]:
    rows = evaluation.get("rows") or []
    keys = [
        (int(row.get("subject_id", -1)), int(row.get("repetition", -1)))
        for row in rows
    ]
    actual_keys = set(keys)
    duplicate_keys = sorted(key for key in actual_keys if keys.count(key) > 1)
    missing_keys = sorted(EXPECTED_KEYS - actual_keys)
    extra_keys = sorted(actual_keys - EXPECTED_KEYS)
    states = _state_inventory(runs_root)
    nonterminal = [
        row for row in states if row.get("status") not in TERMINAL_STATUSES
    ]
    terminal_runs = len(states) - len(nonterminal)
    integrity_failures = [
        [row.get("subject_id"), row.get("repetition")]
        for row in rows
        if row.get("contract_integrity", {}).get("status") != C.MEASURED
        or row.get("contract_integrity", {}).get("value") is not True
    ]
    terminal_measurement_failures = [
        [row.get("subject_id"), row.get("repetition")]
        for row in rows
        if row.get("terminal_run", {}).get("status") != C.MEASURED
        or row.get("terminal_run", {}).get("value") is not True
    ]
    expected_test_rows = all(
        int(row.get("fixed_tests", {}).get("expected", -1))
        == int(row.get("test_count", -2))
        for row in rows
    )
    integrations = evaluation.get("integration") or []
    integration_repetitions = sorted(
        int(row.get("repetition", -1)) for row in integrations
    )
    calibration = prepared_manifest.get("calibration") or {}
    original = calibration.get("original_c") or {}
    translated = calibration.get("translated_rust_contracts") or {}
    active_arrays = calibration.get("active_test_arrays") or {}
    calibration_valid = (
        original.get("ctest_passed") is True
        and original.get("ctest_total") == 17
        and translated.get("all_contracts_calibrated") is True
        and translated.get("expected_tests") == 125
        and translated.get("original_c_tests_passed") == 125
        and translated.get("c2rust_diagnostic_tests_passed") == 125
        and translated.get("stripped_scaffold_tests_passed") == 0
        and translated.get("ground_truth_retained") is False
        and active_arrays.get("verified") is True
        and active_arrays.get("active_test_count") == 125
    )
    missing_evaluation_files = sorted(
        name
        for name in REQUIRED_EVALUATION_FILES
        if not (evaluation_root / name).is_file()
    )
    missing_report_files = sorted(
        name
        for name in REQUIRED_REPORT_FILES
        if not (report_root / name).is_file()
    )
    pdfs = {
        name: (
            (report_root / name).is_file()
            and (report_root / name).read_bytes()[:5] == b"%PDF-"
        )
        for name in (
            "comparison.pdf",
            "summary_figure.pdf",
            "repetitions_figure.pdf",
        )
    }
    report_statuses_valid = all(
        report_manifest.get(field) == C.MEASURED
        for field in (
            "pdf_status",
            "summary_figure_pdf_status",
            "repetitions_figure_pdf_status",
        )
    )
    csv_counts = {
        "evaluation.csv": _csv_count(evaluation_root / "evaluation.csv"),
        "integration.csv": _csv_count(evaluation_root / "integration.csv"),
        "module_results.csv": _csv_count(report_root / "module_results.csv"),
        "repetition_metrics.csv": _csv_count(
            report_root / "repetition_metrics.csv"
        ),
        "integration_steps.csv": _csv_count(
            report_root / "integration_steps.csv"
        ),
        "table4_extended.csv": _csv_count(
            report_root / "table4_extended.csv"
        ),
        "table5_extended.csv": _csv_count(
            report_root / "table5_extended.csv"
        ),
        "table6_reference.csv": _csv_count(
            report_root / "table6_reference.csv"
        ),
        "availability.csv": _csv_count(report_root / "availability.csv"),
    }
    csv_counts_valid = (
        csv_counts["evaluation.csv"] == 45
        and csv_counts["integration.csv"] == 3
        and csv_counts["module_results.csv"] == 45
        and csv_counts["repetition_metrics.csv"] == 3
        and csv_counts["integration_steps.csv"] == 45
        and csv_counts["table4_extended.csv"] == 24
        and csv_counts["table5_extended.csv"] == 20
        and csv_counts["table6_reference.csv"] == 5
        and csv_counts["availability.csv"] == 7
    )
    execution_git_shas = sorted(
        {
            row["codeweaver_git_sha"]
            for row in states
            if row.get("codeweaver_git_sha")
        }
    )
    complete = (
        evaluation.get("schema_version") == 1
        and prepared_manifest.get("counts_match_expected") is True
        and prepared_manifest.get("counts")
        == {"groups": 15, "modules": 19, "tests": 125}
        and not duplicate_keys
        and not missing_keys
        and not extra_keys
        and not nonterminal
        and not integrity_failures
        and not terminal_measurement_failures
        and expected_test_rows
        and integration_repetitions == [0, 1, 2]
        and calibration_valid
        and not missing_evaluation_files
        and not missing_report_files
        and all(pdfs.values())
        and report_statuses_valid
        and csv_counts_valid
        and len(execution_git_shas) == 1
    )
    return {
        "complete": complete,
        "expected_runs": 45,
        "evaluation_rows": len(rows),
        "terminal_runs": terminal_runs,
        "run_status_counts": {
            status: sum(row.get("status") == status for row in states)
            for status in sorted({str(row.get("status")) for row in states})
        },
        "duplicate_keys": duplicate_keys,
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "nonterminal_runs": nonterminal,
        "contract_integrity_failures": integrity_failures,
        "terminal_measurement_failures": terminal_measurement_failures,
        "expected_test_rows_valid": expected_test_rows,
        "integration_repetitions": integration_repetitions,
        "calibration_valid": calibration_valid,
        "missing_evaluation_files": missing_evaluation_files,
        "missing_report_files": missing_report_files,
        "pdfs": pdfs,
        "report_statuses_valid": report_statuses_valid,
        "csv_counts": csv_counts,
        "csv_counts_valid": csv_counts_valid,
        "execution_git_shas": execution_git_shas,
        "execution_revision_consistent": len(execution_git_shas) == 1,
        "states": states,
    }


def _source_provenance(repository_root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return PR._run_git(repository_root, list(args)).strip()

    status = git("status", "--short", "--untracked-files=no")
    return {
        "repository": "https://github.com/gsoosk/CodeWeaver",
        "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "tracked_worktree_clean": not bool(status),
        "tracked_status": status.splitlines(),
    }


def _environment_lock(path: Path, executable: Path) -> None:
    result = subprocess.run(
        [str(executable), "-m", "pip", "freeze"],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    C.atomic_write_text(
        path,
        result.stdout
        if result.returncode == 0
        else f"pip freeze unavailable: {result.stderr.strip()}\n",
    )


def _archive(
    source: Path,
    destination: Path,
    *,
    prefix: str,
    max_part_bytes: int,
) -> dict[str, Any]:
    archive, file_count = PR.create_filtered_archive(
        source, destination, arc_prefix=prefix
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


def _readme(
    aggregate: dict[str, Any],
    completeness: dict[str, Any],
    archive: dict[str, Any],
    infrastructure_archive: dict[str, Any] | None,
    campaign_file_count: int,
) -> str:
    distributions = aggregate["distributions"]
    return f"""# CodeWeaver - EvoC2Rust Vivo-Bench comparison

This artifact contains the leakage-safe, three-repetition CodeWeaver
comparison with *EvoC2Rust* (DOI `10.1145/3786583.3786856`) on the public
Vivo-Bench revision.

## Headline results

- Terminal measured runs: {completeness['terminal_runs']}/45
- Mean ICompRate: {distributions['incremental_compilation_percent']['mean']:.2f}%
- Mean FCompRate: {distributions['fill_compilation_percent']['mean']:.2f}%
- Mean TestRate: {distributions['test_rate_percent']['mean']:.2f}%
- Mean SafeRate: {distributions['safe_rate_percent']['mean']:.2f}%
- Raw archive files: {archive['file_count']}
- Campaign metadata files: {campaign_file_count}
- Infrastructure-failure evidence: {"archived separately" if infrastructure_archive else "not supplied"}

Read `report/comparison.pdf` first. Exact tables and figures are under
`report/`, normalized measurements under `data/evaluation/`, immutable
prepared contracts under `reproduction/prepared-workspaces/`, and provenance
under `metadata/`. Pre-model failures excluded from the measured matrix are
preserved under `infrastructure-failure-archives/`.

The paper reports 113 Vivo-Bench test cases; the pinned public revision enables
125 test functions. The report preserves this denominator drift. C2R-Bench,
AccRate references, the EvoC2Rust implementation, ablations, and runtime traces
are unreleased, so those experiments are reference-only rather than fabricated.

Verify the artifact from this directory with:

```sh
sha256sum -c metadata/checksums.sha256
```

If the raw archive is split, concatenate numbered parts in lexical order:

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
"""


def build_package(
    *,
    repository_root: Path,
    workspace_root: Path,
    runs_root: Path,
    evaluation_root: Path,
    report_root: Path,
    output_root: Path,
    c2rust_binary: Path | None = None,
    artifact_license: Path | None = None,
    execution_python: Path | None = None,
    campaign_metadata_root: Path | None = None,
    infrastructure_failures_root: Path | None = None,
    max_part_bytes: int = 90 * 1024 * 1024,
    require_complete: bool = False,
) -> dict[str, Any]:
    for label, root in (
        ("campaign metadata", campaign_metadata_root),
        ("infrastructure failures", infrastructure_failures_root),
    ):
        if root is not None and not root.is_dir():
            raise FileNotFoundError(f"{label} directory is absent: {root}")
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    evaluation = C.read_json(evaluation_root / "evaluation.json")
    prepared_manifest = C.read_json(workspace_root / "manifest.json")
    report_manifest = C.read_json(report_root / "report_manifest.json")
    aggregate = C.read_json(report_root / "aggregate.json")
    completeness = validate_completeness(
        evaluation=evaluation,
        prepared_manifest=prepared_manifest,
        report_manifest=report_manifest,
        evaluation_root=evaluation_root,
        report_root=report_root,
        runs_root=runs_root,
    )
    source = _source_provenance(repository_root)
    if require_complete and not completeness["complete"]:
        raise RuntimeError(
            "EvoC2Rust result set is incomplete: "
            + json.dumps(
                {
                    key: value
                    for key, value in completeness.items()
                    if key != "states" and value
                },
                sort_keys=True,
            )
        )
    if require_complete and not source["tracked_worktree_clean"]:
        raise RuntimeError("tracked repository files must be clean")

    copied = {
        "evaluation": PR._copy_tree(
            evaluation_root, output_root / "data/evaluation"
        ),
        "report": PR._copy_tree(report_root, output_root / "report"),
        "prepared_workspaces": PR._copy_tree(
            workspace_root,
            output_root / "reproduction/prepared-workspaces",
        ),
        "source_snapshot": PR._copy_repository_snapshot(
            repository_root, output_root / "reproduction/source"
        ),
        "campaign_metadata": (
            PR._copy_tree(
                campaign_metadata_root,
                output_root / "metadata/campaign",
            )
            if campaign_metadata_root is not None
            else 0
        ),
    }
    for name in ("subjects.json", "experiment.toml", "README.md"):
        PR._copy_file(
            repository_root / "experiments/evoc2rust" / name,
            output_root / "reproduction" / name,
        )
    if artifact_license is not None:
        PR._copy_file(
            artifact_license,
            output_root / "reproduction/vivo-bench-LICENSE",
        )
    tool = None
    if c2rust_binary is not None:
        expected = evaluation["artifact"].get("c2rust_sha256") or (
            evaluation.get("protocol", {}).get("c2rust_sha256")
        )
        actual = C.file_sha256(c2rust_binary)
        PR._copy_file(
            c2rust_binary,
            output_root / "reproduction/tools" / c2rust_binary.name,
        )
        tool = {
            "name": c2rust_binary.name,
            "sha256": actual,
            "bytes": c2rust_binary.stat().st_size,
            "matches_frozen_hash": (
                actual
                == prepared_manifest["tools"]["c2rust"]["sha256"]
            ),
            "expected_from_evaluation": expected,
        }
    if require_complete and (
        tool is None or not tool["matches_frozen_hash"]
    ):
        raise RuntimeError("the pinned C2Rust binary is absent or mismatched")

    C.atomic_write_json(
        output_root / "metadata/source_provenance.json", source
    )
    _environment_lock(
        output_root / "metadata/rendering-python-environment-lock.txt",
        Path(__import__("sys").executable),
    )
    _environment_lock(
        output_root / "metadata/execution-python-environment-lock.txt",
        execution_python or Path(__import__("sys").executable),
    )
    raw_archive = _archive(
        runs_root / "full",
        output_root / "raw-run-archives/full.tar.gz",
        prefix="full",
        max_part_bytes=max_part_bytes,
    )
    infrastructure_archive = (
        _archive(
            infrastructure_failures_root,
            output_root
            / "infrastructure-failure-archives"
            / "excluded-attempts.tar.gz",
            prefix="infrastructure-failures",
            max_part_bytes=max_part_bytes,
        )
        if infrastructure_failures_root is not None
        else None
    )
    manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "paper": evaluation["paper"],
        "artifact": evaluation["artifact"],
        "protocol": evaluation["protocol"],
        "source_provenance": source,
        "completeness": completeness,
        "copied_file_counts": copied,
        "raw_archive": raw_archive,
        "infrastructure_failure_archive": infrastructure_archive,
        "tool": tool,
    }
    C.atomic_write_json(
        output_root / "metadata/package_manifest.json", manifest
    )
    C.atomic_write_text(
        output_root / "README.md",
        _readme(
            aggregate,
            completeness,
            raw_archive,
            infrastructure_archive,
            copied["campaign_metadata"],
        ),
    )
    final = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "verdict": "COMPLETE" if completeness["complete"] else "INCOMPLETE",
        "completeness": completeness,
        "comparison_pdf_valid": (
            output_root / "report/comparison.pdf"
        ).read_bytes()[:5]
        == b"%PDF-",
        "comparison_pdf_sha256": C.file_sha256(
            output_root / "report/comparison.pdf"
        ),
        "summary_figure_pdf_valid": (
            output_root / "report/summary_figure.pdf"
        ).read_bytes()[:5]
        == b"%PDF-",
        "repetitions_figure_pdf_valid": (
            output_root / "report/repetitions_figure.pdf"
        ).read_bytes()[:5]
        == b"%PDF-",
        "raw_archive_files": raw_archive["file_count"],
        "raw_archive_parts": len(raw_archive["parts"]),
        "infrastructure_failure_archive_files": (
            infrastructure_archive["file_count"]
            if infrastructure_archive is not None
            else 0
        ),
        "infrastructure_failure_archive_parts": (
            len(infrastructure_archive["parts"])
            if infrastructure_archive is not None
            else 0
        ),
        "campaign_metadata_files": copied["campaign_metadata"],
        "source_commit": source["git_commit"],
        "tool": tool,
    }
    C.atomic_write_json(
        output_root / "metadata/final_verification.json", final
    )
    PR.write_checksums(output_root)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--evaluation-root", required=True)
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--c2rust-binary")
    parser.add_argument("--artifact-license")
    parser.add_argument("--execution-python")
    parser.add_argument("--campaign-metadata-root")
    parser.add_argument("--infrastructure-failures-root")
    parser.add_argument("--max-part-bytes", type=int, default=90 * 1024 * 1024)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_package(
        repository_root=Path(args.repository_root).resolve(),
        workspace_root=Path(args.workspace_root).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        evaluation_root=Path(args.evaluation_root).resolve(),
        report_root=Path(args.report_root).resolve(),
        output_root=Path(args.out).resolve(),
        c2rust_binary=(
            Path(args.c2rust_binary).resolve() if args.c2rust_binary else None
        ),
        artifact_license=(
            Path(args.artifact_license).resolve()
            if args.artifact_license
            else None
        ),
        execution_python=(
            Path(args.execution_python).resolve()
            if args.execution_python
            else None
        ),
        campaign_metadata_root=(
            Path(args.campaign_metadata_root).resolve()
            if args.campaign_metadata_root
            else None
        ),
        infrastructure_failures_root=(
            Path(args.infrastructure_failures_root).resolve()
            if args.infrastructure_failures_root
            else None
        ),
        max_part_bytes=args.max_part_bytes,
        require_complete=args.require_complete,
    )
    print(
        f"wrote EvoC2Rust result package under {Path(args.out).resolve()} "
        f"({manifest['completeness']['terminal_runs']}/45 terminal runs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
