"""Leakage-safe preparation of the 23 Rustine comparison workspaces."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

from experiments.rustine import common as C
from experiments.rustine.config import load_subject_config

PREPARED_MARKER = ".recodeagent_prepared.json"
PREPARATION_SCHEMA = 2
TRANSLATION_JSON = "translation.json"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _find_assignment_lines(text: str, table: str) -> dict[str, str]:
    lines = text.splitlines()
    in_table = False
    result: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_table = stripped == f"[{table}]"
            continue
        if in_table and "=" in line and not stripped.startswith("#"):
            key = line.split("=", 1)[0].strip()
            if re.fullmatch(r"[A-Za-z0-9_-]+", key):
                result[key] = line.strip()
    return result


def _insert_table_assignments(text: str, table: str, assignments: list[str]) -> str:
    if not assignments:
        return text if text.endswith("\n") else text + "\n"
    lines = text.splitlines()
    header = f"[{table}]"
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == header)
    except StopIteration:
        lines.extend(["", header, *assignments])
        return "\n".join(lines).rstrip() + "\n"
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("["):
            end = index
            break
    existing = {
        line.split("=", 1)[0].strip()
        for line in lines[start + 1 : end]
        if "=" in line and not line.lstrip().startswith("#")
    }
    additions = [line for line in assignments if line.split("=", 1)[0].strip() not in existing]
    lines[end:end] = additions
    return "\n".join(lines).rstrip() + "\n"


def _cargo_bins(cargo: dict[str, Any]) -> list[dict[str, str]]:
    bins = cargo.get("bin") or []
    result = []
    for entry in bins:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str) and isinstance(
            entry.get("path"), str
        ):
            result.append({"name": entry["name"], "path": entry["path"]})
    return result


def _append_missing_bins(
    cargo_text: str, skeleton_cargo: dict[str, Any], translate_cargo: dict[str, Any], targets: list[str]
) -> str:
    existing = {entry["name"]: entry for entry in _cargo_bins(skeleton_cargo)}
    translated = {entry["name"]: entry for entry in _cargo_bins(translate_cargo)}
    additions: list[dict[str, str]] = []
    for target in targets:
        candidate = existing.get(target) or translated.get(target)
        if candidate is None:
            raise ValueError(f"contract target {target!r} is absent from both Cargo manifests")
        if target not in existing:
            additions.append(candidate)
    text = cargo_text.rstrip() + "\n"
    for entry in additions:
        text += (
            "\n[[bin]]\n"
            f"name = {_toml_string(entry['name'])}\n"
            f"path = {_toml_string(entry['path'])}\n"
        )
    return text


def _rewrite_crate_name(text: str, translate_name: str, skeleton_name: str) -> str:
    source_ident = translate_name.replace("-", "_")
    target_ident = skeleton_name.replace("-", "_")
    text = re.sub(rf"\b{re.escape(source_ident)}\b", target_ident, text)
    return re.sub(
        r"\btranslate(?:_[A-Za-z0-9_]+)?\b(?=\s*::)",
        target_ident,
        text,
    )


def _contract_modules(translate_lib: Path, contract_files: list[str]) -> list[str]:
    if not translate_lib.exists():
        return []
    allowed = {
        Path(path).stem
        for path in contract_files
        if path.startswith("src/") and not Path(path).stem.endswith("_main")
    }
    text = translate_lib.read_text(encoding="utf-8", errors="replace")
    declared = re.findall(r"(?m)^\s*pub\s+mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", text)
    return [module for module in declared if module in allowed]


def _ensure_modules(lib_path: Path, modules: list[str]) -> None:
    if not modules:
        return
    text = lib_path.read_text(encoding="utf-8", errors="replace") if lib_path.exists() else ""
    additions = []
    for module in modules:
        if not re.search(rf"(?m)^\s*(?:pub\s+)?mod\s+{re.escape(module)}\s*;", text):
            additions.extend([f"pub mod {module};", f"pub use {module}::*;", ""])
    if additions:
        lib_path.parent.mkdir(parents=True, exist_ok=True)
        lib_path.write_text(text.rstrip() + "\n\n" + "\n".join(additions), encoding="utf-8")


def _canonical_cargo(
    skeleton_path: Path, translate_path: Path, contract: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    skeleton_text = skeleton_path.read_text(encoding="utf-8")
    translate_text = translate_path.read_text(encoding="utf-8")
    skeleton = tomllib.loads(skeleton_text)
    translated = tomllib.loads(translate_text)
    translated_dependencies = _find_assignment_lines(translate_text, "dependencies")
    dependency_lines = []
    for dependency in contract["test_dependencies"]:
        if dependency not in translated_dependencies:
            raise ValueError(f"test dependency {dependency!r} is absent from translation Cargo.toml")
        dependency_lines.append(translated_dependencies[dependency])
    cargo_text = _insert_table_assignments(skeleton_text, "dependencies", dependency_lines)
    cargo_text = _append_missing_bins(cargo_text, skeleton, translated, contract["targets"])
    parsed = tomllib.loads(cargo_text)
    return cargo_text, {
        "package": {
            key: parsed["package"][key]
            for key in ("name", "version", "edition")
            if key in parsed.get("package", {})
        },
        "dependencies": _find_assignment_lines(cargo_text, "dependencies"),
        "build_dependencies": _find_assignment_lines(cargo_text, "build-dependencies"),
        "bins": _cargo_bins(parsed),
        "lib": {
            "name": parsed["package"]["name"].replace("-", "_"),
            "path": "src/lib.rs",
        },
        "allow_build_script": (skeleton_path.parent / "build.rs").is_file(),
    }


def generate_brief(subject: dict[str, Any]) -> str:
    return f"""# Rustine same-subject comparison: {subject['name']}

Translate the disclosed pre-refactoring C under `source/` into Rust using the
immutable generated package topology under `scaffold/`. This is subject
{subject['id']} of 23 from Rustine, *Translating Large-Scale C Repositories to
Idiomatic Rust* (arXiv:2511.20617v1).

## Scientific integrity constraints

- Never edit or weaken `oracle/`, `scaffold/`, `immutable_evaluator.py`, Cargo
  targets, test drivers, or module wiring to gain credit.
- Implement production behavior in `pipeline/target`; do not replace fixed
  tests with generated success output or bypass assertions.
- The Rustine production translation is intentionally unavailable. Only the
  disclosed C preprocessing output, generated skeleton, and fixed test
  contract are present.
- Compilation is independently checked with `cargo build --all-targets`.
- Validation uses a temporary copy with pristine contract files and Cargo
  wiring restored before execution.
- Paper-comparable coverage includes only the production module graph and
  immutable Rust contract files; production-only coverage is retained
  separately in the raw evaluation.

Benchmark context: https://arxiv.org/abs/2511.20617
"""


def generate_codeweaver_toml(subject: dict[str, Any], protocol: dict[str, Any]) -> str:
    python = shlex.quote(sys.executable)
    build_command = (
        f"{python} immutable_evaluator.py --stage build --target pipeline/target "
        "--contract oracle --result pipeline/immutable-build.json"
    )
    test_command = (
        f"{python} immutable_evaluator.py --stage test --target pipeline/target "
        "--contract oracle --result pipeline/immutable-test.json"
    )
    return f"""# Generated by experiments/rustine/prepare.py. Do not edit.
[project]
name = {_toml_string(f"Rustine {subject['id']}: {subject['name']}")}
slug = {_toml_string(f"rustine-{subject['id']:02d}-{subject['name']}")}
description = {_toml_string("Same-subject CodeWeaver comparison against Rustine.")}

[translation]
source_language = "C"
target_language = "Rust"
brief_file = "brief.md"

[paths]
source_dir = "source"
reference_dirs = ["oracle"]
immutable_input = "scaffold"
working_copy = "pipeline/target"
pipeline_dir = "pipeline"

[commands]
build_check = {_toml_string(build_command)}
unit_test = {_toml_string(test_command)}
validate = {_toml_string(test_command)}

[validation]
gate_template = "{{tests_space}}"

[model]
default = {_toml_string(protocol["model"])}
effort_default = {_toml_string(protocol["effort"])}

[execution]
max_iter = {protocol["max_iter"]}
parity_check = true
max_parity_rounds = {protocol["max_parity_rounds"]}
agent_timeout = {protocol["agent_timeout_seconds"]}
"""


def _copy_contract_file(
    source: Path,
    scaffold_destination: Path,
    oracle_destination: Path,
    *,
    translate_name: str,
    skeleton_name: str,
) -> None:
    if source.name == TRANSLATION_JSON or source.suffix != ".rs":
        raise ValueError(f"non-Rust production file cannot be copied as a test module: {source}")
    text = source.read_text(encoding="utf-8", errors="strict")
    text = _rewrite_crate_name(text, translate_name, skeleton_name)
    for destination in (scaffold_destination, oracle_destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")


def _download_external_asset(asset: dict[str, str]) -> bytes:
    try:
        with urllib.request.urlopen(asset["url"], timeout=60) as response:
            payload = response.read()
    except OSError as exc:
        raise RuntimeError(
            f"could not download pinned external asset {asset['path']}: {exc}"
        ) from exc
    actual = hashlib.sha256(payload).hexdigest()
    if actual != asset["sha256"]:
        raise ValueError(
            f"external asset hash mismatch for {asset['path']}: "
            f"expected {asset['sha256']}, found {actual}"
        )
    return payload


def _preparation_spec_sha256(
    subject: dict[str, Any], protocol: dict[str, Any]
) -> str:
    payload = json.dumps(
        {"subject": subject, "protocol": protocol},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reuse_prepared_workspace(
    prepared: Path, subject: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, Any]:
    marker_path = prepared / PREPARED_MARKER
    if not marker_path.is_file():
        raise FileExistsError(f"refusing to overwrite unmarked workspace: {prepared}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    expected = {
        "preparation_schema": PREPARATION_SCHEMA,
        "subject_id": subject["id"],
        "spec_sha256": _preparation_spec_sha256(subject, protocol),
        "contract_sha256": C.tree_sha256(prepared / "oracle"),
        "evaluator_sha256": C.file_sha256(prepared / "immutable_evaluator.py"),
        "source_sha256": C.tree_sha256(prepared / "source"),
        "scaffold_sha256": C.tree_sha256(prepared / "scaffold"),
        "config_sha256": C.file_sha256(prepared / "codeweaver.toml"),
        "brief_sha256": C.file_sha256(prepared / "brief.md"),
    }
    mismatches = [
        key for key, value in expected.items() if marker.get(key) != value
    ]
    current_evaluator = C.file_sha256(Path(__file__).with_name("evaluator.py"))
    if marker.get("evaluator_sha256") != current_evaluator:
        mismatches.append("current_evaluator_sha256")
    if mismatches:
        raise ValueError(
            f"prepared workspace integrity check failed for subject {subject['id']}: "
            f"{sorted(set(mismatches))}; rerun with --force"
        )
    return marker


def _assert_no_solution_leakage(
    translate_dir: Path, scaffold: Path, skeleton_dir: Path, allowed_relpaths: set[str]
) -> None:
    if (scaffold / TRANSLATION_JSON).exists() or any(
        path.name == TRANSLATION_JSON for path in scaffold.rglob("*")
    ):
        raise RuntimeError("translation.json leaked into the prepared scaffold")
    skeleton_files = {
        path.relative_to(skeleton_dir).as_posix()
        for path in skeleton_dir.rglob("*")
        if path.is_file()
    }
    prepared_files = {
        path.relative_to(scaffold).as_posix() for path in scaffold.rglob("*") if path.is_file()
    }
    permitted_changes = allowed_relpaths | {"Cargo.toml", "src/lib.rs"}
    unexpected = prepared_files - skeleton_files - permitted_changes
    if unexpected:
        raise RuntimeError(f"unexpected non-contract files copied from translate/: {sorted(unexpected)}")
    translated_rs = {
        path.relative_to(translate_dir).as_posix()
        for path in translate_dir.rglob("*.rs")
        if path.is_file()
    }
    leaked = (prepared_files & translated_rs) - skeleton_files - allowed_relpaths
    if leaked:
        raise RuntimeError(f"Rustine production implementation leaked: {sorted(leaked)}")


def prepare_subject(
    subject: dict[str, Any],
    *,
    artifact_root: Path,
    workspace_root: Path,
    protocol: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    artifact_subject = artifact_root / "artifacts" / subject["artifact_dir"]
    preprocess = artifact_subject / "preprocess"
    skeleton = artifact_subject / "skeleton"
    contract_stage = next(
        (
            stage
            for stage in ("manual_debug", "automatic_debug", "translate")
            if (artifact_subject / stage / "Cargo.toml").is_file()
        ),
        "translate",
    )
    contract_source = artifact_subject / contract_stage
    for required in (preprocess, skeleton, contract_source):
        if not required.is_dir():
            raise FileNotFoundError(f"subject {subject['id']} missing artifact directory: {required}")
    for forbidden in (preprocess / TRANSLATION_JSON, skeleton / TRANSLATION_JSON):
        if forbidden.exists():
            raise RuntimeError(f"unexpected solution metadata in disclosed input: {forbidden}")

    prepared = workspace_root / str(subject["id"])
    if prepared.exists():
        if not force:
            return _reuse_prepared_workspace(prepared, subject, protocol)
        shutil.rmtree(prepared)
    prepared.mkdir(parents=True)
    shutil.copytree(preprocess, prepared / "source")
    shutil.copytree(skeleton, prepared / "scaffold")
    oracle = prepared / "oracle"
    oracle.mkdir()

    skeleton_cargo_path = skeleton / "Cargo.toml"
    translate_cargo_path = contract_source / "Cargo.toml"
    canonical_cargo, cargo_requirements = _canonical_cargo(
        skeleton_cargo_path, translate_cargo_path, subject["contract"]
    )
    (prepared / "scaffold" / "Cargo.toml").write_text(canonical_cargo, encoding="utf-8")

    skeleton_cargo = tomllib.loads(skeleton_cargo_path.read_text(encoding="utf-8"))
    translate_cargo = tomllib.loads(translate_cargo_path.read_text(encoding="utf-8"))
    skeleton_name = skeleton_cargo["package"]["name"]
    translate_name = translate_cargo["package"]["name"]
    copied: list[str] = []
    for rel in subject["contract"]["files"]:
        source = contract_source / Path(rel)
        if not source.is_file():
            raise FileNotFoundError(f"declared contract file missing: {source}")
        _copy_contract_file(
            source,
            prepared / "scaffold" / Path(rel),
            oracle / Path(rel),
            translate_name=translate_name,
            skeleton_name=skeleton_name,
        )
        copied.append(rel)
    for rel in subject["contract"]["assets"]:
        source = contract_source / Path(rel)
        if not source.is_file():
            raise FileNotFoundError(f"declared contract asset missing: {source}")
        for destination in (prepared / "scaffold" / Path(rel), oracle / Path(rel)):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        copied.append(rel)
    external_assets = subject["contract"].get("external_assets", [])
    for asset in external_assets:
        payload = _download_external_asset(asset)
        rel = asset["path"]
        for destination in (prepared / "scaffold" / Path(rel), oracle / Path(rel)):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        copied.append(rel)
    support_files = [
        rel for rel in ("build.rs", "wrapper.h") if (skeleton / rel).is_file()
    ]
    for rel in support_files:
        destination = oracle / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skeleton / rel, destination)
        copied.append(rel)

    modules = _contract_modules(
        contract_source / "src" / "lib.rs", subject["contract"]["files"]
    )
    _ensure_modules(prepared / "scaffold" / "src" / "lib.rs", modules)
    _assert_no_solution_leakage(
        contract_source, prepared / "scaffold", skeleton, set(copied)
    )

    file_hashes = {
        rel: C.file_sha256(oracle / Path(rel))
        for rel in copied
    }
    contract_lock = {
        "schema_version": 1,
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "contract_stage": contract_stage,
        "kind": subject["contract"]["kind"],
        "files": list(subject["contract"]["files"]),
        "assets": list(subject["contract"]["assets"])
        + [asset["path"] for asset in external_assets],
        "external_assets": external_assets,
        "support_files": support_files,
        "targets": list(subject["contract"]["targets"]),
        "executions": subject["contract"].get("executions"),
        "assertion_credit": subject["contract"]["assertion_credit"],
        "success_regex": subject["contract"].get("success_regex"),
        "failure_regex": subject["contract"].get("failure_regex"),
        "paper_assertions": subject["paper_validation"]["assertions_executed"],
        "file_sha256": file_hashes,
        "cargo": cargo_requirements,
        "tools": {
            "cargo_llvm_cov_version": protocol["cargo_llvm_cov_version"],
            "cargo_newmetrics_sha256": protocol["cargo_newmetrics_sha256"],
        },
        "modules": modules,
    }
    C.atomic_write_json(oracle / "contract.json", contract_lock)
    shutil.copy2(Path(__file__).with_name("evaluator.py"), prepared / "immutable_evaluator.py")
    C.atomic_write_text(prepared / "brief.md", generate_brief(subject))
    C.atomic_write_text(
        prepared / "codeweaver.toml", generate_codeweaver_toml(subject, protocol)
    )

    marker = {
        "preparation_schema": PREPARATION_SCHEMA,
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "contract_stage": contract_stage,
        "prepared_dir": str(prepared),
        "contract_sha256": C.tree_sha256(oracle),
        "evaluator_sha256": C.file_sha256(prepared / "immutable_evaluator.py"),
        "source_sha256": C.tree_sha256(prepared / "source"),
        "scaffold_sha256": C.tree_sha256(prepared / "scaffold"),
        "config_sha256": C.file_sha256(prepared / "codeweaver.toml"),
        "brief_sha256": C.file_sha256(prepared / "brief.md"),
        "spec_sha256": _preparation_spec_sha256(subject, protocol),
        "ground_truth_excluded": True,
        "prepared_at": C.utcnow_iso(),
    }
    C.atomic_write_json(prepared / PREPARED_MARKER, marker)
    return marker


def verify_artifact_root(artifact_root: Path, expected_commit: str) -> dict[str, Any]:
    artifacts = artifact_root / "artifacts"
    if not artifacts.is_dir():
        raise FileNotFoundError(f"Rustine artifact root has no artifacts/ directory: {artifact_root}")
    result = subprocess.run(
        ["git", "-C", str(artifact_root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    commit = result.stdout.strip() if result.returncode == 0 else None
    if commit is None:
        raise ValueError(
            f"cannot verify Rustine artifact commit at {artifact_root}: "
            f"{result.stderr.strip() or 'git rev-parse failed'}"
        )
    if commit != expected_commit:
        raise ValueError(f"artifact commit mismatch: expected {expected_commit}, found {commit}")
    status = subprocess.run(
        [
            "git",
            "-C",
            str(artifact_root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    if status.returncode != 0:
        raise ValueError(
            f"cannot verify Rustine artifact cleanliness: "
            f"{status.stderr.strip() or 'git status failed'}"
        )
    if status.stdout.strip():
        changed = status.stdout.strip().splitlines()
        raise ValueError(
            "Rustine artifact checkout is dirty; preparation requires the exact pinned "
            f"tree (first entries: {changed[:5]})"
        )
    untracked = subprocess.run(
        [
            "git",
            "-C",
            str(artifact_root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "artifacts",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    if untracked.returncode != 0:
        raise ValueError(
            f"cannot verify untracked Rustine artifact inputs: "
            f"{untracked.stderr.strip() or 'git ls-files failed'}"
        )
    if untracked.stdout.strip():
        changed = untracked.stdout.strip().splitlines()
        raise ValueError(
            "Rustine artifacts/ contains untracked inputs; preparation requires the exact "
            f"pinned tree (first entries: {changed[:5]})"
        )
    return {"commit": commit, "commit_verified": True, "worktree_clean": True}


def prepare_all(
    *,
    artifact_root: Path,
    workspace_root: Path,
    config: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    workspace_root = workspace_root.resolve()
    verification = verify_artifact_root(artifact_root, config["artifact"]["commit"])
    workspace_root.mkdir(parents=True, exist_ok=True)
    rows = []
    markers = []
    for subject in config["subjects"]:
        marker = prepare_subject(
            subject,
            artifact_root=artifact_root,
            workspace_root=workspace_root,
            protocol=config["protocol"],
            force=force,
        )
        markers.append(marker)
        rows.append(
            {
                "id": str(subject["id"]),
                "subject_id": subject["id"],
                "tool": "rustine",
                "project": subject["name"],
                "source_language": "C",
                "target_language": "Rust",
                "source_rel_path": f"artifacts/{subject['artifact_dir']}/preprocess",
                "oracle_rel_path": None,
                "scaffold_rel_path": f"artifacts/{subject['artifact_dir']}/skeleton",
                "ground_truth_target_rel_path": None,
                "loc_source": subject["loc"],
                "status": "ok",
                "contract_sha256": marker["contract_sha256"],
                "evaluator_sha256": marker["evaluator_sha256"],
            }
        )
    manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "artifact_root": str(artifact_root),
        "artifact": {**config["artifact"], **verification},
        "protocol": config["protocol"],
        "counts": {"rustine": len(rows), "total": len(rows)},
        "expected_counts": {"rustine": 23, "total": 23},
        "counts_match_expected": len(rows) == 23,
        "projects": rows,
        "preparation": markers,
        "provenance": C.collect_provenance(artifact_root=artifact_root),
    }
    C.atomic_write_json(workspace_root / "manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--config", default=str(C.DEFAULT_CONFIG))
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_subject_config(args.config)
    manifest = prepare_all(
        artifact_root=Path(args.artifact_root),
        workspace_root=Path(args.workspace_root),
        config=config,
        force=args.force,
    )
    print(
        f"prepared {manifest['counts']['total']} Rustine subjects; "
        f"manifest={Path(args.workspace_root).resolve() / 'manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
