#!/usr/bin/env python3
"""Assemble the publishable CRUST results package from the frozen run artifacts.

Mirrors the AlphaTrans publication packages: frozen translations, per-call audits,
a machine-readable scorecard, an isolated scoring wrapper and a manifest. Raw
prompts and event streams stay private; only their hashes are published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SUBJECTS = ("cset", "c-aces", "lambda-calculus-eval", "inversion_list")


def oracle(repo: Path, subject: str, working_copy: str) -> dict:
    result = subprocess.run(
        ["bash", str(repo / "examples/crust/tools/oracle.sh"),
         "--project", subject, "--working-copy", working_copy, "--json"],
        capture_output=True, text=True, timeout=1800)
    line = [ln for ln in result.stdout.splitlines() if ln.startswith("{")]
    if not line:
        return {"state": "oracle_failed", "stderr": result.stderr[-400:]}
    return json.loads(line[-1])


def contract_ok(repo: Path, subject_dir: Path, working_copy: Path) -> bool:
    result = subprocess.run(
        ["bash", str(repo / "examples/crust/tools/build_check.sh"),
         str(working_copy), str(subject_dir / ".scaffold")],
        capture_output=True, text=True, timeout=900)
    return "no longer declares module" not in (result.stdout + result.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--b0-tag", required=True)
    ap.add_argument("--repo-tag", help="whole-repository single-call B0 arm")
    ap.add_argument("--build-tag", required=True)
    ap.add_argument("--test-tag", required=True)
    args = ap.parse_args()

    repo, out = args.repo.resolve(), args.out.resolve()
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    arms = {"b0-per-file": args.b0_tag, "repair-build": args.build_tag,
            "repair-test": args.test_tag}
    if args.repo_tag:
        arms["b0-whole-repo"] = args.repo_tag
    subjects_dir = repo / "examples/crust/subjects"

    results, stub_baseline = [], {}
    for subject in SUBJECTS:
        subject_dir = subjects_dir / subject
        stub_baseline[subject] = oracle(repo, subject, "pipeline/project")
        for arm, tag in arms.items():
            run = subject_dir / f"pipeline-baseline-{tag}"
            if not (run / "project").is_dir():
                results.append({"arm": arm, "subject": subject, "state": "missing"})
                continue
            score = oracle(repo, subject, f"pipeline-baseline-{tag}/project")
            status_path = subject_dir / f"pipeline-baseline-{tag}.status.json"
            status = json.loads(status_path.read_text()) if status_path.is_file() else {}
            audits = sorted((run / "api-audit").glob("*/audit.json")) if (run / "api-audit").is_dir() else []
            usage = [json.loads(p.read_text()) for p in audits]
            results.append({
                "arm": arm, "subject": subject, "tag": tag,
                "oracle": score,
                "contract_intact": contract_ok(repo, subject_dir, run / "project"),
                "api_calls": len(audits),
                "completion_tokens": sum(u.get("usage", {}).get("completion_tokens", 0)
                                         for u in usage) or None,
                "iterations": [
                    {k: v for k, v in it.items() if k in ("iteration", "metric", "status")}
                    for it in status.get("iterations", [])],
            })
            dest = out / "data" / subject / arm
            dest.mkdir(parents=True)
            shutil.copytree(run / "project", dest / "project")
            shutil.rmtree(dest / "project" / "target", ignore_errors=True)
            if (run / "api-audit").is_dir():
                shutil.copytree(run / "api-audit", dest / "api-audit")
            for name in ("oracle_score.txt", "metadata.json", "generation.json"):
                if (run / name).is_file():
                    shutil.copy2(run / name, dest / name)
        meta = out / "metadata" / subject
        meta.mkdir(parents=True)
        shutil.copytree(subject_dir / ".oracle-master", meta / "oracle-master")
        shutil.copy2(subject_dir / ".scaffold" / "src" / "lib.rs", meta / "scaffold-lib.rs")

    normalized: list[dict] = []
    (out / "report").mkdir(parents=True, exist_ok=True)
    (out / "report" / "scorecard.json").write_text(json.dumps({
        "campaign": "CRUST-bench C->Rust baselines and repair",
        "model": "claude-sonnet-5", "reasoning_effort": "medium",
        "stub_baseline": stub_baseline,
        "arms": arms,
        "results": results,
    }, indent=2) + "\n")

    (out / "reproduction").mkdir(parents=True, exist_ok=True)
    for tool in ("oracle.sh", "build_check.sh"):
        shutil.copy2(repo / "examples/crust/tools" / tool, out / "reproduction" / tool)
    shutil.copy2(repo / "examples/crust/setup.sh", out / "reproduction" / "setup.sh")

    rows = []
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.txt":
            continue
        # Machine paths are not results. The AlphaTrans packages normalise them and
        # keep the original hashes in provenance; do the same here so a published
        # artifact does not carry someone's home directory around.
        if path.suffix in (".txt", ".json", ".md", ".log"):
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = None
            if text and str(repo) in text:
                original = hashlib.sha256(path.read_bytes()).hexdigest()
                path.write_text(text.replace(str(repo), "<repo>"), encoding="utf-8")
                normalized.append({"path": str(path.relative_to(out)).replace("\\", "/"),
                                   "sha256_before_normalization": original})
        rows.append((hashlib.sha256(path.read_bytes()).hexdigest(),
                     str(path.relative_to(out)).replace("\\", "/")))
    # Written before the manifest so the manifest covers it too.
    provenance = out / "metadata" / "publication-provenance.json"
    provenance.write_text(json.dumps({
        "note": "Machine paths in textual evidence are normalized to <repo>. "
                "Original hashes are recorded here. Generated code bytes are unchanged.",
        "normalized_files": normalized,
    }, indent=2) + "\n")
    rows.append((hashlib.sha256(provenance.read_bytes()).hexdigest(),
                 str(provenance.relative_to(out)).replace("\\", "/")))
    with (out / "SHA256SUMS.txt").open("w", newline="\n") as fh:
        for digest, rel in sorted(rows, key=lambda r: r[1]):
            fh.write(f"{digest}  {rel}\n")
    print(f"packaged {len(results)} runs, {len(rows)} files, "
          f"{len(normalized)} path-normalized -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
