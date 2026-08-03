"""Tests for experiments/recodeagent/prepare.py: isolated per-project workspace
construction, the hard ground-truth-leakage safety invariant, generated
CodeWeaver config validity (checked against the REAL codeweaver.config.load
so the harness stays honest about integrating with CodeWeaver's actual
schema), idempotency/force-rebuild semantics, and run materialization.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import prepare as P

# The real CodeWeaver config loader -- used to validate generated TOML against
# CodeWeaver's actual schema, not a re-implementation of it.
from codeweaver import config as cw_config

PROTOCOL = {
    "model": "claude-opus-4.8", "effort_default": "high",
    "max_iter": 5, "max_parity_rounds": 3, "agent_timeout_seconds": 5000,
}

CRUST_SPEC = {
    "label": "CRUST", "source_language": "C", "target_language": "Rust",
    "build_cmd": ["cargo", "build"], "unit_test_cmd": ["cargo", "test"],
    "validate_cmd": ["cargo", "test", "{gate}"], "gate_template": "{tests_or}",
}
SKEL_SPEC = {
    "label": "SKEL", "source_language": "Python", "target_language": "JavaScript",
    "build_cmd": ["npm", "install"], "unit_test_cmd": ["npm", "test"],
    "validate_cmd": ["npm", "test", "--", "{gate}"], "gate_template": "{tests_or}",
}


def _make_source_tree(root: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


@pytest.fixture()
def artifact_root(tmp_path: Path) -> Path:
    root = tmp_path / "artifact"
    _make_source_tree(root / "bitset" / "CBench", {"main.c": "int f(void) { return 0; }\n"})
    _make_source_tree(root / "bitset" / "RBench", {"lib.rs": "// oracle scaffold\n"})
    _make_source_tree(root / "bitset" / "interfaces", {"lib.rs": "pub trait Bitset {}\n"})
    _make_source_tree(root / "bitset" / "solution", {"lib.rs": "// SECRET ground truth solution -- must never leak\n"})
    _make_source_tree(root / "leftpad" / "src", {"main.py": "def pad(s):\n    return s\n"})
    return root


def _crust_row(has_ground_truth: bool = True) -> dict:
    return {
        "id": "crust__bitset", "tool": "crust", "project": "bitset",
        "source_language": "C", "target_language": "Rust",
        "source_rel_path": str(Path("bitset") / "CBench"),
        "oracle_rel_path": str(Path("bitset") / "RBench"),
        "scaffold_rel_path": str(Path("bitset") / "interfaces"),
        "ground_truth_target_rel_path": str(Path("bitset") / "solution") if has_ground_truth else None,
        "loc_source": 1, "test_count_source": 0, "function_count_source": 1,
        "status": "ok", "notes": "", "discovered_at": C.utcnow_iso(),
    }


def _skel_row() -> dict:
    return {
        "id": "skel__leftpad", "tool": "skel", "project": "leftpad",
        "source_language": "Python", "target_language": "JavaScript",
        "source_rel_path": str(Path("leftpad") / "src"),
        "oracle_rel_path": None, "scaffold_rel_path": None,
        "ground_truth_target_rel_path": None,
        "loc_source": 2, "test_count_source": 0, "function_count_source": 1,
        "status": "ok", "notes": "", "discovered_at": C.utcnow_iso(),
    }


# --------------------------------------------------------------------------- #
# Basic workspace construction
# --------------------------------------------------------------------------- #
def test_prepare_project_copies_source_generates_config_and_brief(tmp_path: Path, artifact_root: Path):
    workspace_root = tmp_path / "workspaces"
    result = P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=workspace_root,
                               dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    assert result.prepared_dir == workspace_root / "crust__bitset"
    assert (result.prepared_dir / "source" / "main.c").exists()
    assert (result.prepared_dir / "codeweaver.toml").exists()
    assert (result.prepared_dir / "brief.md").exists()


def test_prepare_project_copies_oracle_and_scaffold_when_present(tmp_path: Path, artifact_root: Path):
    result = P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                               dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    assert result.has_oracle is True
    assert result.has_scaffold is True
    assert (result.prepared_dir / "oracle" / "lib.rs").read_text(encoding="utf-8") == "// oracle scaffold\n"
    assert (result.prepared_dir / "scaffold" / "lib.rs").read_text(encoding="utf-8") == "pub trait Bitset {}\n"


def test_prepare_project_skips_oracle_and_scaffold_when_absent(tmp_path: Path, artifact_root: Path):
    result = P.prepare_project(_skel_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                               dataset_spec=SKEL_SPEC, protocol=PROTOCOL)
    assert result.has_oracle is False
    assert result.has_scaffold is False
    assert not (result.prepared_dir / "oracle").exists()
    assert not (result.prepared_dir / "scaffold").exists()


# --------------------------------------------------------------------------- #
# HARD SAFETY INVARIANT: ground-truth target must never leak
# --------------------------------------------------------------------------- #
def test_ground_truth_directory_is_never_copied_into_workspace(tmp_path: Path, artifact_root: Path):
    result = P.prepare_project(_crust_row(has_ground_truth=True), artifact_root=artifact_root,
                               workspace_root=tmp_path / "ws", dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    assert result.ground_truth_excluded is True
    # No file or directory named like the ground-truth tree exists anywhere
    # under the prepared workspace, and the secret marker string is absent
    # from every text file we wrote.
    assert not (result.prepared_dir / "solution").exists()
    for p in result.prepared_dir.rglob("*"):
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            assert "SECRET ground truth" not in text


def test_assert_no_ground_truth_leakage_raises_when_path_string_present():
    row = _crust_row(has_ground_truth=True)
    with pytest.raises(C.GroundTruthLeakageError):
        P.assert_no_ground_truth_leakage(row, [f"some text mentioning {row['ground_truth_target_rel_path']}"])


def test_assert_no_ground_truth_leakage_noop_when_absent():
    row = _crust_row(has_ground_truth=False)
    P.assert_no_ground_truth_leakage(row, ["totally unrelated text"])  # must not raise


def test_generated_brief_and_config_never_literally_contain_ground_truth_path(tmp_path: Path, artifact_root: Path):
    row = _crust_row(has_ground_truth=True)
    brief = P.generate_brief(row, CRUST_SPEC)
    config_text = P.generate_codeweaver_toml(row, CRUST_SPEC, PROTOCOL, has_oracle=True, has_scaffold=True)
    assert row["ground_truth_target_rel_path"] not in brief
    assert row["ground_truth_target_rel_path"] not in config_text


# --------------------------------------------------------------------------- #
# Generated config is valid per the REAL codeweaver.config schema
# --------------------------------------------------------------------------- #
def test_generated_config_loads_via_real_codeweaver_config(tmp_path: Path, artifact_root: Path):
    result = P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                               dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    cfg = cw_config.load(result.prepared_dir / "codeweaver.toml")
    assert cfg.name == "crust__bitset"
    assert cfg.source_language == "C"
    assert cfg.target_language == "Rust"
    assert cfg.source_dir == "source"
    assert cfg.reference_dirs == ["oracle"]
    assert cfg.immutable_input == "scaffold"
    assert cfg.working_copy == "pipeline/target"
    assert cfg.build_check_cmd == "cd pipeline/target && cargo build"
    assert cfg.unit_test_cmd == "cd pipeline/target && cargo test"
    assert cfg.model.default == "claude-opus-4.8"
    assert cfg.max_iter == 5
    assert cfg.parity_check is True
    assert cfg.agent_timeout == 5000
    assert cfg.auto_milestones is True  # no [[milestones]] declared
    assert "translate" in cfg.brief.lower() or "recodeagent" in cfg.brief.lower()


def test_generated_config_without_oracle_or_scaffold_still_loads(tmp_path: Path, artifact_root: Path):
    result = P.prepare_project(_skel_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                               dataset_spec=SKEL_SPEC, protocol=PROTOCOL)
    cfg = cw_config.load(result.prepared_dir / "codeweaver.toml")
    assert cfg.reference_dirs == []
    assert cfg.immutable_input == ""


def test_generated_config_build_cmd_round_trips_exactly_for_alphatrans_payload():
    """Regression for review finding #1: generate_codeweaver_toml() used to
    flatten build_cmd/unit_test_cmd/validate_cmd argv arrays with a plain
    ``" ".join(...)``, corrupting any element containing shell metacharacters.
    AlphaTrans's REAL build_cmd (see experiment.toml) is exactly this kind of
    payload -- a ``python -c "..."`` argument containing spaces, semicolons,
    parens, and a single-quoted string literal. ``shlex.join()`` must
    serialize it so ``shlex.split()`` (simulating the POSIX shell that "runs"
    this documented shell-command-string field -- see codeweaver/config.py's
    ``build_check_cmd``/``unit_test_cmd``/``validate_cmd`` docs) parses it
    back into the EXACT original argv, never a corrupted/re-split command."""
    import shlex
    import tomllib

    alphatrans_build_cmd = [
        "python", "-c",
        "import compileall,sys; sys.exit(0 if compileall.compile_dir('.', quiet=1) else 1)",
    ]
    alphatrans_spec = {
        "label": "AlphaTrans", "source_language": "Java", "target_language": "Python",
        "build_cmd": alphatrans_build_cmd,
        "unit_test_cmd": ["python", "-m", "unittest", "discover"],
        "validate_cmd": ["python", "-m", "unittest", "discover"],
        "gate_template": '-k "{tests_or}"',
    }
    row = {
        "id": "alphatrans__cli", "tool": "alphatrans", "project": "cli",
        "source_language": "Java", "target_language": "Python",
    }
    config_text = P.generate_codeweaver_toml(row, alphatrans_spec, PROTOCOL, has_oracle=False, has_scaffold=False)
    parsed = tomllib.loads(config_text)  # the config must still be syntactically valid TOML
    build_check_str = parsed["commands"]["build_check"]

    # The core regression check: splitting the serialized shell-command
    # string back into argv (as the documented "shell, run by the agents"
    # consumer would) must reproduce the EXACT original argv, not a mangled
    # or differently-split-apart command.
    prefix, serialized_argv = build_check_str.split(" && ", 1)
    assert prefix == "cd pipeline/target"
    assert shlex.split(serialized_argv) == [sys.executable, *alphatrans_build_cmd[1:]]

    # Prove the pre-fix behavior really would have failed this same check --
    # otherwise this wouldn't be a meaningful regression guard.
    naive_join = " ".join(alphatrans_build_cmd)
    assert shlex.split(naive_join) != alphatrans_build_cmd


def test_generated_config_build_cmd_round_trips_via_real_codeweaver_config_loader(
    tmp_path: Path, artifact_root: Path,
):
    """Same round-trip guarantee, but validated end-to-end through the REAL
    codeweaver.config loader (like the other "generated config is valid"
    tests above), for an AlphaTrans-shaped project prepared on disk."""
    import shlex

    alphatrans_build_cmd = [
        "python", "-c",
        "import compileall,sys; sys.exit(0 if compileall.compile_dir('.', quiet=1) else 1)",
    ]
    alphatrans_spec = {
        "label": "AlphaTrans", "source_language": "Java", "target_language": "Python",
        "build_cmd": alphatrans_build_cmd,
        "unit_test_cmd": ["python", "-m", "unittest", "discover"],
        "validate_cmd": ["python", "-m", "unittest", "discover"],
        "gate_template": '-k "{tests_or}"',
    }
    row = _skel_row()
    row.update({"id": "alphatrans__leftpad", "tool": "alphatrans"})
    result = P.prepare_project(row, artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                               dataset_spec=alphatrans_spec, protocol=PROTOCOL)
    cfg = cw_config.load(result.prepared_dir / "codeweaver.toml")
    prefix, serialized_argv = cfg.build_check_cmd.split(" && ", 1)
    assert prefix == "cd pipeline/target"
    assert shlex.split(serialized_argv) == [sys.executable, *alphatrans_build_cmd[1:]]


# --------------------------------------------------------------------------- #
# Idempotency / force
# --------------------------------------------------------------------------- #
def test_prepare_project_is_idempotent_by_default(tmp_path: Path, artifact_root: Path):
    workspace_root = tmp_path / "ws"
    P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=workspace_root,
                      dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    sentinel = workspace_root / "crust__bitset" / "source" / "sentinel.txt"
    sentinel.write_text("stray edit that should survive a no-op re-prepare", encoding="utf-8")

    P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=workspace_root,
                      dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    assert sentinel.exists()  # not wiped: second call was a no-op (already prepared)


def test_prepare_project_force_rebuilds_from_scratch(tmp_path: Path, artifact_root: Path):
    workspace_root = tmp_path / "ws"
    P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=workspace_root,
                      dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    sentinel = workspace_root / "crust__bitset" / "source" / "sentinel.txt"
    sentinel.write_text("stray edit that should be wiped by --force", encoding="utf-8")

    P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=workspace_root,
                      dataset_spec=CRUST_SPEC, protocol=PROTOCOL, force=True)
    assert not sentinel.exists()


def test_prepare_project_missing_source_raises(tmp_path: Path, artifact_root: Path):
    row = _crust_row()
    row["source_rel_path"] = str(Path("bitset") / "does_not_exist")
    with pytest.raises(FileNotFoundError):
        P.prepare_project(row, artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                          dataset_spec=CRUST_SPEC, protocol=PROTOCOL)


# --------------------------------------------------------------------------- #
# prepare_all: filtering
# --------------------------------------------------------------------------- #
def test_prepare_all_filters_by_tool_and_project_id(tmp_path: Path, artifact_root: Path):
    manifest = {"projects": [_crust_row(), _skel_row()]}
    cfg = {"datasets": {"crust": CRUST_SPEC, "skel": SKEL_SPEC}, "protocol": PROTOCOL}

    only_skel = P.prepare_all(manifest, artifact_root=artifact_root, workspace_root=tmp_path / "ws1",
                              cfg=cfg, tools={"skel"})
    assert [p.project_id for p in only_skel] == ["skel__leftpad"]

    only_bitset = P.prepare_all(manifest, artifact_root=artifact_root, workspace_root=tmp_path / "ws2",
                                cfg=cfg, project_ids={"crust__bitset"})
    assert [p.project_id for p in only_bitset] == ["crust__bitset"]

    both = P.prepare_all(manifest, artifact_root=artifact_root, workspace_root=tmp_path / "ws3", cfg=cfg)
    assert {p.project_id for p in both} == {"crust__bitset", "skel__leftpad"}


# --------------------------------------------------------------------------- #
# Run materialization
# --------------------------------------------------------------------------- #
def test_materialize_run_creates_isolated_copy_excluding_marker_and_pipeline(tmp_path: Path, artifact_root: Path):
    prepared = P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                                 dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    (prepared.prepared_dir / "pipeline").mkdir()
    (prepared.prepared_dir / "pipeline" / "burr.db").write_text("stale state from a previous prepare", encoding="utf-8")

    run_dir = tmp_path / "runs" / "full" / "crust__bitset" / "rep0"
    out = P.materialize_run(prepared.prepared_dir, run_dir)
    assert out == run_dir
    assert (run_dir / "source" / "main.c").exists()
    assert (run_dir / "codeweaver.toml").exists()
    assert not (run_dir / "pipeline").exists()          # fresh run must start with no stale pipeline state
    assert not (run_dir / P.TEMPLATE_MARKER).exists()   # internal prepare.py bookkeeping stays out of the run dir


def test_materialize_run_is_idempotent_by_default(tmp_path: Path, artifact_root: Path):
    prepared = P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                                 dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    run_dir = tmp_path / "run"
    P.materialize_run(prepared.prepared_dir, run_dir)
    (run_dir / "pipeline").mkdir()
    (run_dir / "pipeline" / "burr.db").write_text("in-progress run state", encoding="utf-8")

    P.materialize_run(prepared.prepared_dir, run_dir)  # must NOT wipe in-progress state
    assert (run_dir / "pipeline" / "burr.db").exists()


def test_materialize_run_force_wipes_existing_run_dir(tmp_path: Path, artifact_root: Path):
    prepared = P.prepare_project(_crust_row(), artifact_root=artifact_root, workspace_root=tmp_path / "ws",
                                 dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    run_dir = tmp_path / "run"
    P.materialize_run(prepared.prepared_dir, run_dir)
    (run_dir / "pipeline").mkdir()
    (run_dir / "pipeline" / "burr.db").write_text("in-progress run state", encoding="utf-8")

    P.materialize_run(prepared.prepared_dir, run_dir, force=True)
    assert not (run_dir / "pipeline").exists()


def test_materialize_run_requires_a_prepared_workspace(tmp_path: Path):
    not_prepared = tmp_path / "random_dir"
    not_prepared.mkdir()
    with pytest.raises(FileNotFoundError):
        P.materialize_run(not_prepared, tmp_path / "run")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_main_prepares_all_projects_from_manifest(tmp_path: Path, artifact_root: Path, capsys):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"projects": [_crust_row(), _skel_row()]}), encoding="utf-8")

    # Build a minimal, self-contained experiment.toml-equivalent config on disk
    # so the CLI test does not depend on the bundled experiment.toml's dataset
    # definitions (which use real cargo/npm commands, irrelevant here).
    import tomllib
    cfg_path = tmp_path / "mini_experiment.toml"
    cfg_path.write_text(
        "[protocol]\nmodel = \"claude-opus-4.8\"\neffort_default = \"high\"\n"
        "max_iter = 5\nmax_parity_rounds = 3\nagent_timeout_seconds = 5000\n\n"
        "[datasets.crust]\nlabel = \"CRUST\"\nsource_language = \"C\"\ntarget_language = \"Rust\"\n"
        "build_cmd = [\"cargo\", \"build\"]\nunit_test_cmd = [\"cargo\", \"test\"]\n"
        "validate_cmd = [\"cargo\", \"test\"]\ngate_template = \"{tests_or}\"\n\n"
        "[datasets.skel]\nlabel = \"SKEL\"\nsource_language = \"Python\"\ntarget_language = \"JavaScript\"\n"
        "build_cmd = [\"npm\", \"install\"]\nunit_test_cmd = [\"npm\", \"test\"]\n"
        "validate_cmd = [\"npm\", \"test\"]\ngate_template = \"{tests_or}\"\n",
        encoding="utf-8",
    )
    with open(cfg_path, "rb") as f:
        tomllib.load(f)  # sanity: the hand-written fixture toml itself parses

    workspace_root = tmp_path / "workspaces"
    rc = P.main([
        "--manifest", str(manifest_path), "--artifact-root", str(artifact_root),
        "--workspace-root", str(workspace_root), "--config", str(cfg_path),
    ])
    assert rc == 0
    assert (workspace_root / "crust__bitset" / "codeweaver.toml").exists()
    assert (workspace_root / "skel__leftpad" / "codeweaver.toml").exists()
    out = capsys.readouterr().out
    assert "prepared 2 project workspace(s)" in out
