"""Pluggable LLM backends for the baseline harnesses.

A backend is anything that can turn (system, user) into text plus a usage record.
Keeping this abstract lets the same baseline protocol run against:

  * `copilot`  -- the GitHub Copilot CLI, i.e. the EXACT model/effort CodeWeaver
                  itself uses. This is the model-matched configuration and should
                  be the default for any published comparison.
  * `foundry`  -- Azure AI Foundry, for models Copilot does not serve.

Model matching matters: a baseline run on a different model measures the model, not
the scaffolding. Always report which backend produced a number.
"""
from __future__ import annotations

import dataclasses
from typing import Protocol


@dataclasses.dataclass
class Usage:
    """What a single call cost. Fields are None when a backend cannot report them."""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    premium_requests: float | None = None
    nano_aiu: int | None = None
    wall_clock_s: float | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}


@dataclasses.dataclass
class Completion:
    text: str
    usage: Usage
    model: str
    raw: dict | None = None


class LLMBackend(Protocol):
    """Minimal surface every backend implements."""

    name: str
    model: str

    def complete(self, system: str, user: str) -> Completion:
        ...


def build_backend(kind: str, model: str, **kw) -> LLMBackend:
    """Factory. Imports lazily so an unused backend's deps are never required."""
    if kind == "foundry":
        from .foundry import FoundryBackend
        return FoundryBackend(model=model, **kw)
    if kind == "copilot":
        from .copilot import CopilotBackend
        return CopilotBackend(model=model, **kw)
    raise ValueError(f"unknown backend {kind!r} (expected 'foundry' or 'copilot')")
