#!/usr/bin/env python3
"""Run one immutable B0 repetition and score it without pipeline deferrals."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import single_shot


def parse_score(output: str) -> dict:
    summaries = re.findall(r"^\[oracle\] result\s*:\s*(.*)$", output, re.MULTILINE)
    exits = re.findall(r"^\[oracle\] exitcode\s*:\s*(\d+)", output, re.MULTILINE)
    if not summaries or not exits:
        raise ValueError("Oracle did not report a result and exit code")
    counts = {key: 0 for key in ("passed", "failed", "skipped", "deselected", "errors")}
    for count, key in re.findall(r"(\d+) (passed|failed|skipped|deselected|errors?)\b", summaries[-1]):
        counts["errors" if key == "error" else key] = int(count)
    if int(exits[-1]) not in (0, 1) or counts["errors"] or not counts["passed"] + counts["failed"]:
        raise ValueError(f"Oracle did not complete normal scoring: {summaries[-1]}")
    return {**counts, "exit_code": int(exits[-1]), "summary": summaries[-1]}


def select_worst(current: dict, reference: dict) -> str:
    for key in ("skipped", "deselected"):
        if current[key] != reference[key]:
            raise ValueError(f"Cannot compare scores with different {key} counts")
    if current["passed"] + current["failed"] != reference["passed"] + reference["failed"]:
        raise ValueError("Cannot compare scores with different test denominators")
    return "current" if current["passed"] < reference["passed"] else "reference"


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--context", choices=("default", "long_context"), default="long_context")
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--compare-tag", help="retain and compare against an earlier run of this subject")
    args = parser.parse_args()

    subject = single_shot.EXAMPLE / "subjects" / args.project
    run = subject / f"pipeline-baseline-{args.tag}"
    status_file = subject / f"pipeline-baseline-{args.tag}.status.json"
    if run.exists() or status_file.exists():
        raise SystemExit(f"Run tag already exists; refusing to overwrite: {args.tag}")
    config = single_shot.read_config(args.project)
    reference = None
    if args.compare_tag:
        reference = subject / f"pipeline-baseline-{args.compare_tag}"
        reference_meta = json.loads((reference / "metadata.json").read_text())
        if reference_meta["model"] != config["model"] or reference_meta["effort"] != config["effort"]:
            raise SystemExit("Reference model/effort do not match this run")
        reference_score = parse_score((reference / "oracle_score.txt").read_text())

    version = subprocess.check_output(["copilot", "--version"], text=True).strip()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=single_shot.REPO, text=True,
    ).strip()
    command = [
        sys.executable, "-u", str(single_shot.HERE / "single_shot.py"),
        "--project", args.project, "--tag", args.tag,
        "--backend", "copilot", "--model", config["model"], "--effort", config["effort"],
        "--context", args.context, "--max-rounds", str(args.max_rounds),
    ]
    state = {
        "state": "generating", "pid": os.getpid(), "project": args.project,
        "tag": args.tag, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "code_revision": revision, "copilot_version": version,
        "generation_command": command, "context": args.context,
        "reference_tag": args.compare_tag,
    }
    write_json(status_file, state)
    print(f"[batch] status: {status_file}", flush=True)
    generation = subprocess.run(command, cwd=single_shot.REPO)
    if generation.returncode:
        state.update(state="generation_failed", exit_code=generation.returncode)
        write_json(status_file, state)
        return generation.returncode

    state["state"] = "scoring"
    write_json(status_file, state)
    score_command = [
        "bash", str(single_shot.EXAMPLE / "tools/oracle.sh"),
        "--project", args.project, "--all", "--no-pipeline-skips",
        "--working-copy", f"pipeline-baseline-{args.tag}/project",
    ]
    try:
        scored = subprocess.run(
            score_command, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600,
        )
    except subprocess.TimeoutExpired:
        state.update(state="scoring_failed", error="Oracle exceeded 600 seconds")
        write_json(status_file, state)
        raise
    (run / "oracle_score.txt").write_text(scored.stdout, encoding="utf-8")
    try:
        score = parse_score(scored.stdout)
        if scored.returncode != score["exit_code"]:
            raise ValueError("Oracle process and reported exit codes disagree")
    except ValueError as exc:
        state.update(state="scoring_failed", error=str(exc), exit_code=scored.returncode)
        write_json(status_file, state)
        print(f"[batch] scoring failed: {exc}", file=sys.stderr)
        return 2
    score["pipeline_deferrals_applied"] = False
    write_json(run / "score.json", score)
    print(f"[batch] oracle: {score['summary']}", flush=True)

    metadata = json.loads((run / "metadata.json").read_text())
    evidence = {
        "code_revision": revision, "copilot_version": version,
        "context": args.context, "oracle_score": score,
        "source_hashes": {
            path.relative_to(run / "project").as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((run / "project/src/main").rglob("*.py"))
        },
        "generation_complete": metadata["complete"],
        "copilot_audit": metadata["copilot_audit"],
    }
    write_json(run / "run_evidence.json", evidence)
    if reference is not None:
        try:
            selected = select_worst(score, reference_score)
        except ValueError as exc:
            state.update(state="comparison_failed", error=str(exc), oracle_score=score)
            write_json(status_file, state)
            return 2
        selection = {
            "policy": "worst-of-two; selected minimum pass count, not an unselected pass@1 estimate",
            "current_tag": args.tag, "reference_tag": args.compare_tag,
            "current_score": score, "reference_score": reference_score,
            "selected_tag": args.tag if selected == "current" else args.compare_tag,
            "new_run_is_worse": selected == "current",
            "both_runs_retained": True,
            "protocol_note": (
                "The original run has no tool-access audit and no recorded context tier. "
                "This run disables tools, audits all responses, and records the explicit "
                "context tier and CLI version. They are not identical-protocol repetitions."
            ),
        }
        write_json(run / "selection.json", selection)
        state["selected_tag"] = selection["selected_tag"]
        print(f"[batch] worst-of-two selection: {selection['selected_tag']}", flush=True)
    state.update(
        state="completed", finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        generation_complete=metadata["complete"], oracle_score=score,
    )
    write_json(status_file, state)
    print("[batch] completed; all generation artifacts and observed failures retained", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
