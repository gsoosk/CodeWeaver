"""Independent evaluation of already-produced Rustine comparison workspaces."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from experiments.recodeagent.common import parse_copilot_jsonl, summarize_copilot_events
from experiments.rustine import common as C
from experiments.rustine.config import load_subject_config, subjects_by_id
from experiments.rustine.evaluator import CommandBackend

StageRunner = Callable[..., dict[str, Any]]
SAFETY_HIR_FIELDS = (
    "raw_pointer_declarations",
    "raw_pointer_dereferences",
    "unsafe_lines",
    "unsafe_type_casts",
    "unsafe_calls",
)


def _load_workspace_evaluator(path: Path):
    spec = importlib.util.spec_from_file_location(
        f"_rustine_workspace_evaluator_{abs(hash(path))}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import workspace evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_workspace_stage(
    stage: str,
    *,
    workspace: Path,
    target: Path,
    contract_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    evaluator_path = workspace / "immutable_evaluator.py"
    module = _load_workspace_evaluator(evaluator_path)
    return module.evaluate_stage(
        stage, target=target, contract_dir=contract_dir, timeout=timeout
    )


def _run_completion(workspace: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    state_path = workspace / "recodeagent_run_state.json"
    if not state_path.exists():
        return C.measurement(C.MISSING, reason="recodeagent_run_state.json is absent"), None
    try:
        state = C.read_json(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        return C.measurement(C.ERROR, reason=f"invalid run state: {exc}"), None
    status = state.get("status")
    completed = status == "completed"
    reason = "" if completed else f"run state status={status!r}: {state.get('error', '')}".strip()
    return C.measurement(C.MEASURED, completed, reason), state


def _elapsed_measurement(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state:
        return C.measurement(C.MISSING, reason="run state is unavailable")
    started = state.get("started_at")
    ended = state.get("ended_at")
    if not started or not ended:
        return C.measurement(C.MISSING, reason="run state lacks start/end timestamps")
    try:
        start_dt = dt.datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        end_dt = dt.datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
    except ValueError as exc:
        return C.measurement(C.ERROR, reason=f"invalid run timestamps: {exc}")
    return C.measurement(C.MEASURED, max(0.0, (end_dt - start_dt).total_seconds()))


def _usage_measurements(workspace: Path) -> dict[str, dict[str, Any]]:
    log_dir = workspace / "pipeline" / "logs"
    paths = sorted(log_dir.rglob("*.stdout.jsonl")) if log_dir.is_dir() else []
    fields = ("input_tokens", "output_tokens", "nano_aiu", "premium_requests")
    if not paths:
        reason = "no Copilot JSONL logs were found"
        return {
            field: C.measurement(C.MISSING, reason=reason) for field in fields
        }
    totals = {field: 0 for field in fields}
    seen = {field: False for field in fields}
    for path in paths:
        events = parse_copilot_jsonl(path.read_text(encoding="utf-8", errors="replace"))
        summary = summarize_copilot_events(events)
        if summary.input_tokens is not None:
            totals["input_tokens"] += int(summary.input_tokens)
            seen["input_tokens"] = True
        if summary.output_tokens is not None:
            totals["output_tokens"] += int(summary.output_tokens)
            seen["output_tokens"] = True
        if summary.nano_aiu is not None:
            totals["nano_aiu"] += int(summary.nano_aiu)
            seen["nano_aiu"] = True
        if summary.premium_requests is not None:
            totals["premium_requests"] += int(summary.premium_requests)
            seen["premium_requests"] = True
    labels = {
        "input_tokens": "input tokens",
        "output_tokens": "output tokens",
        "nano_aiu": "nano AIU",
        "premium_requests": "premium requests",
    }
    return {
        field: (
            C.measurement(C.MEASURED, totals[field])
            if seen[field]
            else C.measurement(
                C.UNAVAILABLE,
                reason=f"Copilot logs did not expose {labels[field]}",
            )
        )
        for field in fields
    }


def _integrity_measurement(
    workspace: Path, manifest_row: dict[str, Any]
) -> dict[str, Any]:
    oracle = workspace / "oracle"
    evaluator = workspace / "immutable_evaluator.py"
    if not oracle.is_dir() or not evaluator.is_file():
        return C.measurement(C.MISSING, reason="oracle or immutable evaluator is absent")
    actual_contract = C.tree_sha256(oracle)
    actual_evaluator = C.file_sha256(evaluator)
    if actual_contract != manifest_row.get("contract_sha256"):
        return C.measurement(C.MEASURED, False, "fixed contract checksum differs from preparation")
    if actual_evaluator != manifest_row.get("evaluator_sha256"):
        return C.measurement(C.MEASURED, False, "immutable evaluator checksum differs from preparation")
    return C.measurement(C.MEASURED, True)


def _unavailable_assertions(reason: str, status: str = C.MISSING) -> dict[str, dict[str, Any]]:
    return {
        key: C.measurement(status, reason=reason)
        for key in ("executed", "passed", "failed")
    }


def _coverage_fields(stage: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    metric = stage.get("measurement", {})
    if metric.get("status") != C.MEASURED:
        mirrored = C.measurement(metric.get("status", C.ERROR), reason=metric.get("reason", ""))
        return mirrored, dict(mirrored)
    value = metric.get("value") or {}
    return (
        C.measurement(C.MEASURED, value.get("function_percent")),
        C.measurement(C.MEASURED, value.get("line_percent")),
    )


def _safety_fields(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metric = stage.get("measurement", {})
    result = {"pointer_arithmetic": stage.get(
        "pointer_arithmetic",
        C.measurement(C.MISSING, reason="pointer-arithmetic measurement was not produced"),
    )}
    if metric.get("status") == C.MEASURED:
        value = metric.get("value") or {}
        for field in SAFETY_HIR_FIELDS:
            if field in value:
                result[field] = C.measurement(C.MEASURED, value[field])
            else:
                result[field] = C.measurement(
                    C.ERROR, reason=f"newmetrics output omitted {field}"
                )
    else:
        for field in SAFETY_HIR_FIELDS:
            result[field] = C.measurement(
                metric.get("status", C.ERROR), reason=metric.get("reason", "")
            )
    return result


def evaluate_workspace(
    subject: dict[str, Any],
    manifest_row: dict[str, Any],
    *,
    workspace: Path,
    variant: str,
    repetition: int,
    timeout: float,
    measure_coverage: bool = True,
    measure_safety: bool = True,
    stage_runner: StageRunner = run_workspace_stage,
) -> dict[str, Any]:
    run_completion, state = _run_completion(workspace)
    integrity = _integrity_measurement(workspace, manifest_row)
    usage = _usage_measurements(workspace)
    row: dict[str, Any] = {
        "subject_id": subject["id"],
        "subject": subject["name"],
        "artifact_dir": subject["artifact_dir"],
        "loc": subject["loc"],
        "variant": variant,
        "repetition": repetition,
        "workspace": str(workspace),
        "pipeline_status": state.get("status") if state else None,
        "pipeline_error": state.get("error", "") if state else "",
        "execution_provenance": state.get("provenance", {}) if state else {},
        "paper_validation": subject["paper_validation"],
        "paper_safety": subject["paper_safety"],
        "run_completion": run_completion,
        "contract_integrity": integrity,
        "elapsed_seconds": _elapsed_measurement(state),
        **usage,
    }
    target = workspace / "pipeline" / "target"
    if integrity.get("value") is not True:
        reason = integrity.get("reason") or "fixed contract integrity is not verified"
        downstream_status = (
            integrity.get("status")
            if integrity.get("status") in {C.MISSING, C.UNAVAILABLE}
            else C.ERROR
        )
        row.update(
            {
                "compilation": C.measurement(downstream_status, reason=reason),
                "fixed_contract_tests": C.measurement(downstream_status, reason=reason),
                "assertions": _unavailable_assertions(reason, downstream_status),
                "function_coverage_percent": C.measurement(downstream_status, reason=reason),
                "line_coverage_percent": C.measurement(downstream_status, reason=reason),
                "safety": {
                    field: C.measurement(downstream_status, reason=reason)
                    for field in ("pointer_arithmetic", *SAFETY_HIR_FIELDS)
                },
            }
        )
        return row
    if not target.is_dir():
        reason = "pipeline/target is absent"
        row.update(
            {
                "compilation": C.measurement(C.MISSING, reason=reason),
                "fixed_contract_tests": C.measurement(C.MISSING, reason=reason),
                "assertions": _unavailable_assertions(reason),
                "function_coverage_percent": C.measurement(C.MISSING, reason=reason),
                "line_coverage_percent": C.measurement(C.MISSING, reason=reason),
                "safety": {
                    field: C.measurement(C.MISSING, reason=reason)
                    for field in ("pointer_arithmetic", *SAFETY_HIR_FIELDS)
                },
            }
        )
        return row

    stage_args = {
        "workspace": workspace,
        "target": target,
        "contract_dir": workspace / "oracle",
        "timeout": timeout,
    }
    build = stage_runner("build", **stage_args)
    tests = stage_runner("test", **stage_args)
    row["compilation"] = build["measurement"]
    row["fixed_contract_tests"] = tests["measurement"]
    row["assertions"] = tests.get(
        "assertions",
        _unavailable_assertions("test evaluator did not return assertion measurements", C.ERROR),
    )
    row["evaluation_commands"] = {
        "build": build.get("commands", []),
        "test": tests.get("commands", []),
    }

    if measure_coverage:
        coverage = stage_runner("coverage", **stage_args)
        function_coverage, line_coverage = _coverage_fields(coverage)
        row["function_coverage_percent"] = function_coverage
        row["line_coverage_percent"] = line_coverage
        row["coverage_details"] = {
            "paper_comparable": coverage.get("measurement"),
            "production_only": coverage.get("production_only_measurement"),
            "files": coverage.get("coverage_files", {}),
        }
        row["evaluation_commands"]["coverage"] = coverage.get("commands", [])
    else:
        reason = "coverage measurement disabled by caller"
        row["function_coverage_percent"] = C.measurement(C.SKIPPED, reason=reason)
        row["line_coverage_percent"] = C.measurement(C.SKIPPED, reason=reason)
    if measure_safety:
        safety = stage_runner("safety", **stage_args)
        row["safety"] = _safety_fields(safety)
        row["safety_diagnostics"] = {
            "pointer_arithmetic_source_pattern": safety.get(
                "pointer_arithmetic_diagnostic",
                C.measurement(
                    C.MISSING,
                    reason="source-pattern pointer diagnostic was not produced",
                ),
            )
        }
        row["evaluation_commands"]["safety"] = safety.get("commands", [])
        row["production_files"] = safety.get("production_files", [])
    else:
        row["safety"] = {
            field: C.measurement(C.SKIPPED, reason="safety measurement disabled by caller")
            for field in ("pointer_arithmetic", *SAFETY_HIR_FIELDS)
        }
    return row


def _csv_row(row: dict[str, Any]) -> dict[str, Any]:
    flat = {
        "subject_id": row["subject_id"],
        "subject": row["subject"],
        "variant": row["variant"],
        "repetition": row["repetition"],
        "loc": row["loc"],
        "pipeline_status": row["pipeline_status"],
        "pipeline_error": row["pipeline_error"],
    }
    for name in (
        "run_completion",
        "contract_integrity",
        "compilation",
        "fixed_contract_tests",
        "function_coverage_percent",
        "line_coverage_percent",
        "elapsed_seconds",
        "input_tokens",
        "output_tokens",
        "nano_aiu",
        "premium_requests",
    ):
        C.flatten_measurement(flat, name, row[name])
    for name, metric in row["assertions"].items():
        C.flatten_measurement(flat, f"assertions_{name}", metric)
    for name, metric in row["safety"].items():
        C.flatten_measurement(flat, name, metric)
    return flat


def evaluate_runs(
    *,
    config: dict[str, Any],
    manifest: dict[str, Any],
    runs_root: Path,
    variant: str = "full",
    repetitions: int | None = None,
    timeout: float | None = None,
    measure_coverage: bool = True,
    measure_safety: bool = True,
    max_workers: int = 1,
    stage_runner: StageRunner = run_workspace_stage,
) -> dict[str, Any]:
    by_subject = subjects_by_id(config)
    manifest_rows = {int(row["subject_id"]): row for row in manifest["projects"]}
    repetitions = repetitions if repetitions is not None else int(
        manifest.get("protocol", {}).get("repetitions", config["protocol"]["repetitions"])
    )
    timeout = timeout or float(config["protocol"]["agent_timeout_seconds"])
    jobs = []
    for subject_id in range(1, 24):
        subject = by_subject[subject_id]
        manifest_row = manifest_rows[subject_id]
        for repetition in range(repetitions):
            workspace = runs_root / variant / str(subject_id) / f"rep{repetition}"
            jobs.append((subject, manifest_row, workspace, repetition))

    def evaluate_one(job):
        subject, manifest_row, workspace, repetition = job
        return evaluate_workspace(
            subject,
            manifest_row,
            workspace=workspace,
            variant=variant,
            repetition=repetition,
            timeout=timeout,
            measure_coverage=measure_coverage,
            measure_safety=measure_safety,
            stage_runner=stage_runner,
        )

    if max_workers <= 1:
        rows = [evaluate_one(job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            rows = list(pool.map(evaluate_one, jobs))
    return {
        "schema_version": 2,
        "generated_at": C.utcnow_iso(),
        "paper": config["paper"],
        "artifact": {**config["artifact"], **manifest.get("artifact", {})},
        "protocol": {**config["protocol"], "evaluated_repetitions": repetitions},
        "runs_root": str(runs_root),
        "rows": rows,
        "preparation_provenance": manifest.get("provenance", {}),
        "provenance": {
            **C.collect_provenance(),
            "tools": collect_tool_provenance(runs_root),
        },
    }


def collect_tool_provenance(cwd: Path) -> dict[str, Any]:
    backend = CommandBackend.discover()
    if backend is None:
        return {
            "backend": C.UNAVAILABLE,
            "reason": "cargo is unavailable natively and through WSL",
        }
    probe_cwd = cwd if cwd.is_dir() else (cwd.parent if cwd.parent.is_dir() else Path.cwd())
    probes = {
        "cargo": (["cargo", "--version"], None),
        "rustc_nightly": (
            ["rustc", "+nightly-2025-05-13", "--version"],
            None,
        ),
        "cargo_llvm_cov": (["cargo", "llvm-cov", "--version"], None),
    }
    if backend.mode == "wsl" or os.name != "nt":
        probes["cargo_newmetrics_sha256"] = (
            ["sha256sum", "/opt/codeweaver-rustine-tools/bin/cargo-newmetrics"],
            None,
        )
    results = {"backend": backend.mode}
    for name, (argv, env) in probes.items():
        result = backend.run(argv, cwd=probe_cwd, timeout=30, env=env)
        results[name] = {
            "status": C.MEASURED if result["ok"] else C.UNAVAILABLE,
            "value": (result["stdout"] or result["stderr"]).strip().splitlines()[:1],
            "returncode": result["returncode"],
        }
    return results


def write_evaluation(output_dir: Path, evaluation: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = C.atomic_write_json(output_dir / "evaluation.json", evaluation)
    flat_rows = [_csv_row(row) for row in evaluation["rows"]]
    fieldnames = list(flat_rows[0]) if flat_rows else []
    csv_path = C.write_csv(output_dir / "evaluation.csv", flat_rows, fieldnames)
    return json_path, csv_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(C.DEFAULT_CONFIG))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--no-coverage", action="store_true")
    parser.add_argument("--no-safety", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_subject_config(args.config)
    manifest = C.read_json(args.manifest)
    evaluation = evaluate_runs(
        config=config,
        manifest=manifest,
        runs_root=Path(args.runs_root).resolve(),
        variant=args.variant,
        repetitions=args.repetitions,
        timeout=args.timeout,
        measure_coverage=not args.no_coverage,
        measure_safety=not args.no_safety,
        max_workers=max(1, args.jobs),
    )
    json_path, csv_path = write_evaluation(Path(args.out), evaluation)
    print(f"wrote {json_path} and {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
