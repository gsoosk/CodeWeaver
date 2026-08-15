"""Uniform post-hoc replay of released ReCodeAgent and prior-system targets.

This module materializes each released target into an isolated synthetic
``run.py`` layout, then delegates all evaluation to :func:`collect.collect_run`.
It never invokes an LLM and never builds or tests inside either official
artifact tree.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from experiments.recodeagent import collect as COL
from experiments.recodeagent import common as C
from experiments.recodeagent import manifest as M
from experiments.recodeagent import run as R
from experiments.recodeagent.common import Status

SYSTEMS = ("recodeagent", "prior")
TARGET_SUBDIRS = {
    "crust": "rust",
    "oxidizer": "rust",
    "alphatrans": "python",
    "skel": "javascript",
}
PRIOR_PAPER_TECHNIQUES = {
    "crust": "swe-agent",
    "oxidizer": "oxidizer",
    "alphatrans": "alphatrans",
    "skel": "skel",
}
KEEP_ROOT_MARKER = ".baseline_replay_materialized.json"
SCHEMA_VERSION = 1

_FAILURE_COLUMNS = [
    "system",
    "paper_technique",
    "variant",
    "project_id",
    "tool",
    "repetition",
    "workspace_dir",
    "artifact_target_path",
    "expected_artifact_target_path",
    "evaluator_adaptations_json",
    "failure_status",
    "reason",
    "detected_at",
]


@dataclass(frozen=True)
class TargetResolution:
    """Exact released-target resolution for one system/project pair."""

    system: str
    paper_technique: str
    project_id: str
    tool: str
    project: str
    target_path: Path | None
    expected_target_path: Path | None
    scaffold_path: Path | None = None
    failure_status: str | None = None
    reason: str = ""

    @property
    def available(self) -> bool:
        return self.target_path is not None and self.failure_status is None


@dataclass(frozen=True)
class ReplayJob:
    system: str
    manifest_row: dict[str, Any]


@dataclass
class ReplayJobResult:
    row: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None


def paper_technique_for(system: str, tool: str) -> str:
    """Return the paper-facing technique label for a system/tool pair."""
    if system == "recodeagent":
        return "recodeagent"
    if system == "prior" and tool in PRIOR_PAPER_TECHNIQUES:
        return PRIOR_PAPER_TECHNIQUES[tool]
    raise ValueError(f"unsupported system/tool pair: {(system, tool)!r}")


def _project_target_path(root: Path, tool: str, project: str, target_subdir: str) -> Path:
    return root / "data" / "tool_projects" / tool / project / target_subdir


def _recodeagent_target_path(results_root: Path, tool: str, project: str, target_subdir: str) -> Path:
    return (
        results_root
        / "recodeagent_translations"
        / "data"
        / "tool_projects"
        / tool
        / project
        / target_subdir
    )


def resolve_artifact_target(
    system: str,
    manifest_row: dict[str, Any],
    implementation_root: Path,
    results_root: Path,
) -> TargetResolution:
    """Resolve one released target using only the verified artifact layouts."""
    tool = str(manifest_row["tool"])
    project = str(manifest_row["project"])
    project_id = str(manifest_row["id"])
    technique = paper_technique_for(system, tool)
    target_subdir = TARGET_SUBDIRS[tool]

    if system == "prior" and tool == "crust":
        return TargetResolution(
            system=system,
            paper_technique=technique,
            project_id=project_id,
            tool=tool,
            project=project,
            target_path=None,
            expected_target_path=None,
            failure_status=Status.UNAVAILABLE,
            reason=(
                "released SWE-agent CRUST target outputs are unavailable; "
                "implementation-root's rust tree is only the pristine stub scaffold "
                "and is intentionally excluded from replay"
            ),
        )

    expected = (
        _recodeagent_target_path(results_root, tool, project, target_subdir)
        if system == "recodeagent"
        else _project_target_path(implementation_root, tool, project, target_subdir)
    )
    if not expected.is_dir():
        return TargetResolution(
            system=system,
            paper_technique=technique,
            project_id=project_id,
            tool=tool,
            project=project,
            target_path=None,
            expected_target_path=expected,
            failure_status=Status.MISSING,
            reason=f"released target directory is missing: {expected}",
        )

    if tool == "skel":
        required_entrypoints = (
            ("index.js", "source.js") if system == "recodeagent" else ("translated.js",)
        )
        if not any((expected / name).is_file() for name in required_entrypoints):
            return TargetResolution(
                system=system,
                paper_technique=technique,
                project_id=project_id,
                tool=tool,
                project=project,
                target_path=None,
                expected_target_path=expected,
                failure_status=Status.MISSING,
                reason=(
                    f"released SKEL target has no supported evaluator entrypoint; expected one of "
                    f"{list(required_entrypoints)!r} under {expected}"
                ),
            )

    scaffold = None
    if system == "recodeagent" and tool == "crust":
        scaffold = _project_target_path(implementation_root, tool, project, "rust")
        if not scaffold.is_dir():
            return TargetResolution(
                system=system,
                paper_technique=technique,
                project_id=project_id,
                tool=tool,
                project=project,
                target_path=None,
                expected_target_path=expected,
                scaffold_path=scaffold,
                failure_status=Status.MISSING,
                reason=f"pristine CRUST implementation scaffold is missing: {scaffold}",
            )

    return TargetResolution(
        system=system,
        paper_technique=technique,
        project_id=project_id,
        tool=tool,
        project=project,
        target_path=expected,
        expected_target_path=expected,
        scaffold_path=scaffold,
    )


def _copy_tree(source: Path, destination: Path) -> None:
    """Copy an artifact tree without following symlinks into official data."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def normalize_evaluator_entrypoint(
    target_dir: Path,
    *,
    system: str,
    tool: str,
) -> list[dict[str, Any]]:
    """Apply only the documented SKEL evaluator entrypoint adaptation."""
    if tool != "skel":
        return []
    if system == "recodeagent" and (target_dir / "index.js").is_file():
        return []

    source_name = "source.js" if system == "recodeagent" else "translated.js"
    source = target_dir / source_name
    destination = target_dir / "index.js"
    if not source.is_file():
        raise FileNotFoundError(f"SKEL evaluator source entrypoint is missing: {source}")
    replaced_existing_destination = destination.is_file()
    shutil.copy2(source, destination)
    return [
        {
            "kind": "evaluator_entrypoint_copy",
            "source": f"pipeline/target/{source_name}",
            "destination": "pipeline/target/index.js",
            "preserved_original": True,
            "replaced_existing_destination": replaced_existing_destination,
            "reason": "collect's SKEL evaluator expects pipeline/target/index.js",
        }
    ]


def _synthetic_state(
    resolution: TargetResolution,
    run_dir: Path,
    environment_provenance: dict[str, Any],
) -> dict[str, Any]:
    now = C.utcnow_iso()
    provenance = {
        key: environment_provenance[key]
        for key in (
            "model",
            "agent_timeout_seconds",
            "git_sha",
            "codeweaver_package_version",
            "copilot_cli_version",
        )
        if key in environment_provenance
    }
    provenance.update(
        {
            "replay_mode": {
                "value": "post_hoc_released_artifact_replay",
                "status": Status.MEASURED,
                "reason": "synthetic terminal state; no LLM or translation agent was invoked",
            },
            "artifact_target_path": {
                "value": str(resolution.target_path),
                "status": Status.MEASURED,
                "reason": "",
            },
        }
    )
    return {
        "variant": "full",
        "project_id": resolution.project_id,
        "repetition": 0,
        "status": "completed",
        "app_id": C.slugify(f"baseline-{resolution.system}-{resolution.project_id}")[:60],
        "workspace_dir": str(run_dir),
        "argv": None,
        "returncode": None,
        "attempt": 1,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "ended_at": None,
        "timeout_seconds": None,
        "error": "",
        "provenance": provenance,
    }


def materialize_synthetic_run(
    resolution: TargetResolution,
    run_dir: Path,
    environment_provenance: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create the isolated run layout consumed by ``collect_run``."""
    if not resolution.available or resolution.target_path is None:
        raise ValueError("cannot materialize an unavailable target")
    if run_dir.exists():
        shutil.rmtree(run_dir)
    target_dir = run_dir / "pipeline" / "target"
    _copy_tree(resolution.target_path, target_dir)
    adaptations = normalize_evaluator_entrypoint(
        target_dir, system=resolution.system, tool=resolution.tool
    )
    if resolution.scaffold_path is not None:
        _copy_tree(resolution.scaffold_path, run_dir / "scaffold")
    C.atomic_write_json(
        run_dir / R.STATE_FILENAME,
        _synthetic_state(resolution, run_dir, environment_provenance),
    )
    return adaptations


def _safe_project_rows(
    manifest: dict[str, Any],
    dataset_specs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    projects = manifest.get("projects")
    if not isinstance(projects, list):
        raise ValueError("manifest.projects must be a list")
    if manifest.get("counts_match_expected") is False:
        raise ValueError("manifest reports counts_match_expected=false")
    expected_total = manifest.get("expected_total")
    if isinstance(expected_total, int) and expected_total != len(projects):
        raise ValueError(
            f"manifest expected_total={expected_total} but contains {len(projects)} project rows"
        )

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for index, raw_row in enumerate(projects):
        if not isinstance(raw_row, dict):
            raise ValueError(f"manifest project row {index} is not an object")
        row = dict(raw_row)
        tool = row.get("tool")
        project = row.get("project")
        project_id = row.get("id")
        if tool not in TARGET_SUBDIRS or tool not in dataset_specs:
            raise ValueError(f"manifest row {index} has unsupported tool {tool!r}")
        if not isinstance(project, str) or not project or project in {".", ".."}:
            raise ValueError(f"manifest row {index} has invalid project {project!r}")
        if "/" in project or "\\" in project:
            raise ValueError(f"manifest row {index} project contains a path separator: {project!r}")
        expected_id = f"{tool}__{project}"
        if project_id != expected_id:
            raise ValueError(
                f"manifest row {index} id must be exact tool__project form "
                f"{expected_id!r}, got {project_id!r}"
            )
        folded = expected_id.casefold()
        if folded in seen:
            raise ValueError(f"manifest has duplicate or case-colliding project id {project_id!r}")
        seen.add(folded)
        rows.append(row)
    return rows


def parse_systems(raw: str) -> list[str]:
    """Parse and validate the comma-separated ``--system`` selector."""
    values = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not values:
        raise argparse.ArgumentTypeError("--system must select recodeagent, prior, or both")
    unknown = [value for value in values if value not in SYSTEMS]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown system(s) {unknown!r}; choose from {list(SYSTEMS)!r}"
        )
    if len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("--system contains duplicate entries")
    return values


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def prepare_keep_materialized_root(
    keep_root: Path,
    *,
    implementation_root: Path,
    results_root: Path,
    output_root: Path,
) -> Path:
    """Validate and mark a deterministic debug-materialization root."""
    keep_root = keep_root.resolve()
    implementation_root = implementation_root.resolve()
    results_root = results_root.resolve()
    output_root = output_root.resolve()

    for official_root, label in (
        (implementation_root, "implementation root"),
        (results_root, "results root"),
    ):
        if _path_is_within(keep_root, official_root) or _path_is_within(official_root, keep_root):
            raise ValueError(
                f"--keep-materialized-root must not overlap the official {label}: {keep_root}"
            )
    if keep_root == output_root:
        raise ValueError("--keep-materialized-root must not equal --output-root")

    marker = keep_root / KEEP_ROOT_MARKER
    if keep_root.exists():
        entries = list(keep_root.iterdir())
        if entries and not marker.is_file():
            raise ValueError(
                f"--keep-materialized-root is non-empty and lacks {KEEP_ROOT_MARKER}: {keep_root}"
            )
        if marker.is_file():
            recorded = C.read_json_or(marker, {})
            if recorded.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(f"unrecognized keep-root marker at {marker}")
            expected_roots = {
                "implementation_root": str(implementation_root),
                "results_root": str(results_root),
            }
            if recorded.get("official_roots") != expected_roots:
                raise ValueError(
                    f"keep-root marker was created for different official roots: {marker}"
                )
    keep_root.mkdir(parents=True, exist_ok=True)
    C.atomic_write_json(
        marker,
        {
            "schema_version": SCHEMA_VERSION,
            "created_for": "experiments.recodeagent.baseline_replay",
            "official_roots": {
                "implementation_root": str(implementation_root),
                "results_root": str(results_root),
            },
        },
    )
    return keep_root


@contextlib.contextmanager
def _project_run_dir(
    *,
    system: str,
    project_id: str,
    output_root: Path,
    keep_root: Path | None,
) -> Iterator[Path]:
    if keep_root is not None:
        yield keep_root / system / project_id
        return

    work_parent = output_root / ".baseline_replay_tmp"
    work_parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{C.slugify(system)}-{C.slugify(project_id)}-"
    with tempfile.TemporaryDirectory(prefix=prefix, dir=work_parent) as tmp:
        yield Path(tmp) / "run"


def _failure_row(
    resolution: TargetResolution,
    *,
    status: str,
    reason: str,
    workspace_dir: Path | None = None,
    adaptations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "system": resolution.system,
        "paper_technique": resolution.paper_technique,
        "variant": "full",
        "project_id": resolution.project_id,
        "tool": resolution.tool,
        "repetition": 0,
        "workspace_dir": str(workspace_dir) if workspace_dir is not None else "",
        "artifact_target_path": (
            str(resolution.target_path) if resolution.target_path is not None else ""
        ),
        "expected_artifact_target_path": (
            str(resolution.expected_target_path)
            if resolution.expected_target_path is not None
            else ""
        ),
        "evaluator_adaptations_json": json.dumps(adaptations or [], sort_keys=True),
        "failure_status": status,
        "reason": reason,
        "detected_at": C.utcnow_iso(),
    }


def _collect_job(
    job: ReplayJob,
    *,
    implementation_root: Path,
    results_root: Path,
    output_root: Path,
    keep_root: Path | None,
    dataset_specs: dict[str, dict[str, Any]],
    timeout: float | None,
    crust_paper_expected_tests: dict[str, int] | None,
    environment_provenance: dict[str, Any],
    raw_run_schema: dict[str, Any],
) -> ReplayJobResult:
    row = job.manifest_row
    resolution = resolve_artifact_target(
        job.system, row, implementation_root, results_root
    )
    if not resolution.available:
        return ReplayJobResult(
            failure=_failure_row(
                resolution,
                status=resolution.failure_status or Status.MISSING,
                reason=resolution.reason,
            )
        )

    run_dir: Path | None = None
    adaptations: list[dict[str, Any]] = []
    try:
        with _project_run_dir(
            system=job.system,
            project_id=resolution.project_id,
            output_root=output_root,
            keep_root=keep_root,
        ) as materialized:
            run_dir = materialized
            adaptations = materialize_synthetic_run(
                resolution, run_dir, environment_provenance
            )
            base_row = COL.collect_run(
                run_dir,
                variant="full",
                project_id=resolution.project_id,
                tool=resolution.tool,
                repetition=0,
                manifest_row=row,
                dataset_spec=dataset_specs[resolution.tool],
                timeout=timeout,
                reference_results_root=results_root,
                crust_paper_expected_tests=crust_paper_expected_tests,
            )
            schema_errors = C.validate_schema(base_row, raw_run_schema)
            if schema_errors:
                raise ValueError(
                    "collect_run returned a row that failed raw_run.schema.json: "
                    + "; ".join(schema_errors)
                )
            external_row = dict(base_row)
            external_row.update(
                {
                    "system": resolution.system,
                    "paper_technique": resolution.paper_technique,
                    "artifact_target_path": str(resolution.target_path),
                    "evaluator_adaptations_json": json.dumps(
                        adaptations, sort_keys=True
                    ),
                }
            )
            return ReplayJobResult(row=external_row)
    except Exception as exc:  # noqa: BLE001 - every expected job needs evidence
        return ReplayJobResult(
            failure=_failure_row(
                resolution,
                status=Status.ERROR,
                reason=f"replay_collection_error: {exc!r}",
                workspace_dir=run_dir,
                adaptations=adaptations,
            )
        )


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    buffer = io.StringIO()
    for row in rows:
        buffer.write(json.dumps(row, default=str) + "\n")
    C.atomic_write_text(path, buffer.getvalue())


def _input_hash(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": str(path),
            "sha256": None,
            "status": Status.MISSING,
            "reason": "input file does not exist",
        }
    return {
        "path": str(path.resolve()),
        "sha256": C.file_sha256(path),
        "size_bytes": path.stat().st_size,
        "status": Status.MEASURED,
        "reason": "",
    }


def _build_summary(
    systems: list[str],
    project_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    by_system: dict[str, Any] = {}
    for system in systems:
        system_rows = [row for row in rows if row["system"] == system]
        system_failures = [failure for failure in failures if failure["system"] == system]
        by_tool: dict[str, Any] = {}
        for tool in TARGET_SUBDIRS:
            expected = sum(1 for row in project_rows if row["tool"] == tool)
            measured = sum(1 for row in system_rows if row["tool"] == tool)
            failed = sum(1 for row in system_failures if row["tool"] == tool)
            by_tool[tool] = {
                "expected": expected,
                "measured": measured,
                "failures": failed,
            }
        by_system[system] = {
            "expected": len(project_rows),
            "measured": len(system_rows),
            "failures": len(system_failures),
            "by_tool": by_tool,
        }

    expected_total = len(systems) * len(project_rows)
    if expected_total != len(rows) + len(failures):
        raise RuntimeError(
            "baseline replay matrix lost jobs: "
            f"expected={expected_total}, measured={len(rows)}, failures={len(failures)}"
        )
    prior_crust_expected = (
        sum(1 for row in project_rows if row["tool"] == "crust")
        if "prior" in systems
        else 0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": C.utcnow_iso(),
        "systems": systems,
        "expected": expected_total,
        "measured": len(rows),
        "failures": len(failures),
        "by_system": by_system,
        "swe_agent_outputs": {
            "available": False,
            "expected_projects_in_selected_matrix": prior_crust_expected,
            "statement": (
                "Released SWE-agent CRUST target outputs are unavailable. "
                "All selected prior/CRUST projects are explicit unavailable failures; "
                "the implementation rust trees are stub scaffolds and are never replayed as SWE-agent output."
            ),
        },
    }


def _build_provenance(
    *,
    implementation_root: Path,
    results_root: Path,
    output_root: Path,
    input_hashes: dict[str, Any],
    systems: list[str],
    jobs: int,
    timeout: float | None,
    keep_root: Path | None,
    environment_provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": C.utcnow_iso(),
        "mode": "post_hoc_artifact_replay",
        "fresh_llm_rerun": False,
        "statement": (
            "This is a uniform post-hoc evaluation of released target artifacts. "
            "It materializes isolated evaluator workspaces and calls collect.collect_run directly; "
            "it does not invoke ReCodeAgent, SWE-agent, another translation system, or any LLM."
        ),
        "systems": systems,
        "jobs": jobs,
        "evaluator_timeout_seconds": timeout,
        "roots": {
            "implementation_root": str(implementation_root.resolve()),
            "results_root": str(results_root.resolve()),
            "output_root": str(output_root.resolve()),
            "keep_materialized_root": str(keep_root) if keep_root is not None else None,
        },
        "inputs": input_hashes,
        "environment": environment_provenance,
        "artifact_layout_contract": {
            "implementation_targets": (
                "<implementation-root>/data/tool_projects/{tool}/{project}/{rust|python|javascript}"
            ),
            "recodeagent_targets": (
                "<results-root>/recodeagent_translations/data/tool_projects/"
                "{tool}/{project}/{rust|python|javascript}"
            ),
            "reference_results_root": str(results_root.resolve()),
        },
        "evaluator_entrypoint_adaptations": {
            "prior_skel": "copy translated.js to index.js in the isolated target, preserving translated.js",
            "recodeagent_skel": (
                "copy source.js to index.js in the isolated target only when index.js is absent, "
                "preserving source.js"
            ),
            "all_other_cases": "none",
        },
        "swe_agent_outputs": {
            "available": False,
            "statement": (
                "Released SWE-agent CRUST targets are unavailable; implementation rust trees are "
                "pristine evaluator scaffolds only and are excluded as candidate outputs."
            ),
        },
    }


def replay_baselines(
    *,
    manifest_path: Path,
    config_path: Path,
    implementation_root: Path,
    results_root: Path,
    output_root: Path,
    systems: list[str],
    jobs: int = 1,
    timeout: float | None = None,
    crust_paper_expected_path: Path | None = None,
    keep_materialized_root: Path | None = None,
) -> dict[str, Any]:
    """Replay the selected baseline matrix and atomically write all outputs."""
    manifest_path = manifest_path.resolve()
    config_path = config_path.resolve()
    implementation_root = implementation_root.resolve()
    results_root = results_root.resolve()
    output_root = output_root.resolve()
    if crust_paper_expected_path is not None:
        crust_paper_expected_path = crust_paper_expected_path.resolve()
    if jobs < 1:
        raise ValueError("--jobs must be at least 1")
    if timeout is not None and timeout <= 0:
        raise ValueError("--timeout must be positive")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    if not config_path.is_file():
        raise FileNotFoundError(f"config not found: {config_path}")
    if not implementation_root.is_dir():
        raise FileNotFoundError(f"implementation root not found: {implementation_root}")
    if not results_root.is_dir():
        raise FileNotFoundError(f"results root not found: {results_root}")
    if (
        not systems
        or any(system not in SYSTEMS for system in systems)
        or len(systems) != len(set(systems))
    ):
        raise ValueError(f"systems must be a non-empty subset of {SYSTEMS!r}")

    input_hashes = {
        "manifest": _input_hash(manifest_path),
        "config": _input_hash(config_path),
    }
    if crust_paper_expected_path is not None:
        key = (
            "results_xlsx"
            if crust_paper_expected_path.suffix.lower() == ".xlsx"
            else "crust_paper_expected_tests"
        )
        input_hashes[key] = _input_hash(crust_paper_expected_path)

    config = M.load_experiment_config(config_path)
    dataset_specs = M.dataset_specs(config)
    manifest = C.read_json(manifest_path)
    project_rows = _safe_project_rows(manifest, dataset_specs)
    output_root.mkdir(parents=True, exist_ok=True)

    crust_paper_expected_tests: dict[str, int] | None = None
    if crust_paper_expected_path is not None:
        crust_paper_expected_tests, reason = COL.read_crust_paper_expected_tests(
            crust_paper_expected_path
        )
        if crust_paper_expected_tests is None:
            print(
                "[baseline-replay] WARNING: --crust-paper-expected-tests could not be "
                f"loaded ({reason}); CRUST expected counts will use collect's native fallback",
                file=sys.stderr,
            )

    environment_provenance = C.collect_provenance(
        model=None, agent_timeout=None, probe_toolchains=True
    )
    keep_root = None
    if keep_materialized_root is not None:
        keep_root = prepare_keep_materialized_root(
            keep_materialized_root,
            implementation_root=implementation_root,
            results_root=results_root,
            output_root=output_root,
        )

    raw_run_schema = C.load_schema("raw_run.schema.json")
    replay_jobs = [
        ReplayJob(system=system, manifest_row=row)
        for system in systems
        for row in project_rows
    ]

    def execute(job: ReplayJob) -> ReplayJobResult:
        return _collect_job(
            job,
            implementation_root=implementation_root,
            results_root=results_root,
            output_root=output_root,
            keep_root=keep_root,
            dataset_specs=dataset_specs,
            timeout=timeout,
            crust_paper_expected_tests=crust_paper_expected_tests,
            environment_provenance=environment_provenance,
            raw_run_schema=raw_run_schema,
        )

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(execute, replay_jobs))

    rows = [result.row for result in results if result.row is not None]
    failures = [result.failure for result in results if result.failure is not None]
    summary = _build_summary(systems, project_rows, rows, failures)
    provenance = _build_provenance(
        implementation_root=implementation_root,
        results_root=results_root,
        output_root=output_root,
        input_hashes=input_hashes,
        systems=systems,
        jobs=jobs,
        timeout=timeout,
        keep_root=keep_root,
        environment_provenance=environment_provenance,
    )

    jsonl_path = output_root / "baseline_raw_runs.jsonl"
    csv_path = output_root / "baseline_raw_runs.csv"
    failures_path = output_root / "baseline_failures.csv"
    summary_path = output_root / "baseline_replay_summary.json"
    provenance_path = output_root / "baseline_replay_provenance.json"
    _write_jsonl(rows, jsonl_path)
    COL._write_csv(  # noqa: SLF001 - preserve collect.py's exact atomic CSV style
        rows,
        [
            "system",
            "paper_technique",
            *COL._RAW_RUNS_CSV_COLUMNS,  # noqa: SLF001 - required published column contract
            "artifact_target_path",
            "evaluator_adaptations_json",
        ],
        csv_path,
    )
    COL._write_csv(  # noqa: SLF001 - preserve collect.py's exact atomic CSV style
        failures, _FAILURE_COLUMNS, failures_path
    )
    C.atomic_write_json(summary_path, summary)
    C.atomic_write_json(provenance_path, provenance)

    temp_parent = output_root / ".baseline_replay_tmp"
    with contextlib.suppress(OSError):
        temp_parent.rmdir()
    return {
        "rows": rows,
        "failures": failures,
        "summary": summary,
        "provenance": provenance,
        "paths": {
            "jsonl": jsonl_path,
            "csv": csv_path,
            "failures": failures_path,
            "summary": summary_path,
            "provenance": provenance_path,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone baseline replay CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m experiments.recodeagent.baseline_replay",
        description=(
            "Uniformly re-evaluate released ReCodeAgent and prior-paper targets "
            "without rerunning an LLM."
        ),
    )
    parser.add_argument("--manifest", required=True, help="exact benchmark manifest.json")
    parser.add_argument(
        "--config",
        default=str(C.DEFAULT_EXPERIMENT_CONFIG),
        help="experiment TOML (default: bundled experiment.toml)",
    )
    parser.add_argument("--implementation-root", required=True)
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--system",
        type=parse_systems,
        default=list(SYSTEMS),
        help="comma-separated recodeagent,prior (default: both)",
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument(
        "--crust-paper-expected-tests",
        default=None,
        help=(
            "official results.xlsx or JSON/CSV CRUST expected-count inventory; "
            "parsed exactly by collect.read_crust_paper_expected_tests"
        ),
    )
    parser.add_argument(
        "--keep-materialized-root",
        default=None,
        help="retain deterministic <root>/<system>/<project-id> evaluator workspaces",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = replay_baselines(
        manifest_path=Path(args.manifest),
        config_path=Path(args.config),
        implementation_root=Path(args.implementation_root),
        results_root=Path(args.results_root),
        output_root=Path(args.output_root),
        systems=list(args.system),
        jobs=args.jobs,
        timeout=args.timeout,
        crust_paper_expected_path=(
            Path(args.crust_paper_expected_tests)
            if args.crust_paper_expected_tests
            else None
        ),
        keep_materialized_root=(
            Path(args.keep_materialized_root) if args.keep_materialized_root else None
        ),
    )
    print(
        "[baseline-replay] "
        f"{result['summary']['measured']} measured, "
        f"{result['summary']['failures']} failure/unavailable "
        f"of {result['summary']['expected']} expected"
    )
    print(f"[baseline-replay] outputs -> {Path(args.output_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
