"""GitHub Copilot CLI backend.

This is the **model-matched** backend: it drives the same `copilot` binary, the same
model and the same reasoning effort that CodeWeaver's own agents use, so a baseline
number produced here differs from CodeWeaver only in the scaffolding -- which is the
whole point of the comparison.

The CLI is invoked in one-shot mode with tools disabled as far as the surface allows:
the baseline must be a SINGLE generation, not an agent loop. We pass the prompt on
stdin-free `-p`, ask for JSON output, and read the final assistant message.

Usage (premium requests, AIU) is recovered from the JSONL event stream, so this
backend reports real cost where the Foundry one can only report tokens.
"""
from __future__ import annotations

import json
import os
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
    ):
        self.model = model
        self.effort = effort
        self.timeout = timeout
        self.binary = binary

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
        with tempfile.TemporaryDirectory(prefix="cw_singleshot_") as cwd:
            cmd = [
                self.binary,
                "--model", self.model,
                "--reasoning-effort", self.effort,
                "--allow-all", "--no-ask-user",
                "--output-format", "json", "--no-color",
            ]
            t0 = time.monotonic()
            proc = subprocess.run(
                cmd, cwd=cwd, input=prompt, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.timeout,
                env={**os.environ},
            )
            elapsed = time.monotonic() - t0

        text, premium, aiu = "", None, None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = ev.get("type")
            if kind == "assistant.message":
                text = ev.get("data", {}).get("content", "") or text
            elif kind == "session.usage_checkpoint":
                d = ev.get("data", {})
                premium = d.get("totalPremiumRequests", premium)
                aiu = d.get("totalNanoAiu", aiu)
            elif kind == "result":
                u = ev.get("usage", {}) or {}
                premium = u.get("premiumRequests", premium)

        if not text and proc.returncode != 0:
            raise RuntimeError(
                f"copilot exited {proc.returncode} with no assistant message; "
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
