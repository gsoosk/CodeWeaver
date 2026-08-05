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
import re
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
REQUIRED_BASELINE_FILES = (
    "baseline_raw_runs.jsonl",
    "baseline_raw_runs.csv",
    "baseline_failures.csv",
    "baseline_replay_summary.json",
    "baseline_replay_provenance.json",
)
REQUIRED_SYSTEM_COMPARISON_FILES = (
    "system_comparison.json",
    "system_comparison_inventory.csv",
    "system_comparison_metrics.csv",
    "system_comparison_paired.csv",
    "system_comparison_crust_overlap.csv",
    "system_comparison_cost_frontier.csv",
    "system_comparison_failure_evidence.csv",
    "system_comparison_tables.tex",
    "system_comparison_provenance.json",
)
REQUIRED_SYSTEM_COMPARISON_PDF = "system_comparison.pdf"
SNAPSHOT_EXCLUDED_TOP_LEVEL_DIRS = {"results", "raw-run-archives"}


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
        if relative.parts and relative.parts[0] in SNAPSHOT_EXCLUDED_TOP_LEVEL_DIRS:
            continue
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


def _destination_label(root: Path) -> str:
    """Produce a stable, portable destination label from an input root name."""
    label = C.slugify(root.resolve().name)
    if not label:
        raise ValueError(f"could not derive a destination label from {root}")
    return label


def _labelled_roots(
    roots: Iterable[Path] | None,
    *,
    kind: str,
) -> list[tuple[str, Path]]:
    labelled: list[tuple[str, Path]] = []
    labels: set[str] = set()
    for root in roots or ():
        path = Path(root)
        if not path.is_dir():
            raise FileNotFoundError(path)
        label = _destination_label(path)
        if label in labels:
            raise ValueError(
                f"duplicate {kind} destination label {label!r}; rename one input root"
            )
        labels.add(label)
        labelled.append((label, path))
    return labelled


def _require_baseline_root(root: Path) -> None:
    missing = [
        str(root / filename)
        for filename in REQUIRED_BASELINE_FILES
        if not (root / filename).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "baseline replay root is incomplete; required file(s) missing: "
            + ", ".join(missing)
        )


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    value = C.read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return value


def _valid_pdf(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def _system_comparison_completeness(data: dict[str, Any]) -> dict[str, Any]:
    """Gate only unaccounted missing/error comparison cells.

    Current comparison artifacts expose per-inventory missing components and
    a checked aggregate. Older artifacts only have ``missing``. For those,
    retained, non-conflicting failure evidence can still verify that a
    missing cell was explicitly accounted for; otherwise the legacy cell is
    conservatively treated as unaccounted.
    """
    inventory = data.get("inventory")
    if not isinstance(inventory, list) or not all(isinstance(row, dict) for row in inventory):
        raise ValueError(
            "system comparison JSON has no valid inventory list; cannot audit comparison completeness"
        )

    count_fields = ("expected", "measured", "unavailable", "error", "missing")
    totals = {key: 0 for key in count_fields}
    accounted_missing = 0
    unaccounted_missing = 0
    current_accounting = any(
        "accounted_missing" in row or "unaccounted_missing" in row
        for row in inventory
    )
    for row in inventory:
        row_counts: dict[str, int] = {}
        for key in count_fields:
            value = row.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"system comparison inventory has invalid {key} value {value!r}"
                )
            row_counts[key] = value
            totals[key] += value
        if current_accounting:
            if "accounted_missing" not in row or "unaccounted_missing" not in row:
                raise ValueError(
                    "system comparison inventory mixes current and legacy missing accounting"
                )
            row_accounted = row["accounted_missing"]
            row_unaccounted = row["unaccounted_missing"]
            for key, value in (
                ("accounted_missing", row_accounted),
                ("unaccounted_missing", row_unaccounted),
            ):
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(
                        f"system comparison inventory has invalid {key} value {value!r}"
                    )
            if row_accounted + row_unaccounted != row_counts["missing"]:
                raise ValueError(
                    "system comparison inventory missing accounting does not sum to missing"
                )
        else:
            evidence = row.get("failure_evidence_rows")
            conflicts = row.get("conflicting_failure_evidence_rows")
            if (
                isinstance(evidence, int)
                and not isinstance(evidence, bool)
                and evidence >= 0
                and isinstance(conflicts, int)
                and not isinstance(conflicts, bool)
                and 0 <= conflicts <= evidence
            ):
                # In legacy inventory, unavailable/error cells consume their
                # own retained failure evidence. Only the remainder can prove
                # missing cells explicitly accounted for.
                verified_missing = max(
                    0,
                    evidence - conflicts - row_counts["unavailable"] - row_counts["error"],
                )
                row_accounted = min(row_counts["missing"], verified_missing)
            else:
                row_accounted = 0
            row_unaccounted = row_counts["missing"] - row_accounted
        accounted_missing += row_accounted
        unaccounted_missing += row_unaccounted

    totals["accounted_missing"] = accounted_missing
    totals["unaccounted_missing"] = unaccounted_missing
    aggregate = data.get("inventory_completeness")
    if aggregate is not None:
        if not isinstance(aggregate, dict):
            raise ValueError("system comparison inventory_completeness must be an object")
        for key, value in totals.items():
            aggregate_value = aggregate.get(key)
            if aggregate_value != value:
                raise ValueError(
                    f"system comparison inventory_completeness {key} does not match inventory"
                )
        if aggregate.get("all_expected_cells_accounted_for") != (unaccounted_missing == 0):
            raise ValueError(
                "system comparison inventory_completeness accounting flag does not match inventory"
            )
    overlap = data.get("crust_three_system_overlap")
    overlap_status = overlap.get("status") if isinstance(overlap, dict) else None
    has_unaccounted_or_error = bool(unaccounted_missing or totals["error"])
    explicit_unavailability = bool(
        totals["unavailable"] or overlap_status == C.Status.UNAVAILABLE
    )
    has_accounted_missing = bool(accounted_missing)
    return {
        "status": (
            "incomplete_unaccounted_missing_or_error"
            if has_unaccounted_or_error
            else (
                "complete_with_explicit_unavailability_and_accounted_missing"
                if explicit_unavailability and has_accounted_missing
                else (
                    "complete_with_explicit_unavailability"
                    if explicit_unavailability
                    else (
                        "complete_with_accounted_missing"
                        if has_accounted_missing
                        else "complete"
                    )
                )
            )
        ),
        "complete": not has_unaccounted_or_error,
        "inventory_totals": totals,
        "explicit_unavailability_count": totals["unavailable"],
        "missing_artifact_cell_count": totals["missing"],
        "accounted_missing_artifact_cell_count": accounted_missing,
        "unaccounted_missing_artifact_cell_count": unaccounted_missing,
        "error_cell_count": totals["error"],
        "crust_overlap_status": overlap_status,
        "note": (
            "Explicit unavailable replay/workbook evidence and accounted released-artifact "
            "absence are retained as such; unaccounted missing cells and errors are rejected."
        ),
    }


def _require_system_comparison_root(root: Path) -> dict[str, Any]:
    missing = [
        str(root / filename)
        for filename in REQUIRED_SYSTEM_COMPARISON_FILES
        if not (root / filename).is_file()
        or (root / filename).stat().st_size == 0
    ]
    pdf = root / REQUIRED_SYSTEM_COMPARISON_PDF
    if not _valid_pdf(pdf):
        missing.append(str(pdf))
    if missing:
        raise FileNotFoundError(
            "system-comparison root is incomplete; required valid output(s) missing: "
            + ", ".join(missing)
        )
    data = _read_json_object(root / "system_comparison.json", label="system comparison JSON")
    _read_json_object(
        root / "system_comparison_provenance.json",
        label="system comparison provenance",
    )
    return _system_comparison_completeness(data)


def _require_campaign_metadata_root(root: Path) -> None:
    """Reject run workspaces: campaign metadata may contain only logs/summaries."""
    if any(root.rglob("recodeagent_run_state.json")):
        raise ValueError(
            f"campaign metadata root contains recodeagent_run_state.json run state: {root}"
        )
    run_variants = set(C.RUN_VARIANTS)
    for child in root.iterdir():
        if child.is_dir() and child.name in run_variants:
            raise ValueError(
                f"campaign metadata root contains run-variant directory {child}: {root}"
            )
    rep_pattern = re.compile(r"rep\d+$")
    for directory in root.rglob("*"):
        if not directory.is_dir() or not rep_pattern.fullmatch(directory.name):
            continue
        if any(part in run_variants for part in directory.relative_to(root).parts):
            raise ValueError(
                f"campaign metadata root contains run directory {directory}: {root}"
            )


def _validate_variants(variants: list[str] | None) -> list[str]:
    selected = list(C.RUN_VARIANTS) if variants is None else list(variants)
    if not selected:
        raise ValueError("at least one archive variant is required")
    if len(selected) != len(set(selected)):
        raise ValueError(f"archive variants must not contain duplicates: {selected!r}")
    unknown = [variant for variant in selected if variant not in C.RUN_VARIANTS]
    if unknown:
        raise ValueError(
            f"unknown archive variant(s) {unknown!r}; choose from {C.RUN_VARIANTS}"
        )
    return selected


def _parse_variants(raw: str) -> list[str]:
    if raw == "all":
        return list(C.RUN_VARIANTS)
    if not raw or any(not item.strip() for item in raw.split(",")):
        raise ValueError("archive --variant must be 'all' or a non-empty comma-separated list")
    return _validate_variants([item.strip() for item in raw.split(",")])


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


def _result_readme(selected_variants: list[str]) -> str:
    variant_description = (
        "the Full variant"
        if selected_variants == ["full"]
        else f"{len(selected_variants)} selected variants ({', '.join(selected_variants)})"
    )
    return f"""# CodeWeaver ReCodeAgent experiment results

This repository contains the measured 118-project reproduction of
the experiments in arXiv:2604.07341 for {variant_description}, including raw normalized data, independent
test/coverage evidence, paper-equivalent tables and figures, PDFs, provenance,
and filtered raw run archives.

- `results/`: final tables, figures, the exact paper comparison PDF, and
  reproducibility report.
- `results/analysis/paper_tables_side_by_side.pdf`: exact paper Tables 1 and 2
  with the measured CodeWeaver Full result beside every corresponding metric.
- `results/system-comparison/`: GPT-5.6 Sol cross-system JSON/CSVs/LaTeX/PDF
  and its provenance, when a system-comparison root was supplied.
- `results/analysis/paper_table{{1,2}}_side_by_side.csv`: machine-readable
  paper and CodeWeaver values with distinct provenance/status columns.
- `data/`: normalized raw rows, project-level RQ2/generated-test evidence,
  heuristic test-comparison outputs, and complete baseline replays under
  `data/baselines/<label>/` when supplied.
- `raw-run-archives/`: split compressed run outputs; concatenate numbered
  parts before extracting when an archive was split.
- `metadata/campaign/<label>/`: supplied campaign summaries/logs only; run
  workspaces are deliberately rejected to avoid duplicate raw packaging.
- `infrastructure-failure-archives/`: excluded retries, retained separately
  so authentication, transport, and interrupted-state decisions are auditable.
- `reproduction/source/`: exact CodeWeaver/harness source snapshot.
- `metadata/package_manifest.json`: input paths, copied-file counts, archive
  selection, and system-comparison completeness evidence.
- `metadata/checksums.sha256`: SHA-256 for every packaged file, including all
  supplied baseline/comparison/test/campaign evidence.

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
    variants: list[str] | None = None,
    baseline_roots: Iterable[Path] | None = None,
    system_comparison_root: Path | None = None,
    test_comparison_root: Path | None = None,
    campaign_metadata_roots: Iterable[Path] | None = None,
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
    selected_variants = _validate_variants(variants)
    labelled_baselines = _labelled_roots(baseline_roots, kind="baseline")
    labelled_campaign_metadata = _labelled_roots(
        campaign_metadata_roots, kind="campaign metadata",
    )
    for _, root in labelled_baselines:
        _require_baseline_root(root)
    for _, root in labelled_campaign_metadata:
        _require_campaign_metadata_root(root)
    comparison_completeness = (
        _require_system_comparison_root(system_comparison_root)
        if system_comparison_root is not None
        else None
    )
    if (
        require_complete
        and comparison_completeness is not None
        and not comparison_completeness["complete"]
    ):
        raise RuntimeError(
            "refusing to package a system comparison with missing/error evidence: "
            f"{comparison_completeness['unaccounted_missing_artifact_cell_count']} "
            "unaccounted missing, "
            f"{comparison_completeness['error_cell_count']} error cell(s)"
        )

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
    copied["baselines"] = 0
    baseline_inputs: list[dict[str, Any]] = []
    for label, root in labelled_baselines:
        count = _copy_root_files(root, output_root / "data" / "baselines" / label)
        copied["baselines"] += count
        baseline_inputs.append({"label": label, "path": str(root), "file_count": count})
    copied["system_comparison"] = 0
    if system_comparison_root is not None:
        copied["system_comparison"] = _copy_root_files(
            system_comparison_root, output_root / "results" / "system-comparison",
        )
    copied["test_comparison"] = 0
    if test_comparison_root is not None:
        copied["test_comparison"] = _copy_root_files(
            test_comparison_root, output_root / "data" / "test-comparisons",
        )
    copied["campaign_metadata"] = 0
    campaign_metadata_inputs: list[dict[str, Any]] = []
    for label, root in labelled_campaign_metadata:
        count = _copy_root_files(root, output_root / "metadata" / "campaign" / label)
        copied["campaign_metadata"] += count
        campaign_metadata_inputs.append(
            {"label": label, "path": str(root), "file_count": count}
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
        for variant in selected_variants:
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

    C.atomic_write_text(output_root / "README.md", _result_readme(selected_variants))
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
            "baseline_roots": baseline_inputs,
            "system_comparison_root": (
                str(system_comparison_root) if system_comparison_root is not None else None
            ),
            "test_comparison_root": (
                str(test_comparison_root) if test_comparison_root is not None else None
            ),
            "campaign_metadata_roots": campaign_metadata_inputs,
        },
        "copied_file_counts": copied,
        "selected_variants": selected_variants,
        "run_archives": archives,
        "infrastructure_failure_archives": infrastructure_archives,
        "system_comparison_completeness": comparison_completeness,
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
    parser.add_argument(
        "--variant", default="all",
        help="archive variant(s): 'all' (default) or a comma-separated subset",
    )
    parser.add_argument(
        "--baseline-root", action="append", default=[],
        help="complete baseline_replay.py output root; repeat for disjoint roots",
    )
    parser.add_argument(
        "--system-comparison-root",
        help="complete compare-systems output root (requires real PDF and core artifacts)",
    )
    parser.add_argument(
        "--test-comparison-root",
        help="heuristic test_compare.py output root to copy under data/test-comparisons",
    )
    parser.add_argument(
        "--campaign-metadata-root", action="append", default=[],
        help="campaign summaries/logs root; repeatable and rejects run workspaces",
    )
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--skip-run-archives", action="store_true")
    parser.add_argument("--max-part-mib", type=int, default=95)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        variants = _parse_variants(args.variant)
    except ValueError as exc:
        build_parser().error(str(exc))
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
        variants=variants,
        baseline_roots=[Path(root) for root in args.baseline_root],
        system_comparison_root=(
            Path(args.system_comparison_root)
            if args.system_comparison_root
            else None
        ),
        test_comparison_root=(
            Path(args.test_comparison_root) if args.test_comparison_root else None
        ),
        campaign_metadata_roots=[
            Path(root) for root in args.campaign_metadata_root
        ],
    )
    print(
        f"[package-results] wrote {args.output_root}; "
        f"{len(manifest['run_archives'])} run archive(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
