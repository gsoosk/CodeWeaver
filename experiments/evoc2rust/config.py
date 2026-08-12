"""Strict validation for the frozen Vivo-Bench comparison configuration."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from experiments.evoc2rust import common as C

EXPECTED_ARTIFACT_COMMIT = "c88cef1a1d15079478be14ab361dda8f3b49fee2"
EXPECTED_C2RUST_SHA256 = (
    "e11377b3102b768cff101b191c29daf1d5dd4449e22af5b61684443a65fd07cb"
)
EXPECTED_MODULES = {
    "arraylist",
    "avl-tree",
    "binary-heap",
    "binomial-heap",
    "bloom-filter",
    "compare-int",
    "compare-pointer",
    "compare-string",
    "hash-int",
    "hash-pointer",
    "hash-string",
    "hash-table",
    "list",
    "queue",
    "rb-tree",
    "set",
    "slist",
    "sortedarray",
    "trie",
}


def _require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    extra = set(value) - expected
    if missing or extra:
        raise ValueError(
            f"{label} keys invalid; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    _require_keys(
        config,
        {"schema_version", "paper", "artifact", "tools", "protocol", "subjects"},
        "config",
    )
    if config["schema_version"] != 1:
        raise ValueError("unsupported EvoC2Rust config schema")
    paper = config["paper"]
    if paper.get("doi") != "10.1145/3786583.3786856":
        raise ValueError("paper DOI drifted")
    if len(paper.get("table4_rows", [])) != 20:
        raise ValueError("paper Table 4 rows drifted")
    if len(paper.get("table5_c2r_rows", [])) != 14:
        raise ValueError("paper Table 5 C2R-Bench rows drifted")
    if len(paper.get("table6_rows", [])) != 5:
        raise ValueError("paper Table 6 rows drifted")
    if paper.get("dataset_statistics") != {
        "vivo_bench_paper_test_cases": 113,
        "vivo_bench_pinned_active_test_functions": 125,
        "vivo_bench_pinned_disabled_test_functions": 2,
        "c2r_bench_projects": 6,
        "c2r_bench_test_cases": 222,
    }:
        raise ValueError("paper dataset statistics drifted")
    if (
        paper["table4_rows"][5].get("method") != "EvoC2Rust"
        or paper["table4_rows"][5].get("safe_rate_percent") != 98.0
        or paper["table6_rows"][0].get("test_rate_percent") != 89.53
    ):
        raise ValueError("paper reference values drifted")
    artifact = config["artifact"]
    if artifact.get("commit") != EXPECTED_ARTIFACT_COMMIT:
        raise ValueError("Vivo-Bench artifact commit drifted")
    tools = config["tools"]
    expected_tools = {
        "c2rust_version": "0.22.1",
        "c2rust_sha256": EXPECTED_C2RUST_SHA256,
        "rust_toolchain": "nightly-2025-09-15",
        "cc_version": "1.4.2",
    }
    if tools != expected_tools:
        raise ValueError("tool lock drifted")
    protocol = config["protocol"]
    expected_protocol = {
        "model": "gpt-5.6-sol",
        "effort": "max",
        "agent_timeout_seconds": 5000,
        "max_iter": 5,
        "max_parity_rounds": 3,
        "repetitions": 3,
    }
    if protocol != expected_protocol:
        raise ValueError("CodeWeaver protocol drifted")

    subjects = config["subjects"]
    if not isinstance(subjects, list) or len(subjects) != 15:
        raise ValueError("exactly 15 Vivo-Bench test groups are required")
    if [subject.get("id") for subject in subjects] != list(range(1, 16)):
        raise ValueError("subject IDs must be exactly 1..15")
    names = [subject.get("name") for subject in subjects]
    if len(set(names)) != len(names):
        raise ValueError("subject names must be unique")

    target_modules: list[str] = []
    total_tests = 0
    total_assertions = 0
    expected_subject_keys = {
        "id",
        "name",
        "modules",
        "support_modules",
        "test_file",
        "test_module",
        "loc_source",
        "test_functions",
        "c_assertions",
    }
    for subject in subjects:
        _require_keys(subject, expected_subject_keys, f"subject {subject.get('id')}")
        modules = subject["modules"]
        support = subject["support_modules"]
        tests = subject["test_functions"]
        if not modules or any(module not in EXPECTED_MODULES for module in modules):
            raise ValueError(f"subject {subject['id']} has invalid target modules")
        if any(module not in EXPECTED_MODULES for module in support):
            raise ValueError(f"subject {subject['id']} has invalid support modules")
        if set(modules) & set(support):
            raise ValueError(f"subject {subject['id']} targets a support module")
        if len(modules) != len(set(modules)) or len(support) != len(set(support)):
            raise ValueError(f"subject {subject['id']} contains duplicate modules")
        if not subject["test_file"].startswith("test/test-"):
            raise ValueError(f"subject {subject['id']} has an invalid test path")
        if not subject["test_module"].startswith("test_"):
            raise ValueError(f"subject {subject['id']} has an invalid Rust test module")
        if not tests or len(tests) != len(set(tests)):
            raise ValueError(f"subject {subject['id']} has invalid test functions")
        if any(not name.startswith("test_") for name in tests):
            raise ValueError(f"subject {subject['id']} has an invalid test name")
        if subject["loc_source"] <= 0 or subject["c_assertions"] <= 0:
            raise ValueError(f"subject {subject['id']} has invalid benchmark counts")
        target_modules.extend(modules)
        total_tests += len(tests)
        total_assertions += subject["c_assertions"]
    if set(target_modules) != EXPECTED_MODULES or len(target_modules) != 19:
        raise ValueError("the 15 groups must partition all 19 Vivo-Bench modules")
    if total_tests != 125:
        raise ValueError(f"expected 125 active fixed test functions, found {total_tests}")
    if total_assertions != 637:
        raise ValueError(f"expected 637 active C assertion sites, found {total_assertions}")
    return config


def load_config(path: str | Path = C.DEFAULT_CONFIG) -> dict[str, Any]:
    value = C.read_json(path)
    if not isinstance(value, dict):
        raise ValueError("EvoC2Rust configuration must be a JSON object")
    return validate_config(copy.deepcopy(value))


def subjects_by_id(config: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(subject["id"]): subject for subject in config["subjects"]}
