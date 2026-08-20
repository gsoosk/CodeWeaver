"""Derive Clippy idiomaticity measurements without additional model calls."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from . import common as C


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _diagnostics(output: str) -> list[dict[str, Any]]:
    diagnostics: dict[tuple[Any, ...], dict[str, Any]] = {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("reason") != "compiler-message":
            continue
        message = event.get("message") or {}
        level = message.get("level")
        if level not in {"warning", "error"}:
            continue
        primary = next(
            (
                span
                for span in message.get("spans") or []
                if span.get("is_primary")
            ),
            {},
        )
        code = (message.get("code") or {}).get("code") or ""
        record = {
            "level": level,
            "code": code,
            "message": message.get("message", ""),
            "file": primary.get("file_name", ""),
            "line": primary.get("line_start", ""),
        }
        key = tuple(record.values())
        diagnostics[key] = record
    return list(diagnostics.values())


def analyze_target(
    row: dict[str, str],
    *,
    historical_runs_root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    project_id = row["project_id"]
    repetition = int(row["repetition"])
    target = (
        historical_runs_root
        / project_id
        / f"rep{repetition}"
        / "pipeline"
        / "target"
    )
    base = {
        "project_id": project_id,
        "repetition": repetition,
        "target_function_count": row.get("target_function_count", ""),
        "target_path": str(target),
    }
    if not (target / "Cargo.toml").is_file():
        return {
            **base,
            "status": "missing_target",
            "returncode": "",
            "timed_out": False,
            "warnings": "",
            "errors": "",
            "lint_alerts": "",
            "lint_alerts_per_function": "",
            "diagnostic_codes_json": "{}",
            "stderr_tail": "",
        }
    result = C.run_command(
        [
            "cargo",
            "clippy",
            "--no-deps",
            "--message-format=json",
        ],
        cwd=target,
        timeout=timeout_seconds,
        env={"CARGO_TERM_COLOR": "never"},
    )
    diagnostics = _diagnostics(result["stdout"])
    warnings = sum(row["level"] == "warning" for row in diagnostics)
    errors = sum(row["level"] == "error" for row in diagnostics)
    counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        code = diagnostic["code"] or diagnostic["level"]
        counts[code] = counts.get(code, 0) + 1
    function_count = int(float(row.get("target_function_count") or 0))
    alerts = warnings + errors
    return {
        **base,
        "status": (
            "measured"
            if result["returncode"] == 0
            else "incomplete_timeout"
            if result["timed_out"]
            else "incomplete_compile_error"
        ),
        "returncode": result["returncode"],
        "timed_out": result["timed_out"],
        "warnings": warnings,
        "errors": errors,
        "lint_alerts": alerts,
        "lint_alerts_per_function": (
            alerts / function_count if function_count else ""
        ),
        "diagnostic_codes_json": json.dumps(counts, sort_keys=True),
        "stderr_tail": result["stderr"][-1000:],
    }


def analyze(
    *,
    historical_raw: Path,
    historical_runs_root: Path,
    output: Path,
    workers: int,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in _load_csv(historical_raw)
        if row.get("variant") == "full" and row.get("tool") == "crust"
    ]
    if len(rows) != 300:
        raise ValueError(f"expected 300 full CRUST rows, found {len(rows)}")
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                analyze_target,
                row,
                historical_runs_root=historical_runs_root,
                timeout_seconds=timeout_seconds,
            ): (row["project_id"], row["repetition"])
            for row in rows
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (row["project_id"], row["repetition"]))
    C.write_csv(
        output,
        results,
        [
            "project_id",
            "repetition",
            "status",
            "returncode",
            "timed_out",
            "target_function_count",
            "warnings",
            "errors",
            "lint_alerts",
            "lint_alerts_per_function",
            "diagnostic_codes_json",
            "target_path",
            "stderr_tail",
        ],
    )
    measured = [row for row in results if row["status"] == "measured"]
    incomplete = [
        row for row in results if row["status"].startswith("incomplete_")
    ]
    per_function = [
        float(row["lint_alerts_per_function"])
        for row in measured
        if row["lint_alerts_per_function"] != ""
    ]
    summary = {
        "generated_at": C.utcnow_iso(),
        "rows": len(results),
        "measured_rows": len(measured),
        "incomplete_rows": len(incomplete),
        "clean_rows": len(measured),
        "warning_total": sum(int(row["warnings"]) for row in measured),
        "error_total": sum(int(row["errors"]) for row in measured),
        "incomplete_warning_diagnostics": sum(
            int(row["warnings"]) for row in incomplete
        ),
        "incomplete_error_diagnostics": sum(
            int(row["errors"]) for row in incomplete
        ),
        "mean_lint_alerts": (
            statistics.mean(float(row["lint_alerts"]) for row in measured)
            if measured
            else None
        ),
        "mean_lint_alerts_per_function": (
            statistics.mean(per_function) if per_function else None
        ),
        "command": "cargo clippy --no-deps --message-format=json",
        "deduplication": "level, code, message, primary file, primary line",
    }
    C.atomic_write_json(output.with_suffix(".summary.json"), summary)
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-raw", required=True)
    parser.add_argument("--historical-runs-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=900)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    analyze(
        historical_raw=Path(args.historical_raw),
        historical_runs_root=Path(args.historical_runs_root),
        output=Path(args.output),
        workers=args.workers,
        timeout_seconds=args.timeout_seconds,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
