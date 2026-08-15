"""Independently evaluate RepoTransBench and RustRepoTrans campaign runs."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from . import common as C
from .config import REPOTRANSBENCH_SUBJECTS, RUSTREPOTRANS_SUBJECTS

RUN_STATE = "recodeagent_run_state.json"
TERMINAL_STATUSES = {"completed", "failed", "timeout"}


def _contains_symlink(root: Path) -> bool:
    return any(path.is_symlink() for path in root.rglob("*"))


def _copy_candidate_java(candidate: Path, evaluation: Path) -> list[Path]:
    source_root = candidate / "src" / "main" / "java"
    if not source_root.is_dir():
        return []
    copied: list[Path] = []
    for source in sorted(source_root.rglob("*.java")):
        relative = source.relative_to(source_root)
        destination = evaluation / "src" / "main" / "java" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied


def _parse_surefire(root: Path) -> dict[str, int]:
    counts = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "modules_total": 0,
        "modules_passed": 0,
    }
    for path in sorted(root.rglob("target/surefire-reports/TEST-*.xml")):
        suite = ET.parse(path).getroot()
        total = int(suite.attrib.get("tests", 0))
        failed = int(suite.attrib.get("failures", 0))
        errors = int(suite.attrib.get("errors", 0))
        skipped = int(suite.attrib.get("skipped", 0))
        counts["modules_total"] += 1
        if total > 0 and failed == 0 and errors == 0 and skipped == 0:
            counts["modules_passed"] += 1
        counts["total"] += total
        counts["failed"] += failed
        counts["errors"] += errors
        counts["skipped"] += skipped
        counts["passed"] += total - failed - errors - skipped
    return counts


def _mask_rust(text: str) -> str:
    chars = list(text)
    index = 0
    block_depth = 0
    mode = "code"
    while index < len(chars):
        current = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if mode == "code":
            if current == "/" and following == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                mode = "line_comment"
                continue
            if current == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                index += 2
                block_depth = 1
                mode = "block_comment"
                continue
            if current == '"':
                chars[index] = " "
                index += 1
                mode = "string"
                continue
            if current == "'":
                # A lifetime is code; a character literal contains a closing quote.
                closing = text.find("'", index + 1, min(len(text), index + 8))
                if closing >= 0:
                    chars[index] = " "
                    index += 1
                    mode = "character"
                    continue
        elif mode == "line_comment":
            if current == "\n":
                mode = "code"
            else:
                chars[index] = " "
            index += 1
            continue
        elif mode == "block_comment":
            if current == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                block_depth += 1
                index += 2
                continue
            if current == "*" and following == "/":
                chars[index] = chars[index + 1] = " "
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    mode = "code"
                continue
            if current != "\n":
                chars[index] = " "
            index += 1
            continue
        elif mode in {"string", "character"}:
            closing = '"' if mode == "string" else "'"
            if current == "\\" and following:
                chars[index] = chars[index + 1] = " "
                index += 2
                continue
            if current == closing:
                chars[index] = " "
                mode = "code"
            elif current != "\n":
                chars[index] = " "
            index += 1
            continue
        index += 1
    return "".join(chars)


def extract_rust_function(text: str, signature: str) -> str:
    name_match = re.search(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)", signature)
    if not name_match:
        raise ValueError(f"cannot determine function name from {signature!r}")
    name = name_match.group(1)
    masked = _mask_rust(text)
    matches = list(re.finditer(rf"\bfn\s+{re.escape(name)}\b", masked))
    if len(matches) != 1:
        raise ValueError(f"expected one Rust function {name!r}, found {len(matches)}")
    start = matches[0].start()
    while start > 0 and masked[start - 1] not in "\n}":
        start -= 1
    while start < len(text) and text[start] in " \t":
        start += 1
    opening = masked.find("{", matches[0].end())
    if opening < 0:
        raise ValueError(f"function {name!r} has no body")
    depth = 1
    cursor = opening + 1
    while cursor < len(masked) and depth:
        if masked[cursor] == "{":
            depth += 1
        elif masked[cursor] == "}":
            depth -= 1
        cursor += 1
    if depth:
        raise ValueError(f"function {name!r} has an unbalanced body")
    return text[start:cursor].strip()


def _replace_stub(path: Path, signature: str, function: str) -> None:
    content = path.read_text(encoding="utf-8")
    name = re.search(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)", signature)
    if not name:
        raise ValueError(f"invalid signature: {signature}")
    stub = extract_rust_function(content, signature)
    if "RustRepoTrans translation required" not in stub:
        raise ValueError(f"trusted stub missing in {path}")
    path.write_text(content.replace(stub, function, 1), encoding="utf-8")


def _parse_cargo_tests(output: str) -> dict[str, int]:
    passed = failed = ignored = measured = filtered = 0
    pattern = re.compile(
        r"test result: (?:ok|FAILED)\.\s+"
        r"(\d+) passed;\s+(\d+) failed;\s+(\d+) ignored;\s+"
        r"(\d+) measured;\s+(\d+) filtered out"
    )
    for match in pattern.finditer(output):
        values = [int(value) for value in match.groups()]
        passed += values[0]
        failed += values[1]
        ignored += values[2]
        measured += values[3]
        filtered += values[4]
    return {
        "total": passed + failed + ignored,
        "passed": passed,
        "failed": failed,
        "ignored": ignored,
        "measured": measured,
        "filtered_out": filtered,
    }


def _state(run_dir: Path) -> dict[str, Any]:
    path = run_dir / RUN_STATE
    return C.read_json(path) if path.exists() else {"status": "missing"}


def _write_command_log(root: Path, name: str, result: dict[str, Any]) -> None:
    log = {key: value for key, value in result.items() if key not in {"stdout", "stderr"}}
    C.atomic_write_json(root / f"{name}.json", log)
    C.atomic_write_text(root / f"{name}.stdout.log", result["stdout"])
    C.atomic_write_text(root / f"{name}.stderr.log", result["stderr"])


def evaluate_repotransbench_run(
    subject: dict[str, Any],
    *,
    repetition: int,
    workspace_root: Path,
    runs_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    run_dir = runs_root / "full" / subject["id"] / f"rep{repetition}"
    candidate = run_dir / "pipeline" / "target"
    prepared = workspace_root / subject["id"]
    state = _state(run_dir)
    terminal = state.get("status") in TERMINAL_STATUSES
    row: dict[str, Any] = {
        "campaign": "repotransbench",
        "subject_id": subject["id"],
        "subject": subject["name"],
        "source_language": "Python",
        "target_language": "Java",
        "repetition": repetition,
        "run_status": state.get("status", "missing"),
        "expected_tests": subject["tests"],
        "build": False,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_errors": 0,
        "tests_skipped": 0,
        "tests_not_executed": subject["tests"],
        "pass_all": False,
        "evaluation_status": "measured" if terminal else "not_measured",
        "candidate_status": "missing_candidate",
    }
    if not terminal:
        return row
    if not candidate.is_dir() or _contains_symlink(candidate):
        row["candidate_status"] = (
            "candidate_symlink_rejected" if candidate.is_dir() else "missing_candidate"
        )
        return row
    log_root = output_root / "logs" / subject["id"] / f"rep{repetition}"
    generated_root = output_root / "generated" / subject["id"] / f"rep{repetition}"
    with tempfile.TemporaryDirectory(prefix="repotransbench-eval-") as temporary:
        evaluation = Path(temporary) / "project"
        C.copytree_clean(prepared / "scaffold", evaluation)
        copied = _copy_candidate_java(candidate, evaluation)
        if not copied:
            row["candidate_status"] = "missing_production_java"
            return row
        generated_root.mkdir(parents=True, exist_ok=True)
        for path in copied:
            relative = path.relative_to(evaluation / "src" / "main" / "java")
            destination = generated_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        build = C.run_command(
            ["mvn", "-q", "-B", "-DskipTests", "package"],
            cwd=evaluation,
            timeout=1200,
            env={"MAVEN_OPTS": "-Dstyle.color=never"},
        )
        tests = C.run_command(
            ["mvn", "-q", "-B", "test"],
            cwd=evaluation,
            timeout=1200,
            env={"MAVEN_OPTS": "-Dstyle.color=never"},
        )
        _write_command_log(log_root, "build", build)
        _write_command_log(log_root, "tests", tests)
        counts = _parse_surefire(evaluation)
    row.update(
        {
            "build": build["returncode"] == 0,
            "build_returncode": build["returncode"],
            "test_returncode": tests["returncode"],
            "tests_total": counts["total"],
            "tests_passed": counts["passed"],
            "tests_failed": counts["failed"],
            "tests_errors": counts["errors"],
            "tests_skipped": counts["skipped"],
            "test_modules_total": counts["modules_total"],
            "test_modules_passed": counts["modules_passed"],
            "tests_not_executed": max(0, subject["tests"] - counts["total"]),
            "generated_files": len(copied),
            "candidate_status": "evaluated",
        }
    )
    row["pass_all"] = bool(
        row["build"]
        and tests["returncode"] == 0
        and counts["passed"] >= subject["tests"]
        and counts["failed"] == 0
        and counts["errors"] == 0
        and counts["skipped"] == 0
    )
    return row


def evaluate_rustrepotrans_run(
    subject: dict[str, Any],
    *,
    repetition: int,
    workspace_root: Path,
    runs_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    run_dir = runs_root / "full" / subject["id"] / f"rep{repetition}"
    candidate = run_dir / "pipeline" / "target"
    prepared = workspace_root / subject["id"]
    state = _state(run_dir)
    metadata = C.read_json(prepared / "prepared.json")
    terminal = state.get("status") in TERMINAL_STATUSES
    row: dict[str, Any] = {
        "campaign": "rustrepotrans",
        "subject_id": subject["id"],
        "subject": subject["name"],
        "source_language": subject["source_language"],
        "target_language": "Rust",
        "repetition": repetition,
        "run_status": state.get("status", "missing"),
        "expected_tests": subject["expected_tests"],
        "build": False,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_ignored": 0,
        "tests_not_executed": subject["expected_tests"],
        "pass_all": False,
        "evaluation_status": "measured" if terminal else "not_measured",
        "candidate_status": "missing_candidate",
    }
    if not terminal:
        return row
    if not candidate.is_dir() or _contains_symlink(candidate):
        row["candidate_status"] = (
            "candidate_symlink_rejected" if candidate.is_dir() else "missing_candidate"
        )
        return row
    candidate_file = candidate / subject["target_rel_path"]
    if not candidate_file.is_file():
        row["candidate_status"] = "missing_target_file"
        return row
    try:
        function = extract_rust_function(
            candidate_file.read_text(encoding="utf-8"), metadata["target_signature"]
        )
    except (OSError, UnicodeError, ValueError) as exc:
        row["candidate_status"] = "function_extraction_failed"
        row["evaluation_reason"] = str(exc)
        return row
    if "RustRepoTrans translation required" in function:
        row["candidate_status"] = "stub_remaining"
        return row
    generated = (
        output_root
        / "generated"
        / subject["id"]
        / f"rep{repetition}"
        / "translated_function.rs"
    )
    C.atomic_write_text(generated, function + "\n")
    log_root = output_root / "logs" / subject["id"] / f"rep{repetition}"
    with tempfile.TemporaryDirectory(prefix="rustrepotrans-eval-") as temporary:
        evaluation = Path(temporary) / "project"
        C.copytree_clean(prepared / "scaffold", evaluation)
        _replace_stub(
            evaluation / subject["target_rel_path"],
            metadata["target_signature"],
            function,
        )
        build = C.run_command(
            subject["build_command"],
            cwd=evaluation,
            timeout=1800,
            env={"CARGO_TERM_COLOR": "never"},
        )
        tests = C.run_command(
            subject["test_command"],
            cwd=evaluation,
            timeout=2400,
            env={"CARGO_TERM_COLOR": "never"},
        )
        _write_command_log(log_root, "build", build)
        _write_command_log(log_root, "tests", tests)
        counts = _parse_cargo_tests(tests["stdout"] + "\n" + tests["stderr"])
    row.update(
        {
            "build": build["returncode"] == 0,
            "build_returncode": build["returncode"],
            "test_returncode": tests["returncode"],
            "tests_total": counts["total"],
            "tests_passed": counts["passed"],
            "tests_failed": counts["failed"],
            "tests_ignored": counts["ignored"],
            "tests_not_executed": max(
                0, subject["expected_tests"] - counts["total"]
            ),
            "generated_function_sha256": C.sha256_text(function),
            "candidate_status": "evaluated",
        }
    )
    row["pass_all"] = bool(
        row["build"]
        and tests["returncode"] == 0
        and counts["passed"] >= subject["expected_tests"]
        and counts["failed"] == 0
        and counts["ignored"] == 0
    )
    return row


def evaluate_campaign(
    campaign: str,
    *,
    workspace_root: Path,
    runs_root: Path,
    output_root: Path,
    repetitions: int = 3,
) -> list[dict[str, Any]]:
    subjects = (
        REPOTRANSBENCH_SUBJECTS
        if campaign == "repotransbench"
        else RUSTREPOTRANS_SUBJECTS
    )
    evaluator = (
        evaluate_repotransbench_run
        if campaign == "repotransbench"
        else evaluate_rustrepotrans_run
    )
    rows = [
        evaluator(
            subject,
            repetition=repetition,
            workspace_root=workspace_root,
            runs_root=runs_root,
            output_root=output_root,
        )
        for subject in subjects
        for repetition in range(repetitions)
    ]
    output_root.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    C.write_csv(output_root / "raw_runs.csv", rows, fields)
    C.atomic_write_text(
        output_root / "raw_runs.jsonl",
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
    )
    C.atomic_write_json(
        output_root / "summary.json",
        {
            "generated_at": C.utcnow_iso(),
            "campaign": campaign,
            "rows": len(rows),
            "measured": sum(row["evaluation_status"] == "measured" for row in rows),
            "build_passed": sum(bool(row.get("build")) for row in rows),
            "pass_all": sum(bool(row.get("pass_all")) for row in rows),
            "expected_rows": len(subjects) * repetitions,
            "complete": len(rows) == len(subjects) * repetitions
            and all(row["evaluation_status"] == "measured" for row in rows),
        },
    )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=["repotransbench", "rustrepotrans"], required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = evaluate_campaign(
        args.campaign,
        workspace_root=Path(args.workspace_root),
        runs_root=Path(args.runs_root),
        output_root=Path(args.output_root),
        repetitions=args.repetitions,
    )
    passed = sum(bool(row.get("pass_all")) for row in rows)
    print(f"evaluated {len(rows)} rows; {passed} pass all fixed tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
