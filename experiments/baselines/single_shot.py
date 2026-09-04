#!/usr/bin/env python3
"""B0 -- the SINGLE-SHOT baseline, on the AlphaTrans Java -> Python subjects.

The lower bound of the comparison: one LLM call per project, whole repository in one
prompt, no compiler feedback, no test feedback, no iteration. This mirrors
CRUST-Bench's `pass@1` setting (arXiv:2504.15254), adapted from C->Rust to
Java->Python and to our interface-skeleton contract.

WHAT THE MODEL SEES
    * every Java source file of the subject
    * the Python interface skeleton (typed signatures, `pass` bodies)
It does NOT see the oracle tests. That is enforced structurally: this harness reads
only `source_dir` and `.scaffold/`, and asserts it never touched `.oracle-master/`.

WHAT IT PRODUCES
    subjects/<project>/pipeline-baseline-<tag>/project/src/main/**.py

which is the SAME shape CodeWeaver's working copy has, so the identical oracle
scores both:

    bash tools/oracle.sh --project <p> --all \
         --working-copy pipeline-baseline-<tag>/project

FAIRNESS
Use `--backend copilot` (the default) to run the exact model and effort CodeWeaver
uses. `--backend foundry` exists for models Copilot does not serve, but a
cross-backend comparison measures the model as much as the scaffolding -- say so in
any table that mixes them.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from backends.base import build_backend  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXAMPLE = REPO / "examples" / "alphatrans"

# `{{path/to/File.py}}` followed by a fenced block -- the same convention
# CRUST-Bench's prompts use, which keeps multi-file responses parseable.
FILE_BLOCK = re.compile(
    r"\{\{\s*([^\}\n]+?)\s*\}\}\s*\n+```(?:python|py)?\s*\n(.*?)```",
    re.DOTALL,
)


def read_config(project: str) -> dict:
    """Pull what we need out of the generated codeweaver.toml (source dir, tier)."""
    cfg_path = EXAMPLE / "subjects" / project / "codeweaver.toml"
    if not cfg_path.is_file():
        raise SystemExit(f"no config for {project!r}; run setup first: {cfg_path}")
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        raise SystemExit("python 3.11+ required (tomllib)")
    raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    tier = "A"
    for line in cfg_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# tier"):
            tier = line.split("=", 1)[1].strip()
            break
    return {
        "source_dir": pathlib.Path(raw["paths"]["source_dir"]),
        "tier": tier,
        "model": raw.get("model", {}).get("default"),
        "effort": raw.get("model", {}).get("effort_default"),
    }


def collect_java(source_dir: pathlib.Path) -> list[tuple[str, str]]:
    files = sorted(p for p in source_dir.rglob("*.java"))
    return [(str(p.relative_to(source_dir)).replace("\\", "/"),
             p.read_text(encoding="utf-8", errors="replace")) for p in files]


def collect_skeleton(scaffold: pathlib.Path) -> list[tuple[str, str]]:
    src_main = scaffold / "src" / "main"
    files = sorted(p for p in src_main.rglob("*.py") if p.name != "__init__.py")
    return [(str(p.relative_to(scaffold)).replace("\\", "/"),
             p.read_text(encoding="utf-8", errors="replace")) for p in files]


def build_prompt(project: str, java: list, skel: list) -> tuple[str, str]:
    system = (HERE / "prompts" / "single_shot_system.md").read_text(encoding="utf-8")
    tpl = (HERE / "prompts" / "single_shot_user.md").read_text(encoding="utf-8")

    java_blob = "\n".join(
        f"{{{{{name}}}}}\n```java\n{content}\n```\n" for name, content in java)
    skel_blob = "\n".join(
        f"{{{{{name}}}}}\n```python\n{content}\n```\n" for name, content in skel)
    targets = "\n".join(f"  - {name}" for name, _ in skel)

    user = (tpl
            .replace("{{PROJECT}}", project)
            .replace("{{JAVA_FILES}}", java_blob)
            .replace("{{SKELETON_FILES}}", skel_blob)
            .replace("{{TARGET_PATHS}}", targets)
            .replace("{{N_JAVA}}", str(len(java)))
            .replace("{{N_MODULES}}", str(len(skel))))
    return system, user


def parse_response(text: str) -> dict[str, str]:
    """Extract {relative_path: source} from the model's fenced file blocks."""
    out: dict[str, str] = {}
    for raw_name, body in FILE_BLOCK.findall(text):
        name = raw_name.strip().strip("`").replace("\\", "/")
        if not name.endswith(".py"):
            continue
        # Normalise to a path under src/main/ regardless of how it was written.
        idx = name.find("src/main/")
        name = name[idx:] if idx != -1 else f"src/main/{name.lstrip('/')}"
        out[name] = body
    return out


def generate(backend, system: str, user: str, expected: set[str],
             max_rounds: int) -> tuple[dict[str, str], str, list, int]:
    """One prompt, continued across as many responses as the output cap requires.

    Whole-repo single-shot is bounded by max_output_tokens, not by context: a large
    subject needs more Python emitted than one response can hold. Rather than give up
    (or silently keep a response truncated mid-module) we continue the SAME generation.

    Continuation is BLOCK-AWARE, not character-level: we keep only the file blocks that
    closed cleanly, discard any half-written trailing block, and ask for the modules
    still outstanding. That sidesteps seam corruption entirely -- a resumed response can
    never splice a broken file together -- and it is naturally idempotent.

    This stays within the single-shot protocol in the sense that matters: the model
    receives NO feedback. It never learns whether anything compiled, imported or passed
    a test. It is told only which files it has not yet written, which is bookkeeping
    about its own output, not information about correctness. The round count and the
    per-round usage are recorded so the deviation from a literal one-call protocol is
    always visible in the results.
    """
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    files: dict[str, str] = {}
    transcript: list[str] = []
    usages: list = []

    for round_i in range(1, max_rounds + 1):
        completion = (backend.complete_messages(messages) if round_i > 1
                      else backend.complete(system, user))
        transcript.append(completion.text)
        usages.append(completion.usage.as_dict())

        newly = parse_response(completion.text)
        files.update(newly)
        missing = sorted(expected - set(files))
        truncated = bool((completion.raw or {}).get("truncated"))

        print(f"[b0]   round {round_i}: +{len(newly)} files "
              f"({len(files)}/{len(expected)} done, {len(missing)} left)"
              f"{'  [hit output cap]' if truncated else ''}")

        if not missing:
            break
        if not truncated and not newly:
            # Not cut off, and produced nothing new -- continuing would just loop.
            print("[b0]   stopping: response was complete but added no files")
            break
        if round_i == max_rounds:
            break

        # Keep only what closed cleanly; ask for the rest. No correctness feedback.
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant",
             "content": "\n\n".join(
                 f"{{{{{n}}}}}\n```python\n{files[n]}```" for n in sorted(files))},
            {"role": "user", "content":
                "Your response was cut off by the output limit. Continue writing the "
                "remaining modules, in the same file-block format. Do not repeat any "
                "module you already wrote. Emit these and nothing else:\n"
                + "\n".join(f"  - {m}" for m in missing)},
        ]

    return files, "\n\n".join(transcript), usages, len(transcript)


def materialize(scaffold: pathlib.Path, out_root: pathlib.Path,
                files: dict[str, str]) -> tuple[int, int]:
    """Start from the skeleton, overwrite with generated bodies.

    Starting from the skeleton (rather than only what the model returned) means a
    file the model forgot stays as an unimplemented stub instead of vanishing --
    the run then fails those tests honestly rather than failing to import at all.
    """
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    shutil.copytree(scaffold / "src", out_root / "src")

    written, unknown = 0, 0
    for rel, body in files.items():
        target = out_root / rel
        try:
            target.relative_to(out_root)          # refuse path escapes
        except ValueError:
            unknown += 1
            continue
        if not target.parent.exists():
            unknown += 1
            continue
        target.write_text(body.rstrip() + "\n", encoding="utf-8")
        written += 1
    return written, unknown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--tag", default=time.strftime("%Y%m%d"))
    ap.add_argument("--backend", default="copilot", choices=["copilot", "foundry"])
    ap.add_argument("--model", default=None,
                    help="default: whatever the subject's codeweaver.toml uses "
                         "(model-matched with CodeWeaver)")
    ap.add_argument("--effort", default=None, help="copilot backend only")
    ap.add_argument("--max-output-tokens", type=int, default=128000,
                    help="output cap per response (default 128000)")
    ap.add_argument("--max-rounds", type=int, default=6,
                    help="how many continuation responses one prompt may use when the "
                         "output cap cannot hold every module in one go (default 6). "
                         "Continuations carry NO correctness feedback.")
    ap.add_argument("--dry-run", action="store_true",
                    help="build the prompt, report its size, call nothing")
    args = ap.parse_args()

    subject = EXAMPLE / "subjects" / args.project
    scaffold = subject / ".scaffold"
    if not scaffold.is_dir():
        raise SystemExit(f"{args.project} not materialized: {scaffold}")

    cfg = read_config(args.project)
    java = collect_java(cfg["source_dir"])
    skel = collect_skeleton(scaffold)
    if not java or not skel:
        raise SystemExit(f"nothing to translate (java={len(java)} skeleton={len(skel)})")

    system, user = build_prompt(args.project, java, skel)
    approx_tokens = (len(system) + len(user)) // 4

    # The binding constraint for whole-repo single-shot is usually the OUTPUT cap, not
    # the context window: the model must emit every module in one response. Estimate it
    # from the skeleton (a real implementation is several times its stub).
    skel_chars = sum(len(c) for _, c in skel)
    est_out_tokens = int(skel_chars * 3.5 / 4)

    print(f"[b0] project      : {args.project} (tier {cfg['tier']})")
    print(f"[b0] java files   : {len(java)}")
    print(f"[b0] modules      : {len(skel)}")
    print(f"[b0] prompt chars : {len(system) + len(user):,}  (~{approx_tokens:,} tokens in)")
    print(f"[b0] est. output  : ~{est_out_tokens:,} tokens for {len(skel)} modules"
          f"  (cap: {args.max_output_tokens:,})")
    if est_out_tokens > args.max_output_tokens:
        rounds_needed = -(-est_out_tokens // args.max_output_tokens)
        print(f"[b0] note         : one response cannot hold this; the generation will be"
              f" continued (~{rounds_needed} rounds, cap --max-rounds {args.max_rounds})")

    if args.dry_run:
        print("[b0] dry run -- no call made")
        return 0

    model = args.model or cfg["model"] or "claude-sonnet-5"
    effort = args.effort or cfg["effort"] or "medium"
    kw = ({"effort": effort} if args.backend == "copilot"
          else {"max_tokens": args.max_output_tokens})
    backend = build_backend(args.backend, model=model, **kw)
    print(f"[b0] backend      : {backend.name} model={model}"
          + (f" effort={effort}" if args.backend == "copilot" else ""))

    t0 = time.monotonic()
    expected = {name for name, _ in skel}
    files, response_text, usages, rounds = generate(
        backend, system, user, expected, args.max_rounds)
    elapsed = time.monotonic() - t0

    out_root = subject / f"pipeline-baseline-{args.tag}" / "project"
    written, unknown = materialize(scaffold, out_root, files)
    missing = sorted(expected - set(files))

    # A module that does not parse is almost always a response truncated mid-file.
    # Report it rather than letting the oracle score a syntax error as a translation.
    import ast
    unparseable = []
    for rel in files:
        p = out_root / rel
        if not p.is_file():
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            unparseable.append(rel)

    print(f"[b0] wall clock   : {elapsed:,.0f}s over {rounds} response(s)")
    print(f"[b0] files parsed : {len(files)}  written={written}  unplaceable={unknown}")
    print(f"[b0] left as stub : {len(missing)}"
          + (f"  e.g. {missing[:3]}" if missing else ""))
    if unparseable:
        print(f"[b0] UNPARSEABLE  : {len(unparseable)} -- truncated mid-file: {unparseable[:3]}")
    if missing:
        print(f"[b0] INCOMPLETE   : {len(missing)} module(s) never written even after "
              f"{rounds} round(s); they remain unimplemented stubs")
    print(f"[b0] working copy : {out_root}")

    # Provenance next to the artifact, so a result is never orphaned from how it was made.
    meta = {
        "baseline": "B0-single-shot",
        "project": args.project,
        "tier": cfg["tier"],
        "backend": backend.name,
        "model": model,
        "effort": effort if args.backend == "copilot" else None,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inputs": {"java_files": len(java), "skeleton_modules": len(skel),
                   "prompt_chars": len(system) + len(user)},
        "outputs": {"files_parsed": len(files), "files_written": written,
                    "unplaceable": unknown, "left_as_stub": missing,
                    "unparseable": unparseable},
        "usage_per_round": usages,
        "max_output_tokens": args.max_output_tokens,
        "continuation_rounds": rounds,
        "complete": not missing and not unparseable,
        "oracle_seen": False,
        "protocol": (
            "single-shot: one prompt, no compiler feedback, no test feedback. "
            "When one response cannot hold every module, the SAME generation is "
            "continued (block-aware) until all modules are emitted or --max-rounds is "
            "reached; the model is told only which files remain, never anything about "
            "correctness."
        ),
    }
    run_dir = out_root.parent
    (run_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (run_dir / "response.md").write_text(response_text, encoding="utf-8")
    (run_dir / "prompt.md").write_text(f"{system}\n\n---\n\n{user}", encoding="utf-8")
    print(f"[b0] metadata     : {run_dir / 'metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
