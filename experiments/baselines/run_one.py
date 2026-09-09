#!/usr/bin/env python3
"""Generate/recover one immutable B0 artifact, then score without pipeline deferrals."""
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
    parser.add_argument("--backend", choices=("copilot", "copilot-api"), default="copilot")
    parser.add_argument("--granularity", choices=("repo", "per-file"), default="repo",
                        help="per-file issues one request per module (AlphaTrans ablation granularity)")
    parser.add_argument("--model", help="CLI defaults to subject config; API requires an explicit supported model")
    parser.add_argument("--effort", help="CLI defaults to subject config; API omits reasoning_effort unless set")
    parser.add_argument("--max-output-tokens", type=int, help="API requires an explicit output cap; CLI cap is not enforced")
    single_shot.add_api_arguments(parser)
    parser.add_argument("--resume-tag", help="linked recovery/continuation, not an independent new sample")
    parser.add_argument("--context", choices=("default", "long_context"),
                        help="CLI only (default long_context); unsupported for API")
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--compare-tag", help="retain and compare against an earlier run of this subject")
    args = parser.parse_args()
    for tag in (args.project, args.tag, args.resume_tag, args.compare_tag):
        if tag is not None:
            single_shot.validate_tag(tag)
    if args.max_rounds < 1:
        raise ValueError("--max-rounds must be positive")
    api_backend = None
    if args.backend == "copilot-api":
        if args.compare_tag:
            raise SystemExit("--compare-tag is currently CLI-only; API observations remain separate")
        api_backend = single_shot.configured_api_backend(args)
    else:
        single_shot.reject_api_arguments(args)
        if args.granularity != "repo":
            raise SystemExit("--granularity per-file currently requires --backend copilot-api")
        args.context = args.context or "long_context"

    subject = single_shot.EXAMPLE / "subjects" / args.project
    run = subject / f"pipeline-baseline-{args.tag}"
    status_file = subject / f"pipeline-baseline-{args.tag}.status.json"
    if run.exists() or status_file.exists():
        raise SystemExit(f"Run tag already exists; refusing to overwrite: {args.tag}")
    config = single_shot.read_config(args.project)
    model = api_backend.model if api_backend is not None else (args.model or config["model"] or "claude-sonnet-5")
    effort = args.effort if api_backend is not None else (args.effort or config["effort"] or "medium")
    reference = None
    source_observation = args.tag
    if args.resume_tag:
        source = subject / f"pipeline-baseline-{args.resume_tag}"
        source_meta_path = source / "metadata.json"
        if not source_meta_path.exists():
            source_meta_path = source / "generation.json"
        source_meta = single_shot.json_object(source_meta_path.read_bytes(), "source metadata")
        source_observation = single_shot.validate_tag(source_meta.get("observation_tag", args.resume_tag))
    if args.compare_tag:
        reference = subject / f"pipeline-baseline-{args.compare_tag}"
        reference_meta = json.loads((reference / "metadata.json").read_text())
        if reference_meta.get("backend") != args.backend:
            raise SystemExit("Reference backend does not match this run; cross-backend selection is unsupported")
        if reference_meta["model"] != model or reference_meta["effort"] != effort:
            raise SystemExit("Reference model/effort do not match this run")
        reference_observation = reference_meta.get("observation_tag", args.compare_tag)
        if reference_observation == source_observation:
            raise SystemExit("Cannot select worst-of-two from recovery tags of the SAME observation")
        reference_score = parse_score((reference / "oracle_score.txt").read_text())

    provenance = (api_backend.provenance() if api_backend is not None else {
        "copilot_version": subprocess.check_output(["copilot", "--version"], text=True).strip(),
        "transport": "copilot-cli",
    })
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=single_shot.REPO, text=True,
    ).strip()
    command = [
        sys.executable, "-u", str(single_shot.HERE / "single_shot.py"),
        "--project", args.project, "--tag", args.tag,
        "--backend", args.backend, "--model", model, "--max-rounds", str(args.max_rounds),
    ]
    if effort is not None:
        command.extend(["--effort", effort])
    if args.context is not None:
        command.extend(["--context", args.context])
    if args.max_output_tokens is not None:
        command.extend(["--max-output-tokens", str(args.max_output_tokens)])
    if api_backend is not None:
        command.extend(["--api-base-url", api_backend.base_url,
                        "--api-token-limit-field", api_backend.token_limit_field,
                        "--api-timeout", str(api_backend.timeout)])
        if args.granularity != "repo":
            command.extend(["--granularity", args.granularity])
        if args.temperature is not None:
            command.extend(["--temperature", str(args.temperature)])
        if args.api_stream:
            command.append("--api-stream")
    if args.resume_tag:
        command.extend(["--resume-tag", args.resume_tag])
    state = {
        "state": "generating", "pid": os.getpid(), "project": args.project,
        "tag": args.tag, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "code_revision": revision, "backend": args.backend, "model": model, "effort": effort,
        **provenance,
        "generation_command": command, "context": args.context,
        "reference_tag": args.compare_tag,
        "resume_tag": args.resume_tag, "observation_tag": source_observation,
        "independent_sample": not bool(args.resume_tag),
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
        "code_revision": revision, "backend": args.backend, "model": model, "effort": effort,
        **provenance,
        "context": args.context, "oracle_score": score,
        "source_hashes": {
            path.relative_to(run / "project").as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((run / "project/src/main").rglob("*.py"))
        },
        "generation_complete": metadata["complete"],
        "observation_tag": metadata["observation_tag"],
        "independent_sample": metadata["independent_sample"],
        "recovery": metadata["recovery"],
        "backend_invocations": metadata["backend_invocations"],
        "new_backend_invocations": metadata["new_backend_invocations"],
        "observed_model_calls": metadata["observed_model_calls"],
        "observed_assistant_turns": metadata["observed_assistant_turns"],
    }
    if api_backend is not None:
        evidence.update(api_audit=metadata["api_audit"], returned_models=metadata["returned_models"],
                        explicit_http_model_requests=metadata["explicit_http_model_requests"])
    else:
        evidence["copilot_audit"] = metadata["copilot_audit"]
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
            "current_observation_tag": metadata["observation_tag"],
            "reference_observation_tag": reference_observation,
            "current_is_linked_recovery": bool(args.resume_tag),
            "recovery_note": (
                "A recovery tag continues the same original observation; it is not another sample."
                if args.resume_tag else None
            ),
            "protocol_note": (
                "Both artifacts retain tool-access audits and context metadata. "
                "Their recorded configuration and code/CLI provenance must be compared "
                "before claiming identical protocols."
                if reference_meta.get("copilot_audit") and reference_meta.get("context") else
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
        backend_invocations=metadata["backend_invocations"],
        new_backend_invocations=metadata["new_backend_invocations"],
        observed_model_calls=metadata["observed_model_calls"],
    )
    write_json(status_file, state)
    print("[batch] completed; all generation artifacts and observed failures retained", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
