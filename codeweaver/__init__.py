"""CodeWeaver: a general-purpose, ReCodeAgent-style multi-agent framework for
LLM-driven code translation and migration.

A small deterministic **Apache Burr** state machine sequences four **GitHub
Copilot CLI** custom agents (Analyzer, Planner, Translator, Validator) through the
paper's workflow:

    analyze -> plan -> select_milestone -> translate -> validate
                            ^                              |
        (passed & more) ----+          repair (failed & iter < max_iter)

Burr owns sequencing, the milestone x repair loop, typed state, crash-resume and
the telemetry UI. It never calls an LLM -- Copilot CLI is the agent runtime.

Everything project-specific (languages, paths, milestones, validation commands,
the project brief) lives in a **project config** (``codeweaver.toml``); the core
package is language- and project-agnostic.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
