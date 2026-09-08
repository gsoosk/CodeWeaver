"""GitHub Copilot CLI backend.

This is the **model-matched** backend: it drives the same `copilot` binary, the same
model and the same reasoning effort that CodeWeaver's own agents use, so a baseline
number produced here differs from CodeWeaver only in the scaffolding -- which is the
whole point of the comparison.

The CLI receives the prompt on stdin, with a non-matching tool allowlist and explicit
read/write/shell denials. Custom instructions and built-in MCP servers are disabled.
Every response is audited; any attempted tool call invalidates the generation.

Usage (premium requests, AIU) is recovered from the JSONL event stream, so this
backend reports real cost where the Foundry one can only report tokens.
"""
from __future__ import annotations

import json
import hashlib
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import tempfile
import time

from .base import Completion, Usage


def command(binary: str, model: str, effort: str, context: str | None) -> list[str]:
    """The exact audited, no-tools invocation, also checked during offline replay."""
    argv = [
        binary, "--model", model, "--reasoning-effort", effort,
        # An empty list means "use defaults"; match no registered tool instead.
        "--available-tools=__b0_no_tools__",
        "--deny-tool=read", "--deny-tool=write", "--deny-tool=shell",
        "--disable-builtin-mcps", "--no-custom-instructions",
        "--no-ask-user", "--no-auto-update",
        "--output-format", "json", "--no-color",
    ]
    if context is not None:
        argv.extend(["--context", context])
    return argv


def flatten_messages(messages: list[dict]) -> str:
    parts = []
    for message in messages:
        tag = "## Already written\n" if message["role"] == "assistant" else ""
        parts.append(f"{tag}{message['content']}")
    return "\n\n---\n\n".join(parts)


def checked_number(value: object, label: str, *, integer: bool = False) -> int | float:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or (isinstance(value, float) and not math.isfinite(value)) or value < 0
            or (integer and not isinstance(value, int))):
        raise ValueError(f"Invalid {label}: expected a nonnegative {'integer' if integer else 'number'}")
    return value


def strict_json(content: str | bytes) -> object:
    def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(content, object_pairs_hook=unique_keys, parse_constant=invalid_constant)


@dataclass
class CopilotEvents:
    assistant_messages: list[str] = field(default_factory=list)
    transcript_messages: list[dict[str, str]] = field(default_factory=list)
    event_counts: dict[str, int] = field(default_factory=dict)
    tool_events: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    def validate_user_messages(self, prompt: str) -> None:
        allowed = {"", prompt, "Please continue from where you left off."}
        if any(message["role"] == "user" and message["content"] not in allowed
               for message in self.transcript_messages):
            raise ValueError("Unexpected Copilot user message; cannot verify test-blind continuation")

    def audit(self, round_i: int, returncode: int) -> dict:
        return {
            "round": round_i, "tools": "disabled",
            "tool_allowlist": ["__b0_no_tools__"],
            "tool_event_count": len(self.tool_events), "event_counts": self.event_counts,
            "returncode": returncode, "usage": self.usage.as_dict(),
        }

    def completion(self, model: str, returncode: int, stderr: str = "") -> Completion:
        if self.tool_events:
            raise RuntimeError(f"B0 protocol violation: tool activity observed: {self.tool_events[:5]}")
        if returncode != 0 or not self.assistant_messages:
            raise RuntimeError(
                f"copilot exited {returncode}; assistant message present={bool(self.assistant_messages)}; "
                f"stderr: {stderr[:800]}"
            )
        return Completion(
            text="\n\n".join(self.assistant_messages), usage=self.usage, model=model,
            raw={"finish_reason": None, "truncated": False,
                 "assistant_messages": self.assistant_messages,
                 "transcript_messages": self.transcript_messages,
                 "event_counts": self.event_counts},
        )


def decode_events(stdout: str) -> CopilotEvents:
    """Decode live or saved JSONL, fail closed on malformed or unauditable events."""
    decoded = CopilotEvents()
    for line_no, line in enumerate(stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = strict_json(line)
        except ValueError as exc:
            raise ValueError(f"Malformed Copilot JSONL at line {line_no}; cannot audit tool access") from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str) or not event["type"]:
            raise ValueError(f"Invalid Copilot event at line {line_no}")
        kind = event["type"]
        data = event.get("data", {})
        if not isinstance(data, dict):
            raise ValueError(f"Invalid Copilot event data at line {line_no}")
        decoded.event_counts[kind] = decoded.event_counts.get(kind, 0) + 1
        if kind.startswith("tool.") or kind.startswith("assistant.tool_call"):
            decoded.tool_events.append(kind)
        if kind in ("assistant.message", "user.message"):
            content = data.get("content", "")
            if kind == "assistant.message" and content is None:
                content = ""
            if not isinstance(content, str):
                raise ValueError(f"Invalid {kind} content at line {line_no}")
            requests = data.get("toolRequests")
            if requests is not None and not isinstance(requests, list):
                raise ValueError(f"Invalid toolRequests at line {line_no}")
            if requests:
                decoded.tool_events.append(f"{kind}.toolRequests")
            decoded.transcript_messages.append({"role": kind.split(".")[0], "content": content})
            if kind == "assistant.message" and content:
                decoded.assistant_messages.append(content)
        if kind == "session.usage_checkpoint":
            for key, attr, integer in (
                ("totalPremiumRequests", "premium_requests", False),
                ("totalNanoAiu", "nano_aiu", True),
            ):
                if key in data:
                    setattr(decoded.usage, attr, checked_number(data[key], key, integer=integer))
        elif kind == "result":
            usage = event.get("usage", {})
            if usage is None:
                usage = {}
            if not isinstance(usage, dict):
                raise ValueError(f"Invalid result usage at line {line_no}")
            if "premiumRequests" in usage:
                decoded.usage.premium_requests = checked_number(usage["premiumRequests"], "premiumRequests")
    return decoded


class CopilotBackend:
    name = "copilot"

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        effort: str = "medium",
        timeout: float = 3600.0,
        binary: str = "copilot",
        audit_dir: str | Path | None = None,
        context: str | None = None,
        start_round: int = 0,
    ):
        self.model = model
        self.effort = effort
        self.timeout = timeout
        self.binary = binary
        self.audit_dir = Path(audit_dir) if audit_dir is not None else None
        self.context = context
        self.audit_records: list[dict] = []
        if type(start_round) is not int or start_round < 0:
            raise ValueError("start_round must be a nonnegative invocation count")
        self.calls = start_round

    def complete(self, system: str, user: str) -> Completion:
        # The CLI has no separate system slot in one-shot mode; prepend it.
        prompt = f"{system}\n\n---\n\n{user}" if system else user
        return self._invoke(prompt)

    def complete_messages(self, messages: list[dict]) -> Completion:
        """Flatten a message list into one prompt.

        Outer invocations replay the prompt and closed modules with no correctness
        feedback. The CLI can also internally continue within one invocation.
        """
        return self._invoke(flatten_messages(messages))

    def _invoke(self, prompt: str) -> Completion:
        # A whole-repo prompt is hundreds of KB, which blows past ARG_MAX if passed
        # as `-p <text>`. The CLI reads the prompt from stdin when -p is omitted.
        self.calls += 1
        audit = None
        if self.audit_dir is not None:
            audit = self.audit_dir / f"round-{self.calls:02d}"
            audit.mkdir(parents=True, exist_ok=False)
        with tempfile.TemporaryDirectory(prefix="cw_singleshot_", dir=Path.cwd()) as cwd:
            cmd = command(self.binary, self.model, self.effort, self.context)
            if audit is not None:
                (audit / "request.json").write_text(json.dumps({
                    "argv": cmd, "cwd_policy": "empty temporary directory",
                    "prompt_chars": len(prompt),
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                }, indent=2), encoding="utf-8")
            t0 = time.monotonic()
            try:
                proc = subprocess.run(
                    cmd, cwd=cwd, input=prompt, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=self.timeout,
                    env={**os.environ},
                )
            except subprocess.TimeoutExpired as exc:
                if audit is not None:
                    for name, content in (("stdout.jsonl", exc.stdout), ("stderr.txt", exc.stderr)):
                        if isinstance(content, bytes):
                            content = content.decode("utf-8", errors="replace")
                        (audit / name).write_text(content or "", encoding="utf-8", newline="\n")
                    (audit / "audit.json").write_text(json.dumps({
                        "round": self.calls, "returncode": None,
                        "valid": False, "error": "CLI invocation timed out",
                    }, indent=2), encoding="utf-8")
                raise
            elapsed = time.monotonic() - t0
        if audit is not None:
            (audit / "stdout.jsonl").write_text(proc.stdout, encoding="utf-8", newline="\n")
            (audit / "stderr.txt").write_text(proc.stderr, encoding="utf-8", newline="\n")

        try:
            decoded = decode_events(proc.stdout)
            decoded.validate_user_messages(prompt)
        except ValueError as exc:
            if audit is not None:
                (audit / "audit.json").write_text(json.dumps({
                    "round": self.calls, "returncode": proc.returncode,
                    "valid": False, "error": str(exc),
                }, indent=2), encoding="utf-8")
            raise RuntimeError(str(exc)) from exc
        decoded.usage.wall_clock_s = round(elapsed, 2)
        record = decoded.audit(self.calls, proc.returncode)
        self.audit_records.append(record)
        if audit is not None:
            (audit / "audit.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return decoded.completion(self.model, proc.returncode, proc.stderr)
