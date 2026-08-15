"""Archive new runs and write final verification records for five artifacts."""
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path
from typing import Any

from experiments.recodeagent import package_results as PR

from . import common as C
from .config import REPOTRANSBENCH_SUBJECTS, RUSTREPOTRANS_SUBJECTS
from .report import RESULT_NAMES

EXPECTED_RAW_ROWS = {
    "crust": 300,
    "alphatrans": 12,
    "sactor": 150,
    "repotransbench": 9,
    "rustrepotrans": 9,
}
TERMINAL_STATUSES = {"completed", "failed", "timeout"}
REQUIRED_FILES = {
    "README.md",
    "data/raw_runs.csv",
    "data/raw_runs.jsonl",
    "data/summary.json",
    "licenses/CodeWeaver-MIT.txt",
    "metadata/availability.csv",
    "metadata/rendering_environment.json",
    "metadata/report_manifest.json",
    "metadata/source_provenance.json",
    "report/comparison.md",
    "report/comparison.pdf",
    "report/comparison.tex",
    "report/figure.pdf",
    "report/figure.svg",
}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pdf_valid(path: Path) -> bool:
    return (
        path.is_file()
        and path.stat().st_size > 12
        and path.read_bytes()[:5] == b"%PDF-"
    )


def _archive_valid(root: Path, inventory: dict[str, Any] | None) -> bool:
    if inventory is None:
        return True
    raw = inventory.get("raw_runs") or {}
    parts = raw.get("parts") or []
    if int(raw.get("file_count", 0)) <= 0 or not parts:
        return False
    for part in parts:
        path = root / str(part.get("path", ""))
        if (
            not path.is_file()
            or path.stat().st_size != int(part.get("bytes", -1))
            or C.sha256_file(path) != part.get("sha256")
        ):
            return False
    return int(raw.get("withheld_scaffold_files", 0)) > 0


def _state_inventory(
    campaign_root: Path, subjects: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        for repetition in range(3):
            path = (
                campaign_root
                / "runs"
                / "full"
                / subject["id"]
                / f"rep{repetition}"
                / "recodeagent_run_state.json"
            )
            if not path.is_file():
                rows.append(
                    {
                        "subject_id": subject["id"],
                        "repetition": repetition,
                        "status": "missing",
                        "state_path": str(path),
                    }
                )
                continue
            state = C.read_json(path)
            provenance = state.get("provenance") or {}
            rows.append(
                {
                    "subject_id": subject["id"],
                    "repetition": repetition,
                    "status": state.get("status"),
                    "state_path": str(path),
                    "state_sha256": C.sha256_file(path),
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


def _archive(
    source: Path,
    destination: Path,
    *,
    prefix: str,
    max_part_bytes: int,
    predicate=PR.meaningful_run_file,
) -> dict[str, Any]:
    if not source.is_dir():
        raise FileNotFoundError(source)
    for existing in destination.parent.glob(f"{destination.name}*"):
        if existing.is_file():
            existing.unlink()
    archive, file_count = PR.create_filtered_archive(
        source, destination, arc_prefix=prefix, predicate=predicate
    )
    parts = PR.split_file(archive, max_part_bytes)
    return {
        "source": str(source),
        "file_count": file_count,
        "parts": [
            {
                "path": str(path.relative_to(destination.parent.parent)),
                "bytes": path.stat().st_size,
                "sha256": C.sha256_file(path),
            }
            for path in parts
        ],
    }


def _related_run_file(relative: Path) -> bool:
    if not PR.meaningful_run_file(relative):
        return False
    parts = relative.parts
    if any(part in {"scaffold", "oracle", "licenses"} for part in parts):
        return False
    for index, part in enumerate(parts):
        if (
            part == "target"
            and index > 0
            and parts[index - 1] == "pipeline"
        ):
            # Generated Java files/Rust functions are exported separately.
            # Full benchmark/project trees remain acquisition-time inputs.
            return False
    return relative.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}


def _write_withheld_scaffold_hashes(
    campaign_root: Path,
    result_root: Path,
    subjects: list[dict[str, Any]],
) -> int:
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        scaffold = campaign_root / "workspaces" / subject["id"] / "scaffold"
        if not scaffold.is_dir():
            raise FileNotFoundError(scaffold)
        for path in sorted(item for item in scaffold.rglob("*") if item.is_file()):
            relative = path.relative_to(scaffold)
            if "target" in relative.parts:
                continue
            rows.append(
                {
                    "subject_id": subject["id"],
                    "relative_path": f"scaffold/{relative.as_posix()}",
                    "bytes": path.stat().st_size,
                    "sha256": C.sha256_file(path),
                }
            )
    C.write_csv(
        result_root / "metadata" / "withheld_scaffold_manifest.csv",
        rows,
        ["subject_id", "relative_path", "bytes", "sha256"],
    )
    return len(rows)


def package_campaign(
    key: str,
    *,
    campaign_root: Path,
    result_root: Path,
    infrastructure_failures: Path | None,
    max_part_bytes: int,
) -> dict[str, Any]:
    raw_root = result_root / "raw-run-archives"
    archive = _archive(
        campaign_root / "runs",
        raw_root / "full.tar.gz",
        prefix=f"{key}-runs",
        max_part_bytes=max_part_bytes,
        predicate=_related_run_file,
    )
    subjects = (
        REPOTRANSBENCH_SUBJECTS
        if key == "repotransbench"
        else RUSTREPOTRANS_SUBJECTS
    )
    archive["withheld_scaffold_files"] = _write_withheld_scaffold_hashes(
        campaign_root, result_root, subjects
    )
    workspace_manifest = campaign_root / "workspaces" / "manifest.json"
    if not workspace_manifest.is_file():
        raise FileNotFoundError(workspace_manifest)
    metadata_destination = result_root / "metadata" / "campaign_manifest.json"
    metadata_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workspace_manifest, metadata_destination)
    for name in ("pilot-summary.json", "matrix-summary.json"):
        source = campaign_root / name
        if source.is_file():
            shutil.copy2(source, result_root / "metadata" / name)
    infrastructure_archive = None
    if infrastructure_failures is not None and infrastructure_failures.is_dir():
        infrastructure_archive = _archive(
            infrastructure_failures,
            result_root
            / "infrastructure-failure-archives"
            / "python-module-pre-model.tar.gz",
            prefix="python-module-pre-model",
            max_part_bytes=max_part_bytes,
            predicate=_related_run_file,
        )
    return {
        "raw_runs": archive,
        "infrastructure_failures": infrastructure_archive,
    }


def verify_result(
    key: str,
    root: Path,
    *,
    campaign_root: Path | None = None,
    archive_inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = sorted(
        relative for relative in REQUIRED_FILES if not (root / relative).is_file()
    )
    if key in {"repotransbench", "rustrepotrans"}:
        if not (root / "data" / "evaluation_summary.json").is_file():
            missing.append("data/evaluation_summary.json")
        subjects = (
            REPOTRANSBENCH_SUBJECTS
            if key == "repotransbench"
            else RUSTREPOTRANS_SUBJECTS
        )
        for subject in subjects:
            prepared = f"metadata/prepared/{subject['id']}.json"
            if not (root / prepared).is_file():
                missing.append(prepared)
            license_root = root / "licenses" / "subjects" / subject["id"]
            if not any(path.is_file() for path in license_root.glob("*")):
                missing.append(
                    f"licenses/subjects/{subject['id']}/<license>"
                )
        if not (root / "metadata" / "withheld_scaffold_manifest.csv").is_file():
            missing.append("metadata/withheld_scaffold_manifest.csv")
        missing.sort()
    raw_rows = (
        _csv_rows(root / "data" / "raw_runs.csv")
        if (root / "data" / "raw_runs.csv").is_file()
        else []
    )
    expected = EXPECTED_RAW_ROWS[key]
    raw_keys = [
        (
            row.get("subject_id") or row.get("project_id"),
            int(row.get("repetition", -1)),
        )
        for row in raw_rows
    ]
    raw_keys_valid = (
        len(raw_keys) == expected
        and len(set(raw_keys)) == expected
        and {repetition for _, repetition in raw_keys} == {0, 1, 2}
    )
    run_statuses = sorted({row.get("run_status", "") for row in raw_rows})
    run_statuses_valid = bool(raw_rows) and all(
        status in TERMINAL_STATUSES for status in run_statuses
    )
    provenance_path = root / "metadata" / "source_provenance.json"
    provenance = C.read_json(provenance_path) if provenance_path.is_file() else {}
    provenance_valid = bool(
        (provenance.get("codeweaver_source") or {}).get("git_commit")
    )
    if key in {"crust", "alphatrans", "sactor"}:
        provenance_valid = provenance_valid and (
            (provenance.get("reused_campaign_evidence") or {}).get("status")
            == "verified"
        )
    evaluation_statuses = sorted(
        {row.get("evaluation_status", "") for row in raw_rows}
    )
    new_measurements_valid = key not in {
        "repotransbench",
        "rustrepotrans",
    } or evaluation_statuses == ["measured"]
    pdfs = {
        relative: _pdf_valid(root / relative)
        for relative in ("report/comparison.pdf", "report/figure.pdf")
    }
    states: list[dict[str, Any]] = []
    if campaign_root is not None:
        subjects = (
            REPOTRANSBENCH_SUBJECTS
            if key == "repotransbench"
            else RUSTREPOTRANS_SUBJECTS
        )
        states = _state_inventory(campaign_root, subjects)
    state_statuses_valid = not states or (
        len(states) == 9
        and all(row.get("status") in TERMINAL_STATUSES for row in states)
    )
    execution_git_shas = sorted(
        {
            str(row["codeweaver_git_sha"])
            for row in states
            if row.get("codeweaver_git_sha")
        }
    )
    subject_repetitions = {
        (row.get("subject_id"), int(row.get("repetition", -1))) for row in states
    }
    execution_revision_consistent = not states or len(execution_git_shas) == 1
    archive_valid = _archive_valid(root, archive_inventory)
    complete = (
        not missing
        and len(raw_rows) == expected
        and raw_keys_valid
        and run_statuses_valid
        and provenance_valid
        and new_measurements_valid
        and all(pdfs.values())
        and state_statuses_valid
        and (not states or len(subject_repetitions) == 9)
        and execution_revision_consistent
        and archive_valid
    )
    return {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "artifact": root.name,
        "complete": complete,
        "expected_raw_rows": expected,
        "observed_raw_rows": len(raw_rows),
        "raw_keys_valid": raw_keys_valid,
        "run_statuses": run_statuses,
        "run_statuses_valid": run_statuses_valid,
        "provenance_valid": provenance_valid,
        "evaluation_statuses": evaluation_statuses,
        "new_measurements_valid": new_measurements_valid,
        "missing_files": missing,
        "pdfs": pdfs,
        "state_statuses_valid": state_statuses_valid,
        "archive_valid": archive_valid,
        "execution_git_shas": execution_git_shas,
        "execution_revision_consistent": execution_revision_consistent,
        "states": states,
        "archive_inventory": archive_inventory,
        "comparison_pdf_sha256": (
            C.sha256_file(root / "report" / "comparison.pdf")
            if pdfs["report/comparison.pdf"]
            else None
        ),
    }


def package_all(
    *,
    output_root: Path,
    campaign_root: Path,
    infrastructure_failures: Path | None = None,
    max_part_bytes: int = 45_000_000,
) -> list[Path]:
    archives: dict[str, dict[str, Any]] = {}
    for key in ("repotransbench", "rustrepotrans"):
        result_root = output_root / RESULT_NAMES[key]
        archives[key] = package_campaign(
            key,
            campaign_root=campaign_root / key,
            result_root=result_root,
            infrastructure_failures=infrastructure_failures,
            max_part_bytes=max_part_bytes,
        )
    verified: list[Path] = []
    failures: list[str] = []
    for key, result_name in RESULT_NAMES.items():
        root = output_root / result_name
        campaign = (
            campaign_root / key
            if key in {"repotransbench", "rustrepotrans"}
            else None
        )
        verification = verify_result(
            key,
            root,
            campaign_root=campaign,
            archive_inventory=archives.get(key),
        )
        C.atomic_write_json(
            root / "metadata" / "final_verification.json", verification
        )
        C.checksums(root, output=root / "metadata" / "checksums.sha256")
        if not verification["complete"]:
            failures.append(result_name)
        verified.append(root)
    if failures:
        raise ValueError(f"incomplete result artifacts: {', '.join(failures)}")
    return verified


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--campaign-root", required=True)
    parser.add_argument("--infrastructure-failures")
    parser.add_argument("--max-part-bytes", type=int, default=45_000_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    roots = package_all(
        output_root=Path(args.output_root),
        campaign_root=Path(args.campaign_root),
        infrastructure_failures=(
            Path(args.infrastructure_failures)
            if args.infrastructure_failures
            else None
        ),
        max_part_bytes=args.max_part_bytes,
    )
    print("\n".join(str(root) for root in roots))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
