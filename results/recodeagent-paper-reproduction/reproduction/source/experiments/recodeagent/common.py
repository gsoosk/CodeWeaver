"""Shared, standard-library-only infrastructure for the ReCodeAgent reproduction
harness. Every other module in ``experiments/recodeagent`` imports from here.

Provides:

  - protocol constants pinned to the paper (dataset sizes, RQ names, reference
    totals) -- kept separate from anything this harness measures itself
  - :class:`Measurement` / :class:`Status` -- a value type that keeps "missing"
    and "unavailable" distinct from "zero" or "success" everywhere in the harness
  - hashing (md5/sha256) + atomic file writes (crash-safe, no torn artifacts)
  - :func:`run_argv` -- a safe subprocess runner (argument arrays only, never a
    shell string; timeouts are first-class)
  - provenance capture (git SHA, OS, Python, CodeWeaver package version,
    best-effort toolchain versions)
  - a tiny dependency-free JSON-schema-ish validator for ``schemas/*.json``
  - optional third-party dependency probing (pandas/matplotlib/reportlab/scipy/
    sentence-transformers) that never raises and never fakes availability
"""
from __future__ import annotations

import contextlib
import dataclasses
import datetime as _dt
import hashlib
import importlib
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent
SCHEMAS_DIR = PACKAGE_DIR / "schemas"
DEFAULT_EXPERIMENT_CONFIG = PACKAGE_DIR / "experiment.toml"

# --------------------------------------------------------------------------- #
# Protocol constants (pinned facts about the paper / official artifact).
# These are NOT measurements -- they describe what the reproduction targets.
# --------------------------------------------------------------------------- #
PAPER_ARXIV_ID = "2604.07341"
OFFICIAL_ARTIFACT_COMMIT = "3a178a6a99f34c76a37f732c0fd887dad279cf9f"
ZENODO_RECORD_ID = "21399688"
ZENODO_FILES_BASE_URL = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}/files"

# tool key -> (paper name, expected project count, source language, target language)
DATASET_SPECS: dict[str, dict[str, Any]] = {
    "crust": {"label": "CRUST", "expected_count": 100, "source_language": "C", "target_language": "Rust"},
    "oxidizer": {"label": "Oxidizer", "expected_count": 6, "source_language": "Go", "target_language": "Rust"},
    "alphatrans": {"label": "AlphaTrans", "expected_count": 4, "source_language": "Java", "target_language": "Python"},
    "skel": {"label": "SKEL", "expected_count": 8, "source_language": "Python", "target_language": "JavaScript"},
}
EXPECTED_TOOL_COUNTS: dict[str, int] = {k: v["expected_count"] for k, v in DATASET_SPECS.items()}
EXPECTED_TOTAL_PROJECTS = sum(EXPECTED_TOOL_COUNTS.values())
assert EXPECTED_TOTAL_PROJECTS == 118, "dataset spec drifted from the pinned paper protocol"

RUN_VARIANTS: tuple[str, ...] = (
    "full",
    "noanalyzer",
    "noplanning",
    "novalidator",
    "baseagent-condensed",
    "baseagent-concat",
)
ABLATION_VARIANTS = tuple(v for v in RUN_VARIANTS if v != "full")

# Paper-reported reference totals (kept separate from anything measured here;
# analyze.py must never blend these into a "measured" row).
#
# Provenance: `total_loc`/`validated_tests`/`translated_tests`/`functions`
# were given explicitly in this task's own protocol spec ("230K LoC, 2,107
# validated tests, 1,484 translated tests (CRUST excluded), 4,583
# functions"). All four were independently cross-checked read-only against
# the real official `results.xlsx`'s `results (claude-4.5-sonnet)` sheet,
# "total" row (row 23 of 24), during a later integration pass -- not
# vendored into this repo:
#   - `validated_tests` (2107) == that sheet's "# executed tests" column,
#     exact match.
#   - `translated_tests` (1484) == that sheet's "AGENT (# test exec - trans)"
#     column, exact match; CRUST's 4 aggregate rows (tool="swe-agent",
#     project="crust-bench (<compile status>)") show a literal "-" in this
#     column, confirming "CRUST excluded" is real (a structural absence in
#     the paper's own data, not a filter this harness invented).
#   - `functions` (4583) == that sheet's "Exercised" column (functions
#     covered by at least one test), which is DISTINCT from "AMF" ("All
#     Methods/Functions", 5068 total incl. CRUST) minus "Not Exercised"
#     (485) -- i.e. this figure means functions-with-coverage, not the raw
#     function count. Unlike `translated_tests`, this total DOES include
#     CRUST's 4 aggregate rows.
#   - `total_loc` (230_000) is the paper's own rounded headline figure; the
#     real sheet's precise "LoC" total column sums to 233,057 (also
#     including CRUST) -- kept below as `total_loc_precise` alongside the
#     rounded headline value rather than silently overwriting it.
PAPER_REFERENCE_TOTALS: dict[str, int] = {
    "total_loc": 230_000,
    "total_loc_precise": 233_057,  # verified exact sum from results.xlsx; see comment above
    "validated_tests": 2107,
    "translated_tests": 1484,  # CRUST excluded per the paper's protocol (verified: literal "-" cells)
    "functions": 4583,  # "Exercised" functions specifically, not the raw 5,068 "AMF" total
}

# Per-tool breakdown of `PAPER_REFERENCE_TOTALS["validated_tests"]` (2,107),
# explicitly provided by this task's own protocol spec: "validated
# developer-test denominator is exactly 2,107 = 623 CRUST + 1,484
# non-CRUST (Oxidizer 229, AlphaTrans 1,181, SKEL 74)". Sums exactly to
# `PAPER_REFERENCE_TOTALS["validated_tests"]` (623 + 229 + 1181 + 74 ==
# 2107) and to `PAPER_REFERENCE_TOTALS["translated_tests"]`'s own
# CRUST-excluded 1,484 (229 + 1181 + 74 == 1484). Kept here, structurally
# separate from anything measured, purely so `table1_paper_reference_rows`
# can surface the paper's own per-tool validated-test context alongside
# this harness's newly measured `validated_tests_*` fields (see
# collect.py's independent-oracle adapters) -- never asserted as a target
# our own measured counts must reproduce, and never blended into any
# measured row/column.
PAPER_REFERENCE_VALIDATED_TESTS_BY_TOOL: dict[str, int] = {
    "crust": 623,
    "oxidizer": 229,
    "alphatrans": 1181,
    "skel": 74,
}
PAPER_RUNTIME_TESTS_BY_PROJECT: dict[tuple[str, str], int] = {
    ("oxidizer", "checkdigit"): 36,
    ("oxidizer", "go-edlib"): 36,
    ("oxidizer", "gohistogram"): 2,
    ("oxidizer", "gonameparts"): 26,
    ("oxidizer", "stats"): 121,
    ("oxidizer", "textrank"): 8,
    ("alphatrans", "commons-cli"): 381,
    ("alphatrans", "commons-csv"): 298,
    ("alphatrans", "commons-fileupload"): 39,
    ("alphatrans", "commons-validator"): 463,
    ("skel", "bst"): 11,
    ("skel", "colorsys"): 2,
    ("skel", "heapq"): 8,
    ("skel", "html"): 7,
    ("skel", "mathgen"): 5,
    ("skel", "rbt"): 10,
    ("skel", "strsim"): 19,
    ("skel", "toml"): 12,
}
assert sum(PAPER_RUNTIME_TESTS_BY_PROJECT.values()) == 1484

# Paper Table 1's per-project "Exercised" function denominator. CRUST is
# intentionally absent: §4.2.3 excludes it from function-level validation.
PAPER_EXERCISED_FUNCTIONS_BY_PROJECT: dict[tuple[str, str], int] = {
    ("oxidizer", "checkdigit"): 29,
    ("oxidizer", "go-edlib"): 24,
    ("oxidizer", "gohistogram"): 19,
    ("oxidizer", "gonameparts"): 15,
    ("oxidizer", "stats"): 52,
    ("oxidizer", "textrank"): 52,
    ("alphatrans", "commons-cli"): 257,
    ("alphatrans", "commons-csv"): 213,
    ("alphatrans", "commons-fileupload"): 25,
    ("alphatrans", "commons-validator"): 409,
    ("skel", "bst"): 21,
    ("skel", "colorsys"): 9,
    ("skel", "heapq"): 24,
    ("skel", "html"): 42,
    ("skel", "mathgen"): 82,
    ("skel", "rbt"): 27,
    ("skel", "strsim"): 50,
    ("skel", "toml"): 47,
}
assert sum(PAPER_EXERCISED_FUNCTIONS_BY_PROJECT.values()) == 1397

PAPER_GENERATED_TESTS_BY_PROJECT_NON_CRUST: dict[tuple[str, str], int] = {
    ("oxidizer", "checkdigit"): 71,
    ("oxidizer", "go-edlib"): 3,
    ("oxidizer", "gohistogram"): 66,
    ("oxidizer", "gonameparts"): 22,
    ("oxidizer", "stats"): 320,
    ("oxidizer", "textrank"): 127,
    ("alphatrans", "commons-cli"): 257,
    ("alphatrans", "commons-csv"): 192,
    ("alphatrans", "commons-fileupload"): 208,
    ("alphatrans", "commons-validator"): 132,
    ("skel", "bst"): 6,
    ("skel", "colorsys"): 46,
    ("skel", "heapq"): 11,
    ("skel", "html"): 13,
    ("skel", "mathgen"): 11,
    ("skel", "rbt"): 5,
    ("skel", "strsim"): 64,
    ("skel", "toml"): 150,
}
assert sum(PAPER_GENERATED_TESTS_BY_PROJECT_NON_CRUST.values()) == 1704

OFFICIAL_ARTIFACT_FILES: dict[str, dict[str, str]] = {
    "implementation_zip": {
        "filename": "implementation.zip",
        "md5": "a2151028151e0852ce4db060a22ac76a",
        "url": f"{ZENODO_FILES_BASE_URL}/implementation.zip/content",
    },
    "results_xlsx": {
        "filename": "results.xlsx",
        "md5": "a404779f2dcd7ac44d43bf72f4e88b98",
        "url": f"{ZENODO_FILES_BASE_URL}/results.xlsx/content",
    },
    "results_zip": {
        "filename": "results.zip",
        "md5": "5df332d2a1477ec30f719dd7d0ff2470",
        "url": f"{ZENODO_FILES_BASE_URL}/results.zip/content",
    },
}

# The paper's protocol timeout and reference model (used as documented defaults;
# experiment.toml is the authoritative, overridable source at runtime).
#
# Model ID provenance (two real sources, not fully identical, both checked):
#  - Explicit user-provided integration update: "claude-sonnet-4.5" (used
#    here, correcting the earlier "claude-4.5-sonnet" guess made before any
#    official artifact was available).
#  - The official artifact's own `.claude/settings.local.json` pins the
#    precise underlying Bedrock model identifier
#    "global.anthropic.claude-sonnet-4-5-20250929-v1:0" -- i.e. the
#    "claude-sonnet-4-5" family (hyphenated, Anthropic's own convention),
#    dated snapshot 2025-09-29. The artifact's own `results.xlsx` instead
#    labels its results sheet "results (claude-4.5-sonnet)" -- an informal
#    human-written label, not a literal API model ID. All three name the
#    same model family; this constant uses the user-provided short form.
PAPER_AGENT_TIMEOUT_SECONDS = 5000
PAPER_REFERENCE_MODEL = "claude-sonnet-4.5"


# --------------------------------------------------------------------------- #
# Status / Measurement -- "missing" must never collapse into "zero" or "success"
# --------------------------------------------------------------------------- #
class Status:
    """String constants (not an Enum, so they serialize as plain JSON strings
    with no extra decoding step needed by pandas/csv consumers)."""

    MEASURED = "measured"
    MISSING = "missing"              # expected data not found / not produced
    UNAVAILABLE = "unavailable"      # optional capability not installed/configured
    ERROR = "error"                  # attempted and failed
    NOT_APPLICABLE = "not_applicable"
    DRY_RUN = "dry_run"
    SKIPPED = "skipped"

    ALL = (MEASURED, MISSING, UNAVAILABLE, ERROR, NOT_APPLICABLE, DRY_RUN, SKIPPED)


@dataclass
class Measurement:
    """A single measured (or explicitly-not-measured) value.

    Never coerce a missing/unavailable/error Measurement to ``0`` or ``False``:
    downstream aggregation (analyze.py) must skip non-``measured`` rows rather
    than silently treating them as zero, per the harness's core honesty
    requirement.
    """

    value: Any = None
    status: str = Status.MISSING
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status not in Status.ALL:
            raise ValueError(f"unknown Measurement status: {self.status!r}")
        if self.status == Status.MEASURED and self.value is None:
            # A measured None is indistinguishable from missing downstream;
            # force callers to be explicit.
            raise ValueError("Measurement(status=measured) requires a non-None value")

    @classmethod
    def ok(cls, value: Any) -> "Measurement":
        return cls(value=value, status=Status.MEASURED)

    @classmethod
    def missing(cls, reason: str = "") -> "Measurement":
        return cls(value=None, status=Status.MISSING, reason=reason)

    @classmethod
    def unavailable(cls, reason: str = "") -> "Measurement":
        return cls(value=None, status=Status.UNAVAILABLE, reason=reason)

    @classmethod
    def error(cls, reason: str = "") -> "Measurement":
        return cls(value=None, status=Status.ERROR, reason=reason)

    @classmethod
    def na(cls, reason: str = "") -> "Measurement":
        return cls(value=None, status=Status.NOT_APPLICABLE, reason=reason)

    @classmethod
    def skipped(cls, reason: str = "") -> "Measurement":
        return cls(value=None, status=Status.SKIPPED, reason=reason)

    @property
    def is_measured(self) -> bool:
        return self.status == Status.MEASURED

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "status": self.status, "reason": self.reason}

    def flatten(self, key: str) -> dict[str, Any]:
        """Expand into ``{key}``/``{key}_status``/``{key}_reason`` columns, the
        convention raw_runs.csv/test comparison CSVs use so a plain ``csv``
        reader (no pandas) can still tell measured apart from missing."""
        return {key: self.value, f"{key}_status": self.status, f"{key}_reason": self.reason}


def measurement_from_dict(d: Mapping[str, Any]) -> Measurement:
    return Measurement(value=d.get("value"), status=str(d.get("status", Status.MISSING)),
                       reason=str(d.get("reason", "")))


# --------------------------------------------------------------------------- #
# Time
# --------------------------------------------------------------------------- #
def utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #
def file_hash(path: str | os.PathLike, algo: str = "sha256", chunk_size: int = 1 << 20) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def file_md5(path: str | os.PathLike) -> str:
    return file_hash(path, "md5")


def file_sha256(path: str | os.PathLike) -> str:
    return file_hash(path, "sha256")


# --------------------------------------------------------------------------- #
# Atomic file I/O -- write-to-temp + os.replace so a crash never leaves a torn
# / partially written artifact behind (required for resumable run state).
# --------------------------------------------------------------------------- #
def atomic_write_bytes(path: str | os.PathLike, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def atomic_write_text(path: str | os.PathLike, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(path: str | os.PathLike, obj: Any, *, indent: int = 2, sort_keys: bool = False) -> None:
    atomic_write_text(path, json.dumps(obj, indent=indent, sort_keys=sort_keys, default=str) + "\n")


def read_json(path: str | os.PathLike) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_json_or(path: str | os.PathLike, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        return read_json(p)
    except (json.JSONDecodeError, OSError):
        return default


def append_jsonl(path: str | os.PathLike, obj: Any) -> None:
    """Append one JSON object as a line. Not atomic across processes (JSONL
    logs are append-only working data, not resumable state); callers that need
    atomicity for authoritative state must use atomic_write_json instead."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def read_jsonl(path: str | os.PathLike) -> list[Any]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# --------------------------------------------------------------------------- #
# Safe subprocess execution -- argument arrays ONLY, never shell=True.
# --------------------------------------------------------------------------- #
@dataclass
class ExecResult:
    argv: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool
    started_at: str
    ended_at: str
    error: str = ""
    cwd: str | None = None

    @property
    def ok(self) -> bool:
        return not self.timed_out and not self.error and self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def run_argv(
    argv: Sequence[str],
    *,
    cwd: str | os.PathLike | None = None,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> ExecResult:
    """Run a command from an argument array. Refuses shell strings outright so
    no caller can accidentally introduce shell injection."""
    if isinstance(argv, (str, bytes)):
        raise TypeError(
            "run_argv() requires a list/tuple of argument strings, not a shell "
            "string -- this harness never invokes a shell."
        )
    argv_list = [str(a) for a in argv]
    started = utcnow_iso()
    t0 = time.monotonic()
    full_env = dict(env) if env is not None else None
    try:
        popen_kwargs: dict[str, Any] = {}
        if os.name == "posix":
            # A timed-out compiler/test runner often has long-lived children.
            # Isolating the command in its own process group lets the timeout
            # path close every inherited stdout/stderr pipe instead of hanging
            # forever in subprocess.run()'s post-kill communicate().
            popen_kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            argv_list,
            cwd=str(cwd) if cwd else None,
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            **popen_kwargs,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        dt = time.monotonic() - t0
        return ExecResult(
            argv=argv_list, returncode=proc.returncode, stdout=stdout or "",
            stderr=stderr or "", duration_s=dt, timed_out=False,
            started_at=started, ended_at=utcnow_iso(), cwd=str(cwd) if cwd else None,
        )
    except subprocess.TimeoutExpired as e:
        if os.name == "posix":
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        stdout, stderr = proc.communicate()
        dt = time.monotonic() - t0
        return ExecResult(
            argv=argv_list, returncode=None, stdout=stdout or "", stderr=stderr or "", duration_s=dt,
            timed_out=True, started_at=started, ended_at=utcnow_iso(),
            error=f"timed out after {timeout}s", cwd=str(cwd) if cwd else None,
        )
    except OSError as e:
        dt = time.monotonic() - t0
        return ExecResult(
            argv=argv_list, returncode=None, stdout="", stderr="", duration_s=dt,
            timed_out=False, started_at=started, ended_at=utcnow_iso(),
            error=repr(e), cwd=str(cwd) if cwd else None,
        )


# --------------------------------------------------------------------------- #
# GitHub Copilot CLI JSONL event parsing (``--output-format json``).
#
# Shared by run.py (the baseagent-* raw-prompt executor, which cannot reuse
# codeweaver.copilot.invoke_agent because that hardcodes ``--agent``) and
# collect.py (trajectory/tool-invocation/cost metrics for RQ4). Kept in one
# place so both modules agree on exactly one interpretation of the event
# schema, mirroring codeweaver/copilot.py's own (private) parsing.
#
# Copilot CLI 1.0.77 emits ``outputTokens`` on each ``assistant.message`` but
# does not expose input-token counts. We sum the observed output fields and
# leave input tokens unavailable rather than estimating them.
# --------------------------------------------------------------------------- #
_INPUT_TOKEN_KEYS = ("inputTokens", "input_tokens", "promptTokens", "prompt_tokens")
_OUTPUT_TOKEN_KEYS = ("outputTokens", "output_tokens", "completionTokens", "completion_tokens")


def parse_copilot_jsonl(raw: str) -> list[dict[str, Any]]:
    """Parse a Copilot CLI ``--output-format json`` transcript (newline-delimited
    JSON) into a list of event dicts. Silently skips blank/unparseable lines
    (a stray non-JSON log line must not abort trajectory parsing)."""
    events: list[dict[str, Any]] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


@dataclass
class CopilotEventSummary:
    """Aggregate counts derived from one agent invocation's JSONL transcript.
    ``tokens_status``/``tokens_reason`` record why token counts are None when
    they are (missing vs. unavailable) -- see Measurement's same convention."""
    exit_code: int | None = None
    assistant_turns: int = 0
    tool_invocations: int = 0
    files_modified: list[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    premium_requests: int | None = None
    nano_aiu: int | None = None
    session_duration_ms: int | None = None
    tool_counts: dict[str, int] = field(default_factory=dict)
    input_tokens: int | None = None
    output_tokens: int | None = None
    tokens_status: str = Status.UNAVAILABLE
    tokens_reason: str = "copilot CLI JSON output did not include a recognized token-count field"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def summarize_copilot_events(events: Sequence[Mapping[str, Any]]) -> CopilotEventSummary:
    summary = CopilotEventSummary()
    message_output_tokens = 0
    has_message_output_tokens = False
    for ev in events:
        if not isinstance(ev, Mapping):
            continue
        etype = ev.get("type")
        if etype == "assistant.message":
            summary.assistant_turns += 1
            data = ev.get("data") if isinstance(ev.get("data"), Mapping) else {}
            tool_requests = data.get("toolRequests")
            if isinstance(tool_requests, list):
                for request in tool_requests:
                    if not isinstance(request, Mapping):
                        continue
                    name = request.get("name")
                    if isinstance(name, str) and name:
                        summary.tool_counts[name] = summary.tool_counts.get(name, 0) + 1
            for key in _OUTPUT_TOKEN_KEYS:
                value = data.get(key)
                if isinstance(value, (int, float)):
                    message_output_tokens += int(value)
                    has_message_output_tokens = True
                    break
        elif etype == "tool.execution_complete":
            summary.tool_invocations += 1
        elif etype == "session.usage_checkpoint":
            data = ev.get("data") if isinstance(ev.get("data"), Mapping) else {}
            nano_aiu = data.get("totalNanoAiu")
            if isinstance(nano_aiu, (int, float)):
                summary.nano_aiu = int(nano_aiu)
            premium = data.get("totalPremiumRequests")
            if isinstance(premium, (int, float)):
                summary.premium_requests = int(premium)
        elif etype == "result":
            summary.exit_code = ev.get("exitCode", summary.exit_code)
            usage = ev.get("usage") if isinstance(ev.get("usage"), Mapping) else {}
            cc = usage.get("codeChanges") if isinstance(usage.get("codeChanges"), Mapping) else {}
            summary.files_modified = list(cc.get("filesModified") or summary.files_modified)
            summary.lines_added = cc.get("linesAdded", summary.lines_added)
            summary.lines_removed = cc.get("linesRemoved", summary.lines_removed)
            summary.premium_requests = usage.get("premiumRequests", summary.premium_requests)
            summary.session_duration_ms = usage.get("sessionDurationMs", summary.session_duration_ms)
            for key in _INPUT_TOKEN_KEYS:
                if key in usage:
                    summary.input_tokens = usage[key]
                    break
            for key in _OUTPUT_TOKEN_KEYS:
                if key in usage:
                    summary.output_tokens = usage[key]
                    break
    if has_message_output_tokens:
        summary.output_tokens = message_output_tokens
    if summary.input_tokens is not None or summary.output_tokens is not None:
        summary.tokens_status = Status.MEASURED
        summary.tokens_reason = (
            "" if summary.input_tokens is not None
            else "output tokens measured; Copilot CLI did not expose input tokens"
        )
    return summary


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #
def probe_tool_version(argv: Sequence[str], *, timeout: float = 15.0) -> Measurement:
    """Best-effort ``<tool> --version``-style probe. Never raises; returns an
    ``unavailable`` Measurement if the tool cannot be launched at all."""
    res = run_argv(argv, timeout=timeout)
    if res.error:
        return Measurement.unavailable(f"{argv[0]} not runnable: {res.error}")
    text = (res.stdout or res.stderr).strip()
    if not text:
        return Measurement.unavailable(f"{argv[0]} produced no output (exit {res.returncode})")
    return Measurement.ok(text.splitlines()[0].strip())


def git_sha(cwd: str | os.PathLike | None = None) -> Measurement:
    res = run_argv(["git", "rev-parse", "HEAD"], cwd=cwd or REPO_ROOT, timeout=15)
    if res.returncode == 0 and res.stdout.strip():
        return Measurement.ok(res.stdout.strip())
    return Measurement.error(res.error or res.stderr.strip() or "git rev-parse failed")


def codeweaver_package_version() -> Measurement:
    try:
        from importlib import metadata as importlib_metadata
        return Measurement.ok(importlib_metadata.version("codeweaver"))
    except Exception as e:  # noqa: BLE001 - best effort provenance, never fatal
        return Measurement.unavailable(f"codeweaver package version unavailable: {e!r}")


def copilot_cli_version() -> Measurement:
    return probe_tool_version(["copilot", "--version"])


TOOLCHAIN_PROBES: dict[str, list[str]] = {
    "rustc": ["rustc", "--version"],
    "cargo": ["cargo", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "java": ["java", "-version"],
    "go": ["go", "version"],
    "git": ["git", "--version"],
}


def collect_provenance(*, model: str | None = None, agent_timeout: float | None = None,
                       probe_toolchains: bool = True) -> dict[str, Any]:
    """Collect a full provenance record for a run/report: model id, CLI
    versions, git SHA, OS, timeout, and best-effort toolchain versions. Every
    field is a Measurement dict (never a fabricated placeholder)."""
    rec: dict[str, Any] = {
        "captured_at": utcnow_iso(),
        "model": Measurement.ok(model).to_dict() if model else Measurement.na("no model specified").to_dict(),
        "agent_timeout_seconds": (
            Measurement.ok(agent_timeout).to_dict() if agent_timeout is not None
            else Measurement.na("no timeout specified").to_dict()
        ),
        "git_sha": git_sha().to_dict(),
        "codeweaver_package_version": codeweaver_package_version().to_dict(),
        "copilot_cli_version": copilot_cli_version().to_dict(),
        "python_version": Measurement.ok(sys.version.split()[0]).to_dict(),
        "os": Measurement.ok(f"{platform.system()} {platform.release()} ({platform.machine()})").to_dict(),
        "hostname": Measurement.ok(socket.gethostname()).to_dict(),
    }
    if probe_toolchains:
        rec["toolchains"] = {
            name: probe_tool_version(argv).to_dict() for name, argv in TOOLCHAIN_PROBES.items()
        }
    return rec


# --------------------------------------------------------------------------- #
# Optional third-party dependencies -- probe, never fabricate availability
# --------------------------------------------------------------------------- #
_OPTIONAL_MODULES = ("pandas", "matplotlib", "reportlab", "scipy", "sentence_transformers", "openpyxl")


def optional_import(name: str):
    """Best-effort import of an optional dependency. Returns the module, or
    None if unavailable. Never raises -- callers must branch on None and
    record an ``unavailable`` Measurement rather than silently degrading."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None
    except Exception:  # noqa: BLE001 - a broken optional install must not crash the harness
        return None


def optional_dependency_report() -> dict[str, bool]:
    return {name: optional_import(name) is not None for name in _OPTIONAL_MODULES}


# --------------------------------------------------------------------------- #
# Minimal, dependency-free JSON-schema-ish validator.
#
# schemas/*.json exist primarily as documentation/interop for external tooling
# that DOES have `jsonschema` installed; this validator lets the harness itself
# check its own outputs against them without adding a dependency. It supports
# the (small) subset of JSON Schema the harness's schemas actually use:
# "type", "required", "properties", "items", "enum", "additionalProperties".
# --------------------------------------------------------------------------- #
_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list, tuple),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}


def _check_type(value: Any, expected: str | list[str], path: str, errors: list[str]) -> bool:
    expected_list = [expected] if isinstance(expected, str) else list(expected)
    for et in expected_list:
        types = _TYPE_MAP.get(et)
        if types is None:
            continue
        # bool is a subclass of int in Python; don't let "integer" accept bools.
        if types == (int, float) and isinstance(value, bool):
            continue
        if isinstance(value, types):
            if et == "integer" and isinstance(value, bool):
                continue
            return True
    errors.append(f"{path}: expected type {expected!r}, got {type(value).__name__}")
    return False


def validate_schema(obj: Any, schema: Mapping[str, Any], *, path: str = "$") -> list[str]:
    """Validate ``obj`` against a (subset-of-JSON-Schema) ``schema``. Returns a
    list of human-readable error strings; empty means valid."""
    errors: list[str] = []
    _validate_node(obj, schema, path, errors)
    return errors


def _validate_node(value: Any, schema: Mapping[str, Any], path: str, errors: list[str]) -> None:
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum {schema['enum']!r}")
    expected_type = schema.get("type")
    if expected_type is not None and not _check_type(value, expected_type, path, errors):
        return
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in value:
                _validate_node(value[key], subschema, f"{path}.{key}", errors)
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            if extra:
                errors.append(f"{path}: unexpected properties {sorted(extra)!r}")
    elif isinstance(value, (list, tuple)):
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _validate_node(item, item_schema, f"{path}[{i}]", errors)


def load_schema(name: str) -> dict[str, Any]:
    p = SCHEMAS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"unknown schema: {name} (looked in {SCHEMAS_DIR})")
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #
class PathTraversalError(Exception):
    """Raised when an archive member (or any adapter-resolved path) would
    escape its intended destination directory."""


class GroundTruthLeakageError(Exception):
    """Raised when code would copy or reference a ground-truth target
    implementation into a location Copilot can read -- a hard safety
    invariant of prepare.py."""


def resolve_within(dest_root: str | os.PathLike, member_name: str) -> Path:
    """Resolve ``member_name`` under ``dest_root`` and raise
    :class:`PathTraversalError` if the result would escape ``dest_root``
    (zip-slip / absolute-path / drive-letter traversal)."""
    dest_root = Path(dest_root).resolve()
    # Reject absolute paths and Windows drive-letter / UNC forms outright --
    # these are unambiguous escape attempts regardless of ".." resolution.
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized) or normalized.startswith("//"):
        raise PathTraversalError(f"archive member has an absolute/drive path: {member_name!r}")
    candidate = (dest_root / normalized).resolve()
    try:
        candidate.relative_to(dest_root)
    except ValueError as e:
        raise PathTraversalError(
            f"archive member {member_name!r} would extract outside {dest_root} (-> {candidate})"
        ) from e
    return candidate


_WINDOWS_ILLEGAL_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def windows_unsafe_reason(member_name: str) -> str | None:
    """Return a human-readable reason if ``member_name`` cannot be created as
    a file/directory name on native Windows (NTFS/vfat), else ``None``. A
    leading drive letter's colon is fine (`C:`); ``resolve_within`` already
    rejects those as traversal, so any other colon here is a real conflict."""
    normalized = member_name.replace("\\", "/")
    for part in normalized.split("/"):
        if not part or part in (".", ".."):
            continue
        if _WINDOWS_ILLEGAL_CHARS.search(part):
            return f"segment {part!r} contains a character illegal on Windows ({_WINDOWS_ILLEGAL_CHARS.pattern})"
        stem = part.rsplit(".", 1)[0].upper()
        if stem in _WINDOWS_RESERVED_NAMES:
            return f"segment {part!r} is a reserved Windows device name"
        if part[-1] in (" ", "."):
            return f"segment {part!r} ends with a space/dot, which Windows silently strips/rejects"
    return None


def is_native_windows() -> bool:
    """True on native Windows. False under WSL (which reports Linux)."""
    return platform.system() == "Windows"


# --------------------------------------------------------------------------- #
# Small formatting helpers shared by collect/analyze/report
# --------------------------------------------------------------------------- #
def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip())
    return re.sub(r"-{2,}", "-", text).strip("-").lower() or "item"


def dict_to_flat_row(d: Mapping[str, Any], *, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict of scalars/Measurements into CSV-friendly columns."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, Measurement):
            out.update(v.flatten(key))
        elif isinstance(v, dict):
            out.update(dict_to_flat_row(v, prefix=f"{key}_"))
        else:
            out[key] = v
    return out


__all__ = [name for name in globals() if not name.startswith("_")]
