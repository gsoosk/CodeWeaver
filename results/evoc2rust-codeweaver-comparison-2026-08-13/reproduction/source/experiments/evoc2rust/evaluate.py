"""Independently evaluate terminal EvoC2Rust comparison workspaces."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from experiments.evoc2rust import common as C
from experiments.evoc2rust.config import load_config, subjects_by_id
from experiments.evoc2rust.evaluator import RUST_PREAMBLE, run_command
from experiments.recodeagent.common import (
    parse_copilot_jsonl,
    summarize_copilot_events,
)

TERMINAL_STATUSES = {"completed", "failed", "timeout"}


def _load_workspace_evaluator(path: Path):
    spec = importlib.util.spec_from_file_location(
        f"_evoc2rust_workspace_evaluator_{abs(hash(path))}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import immutable evaluator: {path}")
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
    module = _load_workspace_evaluator(workspace / "immutable_evaluator.py")
    return module.evaluate_stage(
        stage,
        target=target,
        contract_dir=contract_dir,
        timeout=timeout,
    )


def _run_state(workspace: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    path = workspace / "recodeagent_run_state.json"
    if not path.is_file():
        return C.measurement(C.MISSING, reason="run state is absent"), None
    try:
        state = C.read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return C.measurement(C.ERROR, reason=f"invalid run state: {exc}"), None
    status = state.get("status")
    terminal = status in TERMINAL_STATUSES
    reason = "" if terminal else f"run state is not terminal: {status!r}"
    return C.measurement(C.MEASURED, terminal, reason), state


def _elapsed(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state or not state.get("started_at") or not state.get("ended_at"):
        return C.measurement(C.MISSING, reason="run timestamps are unavailable")
    try:
        started = dt.datetime.fromisoformat(
            str(state["started_at"]).replace("Z", "+00:00")
        )
        ended = dt.datetime.fromisoformat(
            str(state["ended_at"]).replace("Z", "+00:00")
        )
    except ValueError as exc:
        return C.measurement(C.ERROR, reason=f"invalid run timestamp: {exc}")
    return C.measurement(
        C.MEASURED, max(0.0, (ended - started).total_seconds())
    )


def _usage(workspace: Path) -> dict[str, dict[str, Any]]:
    log_root = workspace / "pipeline/logs"
    paths = sorted(log_root.rglob("*.stdout.jsonl")) if log_root.is_dir() else []
    fields = ("input_tokens", "output_tokens", "nano_aiu", "premium_requests")
    if not paths:
        return {
            field: C.measurement(C.MISSING, reason="Copilot JSONL logs are absent")
            for field in fields
        }
    totals = {field: 0 for field in fields}
    seen = {field: False for field in fields}
    for path in paths:
        events = parse_copilot_jsonl(
            path.read_text(encoding="utf-8", errors="replace")
        )
        summary = summarize_copilot_events(events)
        for field in fields:
            value = getattr(summary, field)
            if value is not None:
                totals[field] += int(value)
                seen[field] = True
    return {
        field: (
            C.measurement(C.MEASURED, totals[field])
            if seen[field]
            else C.measurement(
                C.UNAVAILABLE,
                reason=f"Copilot logs do not expose {field}",
            )
        )
        for field in fields
    }


def _integrity(
    workspace: Path, manifest_row: dict[str, Any]
) -> dict[str, Any]:
    oracle = workspace / "oracle"
    evaluator = workspace / "immutable_evaluator.py"
    if not oracle.is_dir() or not evaluator.is_file():
        return C.measurement(
            C.MISSING, reason="oracle or immutable evaluator is absent"
        )
    if C.tree_sha256(oracle) != manifest_row.get("contract_sha256"):
        return C.measurement(
            C.MEASURED, False, "fixed-contract checksum differs from preparation"
        )
    if C.file_sha256(evaluator) != manifest_row.get("evaluator_sha256"):
        return C.measurement(
            C.MEASURED, False, "immutable-evaluator checksum differs from preparation"
        )
    return C.measurement(C.MEASURED, True)


def _missing_row_metrics(row: dict[str, Any], status: str, reason: str) -> None:
    row["compilation"] = C.measurement(status, reason=reason)
    row["fixed_contract_tests"] = C.measurement(status, reason=reason)
    row["fixed_tests"] = {
        "expected": row["test_count"],
        "executed": 0,
        "passed": 0,
        "failed": 0,
        "not_executed": row["test_count"],
    }
    row["safety"] = C.measurement(status, reason=reason)
    row["evaluation_commands"] = {}


def evaluate_workspace(
    subject: dict[str, Any],
    manifest_row: dict[str, Any],
    *,
    workspace: Path,
    variant: str,
    repetition: int,
    timeout: float,
) -> dict[str, Any]:
    terminal, state = _run_state(workspace)
    integrity = _integrity(workspace, manifest_row)
    row: dict[str, Any] = {
        "subject_id": subject["id"],
        "subject": subject["name"],
        "modules": subject["modules"],
        "module_count": len(subject["modules"]),
        "test_count": len(subject["test_functions"]),
        "c_assertions": subject["c_assertions"],
        "loc_source": subject["loc_source"],
        "variant": variant,
        "repetition": repetition,
        "workspace": str(workspace),
        "pipeline_status": state.get("status") if state else None,
        "pipeline_error": state.get("error", "") if state else "",
        "execution_provenance": state.get("provenance", {}) if state else {},
        "terminal_run": terminal,
        "contract_integrity": integrity,
        "elapsed_seconds": _elapsed(state),
        **_usage(workspace),
    }
    if integrity.get("value") is not True:
        status = (
            integrity.get("status")
            if integrity.get("status") in {C.MISSING, C.UNAVAILABLE}
            else C.ERROR
        )
        _missing_row_metrics(
            row,
            status,
            integrity.get("reason") or "contract integrity is not verified",
        )
        return row
    target = workspace / "pipeline/target"
    if not target.is_dir():
        _missing_row_metrics(row, C.MISSING, "pipeline/target is absent")
        return row

    arguments = {
        "workspace": workspace,
        "target": target,
        "contract_dir": workspace / "oracle",
        "timeout": timeout,
    }
    build = run_workspace_stage("build", **arguments)
    tests = run_workspace_stage("test", **arguments)
    safety = run_workspace_stage("safety", **arguments)
    row["compilation"] = build["measurement"]
    row["fixed_contract_tests"] = tests["measurement"]
    row["fixed_tests"] = tests.get(
        "summary",
        {
            "expected": row["test_count"],
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "not_executed": row["test_count"],
        },
    )
    row["fixed_test_results"] = tests.get("tests", [])
    row["safety"] = safety["measurement"]
    row["evaluation_commands"] = {
        "build": build.get("commands", []),
        "test": tests.get("commands", []),
    }
    return row


def _integration_cargo() -> str:
    return """[package]
name = "vivo_subject_01"
version = "0.1.0"
edition = "2021"
publish = false
autobins = false

[lib]
name = "vivo_subject_01"
path = "src/lib.rs"
crate-type = ["staticlib"]

[build-dependencies]
cc = "=1.4.2"
"""


def _integration_lib(modules: list[str]) -> str:
    lines = [RUST_PREAMBLE.rstrip(), "", "pub mod production {"]
    lines.extend(
        f"    pub mod {module.replace('-', '_')};" for module in modules
    )
    lines.extend(["}", "", "pub mod oracle {", "    pub mod alloc_testing;", "}"])
    return "\n".join(lines) + "\n"


def _integration_build_script(modules: list[str]) -> str:
    if not modules:
        return "fn main() {}\n"
    files = "\n".join(
        f'        .file("fixed/c/{module}.c")' for module in modules
    )
    return f"""fn main() {{
    cc::Build::new()
        .include("fixed/c")
        .include("fixed/test")
        .define("ALLOC_TESTING", None)
{files}
        .compile("vivo_remaining_c");
}}
"""


def _copy_integration_inputs(
    project: Path,
    *,
    config: dict[str, Any],
    workspace_root: Path,
) -> None:
    for subject in config["subjects"]:
        subject_root = workspace_root / str(subject["id"])
        for module in subject["modules"]:
            for suffix in (".c", ".h"):
                shutil.copy2(
                    subject_root / "source/target" / f"{module}{suffix}",
                    project / "fixed/c" / f"{module}{suffix}",
                )
    shutil.copy2(
        workspace_root / "1/source/tests/alloc-testing.h",
        project / "fixed/test/alloc-testing.h",
    )
    shutil.copy2(
        workspace_root / "1/oracle/tests/alloc_testing.rs",
        project / "src/oracle/alloc_testing.rs",
    )
    shutil.copy2(
        workspace_root / "1/oracle/Cargo.lock", project / "Cargo.lock"
    )
    C.atomic_write_text(project / "Cargo.toml", _integration_cargo())
    C.atomic_write_text(
        project / "rust-toolchain.toml",
        f'[toolchain]\nchannel = "{config["tools"]["rust_toolchain"]}"\n',
    )


def _stage_integration_candidate(
    project: Path,
    *,
    modules: list[str],
    rows_by_subject: dict[int, dict[str, Any]],
    subjects_by_identifier: dict[int, dict[str, Any]],
) -> None:
    production = project / "src/production"
    for path in production.glob("*.rs"):
        path.unlink()
    for subject_id, subject in subjects_by_identifier.items():
        for module in subject["modules"]:
            if module not in modules:
                continue
            source = (
                Path(rows_by_subject[subject_id]["workspace"])
                / "pipeline/target/src/production"
                / f"{module.replace('-', '_')}.rs"
            )
            shutil.copy2(
                source, production / f"{module.replace('-', '_')}.rs"
            )
    C.atomic_write_text(project / "src/lib.rs", _integration_lib(modules))


def evaluate_integration(
    *,
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    workspace_root: Path,
    repetition: int,
    timeout: float,
) -> dict[str, Any]:
    rows_by_subject = {
        int(row["subject_id"]): row
        for row in rows
        if int(row["repetition"]) == repetition
    }
    by_id = subjects_by_id(config)
    all_modules = [
        module
        for subject in config["subjects"]
        for module in subject["modules"]
    ]
    accepted: list[str] = []
    steps = []
    with tempfile.TemporaryDirectory(
        prefix=f"evoc2rust-integration-rep{repetition}-"
    ) as temporary:
        project = Path(temporary) / "project"
        (project / "src/production").mkdir(parents=True)
        (project / "src/oracle").mkdir(parents=True)
        (project / "fixed/c").mkdir(parents=True)
        (project / "fixed/test").mkdir(parents=True)
        _copy_integration_inputs(
            project, config=config, workspace_root=workspace_root
        )
        for subject in config["subjects"]:
            subject_id = int(subject["id"])
            row = rows_by_subject[subject_id]
            candidate = [*accepted, *subject["modules"]]
            if (
                row["contract_integrity"].get("value") is not True
                or row["compilation"].get("value") is not True
            ):
                result = {
                    "ok": False,
                    "returncode": None,
                    "timed_out": False,
                    "stdout": "",
                    "stderr": (
                        "individual immutable build did not pass; integration "
                        "was not attempted"
                    ),
                }
            else:
                _stage_integration_candidate(
                    project,
                    modules=candidate,
                    rows_by_subject=rows_by_subject,
                    subjects_by_identifier=by_id,
                )
                remaining = [
                    module for module in all_modules if module not in candidate
                ]
                C.atomic_write_text(
                    project / "build.rs",
                    _integration_build_script(remaining),
                )
                result = run_command(
                    ["cargo", "build", "--locked", "--all-targets"],
                    cwd=project,
                    timeout=timeout,
                )
            if result["ok"]:
                accepted = candidate
            diagnostic = (
                result.get("stderr") or result.get("stdout") or ""
            ).strip()
            steps.append(
                {
                    "subject_id": subject_id,
                    "subject": subject["name"],
                    "modules": subject["modules"],
                    "accepted": result["ok"],
                    "accepted_module_count_after_step": len(accepted),
                    "returncode": result.get("returncode"),
                    "timed_out": result.get("timed_out", False),
                    "diagnostic_tail": diagnostic[-4000:],
                    "output_sha256": hashlib.sha256(
                        (
                            (result.get("stdout") or "")
                            + "\n"
                            + (result.get("stderr") or "")
                        ).encode()
                    ).hexdigest(),
                }
            )
    return {
        "repetition": repetition,
        "module_denominator": len(all_modules),
        "accepted_modules": accepted,
        "accepted_module_count": len(accepted),
        "incremental_compilation_percent": 100.0
        * len(accepted)
        / len(all_modules),
        "steps": steps,
    }


def evaluate_runs(
    *,
    config: dict[str, Any],
    manifest: dict[str, Any],
    workspace_root: Path,
    runs_root: Path,
    variant: str = "full",
    repetitions: int | None = None,
    timeout: float | None = None,
    max_workers: int = 1,
    integration: bool = True,
) -> dict[str, Any]:
    repetitions = repetitions or int(config["protocol"]["repetitions"])
    timeout = timeout or float(config["protocol"]["agent_timeout_seconds"])
    manifest_rows = {
        int(row["subject_id"]): row for row in manifest["projects"]
    }
    jobs = [
        (
            subject,
            manifest_rows[int(subject["id"])],
            runs_root
            / variant
            / str(subject["id"])
            / f"rep{repetition}",
            repetition,
        )
        for repetition in range(repetitions)
        for subject in config["subjects"]
    ]

    def evaluate_one(job):
        subject, manifest_row, workspace, repetition = job
        return evaluate_workspace(
            subject,
            manifest_row,
            workspace=workspace,
            variant=variant,
            repetition=repetition,
            timeout=timeout,
        )

    if max_workers <= 1:
        rows = [evaluate_one(job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            rows = list(pool.map(evaluate_one, jobs))
    integrations = (
        [
            evaluate_integration(
                config=config,
                rows=rows,
                workspace_root=workspace_root,
                repetition=repetition,
                timeout=timeout,
            )
            for repetition in range(repetitions)
        ]
        if integration
        else []
    )
    return {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "paper": config["paper"],
        "artifact": {**config["artifact"], **manifest.get("artifact", {})},
        "protocol": {
            **config["protocol"],
            "evaluated_repetitions": repetitions,
        },
        "workspace_root": str(workspace_root),
        "runs_root": str(runs_root),
        "rows": rows,
        "integration": integrations,
        "preparation_calibration": manifest.get("calibration", {}),
        "preparation_provenance": manifest.get("provenance", {}),
        "provenance": {
            **C.collect_provenance(),
            "cargo": _version(["cargo", "--version"]),
            "rustc": _version(
                [
                    "rustc",
                    f"+{config['tools']['rust_toolchain']}",
                    "--version",
                ]
            ),
        },
    }


def _version(argv: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": C.UNAVAILABLE, "reason": str(exc)}
    text = (result.stdout or result.stderr).strip().splitlines()
    return {
        "status": C.MEASURED if result.returncode == 0 else C.ERROR,
        "returncode": result.returncode,
        "value": text[0] if text else "",
    }


def _csv_row(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "subject_id": row["subject_id"],
        "subject": row["subject"],
        "modules": ",".join(row["modules"]),
        "module_count": row["module_count"],
        "test_count": row["test_count"],
        "repetition": row["repetition"],
        "pipeline_status": row["pipeline_status"],
        "tests_expected": row["fixed_tests"]["expected"],
        "tests_executed": row["fixed_tests"]["executed"],
        "tests_passed": row["fixed_tests"]["passed"],
        "tests_failed": row["fixed_tests"]["failed"],
        "tests_not_executed": row["fixed_tests"]["not_executed"],
    }
    for name in (
        "terminal_run",
        "contract_integrity",
        "compilation",
        "fixed_contract_tests",
        "elapsed_seconds",
        "input_tokens",
        "output_tokens",
        "nano_aiu",
        "premium_requests",
    ):
        C.flatten_measurement(result, name, row[name])
    safety = row["safety"]
    result["safe_rate_status"] = safety.get("status")
    result["safe_rate_reason"] = safety.get("reason", "")
    value = safety.get("value")
    if isinstance(value, dict):
        for name in (
            "total_lines",
            "unsafe_lines",
            "safe_lines",
            "safe_rate_percent",
            "unsafe_functions",
            "unsafe_blocks",
        ):
            result[name] = value.get(name)
    return result


def write_evaluation(
    output_dir: Path, evaluation: dict[str, Any]
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = C.atomic_write_json(output_dir / "evaluation.json", evaluation)
    rows = [_csv_row(row) for row in evaluation["rows"]]
    csv_path = C.write_csv(
        output_dir / "evaluation.csv",
        rows,
        list(rows[0]) if rows else [],
    )
    integration_rows = [
        {
            "repetition": row["repetition"],
            "module_denominator": row["module_denominator"],
            "accepted_module_count": row["accepted_module_count"],
            "incremental_compilation_percent": row[
                "incremental_compilation_percent"
            ],
            "accepted_modules": ",".join(row["accepted_modules"]),
        }
        for row in evaluation["integration"]
    ]
    integration_path = C.write_csv(
        output_dir / "integration.csv",
        integration_rows,
        list(integration_rows[0]) if integration_rows else [],
    )
    return json_path, csv_path, integration_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(C.DEFAULT_CONFIG))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--no-integration", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    manifest = C.read_json(args.manifest)
    evaluation = evaluate_runs(
        config=config,
        manifest=manifest,
        workspace_root=Path(args.workspace_root).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        variant=args.variant,
        repetitions=args.repetitions,
        timeout=args.timeout,
        max_workers=max(1, args.jobs),
        integration=not args.no_integration,
    )
    paths = write_evaluation(Path(args.out).resolve(), evaluation)
    print("wrote " + ", ".join(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
