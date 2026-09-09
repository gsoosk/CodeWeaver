#!/usr/bin/env python3
"""Iterative repair over a frozen B0 artifact, via the direct API backend.

Two arms, following CRUST-bench's split:

  build  -- feedback is `build_check` output only: which modules fail to parse or
            import, and why. The oracle is never consulted, so the arm stays
            TEST-BLIND and is comparable to the generation-only B0 arms.

  test   -- feedback is the oracle's own failure output. This arm is EXPLICITLY
            NOT test-blind. It is not comparable to any test-blind arm and must
            never be reported beside one without saying so.

Each iteration is one API request carrying the current project source plus the
current diagnostics. The source run is copied, never mutated, and every iteration
is scored and audited so the trajectory is inspectable rather than just its end
state. Repair stops early when the signal is clean, when an iteration changes
nothing, or when the arm's own metric stops improving.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import single_shot
from backends.base import Usage
from run_one import parse_score, write_json


MAX_DIAGNOSTIC_CHARS = 60000


def project_blob(source_root: Path) -> str:
    parts = []
    for path in sorted(source_root.rglob("*.py")):
        if path.name == "__init__.py" and not path.read_text(encoding="utf-8").strip():
            continue
        relative = path.relative_to(source_root.parent.parent).as_posix()
        parts.append(f"{{{{{relative}}}}}\n```python\n{path.read_text(encoding='utf-8')}\n```\n")
    return "\n".join(parts)


def build_signal(project: Path, repo: Path) -> tuple[bool, str, dict]:
    """Parse+import check. Never touches the oracle."""
    result = subprocess.run(
        [sys.executable, str(repo / "examples/alphatrans/tools/build_check.py"), str(project.parent)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
    )
    output = result.stdout + result.stderr
    match = re.search(r"build_check: (\d+)/(\d+) modules parse and import", output)
    metric = {"modules_ok": int(match.group(1)) if match else 0,
              "modules_total": int(match.group(2)) if match else None,
              "syntax_or_import_failures": len(
                  [line for line in output.splitlines() if line.startswith(("SYNTAX", "IMPORT"))])}
    return result.returncode == 0, output, metric


def test_signal(subject: str, working_copy: str, repo: Path) -> tuple[bool, str, dict]:
    """Oracle failure output. Test-guided arm only."""
    result = subprocess.run(
        ["bash", str(repo / "examples/alphatrans/tools/oracle.sh"),
         "--project", subject, "--all", "--no-pipeline-skips", "--working-copy", working_copy],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
    )
    output = result.stdout + result.stderr
    try:
        score = parse_score(output)
    except ValueError:
        score = None
    metric = {"score": score}
    return result.returncode == 0, output, metric


def failure_digest(output: str) -> str:
    """Keep the parts a repairer can act on, bounded so one iteration stays sendable."""
    lines = output.splitlines()
    kept, in_block = [], False
    for line in lines:
        if re.match(r"^(_{5,}|={5,}) ", line):
            in_block = line.strip("_= ").lower().startswith(("error", "test", "_"))
        if line.startswith(("SYNTAX", "IMPORT", "FAILED ", "ERROR ", "E   ")) or in_block:
            kept.append(line)
    if not kept:
        kept = lines
    digest = "\n".join(kept)
    if len(digest) > MAX_DIAGNOSTIC_CHARS:
        head = digest[: MAX_DIAGNOSTIC_CHARS // 2]
        tail = digest[-MAX_DIAGNOSTIC_CHARS // 2:]
        digest = f"{head}\n\n... [{len(digest) - MAX_DIAGNOSTIC_CHARS} characters omitted] ...\n\n{tail}"
    return digest


def better(arm: str, current: dict, best: dict | None) -> bool:
    if best is None:
        return True
    if arm == "build":
        return current["modules_ok"] > best["modules_ok"]
    a, b = current.get("score"), best.get("score")
    if a is None:
        return False
    if b is None:
        return True
    # A run that stops erroring at collection is an improvement even if its
    # visible pass count is lower, because more of the suite actually ran.
    if (a["errors"] == 0) != (b["errors"] == 0):
        return a["errors"] == 0
    return a["passed"] > b["passed"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--source-tag", required=True, help="frozen B0 run to repair; never modified")
    parser.add_argument("--tag", required=True, help="new tag for this repair run")
    parser.add_argument("--arm", required=True, choices=("build", "test"))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort")
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--api-base-url")
    parser.add_argument("--api-stream", action="store_true")
    args = parser.parse_args()
    for tag in (args.project, args.tag, args.source_tag):
        single_shot.validate_tag(tag)
    if args.iterations < 1:
        raise SystemExit("--iterations must be positive")

    subject_dir = single_shot.EXAMPLE / "subjects" / args.project
    source = subject_dir / f"pipeline-baseline-{args.source_tag}"
    run = subject_dir / f"pipeline-baseline-{args.tag}"
    status_file = subject_dir / f"pipeline-baseline-{args.tag}.status.json"
    if not (source / "project").is_dir():
        raise SystemExit(f"No source artifact to repair: {source}")
    if run.exists() or status_file.exists():
        raise SystemExit(f"Run tag already exists; refusing to overwrite: {args.tag}")

    source_meta = json.loads((source / "metadata.json").read_text())
    run.mkdir()
    shutil.copytree(source / "project", run / "project")
    project = run / "project"
    source_root = project / "src" / "main"
    audit_dir = run / "api-audit"

    backend = single_shot.build_backend(
        "copilot-api", model=args.model, max_output_tokens=args.max_output_tokens,
        base_url=args.api_base_url, effort=args.effort, stream=args.api_stream,
        audit_dir=audit_dir,
    )
    system = (single_shot.HERE / "prompts" / f"repair_{args.arm}_system.md").read_text(encoding="utf-8")
    template = (single_shot.HERE / "prompts" / f"repair_{args.arm}_user.md").read_text(encoding="utf-8")
    working_copy = f"pipeline-baseline-{args.tag}/project"

    meta = {
        "baseline": f"B0-repair-{args.arm}",
        "project": args.project, "tag": args.tag, "source_tag": args.source_tag,
        "source_baseline": source_meta.get("baseline"),
        "source_granularity": source_meta.get("granularity"),
        "arm": args.arm,
        "feedback_source": "build_check parse/import diagnostics" if args.arm == "build"
                           else "oracle test failures",
        "test_blind": args.arm == "build",
        "oracle_seen": args.arm == "test",
        "oracle_tests_in_prompt": False,
        "backend": "copilot-api", "model": args.model, "effort": args.effort,
        "max_output_tokens": args.max_output_tokens, "max_iterations": args.iterations,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        **single_shot.code_provenance(),
        **backend.provenance(),
        "protocol": (
            "Iterative repair over a frozen B0 artifact. Each iteration is one explicit HTTP "
            "model request carrying the current project source and the current diagnostics; "
            "no tools, no retries, no conversation state between iterations. The source run is "
            "copied, never modified. "
            + ("Feedback is parse/import diagnostics only; the oracle is never consulted during "
               "repair, so this arm remains test-blind."
               if args.arm == "build" else
               "Feedback is the oracle's own failure output. This arm is NOT test-blind and is "
               "not comparable to any test-blind arm.")
        ),
    }
    state = {"state": "repairing", "pid": os.getpid(), **{k: meta[k] for k in
             ("project", "tag", "source_tag", "arm", "test_blind")}, "iterations": []}
    write_json(status_file, state)
    write_json(run / "generation.json", meta)

    signal = (lambda: build_signal(project, single_shot.REPO)) if args.arm == "build" else \
             (lambda: test_signal(args.project, working_copy, single_shot.REPO))

    ok, output, metric = signal()
    (run / "iteration-00-signal.txt").write_text(output, encoding="utf-8")
    history = [{"iteration": 0, "clean": ok, "metric": metric, "api_calls": 0}]
    print(f"[repair] {args.project} {args.arm} baseline: clean={ok} {metric}", flush=True)
    best = metric
    best_files = {p: p.read_bytes() for p in sorted(source_root.rglob("*.py"))}
    best_iteration = 0
    usages = []

    for iteration in range(1, args.iterations + 1):
        if ok:
            print("[repair] signal is clean; stopping", flush=True)
            break
        user = (template
                .replace("{{DIAGNOSTICS}}", failure_digest(output))
                .replace("{{PROJECT_FILES}}", project_blob(source_root)))
        entry = {"iteration": iteration}
        try:
            completion = backend.complete(system, user)
        except (OSError, ValueError) as exc:
            entry.update(status="request_failed", error=f"{type(exc).__name__}: {exc}")
            history.append(entry)
            print(f"[repair] iteration {iteration}: FAILED ({type(exc).__name__})", flush=True)
            break
        usages.append(completion.usage.as_dict())
        emitted = single_shot.completion_files(completion)
        applied, rejected = [], []
        for relative, body in emitted.items():
            target = project / relative
            try:
                target.resolve().relative_to(source_root.resolve())
            except ValueError:
                rejected.append({"path": relative, "reason": "outside src/main"})
                continue
            if not target.is_file():
                rejected.append({"path": relative, "reason": "not an existing module"})
                continue
            try:
                ast.parse(body)
            except SyntaxError as exc:
                rejected.append({"path": relative, "reason": f"does not parse: {exc.msg}"})
                continue
            target.write_text(body.rstrip() + "\n", encoding="utf-8")
            applied.append(relative)
        (run / f"iteration-{iteration:02d}-response.md").write_text(completion.text, encoding="utf-8")
        ok, output, metric = signal()
        (run / f"iteration-{iteration:02d}-signal.txt").write_text(output, encoding="utf-8")
        improved = better(args.arm, metric, best)
        entry.update(status="applied", files_changed=applied, files_rejected=rejected,
                     truncated=bool((completion.raw or {}).get("truncated")),
                     finish_reason=(completion.raw or {}).get("finish_reason"),
                     clean=ok, metric=metric, improved=improved,
                     usage=completion.usage.as_dict())
        history.append(entry)
        print(f"[repair] iteration {iteration}: changed={len(applied)} rejected={len(rejected)} "
              f"clean={ok} improved={improved} {metric}", flush=True)
        if improved:
            best, best_iteration = metric, iteration
            best_files = {p: p.read_bytes() for p in sorted(source_root.rglob("*.py"))}
        if not applied:
            print("[repair] iteration changed nothing; stopping", flush=True)
            break
        if not improved and iteration > best_iteration:
            print("[repair] no improvement over the best iteration; stopping", flush=True)
            break
        state["iterations"] = history
        write_json(status_file, state)

    # Keep the best iteration's tree, not merely the last one.
    for path, content in best_files.items():
        path.write_bytes(content)
    reverted = best_iteration != history[-1]["iteration"]
    if reverted:
        print(f"[repair] restored iteration {best_iteration} (best {args.arm} signal)", flush=True)

    final = subprocess.run(
        ["bash", str(single_shot.REPO / "examples/alphatrans/tools/oracle.sh"),
         "--project", args.project, "--all", "--no-pipeline-skips", "--working-copy", working_copy],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
    )
    (run / "oracle_score.txt").write_text(final.stdout + final.stderr, encoding="utf-8")
    try:
        score = parse_score(final.stdout + final.stderr)
        score["pipeline_deferrals_applied"] = False
        write_json(run / "score.json", score)
    except ValueError as exc:
        score = None
        state["scoring_error"] = str(exc)

    audits = getattr(backend, "audit_records", [])
    meta.update({
        "iterations_run": len([h for h in history if h["iteration"] > 0]),
        "best_iteration": best_iteration,
        "reverted_to_best": reverted,
        "history": history,
        "usage_per_iteration": usages,
        "usage": {k: sum(u[k] for u in usages) for k in Usage.__dataclass_fields__
                  if usages and all(k in u for u in usages)},
        "api_audit": audits,
        "explicit_http_model_requests": sum(a["http_requests"] for a in audits),
        "final_oracle_score": score,
        "source_hashes": {
            p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source_root.rglob("*.py"))},
    })
    (run / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    state.update(state="completed", iterations=history, final_oracle_score=score,
                 best_iteration=best_iteration,
                 finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    write_json(status_file, state)
    print(f"[repair] done; final oracle: {score['summary'] if score else 'not scoreable'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
