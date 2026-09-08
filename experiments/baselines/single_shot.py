#!/usr/bin/env python3
"""B0 -- the SINGLE-SHOT baseline, on the AlphaTrans Java -> Python subjects.

The lower bound of the comparison: one generation per project, whole repository in
one prompt, no compiler or test feedback. Output-only continuations are not fresh
samples; CLI invocations and internal model turns are counted separately. This adapts
CRUST-Bench's `pass@1` setting (arXiv:2504.15254), adapted from C->Rust to
Java->Python and to our interface-skeleton contract.

WHAT THE MODEL SEES
    * every Java source file of the subject
    * the Python interface skeleton (typed signatures, `pass` bodies)
Oracle tests are not included in the prompt. The Copilot backend additionally
disables tools and audits the event stream; the original permissive B0 run did not
provide this access-control evidence.

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
from dataclasses import dataclass, field
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from backends.base import Completion, Usage, build_backend  # noqa: E402
from backends.copilot import checked_number, command, decode_events, flatten_messages, strict_json  # noqa: E402

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
        if ":" in name or any(part in (".", "..") for part in name.split("/")):
            continue
        out[name] = body
    return out


def completion_files(completion: Completion) -> dict[str, str]:
    """Only closed blocks within one assistant message count, never stitched tails."""
    parts = (completion.raw or {}).get("assistant_messages", [completion.text])
    if not isinstance(parts, list) or any(not isinstance(part, str) for part in parts):
        raise ValueError("Invalid completion assistant_messages")
    files: dict[str, str] = {}
    for part in parts:
        files.update(parse_response(part))
    return files


def continuation_messages(system: str, user: str, files: dict[str, str],
                          expected: set[str], *, legacy: bool = False) -> list[dict]:
    instruction = (
        "Your response was cut off by the output limit. Continue writing the "
        "remaining modules, in the same file-block format. Do not repeat any "
        "module you already wrote. Emit these and nothing else:\n"
    )
    if not legacy:
        instruction = (
            "Write each remaining module IN FULL, in the same file-block format. "
            "Do not continue a partial block or repeat any module already written. "
            "Emit these and nothing else:\n"
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": "\n\n".join(
            f"{{{{{name}}}}}\n```python\n{files[name]}```" for name in sorted(files))},
        {"role": "user", "content": instruction + "\n".join(
            f"  - {name}" for name in sorted(expected - set(files)))},
    ]


def completion_transcript(completion: Completion, round_i: int) -> str:
    messages = (completion.raw or {}).get("transcript_messages")
    if messages is None:
        body = completion.text
    else:
        body = "\n\n".join(
            f"### {message['role']} message {index}\n\n{message['content']}"
            for index, message in enumerate(messages, 1)
        )
    return f"## Backend invocation {round_i}\n\n{body}"


def generate(backend, system: str, user: str, expected: set[str],
             max_rounds: int, *,
             prior_completions: list[Completion] | None = None,
             ) -> tuple[dict[str, str], str, list[dict], int]:
    """Continue one test-blind generation, with a TOTAL backend-invocation budget.

    Saved invocations seed files, transcript and usage, consuming the same budget.
    A CLI invocation can contain several internal assistant turns. Parse each turn
    independently and request missing modules in full, never partial continuations.
    """
    prior = prior_completions or []
    if type(max_rounds) is not int or max_rounds < 1 or len(prior) > max_rounds:
        raise ValueError("--max-rounds must cover all source backend invocations")
    files: dict[str, str] = {}
    transcript: list[str] = []
    usages: list[dict] = []
    for round_i, completion in enumerate(prior, 1):
        files.update(completion_files(completion))
        transcript.append(completion_transcript(completion, round_i))
        usages.append(completion.usage.as_dict())

    for round_i in range(len(prior) + 1, max_rounds + 1):
        if expected <= set(files):
            break
        completion = (backend.complete_messages(continuation_messages(system, user, files, expected))
                      if round_i > 1
                      else backend.complete(system, user))
        transcript.append(completion_transcript(completion, round_i))
        usages.append(completion.usage.as_dict())

        newly = completion_files(completion)
        added = set(newly) - set(files)
        files.update(newly)
        missing = sorted(expected - set(files))
        truncated = bool((completion.raw or {}).get("truncated"))

        print(f"[b0]   invocation {round_i}: +{len(added)} files "
              f"({len(files)}/{len(expected)} done, {len(missing)} left)"
              f"{'  [hit output cap]' if truncated else ''}")

        if not missing:
            break
        if not truncated and not added:
            # Not cut off, and produced nothing new -- continuing would just loop.
            print("[b0]   stopping: response was complete but added no files")
            break
        if round_i == max_rounds:
            break

    return files, "\n\n".join(transcript), usages, len(usages)


def validate_tag(tag: str) -> str:
    if not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", tag):
        raise ValueError("Tags/project names must be simple names, not paths")
    return tag


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def json_object(content: bytes, label: str) -> dict:
    try:
        value = strict_json(content)
    except ValueError as exc:
        raise ValueError(f"Invalid JSON in {label}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {label}")
    return value


def checked_usage(value: object) -> dict:
    if not isinstance(value, dict) or not value:
        raise ValueError("Missing/invalid source invocation usage")
    if set(value) - set(Usage.__dataclass_fields__):
        raise ValueError("Unknown source usage fields")
    for key, number in value.items():
        checked_number(number, f"usage.{key}", integer=key not in ("premium_requests", "wall_clock_s"))
    return value


@dataclass
class Recovery:
    completions: list[Completion] = field(default_factory=list)
    audits: list[dict] = field(default_factory=list)
    audit_files: dict[str, bytes] = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)


def load_recovery(subject: pathlib.Path, source_tag: str, project: str,
                  system: str, user: str, expected: set[str], *,
                  model: str, effort: str, context: str | None,
                  max_rounds: int) -> Recovery:
    """Validate and snapshot test-blind source artifacts without changing the source.

    Never use generated project files, scores, oracle logs or diagnostics as input.
    Validate the actual stream and exact permitted request hashes, not declarations
    of oracle_seen/tool isolation alone. A missing terminal status fails closed.
    """
    validate_tag(source_tag)
    source = subject / f"pipeline-baseline-{source_tag}"
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Recovery source must be a real run directory")
    hashes: dict[str, str] = {}

    def read(path: pathlib.Path) -> bytes:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing/unsafe recovery artifact: {path.name}")
        content = path.read_bytes()
        hashes[path.relative_to(subject).as_posix()] = sha256(content)
        return content

    terminal = {"completed", "generation_failed", "scoring_failed", "comparison_failed", "failed"}
    status_path = subject / f"pipeline-baseline-{source_tag}.status.json"
    status_bytes = read(status_path) if status_path.exists() else None
    status = json_object(status_bytes, "source status") if status_bytes is not None else {}
    manifest_path = source / "generation.json"
    manifest_bytes = read(manifest_path) if manifest_path.exists() else None
    manifest = json_object(manifest_bytes, "generation manifest") if manifest_bytes is not None else {}
    for label, state, content in (
        ("source status", status, status_bytes), ("generation manifest", manifest, manifest_bytes),
    ):
        if content is not None and (
            not isinstance(state.get("state"), str) or state["state"] not in terminal
        ):
            raise ValueError(f"Active or invalid {label}; recovery requires a terminal source run")
    if not status and not manifest:
        raise ValueError("Recovery requires a terminal source status or generation manifest")
    meta_path = source / "metadata.json"
    finalized = meta_path.exists()
    meta = json_object(read(meta_path), "source metadata") if finalized else manifest
    for key, wanted in (
        ("baseline", "B0-single-shot"), ("backend", "copilot"), ("project", project),
        ("model", model), ("effort", effort), ("context", context),
    ):
        if key not in meta or meta[key] != wanted:
            raise ValueError(f"Recovery source {key} mismatch")
    for flag in ("oracle_seen", "oracle_tests_in_prompt", "oracle_feedback_during_generation"):
        if meta.get(flag) is not False:
            raise ValueError(f"Missing/invalid source protocol field: {flag}")
    prompt = f"{system}\n\n---\n\n{user}"
    if read(source / "prompt.md") != prompt.encode("utf-8"):
        raise ValueError("Recovery prompt mismatch: Java, skeleton and system prompt must match exactly")
    revision = meta.get("code_revision", status.get("code_revision"))
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Missing/invalid source code revision")
    observation_tag = validate_tag(meta.get("observation_tag", source_tag))
    if "tag" in meta and meta["tag"] != source_tag:
        raise ValueError("Source metadata tag mismatch")
    if meta.get("recovery") is not None:
        linkage = meta["recovery"]
        if (not isinstance(linkage, dict) or linkage.get("independent_sample") is not False
                or linkage.get("observation_tag") != observation_tag
                or meta.get("independent_sample") is not False):
            raise ValueError("Invalid source recovery linkage")
        validate_tag(linkage.get("source_tag"))
    elif observation_tag != source_tag:
        raise ValueError("Source observation tag has no recovery linkage")
    prior_usage = meta.get("usage_per_round")
    if not isinstance(prior_usage, list):
        raise ValueError("Missing/invalid source usage_per_round")
    prior_usage = [checked_usage(usage) for usage in prior_usage]

    audit_root = source / "backend-audit"
    if not audit_root.is_dir() or audit_root.is_symlink():
        raise ValueError("Missing/unsafe source backend audits")
    rounds = list(audit_root.iterdir())
    if not rounds or any(
        not path.is_dir() or path.is_symlink() or not re.fullmatch(r"round-\d{2,}", path.name)
        for path in rounds
    ):
        raise ValueError("Invalid source audit round directories")
    rounds.sort(key=lambda path: int(path.name.split("-")[1]))
    if len(rounds) > max_rounds:
        raise ValueError("--max-rounds is a TOTAL budget, smaller than source invocation count")
    if finalized:
        count = meta.get("continuation_rounds")
        if type(count) is not int or count != len(rounds) or len(prior_usage) != len(rounds):
            raise ValueError("Source invocation/usage counts disagree with saved audits")
        if "backend_invocations" in meta and (
            type(meta["backend_invocations"]) is not int or meta["backend_invocations"] != len(rounds)
        ):
            raise ValueError("Source backend invocation count mismatch")
    elif len(prior_usage) > len(rounds):
        raise ValueError("Source manifest has more usage records than audits")
    recorded_audits = meta.get("copilot_audit")
    if not isinstance(recorded_audits, list):
        raise ValueError("Missing/invalid source copilot_audit")
    if len(recorded_audits) != (len(rounds) if finalized else len(prior_usage)):
        raise ValueError("Source audit metadata count mismatch")
    recovered = Recovery()
    files: dict[str, str] = {}
    legacy_files: dict[str, str] = {}
    for index, directory in enumerate(rounds, 1):
        if directory.name != f"round-{index:02d}":
            raise ValueError("Source audit rounds must be contiguous and uniquely numbered")
        bundle = {name: read(directory / name) for name in (
            "request.json", "stdout.jsonl", "stderr.txt", "audit.json")}
        request = json_object(bundle["request.json"], "request audit")
        audit = json_object(bundle["audit.json"], "event audit")
        if audit.get("valid", True) is not True:
            raise ValueError("Source invocation audit is marked invalid")
        if request.get("argv") != command("copilot", model, effort, context):
            raise ValueError("Source invocation config/tool-isolation argv mismatch")
        if request.get("cwd_policy") != "empty temporary directory":
            raise ValueError("Missing/invalid source cwd isolation policy")
        candidates = [prompt] if index == 1 else [
            flatten_messages(continuation_messages(system, user, history, expected, legacy=legacy))
            for history, legacy in ((files, False), (legacy_files, True), (files, True))
        ]
        matched_prompts = [
            candidate for candidate in candidates
            if request.get("prompt_chars") == len(candidate)
            and request.get("prompt_sha256") == sha256(candidate.encode("utf-8"))
        ]
        if type(request.get("prompt_chars")) is not int or not matched_prompts:
            raise ValueError(f"Source request prompt mismatch at invocation {index}")
        if type(audit.get("returncode")) is not int or audit["returncode"] != 0:
            raise ValueError(f"Source CLI invocation {index} has an invalid/nonzero exit")
        decoded = decode_events(bundle["stdout.jsonl"].decode("utf-8"))
        decoded.validate_user_messages(matched_prompts[0])
        completion = decoded.completion(model, audit["returncode"])
        expected_audit = decoded.audit(index, 0)
        records = [audit] + (recorded_audits[index - 1:index] if index <= len(recorded_audits) else [])
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("event_counts"), dict):
                raise ValueError("Invalid source event audit")
            if any(type(value) is not int or value < 1 for value in record["event_counts"].values()):
                raise ValueError("Invalid source event audit counters")
            for key in ("round", "tools", "tool_allowlist", "tool_event_count", "event_counts", "returncode"):
                if type(record.get(key)) is not type(expected_audit[key]) or record.get(key) != expected_audit[key]:
                    raise ValueError(f"Source audit does not match stream: {key}")
        usage = (prior_usage[index - 1] if index <= len(prior_usage)
                 else checked_usage(audit.get("usage")))
        if "usage" in audit and checked_usage(audit["usage"]) != usage:
            raise ValueError("Source usage disagrees with invocation audit")
        for key, value in decoded.usage.as_dict().items():
            if usage.get(key) != value:
                raise ValueError(f"Source usage disagrees with event stream: {key}")
        completion.usage = Usage(**usage)
        recovered.completions.append(completion)
        origin = source_tag
        if index <= len(recorded_audits):
            origin = validate_tag(recorded_audits[index - 1].get("origin_tag", source_tag))
        recovered.audits.append({**audit, "origin_tag": origin, "replayed": True})
        for name, content in bundle.items():
            recovered.audit_files[f"backend-audit/{directory.name}/{name}"] = content
        files.update(completion_files(completion))
        legacy_files.update(parse_response(decoded.assistant_messages[-1]))
    # Catch a source runner changing state while its artifacts were being read.
    if ((status_bytes is not None and read(status_path) != status_bytes)
            or (manifest_bytes is not None and read(manifest_path) != manifest_bytes)):
        raise ValueError("Source state changed during recovery validation")
    recovered.provenance = {
        "source_tag": source_tag, "observation_tag": observation_tag,
        "independent_sample": False, "source_code_revision": revision,
        "source_status": status.get("state", manifest.get("state")),
        "source_backend_invocations": len(rounds),
        "recovered_modules": sorted(expected & set(files)),
        "source_artifact_sha256": hashes,
        "source_copilot_version": status.get("copilot_version"),
    }
    return recovered


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


def code_provenance() -> dict:
    return {
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "collector_code_sha256": {
            name: sha256((HERE / name).read_bytes())
            for name in ("single_shot.py", "backends/copilot.py", "backends/base.py", "run_one.py")
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--tag", default=time.strftime("%Y%m%d"))
    ap.add_argument("--resume-tag", help="recover/continue a terminal audited Copilot run under a NEW tag")
    ap.add_argument("--backend", default="copilot", choices=["copilot", "foundry"])
    ap.add_argument("--model", default=None,
                    help="default: whatever the subject's codeweaver.toml uses "
                         "(model-matched with CodeWeaver)")
    ap.add_argument("--effort", default=None, help="copilot backend only")
    ap.add_argument("--context", choices=["default", "long_context"], default=None,
                    help="explicit Copilot context tier; use long_context for large continuations")
    ap.add_argument("--max-output-tokens", type=int, default=128000,
                    help="output cap per response (default 128000)")
    ap.add_argument("--max-rounds", type=int, default=6,
                    help="TOTAL backend-invocation budget, including recovered invocations "
                         "(default 6); internal CLI model calls are counted separately")
    ap.add_argument("--dry-run", action="store_true",
                    help="build the prompt, report its size, call nothing")
    args = ap.parse_args()
    validate_tag(args.project)
    validate_tag(args.tag)
    if args.max_rounds < 1:
        raise ValueError("--max-rounds must be positive")
    if args.resume_tag and args.backend != "copilot":
        raise ValueError("--resume-tag currently requires the Copilot backend")

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

    run_dir = subject / f"pipeline-baseline-{args.tag}"
    if run_dir.exists() and not args.dry_run:
        raise SystemExit(f"refusing to overwrite existing run: {run_dir}; choose a new --tag")
    model = args.model or cfg["model"] or "claude-sonnet-5"
    effort = args.effort or cfg["effort"] or "medium"
    expected = {name for name, _ in skel}
    recovered = (load_recovery(
        subject, args.resume_tag, args.project, system, user, expected,
        model=model, effort=effort, context=args.context, max_rounds=args.max_rounds,
    ) if args.resume_tag else Recovery())
    source_rounds = len(recovered.completions)
    if args.resume_tag:
        print(f"[b0] linked recovery: {args.resume_tag}; "
              f"{len(recovered.provenance['recovered_modules'])} modules, "
              f"{source_rounds}/{args.max_rounds} invocations already used; NOT a new sample")
    if args.dry_run:
        print("[b0] dry run -- no call made")
        return 0

    meta = {
        "baseline": "B0-single-shot",
        "project": args.project,
        "tier": cfg["tier"],
        "backend": args.backend,
        "model": model,
        "effort": effort if args.backend == "copilot" else None,
        "context": args.context if args.backend == "copilot" else None,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inputs": {"java_files": len(java), "skeleton_modules": len(skel),
                   "prompt_chars": len(system) + len(user)},
        **code_provenance(),
        "collector_version": 2,
        "tag": args.tag,
        "observation_tag": recovered.provenance.get("observation_tag", args.tag),
        "independent_sample": not bool(args.resume_tag),
        "recovery": recovered.provenance or None,
        "usage_per_round": [completion.usage.as_dict() for completion in recovered.completions],
        "max_output_tokens": args.max_output_tokens,
        "max_rounds": args.max_rounds,
        "oracle_seen": False,
        "oracle_tests_in_prompt": False,
        "oracle_feedback_during_generation": False,
        "copilot_audit": recovered.audits,
        "protocol": (
            "single-shot: one prompt, no compiler feedback, no test feedback. "
            "When one response cannot hold every module, the SAME generation is "
            "continued (block-aware) until all modules are emitted or --max-rounds is "
            "reached; the model is told only which files remain, never anything about "
            "correctness. Backend invocations can contain internal CLI model turns. "
            "Recovery tags remain linked to the original observation, not new samples."
        ),
    }
    run_dir.mkdir()
    manifest_path = run_dir / "generation.json"
    manifest = {**meta, "state": "generating"}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    success = False
    try:
        (run_dir / "prompt.md").write_text(f"{system}\n\n---\n\n{user}", encoding="utf-8", newline="\n")
        for relative, content in recovered.audit_files.items():
            target = run_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        kw = ({"effort": effort, "context": args.context, "audit_dir": run_dir / "backend-audit",
               "start_round": source_rounds}
              if args.backend == "copilot" else {"max_tokens": args.max_output_tokens})
        replay_complete = args.resume_tag and expected <= set(recovered.provenance["recovered_modules"])
        backend = (None if replay_complete or source_rounds == args.max_rounds
                   else build_backend(args.backend, model=model, **kw))
        print(f"[b0] backend      : {args.backend} model={model}"
              + (f" effort={effort}" if args.backend == "copilot" else ""))
        t0 = time.monotonic()
        files, response_text, usages, rounds = generate(
            backend, system, user, expected, args.max_rounds, prior_completions=recovered.completions)
        elapsed = time.monotonic() - t0

        out_root = run_dir / "project"
        written, unknown = materialize(scaffold, out_root, files)
        missing = sorted(expected - set(files))
        # Syntax diagnostics are recorded only AFTER generation, never sent back.
        import ast
        unparseable = []
        for rel in files:
            path = out_root / rel
            if not path.is_file():
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                unparseable.append(rel)
        print(f"[b0] wall clock   : {elapsed:,.0f}s new work; {rounds} total backend invocation(s)")
        print(f"[b0] files parsed : {len(files)}  written={written}  unplaceable={unknown}")
        print(f"[b0] left as stub : {len(missing)}")
        if unparseable:
            print(f"[b0] UNPARSEABLE  : {unparseable}")
        if missing:
            print(f"[b0] INCOMPLETE   : {len(missing)} module(s) missing after {rounds} invocation(s)")
        audits = recovered.audits + [
            {**audit, "origin_tag": args.tag, "replayed": False}
            for audit in getattr(backend, "audit_records", [])
        ]
        meta.update({
            "outputs": {"files_parsed": len(files), "files_written": written,
                        "unplaceable": unknown, "left_as_stub": missing, "unparseable": unparseable},
            "usage_per_round": usages,
            "usage": {key: sum(usage[key] for usage in usages)
                      for key in Usage.__dataclass_fields__
                      if usages and all(key in usage for usage in usages)},
            "continuation_rounds": rounds,
            "backend_invocations": rounds, "new_backend_invocations": rounds - source_rounds,
            "observed_model_calls": (sum(audit["event_counts"].get("model.call_start", 0)
                                         for audit in audits) if args.backend == "copilot" else None),
            "observed_assistant_turns": (sum(audit["event_counts"].get("assistant.message", 0)
                                             for audit in audits) if args.backend == "copilot" else None),
            "copilot_audit": audits if args.backend == "copilot" else None,
            "complete": not missing and not unparseable,
        })
        (run_dir / "response.md").write_text(response_text, encoding="utf-8", newline="\n")
        (run_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[b0] metadata     : {run_dir / 'metadata.json'}")
        success = True
    finally:
        # Even a later collector/materialization failure leaves a terminal replay manifest.
        manifest["state"] = "completed" if success else "failed"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
