"""GitHub Copilot CLI backend.

This is the **model-matched** backend: it drives the same `copilot` binary, the same
model and the same reasoning effort that CodeWeaver's own agents use, so a baseline
number produced here differs from CodeWeaver only in the scaffolding -- which is the
whole point of the comparison.

The CLI receives the prompt on stdin, with an empty tool allowlist and explicit
read/write/shell denials. Custom instructions and built-in MCP servers are disabled.
Every response is audited; any attempted tool call invalidates the generation.

Usage (premium requests, AIU) is recovered from the JSONL event stream, so this
backend reports real cost where the Foundry one can only report tokens.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .base import Completion, Usage


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
    ):
        self.model = model
        self.effort = effort
        self.timeout = timeout
        self.binary = binary
        self.audit_dir = Path(audit_dir) if audit_dir is not None else None
        self.context = context
        self.audit_records: list[dict] = []
        self.calls = 0

    def complete(self, system: str, user: str) -> Completion:
        # The CLI has no separate system slot in one-shot mode; prepend it.
        prompt = f"{system}\n\n---\n\n{user}" if system else user
        return self._invoke(prompt)

    def complete_messages(self, messages: list[dict]) -> Completion:
        """Flatten a message list into one prompt.

        The CLI is single-turn, so a continuation round is replayed as prompt +
        what has been produced so far + what is still outstanding. The model still
        receives no correctness feedback.
        """
        parts = []
        for m in messages:
            role = m.get("role", "user")
            tag = {"system": "", "user": "", "assistant": "## Already written\n"}.get(role, "")
            parts.append(f"{tag}{m.get('content', '')}")
        return self._invoke("\n\n---\n\n".join(parts))

    def _invoke(self, prompt: str) -> Completion:
        # A whole-repo prompt is hundreds of KB, which blows past ARG_MAX if passed
        # as `-p <text>`. The CLI reads the prompt from stdin when -p is omitted.
        self.calls += 1
        audit = None
        if self.audit_dir is not None:
            audit = self.audit_dir / f"round-{self.calls:02d}"
            audit.mkdir(parents=True, exist_ok=False)
        with tempfile.TemporaryDirectory(prefix="cw_singleshot_") as cwd:
            cmd = [
                self.binary,
                "--model", self.model,
                "--reasoning-effort", self.effort,
                "--available-tools=", "--deny-tool=read", "--deny-tool=write", "--deny-tool=shell",
                "--disable-builtin-mcps", "--no-custom-instructions",
                "--no-ask-user", "--no-auto-update",
                "--output-format", "json", "--no-color",
            ]
            if self.context is not None:
                cmd.extend(["--context", self.context])
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
                        (audit / name).write_text(content or "", encoding="utf-8")
                raise
            elapsed = time.monotonic() - t0
        if audit is not None:
            (audit / "stdout.jsonl").write_text(proc.stdout, encoding="utf-8")
            (audit / "stderr.txt").write_text(proc.stderr, encoding="utf-8")

        text, premium, aiu = "", None, None
        tool_events = []
        event_counts: dict[str, int] = {}
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("Malformed Copilot JSONL; cannot audit tool access") from exc
            kind = ev.get("type")
            if isinstance(kind, str):
                event_counts[kind] = event_counts.get(kind, 0) + 1
                if kind.startswith("tool.execution_") or kind == "assistant.tool_call_delta":
                    tool_events.append(kind)
            if kind == "assistant.message":
                if ev.get("data", {}).get("toolRequests"):
                    tool_events.append("assistant.message.toolRequests")
                text = ev.get("data", {}).get("content", "") or text
            elif kind == "session.usage_checkpoint":
                d = ev.get("data", {})
                premium = d.get("totalPremiumRequests", premium)
                aiu = d.get("totalNanoAiu", aiu)
            elif kind == "result":
                u = ev.get("usage", {}) or {}
                premium = u.get("premiumRequests", premium)

        record = {
            "round": self.calls, "tools": "disabled",
            "tool_event_count": len(tool_events), "event_counts": event_counts,
            "returncode": proc.returncode,
        }
        self.audit_records.append(record)
        if audit is not None:
            (audit / "audit.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        if tool_events:
            raise RuntimeError(f"B0 protocol violation: tool activity observed: {tool_events[:5]}")
        if proc.returncode != 0 or not text:
            raise RuntimeError(
                f"copilot exited {proc.returncode}; assistant message present={bool(text)}; "
                f"stderr: {proc.stderr[:800]}"
            )

        # The CLI does not expose a finish_reason, so truncation cannot be detected
        # here directly. The harness infers it instead: a module that fails to parse,
        # or an expected module that never arrived, drives the continuation loop.
        return Completion(
            text=text,
            usage=Usage(premium_requests=premium, nano_aiu=aiu,
                        wall_clock_s=round(elapsed, 2)),
            model=self.model,
            raw={"finish_reason": None, "truncated": False},
        )
