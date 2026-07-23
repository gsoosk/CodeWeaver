"""Project configuration for CodeWeaver.

A CodeWeaver run is fully described by a project config file -- TOML (preferred;
parsed with the stdlib ``tomllib`` on Python 3.11+), JSON, or YAML (if PyYAML is
installed). The config captures everything that recodeAgent hard-coded for the
xcvrd port: the source/target languages, the project brief, the paths the agents
read/write, the milestone matrix, the validation commands, and model/effort.

The active config is stashed in a module-level slot (``set_active`` /
``active``) so the Burr ``@action`` functions -- whose signatures are fixed by
Burr -- can reach it without threading it through every call.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Milestone:
    """One cumulative slice of the translation.

    A milestone's gate is CUMULATIVE: it must pass its own ``tests`` AND every
    earlier milestone's tests (regression safety). ``tests`` are opaque selector
    tokens (e.g. pytest module stems, test names, tags) that ``gate_template``
    turns into a concrete gate string for the validate command.
    """

    id: str
    title: str
    goal: str
    tests: list[str] = field(default_factory=list)
    marker: str = ""          # optional extra selector (e.g. a pytest -m marker)


@dataclass(frozen=True)
class ModelConfig:
    default: str = "claude-opus-4.8"
    effort_default: str = "high"
    effort: dict[str, str] = field(default_factory=dict)  # per-agent overrides

    def effort_for(self, agent: str) -> str:
        return self.effort.get(agent, self.effort_default)


@dataclass
class Config:
    # identity
    name: str
    slug: str
    description: str = ""

    # translation intent
    source_language: str = "the source language"
    target_language: str = "the target language"
    brief: str = ""                       # project-specific knowledge for every agent

    # paths (all relative to `root`, which is the config file's directory)
    root: Path = field(default_factory=lambda: Path("."))
    source_dir: str = "source"
    reference_dirs: list[str] = field(default_factory=list)   # extra --add-dir grants
    immutable_input: str = ""             # copied to working_copy; never edited (optional)
    working_copy: str = ""                # mutable copy the agents translate into (optional)
    pipeline_dir: str = "pipeline"        # runtime hand-off + artifacts + logs
    analysis_artifact: str = "analysis.md"
    plan_artifact: str = "plan.json"
    report_artifact: str = "report.json"

    # validation commands (shell, run by the agents; support {placeholders})
    build_check_cmd: str = ""
    unit_test_cmd: str = ""
    validate_cmd: str = ""
    gate_template: str = "{tests_or}"     # how cumulative tests become a gate string

    # execution
    model: ModelConfig = field(default_factory=ModelConfig)
    milestones: list[Milestone] = field(default_factory=list)
    max_iter: int = 5
    db_path: str = ""                     # sqlite persistence (default: <pipeline>/burr.db)
    agent_timeout: float | None = None    # per-agent wall-clock cap (seconds)

    # optional prompt-template overrides, keyed by stage
    # (analyze|plan|translate|validate). Empty -> use codeweaver.prompts defaults.
    prompts: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Resolved paths
    # ------------------------------------------------------------------ #
    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p)

    @property
    def source_path(self) -> Path:
        return self.path(self.source_dir)

    @property
    def pipeline_path(self) -> Path:
        override = os.environ.get("CODEWEAVER_PIPELINE_DIR")
        return Path(override) if override else self.path(self.pipeline_dir)

    @property
    def logs_path(self) -> Path:
        return self.pipeline_path / "logs"

    @property
    def working_copy_path(self) -> Path | None:
        return self.path(self.working_copy) if self.working_copy else None

    @property
    def immutable_input_path(self) -> Path | None:
        return self.path(self.immutable_input) if self.immutable_input else None

    def artifact_path(self, name: str) -> Path:
        return self.pipeline_path / name

    @property
    def analysis_path(self) -> Path:
        return self.artifact_path(self.analysis_artifact)

    @property
    def plan_path(self) -> Path:
        return self.artifact_path(self.plan_artifact)

    @property
    def report_path(self) -> Path:
        return self.artifact_path(self.report_artifact)

    @property
    def reference_paths(self) -> list[Path]:
        return [self.path(r) for r in self.reference_dirs]

    @property
    def resolved_db_path(self) -> str:
        return self.db_path or str(self.pipeline_path / "burr.db")

    # ------------------------------------------------------------------ #
    # Validation env passed to the agent shell (points tools at the working copy)
    # ------------------------------------------------------------------ #
    def extra_env(self) -> dict[str, str]:
        env: dict[str, str] = {"CODEWEAVER_PIPELINE_DIR": str(self.pipeline_path)}
        wc = self.working_copy_path
        if wc is not None:
            # Mirror recodeAgent's RECODE_CRATE_DIR so project build scripts can
            # target the working copy. Generic name + legacy alias.
            env["CODEWEAVER_WORKING_COPY"] = str(wc)
        return env


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _load_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".toml", ""):
        try:
            import tomllib
        except ModuleNotFoundError as e:  # pragma: no cover - py<3.11
            raise RuntimeError(
                "TOML config needs Python 3.11+ (tomllib). Use a .json config, "
                "or upgrade Python."
            ) from e
        return tomllib.loads(text)
    if suffix == ".json":
        return json.loads(text)
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ModuleNotFoundError as e:
            raise RuntimeError("YAML config needs PyYAML (`pip install pyyaml`).") from e
        return yaml.safe_load(text)
    raise RuntimeError(f"Unsupported config format: {path.suffix} ({path})")


def _milestones_from(raw: Any) -> list[Milestone]:
    out: list[Milestone] = []
    for m in raw or []:
        out.append(
            Milestone(
                id=str(m["id"]),
                title=str(m.get("title", m["id"])),
                goal=str(m.get("goal", "")),
                tests=[str(t) for t in (m.get("tests") or [])],
                marker=str(m.get("marker", "")),
            )
        )
    return out


def load(config_path: str | os.PathLike) -> Config:
    """Load and validate a project config file into a :class:`Config`."""
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    raw = _load_raw(path)
    root = path.parent

    proj = raw.get("project", {}) or {}
    name = str(proj.get("name") or path.parent.name)
    slug = str(proj.get("slug") or name).strip().replace(" ", "-").lower()

    trans = raw.get("translation", {}) or {}
    paths = raw.get("paths", {}) or {}
    cmds = raw.get("commands", {}) or {}
    validation = raw.get("validation", {}) or {}
    model_raw = raw.get("model", {}) or {}
    exec_raw = raw.get("execution", {}) or {}

    # root override lets a config live elsewhere than the project it describes
    if paths.get("root"):
        root = (path.parent / paths["root"]).resolve()

    model = ModelConfig(
        default=str(model_raw.get("default", "claude-opus-4.8")),
        effort_default=str(model_raw.get("effort_default", "high")),
        effort={k: str(v) for k, v in (model_raw.get("effort", {}) or {}).items()},
    )

    cfg = Config(
        name=name,
        slug=slug,
        description=str(proj.get("description", "")),
        source_language=str(trans.get("source_language", "the source language")),
        target_language=str(trans.get("target_language", "the target language")),
        brief=str(trans.get("brief", "")),
        root=root,
        source_dir=str(paths.get("source_dir", "source")),
        reference_dirs=[str(r) for r in (paths.get("reference_dirs") or [])],
        immutable_input=str(paths.get("immutable_input", "")),
        working_copy=str(paths.get("working_copy", "")),
        pipeline_dir=str(paths.get("pipeline_dir", "pipeline")),
        analysis_artifact=str(paths.get("analysis_artifact", "analysis.md")),
        plan_artifact=str(paths.get("plan_artifact", "plan.json")),
        report_artifact=str(paths.get("report_artifact", "report.json")),
        build_check_cmd=str(cmds.get("build_check", "")),
        unit_test_cmd=str(cmds.get("unit_test", "")),
        validate_cmd=str(cmds.get("validate", "")),
        gate_template=str(validation.get("gate_template", "{tests_or}")),
        model=model,
        milestones=_milestones_from(raw.get("milestones")),
        max_iter=int(exec_raw.get("max_iter", 5)),
        db_path=str(exec_raw.get("db_path", "")),
        agent_timeout=exec_raw.get("agent_timeout"),
        prompts={k: str(v) for k, v in (raw.get("prompts", {}) or {}).items()},
    )

    if not cfg.milestones:
        raise ValueError(
            f"{path}: at least one [[milestones]] entry is required."
        )
    return cfg


# --------------------------------------------------------------------------- #
# Active-config slot (so Burr @action functions can reach the config)
# --------------------------------------------------------------------------- #
_ACTIVE: Config | None = None


def set_active(cfg: Config) -> None:
    global _ACTIVE
    _ACTIVE = cfg


def active() -> Config:
    if _ACTIVE is None:
        raise RuntimeError("no active CodeWeaver config; call config.set_active(cfg) first")
    return _ACTIVE
