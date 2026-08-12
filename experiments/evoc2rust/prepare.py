"""Prepare leakage-safe Vivo-Bench workspaces and immutable test contracts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from experiments.evoc2rust import common as C
from experiments.evoc2rust.config import load_config
from experiments.evoc2rust.evaluator import evaluate_stage

PREPARATION_SCHEMA = 1
PREPARED_MARKER = "prepared.json"
PRIMARY_REL_PATH = Path("01-BlueOS2_Translation/Input/01-Primary")
RUST_PREAMBLE = """#![allow(dead_code)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(non_upper_case_globals)]
#![allow(unused_assignments)]
#![allow(unused_mut)]
#![feature(extern_types)]
#![feature(label_break_value)]
#![feature(raw_ref_op)]
"""


def rust_module_name(module: str) -> str:
    return module.replace("-", "_")


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 1200,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        diagnostic = (result.stdout + "\n" + result.stderr)[-20_000:]
        raise RuntimeError(
            f"command failed ({result.returncode}): {shlex.join(argv)}\n{diagnostic}"
        )
    return result


def verify_artifact_root(
    artifact_root: Path, expected_commit: str
) -> dict[str, Any]:
    if not (artifact_root / PRIMARY_REL_PATH).is_dir():
        raise FileNotFoundError(
            f"Vivo-Bench primary input is absent under {artifact_root}"
        )
    commit = _run(
        ["git", "-C", str(artifact_root), "rev-parse", "HEAD"],
        timeout=20,
    ).stdout.strip()
    if commit != expected_commit:
        raise ValueError(
            f"artifact commit mismatch: expected {expected_commit}, found {commit}"
        )
    status = _run(
        [
            "git",
            "-C",
            str(artifact_root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        timeout=180,
    ).stdout.strip()
    if status:
        raise ValueError("Vivo-Bench checkout must be clean before preparation")
    return {"commit": commit, "commit_verified": True, "worktree_clean": True}


def verify_c2rust(c2rust_binary: Path, tools: dict[str, str]) -> dict[str, Any]:
    if not c2rust_binary.is_file():
        raise FileNotFoundError(c2rust_binary)
    actual_hash = C.file_sha256(c2rust_binary)
    if actual_hash != tools["c2rust_sha256"]:
        raise ValueError(
            "C2Rust binary hash mismatch: "
            f"expected {tools['c2rust_sha256']}, found {actual_hash}"
        )
    version = _run([str(c2rust_binary), "--version"], timeout=30).stdout.strip()
    if tools["c2rust_version"] not in version:
        raise ValueError(f"unexpected C2Rust version: {version}")
    return {
        "path": str(c2rust_binary),
        "version": version,
        "sha256": actual_hash,
    }


def _mask_non_code(text: str) -> str:
    chars = list(text)
    index = 0
    block_depth = 0
    mode = "code"
    while index < len(chars):
        current = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if mode == "code":
            if current == "/" and following == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                mode = "line_comment"
                continue
            if current == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                index += 2
                block_depth = 1
                mode = "block_comment"
                continue
            if current == '"':
                chars[index] = " "
                index += 1
                mode = "string"
                continue
            if current == "'":
                chars[index] = " "
                index += 1
                mode = "character"
                continue
        elif mode == "line_comment":
            if current == "\n":
                mode = "code"
            else:
                chars[index] = " "
            index += 1
            continue
        elif mode == "block_comment":
            if current == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                block_depth += 1
                index += 2
                continue
            if current == "*" and following == "/":
                chars[index] = chars[index + 1] = " "
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    mode = "code"
                continue
            if current != "\n":
                chars[index] = " "
            index += 1
            continue
        elif mode in {"string", "character"}:
            closing = '"' if mode == "string" else "'"
            if current == "\\" and following:
                chars[index] = chars[index + 1] = " "
                index += 2
                continue
            if current == closing:
                chars[index] = " "
                mode = "code"
            elif current != "\n":
                chars[index] = " "
            index += 1
            continue
        index += 1
    return "".join(chars)


def function_body_spans(text: str) -> list[tuple[int, int]]:
    masked = _mask_non_code(text)
    spans: list[tuple[int, int]] = []
    position = 0
    while True:
        match = re.search(r"\bfn\b", masked[position:])
        if match is None:
            break
        fn_start = position + match.start()
        cursor = position + match.end()
        opening = None
        while cursor < len(masked):
            if masked[cursor] == ";":
                break
            if masked[cursor] == "{":
                opening = cursor
                break
            cursor += 1
        if opening is None:
            position = max(cursor + 1, fn_start + 2)
            continue
        depth = 1
        cursor = opening + 1
        while cursor < len(masked) and depth:
            if masked[cursor] == "{":
                depth += 1
            elif masked[cursor] == "}":
                depth -= 1
            cursor += 1
        if depth:
            raise ValueError("unbalanced Rust function body")
        spans.append((opening, cursor - 1))
        position = cursor
    return spans


def strip_function_bodies(text: str) -> tuple[str, int]:
    spans = function_body_spans(text)
    if not spans:
        raise ValueError("generated production module contains no functions")
    replacement = (
        "{\n"
        '    unimplemented!("CodeWeaver must implement this function")\n'
        "}"
    )
    output = text
    for opening, closing in reversed(spans):
        output = output[:opening] + replacement + output[closing + 1 :]
    if len(function_body_spans(output)) != len(spans):
        raise ValueError("function count changed while stripping production bodies")
    for opening, closing in function_body_spans(output):
        if "unimplemented!" not in output[opening : closing + 1]:
            raise ValueError("a production function body was not stripped")
    return output, len(spans)


def _generate_lib(modules: list[str], *, include_oracle: bool = False) -> str:
    lines = [RUST_PREAMBLE.rstrip(), "", "pub mod production {"]
    lines.extend(f"    pub mod {rust_module_name(module)};" for module in modules)
    lines.append("}")
    if include_oracle:
        lines.extend(
            [
                "",
                "pub mod oracle {",
                "    pub mod alloc_testing;",
                "    pub mod framework;",
                "    pub mod fixed_test;",
                "}",
            ]
        )
    return "\n".join(lines) + "\n"


def _generate_cargo(subject: dict[str, Any]) -> str:
    crate = f"vivo_subject_{subject['id']:02d}"
    return f"""[package]
name = "{crate}"
version = "0.1.0"
edition = "2021"
publish = false
autobins = false

[lib]
name = "{crate}"
path = "src/lib.rs"

[build-dependencies]
cc = "=1.4.2"
"""


def _generate_build_script(subject: dict[str, Any]) -> str:
    if not subject["support_modules"]:
        return "fn main() {}\n"
    files = "\n".join(
        f'        .file("fixed/support/src/{module}.c")'
        for module in subject["support_modules"]
    )
    return f"""fn main() {{
    cc::Build::new()
        .include("fixed/support/src")
        .include("fixed/support/test")
        .define("ALLOC_TESTING", None)
{files}
        .compile("vivo_support");
}}
"""


def generate_brief(subject: dict[str, Any]) -> str:
    targets = ", ".join(subject["modules"])
    support = ", ".join(subject["support_modules"]) or "none"
    return f"""# EvoC2Rust Vivo-Bench comparison: {subject['name']}

Translate the target C module group ({targets}) under `source/target/` into the
ABI-compatible Rust skeleton under `scaffold/src/production/`. This is fixed
test group {subject['id']} of 15, covering {len(subject['modules'])} of the 19
Vivo-Bench modules used by EvoC2Rust (DOI 10.1145/3786583.3786856).

## Required behavior

- Preserve every generated `#[no_mangle] extern "C"` symbol, `repr(C)` layout,
  public field, callback type, argument type, and return type.
- Replace every `unimplemented!()` production body with working Rust behavior.
- Prefer safe internal data structures and thin ABI adapters. Keep unsafe code
  narrowly scoped because the paper reports SafeRate.
- The immutable tests exercise allocation failure, memory release, collection
  behavior, callbacks, ordering, and boundary conditions.
- C support modules linked only by the evaluator: {support}.

## Scientific integrity constraints

- Never edit or weaken `oracle/`, `scaffold/`, `immutable_evaluator.py`, Cargo
  topology, test names, or module wiring to gain credit.
- Implement production behavior only in `pipeline/target`.
- C2Rust is used only to derive signatures and fixed tests. Its production
  bodies are intentionally absent from this workspace.
- Independent evaluation restores trusted files in a temporary copy and runs
  each of the {len(subject['test_functions'])} fixed tests separately.

Paper: https://arxiv.org/abs/2508.04295v4
"""


def generate_codeweaver_toml(
    subject: dict[str, Any], protocol: dict[str, Any]
) -> str:
    python = shlex.quote(sys.executable)
    build = (
        f"{python} immutable_evaluator.py --stage build "
        "--target pipeline/target --contract oracle "
        "--result pipeline/immutable-build.json"
    )
    tests = (
        f"{python} immutable_evaluator.py --stage test "
        "--target pipeline/target --contract oracle "
        "--result pipeline/immutable-test.json"
    )
    return f"""# Generated by experiments/evoc2rust/prepare.py. Do not edit.
[project]
name = {_toml_string(f"Vivo-Bench {subject['id']}: {subject['name']}")}
slug = {_toml_string(f"vivo-{subject['id']:02d}-{subject['name']}")}
description = "CodeWeaver comparison against EvoC2Rust on Vivo-Bench."

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
build_check = {_toml_string(build)}
unit_test = {_toml_string(tests)}
validate = {_toml_string(tests)}

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


def _prepare_c2rust_output(
    *,
    primary: Path,
    c2rust_binary: Path,
    destination: Path,
    rust_toolchain: str,
) -> dict[str, Any]:
    build = destination.parent / "cmake"
    _run(
        [
            "cmake",
            "-S",
            str(primary),
            "-B",
            str(build),
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        ]
    )
    _run(["cmake", "--build", str(build), "-j4"])
    ctest = _run(
        ["ctest", "--test-dir", str(build), "--output-on-failure"],
        timeout=300,
    )
    compile_commands = C.read_json(build / "compile_commands.json")
    c_commands = [
        row for row in compile_commands if str(row.get("file", "")).endswith(".c")
    ]
    C.atomic_write_json(build / "compile_commands-c.json", c_commands)
    _run(
        [
            str(c2rust_binary),
            "transpile",
            "--emit-build-files",
            "--emit-c-decl-map",
            "--preserve-unused-functions",
            "--fail-on-error",
            "--output-dir",
            str(destination),
            str(build / "compile_commands-c.json"),
        ],
        timeout=1200,
        env={
            "LLVM_CONFIG_PATH": "/usr/lib/llvm-18/bin/llvm-config",
            "LIBCLANG_PATH": "/usr/lib/llvm-18/lib",
        },
    )
    _run(
        [
            "cargo",
            f"+{rust_toolchain}",
            "check",
            "--manifest-path",
            str(destination / "Cargo.toml"),
            "--all-targets",
        ],
        timeout=600,
    )
    test_count_match = re.search(
        r"0 tests failed out of (\d+)", ctest.stdout
    )
    ctest_total = int(test_count_match.group(1)) if test_count_match else None
    return {
        "ctest_passed": (
            "100% tests passed" in ctest.stdout and ctest_total == 17
        ),
        "ctest_total": ctest_total,
        "ctest_output_sha256": hashlib.sha256(ctest.stdout.encode()).hexdigest(),
        "compile_command_count": len(c_commands),
    }


def _copy_source_inputs(
    primary: Path,
    subject: dict[str, Any],
    source: Path,
) -> None:
    for module in subject["modules"]:
        for suffix in (".c", ".h"):
            destination = source / "target" / f"{module}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(primary / "src" / f"{module}{suffix}", destination)
    for module in subject["support_modules"]:
        for suffix in (".c", ".h"):
            destination = source / "support" / f"{module}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(primary / "src" / f"{module}{suffix}", destination)
    for relative in (
        subject["test_file"],
        "test/alloc-testing.c",
        "test/alloc-testing.h",
        "test/framework.c",
        "test/framework.h",
    ):
        destination = source / "tests" / Path(relative).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(primary / relative, destination)


def active_test_functions(primary: Path, test_file: str) -> list[str]:
    text = (primary / test_file).read_text(encoding="utf-8")
    without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(
        r"(?:static\s+)?UnitTestFunction\s+tests\s*\[\s*\]\s*="
        r"\s*\{(.*?)\};",
        without_comments,
        flags=re.S,
    )
    if match is None:
        raise ValueError(f"cannot locate active test array in {test_file}")
    return re.findall(r"\b(test_[A-Za-z0-9_]+)\b", match.group(1))


def verify_active_tests(
    primary: Path, subjects: list[dict[str, Any]]
) -> dict[str, Any]:
    rows = []
    for subject in subjects:
        active = active_test_functions(primary, subject["test_file"])
        configured = subject["test_functions"]
        if len(active) != len(set(active)):
            raise ValueError(
                f"duplicate active test in {subject['test_file']}"
            )
        if set(active) != set(configured):
            raise ValueError(
                f"active tests drifted for subject {subject['id']}: "
                f"configured_only={sorted(set(configured) - set(active))}, "
                f"upstream_only={sorted(set(active) - set(configured))}"
            )
        rows.append(
            {
                "subject_id": subject["id"],
                "test_file": subject["test_file"],
                "active_test_count": len(active),
                "active_tests_sha256": hashlib.sha256(
                    "\n".join(active).encode()
                ).hexdigest(),
            }
        )
    total = sum(row["active_test_count"] for row in rows)
    if total != 125:
        raise ValueError(f"expected 125 upstream-active tests, found {total}")
    return {"verified": True, "active_test_count": total, "rows": rows}


def _copy_contract(
    primary: Path,
    transpiled: Path,
    subject: dict[str, Any],
    oracle: Path,
) -> None:
    test_files = {
        "tests/alloc_testing.rs": transpiled / "src/test/alloc_testing.rs",
        "tests/framework.rs": transpiled / "src/test/framework.rs",
        "tests/fixed_test.rs": (
            transpiled / f"src/test/{subject['test_module']}.rs"
        ),
    }
    for relative, source in test_files.items():
        destination = oracle / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for module in subject["support_modules"]:
        for suffix in (".c", ".h"):
            destination = oracle / "support/src" / f"{module}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(primary / "src" / f"{module}{suffix}", destination)
    allocation_header = oracle / "support/test/alloc-testing.h"
    allocation_header.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(primary / "test/alloc-testing.h", allocation_header)


def prepare_subject(
    subject: dict[str, Any],
    *,
    primary: Path,
    transpiled: Path,
    workspace_root: Path,
    protocol: dict[str, Any],
    tools: dict[str, str],
    force: bool = False,
) -> dict[str, Any]:
    prepared = workspace_root / str(subject["id"])
    if prepared.exists():
        if not force:
            marker = C.read_json(prepared / PREPARED_MARKER)
            expected = {
                "contract_sha256": C.tree_sha256(prepared / "oracle"),
                "evaluator_sha256": C.file_sha256(
                    prepared / "immutable_evaluator.py"
                ),
                "source_sha256": C.tree_sha256(prepared / "source"),
                "scaffold_sha256": C.tree_sha256(prepared / "scaffold"),
            }
            if all(marker.get(key) == value for key, value in expected.items()):
                return marker
            raise ValueError(
                f"prepared workspace {subject['id']} failed integrity verification"
            )
        shutil.rmtree(prepared)

    source = prepared / "source"
    scaffold = prepared / "scaffold"
    oracle = prepared / "oracle"
    (scaffold / "src/production").mkdir(parents=True)
    oracle.mkdir(parents=True)
    _copy_source_inputs(primary, subject, source)
    _copy_contract(primary, transpiled, subject, oracle)

    function_counts: dict[str, int] = {}
    for module in subject["modules"]:
        generated = transpiled / f"src/src/{rust_module_name(module)}.rs"
        text, function_count = strip_function_bodies(
            generated.read_text(encoding="utf-8")
        )
        C.atomic_write_text(
            scaffold / "src/production" / f"{rust_module_name(module)}.rs",
            text,
        )
        function_counts[module] = function_count
    C.atomic_write_text(
        scaffold / "src/lib.rs",
        _generate_lib(subject["modules"]),
    )
    C.atomic_write_text(scaffold / "Cargo.toml", _generate_cargo(subject))
    C.atomic_write_text(scaffold / "build.rs", _generate_build_script(subject))
    C.atomic_write_text(
        scaffold / "rust-toolchain.toml",
        f'[toolchain]\nchannel = "{tools["rust_toolchain"]}"\n',
    )
    _run(
        [
            "cargo",
            f"+{tools['rust_toolchain']}",
            "generate-lockfile",
            "--manifest-path",
            str(scaffold / "Cargo.toml"),
        ],
        timeout=300,
    )
    shutil.copy2(scaffold / "Cargo.lock", oracle / "Cargo.lock")

    copied_files = [
        path.relative_to(oracle).as_posix()
        for path in oracle.rglob("*")
        if path.is_file()
    ]
    contract = {
        "schema_version": 1,
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "crate_name": f"vivo_subject_{subject['id']:02d}",
        "modules": subject["modules"],
        "support_modules": subject["support_modules"],
        "test_module": subject["test_module"],
        "test_functions": subject["test_functions"],
        "c_assertions": subject["c_assertions"],
        "loc_source": subject["loc_source"],
        "rust_toolchain": tools["rust_toolchain"],
        "cc_version": tools["cc_version"],
        "file_sha256": {
            relative: C.file_sha256(oracle / relative)
            for relative in sorted(copied_files)
        },
    }
    C.atomic_write_json(oracle / "contract.json", contract)
    shutil.copy2(
        Path(__file__).with_name("evaluator.py"),
        prepared / "immutable_evaluator.py",
    )
    C.atomic_write_text(prepared / "brief.md", generate_brief(subject))
    C.atomic_write_text(
        prepared / "codeweaver.toml",
        generate_codeweaver_toml(subject, protocol),
    )
    marker = {
        "preparation_schema": PREPARATION_SCHEMA,
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "prepared_dir": str(prepared),
        "contract_sha256": C.tree_sha256(oracle),
        "evaluator_sha256": C.file_sha256(prepared / "immutable_evaluator.py"),
        "source_sha256": C.tree_sha256(source),
        "scaffold_sha256": C.tree_sha256(scaffold),
        "config_sha256": C.file_sha256(prepared / "codeweaver.toml"),
        "brief_sha256": C.file_sha256(prepared / "brief.md"),
        "function_counts": function_counts,
        "ground_truth_excluded": True,
        "prepared_at": C.utcnow_iso(),
    }
    C.atomic_write_json(prepared / PREPARED_MARKER, marker)
    return marker


def _normalized_test_results(stage: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": row["name"],
            "passed": row["passed"],
            "returncode": row["returncode"],
            "timed_out": row["timed_out"],
        }
        for row in stage.get("tests", [])
    ]


def _test_results_sha256(rows: list[dict[str, Any]]) -> str:
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def calibrate_contracts(
    *,
    primary: Path,
    transpiled: Path,
    workspace_root: Path,
    subjects: list[dict[str, Any]],
    temporary_root: Path,
) -> dict[str, Any]:
    rows = []
    for subject in subjects:
        subject_id = int(subject["id"])
        workspace = workspace_root / str(subject_id)
        full_target = temporary_root / f"calibration-{subject_id:02d}"
        production = full_target / "src/production"
        production.mkdir(parents=True)
        for module in subject["modules"]:
            shutil.copy2(
                transpiled / f"src/src/{rust_module_name(module)}.rs",
                production / f"{rust_module_name(module)}.rs",
            )

        c2rust_stage = evaluate_stage(
            "test",
            target=full_target,
            contract_dir=workspace / "oracle",
            timeout=600,
        )
        original_target = temporary_root / f"original-c-{subject_id:02d}"
        original_production = original_target / "src/production"
        original_production.mkdir(parents=True)
        for module in subject["modules"]:
            C.atomic_write_text(
                original_production / f"{rust_module_name(module)}.rs", ""
            )
        original_contract = temporary_root / f"original-contract-{subject_id:02d}"
        shutil.copytree(workspace / "oracle", original_contract)
        original_lock = C.read_json(original_contract / "contract.json")
        original_lock["support_modules"] = [
            *subject["modules"],
            *subject["support_modules"],
        ]
        for module in subject["modules"]:
            for suffix in (".c", ".h"):
                relative = f"support/src/{module}{suffix}"
                destination = original_contract / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(primary / "src" / f"{module}{suffix}", destination)
                original_lock["file_sha256"][relative] = C.file_sha256(destination)
        C.atomic_write_json(
            original_contract / "contract.json", original_lock
        )
        original_stage = evaluate_stage(
            "test",
            target=original_target,
            contract_dir=original_contract,
            timeout=600,
        )
        stub_build = evaluate_stage(
            "build",
            target=workspace / "scaffold",
            contract_dir=workspace / "oracle",
            timeout=600,
        )
        stub_stage = evaluate_stage(
            "test",
            target=workspace / "scaffold",
            contract_dir=workspace / "oracle",
            timeout=600,
        )
        original_summary = original_stage.get("summary", {})
        c2rust_summary = c2rust_stage.get("summary", {})
        stub_summary = stub_stage.get("summary", {})
        expected = len(subject["test_functions"])
        original_tests = _normalized_test_results(original_stage)
        c2rust_tests = _normalized_test_results(c2rust_stage)
        stub_tests = _normalized_test_results(stub_stage)
        row = {
            "subject_id": subject_id,
            "subject_name": subject["name"],
            "module_count": len(subject["modules"]),
            "contract_sha256": C.tree_sha256(workspace / "oracle"),
            "original_c_calibration_contract_sha256": C.tree_sha256(
                original_contract
            ),
            "full_translation_sha256": C.tree_sha256(production),
            "original_c": {
                "build_passed": bool(
                    original_stage.get("commands")
                    and original_stage["commands"][0].get("ok")
                ),
                "tests_expected": expected,
                "tests_executed": original_summary.get("executed", 0),
                "tests_passed": original_summary.get("passed", 0),
                "tests_failed": original_summary.get("failed", expected),
                "test_results_sha256": _test_results_sha256(original_tests),
            },
            "c2rust_diagnostic": {
                "build_passed": bool(
                    c2rust_stage.get("commands")
                    and c2rust_stage["commands"][0].get("ok")
                ),
                "tests_expected": expected,
                "tests_executed": c2rust_summary.get("executed", 0),
                "tests_passed": c2rust_summary.get("passed", 0),
                "tests_failed": c2rust_summary.get("failed", expected),
                "test_results_sha256": _test_results_sha256(c2rust_tests),
            },
            "stripped_scaffold": {
                "build_passed": stub_build.get("measurement", {}).get("value")
                is True,
                "tests_expected": expected,
                "tests_executed": stub_summary.get("executed", 0),
                "tests_passed": stub_summary.get("passed", 0),
                "tests_failed": stub_summary.get("failed", expected),
                "test_results_sha256": _test_results_sha256(stub_tests),
            },
        }
        if (
            not row["original_c"]["build_passed"]
            or row["original_c"]["tests_executed"] != expected
            or row["original_c"]["tests_passed"] != expected
        ):
            raise RuntimeError(
                f"translated Rust contract did not reproduce original C behavior "
                f"for subject {subject_id}: {original_summary}"
            )
        if (
            not row["stripped_scaffold"]["build_passed"]
            or row["stripped_scaffold"]["tests_executed"] != expected
            or row["stripped_scaffold"]["tests_passed"] != 0
        ):
            raise RuntimeError(
                f"stripped scaffold calibration failed for subject "
                f"{subject_id}: {stub_summary}"
            )
        rows.append(row)

    expected_tests = sum(len(subject["test_functions"]) for subject in subjects)
    original_passed = sum(row["original_c"]["tests_passed"] for row in rows)
    c2rust_passed = sum(
        row["c2rust_diagnostic"]["tests_passed"] for row in rows
    )
    stub_passed = sum(row["stripped_scaffold"]["tests_passed"] for row in rows)
    return {
        "schema_version": 1,
        "groups": len(rows),
        "expected_tests": expected_tests,
        "original_c_tests_passed": original_passed,
        "c2rust_diagnostic_tests_passed": c2rust_passed,
        "stripped_scaffold_tests_passed": stub_passed,
        "all_contracts_calibrated": (
            len(rows) == 15
            and expected_tests == 125
            and original_passed == expected_tests
            and stub_passed == 0
        ),
        "ground_truth_retained": False,
        "rows": rows,
    }


def prepare_all(
    *,
    artifact_root: Path,
    workspace_root: Path,
    c2rust_binary: Path,
    config: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    workspace_root = workspace_root.resolve()
    artifact_verification = verify_artifact_root(
        artifact_root, config["artifact"]["commit"]
    )
    tool_verification = verify_c2rust(c2rust_binary, config["tools"])
    primary = artifact_root / Path(config["artifact"]["primary_rel_path"])
    workspace_root.mkdir(parents=True, exist_ok=True)
    active_test_verification = verify_active_tests(
        primary, config["subjects"]
    )

    with tempfile.TemporaryDirectory(prefix="evoc2rust-preparation-") as temporary:
        temporary_root = Path(temporary)
        transpiled = temporary_root / "transpiled"
        calibration = _prepare_c2rust_output(
            primary=primary,
            c2rust_binary=c2rust_binary,
            destination=transpiled,
            rust_toolchain=config["tools"]["rust_toolchain"],
        )
        if not calibration["ctest_passed"]:
            raise RuntimeError("the pinned original Vivo-Bench C tests did not pass")
        markers = [
            prepare_subject(
                subject,
                primary=primary,
                transpiled=transpiled,
                workspace_root=workspace_root,
                protocol=config["protocol"],
                tools=config["tools"],
                force=force,
            )
            for subject in config["subjects"]
        ]
        rust_contracts = calibrate_contracts(
            primary=primary,
            transpiled=transpiled,
            workspace_root=workspace_root,
            subjects=config["subjects"],
            temporary_root=temporary_root,
        )
        if not rust_contracts["all_contracts_calibrated"]:
            raise RuntimeError("the translated Rust contracts did not calibrate")

    rows = []
    for subject, marker in zip(config["subjects"], markers, strict=True):
        rows.append(
            {
                "id": str(subject["id"]),
                "subject_id": subject["id"],
                "tool": "evoc2rust-vivo",
                "project": subject["name"],
                "source_language": "C",
                "target_language": "Rust",
                "source_rel_path": str(
                    Path(config["artifact"]["primary_rel_path"]) / "src"
                ),
                "oracle_rel_path": None,
                "scaffold_rel_path": None,
                "ground_truth_target_rel_path": None,
                "loc_source": subject["loc_source"],
                "status": "ok",
                "module_count": len(subject["modules"]),
                "test_count": len(subject["test_functions"]),
                "contract_sha256": marker["contract_sha256"],
                "evaluator_sha256": marker["evaluator_sha256"],
            }
        )
    manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "artifact_root": str(artifact_root),
        "artifact": {**config["artifact"], **artifact_verification},
        "tools": {**config["tools"], "c2rust": tool_verification},
        "protocol": config["protocol"],
        "counts": {
            "groups": len(rows),
            "modules": sum(row["module_count"] for row in rows),
            "tests": sum(row["test_count"] for row in rows),
        },
        "expected_counts": {"groups": 15, "modules": 19, "tests": 125},
        "counts_match_expected": (
            len(rows) == 15
            and sum(row["module_count"] for row in rows) == 19
            and sum(row["test_count"] for row in rows) == 125
        ),
        "projects": rows,
        "preparation": markers,
        "calibration": {
            "original_c": calibration,
            "translated_rust_contracts": rust_contracts,
            "active_test_arrays": active_test_verification,
        },
        "provenance": C.collect_provenance(artifact_root=artifact_root),
    }
    C.atomic_write_json(workspace_root / "manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--c2rust-binary", required=True)
    parser.add_argument("--config", default=str(C.DEFAULT_CONFIG))
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = prepare_all(
        artifact_root=Path(args.artifact_root),
        workspace_root=Path(args.workspace_root),
        c2rust_binary=Path(args.c2rust_binary).resolve(),
        config=load_config(args.config),
        force=args.force,
    )
    print(
        f"prepared {manifest['counts']['groups']} Vivo-Bench groups "
        f"({manifest['counts']['modules']} modules, "
        f"{manifest['counts']['tests']} tests)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
