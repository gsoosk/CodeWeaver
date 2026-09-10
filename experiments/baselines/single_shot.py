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

`--backend copilot-api` sends native chat messages to a private loopback proxy,
with no CLI, tools or implicit client continuation. It is a separately labeled
transport/protocol, not a reproduction of the CLI's hidden scaffolding.
"""
from __future__ import annotations

import argparse
import ast
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


class Profile:
    """What differs between translation examples, in one place.

    Everything AlphaTrans-specific used to be inlined: the `.java` glob, the
    `src/main` prefix, the ```python fence, `ast.parse` as the syntax gate. None
    of that transfers to a C->Rust example, but the machinery around it -- block
    parsing, continuation, audits, recovery -- does. So the differences live here
    and the pipeline reads them.

    The alphatrans profile reproduces the previously hardcoded behaviour exactly;
    published results stay reproducible.
    """

    def __init__(self, name, example_rel, source_exts, source_fence, target_ext,
                 target_fence, target_root, source_dir_default, exclude_dirs=(),
                 validate=None, module_key=None):
        self.name = name
        self.example = REPO / example_rel
        self.source_exts = source_exts
        self.source_fence = source_fence
        self.target_ext = target_ext
        self.target_fence = target_fence
        self.target_root = target_root
        self.source_dir_default = source_dir_default
        self.exclude_dirs = exclude_dirs
        self._validate = validate
        self._module_key = module_key

    def file_block(self) -> re.Pattern:
        return re.compile(
            r"\{\{\s*([^\}\n]+?)\s*\}\}\s*\n+```(?:" + self.target_fence +
            r")?\s*\n(.*?)```", re.DOTALL)

    def bare_block(self) -> re.Pattern:
        return re.compile(r"```(?:" + self.target_fence + r")?\s*\n(.*?)```", re.DOTALL)

    def validate_syntax(self, path: pathlib.Path) -> str | None:
        """Return an error string, or None if the file is syntactically fine.

        Rust has no stdlib parser available here, and `cargo build` in
        build_check already checks far more than a parse would, so the Rust
        profile deliberately has no pre-check rather than a weak imitation of one.
        """
        if self._validate is None:
            return None
        return self._validate(path)

    def module_key(self, name: str) -> str:
        """Normalise a source or target path to the key the two share."""
        if self._module_key is not None:
            return self._module_key(name)
        return name


def _py_validate(path: pathlib.Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def _crust_key(name: str) -> str:
    """C and Rust names differ by case and separator, not by identity.

    `src/Aces-internal.c` and `src/aces_internal.rs` are the same module;
    `src/inversion-list/inversion-list.h` and `src/inversion_list.rs` likewise.
    Directory structure does not survive the translation, so only the stem is
    compared.
    """
    stem = name.rsplit("/", 1)[-1]
    stem = stem.rsplit(".", 1)[0]
    return stem.lower().replace("-", "_")


PROFILES = {
    "alphatrans": Profile(
        name="alphatrans", example_rel="examples/alphatrans",
        source_exts=(".java",), source_fence="java",
        target_ext=".py", target_fence="python|py", target_root="src/main",
        source_dir_default=None, validate=_py_validate),
    "crust": Profile(
        name="crust", example_rel="examples/crust",
        source_exts=(".c", ".h"), source_fence="c",
        target_ext=".rs", target_fence="rust|rs", target_root="src",
        source_dir_default="c-source",
        exclude_dirs=("tests", "test", "t", "target", ".git"),
        validate=None, module_key=_crust_key),
}

# Module-level default keeps existing callers (run_one.py, repair_loop.py) working.
PROFILE = PROFILES["alphatrans"]
EXAMPLE = PROFILE.example


def use_profile(name: str) -> Profile:
    """Switch the active profile. Must be called before any path is resolved.

    Requesting the profile that is already active is a no-op. Switching is an
    explicit action; re-asserting the default must not overwrite module globals,
    which callers and tests are entitled to patch.
    """
    global PROFILE, EXAMPLE, FILE_BLOCK, BARE_BLOCK
    if name not in PROFILES:
        raise SystemExit(f"unknown example profile {name!r}; have {sorted(PROFILES)}")
    if PROFILES[name] is PROFILE:
        return PROFILE
    PROFILE = PROFILES[name]
    EXAMPLE = PROFILE.example
    FILE_BLOCK = PROFILE.file_block()
    BARE_BLOCK = PROFILE.bare_block()
    return PROFILE


# `{{path/to/File.py}}` followed by a fenced block -- the same convention
# CRUST-Bench's prompts use, which keeps multi-file responses parseable.
FILE_BLOCK = PROFILE.file_block()

# Per-file mode only. With a single target module the model has nothing to
# disambiguate and answers with a bare fenced block, which is also the shape
# AlphaTrans's own class-by-class parser extracts.
BARE_BLOCK = PROFILE.bare_block()


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
    # AlphaTrans records an absolute dataset path; the CRUST example keeps its C
    # sources inside the subject, so a relative value resolves against the subject
    # rather than against whatever directory the harness happens to run from.
    source_dir = pathlib.Path(raw["paths"]["source_dir"])
    if not source_dir.is_absolute():
        source_dir = (cfg_path.parent / source_dir).resolve()
    return {
        "source_dir": source_dir,
        "tier": tier,
        "model": raw.get("model", {}).get("default"),
        "effort": raw.get("model", {}).get("effort_default"),
    }


def collect_java(source_dir: pathlib.Path) -> list[tuple[str, str]]:
    """Collect translation inputs. Named for history; honours the active profile.

    Excluded directories matter: for CRUST the C test suites are what its Rust
    tests were generated from, so including them would leak the oracle.
    """
    files = []
    for ext in PROFILE.source_exts:
        files.extend(source_dir.rglob(f"*{ext}"))
    out = []
    for p in sorted(set(files)):
        rel = p.relative_to(source_dir)
        if any(part in PROFILE.exclude_dirs for part in rel.parts):
            continue
        out.append((str(rel).replace("\\", "/"),
                    p.read_text(encoding="utf-8", errors="replace")))
    return out


def collect_skeleton(scaffold: pathlib.Path) -> list[tuple[str, str]]:
    root = scaffold / PROFILE.target_root
    files = sorted(p for p in root.rglob(f"*{PROFILE.target_ext}")
                   if p.name not in ("__init__.py", "lib.rs"))
    return [(str(p.relative_to(scaffold)).replace("\\", "/"),
             p.read_text(encoding="utf-8", errors="replace")) for p in files]


def build_prompt(project: str, java: list, skel: list) -> tuple[str, str]:
    system = (HERE / "prompts" / "single_shot_system.md").read_text(encoding="utf-8")
    tpl = (HERE / "prompts" / "single_shot_user.md").read_text(encoding="utf-8")
    sf = PROFILE.source_fence.split("|")[0]
    tf = PROFILE.target_fence.split("|")[0]
    java_blob = "\n".join(
        f"{{{{{name}}}}}\n```{sf}\n{content}\n```\n" for name, content in java)
    skel_blob = "\n".join(
        f"{{{{{name}}}}}\n```{tf}\n{content}\n```\n" for name, content in skel)
    targets = "\n".join(f"  - {name}" for name, _ in skel)

    user = (tpl
            .replace("{{PROJECT}}", project)
            .replace("{{JAVA_FILES}}", java_blob)
            .replace("{{SKELETON_FILES}}", skel_blob)
            .replace("{{TARGET_PATHS}}", targets)
            .replace("{{N_JAVA}}", str(len(java)))
            .replace("{{N_MODULES}}", str(len(skel))))
    return system, user


def pair_per_file(java: list, skel: list) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Map each target module to the source file(s) it comes from.

    AlphaTrans is one-to-one: `src/main/java/<pkg>/<Class>.java` sits beside
    `src/main/<pkg>/<Class>.py`, so the key is the path minus the leading `java/`
    segment and the extension.

    CRUST is one-to-many and renames: a single `src/aces_internal.rs` corresponds
    to both `src/Aces-internal.c` and `src/include/Aces-internal.h`. Those are
    concatenated in declaration-then-definition order, since a C header carries
    the types the implementation needs. A module with no counterpart is reported
    as an orphan, never silently paired with an unrelated file.
    """
    by_key: dict[str, list[tuple[str, str]]] = {}
    for name, content in java:
        if PROFILE.name == "alphatrans":
            key = name[len("java/"):] if name.startswith("java/") else name
            key = key[:-len(".java")]
        else:
            key = PROFILE.module_key(name)
        by_key.setdefault(key, []).append((name, content))

    units, orphans = [], []
    prefix = PROFILE.target_root + "/"
    for name, content in skel:
        if PROFILE.name == "alphatrans":
            key = name[len(prefix):] if name.startswith(prefix) else name
            key = key[:-len(PROFILE.target_ext)]
        else:
            key = PROFILE.module_key(name)
        entries = by_key.get(key)
        if not entries:
            orphans.append(name)
            continue
        # Headers first: declarations before definitions.
        entries = sorted(entries, key=lambda e: (not e[0].endswith(".h"), e[0]))
        src_name = ", ".join(e[0] for e in entries)
        sf = PROFILE.source_fence.split("|")[0]
        src_body = "\n\n".join(
            f"/* {e[0]} */\n{e[1]}" if len(entries) > 1 else e[1] for e in entries)
        units.append((name, src_name, src_body, content))
    return units, orphans


def build_per_file_prompt(project: str, unit: tuple[str, str, str, str]) -> tuple[str, str]:
    """One source unit plus its one skeleton module -- AlphaTrans's granularity."""
    module, java_name, java_source, skeleton = unit
    system = (HERE / "prompts" / "single_shot_system.md").read_text(encoding="utf-8")
    tpl = (HERE / "prompts" / "per_file_user.md").read_text(encoding="utf-8")
    sf = PROFILE.source_fence.split("|")[0]
    tf = PROFILE.target_fence.split("|")[0]
    user = (tpl
            .replace("{{PROJECT}}", project)
            .replace("{{TARGET_PATH}}", module)
            .replace("{{JAVA_FILE}}", f"{{{{{java_name}}}}}\n```{sf}\n{java_source}\n```\n")
            .replace("{{SKELETON_FILE}}", f"{{{{{module}}}}}\n```{tf}\n{skeleton}\n```\n"))
    return system, user


def generate_per_file(backend, project: str, units: list, *,
                      consecutive_failure_limit: int = 3):
    """One independent request per module; no continuation and no retries.

    Only the block whose path matches the requested module is accepted, so a
    response that answers with some other file counts as a miss rather than
    silently overwriting a sibling. A per-module error leaves that module as an
    unimplemented stub; the subject is abandoned once failures are consecutive
    enough to look systemic rather than incidental.
    """
    files: dict[str, str] = {}
    transcript: list[str] = []
    usages: list[dict] = []
    outcomes: list[dict] = []
    consecutive = 0
    for index, unit in enumerate(units, 1):
        module = unit[0]
        system, user = build_per_file_prompt(project, unit)
        outcome = {"module": module, "request": index}
        try:
            completion = backend.complete(system, user)
        except (OSError, ValueError) as exc:
            consecutive += 1
            outcome.update(status="request_failed", error=f"{type(exc).__name__}: {exc}")
            outcomes.append(outcome)
            print(f"[b0]   {index}/{len(units)} {module}: FAILED ({type(exc).__name__})")
            if consecutive >= consecutive_failure_limit:
                outcome["abandoned_subject"] = True
                print(f"[b0]   stopping: {consecutive} consecutive request failures")
                break
            continue
        consecutive = 0
        transcript.append(f"## {module}\n\n{completion.text}")
        usages.append(completion.usage.as_dict())
        emitted = completion_files(completion)
        truncated = bool((completion.raw or {}).get("truncated"))
        parts = (completion.raw or {}).get("assistant_messages") or [completion.text]
        bare = [block for part in parts for block in BARE_BLOCK.findall(part)]
        body, attribution = None, None
        if module in emitted:
            body, attribution = emitted[module], "explicit_path_block"
        elif bare:
            # Only one module was requested, so an unlabelled block is unambiguous.
            body, attribution = bare[0], "bare_block"
        outcome.update(
            status="written" if body is not None else "module_not_emitted",
            attribution=attribution,
            blocks_returned=sorted(emitted),
            bare_blocks=len(bare),
            truncated=truncated,
            finish_reason=(completion.raw or {}).get("finish_reason"),
        )
        if body is not None:
            files[module] = body
        outcomes.append(outcome)
        print(f"[b0]   {index}/{len(units)} {module}: {outcome['status']}"
              f"{' (' + attribution + ')' if attribution else ''}"
              f"{'  [hit output cap]' if truncated else ''}")
    return files, "\n\n".join(transcript), usages, len(usages), outcomes


def parse_response(text: str) -> dict[str, str]:
    """Extract {relative_path: source} from the model's fenced file blocks."""
    out: dict[str, str] = {}
    for raw_name, body in FILE_BLOCK.findall(text):
        name = raw_name.strip().strip("`").replace("\\", "/")
        if not name.endswith(PROFILE.target_ext):
            continue
        # Normalise to a path under the target root regardless of how it was written.
        root = PROFILE.target_root + "/"
        idx = name.find(root)
        name = name[idx:] if idx != -1 else f"{root}{name.lstrip('/')}"
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
    # Anything else the scaffold holds is build metadata the target language needs
    # -- Cargo.toml and Cargo.lock for Rust. Without the manifest a Rust crate
    # cannot be compiled or scored at all, so a src-only copy would report every
    # run as a build failure regardless of what the model wrote.
    for extra in sorted(scaffold.iterdir()):
        if extra.is_file():
            shutil.copy2(extra, out_root / extra.name)

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
            for name in ("single_shot.py", "backends/copilot.py", "backends/copilot_api.py",
                         "backends/base.py", "run_one.py")
        },
    }


def add_api_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-base-url", help="loopback /v1 URL; otherwise COPILOT_API_BASE_URL or 127.0.0.1:4141/v1")
    parser.add_argument("--api-token-limit-field", choices=("max_tokens", "max_completion_tokens"),
                        default=None, help="API output-limit field (default max_tokens); no automatic fallback")
    parser.add_argument("--api-timeout", type=float, default=None, help="API HTTP timeout in seconds (default 3600)")
    parser.add_argument("--temperature", type=float, default=None, help="API only; omitted unless explicitly set")
    parser.add_argument("--api-stream", action="store_true",
                        help="consume one API completion as SSE (enables the provider's streaming output limit)")


def configured_api_backend(args):
    """Validate locally, including in dry runs; constructing a backend sends nothing."""
    if args.context is not None:
        raise ValueError("--context is CLI-only; API context capacity is provider/model-controlled")
    if args.resume_tag:
        raise ValueError("--resume-tag currently requires the Copilot CLI backend")
    return build_backend(
        "copilot-api", model=args.model, max_output_tokens=args.max_output_tokens,
        base_url=args.api_base_url, effort=args.effort,
        token_limit_field=args.api_token_limit_field or "max_tokens",
        temperature=args.temperature, timeout=args.api_timeout if args.api_timeout is not None else 3600.0,
        stream=args.api_stream,
    )


def reject_api_arguments(args) -> None:
    if args.api_stream or any(getattr(args, key) is not None for key in (
        "api_base_url", "api_token_limit_field", "api_timeout", "temperature",
    )):
        raise ValueError("--api-* and --temperature require --backend copilot-api")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--example", default="alphatrans", choices=sorted(PROFILES),
                    help="which translation example the subject belongs to: "
                         "alphatrans (Java->Python) or crust (C->Rust). "
                         "Selects source/target languages, paths and syntax gate.")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--resume-tag", help="recover/continue a terminal audited Copilot run under a NEW tag")
    ap.add_argument("--backend", default="copilot", choices=["copilot", "foundry", "copilot-api"])
    ap.add_argument("--granularity", default="repo", choices=["repo", "per-file"],
                    help="repo: whole repository in one generation (CRUST-Bench style). "
                         "per-file: one independent request per module, matching AlphaTrans's "
                         "class-by-class ablation granularity. API backend only.")
    ap.add_argument("--model", default=None,
                    help="default: whatever the subject's codeweaver.toml uses "
                         "(model-matched with CodeWeaver); API requires an explicit model")
    ap.add_argument("--effort", default=None, help="CLI effort or explicit API reasoning_effort; API has no default")
    ap.add_argument("--context", choices=["default", "long_context"], default=None,
                    help="explicit Copilot context tier; use long_context for large continuations")
    ap.add_argument("--max-output-tokens", type=int, default=None,
                    help="Foundry cap (default 128000); API requires an explicit positive cap; not enforced by CLI")
    add_api_arguments(ap)
    ap.add_argument("--max-rounds", type=int, default=6,
                    help="TOTAL backend-invocation budget, including recovered invocations "
                         "(default 6); internal CLI model calls are counted separately")
    ap.add_argument("--dry-run", action="store_true",
                    help="build the prompt, report its size, call nothing")
    args = ap.parse_args()
    profile = use_profile(args.example)
    args.tag = args.tag or (("b0-api-" if args.backend == "copilot-api" else "") + time.strftime("%Y%m%d"))
    validate_tag(args.project)
    validate_tag(args.tag)
    if args.max_rounds < 1:
        raise ValueError("--max-rounds must be positive")
    if args.resume_tag and args.backend != "copilot":
        raise ValueError("--resume-tag currently requires the Copilot backend")
    if args.granularity == "per-file":
        if args.backend != "copilot-api":
            raise ValueError("--granularity per-file currently requires the copilot-api backend")
        if args.resume_tag:
            raise ValueError("--granularity per-file does not support --resume-tag")
    api_backend = None
    if args.backend == "copilot-api":
        api_backend = configured_api_backend(args)
    else:
        reject_api_arguments(args)
        if args.max_output_tokens is None:
            args.max_output_tokens = 128000
        if args.max_output_tokens < 1:
            raise ValueError("--max-output-tokens must be positive")

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
    per_file = args.granularity == "per-file"
    units, orphans = pair_per_file(java, skel) if per_file else ([], [])

    # The binding constraint for whole-repo single-shot is usually the OUTPUT cap, not
    # the context window: the model must emit every module in one response. Estimate it
    # from the skeleton (a real implementation is several times its stub).
    skel_chars = sum(len(c) for _, c in skel)
    est_out_tokens = int(skel_chars * 3.5 / 4)

    print(f"[b0] project      : {args.project} (tier {cfg['tier']})")
    print(f"[b0] java files   : {len(java)}")
    print(f"[b0] modules      : {len(skel)}")
    print(f"[b0] granularity  : {args.granularity}")
    if per_file:
        sizes = [len(build_per_file_prompt(args.project, unit)[1]) for unit in units]
        print(f"[b0] requests     : {len(units)} (one per module)"
              + (f"; {len(orphans)} module(s) have no Java counterpart" if orphans else ""))
        if sizes:
            print(f"[b0] prompt chars : max {max(sizes):,}  median {sorted(sizes)[len(sizes)//2]:,}"
                  f"  (~{max(sizes)//4:,} tokens for the largest)")
        if orphans:
            print(f"[b0] no Java for  : {orphans}")
    else:
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
    model = api_backend.model if api_backend is not None else (args.model or cfg["model"] or "claude-sonnet-5")
    effort = args.effort if api_backend is not None else (args.effort or cfg["effort"] or "medium")
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
        if api_backend is not None:
            probe = build_per_file_prompt(args.project, units[0]) if per_file else (system, user)
            api_backend.request_payload([{"role": "system", "content": probe[0]},
                                         {"role": "user", "content": probe[1]}])
            print(f"[b0] API config   : {json.dumps(api_backend.provenance()['api_configuration'])}")
            print("[b0] API capacity/model support not checked; dry run makes no HTTP request")
        print("[b0] dry run -- no call made")
        return 0

    meta = {
        "baseline": "B0-single-shot",
        "project": args.project,
        "tier": cfg["tier"],
        "backend": args.backend,
        "model": model,
        "effort": effort if args.backend in ("copilot", "copilot-api") else None,
        "context": args.context if args.backend == "copilot" else None,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inputs": {"java_files": len(java), "skeleton_modules": len(skel),
                   "prompt_chars": len(system) + len(user)},
        **code_provenance(),
        "collector_version": 2,
        "granularity": args.granularity,
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
        "copilot_audit": recovered.audits if args.backend == "copilot" else None,
        "protocol": (
            "single-shot: one prompt, no compiler feedback, no test feedback. "
            "When one response cannot hold every module, the SAME generation is "
            "continued (block-aware) until all modules are emitted or --max-rounds is "
            "reached; the model is told only which files remain, never anything about "
            "correctness. Backend invocations can contain internal CLI model turns. "
            "Recovery tags remain linked to the original observation, not new samples."
        ),
    }
    if api_backend is not None:
        meta.update(api_backend.provenance())
        single_call = args.max_rounds == 1
        meta.update(api_audit=[], explicit_http_model_requests=0, single_call=single_call and not per_file)
        if per_file:
            meta.update(
                per_file_units=len(units), per_file_orphan_modules=orphans,
                per_file_outcomes=[], protocol=(
                    "B0 API-only, PER-FILE: one independent HTTP model request per module, "
                    "matching the granularity of AlphaTrans's class-by-class ablation. Each "
                    "request carries only that Java class and its interface skeleton module. "
                    "No continuation, no retries, no tools, no compiler or oracle feedback. "
                    "Requests share no conversation state, so nothing a module learns can "
                    "reach another. Unlike AlphaTrans's baseline this keeps the typed "
                    "interface contract and is scored by the same hidden oracle, so it is "
                    "comparable to our other arms but is not a byte-exact replication."
                ))
        else:
            meta.update(protocol=(
                "B0 API-only, STRICT single call: exactly one explicit HTTP model request per "
                "subject, native system/user messages, no CLI, tools, retries or continuation of "
                "any kind. Whatever one response cannot hold is left as an unimplemented skeleton "
                "stub and scored as such. Not comparable to continuation-allowed arms."
                if single_call else
                "B0 API-only: native system/user messages, no CLI, tools, retries or automatic "
                "client/proxy continuation. Each invocation is one explicit HTTP model request. "
                "Only closed file blocks and missing-module bookkeeping enter subsequent requests; "
                "no compiler/oracle feedback. Different transport/protocol from Copilot CLI; "
                "hidden provider prompts are not observable or claimed equivalent."
            ))
    run_dir.mkdir()
    manifest_path = run_dir / "generation.json"
    manifest = {**meta, "state": "generating"}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    success = False
    backend = None
    try:
        if per_file:
            prompts = run_dir / "prompts"
            prompts.mkdir()
            for unit in units:
                unit_system, unit_user = build_per_file_prompt(args.project, unit)
                name = unit[0].replace("/", "__") + ".md"
                (prompts / name).write_text(f"{unit_system}\n\n---\n\n{unit_user}",
                                            encoding="utf-8", newline="\n")
        else:
            (run_dir / "prompt.md").write_text(f"{system}\n\n---\n\n{user}", encoding="utf-8", newline="\n")
        for relative, content in recovered.audit_files.items():
            target = run_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        kw = ({"effort": effort, "context": args.context, "audit_dir": run_dir / "backend-audit",
               "start_round": source_rounds}
              if args.backend == "copilot" else {"max_tokens": args.max_output_tokens})
        replay_complete = args.resume_tag and expected <= set(recovered.provenance["recovered_modules"])
        if api_backend is not None:
            api_backend.audit_dir = run_dir / "api-audit"
            backend = api_backend
        else:
            backend = (None if replay_complete or source_rounds == args.max_rounds
                       else build_backend(args.backend, model=model, **kw))
        print(f"[b0] backend      : {args.backend} model={model}"
              + (f" effort={effort}" if effort is not None and args.backend in ("copilot", "copilot-api") else ""))
        t0 = time.monotonic()
        outcomes = []
        if per_file:
            files, response_text, usages, rounds, outcomes = generate_per_file(
                backend, args.project, units)
        else:
            files, response_text, usages, rounds = generate(
                backend, system, user, expected, args.max_rounds,
                prior_completions=recovered.completions)
        elapsed = time.monotonic() - t0

        out_root = run_dir / "project"
        written, unknown = materialize(scaffold, out_root, files)
        missing = sorted(expected - set(files))
        # Syntax diagnostics are recorded only AFTER generation, never sent back.
        unparseable = []
        for rel in files:
            path = out_root / rel
            if not path.is_file():
                continue
            if PROFILE.validate_syntax(path) is not None:
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
                                             for audit in audits) if args.backend == "copilot"
                                         else rounds if api_backend is not None else None),
            "copilot_audit": audits if args.backend == "copilot" else None,
            "complete": not missing and not unparseable,
        })
        if api_backend is not None:
            meta.update(api_audit=audits, returned_models=[audit["returned_model"] for audit in audits],
                        explicit_http_model_requests=sum(audit["http_requests"] for audit in audits))
            if per_file:
                meta.update(per_file_outcomes=outcomes, per_file_requests_attempted=len(outcomes),
                            per_file_requests_failed=sum(
                                1 for outcome in outcomes if outcome["status"] == "request_failed"),
                            per_file_modules_not_emitted=sum(
                                1 for outcome in outcomes if outcome["status"] == "module_not_emitted"))
        (run_dir / "response.md").write_text(response_text, encoding="utf-8", newline="\n")
        (run_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[b0] metadata     : {run_dir / 'metadata.json'}")
        success = True
    finally:
        # Even a later collector/materialization failure leaves a terminal replay manifest.
        if api_backend is not None:
            manifest["api_audit"] = api_backend.audit_records
            manifest["explicit_http_model_requests"] = sum(
                audit["http_requests"] for audit in api_backend.audit_records)
        manifest["state"] = "completed" if success else "failed"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
