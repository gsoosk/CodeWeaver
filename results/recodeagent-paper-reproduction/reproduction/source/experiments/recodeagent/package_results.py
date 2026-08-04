"""Build the final local Git-ready results repository.

The package contains measured CSV/JSON/PDF outputs, the exact harness source,
checksums/provenance, and compressed raw run outputs with build caches removed.
Official third-party benchmark artifacts are referenced by pinned checksums and
URLs rather than redistributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any, Iterable

from experiments.recodeagent import common as C

ARCHIVE_EXCLUDED_DIRS = {
    ".git",
    ".gradle",
    ".mypy_cache",
    ".nox",
    ".nyc_output",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
ARCHIVE_EXCLUDED_SUFFIXES = {
    ".gcda",
    ".gcno",
    ".o",
    ".obj",
    ".pyc",
    ".rlib",
    ".rmeta",
}
REQUIRED_ANALYSIS_PDFS = (
    "table1_effectiveness.pdf",
    "table1_paper_reference.pdf",
    "table2_test_translation.pdf",
    "figure7_ablation.pdf",
    "figure8_cost_tools.pdf",
    "table_generated_tests.pdf",
    "table_function_validation.pdf",
    "paper_tables_side_by_side.pdf",
)
REQUIRED_ANALYSIS_FILES = (
    "paper_table1_side_by_side.csv",
    "paper_table2_side_by_side.csv",
    "paper_tables_side_by_side_provenance.json",
)


def _run_git(source_root: Path, args: list[str]) -> str:
    result = C.run_argv(["git", "--no-pager", *args], cwd=source_root)
    if not result.ok:
        raise RuntimeError(result.error or result.stderr or result.stdout)
    return result.stdout


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> int:
    count = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in ARCHIVE_EXCLUDED_DIRS for part in relative.parts):
            continue
        if not path.is_file() or path.suffix.lower() in ARCHIVE_EXCLUDED_SUFFIXES:
            continue
        _copy_file(path, destination / relative)
        count += 1
    return count


def meaningful_run_file(relative: Path) -> bool:
    """Whether one run-relative file belongs in the auditable raw archive."""
    parts = relative.parts
    if not parts or any(part in ARCHIVE_EXCLUDED_DIRS for part in parts):
        return False
    if "source" in parts:
        # Benchmark inputs are reproducible from the pinned artifact and are
        # identified by the manifest, not repeated in all 708 run archives.
        return False
    for index, part in enumerate(parts):
        if part != "target":
            continue
        # Preserve pipeline/target (the translated output), but exclude Rust
        # build caches such as pipeline/target/target and scaffold/target.
        if index == 0 or parts[index - 1] != "pipeline":
            return False
    if relative.suffix.lower() in ARCHIVE_EXCLUDED_SUFFIXES:
        return False
    name = relative.name
    if name.startswith(".coverage") or name in {"coverage.out", "coverage-summary.json"}:
        return False
    return True


def create_filtered_archive(
    source: Path,
    archive_path: Path,
    *,
    arc_prefix: str,
    predicate=meaningful_run_file,
) -> tuple[Path, int]:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    included = 0
    with tarfile.open(archive_path, mode="w:gz", compresslevel=6) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            if not predicate(relative):
                continue
            archive.add(
                path,
                arcname=(Path(arc_prefix) / relative).as_posix(),
                recursive=False,
            )
            included += 1
    return archive_path, included


def split_file(path: Path, max_part_bytes: int) -> list[Path]:
    if max_part_bytes <= 0 or path.stat().st_size <= max_part_bytes:
        return [path]
    parts: list[Path] = []
    with path.open("rb") as source:
        index = 0
        while True:
            chunk = source.read(max_part_bytes)
            if not chunk:
                break
            part = path.with_name(f"{path.name}.part-{index:03d}")
            part.write_bytes(chunk)
            parts.append(part)
            index += 1
    path.unlink()
    return parts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(root: Path) -> Path:
    destination = root / "metadata" / "checksums.sha256"
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == destination:
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    C.atomic_write_text(destination, "\n".join(rows) + "\n")
    return destination


def infrastructure_failure_audit(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for state_path in sorted(root.rglob("recodeagent_run_state.json")):
        state = C.read_json_or(state_path, {})
        relative = state_path.relative_to(root)
        rows.append({
            "attempt": relative.parts[0] if relative.parts else "",
            "state_path": relative.as_posix(),
            "state_sha256": _sha256(state_path),
            "variant": state.get("variant"),
            "project_id": state.get("project_id"),
            "repetition": state.get("repetition"),
            "status": state.get("status"),
            "started_at": state.get("started_at"),
            "ended_at": state.get("ended_at"),
            "returncode": state.get("returncode"),
            "num_calls": state.get("num_calls"),
            "error": state.get("error"),
        })
    return rows


def capture_environment(metadata: Path) -> None:
    C.atomic_write_json(
        metadata / "rendering_environment.json",
        C.collect_provenance(
            model=C.PAPER_REFERENCE_MODEL,
            agent_timeout=C.PAPER_AGENT_TIMEOUT_SECONDS,
            probe_toolchains=True,
        ),
    )
    freeze = C.run_argv([sys.executable, "-m", "pip", "freeze"])
    content = freeze.stdout if freeze.ok else (
        f"pip freeze unavailable: {freeze.error or freeze.stderr}\n"
    )
    C.atomic_write_text(metadata / "python-environment-lock.txt", content)


def _copy_repository_snapshot(source_root: Path, destination: Path) -> int:
    tracked = [
        line.strip()
        for line in _run_git(source_root, ["ls-files"]).splitlines()
        if line.strip()
    ]
    count = 0
    for raw_relative in tracked:
        relative = Path(raw_relative)
        source = source_root / relative
        if source.is_file():
            _copy_file(source, destination / relative)
            count += 1
    for relative_root in (
        Path("experiments") / "recodeagent",
        Path("tests"),
    ):
        source = source_root / relative_root
        if source.is_dir():
            count += _copy_tree(source, destination / relative_root)
    return count


def _copy_root_files(source: Path, destination: Path) -> int:
    if not source.is_dir():
        raise FileNotFoundError(source)
    return _copy_tree(source, destination)


def _require_outputs(analysis_root: Path, report_root: Path) -> None:
    invalid: list[str] = []
    paths = [analysis_root / filename for filename in REQUIRED_ANALYSIS_PDFS]
    paths.append(report_root / "reproducibility_report.pdf")
    for path in paths:
        if not path.is_file():
            invalid.append(str(path))
            continue
        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                invalid.append(str(path))
    if invalid:
        raise FileNotFoundError(
            "required valid PDF output(s) missing: " + ", ".join(invalid)
        )
    missing_files = [
        str(analysis_root / filename)
        for filename in REQUIRED_ANALYSIS_FILES
        if not (analysis_root / filename).is_file()
        or (analysis_root / filename).stat().st_size == 0
    ]
    if missing_files:
        raise FileNotFoundError(
            "required analysis output(s) missing: " + ", ".join(missing_files)
        )
    comparison_provenance = C.read_json(
        analysis_root / "paper_tables_side_by_side_provenance.json"
    )
    if not comparison_provenance.get("available", False):
        raise RuntimeError(
            "refusing to package without the exact paper Tables 1/2 "
            "side-by-side comparison"
        )


def _result_readme() -> str:
    return """# CodeWeaver ReCodeAgent experiment results

This repository contains the measured 118-project x 6-variant reproduction of
the experiments in arXiv:2604.07341, including raw normalized data, independent
test/coverage evidence, paper-equivalent tables and figures, PDFs, provenance,
and filtered raw run archives.

- `results/`: final tables, figures, and reproducibility report.
- `results/analysis/paper_tables_side_by_side.pdf`: exact paper Tables 1 and 2
  with the measured CodeWeaver Full result beside every corresponding metric.
- `results/analysis/paper_table{1,2}_side_by_side.csv`: machine-readable
  paper and CodeWeaver values with distinct provenance/status columns.
- `data/`: normalized raw rows and project-level RQ2/generated-test evidence.
- `raw-run-archives/`: split compressed run outputs; concatenate numbered
  parts before extracting when an archive was split.
- `infrastructure-failure-archives/`: excluded retries, retained separately
  so authentication, transport, and interrupted-state decisions are auditable.
- `reproduction/source/`: exact CodeWeaver/harness source snapshot.
- `metadata/checksums.sha256`: SHA-256 for every packaged file.

Official benchmark artifacts are not redistributed. Their pinned Zenodo
record, filenames, and MD5 checksums are recorded in the harness source and
manifest so acquisition remains reproducible.
"""


def package_results(
    *,
    manifest_path: Path,
    collected_root: Path,
    paper_test_root: Path,
    analysis_root: Path,
    report_root: Path,
    runs_root: Path,
    output_root: Path,
    source_root: Path,
    require_complete: bool,
    include_run_archives: bool,
    max_part_bytes: int,
    infrastructure_failures_root: Path | None = None,
) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output root is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    report_data_path = report_root / "reproducibility_report_data.json"
    report_data = C.read_json(report_data_path)
    verdict = report_data.get("verdict") or {}
    if require_complete and not verdict.get("complete"):
        raise RuntimeError(
            "refusing to package an incomplete reproduction: "
            + "; ".join(verdict.get("reasons") or ["completion verdict is false"])
        )
    _require_outputs(analysis_root, report_root)

    copied: dict[str, int] = {}
    copied["collected"] = _copy_root_files(
        collected_root, output_root / "data" / "collected",
    )
    copied["paper_test"] = _copy_root_files(
        paper_test_root, output_root / "data" / "paper-test",
    )
    copied["analysis"] = _copy_root_files(
        analysis_root, output_root / "results" / "analysis",
    )
    copied["report"] = _copy_root_files(
        report_root, output_root / "results" / "report",
    )
    _copy_file(manifest_path, output_root / "data" / "manifest.json")
    manifest_csv = manifest_path.with_suffix(".csv")
    if manifest_csv.is_file():
        _copy_file(manifest_csv, output_root / "data" / "manifest.csv")
    copied["source"] = _copy_repository_snapshot(
        source_root, output_root / "reproduction" / "source",
    )
    run_metadata = output_root / "metadata" / "run-summaries"
    copied["run_metadata"] = 0
    for path in sorted(runs_root.iterdir()):
        if path.is_file() and path.suffix.lower() in {".json", ".log"}:
            _copy_file(path, run_metadata / path.name)
            copied["run_metadata"] += 1

    metadata = output_root / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    C.atomic_write_text(
        metadata / "source-status.txt",
        _run_git(source_root, ["status", "--short"]),
    )
    C.atomic_write_text(
        metadata / "source.patch",
        _run_git(source_root, ["diff", "--binary"]),
    )
    C.atomic_write_text(
        metadata / "source-commit.txt",
        _run_git(source_root, ["rev-parse", "HEAD"]).strip() + "\n",
    )
    capture_environment(metadata)
    C.atomic_write_json(
        metadata / "official-artifacts.json",
        {
            "arxiv_id": C.PAPER_ARXIV_ID,
            "zenodo_record_id": C.ZENODO_RECORD_ID,
            "official_artifact_commit": C.OFFICIAL_ARTIFACT_COMMIT,
            "files": C.OFFICIAL_ARTIFACT_FILES,
        },
    )

    archives: list[dict[str, Any]] = []
    if include_run_archives:
        for variant in C.RUN_VARIANTS:
            source = runs_root / variant
            if not source.is_dir():
                raise FileNotFoundError(source)
            archive, file_count = create_filtered_archive(
                source,
                output_root / "raw-run-archives" / f"{variant}.tar.gz",
                arc_prefix=variant,
            )
            parts = split_file(archive, max_part_bytes)
            archives.append({
                "variant": variant,
                "file_count": file_count,
                "parts": [part.relative_to(output_root).as_posix() for part in parts],
            })

    infrastructure_archives: list[dict[str, Any]] = []
    if infrastructure_failures_root is not None:
        if not infrastructure_failures_root.is_dir():
            raise FileNotFoundError(infrastructure_failures_root)
        C.atomic_write_json(
            metadata / "infrastructure_failure_audit.json",
            {
                "generated_at": C.utcnow_iso(),
                "source_root": str(infrastructure_failures_root),
                "attempts": infrastructure_failure_audit(
                    infrastructure_failures_root
                ),
            },
        )
        for attempt in sorted(infrastructure_failures_root.iterdir()):
            if not attempt.is_dir():
                continue
            archive, file_count = create_filtered_archive(
                attempt,
                output_root
                / "infrastructure-failure-archives"
                / f"{attempt.name}.tar.gz",
                arc_prefix=attempt.name,
            )
            parts = split_file(archive, max_part_bytes)
            infrastructure_archives.append({
                "attempt": attempt.name,
                "file_count": file_count,
                "parts": [
                    part.relative_to(output_root).as_posix() for part in parts
                ],
            })

    C.atomic_write_text(output_root / "README.md", _result_readme())
    package_manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "completion_verdict": verdict,
        "input_paths": {
            "manifest": str(manifest_path),
            "collected_root": str(collected_root),
            "paper_test_root": str(paper_test_root),
            "analysis_root": str(analysis_root),
            "report_root": str(report_root),
            "runs_root": str(runs_root),
            "source_root": str(source_root),
        },
        "copied_file_counts": copied,
        "run_archives": archives,
        "infrastructure_failure_archives": infrastructure_archives,
    }
    C.atomic_write_json(metadata / "package_manifest.json", package_manifest)
    write_checksums(output_root)
    return package_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the final Git-ready results repository with data, PDFs, and raw archives."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--collected-root", required=True)
    parser.add_argument("--paper-test-root", required=True)
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--source-root", default=str(C.REPO_ROOT))
    parser.add_argument("--infrastructure-failures-root")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--skip-run-archives", action="store_true")
    parser.add_argument("--max-part-mib", type=int, default=95)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = package_results(
        manifest_path=Path(args.manifest),
        collected_root=Path(args.collected_root),
        paper_test_root=Path(args.paper_test_root),
        analysis_root=Path(args.analysis_root),
        report_root=Path(args.report_root),
        runs_root=Path(args.runs_root),
        output_root=Path(args.output_root),
        source_root=Path(args.source_root),
        require_complete=args.require_complete,
        include_run_archives=not args.skip_run_archives,
        max_part_bytes=args.max_part_mib * 1024 * 1024,
        infrastructure_failures_root=(
            Path(args.infrastructure_failures_root)
            if args.infrastructure_failures_root
            else None
        ),
    )
    print(
        f"[package-results] wrote {args.output_root}; "
        f"{len(manifest['run_archives'])} run archive(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
