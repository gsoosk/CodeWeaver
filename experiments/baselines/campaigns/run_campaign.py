#!/usr/bin/env python3
"""Sequential multi-subject campaign driver for the B0 baseline arms.

Consolidates the per-campaign controllers used for the published runs into one
parameterised entry point. The exact invocation behind each published result is
listed in `README.md`; this script reproduces those runs, but it is a consolidation
of four near-identical controllers rather than a byte-identical copy of any one.

Subjects run **sequentially** with a pause between them. The upstream proxy is
unofficial and rate-sensitive, so nothing here parallelises model calls or retries.

A non-200 HTTP status is treated as systemic — auth, quota or policy — and stops the
whole campaign rather than burning the remaining budget against it. A run that
generates but fails to score is recorded and the campaign continues, because a
translation that cannot be collected is a real result, not an infrastructure error.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
BASELINES = HERE.parent
REPO = BASELINES.parent.parent
SUBJECTS = ("commons-cli", "commons-csv", "commons-fileupload", "commons-validator")


def load_catalog(path: Path, model: str, *, need_output: int, need_effort: str | None,
                 need_stream: bool) -> dict:
    """Refuse to run against settings the provider does not actually advertise."""
    catalog = json.loads(path.read_text())
    entry = next((m for m in catalog["data"] if m["id"] == model), None)
    if entry is None:
        raise SystemExit(f"Model {model!r} is not in the catalog at {path}")
    policy = (entry.get("policy") or {}).get("state")
    if policy not in (None, "enabled"):
        raise SystemExit(f"Model {model!r} is not enabled (policy state: {policy})")
    capabilities = entry.get("capabilities") or {}
    limits = capabilities.get("limits") or {}
    supports = capabilities.get("supports") or {}
    if limits.get("max_output_tokens", 0) < need_output:
        raise SystemExit(
            f"{model!r} advertises {limits.get('max_output_tokens')} output tokens, "
            f"less than the requested {need_output}")
    if need_stream and not supports.get("streaming"):
        raise SystemExit(f"{model!r} does not advertise streaming")
    if need_effort and need_effort not in (supports.get("reasoning_effort") or []):
        raise SystemExit(f"{model!r} does not advertise reasoning effort {need_effort!r}")
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", required=True, choices=("generate", "repair"),
                        help="generate: run B0. repair: iterate over an existing B0 artifact.")
    parser.add_argument("--example", default="alphatrans", choices=("alphatrans", "crust"),
                        help="translation example: alphatrans (Java->Python) or crust (C->Rust). "
                             "Selects which examples/<name>/subjects tree the run targets.")
    parser.add_argument("--tag", required=True, help="result tag; must not already exist")
    parser.add_argument("--campaign-dir", type=Path, required=True,
                        help="directory for campaign status and per-run logs; must not exist")
    parser.add_argument("--model-catalog", type=Path, required=True,
                        help="JSON from the proxy's GET /v1/models, used to validate settings")
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--subjects", nargs="+", default=list(SUBJECTS))
    parser.add_argument("--pause-seconds", type=float, default=30.0)
    parser.add_argument("--granularity", choices=("repo", "per-file"), default="per-file",
                        help="generate mode only")
    parser.add_argument("--max-rounds", type=int, default=1,
                        help="generate mode: TOTAL backend invocations per subject; 1 is the "
                             "strict single call")
    parser.add_argument("--source-tag", help="repair mode: the frozen artifact to repair")
    parser.add_argument("--arms", nargs="+", default=["build", "test"], choices=("build", "test"),
                        help="repair mode only")
    parser.add_argument("--iterations", type=int, default=3, help="repair mode only")
    args = parser.parse_args()

    if args.mode == "repair" and not args.source_tag:
        raise SystemExit("--source-tag is required in repair mode")
    if args.campaign_dir.exists():
        raise SystemExit(f"Campaign directory already exists: {args.campaign_dir}")
    # A second campaign writing the same tag corrupts both: they interleave runs and
    # overwrite each other's status file, and the result is unattributable. Refuse.
    live = subprocess.run(["pgrep", "-af", "run_campaign.py"], capture_output=True, text=True)
    others = [ln for ln in live.stdout.splitlines()
              if str(os.getpid()) not in ln.split(None, 1)[0]]
    conflicting = [ln for ln in others if f"--tag {args.tag}" in ln or args.tag in ln]
    if conflicting:
        raise SystemExit("Another campaign is already running with this tag:\n  " +
                         "\n  ".join(conflicting))
    if "COPILOT_API_KEY" not in os.environ:
        print("[campaign] note: COPILOT_API_KEY is unset; the proxy must not require a local key",
              file=sys.stderr)

    entry = load_catalog(args.model_catalog, args.model, need_output=args.max_output_tokens,
                         need_effort=args.effort, need_stream=True)
    args.campaign_dir.mkdir(parents=True)
    subjects_dir = REPO / "examples" / args.example / "subjects"

    plan = [(arm, subject) for arm in (args.arms if args.mode == "repair" else [args.granularity])
            for subject in args.subjects]
    state = {
        "mode": args.mode, "state": "running", "pid": os.getpid(), "tag": args.tag,
        "example": args.example,
        "model": args.model, "reasoning_effort": args.effort,
        "max_output_tokens": args.max_output_tokens, "streaming": True,
        "model_catalog_entry": entry,
        "schedule": f"sequential; {args.pause_seconds}s before each run",
        "runs": {},
    }
    if args.mode == "generate":
        state.update(granularity=args.granularity, max_rounds_per_subject=args.max_rounds)
    else:
        state.update(source_tag=args.source_tag, iterations_per_run=args.iterations,
                     arms={"build": {"feedback": "build_check parse/import diagnostics",
                                     "test_blind": True},
                           "test": {"feedback": "oracle test failures", "test_blind": False}})

    def save():
        temporary = args.campaign_dir / "status.json.tmp"
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(args.campaign_dir / "status.json")

    save()
    for label, subject in plan:
        key = f"{label}/{subject}" if args.mode == "repair" else subject
        state["runs"][key] = {"state": "waiting"}
        save()
        time.sleep(args.pause_seconds)
        if args.mode == "generate":
            command = [
                sys.executable, "-u", str(BASELINES / "run_one.py"),
                "--project", subject, "--tag", args.tag, "--backend", "copilot-api",
                "--example", args.example,
                "--granularity", args.granularity, "--model", args.model,
                "--effort", args.effort, "--max-output-tokens", str(args.max_output_tokens),
                "--api-stream", "--max-rounds", str(args.max_rounds),
            ]
        else:
            command = [
                sys.executable, "-u", str(BASELINES / "repair_loop.py"),
                "--project", subject, "--source-tag", args.source_tag, "--tag", args.tag,
                "--example", args.example,
                "--arm", label, "--iterations", str(args.iterations),
                "--model", args.model, "--effort", args.effort,
                "--max-output-tokens", str(args.max_output_tokens), "--api-stream",
            ]
        print(f"[campaign] {key} starting", flush=True)
        state["runs"][key] = {"state": "running", "started": time.time()}
        save()
        with (args.campaign_dir / f"{key.replace('/', '-')}.log").open("x") as log:
            result = subprocess.run(command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT)

        status_path = subjects_dir / subject / f"pipeline-baseline-{args.tag}.status.json"
        outcome = {"state": "failed_without_status", "exit_code": result.returncode}
        statuses = []
        if status_path.exists():
            status = json.loads(status_path.read_text())
            outcome = {
                "state": status["state"], "exit_code": result.returncode,
                "oracle_score": status.get("final_oracle_score") or status.get("oracle_score"),
                "scoring_error": status.get("scoring_error") or status.get("error"),
            }
            # A worker that died mid-run leaves its last in-progress state behind.
            # Treating that as a result would silently publish a partial artifact.
            if status["state"] in ("running", "repairing", "generating", "scoring"):
                outcome["state"] = "died_in_state_" + status["state"]
        audit_root = subjects_dir / subject / f"pipeline-baseline-{args.tag}" / "api-audit"
        if audit_root.is_dir():
            audits = [json.loads(p.read_text()) for p in sorted(audit_root.glob("round-*/audit.json"))]
            outcome["api_calls"] = len(audits)
            statuses = [a.get("http_status") for a in audits]
        state["runs"][key] = outcome
        save()
        print(f"[campaign] {key}: {outcome['state']} (exit {result.returncode}, "
              f"{outcome.get('api_calls', 0)} calls)", flush=True)

        if any(s not in (None, 200) for s in statuses):
            state["state"] = "stopped_systemic_http_failure"
            save()
            raise SystemExit(f"Non-200 API response in {key}; stopping rather than continuing")
        if outcome["state"] == "failed_without_status":
            state["state"] = "stopped"
            save()
            raise SystemExit(f"{key} failed before recording status; stopping")
        if outcome["state"].startswith("died_in_state_"):
            state["state"] = "stopped_worker_died"
            save()
            raise SystemExit(
                f"{key} died mid-run ({outcome['state']}); stopping rather than "
                f"continuing with a partial artifact")
    state["state"] = "completed"
    save()
    print("[campaign] all runs attempted; source artifacts unchanged", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
