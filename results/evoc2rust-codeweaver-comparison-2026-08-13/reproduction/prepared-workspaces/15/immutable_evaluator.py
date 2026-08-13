"""Immutable evaluator for prepared EvoC2Rust Vivo-Bench workspaces."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

COMMAND_OUTPUT_LIMIT = 250_000
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


def measurement(status: str, value: Any = None, reason: str = "") -> dict[str, Any]:
    return {"status": status, "value": value, "reason": reason}


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded(value: str) -> str:
    if len(value) <= COMMAND_OUTPUT_LIMIT:
        return value
    half = COMMAND_OUTPUT_LIMIT // 2
    return value[:half] + "\n... output truncated ...\n" + value[-half:]


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: float,
) -> dict[str, Any]:
    env = os.environ.copy()
    for name in (
        "CARGO_ENCODED_RUSTFLAGS",
        "RUSTC_WORKSPACE_WRAPPER",
        "RUSTC_WRAPPER",
        "RUSTFLAGS",
        "RUSTUP_TOOLCHAIN",
    ):
        env.pop(name, None)
    env["CARGO_TERM_COLOR"] = "never"
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "returncode": result.returncode,
            "ok": result.returncode == 0,
            "timed_out": False,
            "stdout": _bounded(result.stdout),
            "stderr": _bounded(result.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "returncode": None,
            "ok": False,
            "timed_out": True,
            "stdout": _bounded(exc.stdout or ""),
            "stderr": _bounded(exc.stderr or ""),
        }
    except OSError as exc:
        return {
            "argv": argv,
            "returncode": None,
            "ok": False,
            "timed_out": False,
            "stdout": "",
            "stderr": str(exc),
        }


def _reason(result: dict[str, Any]) -> str:
    if result.get("timed_out"):
        return "command timed out"
    lines = (result.get("stderr") or result.get("stdout") or "").strip().splitlines()
    return lines[-1] if lines else f"returncode={result.get('returncode')}"


def load_contract(contract_dir: Path) -> dict[str, Any]:
    contract = json.loads(
        (contract_dir / "contract.json").read_text(encoding="utf-8")
    )
    if contract.get("schema_version") != 1:
        raise ValueError("unsupported fixed-contract schema")
    for relative, expected in contract.get("file_sha256", {}).items():
        path = contract_dir / relative
        if not path.is_file():
            raise ValueError(f"fixed-contract file is missing: {relative}")
        if file_sha256(path) != expected:
            raise ValueError(f"fixed-contract file changed: {relative}")
    return contract


def _crate_name(contract: dict[str, Any]) -> str:
    return str(contract["crate_name"])


def _cargo_text(contract: dict[str, Any]) -> str:
    crate = _crate_name(contract)
    return f"""[package]
name = "{crate}"
version = "0.1.0"
edition = "2021"
publish = false
autobins = false

[lib]
name = "{crate}"
path = "src/lib.rs"

[[bin]]
name = "fixed_contract"
path = "src/bin/fixed_contract.rs"

[build-dependencies]
cc = "={contract['cc_version']}"
"""


def _build_script(contract: dict[str, Any]) -> str:
    support = contract["support_modules"]
    if not support:
        return "fn main() {}\n"
    files = "\n".join(
        f'        .file("fixed/support/src/{module}.c")' for module in support
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


def _lib_text(contract: dict[str, Any]) -> str:
    lines = [RUST_PREAMBLE.rstrip(), "", "pub mod production {"]
    lines.extend(
        f"    pub mod {module.replace('-', '_')};"
        for module in contract["modules"]
    )
    lines.extend(
        [
            "}",
            "",
            "pub mod oracle {",
            "    pub mod alloc_testing;",
            "    pub mod framework;",
            "    pub mod fixed_test;",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def _runner_text(contract: dict[str, Any]) -> str:
    crate = _crate_name(contract)
    return f"""fn main() {{
    let name = std::env::args().nth(1).expect("fixed test name is required");
    unsafe {{
        {crate}::oracle::alloc_testing::alloc_test_set_limit(-1);
        {crate}::oracle::fixed_test::__codeweaver_fixed_test_dispatch(
            name.as_str()
        );
        let leaked = {crate}::oracle::alloc_testing::alloc_test_get_allocated();
        assert_eq!(leaked, 0, "fixed test leaked {{leaked}} bytes");
    }}
}}
"""


def _dispatch_text(contract: dict[str, Any]) -> str:
    arms = "\n".join(
        f'        "{name}" => {name}(),'
        for name in contract["test_functions"]
    )
    return f"""

#[doc(hidden)]
pub unsafe fn __codeweaver_fixed_test_dispatch(name: &str) {{
    match name {{
{arms}
        _ => panic!("unknown fixed test: {{name}}"),
    }}
}}
"""


def materialize_evaluation_copy(
    target: Path, contract_dir: Path
) -> tuple[Path, Path, dict[str, Any]]:
    contract = load_contract(contract_dir)
    if not (target / "src/production").is_dir():
        raise FileNotFoundError("candidate has no src/production directory")
    symlinks = [
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_symlink()
    ]
    if symlinks:
        raise ValueError(f"candidate contains unsupported symbolic links: {symlinks}")
    scratch = Path(tempfile.mkdtemp(prefix="evoc2rust-evaluation-"))
    project = scratch / "project"

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"target", ".git", ".cargo", "Cargo.lock"}
        }

    shutil.copytree(target, project, ignore=ignore)
    for forbidden in (
        project / "src/oracle",
        project / "src/bin",
        project / "fixed",
        project / ".cargo",
        project / "build.rs",
        project / "rust-toolchain.toml",
    ):
        if forbidden.is_dir():
            shutil.rmtree(forbidden)
        elif forbidden.exists():
            forbidden.unlink()
    for module in contract["modules"]:
        module_path = (
            project / "src/production" / f"{module.replace('-', '_')}.rs"
        )
        if not module_path.is_file():
            raise FileNotFoundError(f"candidate module is absent: {module_path.name}")
    unexpected = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*.rs")
        if not (
            path.parent == project / "src/production"
            and path.stem in {module.replace("-", "_") for module in contract["modules"]}
        )
        and path != project / "src/lib.rs"
    ]
    if unexpected:
        raise ValueError(f"candidate added unsupported Rust surfaces: {unexpected}")

    for source_relative, destination_relative in (
        ("tests/alloc_testing.rs", "src/oracle/alloc_testing.rs"),
        ("tests/framework.rs", "src/oracle/framework.rs"),
        ("tests/fixed_test.rs", "src/oracle/fixed_test.rs"),
    ):
        destination = project / destination_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(contract_dir / source_relative, destination)
    fixed_test_path = project / "src/oracle/fixed_test.rs"
    with fixed_test_path.open("a", encoding="utf-8") as handle:
        handle.write(_dispatch_text(contract))
    support = contract_dir / "support"
    if support.is_dir():
        shutil.copytree(support, project / "fixed/support")
    (project / "src/bin").mkdir(parents=True)
    (project / "Cargo.toml").write_text(_cargo_text(contract), encoding="utf-8")
    shutil.copy2(contract_dir / "Cargo.lock", project / "Cargo.lock")
    (project / "build.rs").write_text(_build_script(contract), encoding="utf-8")
    (project / "src/lib.rs").write_text(_lib_text(contract), encoding="utf-8")
    (project / "src/bin/fixed_contract.rs").write_text(
        _runner_text(contract), encoding="utf-8"
    )
    (project / "rust-toolchain.toml").write_text(
        f'[toolchain]\nchannel = "{contract["rust_toolchain"]}"\n',
        encoding="utf-8",
    )
    return scratch, project, contract


def _mask_comments(text: str) -> str:
    output = list(text)
    index = 0
    depth = 0
    mode = "code"
    raw_closing = ""
    while index < len(output):
        current = output[index]
        following = output[index + 1] if index + 1 < len(output) else ""
        if mode == "code":
            raw = re.match(r"(?:br|rb|r)(#*)\"", text[index:])
            if raw is not None:
                raw_closing = '"' + raw.group(1)
                for offset in range(len(raw.group(0))):
                    output[index + offset] = " "
                index += len(raw.group(0))
                mode = "raw_string"
                continue
            if current == "/" and following == "/":
                output[index] = output[index + 1] = " "
                index += 2
                mode = "line"
                continue
            if current == "/" and following == "*":
                output[index] = output[index + 1] = " "
                index += 2
                depth = 1
                mode = "block"
                continue
            if current == '"':
                output[index] = " "
                index += 1
                mode = "string"
                continue
            if current == "'":
                closing = index + 1
                escaped = False
                while closing < len(output) and text[closing] != "\n":
                    if text[closing] == "'" and not escaped:
                        break
                    escaped = text[closing] == "\\" and not escaped
                    if text[closing] != "\\":
                        escaped = False
                    closing += 1
                if closing < len(output) and text[closing] == "'":
                    output[index] = " "
                    index += 1
                    mode = "character"
                    continue
        if mode == "line":
            if current == "\n":
                mode = "code"
            else:
                output[index] = " "
            index += 1
            continue
        if mode == "block":
            if current == "/" and following == "*":
                output[index] = output[index + 1] = " "
                depth += 1
                index += 2
                continue
            if current == "*" and following == "/":
                output[index] = output[index + 1] = " "
                depth -= 1
                index += 2
                if depth == 0:
                    mode = "code"
                continue
            if current != "\n":
                output[index] = " "
            index += 1
            continue
        if mode in {"string", "character"}:
            closing = '"' if mode == "string" else "'"
            if current == "\\" and following:
                output[index] = output[index + 1] = " "
                index += 2
                continue
            if current == closing:
                output[index] = " "
                mode = "code"
            elif current != "\n":
                output[index] = " "
            index += 1
            continue
        if mode == "raw_string":
            if text.startswith(raw_closing, index):
                for offset in range(len(raw_closing)):
                    output[index + offset] = " "
                index += len(raw_closing)
                mode = "code"
                continue
            if current != "\n":
                output[index] = " "
            index += 1
            continue
        index += 1
    return "".join(output)


def _matching_brace(text: str, opening: int) -> int:
    depth = 1
    cursor = opening + 1
    while cursor < len(text) and depth:
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
        cursor += 1
    if depth:
        raise ValueError("unbalanced unsafe Rust scope")
    return cursor - 1


def unsafe_line_metrics(paths: list[Path]) -> dict[str, Any]:
    total_lines = 0
    unsafe_lines = 0
    unsafe_functions = 0
    unsafe_blocks = 0
    files: dict[str, Any] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        masked = _mask_comments(text)
        code_lines = {
            index + 1
            for index, line in enumerate(masked.splitlines())
            if line.strip()
        }
        unsafe_ranges: list[tuple[int, int]] = []
        claimed_openings: set[int] = set()
        for match in re.finditer(
            r"\bunsafe\s+(?:extern(?:\s+\"[^\"]*\")?\s+)?fn\b", masked
        ):
            opening = masked.find("{", match.end())
            semicolon = masked.find(";", match.end())
            if opening < 0 or (semicolon >= 0 and semicolon < opening):
                continue
            closing = _matching_brace(masked, opening)
            unsafe_ranges.append((match.start(), closing))
            claimed_openings.add(opening)
            unsafe_functions += 1
        for match in re.finditer(r"\bunsafe\s*\{", masked):
            opening = masked.find("{", match.start(), match.end())
            if opening in claimed_openings:
                continue
            closing = _matching_brace(masked, opening)
            unsafe_ranges.append((match.start(), closing))
            unsafe_blocks += 1
        line_starts = [0]
        for match in re.finditer("\n", text):
            line_starts.append(match.end())

        def line_for_offset(offset: int) -> int:
            import bisect

            return bisect.bisect_right(line_starts, offset)

        unsafe_line_numbers: set[int] = set()
        for start, end in unsafe_ranges:
            unsafe_line_numbers.update(
                range(line_for_offset(start), line_for_offset(end) + 1)
            )
        measured_unsafe = len(code_lines & unsafe_line_numbers)
        total_lines += len(code_lines)
        unsafe_lines += measured_unsafe
        files[path.name] = {
            "code_lines": len(code_lines),
            "unsafe_lines": measured_unsafe,
        }
    safe_lines = total_lines - unsafe_lines
    return {
        "total_lines": total_lines,
        "unsafe_lines": unsafe_lines,
        "safe_lines": safe_lines,
        "safe_rate_percent": (
            100.0 * safe_lines / total_lines if total_lines else None
        ),
        "unsafe_functions": unsafe_functions,
        "unsafe_blocks": unsafe_blocks,
        "files": files,
    }


def evaluate_stage(
    stage: str,
    *,
    target: Path,
    contract_dir: Path,
    timeout: float = 5000,
) -> dict[str, Any]:
    if stage == "safety":
        try:
            contract = load_contract(contract_dir)
            paths = [
                target
                / "src/production"
                / f"{module.replace('-', '_')}.rs"
                for module in contract["modules"]
            ]
            if any(not path.is_file() for path in paths):
                raise FileNotFoundError("one or more candidate modules are absent")
            value = unsafe_line_metrics(paths)
            return {
                "stage": stage,
                "ok": True,
                "measurement": measurement("measured", value),
                "commands": [],
            }
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "stage": stage,
                "ok": False,
                "measurement": measurement("error", reason=str(exc)),
                "commands": [],
            }
    try:
        scratch, project, contract = materialize_evaluation_copy(
            target, contract_dir
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "stage": stage,
            "ok": False,
            "measurement": measurement("error", reason=str(exc)),
            "commands": [],
        }
    try:
        if stage == "build":
            result = run_command(
                ["cargo", "build", "--locked", "--all-targets"],
                cwd=project,
                timeout=timeout,
            )
            return {
                "stage": stage,
                "ok": result["ok"],
                "measurement": measurement(
                    "measured",
                    result["ok"],
                    "" if result["ok"] else _reason(result),
                ),
                "commands": [result],
            }
        if stage != "test":
            raise ValueError(f"unknown evaluation stage: {stage}")
        build = run_command(
            ["cargo", "build", "--locked", "--bin", "fixed_contract"],
            cwd=project,
            timeout=timeout,
        )
        if not build["ok"]:
            return {
                "stage": stage,
                "ok": False,
                "measurement": measurement("measured", False, _reason(build)),
                "tests": [],
                "summary": {
                    "expected": len(contract["test_functions"]),
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "not_executed": len(contract["test_functions"]),
                },
                "commands": [build],
            }
        executable = project / "target/debug/fixed_contract"
        tests = []
        per_test_timeout = max(1.0, min(60.0, timeout))
        for name in contract["test_functions"]:
            result = run_command(
                [str(executable), name],
                cwd=project,
                timeout=per_test_timeout,
            )
            tests.append(
                {
                    "name": name,
                    "passed": result["ok"],
                    "returncode": result["returncode"],
                    "timed_out": result["timed_out"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }
            )
        passed = sum(test["passed"] for test in tests)
        expected = len(contract["test_functions"])
        summary = {
            "expected": expected,
            "executed": len(tests),
            "passed": passed,
            "failed": len(tests) - passed,
            "not_executed": expected - len(tests),
        }
        all_passed = passed == expected
        return {
            "stage": stage,
            "ok": all_passed,
            "measurement": measurement(
                "measured",
                all_passed,
                "" if all_passed else f"{passed}/{expected} fixed tests passed",
            ),
            "tests": tests,
            "summary": summary,
            "commands": [build],
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=("build", "test", "safety"), required=True
    )
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
        destination = Path(args.result)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
