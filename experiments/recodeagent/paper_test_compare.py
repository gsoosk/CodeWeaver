"""Paper-aligned RQ2 test-translation comparison.

The lightweight :mod:`test_compare` module is useful without optional
dependencies, but the paper used its artifact's tree-sitter comparator and a
curated test-name inventory.  This module drives that pinned comparator against
CodeWeaver outputs, dynamically remaps its target side, and preserves both
denominators exposed by the artifact:

* 1,472 statically mapped source test methods; and
* 1,484 runtime cases (two Commons CSV parameterized methods expand to seven
  cases each).

It also classifies and independently executes CodeWeaver-authored generated
tests: unmatched executable target tests for the three non-CRUST tools, and
Rust tests/binaries absent from CRUST's immutable scaffold. The same
classification drives paper-equivalent production-line coverage before and
after those generated tests; the official ReCodeAgent generated harness is
kept as a separately labeled standardized metric by :mod:`collect`.

CRUST is intentionally excluded: its Rust tests are benchmark-provided
scaffolding rather than tests translated by the agent.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import ctypes
import gc
import difflib
import importlib.util
import io
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from experiments.recodeagent import common as C
from experiments.recodeagent import collect as COL
from experiments.recodeagent import run as R
from experiments.recodeagent.collect import parse_cargo_test_output, parse_node_tap_output, parse_pytest_output

SCHEMA_VERSION = 1

LANGUAGE_FIELDS = {
    "oxidizer": ("go", "rust"),
    "alphatrans": ("java", "python"),
    "skel": ("python", "javascript"),
}
LANGUAGE_EXTENSIONS = {
    "go": (".go",),
    "java": (".java",),
    "python": (".py",),
    "rust": (".rs",),
    "javascript": (".js", ".mjs", ".cjs"),
}
PARSER_CLASSES = {
    "go": "GoTestParser",
    "java": "JavaTestParser",
    "python": "PythonTestParser",
    "rust": "RustTestParser",
    "javascript": "JavaScriptTestParser",
}

# Table 2's project-level runtime inventory from results.xlsx.  The matching
# CSV artifacts contain 1,472 static methods; Commons CSV contributes the only
# expansion (two methods x seven runtime cases rather than two static methods).
PAPER_RUNTIME_COUNTS = dict(C.PAPER_RUNTIME_TESTS_BY_PROJECT)
PAPER_STATIC_COUNTS = {
    key: (286 if key == ("alphatrans", "commons-csv") else value)
    for key, value in PAPER_RUNTIME_COUNTS.items()
}
PARAMETERIZED_RUNTIME_WEIGHTS = {
    (
        "alphatrans",
        "commons-csv",
        "org.apache.commons.csv.CSVFileParserTest",
        "testCSVFile",
    ): 7,
    (
        "alphatrans",
        "commons-csv",
        "org.apache.commons.csv.CSVFileParserTest",
        "testCSVUrl",
    ): 7,
}
SUPERCLASS_MAPS = {
    ("alphatrans", "commons-cli"): {
        "BasicParserTest": "ParserTestCase",
        "DefaultParserTest": "ParserTestCase",
        "GnuParserTest": "ParserTestCase",
        "PosixParserTest": "ParserTestCase",
    },
    ("alphatrans", "commons-validator"): {
        **{
            name: "AbstractNumberValidatorTest"
            for name in (
                "BigDecimalValidatorTest",
                "BigIntegerValidatorTest",
                "ByteValidatorTest",
                "DoubleValidatorTest",
                "FloatValidatorTest",
                "IntegerValidatorTest",
                "LongValidatorTest",
                "ShortValidatorTest",
            )
        },
        **{
            name: "AbstractCalendarValidatorTest"
            for name in ("CalendarValidatorTest", "DateValidatorTest")
        },
        **{
            name: "AbstractCheckDigitTest"
            for name in (
                "ABANumberCheckDigitTest",
                "CUSIPCheckDigitTest",
                "EAN13CheckDigitTest",
                "IBANCheckDigitTest",
                "ISBN10CheckDigitTest",
                "ISBNCheckDigitTest",
                "ISINCheckDigitTest",
                "ISSNCheckDigitTest",
                "LuhnCheckDigitTest",
                "ModulusTenABACheckDigitTest",
                "ModulusTenCUSIPCheckDigitTest",
                "ModulusTenEAN13CheckDigitTest",
                "ModulusTenLuhnCheckDigitTest",
                "ModulusTenSedolCheckDigitTest",
                "SedolCheckDigitTest",
                "VerhoeffCheckDigitTest",
            )
        },
    },
}
IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "target",
}


@dataclass(frozen=True)
class TargetTest:
    path: str
    name: str


@dataclass(frozen=True)
class GeneratedTestExecution:
    expected: C.Measurement
    executed: C.Measurement
    passed: C.Measurement
    failed: C.Measurement
    not_executed: C.Measurement

    def flatten(self) -> dict[str, Any]:
        row: dict[str, Any] = {}
        for key in ("expected", "executed", "passed", "failed", "not_executed"):
            row.update(getattr(self, key).flatten(f"generated_tests_{key}"))
        if self.expected.is_measured and self.expected.value:
            passed = int(self.passed.value) if self.passed.is_measured else 0
            row.update(C.Measurement.ok(passed / int(self.expected.value)).flatten(
                "generated_tests_pass_rate"
            ))
        elif self.expected.is_measured and self.expected.value == 0:
            row.update(C.Measurement.na(
                "no CodeWeaver-authored generated tests were discovered"
            ).flatten("generated_tests_pass_rate"))
        else:
            row.update(C.Measurement.unavailable(
                "generated-test expected count is unavailable"
            ).flatten("generated_tests_pass_rate"))
        return row


def _generated_execution(
    expected: int,
    executed: int,
    passed: int,
    failed: int,
    *,
    reason: str = "",
) -> GeneratedTestExecution:
    return GeneratedTestExecution(
        expected=C.Measurement(value=expected, status=C.Status.MEASURED, reason=reason),
        executed=C.Measurement(value=executed, status=C.Status.MEASURED, reason=reason),
        passed=C.Measurement(value=passed, status=C.Status.MEASURED, reason=reason),
        failed=C.Measurement(value=failed, status=C.Status.MEASURED, reason=reason),
        not_executed=C.Measurement(
            value=max(0, expected - executed), status=C.Status.MEASURED, reason=reason
        ),
    )


def _generated_unavailable(reason: str, *, status: str = C.Status.UNAVAILABLE) -> GeneratedTestExecution:
    measurement = C.Measurement(value=None, status=status, reason=reason)
    return GeneratedTestExecution(
        expected=measurement,
        executed=measurement,
        passed=measurement,
        failed=measurement,
        not_executed=measurement,
    )


def _tail(value: str, limit: int = 500) -> str:
    return (value or "").strip()[-limit:]


def _is_executable_test_name(language: str, name: str) -> bool:
    if language in {"python", "javascript"}:
        return _normalize_name(name).startswith("test")
    return True


def filter_generated_target_tests(
    generated: list[TargetTest], target_language: str,
) -> list[TargetTest]:
    """Discard parser-visible helpers that the target test runner cannot run."""
    seen: set[tuple[str, str]] = set()
    selected: list[TargetTest] = []
    for item in generated:
        key = (item.path, item.name)
        if key in seen or not _is_executable_test_name(target_language, item.name):
            continue
        seen.add(key)
        selected.append(item)
    return selected


def _pytest_nodeids(text: str) -> list[str]:
    nodeids: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if ".py::" not in line or line.startswith(("ERROR ", "WARNING ")):
            continue
        nodeid = line.split(" ", 1)[0]
        if nodeid.endswith(":"):
            continue
        nodeids.append(nodeid)
    return nodeids


def _evaluate_python_generated(
    target_root: Path, generated: list[TargetTest], *, timeout: float,
) -> GeneratedTestExecution:
    if not target_root.is_dir():
        return _generated_unavailable("CodeWeaver target directory is missing", status=C.Status.MISSING)
    if not generated:
        return _generated_execution(0, 0, 0, 0)

    by_path: dict[str, list[TargetTest]] = {}
    for item in generated:
        by_path.setdefault(item.path, []).append(item)
    expected = 0
    executed = passed = failed = 0
    blocked: list[str] = []
    for relative_path, items in sorted(by_path.items()):
        collect_result = C.run_argv(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", relative_path],
            cwd=target_root,
            timeout=timeout,
        )
        nodeids = _pytest_nodeids(f"{collect_result.stdout}\n{collect_result.stderr}")
        selected: list[str] = []
        for item in items:
            matches = [
                nodeid for nodeid in nodeids
                if _normalize_path(nodeid.split("::", 1)[0]) == _normalize_path(item.path)
                and _normalize_name(nodeid.rsplit("::", 1)[-1].split("[", 1)[0])
                == _normalize_name(item.name)
            ]
            if matches:
                selected.extend(matches)
                expected += len(matches)
            else:
                expected += 1
                blocked.append(f"{item.path}::{item.name}: not collected")
        selected = sorted(set(selected))
        if not selected:
            detail = collect_result.error or _tail(collect_result.stderr)
            if detail:
                blocked.append(f"{relative_path}: {detail}")
            continue
        result = C.run_argv(
            [sys.executable, "-m", "pytest", "-q", *selected],
            cwd=target_root,
            timeout=timeout,
        )
        parsed = parse_pytest_output(result.stdout, result.stderr)
        if parsed is None:
            blocked.append(
                f"{relative_path}: "
                + ("timed out" if result.timed_out else (result.error or _tail(result.stderr) or
                                                         f"exit code {result.returncode}"))
            )
            continue
        executed += int(parsed["total"])
        passed += int(parsed["passed"])
        failed += int(parsed["failed"])
    reason = "; ".join(blocked[:10])
    return _generated_execution(expected, executed, passed, failed, reason=reason)


def _cargo_target_args(relative_path: str) -> tuple[str, ...]:
    path = Path(relative_path)
    parts = path.parts
    if parts and parts[0] == "tests":
        return ("cargo", "test", "--test", path.stem)
    if len(parts) >= 3 and parts[0] == "src" and parts[1] == "bin":
        return ("cargo", "test", "--bin", path.stem)
    return ("cargo", "test", "--lib")


def _cargo_listed_tests(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"(?m)^(.+?): test\s*$", text)
    ]


def _evaluate_rust_generated(
    target_root: Path, generated: list[TargetTest], *, timeout: float,
) -> GeneratedTestExecution:
    if not target_root.is_dir():
        return _generated_unavailable("CodeWeaver target directory is missing", status=C.Status.MISSING)
    if not generated:
        return _generated_execution(0, 0, 0, 0)

    binary_items = [item for item in generated if item.name.startswith("__binary__:")]
    test_items = [item for item in generated if not item.name.startswith("__binary__:")]
    expected = len(generated)
    executed = passed = failed = 0
    blocked: list[str] = []

    by_target: dict[tuple[str, ...], list[TargetTest]] = {}
    for item in test_items:
        by_target.setdefault(_cargo_target_args(item.path), []).append(item)
    for base, items in sorted(by_target.items()):
        listed_result = C.run_argv([*base, "--", "--list"], cwd=target_root, timeout=timeout)
        listed = _cargo_listed_tests(f"{listed_result.stdout}\n{listed_result.stderr}")
        selected: set[str] = set()
        for item in items:
            matches = [
                name for name in listed
                if _normalize_name(name.rsplit("::", 1)[-1]) == _normalize_name(item.name)
            ]
            if len(matches) == 1:
                selected.add(matches[0])
            elif not matches:
                blocked.append(f"{item.path}::{item.name}: not listed by cargo")
            else:
                blocked.append(f"{item.path}::{item.name}: ambiguous cargo test name")
        if not selected:
            detail = listed_result.error or _tail(listed_result.stderr)
            if detail:
                blocked.append(f"{' '.join(base)}: {detail}")
            continue
        nonselected = [name for name in listed if name not in selected]
        argv = [*base, "--", "--test-threads=1"]
        for name in nonselected:
            argv.extend(["--skip", name])
        result = C.run_argv(argv, cwd=target_root, timeout=timeout)
        parsed = parse_cargo_test_output(result.stdout, result.stderr)
        if parsed is not None and int(parsed["total"]) == len(selected):
            executed += int(parsed["total"])
            passed += int(parsed["passed"])
            failed += int(parsed["failed"])
            continue

        # A substring-based --skip can collide with a generated test name.
        # Fall back to exact one-test invocations rather than attributing a
        # translated test's result to the generated subset.
        for name in sorted(selected):
            one = C.run_argv(
                [*base, name, "--", "--exact", "--test-threads=1"],
                cwd=target_root,
                timeout=timeout,
            )
            one_parsed = parse_cargo_test_output(one.stdout, one.stderr)
            if one_parsed is None or int(one_parsed["total"]) != 1:
                blocked.append(
                    f"{' '.join(base)} {name}: "
                    + ("timed out" if one.timed_out else (one.error or _tail(one.stderr) or
                                                          f"exit code {one.returncode}"))
                )
                continue
            executed += 1
            passed += int(one_parsed["passed"])
            failed += int(one_parsed["failed"])

    for item in binary_items:
        binary_name = item.name.split(":", 1)[1]
        result = C.run_argv(
            ["cargo", "run", "--quiet", "--bin", binary_name],
            cwd=target_root,
            timeout=timeout,
        )
        if result.timed_out or result.error:
            blocked.append(f"{item.path}: {result.error or 'timed out'}")
            continue
        executed += 1
        if result.returncode == 0:
            passed += 1
        else:
            failed += 1
    return _generated_execution(
        expected, executed, passed, failed, reason="; ".join(blocked[:10])
    )


def _javascript_module_type(target_root: Path) -> str:
    package = target_root / "package.json"
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "commonjs"
    return "module" if data.get("type") == "module" else "commonjs"


def _evaluate_javascript_generated(
    target_root: Path, generated: list[TargetTest], *, timeout: float,
) -> GeneratedTestExecution:
    if not target_root.is_dir():
        return _generated_unavailable("CodeWeaver target directory is missing", status=C.Status.MISSING)
    if not generated:
        return _generated_execution(0, 0, 0, 0)

    expected = len(generated)
    executed = passed = failed = 0
    blocked: list[str] = []
    by_path: dict[str, list[TargetTest]] = {}
    for item in generated:
        by_path.setdefault(item.path, []).append(item)
    module_type = _javascript_module_type(target_root)

    for relative_path, items in sorted(by_path.items()):
        if any(not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", item.name) for item in items):
            blocked.extend(
                f"{item.path}::{item.name}: not a callable JavaScript identifier"
                for item in items
            )
            continue
        with tempfile.TemporaryDirectory(prefix="codeweaver_generated_js_") as tmp:
            staged = Path(tmp) / "target"
            shutil.copytree(target_root, staged)
            test_file = staged / relative_path
            try:
                source = test_file.read_text(encoding="utf-8")
            except OSError as exc:
                blocked.append(f"{relative_path}: {exc}")
                continue
            aliases = [f"__codeweaver_generated_{index}" for index in range(len(items))]
            if module_type == "module":
                exports = ", ".join(
                    f"{item.name} as {alias}" for item, alias in zip(items, aliases)
                )
                source += f"\nexport {{ {exports} }};\n"
            else:
                source += "\n" + "\n".join(
                    f"module.exports[{json.dumps(alias)}] = {item.name};"
                    for item, alias in zip(items, aliases)
                ) + "\n"
            test_file.write_text(source, encoding="utf-8")
            import_path = "./" + Path(relative_path).as_posix()
            harness = staged / "__codeweaver_generated_tests.mjs"
            entries = ", ".join(
                f"[{json.dumps(item.name)}, {json.dumps(alias)}]"
                for item, alias in zip(items, aliases)
            )
            harness.write_text(
                "\n".join([
                    f"const loaded = await import({json.dumps(import_path)});",
                    "const target = { ...(loaded.default || {}), ...loaded };",
                    f"const tests = [{entries}];",
                    "let passed = 0, failed = 0;",
                    "for (const [name, alias] of tests) {",
                    "  try {",
                    "    const fn = target[alias];",
                    "    if (typeof fn !== 'function') throw new Error('test function not exported');",
                    "    const value = await fn();",
                    "    if (value === false) throw new Error('test returned false');",
                    "    passed += 1;",
                    "  } catch (error) {",
                    "    failed += 1;",
                    "    console.log('FAIL ' + name + ': ' + (error && error.message || error));",
                    "  }",
                    "}",
                    "console.log('# pass ' + passed);",
                    "console.log('# fail ' + failed);",
                ]) + "\n",
                encoding="utf-8",
            )
            result = C.run_argv(["node", harness.name], cwd=staged, timeout=timeout)
            parsed = parse_node_tap_output(result.stdout, result.stderr)
            if parsed is None:
                blocked.append(
                    f"{relative_path}: "
                    + ("timed out" if result.timed_out else (result.error or _tail(result.stderr) or
                                                             f"exit code {result.returncode}"))
                )
                continue
            executed += int(parsed["total"])
            passed += int(parsed["passed"])
            failed += int(parsed["failed"])
    return _generated_execution(
        expected, executed, passed, failed, reason="; ".join(blocked[:10])
    )


def evaluate_codeweaver_generated_tests(
    tool: str,
    target_root: Path,
    generated: list[TargetTest],
    *,
    timeout: float = 300,
) -> GeneratedTestExecution:
    if tool == "alphatrans":
        return _evaluate_python_generated(target_root, generated, timeout=timeout)
    if tool in {"oxidizer", "crust"}:
        return _evaluate_rust_generated(target_root, generated, timeout=timeout)
    if tool == "skel":
        return _evaluate_javascript_generated(target_root, generated, timeout=timeout)
    return _generated_unavailable(f"no generated-test execution adapter for {tool}")


def evaluate_codeweaver_generated_coverage(
    tool: str,
    run_dir: Path,
    manifest_row: dict[str, Any],
    reference_results_root: Path,
    generated: list[TargetTest],
    *,
    timeout: float = 300,
) -> tuple[C.Measurement, C.Measurement]:
    """Developer-oracle coverage before/after only the classified generated
    tests for this CodeWeaver target."""
    project = _project_name(manifest_row)
    ref_project_dir = (
        None
        if tool == "crust"
        else COL.reference_project_dir(reference_results_root, tool, project)
    )
    return COL.codeweaver_generated_coverage_pair(
        tool,
        run_dir / "pipeline" / "target",
        [(item.path, item.name) for item in generated],
        ref_project_dir=ref_project_dir,
        scaffold_dir=run_dir / "scaffold",
        name_mapping=COL.read_name_mapping(run_dir),
        timeout=timeout,
    )


def discover_crust_generated_tests(
    official: Any, run_dir: Path,
) -> list[TargetTest]:
    """Find target Rust tests/binaries absent from CRUST's given scaffold."""
    target_root = run_dir / "pipeline" / "target"
    scaffold_root = run_dir / "scaffold"
    target_tests = discover_target_tests(official, target_root, "rust")
    scaffold_tests = discover_target_tests(official, scaffold_root, "rust")
    scaffold_keys = {
        (_normalize_path(item.path), _normalize_name(item.name))
        for item in scaffold_tests
    }
    generated = [
        item for item in target_tests
        if (_normalize_path(item.path), _normalize_name(item.name)) not in scaffold_keys
    ]

    generated_paths = {_normalize_path(item.path) for item in generated}
    target_bins = target_root / "src" / "bin"
    scaffold_bins = scaffold_root / "src" / "bin"
    if target_bins.is_dir():
        for path in sorted(target_bins.glob("*.rs")):
            relative = path.relative_to(target_root).as_posix()
            if (scaffold_bins / path.name).is_file() or _normalize_path(relative) in generated_paths:
                continue
            generated.append(TargetTest(relative, f"__binary__:{path.stem}"))
    return generated


GENERATED_PROJECT_COLUMNS = [
    "variant", "repetition", "project_id", "tool", "project",
    "generated_target_test_methods",
    "generated_tests_expected", "generated_tests_expected_status", "generated_tests_expected_reason",
    "generated_tests_executed", "generated_tests_executed_status", "generated_tests_executed_reason",
    "generated_tests_passed", "generated_tests_passed_status", "generated_tests_passed_reason",
    "generated_tests_failed", "generated_tests_failed_status", "generated_tests_failed_reason",
    "generated_tests_not_executed", "generated_tests_not_executed_status",
    "generated_tests_not_executed_reason",
    "generated_tests_pass_rate", "generated_tests_pass_rate_status", "generated_tests_pass_rate_reason",
    "coverage_before", "coverage_before_status", "coverage_before_reason",
    "coverage_after", "coverage_after_status", "coverage_after_reason",
]


def generated_project_row(
    *,
    variant: str,
    repetition: int,
    manifest_row: dict[str, Any],
    generated: list[TargetTest],
    execution: GeneratedTestExecution,
    coverage_before: C.Measurement,
    coverage_after: C.Measurement,
) -> dict[str, Any]:
    return {
        "variant": variant,
        "repetition": repetition,
        "project_id": str(manifest_row["id"]),
        "tool": str(manifest_row["tool"]).lower(),
        "project": _project_name(manifest_row),
        "generated_target_test_methods": len(generated),
        **execution.flatten(),
        **coverage_before.flatten("coverage_before"),
        **coverage_after.flatten("coverage_after"),
    }


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_path(value: str) -> str:
    value = value.replace("\\", "/").lower()
    value = re.sub(r"(^|/)(src/)?test/(python/|java/)?", "/", value)
    return re.sub(r"[^a-z0-9/]", "", value)


def _project_name(manifest_row: dict[str, Any]) -> str:
    return str(manifest_row.get("project") or manifest_row["id"].split("__", 1)[-1])


def runtime_weight(tool: str, project: str, source_path: str, source_name: str) -> int:
    return PARAMETERIZED_RUNTIME_WEIGHTS.get((tool, project, source_path, source_name), 1)


def _target_score(expected_path: str, expected_name: str, candidate: TargetTest) -> float:
    expected_norm = _normalize_name(expected_name)
    candidate_norm = _normalize_name(candidate.name)
    if not expected_norm or not candidate_norm:
        return 0.0
    name_score = difflib.SequenceMatcher(None, expected_norm, candidate_norm).ratio()
    if expected_norm == candidate_norm:
        name_score = 1.0
    path_score = (
        difflib.SequenceMatcher(
            None, _normalize_path(expected_path), _normalize_path(candidate.path)
        ).ratio()
        if expected_path
        else 0.0
    )
    return 0.88 * name_score + 0.12 * path_score


def map_reference_rows(
    rows: list[dict[str, str]],
    candidates: list[TargetTest],
    *,
    source_language: str,
    target_language: str,
    minimum_score: float = 0.55,
) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[TargetTest]]:
    """Map the artifact's source inventory onto tests found in one CW target."""
    source_path_key = f"{source_language} test path"
    source_name_key = f"{source_language} test name"
    target_path_key = f"{target_language} test path"
    target_name_key = f"{target_language} test name"

    scored: list[tuple[float, int, int]] = []
    for row_index, row in enumerate(rows):
        expected_name = row.get(target_name_key) or row.get(source_name_key, "")
        expected_path = row.get(target_path_key, "")
        for candidate_index, candidate in enumerate(candidates):
            score = _target_score(expected_path, expected_name, candidate)
            if score >= minimum_score:
                scored.append((score, row_index, candidate_index))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))

    assignments: dict[int, tuple[int, float]] = {}
    used_candidates: set[int] = set()
    for score, row_index, candidate_index in scored:
        if row_index in assignments or candidate_index in used_candidates:
            continue
        assignments[row_index] = (candidate_index, score)
        used_candidates.add(candidate_index)

    mapped_rows: list[dict[str, str]] = []
    metadata: list[dict[str, Any]] = []
    for row_index, original in enumerate(rows):
        row = dict(original)
        assignment = assignments.get(row_index)
        if assignment is None:
            row[target_path_key] = ""
            row[target_name_key] = ""
            mapped = False
            score = None
            target_path = None
            target_name = None
        else:
            candidate_index, score = assignment
            candidate = candidates[candidate_index]
            row[target_path_key] = candidate.path
            row[target_name_key] = candidate.name
            mapped = True
            target_path = candidate.path
            target_name = candidate.name
        mapped_rows.append(row)
        metadata.append(
            {
                "source_path": row.get(source_path_key, ""),
                "source_name": row.get(source_name_key, ""),
                "target_path": target_path,
                "target_name": target_name,
                "mapped": mapped,
                "mapping_score": score,
            }
        )

    generated = [
        candidate for index, candidate in enumerate(candidates) if index not in used_candidates
    ]
    return mapped_rows, metadata, generated


def _load_official_module(implementation_root: Path):
    path = implementation_root / "src" / "analysis" / "compare_tests.py"
    if not path.is_file():
        raise FileNotFoundError(f"official comparator not found: {path}")
    spec = importlib.util.spec_from_file_location("recodeagent_official_compare_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load official comparator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _parser_for(official: Any, language: str):
    return getattr(official, PARSER_CLASSES[language])()


def discover_target_tests(
    official: Any, target_root: Path, target_language: str
) -> list[TargetTest]:
    parser = _parser_for(official, target_language)
    extensions = LANGUAGE_EXTENSIONS[target_language]
    found: list[TargetTest] = []
    if not target_root.is_dir():
        return found
    for path in sorted(target_root.rglob("*")):
        if (
            not path.is_file()
            or path.suffix.lower() not in extensions
            or any(part in IGNORED_PARTS for part in path.relative_to(target_root).parts)
        ):
            continue
        methods = parser.parse_test_file(path)
        rel = path.relative_to(target_root).as_posix()
        found.extend(TargetTest(rel, name) for name in sorted(methods))
    return found


def exclude_uninventoried_source_tests(
    generated: list[TargetTest], source_candidates: list[TargetTest]
) -> list[TargetTest]:
    """Do not call source-side helpers/orchestrators generated target tests."""
    source_names = {_normalize_name(item.name) for item in source_candidates}
    return [
        item for item in generated if _normalize_name(item.name) not in source_names
    ]


def _reference_mapping_path(
    reference_results_root: Path, tool: str, project: str
) -> Path:
    return (
        reference_results_root
        / "recodeagent_translations"
        / "data"
        / "tool_projects"
        / tool
        / project
        / "test_name_mapping.csv"
    )


def _source_base(run_dir: Path, tool: str) -> Path:
    if tool == "alphatrans":
        return run_dir / "source" / "src" / "test" / "java"
    return run_dir / "source"


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    C.atomic_write_text(path, buf.getvalue())


def _run_official_comparator(
    official: Any,
    *,
    mapping_path: Path,
    source_base: Path,
    target_base: Path,
    source_language: str,
    target_language: str,
    superclass_map: dict[str, str],
    report_path: Path,
) -> dict[str, Any]:
    comparator = official.TestComparator(
        mapping_path,
        source_base,
        target_base,
        superclass_map=superclass_map,
        compute_similarity=False,
    )
    # The official detector relies mostly on directory names.  Run trees use
    # neutral source/target names, so set both languages and parsers explicitly.
    comparator.source_lang = source_language
    comparator.target_lang = target_language
    comparator.source_parser = _parser_for(official, source_language)
    comparator.target_parser = _parser_for(official, target_language)
    comparator.compare_all_tests()
    comparator.generate_json_report(report_path)
    return json.loads(report_path.read_text(encoding="utf-8"))


def _body_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def add_batched_embeddings(
    report: dict[str, Any],
    model: Any,
    *,
    batch_size: int,
) -> None:
    pairs: list[dict[str, Any]] = []
    texts: list[str] = []
    for pair in report.get("test_pairs", []):
        source = _body_text(pair.get("source_test", {}).get("body"))
        target = _body_text(pair.get("target_test", {}).get("body"))
        if not source or not target:
            continue
        pairs.append(pair)
        texts.extend((source, target))
    if not texts:
        report.setdefault("summary", {})["embedding_similarity_status"] = "unavailable"
        return
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    scores: list[float] = []
    for index, pair in enumerate(pairs):
        a = vectors[2 * index]
        b = vectors[2 * index + 1]
        score = float(sum(float(x) * float(y) for x, y in zip(a, b)))
        pair.setdefault("metrics", {})["similarity_score"] = round(score, 6)
        scores.append(score)
    summary = report.setdefault("summary", {})
    summary["embedding_similarity_status"] = "measured"
    summary["avg_similarity_score"] = round(sum(scores) / len(scores), 6)
    summary["min_similarity_score"] = round(min(scores), 6)
    summary["max_similarity_score"] = round(max(scores), 6)
    summary["embedding_similarity_count"] = len(scores)


def release_embedding_working_memory() -> None:
    """Release large per-project CPU tensors before the next project."""
    gc.collect()
    with contextlib.suppress(AttributeError, OSError):
        ctypes.CDLL(None).malloc_trim(0)


def _assertion_type_group_counts(
    summary: dict[str, Any], *, tool: str | None = None,
) -> dict[str, tuple[int, int]]:
    """Collapse the official comparator's assertion names into Table 2 groups."""
    raw = summary.get("assertion_match_percentages") or {}
    grouped = {
        "assert_equal": [0, 0],
        "assert_true": [0, 0],
        "assert_false": [0, 0],
        "other": [0, 0],
    }
    for source_type, values in raw.items():
        if not isinstance(values, dict):
            continue
        normalized = _normalize_name(str(source_type))
        if tool in {"oxidizer", "skel"}:
            group = "assert_equal"
        elif "false" in normalized:
            group = "assert_false"
        elif "true" in normalized:
            group = "assert_true"
        elif "equal" in normalized or normalized in {"asserteq", "assert"}:
            group = "assert_equal"
        else:
            group = "other"
        grouped[group][0] += int(values.get("good_match_count") or 0)
        grouped[group][1] += int(values.get("total_source") or 0)
    return {key: (value[0], value[1]) for key, value in grouped.items()}


def _runtime_assertion_match_counts(
    metadata: list[dict[str, Any]], report: dict[str, Any],
) -> tuple[int, int]:
    matched = 0
    mismatched = 0
    pairs = report.get("test_pairs") or []
    for index, item in enumerate(metadata):
        weight = int(item.get("runtime_weight") or 1)
        pair = pairs[index] if index < len(pairs) and isinstance(pairs[index], dict) else {}
        is_match = (pair.get("metrics") or {}).get("assertions_match")
        if is_match is True:
            matched += weight
        else:
            mismatched += weight
    return matched, mismatched


def _project_summary(
    *,
    variant: str,
    repetition: int,
    project_id: str,
    tool: str,
    project: str,
    metadata: list[dict[str, Any]],
    generated: list[TargetTest],
    generated_execution: GeneratedTestExecution,
    report: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    source_language, _target_language = LANGUAGE_FIELDS[tool]
    for item in metadata:
        item["runtime_weight"] = runtime_weight(
            tool, project, item["source_path"], item["source_name"]
        )
    mapped_static = sum(bool(item["mapped"]) for item in metadata)
    mapped_runtime = sum(
        int(item["runtime_weight"]) for item in metadata if item["mapped"]
    )
    runtime_total = PAPER_RUNTIME_COUNTS[(tool, project)]
    summary = report.get("summary", {})
    assert_equal = summary.get("assertEquals_summary", {})
    assertion_groups = _assertion_type_group_counts(summary, tool=tool)
    assertion_runtime_match, assertion_runtime_mismatch = _runtime_assertion_match_counts(
        metadata, report
    )
    return {
        "variant": variant,
        "repetition": repetition,
        "project_id": project_id,
        "tool": tool,
        "project": project,
        "source_language": source_language,
        "paper_runtime_tests": runtime_total,
        "static_source_methods": len(metadata),
        "parameterized_expansion_cases": runtime_total - len(metadata),
        "mapped_static_methods": mapped_static,
        "not_mapped_static_methods": len(metadata) - mapped_static,
        "mapped_runtime_cases": mapped_runtime,
        "not_mapped_runtime_cases": runtime_total - mapped_runtime,
        "runtime_translation_rate": mapped_runtime / runtime_total if runtime_total else None,
        "generated_target_test_methods": len(generated),
        **generated_execution.flatten(),
        "both_ast_methods_found": summary.get("both_found"),
        "source_ast_methods_missing": summary.get("source_missing"),
        "target_ast_methods_missing": summary.get("target_missing"),
        "assertion_count_matches": summary.get("assertions_match_count"),
        "assertion_count_mismatches": summary.get("assertions_mismatch_count"),
        "assertion_count_runtime_matches": assertion_runtime_match,
        "assertion_count_runtime_mismatches": assertion_runtime_mismatch,
        "assert_equal_comparable": assert_equal.get("total_comparable_pairs"),
        "assert_equal_matching": assert_equal.get("total_matching_assertions"),
        "assert_equal_match_rate": assert_equal.get("overall_match_rate"),
        "assert_equal_type_good": assertion_groups["assert_equal"][0],
        "assert_equal_type_total": assertion_groups["assert_equal"][1],
        "assert_true_type_good": assertion_groups["assert_true"][0],
        "assert_true_type_total": assertion_groups["assert_true"][1],
        "assert_false_type_good": assertion_groups["assert_false"][0],
        "assert_false_type_total": assertion_groups["assert_false"][1],
        "other_type_good": assertion_groups["other"][0],
        "other_type_total": assertion_groups["other"][1],
        "avg_cosine_similarity": summary.get("avg_similarity_score"),
        "embedding_similarity_count": summary.get("embedding_similarity_count"),
        "avg_source_loc": summary.get("avg_line_count_source"),
        "avg_target_loc": summary.get("avg_line_count_target"),
        "avg_source_method_calls": summary.get("avg_method_calls_source"),
        "avg_target_method_calls": summary.get("avg_method_calls_target"),
        "report_path": str(report_path),
    }


def compare_project(
    official: Any,
    *,
    run_dir: Path,
    variant: str,
    repetition: int,
    manifest_row: dict[str, Any],
    reference_results_root: Path,
    output_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[TargetTest], Path]:
    project_id = str(manifest_row["id"])
    tool = str(manifest_row["tool"]).lower()
    project = _project_name(manifest_row)
    source_language, target_language = LANGUAGE_FIELDS[tool]
    reference_mapping = _reference_mapping_path(reference_results_root, tool, project)
    if not reference_mapping.is_file():
        raise FileNotFoundError(f"reference test mapping not found: {reference_mapping}")
    with reference_mapping.open(newline="", encoding="utf-8") as handle:
        reference_rows = list(csv.DictReader(handle))
        columns = list(reference_rows[0]) if reference_rows else []

    source_root = _source_base(run_dir, tool)
    target_root = run_dir / "pipeline" / "target"
    candidates = discover_target_tests(official, target_root, target_language)
    mapped_rows, metadata, generated = map_reference_rows(
        reference_rows,
        candidates,
        source_language=source_language,
        target_language=target_language,
    )
    source_candidates = discover_target_tests(official, source_root, source_language)
    generated = exclude_uninventoried_source_tests(generated, source_candidates)
    generated = filter_generated_target_tests(generated, target_language)
    project_output = output_root / variant / project_id / f"rep{repetition}"
    project_output.mkdir(parents=True, exist_ok=True)
    mapping_path = project_output / "codeweaver_test_name_mapping.csv"
    _write_csv(mapping_path, mapped_rows, columns)
    C.atomic_write_json(
        project_output / "mapping_metadata.json",
        {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "paper_runtime_tests": PAPER_RUNTIME_COUNTS[(tool, project)],
            "static_source_methods": len(metadata),
            "mappings": metadata,
            "generated_target_tests": [
                {"path": item.path, "name": item.name} for item in generated
            ],
        },
    )
    report_path = project_output / "test_comparison_report.json"
    report = _run_official_comparator(
        official,
        mapping_path=mapping_path,
        source_base=source_root,
        target_base=target_root,
        source_language=source_language,
        target_language=target_language,
        superclass_map=SUPERCLASS_MAPS.get((tool, project), {}),
        report_path=report_path,
    )
    return report, metadata, generated, report_path


PROJECT_COLUMNS = [
    "variant",
    "repetition",
    "project_id",
    "tool",
    "project",
    "source_language",
    "paper_runtime_tests",
    "static_source_methods",
    "parameterized_expansion_cases",
    "mapped_static_methods",
    "not_mapped_static_methods",
    "mapped_runtime_cases",
    "not_mapped_runtime_cases",
    "runtime_translation_rate",
    "generated_target_test_methods",
    "generated_tests_expected",
    "generated_tests_expected_status",
    "generated_tests_expected_reason",
    "generated_tests_executed",
    "generated_tests_executed_status",
    "generated_tests_executed_reason",
    "generated_tests_passed",
    "generated_tests_passed_status",
    "generated_tests_passed_reason",
    "generated_tests_failed",
    "generated_tests_failed_status",
    "generated_tests_failed_reason",
    "generated_tests_not_executed",
    "generated_tests_not_executed_status",
    "generated_tests_not_executed_reason",
    "generated_tests_pass_rate",
    "generated_tests_pass_rate_status",
    "generated_tests_pass_rate_reason",
    "both_ast_methods_found",
    "source_ast_methods_missing",
    "target_ast_methods_missing",
    "assertion_count_matches",
    "assertion_count_mismatches",
    "assertion_count_runtime_matches",
    "assertion_count_runtime_mismatches",
    "assert_equal_comparable",
    "assert_equal_matching",
    "assert_equal_match_rate",
    "assert_equal_type_good",
    "assert_equal_type_total",
    "assert_true_type_good",
    "assert_true_type_total",
    "assert_false_type_good",
    "assert_false_type_total",
    "other_type_good",
    "other_type_total",
    "avg_cosine_similarity",
    "embedding_similarity_count",
    "avg_source_loc",
    "avg_target_loc",
    "avg_source_method_calls",
    "avg_target_method_calls",
    "report_path",
]
FAILURE_COLUMNS = [
    "variant",
    "repetition",
    "project_id",
    "tool",
    "reason",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the paper's AST-based RQ2 protocol on CodeWeaver outputs."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--reference-results-root", required=True)
    parser.add_argument("--reference-implementation-root", required=True)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--project", default=None, help="comma-separated project ids")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--embedding-model", default="Qwen/Qwen3-Embedding-0.6B")
    parser.add_argument("--embedding-batch-size", type=int, default=8)
    parser.add_argument("--generated-test-timeout", type=float, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = C.read_json(args.manifest)
    official = _load_official_module(Path(args.reference_implementation_root))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    model = None
    if args.embeddings:
        sentence_transformers = C.optional_import("sentence_transformers")
        if sentence_transformers is None:
            raise RuntimeError("--embeddings requires sentence-transformers")
        model = sentence_transformers.SentenceTransformer(
            args.embedding_model, trust_remote_code=True
        )

    project_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    generated_rows: list[dict[str, Any]] = []
    generated_failures: list[dict[str, Any]] = []
    variants = [item.strip() for item in args.variant.split(",") if item.strip()]
    all_projects = list(manifest.get("projects", []))
    if args.project:
        selected = {item.strip() for item in args.project.split(",") if item.strip()}
        all_projects = [row for row in all_projects if str(row["id"]) in selected]
    projects = [
        row for row in all_projects
        if str(row.get("tool", "")).lower() in LANGUAGE_FIELDS
    ]
    crust_projects = [
        row for row in all_projects
        if str(row.get("tool", "")).lower() == "crust"
    ]
    for variant in variants:
        for manifest_row in projects:
            project_id = str(manifest_row["id"])
            tool = str(manifest_row["tool"]).lower()
            for repetition in range(args.repetitions):
                run_dir = R.run_dir_for(
                    Path(args.runs_root), variant, project_id, repetition
                )
                state = C.read_json_or(run_dir / R.STATE_FILENAME, {})
                if state.get("status") not in {"completed", "failed", "timeout"}:
                    failure = {
                        "variant": variant,
                        "repetition": repetition,
                        "project_id": project_id,
                        "tool": tool,
                        "reason": f"run is not terminal: {state.get('status', 'not_attempted')}",
                    }
                    failures.append(failure)
                    generated_failures.append(dict(failure))
                    continue
                try:
                    report, metadata, generated, report_path = compare_project(
                        official,
                        run_dir=run_dir,
                        variant=variant,
                        repetition=repetition,
                        manifest_row=manifest_row,
                        reference_results_root=Path(args.reference_results_root),
                        output_root=output_root,
                    )
                    if model is not None:
                        add_batched_embeddings(
                            report, model, batch_size=args.embedding_batch_size
                        )
                        C.atomic_write_json(report_path, report)
                    generated_execution = evaluate_codeweaver_generated_tests(
                        tool,
                        run_dir / "pipeline" / "target",
                        generated,
                        timeout=args.generated_test_timeout,
                    )
                    coverage_before, coverage_after = (
                        evaluate_codeweaver_generated_coverage(
                            tool,
                            run_dir,
                            manifest_row,
                            Path(args.reference_results_root),
                            generated,
                            timeout=args.generated_test_timeout,
                        )
                    )
                    project_rows.append(
                        _project_summary(
                            variant=variant,
                            repetition=repetition,
                            project_id=project_id,
                            tool=tool,
                            project=_project_name(manifest_row),
                            metadata=metadata,
                            generated=generated,
                            generated_execution=generated_execution,
                            report=report,
                            report_path=report_path,
                        )
                    )
                    generated_rows.append(generated_project_row(
                        variant=variant,
                        repetition=repetition,
                        manifest_row=manifest_row,
                        generated=generated,
                        execution=generated_execution,
                        coverage_before=coverage_before,
                        coverage_after=coverage_after,
                    ))
                    if model is not None:
                        release_embedding_working_memory()
                except Exception as exc:  # one malformed project must not hide the matrix
                    failures.append(
                        {
                            "variant": variant,
                            "repetition": repetition,
                            "project_id": project_id,
                            "tool": tool,
                            "reason": repr(exc),
                        }
                    )
                    generated_failures.append({
                        "variant": variant,
                        "repetition": repetition,
                        "project_id": project_id,
                        "tool": tool,
                        "reason": repr(exc),
                    })

        for manifest_row in crust_projects:
            project_id = str(manifest_row["id"])
            for repetition in range(args.repetitions):
                run_dir = R.run_dir_for(
                    Path(args.runs_root), variant, project_id, repetition
                )
                state = C.read_json_or(run_dir / R.STATE_FILENAME, {})
                if state.get("status") not in {"completed", "failed", "timeout"}:
                    generated_failures.append({
                        "variant": variant,
                        "repetition": repetition,
                        "project_id": project_id,
                        "tool": "crust",
                        "reason": f"run is not terminal: {state.get('status', 'not_attempted')}",
                    })
                    continue
                try:
                    generated = discover_crust_generated_tests(official, run_dir)
                    execution = evaluate_codeweaver_generated_tests(
                        "crust",
                        run_dir / "pipeline" / "target",
                        generated,
                        timeout=args.generated_test_timeout,
                    )
                    coverage_before, coverage_after = (
                        evaluate_codeweaver_generated_coverage(
                            "crust",
                            run_dir,
                            manifest_row,
                            Path(args.reference_results_root),
                            generated,
                            timeout=args.generated_test_timeout,
                        )
                    )
                    generated_rows.append(generated_project_row(
                        variant=variant,
                        repetition=repetition,
                        manifest_row=manifest_row,
                        generated=generated,
                        execution=execution,
                        coverage_before=coverage_before,
                        coverage_after=coverage_after,
                    ))
                except Exception as exc:
                    generated_failures.append({
                        "variant": variant,
                        "repetition": repetition,
                        "project_id": project_id,
                        "tool": "crust",
                        "reason": repr(exc),
                    })

    _write_csv(output_root / "paper_test_projects.csv", project_rows, PROJECT_COLUMNS)
    _write_csv(output_root / "paper_test_failures.csv", failures, FAILURE_COLUMNS)
    _write_csv(
        output_root / "generated_test_projects.csv",
        generated_rows,
        GENERATED_PROJECT_COLUMNS,
    )
    _write_csv(
        output_root / "generated_test_failures.csv",
        generated_failures,
        FAILURE_COLUMNS,
    )
    C.atomic_write_text(
        output_root / "generated_test_projects.jsonl",
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in generated_rows),
    )
    selected_keys = {
        (str(row["tool"]).lower(), _project_name(row)) for row in projects
    }
    expected_static = (
        sum(PAPER_STATIC_COUNTS[key] for key in selected_keys)
        * len(variants)
        * args.repetitions
    )
    expected_runtime = (
        sum(PAPER_RUNTIME_COUNTS[key] for key in selected_keys)
        * len(variants)
        * args.repetitions
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": C.utcnow_iso(),
        "protocol": "ReCodeAgent RQ2 AST comparator with CodeWeaver target remapping",
        "crust_excluded": True,
        "project_rows": len(project_rows),
        "failures": len(failures),
        "expected_static_source_methods": expected_static,
        "observed_static_source_methods": sum(
            int(row["static_source_methods"]) for row in project_rows
        ),
        "expected_runtime_cases": expected_runtime,
        "observed_runtime_cases": sum(
            int(row["paper_runtime_tests"]) for row in project_rows
        ),
        "mapped_runtime_cases": sum(
            int(row["mapped_runtime_cases"]) for row in project_rows
        ),
        "generated_target_test_methods": sum(
            int(row["generated_target_test_methods"]) for row in project_rows
        ),
        "generated_test_project_rows": len(generated_rows),
        "generated_test_failures": len(generated_failures),
        "codeweaver_generated_tests_expected": sum(
            int(row["generated_tests_expected"])
            for row in generated_rows
            if row.get("generated_tests_expected_status") == C.Status.MEASURED
        ),
        "codeweaver_generated_tests_executed": sum(
            int(row["generated_tests_executed"])
            for row in generated_rows
            if row.get("generated_tests_executed_status") == C.Status.MEASURED
        ),
        "codeweaver_generated_tests_passed": sum(
            int(row["generated_tests_passed"])
            for row in generated_rows
            if row.get("generated_tests_passed_status") == C.Status.MEASURED
        ),
        "coverage_before_measured_projects": sum(
            row.get("coverage_before_status") == C.Status.MEASURED
            for row in generated_rows
        ),
        "coverage_after_measured_projects": sum(
            row.get("coverage_after_status") == C.Status.MEASURED
            for row in generated_rows
        ),
        "embedding_model": args.embedding_model if args.embeddings else None,
        "embedding_status": "measured" if args.embeddings else "not_requested",
    }
    C.atomic_write_json(output_root / "paper_test_summary.json", summary)
    print(
        "[paper-test-compare] "
        f"{len(project_rows)} project row(s), {len(failures)} failure(s), "
        f"{summary['observed_static_source_methods']}/{expected_static} static methods"
    )
    return 0 if not failures and not generated_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
