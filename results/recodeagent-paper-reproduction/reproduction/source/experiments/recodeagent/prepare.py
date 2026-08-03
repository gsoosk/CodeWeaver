"""prepare.py -- build isolated, leakage-safe per-project workspaces + CodeWeaver
configs + briefs from a manifest.json produced by manifest.py.

For each selected project this writes a self-contained, relocatable template
workspace:

    <workspace_root>/<project_id>/
        codeweaver.toml     # generated CodeWeaver project config (see docs/config.md)
        brief.md            # generated project brief (translation.brief_file)
        source/             # COPY of the manifest row's source tree (never the original)
        oracle/             # COPY of the oracle/tests tree, if the manifest has one
        scaffold/            # CRUST only: COPY of the provided Rust interface/test
                             # scaffold (a contract, not a solution) -> immutable_input

HARD SAFETY INVARIANT: a ``ground_truth_target_rel_path`` (an evaluator-only
reference target implementation, if the artifact ships one for a tool family)
is **never** copied into any workspace, and the generated config/brief text is
scanned to guarantee it never even appears as a string. This is enforced by
:func:`prepare_project` and independently re-checked by
:func:`assert_no_ground_truth_leakage` -- both paths are unit tested. Only
CRUST's *scaffold* (interfaces + tests -- a contract, never a full solution)
may be copied into a workspace, matching the paper's own CRUST-Bench protocol.

The template workspace this module builds is never executed directly -- run.py
clones it per (variant, project, repetition) via :func:`materialize_run` before
invoking anything, so the pristine template (and, transitively, the original
--artifact-root) is never mutated by a run.
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent.common import (
    GroundTruthLeakageError,
    atomic_write_json,
    atomic_write_text,
    slugify,
    utcnow_iso,
)

TEMPLATE_MARKER = ".recodeagent_prepared.json"


def load_experiment_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else C.DEFAULT_EXPERIMENT_CONFIG
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)


# --------------------------------------------------------------------------- #
# Brief + config generation
# --------------------------------------------------------------------------- #
def generate_brief(row: dict[str, Any], spec: dict[str, Any]) -> str:
    label = spec.get("label", row["tool"])
    lines = [
        f"# ReCodeAgent reproduction -- {row['project']} ({label})",
        "",
        f"This project is part of a reproduction of the ReCodeAgent paper (arXiv:2604.07341) "
        f"benchmark suite, run through CodeWeaver. Translate **{row['project']}** faithfully from "
        f"{row['source_language']} to {row['target_language']}.",
        "",
        "## Hard constraints",
        f"- Read the {row['source_language']} source under `source/` (read-only reference; do not edit it).",
        "- Correctness is judged ONLY by the configured build/unit-test/validate commands against "
        "your own translation -- do not weaken, skip, or rewrite the oracle to make it pass.",
        "- Do not fabricate a passing result: a milestone/parity claim must be backed by the "
        "actual command output.",
    ]
    if row.get("oracle_rel_path"):
        lines.append(
            "- A read-only oracle/tests tree is provided under `oracle/` (via `reference_dirs`); "
            "study its contract, never edit it."
        )
    if row.get("scaffold_rel_path"):
        lines.append(
            "- A provided Rust interface + test scaffold is under `scaffold/` (via `immutable_input`); "
            "conform your translation to it -- do not change its public interface."
        )
    lines += ["", "## Scope", f"This is one project (`{row['id']}`) of the reproduction's benchmark matrix; "
             "translate only this project's source tree."]
    return "\n".join(lines) + "\n"


def _fmt_toml_str(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _fmt_toml_list(items: list[str]) -> str:
    return "[" + ", ".join(_fmt_toml_str(i) for i in items) + "]"


def _agent_command_argv(items: list[str]) -> list[str]:
    resolved = list(items)
    if resolved and resolved[0] == "python":
        resolved[0] = sys.executable
    return resolved


def generate_codeweaver_toml(row: dict[str, Any], spec: dict[str, Any], protocol: dict[str, Any], *,
                             has_oracle: bool, has_scaffold: bool) -> str:
    project_id = row["id"]
    slug = slugify(project_id)
    # NOTE: these argv arrays must be serialized with POSIX shell quoting
    # (shlex.join), not a plain " ".join. CodeWeaver's own build_check_cmd/
    # unit_test_cmd/validate_cmd are documented as shell command strings
    # ("validation commands (shell, run by the agents)" -- see
    # codeweaver/config.py) that get interpreted by a POSIX shell on this
    # harness's Linux/WSL execution target. A plain join silently drops the
    # quoting a caller needs whenever an argv element itself contains
    # whitespace or shell metacharacters -- e.g. AlphaTrans's real build_cmd
    # is `["python", "-c", "import compileall,sys; sys.exit(0 if ... else 1)"]`;
    # joined with spaces this becomes `python -c import compileall,sys; ...`,
    # which a shell would split into multiple words/commands instead of a
    # single `-c` payload. shlex.join re-quotes each element so a POSIX
    # shell parses it back into the exact same argv.
    # CodeWeaver launches agents from cfg.root, while these adapter commands
    # are defined relative to the produced target tree (and collect.py runs
    # them with that tree as cwd). Keep one canonical argv in experiment.toml,
    # but render the agent-facing shell command with an explicit working-copy
    # cwd so execution and independent collection address the same project.
    target_prefix = "cd pipeline/target && "
    build_cmd = target_prefix + shlex.join(_agent_command_argv(spec.get("build_cmd", [])))
    unit_test_cmd = target_prefix + shlex.join(_agent_command_argv(spec.get("unit_test_cmd", [])))
    validate_cmd = target_prefix + shlex.join(_agent_command_argv(spec.get("validate_cmd", [])))
    gate_template = spec.get("gate_template", "{tests_or}")
    reference_dirs = _fmt_toml_list(["oracle"]) if has_oracle else "[]"
    immutable_input_line = 'immutable_input = "scaffold"\n' if has_scaffold else ""

    return f"""\
# Generated by experiments/recodeagent/prepare.py -- do NOT edit by hand.
# ReCodeAgent-paper reproduction: project {project_id!r} ({spec.get("label", row["tool"])}).
# Source manifest row id: {project_id}

[project]
name = {_fmt_toml_str(project_id)}
slug = {_fmt_toml_str(slug)}
description = {_fmt_toml_str(
    f"ReCodeAgent reproduction: translate {row['project']} ({spec.get('label', row['tool'])}) "
    f"from {row['source_language']} to {row['target_language']}."
)}

[translation]
source_language = {_fmt_toml_str(row["source_language"])}
target_language = {_fmt_toml_str(row["target_language"])}
brief_file = "brief.md"

[paths]
source_dir = "source"
reference_dirs = {reference_dirs}
{immutable_input_line}working_copy = "pipeline/target"
pipeline_dir = "pipeline"

[commands]
build_check = {_fmt_toml_str(build_cmd)}
unit_test  = {_fmt_toml_str(unit_test_cmd)}
validate   = {_fmt_toml_str(validate_cmd)}

[validation]
gate_template = {_fmt_toml_str(gate_template)}

[model]
default = {_fmt_toml_str(protocol.get("model", "claude-opus-4.8"))}
effort_default = {_fmt_toml_str(protocol.get("effort_default", "high"))}

[execution]
max_iter = {int(protocol.get("max_iter", 5))}
parity_check = true
max_parity_rounds = {int(protocol.get("max_parity_rounds", 3))}
agent_timeout = {int(protocol.get("agent_timeout_seconds", 5000))}

# No [[milestones]] declared: the scope stage generates them at runtime,
# matching this harness's other third-party-benchmark examples (each project's
# structure differs too much for one fixed matrix).
"""


# --------------------------------------------------------------------------- #
# Ground-truth leakage guard
# --------------------------------------------------------------------------- #
def assert_no_ground_truth_leakage(row: dict[str, Any], generated_texts: list[str]) -> None:
    gt = row.get("ground_truth_target_rel_path")
    if not gt:
        return
    for text in generated_texts:
        if gt in text:
            raise GroundTruthLeakageError(
                f"generated artifact for {row['id']} references the ground-truth target path "
                f"{gt!r} -- refusing to write it (this must never be exposed to Copilot)"
            )


# --------------------------------------------------------------------------- #
# Workspace construction
# --------------------------------------------------------------------------- #
@dataclass
class PreparedProject:
    project_id: str
    prepared_dir: Path
    has_oracle: bool
    has_scaffold: bool
    ground_truth_excluded: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id, "prepared_dir": str(self.prepared_dir),
            "has_oracle": self.has_oracle, "has_scaffold": self.has_scaffold,
            "ground_truth_excluded": self.ground_truth_excluded,
        }


def _copy_tree_readonly_source(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def prepare_project(
    row: dict[str, Any],
    *,
    artifact_root: Path,
    workspace_root: Path,
    dataset_spec: dict[str, Any],
    protocol: dict[str, Any],
    force: bool = False,
) -> PreparedProject:
    artifact_root = Path(artifact_root)
    prepared_dir = Path(workspace_root) / row["id"]
    marker = prepared_dir / TEMPLATE_MARKER
    if prepared_dir.exists() and marker.exists() and not force:
        data = C.read_json_or(marker, {})
        return PreparedProject(
            project_id=row["id"], prepared_dir=prepared_dir,
            has_oracle=bool(data.get("has_oracle")), has_scaffold=bool(data.get("has_scaffold")),
            ground_truth_excluded=bool(data.get("ground_truth_excluded", True)),
        )

    if prepared_dir.exists():
        shutil.rmtree(prepared_dir)
    prepared_dir.mkdir(parents=True)

    # 1. Source (read-only reference for the Analyzer; a workspace-local copy
    #    so the pristine --artifact-root is never at risk of being edited).
    source_src = artifact_root / row["source_rel_path"]
    if not source_src.exists():
        raise FileNotFoundError(f"manifest source path missing on disk: {source_src}")
    _copy_tree_readonly_source(source_src, prepared_dir / "source")

    # 2. Oracle (tests/spec only -- safe to expose as a read-only reference_dir).
    has_oracle = bool(row.get("oracle_rel_path"))
    if has_oracle:
        oracle_src = artifact_root / row["oracle_rel_path"]
        if oracle_src.exists():
            _copy_tree_readonly_source(oracle_src, prepared_dir / "oracle")
        else:
            has_oracle = False

    # 3. CRUST-only scaffold (interface + tests contract -- never a solution).
    has_scaffold = bool(row.get("scaffold_rel_path"))
    if has_scaffold:
        scaffold_src = artifact_root / row["scaffold_rel_path"]
        if scaffold_src.exists():
            _copy_tree_readonly_source(scaffold_src, prepared_dir / "scaffold")
        else:
            has_scaffold = False

    # 4. HARD INVARIANT: never touch ground_truth_target_rel_path at all.
    #    (No copy call above ever references it -- this is a belt-and-braces
    #    re-check of the artifacts we ARE about to write.)
    brief_text = generate_brief(row, dataset_spec)
    config_text = generate_codeweaver_toml(row, dataset_spec, protocol,
                                           has_oracle=has_oracle, has_scaffold=has_scaffold)
    assert_no_ground_truth_leakage(row, [brief_text, config_text])

    atomic_write_text(prepared_dir / "brief.md", brief_text)
    atomic_write_text(prepared_dir / "codeweaver.toml", config_text)

    marker_data = {
        "project_id": row["id"], "prepared_at": utcnow_iso(),
        "has_oracle": has_oracle, "has_scaffold": has_scaffold,
        "ground_truth_excluded": True,
        "ground_truth_rel_path_seen": row.get("ground_truth_target_rel_path"),
    }
    atomic_write_json(marker, marker_data)

    return PreparedProject(project_id=row["id"], prepared_dir=prepared_dir,
                           has_oracle=has_oracle, has_scaffold=has_scaffold,
                           ground_truth_excluded=True)


def prepare_all(
    manifest: dict[str, Any],
    *,
    artifact_root: Path,
    workspace_root: Path,
    cfg: dict[str, Any],
    project_ids: set[str] | None = None,
    tools: set[str] | None = None,
    force: bool = False,
) -> list[PreparedProject]:
    specs = cfg.get("datasets", {})
    protocol = cfg.get("protocol", {})
    out = []
    for row in manifest["projects"]:
        if project_ids is not None and row["id"] not in project_ids:
            continue
        if tools is not None and row["tool"] not in tools:
            continue
        spec = specs.get(row["tool"], {})
        out.append(prepare_project(row, artifact_root=artifact_root, workspace_root=workspace_root,
                                   dataset_spec=spec, protocol=protocol, force=force))
    return out


# --------------------------------------------------------------------------- #
# Run materialization (shared with run.py): clone a pristine template into a
# fresh, isolated per-run directory. Relative paths inside codeweaver.toml
# stay correct automatically because the whole self-contained tree moves
# together (config.root == the toml's own directory).
# --------------------------------------------------------------------------- #
def materialize_run(prepared_dir: str | Path, run_dir: str | Path, *, force: bool = False) -> Path:
    prepared_dir = Path(prepared_dir)
    run_dir = Path(run_dir)
    if not (prepared_dir / "codeweaver.toml").exists():
        raise FileNotFoundError(f"{prepared_dir} is not a prepared workspace (no codeweaver.toml)")
    if run_dir.exists():
        if not force and (run_dir / "codeweaver.toml").exists():
            return run_dir  # idempotent: already materialized
        shutil.rmtree(run_dir)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(prepared_dir, run_dir, ignore=shutil.ignore_patterns("pipeline", TEMPLATE_MARKER))
    return run_dir


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="prepare.py",
        description="Build isolated, leakage-safe per-project CodeWeaver workspaces from manifest.json.",
    )
    ap.add_argument("--manifest", required=True, help="path to manifest.json (from manifest.py)")
    ap.add_argument("--artifact-root", required=True, help="the original, read-only extracted artifact root")
    ap.add_argument("--workspace-root", required=True, help="where prepared workspaces are written")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--project", default=None, help="comma-separated project ids to prepare (default: all)")
    ap.add_argument("--tool", default=None, help="comma-separated tool keys to prepare (default: all)")
    ap.add_argument("--force", action="store_true", help="rebuild even if already prepared")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_experiment_config(args.config)
    manifest = C.read_json(args.manifest)
    project_ids = set(args.project.split(",")) if args.project else None
    tools = set(args.tool.split(",")) if args.tool else None

    prepared = prepare_all(
        manifest, artifact_root=Path(args.artifact_root), workspace_root=Path(args.workspace_root),
        cfg=cfg, project_ids=project_ids, tools=tools, force=args.force,
    )
    for p in prepared:
        print(f"[prepare] {p.project_id}: {p.prepared_dir} "
             f"(oracle={p.has_oracle} scaffold={p.has_scaffold})")
    print(f"[prepare] prepared {len(prepared)} project workspace(s) under {args.workspace_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
