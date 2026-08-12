"""Workspace-local immutable evaluator for prepared Rustine subjects.

This file is copied verbatim into each prepared workspace, so it intentionally
uses only the Python standard library and has no package-relative imports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

PINNED_TOOLCHAIN = "nightly-2025-05-13"
CARGO_NEWMETRICS_PATH = "/opt/codeweaver-rustine-tools/bin/cargo-newmetrics"
COMMAND_OUTPUT_LIMIT = 250_000


def measurement(status: str, value: Any = None, reason: str = "") -> dict[str, Any]:
    return {"status": status, "value": value, "reason": reason}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_output(text: str) -> str:
    if len(text) <= COMMAND_OUTPUT_LIMIT:
        return text
    half = COMMAND_OUTPUT_LIMIT // 2
    return (
        text[:half]
        + "\n...[command output truncated by immutable evaluator]...\n"
        + text[-half:]
    )


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _set_table_assignment(text: str, table: str, key: str, line: str) -> str:
    lines = text.splitlines()
    header = f"[{table}]"
    try:
        start = next(index for index, item in enumerate(lines) if item.strip() == header)
    except StopIteration:
        lines.extend(["", header, line])
        return "\n".join(lines).rstrip() + "\n"
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("["):
            end = index
            break
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index in range(start + 1, end):
        if pattern.match(lines[index]):
            lines[index] = line
            return "\n".join(lines).rstrip() + "\n"
    lines.insert(end, line)
    return "\n".join(lines).rstrip() + "\n"


def _remove_required_bin_blocks(text: str, names: set[str] | None) -> str:
    lines = text.splitlines()
    blocks: list[tuple[int, int, str | None]] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "[[bin]]":
            index += 1
            continue
        end = index + 1
        while end < len(lines) and not lines[end].strip().startswith("["):
            end += 1
        name = None
        for line in lines[index + 1 : end]:
            match = re.match(r'^\s*name\s*=\s*["\']([^"\']+)["\']', line)
            if match:
                name = match.group(1)
                break
        blocks.append((index, end, name))
        index = end
    for start, end, name in reversed(blocks):
        if names is None or name in names:
            del lines[start:end]
    return "\n".join(lines).rstrip() + "\n"


def _safe_manifest_sections(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith("["):
            index += 1
            continue
        end = index + 1
        while end < len(lines) and not lines[end].strip().startswith("["):
            end += 1
        normalized = stripped.lower()
        allowed = (
            normalized == "[dependencies]"
            or normalized.startswith("[dependencies.")
            or normalized == "[dev-dependencies]"
            or normalized.startswith("[dev-dependencies.")
            or normalized == "[build-dependencies]"
            or normalized.startswith("[build-dependencies.")
            or normalized == "[features]"
            or normalized.startswith("[lints")
            or (
                normalized.startswith("[target.")
                and re.search(
                    r"\.(?:dev-|build-)?dependencies\]$", normalized
                )
            )
        )
        if allowed and not normalized.startswith("[["):
            kept.extend(lines[index:end])
            kept.append("")
        index = end
    return "\n".join(kept).rstrip()


def _rebuild_cargo_topology(text: str, requirements: dict[str, Any]) -> str:
    package = requirements.get("package", {})
    lib = requirements.get("lib", {})
    lines = ["[package]"]
    for key in ("name", "version", "edition"):
        if key in package:
            lines.append(f"{key} = {_toml_value(package[key])}")
    lines.extend(
        [
            "autobins = false",
            "autoexamples = false",
            "autotests = false",
            "autobenches = false",
            (
                'build = "build.rs"'
                if requirements.get("allow_build_script")
                else "build = false"
            ),
            "",
            "[lib]",
            f"name = {_toml_value(lib['name'])}",
            f"path = {_toml_value(lib.get('path', 'src/lib.rs'))}",
        ]
    )
    for entry in requirements.get("bins", []):
        lines.extend(
            [
                "",
                "[[bin]]",
                f"name = {_toml_value(entry['name'])}",
                f"path = {_toml_value(entry['path'])}",
            ]
        )
    safe_sections = _safe_manifest_sections(text)
    if safe_sections:
        lines.extend(["", safe_sections])
    return "\n".join(lines).rstrip() + "\n"


def apply_cargo_contract(cargo_path: Path, requirements: dict[str, Any]) -> None:
    text = cargo_path.read_text(encoding="utf-8")
    text = _rebuild_cargo_topology(text, requirements)
    for key, line in requirements.get("dependencies", {}).items():
        text = _set_table_assignment(text, "dependencies", key, line)
    for key, line in requirements.get("build_dependencies", {}).items():
        text = _set_table_assignment(text, "build-dependencies", key, line)
    cargo_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def ensure_modules(lib_path: Path, modules: list[str]) -> None:
    if not modules:
        return
    text = lib_path.read_text(encoding="utf-8") if lib_path.exists() else ""
    for module in modules:
        text = re.sub(
            rf"(?m)^(?:\s*#\[[^\n]+\]\s*\n)*\s*(?:pub\s+)?mod\s+"
            rf"{re.escape(module)}\s*;\s*\n?",
            "",
            text,
        )
        text = re.sub(
            rf"(?m)^\s*pub\s+use\s+{re.escape(module)}::\*\s*;\s*\n?",
            "",
            text,
        )
        text = text.rstrip() + f"\n\npub mod {module};\npub use {module}::*;\n"
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    lib_path.write_text(text, encoding="utf-8")


def remove_contract_modules(lib_path: Path, modules: list[str]) -> None:
    if not lib_path.exists():
        return
    text = lib_path.read_text(encoding="utf-8")
    for module in modules:
        text = re.sub(
            rf"(?m)^\s*(?:pub\s+)?mod\s+{re.escape(module)}\s*;\s*\n?",
            "",
            text,
        )
        text = re.sub(
            rf"(?m)^\s*pub\s+use\s+{re.escape(module)}::\*\s*;\s*\n?",
            "",
            text,
        )
    lib_path.write_text(text, encoding="utf-8")


def load_contract(contract_dir: Path) -> dict[str, Any]:
    lock = json.loads((contract_dir / "contract.json").read_text(encoding="utf-8"))
    if lock.get("schema_version") != 1:
        raise ValueError("unsupported contract schema")
    for rel, expected in lock.get("file_sha256", {}).items():
        path = contract_dir / Path(rel)
        if not path.is_file():
            raise ValueError(f"immutable contract file is missing: {rel}")
        actual = file_sha256(path)
        if actual != expected:
            raise ValueError(f"immutable contract file changed: {rel}")
    return lock


def materialize_evaluation_copy(
    target: Path, contract_dir: Path, *, production_only: bool = False
) -> tuple[Path, Path, dict[str, Any]]:
    lock = load_contract(contract_dir)
    if not (target / "Cargo.toml").is_file():
        raise FileNotFoundError(f"target has no Cargo.toml: {target}")
    scratch = Path(tempfile.mkdtemp(prefix="rustine-evaluation-"))
    project = scratch / "project"
    shutil.copytree(
        target,
        project,
        ignore=shutil.ignore_patterns("target", ".git", ".cargo"),
    )
    for rel in (
        lock.get("files", [])
        + lock.get("assets", [])
        + lock.get("support_files", [])
    ):
        source = contract_dir / Path(rel)
        destination = project / Path(rel)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for path in (
        project / "rust-toolchain",
        project / "rust-toolchain.toml",
    ):
        if path.is_file():
            path.unlink()
    if not lock["cargo"].get("allow_build_script"):
        build_script = project / "build.rs"
        if build_script.is_file():
            build_script.unlink()
    apply_cargo_contract(project / "Cargo.toml", lock["cargo"])
    ensure_modules(project / "src" / "lib.rs", lock.get("modules", []))
    if production_only:
        for rel in lock.get("files", []) + lock.get("assets", []):
            path = project / Path(rel)
            if path.is_file():
                path.unlink()
        remove_contract_modules(project / "src" / "lib.rs", lock.get("modules", []))
        cargo_path = project / "Cargo.toml"
        cargo_text = _remove_required_bin_blocks(
            cargo_path.read_text(encoding="utf-8"), None
        )
        cargo_text = _set_table_assignment(
            cargo_text, "package", "autobins", "autobins = false"
        )
        cargo_path.write_text(cargo_text, encoding="utf-8")
        for dirname in ("tests", "benches", "examples"):
            path = project / dirname
            if path.exists():
                shutil.rmtree(path)
    return scratch, project, lock


class CommandBackend:
    def __init__(self, mode: str):
        self.mode = mode

    @classmethod
    def discover(cls) -> "CommandBackend | None":
        if shutil.which("cargo"):
            return cls("native")
        if os.name == "nt" and shutil.which("wsl"):
            try:
                probe = subprocess.run(
                    ["wsl", "-e", "bash", "-lc", "command -v cargo >/dev/null"],
                    capture_output=True,
                    timeout=20,
                    check=False,
                )
                if probe.returncode == 0:
                    return cls("wsl")
            except (OSError, subprocess.SubprocessError):
                pass
        return None

    def _wsl_path(self, path: Path) -> str:
        result = subprocess.run(
            ["wsl", "-e", "wslpath", "-a", str(path.resolve())],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"wslpath failed for {path}")
        return result.stdout.strip()

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float,
        env: dict[str, str] | None = None,
        input_text: str | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        command = argv
        child_env = None
        if self.mode == "native":
            child_env = os.environ.copy()
            child_env.update(env or {})
        else:
            exports = ""
            if env:
                exports = " ".join(
                    f"{key}={shlex.quote(value)}" for key, value in env.items()
                ) + " "
            shell = (
                f"cd {shlex.quote(self._wsl_path(cwd))} && "
                f"{exports}{shlex.join(argv)}"
            )
            command = ["wsl", "-e", "bash", "-lc", shell]
        try:
            result = subprocess.run(
                command,
                cwd=cwd if self.mode == "native" else None,
                env=child_env,
                input=input_text,
                stdin=subprocess.DEVNULL if input_text is None else None,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            return {
                "argv": argv,
                "backend": self.mode,
                "returncode": result.returncode,
                "stdout": _bounded_output(result.stdout),
                "stderr": _bounded_output(result.stderr),
                "duration_seconds": time.monotonic() - started,
                "timed_out": False,
                "ok": result.returncode == 0,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "argv": argv,
                "backend": self.mode,
                "returncode": None,
                "stdout": (
                    _bounded_output(exc.stdout or "")
                    if isinstance(exc.stdout, str)
                    else ""
                ),
                "stderr": (
                    _bounded_output(exc.stderr or "")
                    if isinstance(exc.stderr, str)
                    else ""
                ),
                "duration_seconds": time.monotonic() - started,
                "timed_out": True,
                "ok": False,
            }
        except OSError as exc:
            return {
                "argv": argv,
                "backend": self.mode,
                "returncode": None,
                "stdout": "",
                "stderr": str(exc),
                "duration_seconds": time.monotonic() - started,
                "timed_out": False,
                "ok": False,
            }


def _reason(result: dict[str, Any]) -> str:
    if result.get("timed_out"):
        return "command timed out"
    stderr = (result.get("stderr") or "").strip().splitlines()
    stdout = (result.get("stdout") or "").strip().splitlines()
    return (stderr or stdout or [f"returncode={result.get('returncode')}"])[-1]


def _run_rust_binary_contract(
    backend: CommandBackend,
    project: Path,
    lock: dict[str, Any],
    *,
    timeout: float,
    env: dict[str, str] | None = None,
) -> tuple[bool, list[dict[str, Any]], str]:
    commands = []
    output = ""
    executions = lock.get("executions") or [
        {"target": target, "args": [], "stdin": None}
        for target in lock["targets"]
    ]
    for execution in executions:
        target = execution["target"]
        result = backend.run(
            [
                "cargo",
                "run",
                "--quiet",
                "--bin",
                target,
                "--",
                *execution.get("args", []),
            ],
            cwd=project,
            timeout=timeout,
            env=env,
            input_text=execution.get("stdin"),
        )
        commands.append(result)
        output += "\n" + result.get("stdout", "") + "\n" + result.get("stderr", "")
        if not result["ok"]:
            return False, commands, output
    success_regex = lock.get("success_regex")
    failure_regex = lock.get("failure_regex")
    if failure_regex and re.search(failure_regex, output):
        return False, commands, output
    if success_regex and not re.search(success_regex, output):
        return False, commands, output
    return True, commands, output


ROUNDTRIP_BYTES = (
    b"Rustine-CodeWeaver deterministic bzip2 round trip\n"
    b"0123456789abcdef0123456789abcdef\n" * 8
)


def _run_bzip2_roundtrip(
    backend: CommandBackend,
    project: Path,
    *,
    timeout: float,
    env: dict[str, str] | None = None,
) -> tuple[bool, list[dict[str, Any]], str]:
    input_path = project / ".rustine-roundtrip-input.txt"
    compressed = project / ".rustine-roundtrip-input.txt.bz2"
    input_path.write_bytes(ROUNDTRIP_BYTES)
    commands = []
    first = backend.run(
        ["cargo", "run", "--quiet", "--bin", "bzip2", "--", "-k", input_path.name],
        cwd=project,
        timeout=timeout,
        env=env,
    )
    commands.append(first)
    if not first["ok"] or not compressed.exists():
        return False, commands, "compression did not produce the expected .bz2 file"
    input_path.unlink()
    second = backend.run(
        [
            "cargo",
            "run",
            "--quiet",
            "--bin",
            "bzip2",
            "--",
            "-d",
            "-k",
            "-f",
            compressed.name,
        ],
        cwd=project,
        timeout=timeout,
        env=env,
    )
    commands.append(second)
    if not second["ok"] or not input_path.exists():
        return False, commands, "decompression did not restore the input file"
    if input_path.read_bytes() != ROUNDTRIP_BYTES:
        return False, commands, "round-trip output differs from deterministic input"
    return True, commands, "deterministic compression/decompression round trip passed"


def _assertion_measurements(
    lock: dict[str, Any], passed: bool, output: str
) -> dict[str, dict[str, Any]]:
    unavailable = {
        key: measurement("unavailable", reason="exact executed assertion count is not defensible")
        for key in ("executed", "passed", "failed")
    }
    mode = lock["assertion_credit"]
    if mode == "not_applicable":
        return {
            key: measurement("not_applicable", reason="subject has no test contract")
            for key in ("executed", "passed", "failed")
        }
    if mode == "unavailable":
        return unavailable
    if mode == "pass_all_paper_denominator":
        if not passed:
            return {
                key: measurement(
                    "unavailable",
                    reason="a failed/partial run cannot be mapped to the paper assertion denominator",
                )
                for key in ("executed", "passed", "failed")
            }
        total = lock.get("paper_assertions")
        if not isinstance(total, int):
            return unavailable
        return {
            "executed": measurement(
                "inferred",
                total,
                "all fixed checks passed; value is credited from the paper denominator",
            ),
            "passed": measurement(
                "inferred",
                total,
                "all fixed checks passed; value is credited from the paper denominator",
            ),
            "failed": measurement(
                "inferred",
                0,
                "all fixed checks passed; value is credited from the paper denominator",
            ),
        }
    success = re.search(lock["success_regex"], output)
    failure = re.search(lock["failure_regex"], output)
    if success:
        passed_count, total = map(int, success.groups())
        failed_count = total - passed_count
    elif failure:
        failed_count, total = map(int, failure.groups())
        passed_count = total - failed_count
    else:
        return unavailable
    return {
        "executed": measurement("measured", total),
        "passed": measurement("measured", passed_count),
        "failed": measurement("measured", failed_count),
    }


def production_module_paths(project: Path, lock: dict[str, Any]) -> set[str]:
    contract_paths = set(lock.get("files", []))
    discovered: set[Path] = set()
    pending = [project / "src" / "lib.rs"]
    pending.extend(
        project / Path(entry["path"])
        for entry in lock.get("cargo", {}).get("bins", [])
        if entry.get("path") not in contract_paths
    )
    mod_pattern = re.compile(
        r"(?m)(?P<attrs>(?:^\s*#\[[^\n]+\]\s*\n)*)"
        r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;"
    )
    while pending:
        current = pending.pop()
        if current in discovered or not current.is_file():
            continue
        rel = current.relative_to(project).as_posix()
        if rel in contract_paths:
            continue
        discovered.add(current)
        text = current.read_text(encoding="utf-8", errors="replace")
        for match in mod_pattern.finditer(text):
            module = match.group("name")
            path_attr = re.search(
                r'#\s*\[\s*path\s*=\s*["\']([^"\']+)["\']\s*\]',
                match.group("attrs"),
            )
            if path_attr:
                candidates = [current.parent / Path(path_attr.group(1))]
            else:
                candidates = [
                    current.parent / f"{module}.rs",
                    current.parent / module / "mod.rs",
                ]
            pending.extend(candidate for candidate in candidates if candidate.is_file())
    return {path.relative_to(project).as_posix() for path in discovered}


POINTER_ARITHMETIC_RE = re.compile(
    r"\.(?:add|sub|offset|offset_from|byte_add|byte_sub|byte_offset|"
    r"wrapping_add|wrapping_sub|wrapping_offset|wrapping_byte_add|"
    r"wrapping_byte_sub)\s*\("
)


def count_pointer_arithmetic(project: Path, paths: set[str]) -> int:
    return sum(
        len(POINTER_ARITHMETIC_RE.findall((project / Path(rel)).read_text(
            encoding="utf-8", errors="replace"
        )))
        for rel in paths
        if (project / Path(rel)).is_file()
    )


NEWMETRICS_KEYS = {
    "Pointer arithmetic": "pointer_arithmetic",
    "Unsafe lines": "unsafe_lines",
    "Unsafe calls": "unsafe_calls",
    "Unsafe casts": "unsafe_type_casts",
    "Raw pointer dereferences": "raw_pointer_dereferences",
    "Raw pointer declarations": "raw_pointer_declarations",
}


def parse_newmetrics_output(text: str) -> list[dict[str, int]]:
    blocks: list[dict[str, int]] = []
    current: dict[str, int] = {}
    required = set(NEWMETRICS_KEYS.values()) - {"pointer_arithmetic"}
    for line in text.splitlines():
        if ":" not in line:
            continue
        label, raw = (part.strip() for part in line.split(":", 1))
        key = NEWMETRICS_KEYS.get(label)
        if key is not None and key in current:
            blocks.append(current)
            current = {}
        if key is not None and re.fullmatch(r"\d+", raw):
            current[key] = int(raw)
    if current:
        blocks.append(current)
    return [block for block in blocks if required.issubset(block)]


def _parse_exported_env(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line.strip())
        if not match:
            continue
        values = shlex.split(match.group(2))
        if len(values) == 1:
            env[match.group(1)] = values[0]
    return env


def parse_llvm_cov_json(payload: str, included_paths: set[str]) -> dict[str, float | int]:
    data = json.loads(payload)
    entries = data.get("data") or []
    files = entries[0].get("files", []) if entries else []
    totals = {
        "functions_count": 0,
        "functions_covered": 0,
        "lines_count": 0,
        "lines_covered": 0,
    }
    normalized = {path.replace("\\", "/") for path in included_paths}
    matched = 0
    for entry in files:
        filename = str(entry.get("filename", "")).replace("\\", "/")
        if not any(filename == rel or filename.endswith("/" + rel) for rel in normalized):
            continue
        matched += 1
        summary = entry.get("summary", {})
        functions = summary.get("functions", {})
        lines = summary.get("lines", {})
        totals["functions_count"] += int(functions.get("count", 0))
        totals["functions_covered"] += int(functions.get("covered", 0))
        totals["lines_count"] += int(lines.get("count", 0))
        totals["lines_covered"] += int(lines.get("covered", 0))
    if not matched:
        raise ValueError("coverage report contained no production library files")
    totals["function_percent"] = (
        100.0 * totals["functions_covered"] / totals["functions_count"]
        if totals["functions_count"]
        else 0.0
    )
    totals["line_percent"] = (
        100.0 * totals["lines_covered"] / totals["lines_count"]
        if totals["lines_count"]
        else 0.0
    )
    return totals


def evaluate_stage(
    stage: str,
    *,
    target: Path,
    contract_dir: Path,
    timeout: float = 5000,
    backend: CommandBackend | None = None,
) -> dict[str, Any]:
    production_only = stage == "safety"
    try:
        scratch, project, lock = materialize_evaluation_copy(
            target, contract_dir, production_only=production_only
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "stage": stage,
            "ok": False,
            "measurement": measurement("error", reason=str(exc)),
            "commands": [],
        }
    backend = backend or CommandBackend.discover()
    base_env: dict[str, str] = {}
    try:
        if backend is None:
            return {
                "stage": stage,
                "ok": stage in {"coverage", "safety"},
                "measurement": measurement(
                    "unavailable", reason="cargo is unavailable natively and through WSL"
                ),
                "commands": [],
            }
        if stage == "build":
            result = backend.run(
                ["cargo", "build", "--all-targets"],
                cwd=project,
                timeout=timeout,
                env=base_env,
            )
            return {
                "stage": stage,
                "ok": result["ok"],
                "measurement": measurement(
                    "measured", result["ok"], "" if result["ok"] else _reason(result)
                ),
                "commands": [result],
            }
        if stage == "test":
            if lock["kind"] == "none":
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "not_applicable", reason="paper/artifact provides no tests"
                    ),
                    "assertions": _assertion_measurements(lock, False, ""),
                    "commands": [],
                }
            if lock["kind"] == "derived_cli_roundtrip":
                passed, commands, output = _run_bzip2_roundtrip(
                    backend, project, timeout=timeout, env=base_env
                )
            else:
                passed, commands, output = _run_rust_binary_contract(
                    backend, project, lock, timeout=timeout, env=base_env
                )
            failure_reason = ""
            if not passed:
                if commands and not commands[-1]["ok"]:
                    failure_reason = _reason(commands[-1])
                else:
                    lines = output.strip().splitlines()
                    failure_reason = lines[-1] if lines else "fixed contract reported failure"
            return {
                "stage": stage,
                "ok": passed,
                "measurement": measurement(
                    "measured",
                    passed,
                    failure_reason,
                ),
                "assertions": _assertion_measurements(lock, passed, output),
                "commands": commands,
            }
        if stage == "coverage":
            if lock["kind"] == "none":
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "not_applicable", reason="coverage is N/A without a test contract"
                    ),
                    "commands": [],
                }
            version = backend.run(
                ["cargo", "llvm-cov", "--version"],
                cwd=project,
                timeout=30,
                env=base_env,
            )
            if not version["ok"]:
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "unavailable", reason="cargo llvm-cov is not installed"
                    ),
                    "commands": [version],
                }
            expected_version = lock.get("tools", {}).get("cargo_llvm_cov_version")
            actual_version = version["stdout"].strip()
            if actual_version != f"cargo-llvm-cov {expected_version}":
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "unavailable",
                        reason=(
                            "cargo llvm-cov version mismatch: "
                            f"expected {expected_version}, found {actual_version or 'unknown'}"
                        ),
                    ),
                    "commands": [version],
                }
            commands = [version]
            clean = backend.run(
                ["cargo", "llvm-cov", "clean", "--workspace"],
                cwd=project,
                timeout=timeout,
                env=base_env,
            )
            commands.append(clean)
            show_env = backend.run(
                ["cargo", "llvm-cov", "show-env", "--sh"],
                cwd=project,
                timeout=timeout,
                env=base_env,
            )
            commands.append(show_env)
            if not clean["ok"] or not show_env["ok"]:
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement("error", reason=_reason(commands[-1])),
                    "commands": commands,
                }
            coverage_env = {**base_env, **_parse_exported_env(show_env["stdout"])}
            if lock["kind"] == "derived_cli_roundtrip":
                passed, test_commands, _ = _run_bzip2_roundtrip(
                    backend, project, timeout=timeout, env=coverage_env
                )
            else:
                passed, test_commands, _ = _run_rust_binary_contract(
                    backend, project, lock, timeout=timeout, env=coverage_env
                )
            commands.extend(test_commands)
            if not passed:
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "error", reason="instrumented fixed contract did not pass"
                    ),
                    "commands": commands,
                }
            report = backend.run(
                ["cargo", "llvm-cov", "report", "--json", "--summary-only"],
                cwd=project,
                timeout=timeout,
                env=coverage_env,
            )
            commands.append(report)
            if not report["ok"]:
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement("error", reason=_reason(report)),
                    "commands": commands,
                }
            production_paths = production_module_paths(project, lock)
            comparable_paths = production_paths | {
                rel for rel in lock.get("files", []) if rel.endswith(".rs")
            }
            try:
                totals = parse_llvm_cov_json(report["stdout"], comparable_paths)
                production_totals = parse_llvm_cov_json(
                    report["stdout"], production_paths
                )
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement("error", reason=str(exc)),
                    "commands": commands,
                }
            return {
                "stage": stage,
                "ok": True,
                "measurement": measurement("measured", totals),
                "production_only_measurement": measurement(
                    "measured", production_totals
                ),
                "coverage_files": {
                    "paper_comparable": sorted(comparable_paths),
                    "production_only": sorted(production_paths),
                },
                "commands": commands,
            }
        if stage == "safety":
            production_paths = production_module_paths(project, lock)
            pointer_count = count_pointer_arithmetic(project, production_paths)
            pointer_diagnostic = measurement(
                "measured",
                pointer_count,
                "non-HIR source-pattern diagnostic over production modules",
            )
            pointer = measurement(
                "unavailable",
                reason="cargo-newmetrics did not expose a rustc-HIR pointer count",
            )
            env = {"RUSTUP_TOOLCHAIN": PINNED_TOOLCHAIN}
            if backend.mode == "wsl" or os.name != "nt":
                toolchain_lib = (
                    "/root/.rustup/toolchains/"
                    "nightly-2025-05-13-x86_64-unknown-linux-gnu/lib"
                )
                env.update({
                    "PATH": "/opt/codeweaver-rustine-tools/bin:/root/.cargo/bin:"
                    "/usr/local/bin:/usr/bin:/bin",
                    "LD_LIBRARY_PATH": toolchain_lib,
                    "RUSTFLAGS": f"-L {toolchain_lib}",
                })
            hash_result = backend.run(
                ["sha256sum", CARGO_NEWMETRICS_PATH],
                cwd=project,
                timeout=30,
                env=env,
            )
            expected_hash = lock.get("tools", {}).get("cargo_newmetrics_sha256")
            actual_hash = (
                hash_result.get("stdout", "").strip().split()[0]
                if hash_result["ok"] and hash_result.get("stdout", "").strip()
                else ""
            )
            if not hash_result["ok"] or actual_hash != expected_hash:
                reason = (
                    _reason(hash_result)
                    if not hash_result["ok"]
                    else (
                        "cargo-newmetrics hash mismatch: "
                        f"expected {expected_hash}, found {actual_hash or 'unknown'}"
                    )
                )
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement("unavailable", reason=reason),
                    "pointer_arithmetic": pointer,
                    "pointer_arithmetic_diagnostic": pointer_diagnostic,
                    "commands": [hash_result],
                }
            metrics_result = backend.run(
                ["cargo", "newmetrics"],
                cwd=project,
                timeout=timeout,
                env=env,
            )
            if not metrics_result["ok"]:
                diagnostic = (
                    metrics_result.get("stderr", "") + "\n" + metrics_result.get("stdout", "")
                ).lower()
                unavailable = any(
                    marker in diagnostic
                    for marker in (
                        "no such command: `newmetrics`",
                        "command not found",
                        "not recognized as an internal or external command",
                    )
                )
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "unavailable" if unavailable else "error",
                        reason=(
                            "Rustine cargo-newmetrics is not installed"
                            if unavailable
                            else _reason(metrics_result)
                        ),
                    ),
                    "pointer_arithmetic": pointer,
                    "pointer_arithmetic_diagnostic": pointer_diagnostic,
                    "commands": [hash_result, metrics_result],
                }
            blocks = parse_newmetrics_output(
                metrics_result["stdout"] + "\n" + metrics_result["stderr"]
            )
            if len(blocks) != 1:
                return {
                    "stage": stage,
                    "ok": True,
                    "measurement": measurement(
                        "error",
                        reason=f"expected one library newmetrics block, parsed {len(blocks)}",
                    ),
                    "pointer_arithmetic": pointer,
                    "pointer_arithmetic_diagnostic": pointer_diagnostic,
                    "commands": [hash_result, metrics_result],
                }
            block = dict(blocks[0])
            hir_pointer = block.pop("pointer_arithmetic", None)
            if hir_pointer is not None:
                pointer = measurement(
                    "measured",
                    hir_pointer,
                    "Rustine rustc-HIR cargo-newmetrics library-target measurement",
                )
            return {
                "stage": stage,
                "ok": True,
                "measurement": measurement("measured", block),
                "pointer_arithmetic": pointer,
                "pointer_arithmetic_diagnostic": pointer_diagnostic,
                "commands": [hash_result, metrics_result],
                "production_files": sorted(production_paths),
            }
        raise ValueError(f"unknown evaluator stage: {stage}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("build", "test", "coverage", "safety"), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--result")
    parser.add_argument("--timeout", type=float, default=5000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = evaluate_stage(
        args.stage,
        target=Path(args.target).resolve(),
        contract_dir=Path(args.contract).resolve(),
        timeout=args.timeout,
    )
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.result:
        path = Path(args.result)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
