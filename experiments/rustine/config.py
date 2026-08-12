"""Strict loader for the committed 23-subject Rustine reference configuration."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from experiments.rustine.common import DEFAULT_CONFIG

EXPECTED_SUBJECTS = [
    ("qsort", "qsort"),
    ("bst", "bst"),
    ("rgba", "rgba"),
    ("quadtree", "quadtree-0.1.0"),
    ("buffer", "buffer-0.4.0"),
    ("grabc", "grabc"),
    ("urlparser", "url_parser"),
    ("xzoom", "xzoom"),
    ("genann", "genann"),
    ("ht", "ht"),
    ("robotfindskitten", "robotfindskitten"),
    ("libcsv", "libcsv"),
    ("avl-tree", "avl-tree"),
    ("libopenaptx", "libopenaptx"),
    ("libtree", "libtree-3.1.1"),
    ("opl", "opl"),
    ("libzahl", "libzahl-1.0"),
    ("zopfli", "zopfli"),
    ("snudown", "snudown"),
    ("lodepng", "lodepng"),
    ("bzip2", "bzip2"),
    ("binn", "binn-3.0"),
    ("tulpindicator", "tulipindicators"),
]

EXPECTED_CONTRACT_FILES = {
    1: ["src/test.rs", "src/test_main.rs"],
    2: ["src/test.rs", "src/test_main.rs"],
    3: ["src/test.rs", "src/test_main.rs"],
    4: ["src/test.rs", "src/test_main.rs"],
    5: ["src/test.rs", "src/test_main.rs"],
    6: ["src/test_grabc.rs", "src/test_grabc_main.rs"],
    7: ["src/test.rs", "src/test_main.rs"],
    8: [],
    9: ["src/test.rs", "src/test_main.rs"],
    10: [
        "src/lsearch.rs",
        "src/bsearch_main.rs",
        "src/dump.rs",
        "src/perfset.rs",
        "src/perflbh_main.rs",
        "src/perfget.rs",
        "src/demo.rs",
        "src/stats_main.rs",
    ],
    11: ["src/test.rs", "src/test_main.rs"],
    12: ["src/test_csv.rs", "src/test_csv_main.rs"],
    13: ["src/avl_test.rs", "src/avl_test_main.rs"],
    14: ["src/test.rs", "src/test_main.rs"],
    15: ["src/test.rs", "src/test_main.rs"],
    16: ["src/test.rs", "src/test_main.rs"],
    17: ["src/test.rs", "src/test_main.rs", "src/zbtest.rs", "src/zptest.rs"],
    18: ["src/test_zopfli.rs", "src/test_zopfli_main.rs"],
    19: [],
    20: ["src/test.rs", "src/test_main.rs"],
    21: [],
    22: ["src/test_binn.rs", "src/test_binn2.rs", "src/test_binn_main.rs"],
    23: ["src/smoke.rs", "src/smoke_main.rs"],
}
EXPECTED_LOCS = [
    27,
    65,
    411,
    437,
    452,
    490,
    563,
    659,
    690,
    699,
    838,
    1035,
    1170,
    1333,
    1412,
    1642,
    2575,
    2937,
    5271,
    5606,
    5861,
    6361,
    13200,
]
EXPECTED_TARGETS = {
    1: ["test"],
    2: ["test"],
    3: ["test"],
    4: ["test"],
    5: ["test"],
    6: ["test_grabc"],
    7: ["test"],
    8: [],
    9: ["test"],
    10: ["lsearch", "bsearch", "dump", "perfset", "perflbh", "perfget", "demo", "stats"],
    11: ["test"],
    12: ["test_csv"],
    13: ["avl_test"],
    14: ["test"],
    15: ["test"],
    16: ["test"],
    17: ["test"],
    18: ["test_zopfli"],
    19: [],
    20: ["test"],
    21: ["bzip2"],
    22: ["test_binn"],
    23: ["smoke"],
}

SAFETY_FIELDS = {
    "pointer_arithmetic",
    "raw_pointer_declarations",
    "raw_pointer_dereferences",
    "unsafe_lines",
    "unsafe_type_casts",
    "unsafe_calls",
}
VALIDATION_FIELDS = {
    "compilation_percent",
    "function_coverage_percent",
    "line_coverage_percent",
    "assertions_executed",
    "assertions_passed",
    "assertions_failed",
}
CONTRACT_KINDS = {"rust_binary", "none", "derived_cli_roundtrip"}
ASSERTION_CREDIT = {
    "pass_all_paper_denominator",
    "ti_summary",
    "unavailable",
    "not_applicable",
}


def _require_keys(value: dict[str, Any], required: set[str], label: str) -> None:
    missing = required - set(value)
    extra = set(value) - required
    if missing or extra:
        raise ValueError(
            f"{label} keys invalid; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _validate_relpath(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "\\" in raw:
        raise ValueError(f"{label} must be a safe POSIX relative path: {raw!r}")
    return raw


def _validate_subject(subject: dict[str, Any], expected_id: int) -> None:
    _require_keys(
        subject,
        {
            "id",
            "name",
            "artifact_dir",
            "loc",
            "contract",
            "paper_validation",
            "paper_safety",
        },
        f"subject {expected_id}",
    )
    if subject["id"] != expected_id:
        raise ValueError(f"subject IDs must be exactly 1..23 in order; got {subject['id']!r}")
    expected_name, expected_dir = EXPECTED_SUBJECTS[expected_id - 1]
    if (subject["name"], subject["artifact_dir"]) != (expected_name, expected_dir):
        raise ValueError(
            f"subject {expected_id} mapping must be {(expected_name, expected_dir)!r}"
        )
    if subject["loc"] != EXPECTED_LOCS[expected_id - 1]:
        raise ValueError(f"subject {expected_id}.loc does not match the paper reference")

    validation = subject["paper_validation"]
    if not isinstance(validation, dict):
        raise ValueError(f"subject {expected_id}.paper_validation must be an object")
    _require_keys(validation, VALIDATION_FIELDS, f"subject {expected_id}.paper_validation")
    if validation["compilation_percent"] != 100:
        raise ValueError(f"subject {expected_id} paper compilation must be 100")
    for field in ("function_coverage_percent", "line_coverage_percent"):
        value = validation[field]
        if value is not None and (
            not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 100
        ):
            raise ValueError(f"subject {expected_id}.{field} must be 0..100 or null")
    assertions = [
        validation["assertions_executed"],
        validation["assertions_passed"],
        validation["assertions_failed"],
    ]
    if any(v is None for v in assertions):
        if not all(v is None for v in assertions):
            raise ValueError(f"subject {expected_id} assertion references must be all-null or all-set")
    else:
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in assertions):
            raise ValueError(f"subject {expected_id} assertion references must be nonnegative integers")
        if assertions[1] + assertions[2] != assertions[0]:
            raise ValueError(f"subject {expected_id} paper passed+failed must equal executed")

    safety = subject["paper_safety"]
    if not isinstance(safety, dict):
        raise ValueError(f"subject {expected_id}.paper_safety must be an object")
    _require_keys(safety, SAFETY_FIELDS, f"subject {expected_id}.paper_safety")
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in safety.values()):
        raise ValueError(f"subject {expected_id} safety values must be nonnegative integers")

    contract = subject["contract"]
    required_contract = {
        "kind",
        "files",
        "assets",
        "targets",
        "test_dependencies",
        "assertion_credit",
    }
    allowed_contract = required_contract | {
        "success_regex",
        "failure_regex",
        "executions",
        "external_assets",
    }
    missing = required_contract - set(contract)
    extra = set(contract) - allowed_contract
    if missing or extra:
        raise ValueError(
            f"subject {expected_id}.contract keys invalid; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if contract["kind"] not in CONTRACT_KINDS:
        raise ValueError(f"subject {expected_id} has invalid contract kind")
    if contract["assertion_credit"] not in ASSERTION_CREDIT:
        raise ValueError(f"subject {expected_id} has invalid assertion credit mode")
    for field in ("files", "assets", "targets", "test_dependencies"):
        if not isinstance(contract[field], list) or any(
            not isinstance(item, str) or not item for item in contract[field]
        ):
            raise ValueError(f"subject {expected_id}.contract.{field} must be a string array")
        if len(contract[field]) != len(set(contract[field])):
            raise ValueError(f"subject {expected_id}.contract.{field} contains duplicates")
    for path in contract["files"] + contract["assets"]:
        _validate_relpath(path, f"subject {expected_id} contract path")
        if path == "translation.json" or path.endswith("/translation.json"):
            raise ValueError("translation.json is never a contract")
    executions = contract.get("executions", [])
    if not isinstance(executions, list):
        raise ValueError(f"subject {expected_id}.contract.executions must be an array")
    for execution in executions:
        if not isinstance(execution, dict):
            raise ValueError(f"subject {expected_id} execution must be an object")
        _require_keys(
            execution,
            {"target", "args", "stdin"},
            f"subject {expected_id} execution",
        )
        if execution["target"] not in contract["targets"]:
            raise ValueError(f"subject {expected_id} execution target is not declared")
        if not isinstance(execution["args"], list) or any(
            not isinstance(arg, str) for arg in execution["args"]
        ):
            raise ValueError(f"subject {expected_id} execution args must be strings")
        if execution["stdin"] is not None and not isinstance(execution["stdin"], str):
            raise ValueError(f"subject {expected_id} execution stdin must be text or null")
    external_assets = contract.get("external_assets", [])
    if not isinstance(external_assets, list):
        raise ValueError(f"subject {expected_id}.contract.external_assets must be an array")
    for asset in external_assets:
        if not isinstance(asset, dict):
            raise ValueError(f"subject {expected_id} external asset must be an object")
        _require_keys(
            asset,
            {"path", "url", "sha256", "source_commit", "license"},
            f"subject {expected_id} external asset",
        )
        _validate_relpath(asset["path"], f"subject {expected_id} external asset path")
        if not str(asset["url"]).startswith("https://raw.githubusercontent.com/"):
            raise ValueError(f"subject {expected_id} external asset URL is not pinned raw GitHub")
        if not isinstance(asset["sha256"], str) or len(asset["sha256"]) != 64:
            raise ValueError(f"subject {expected_id} external asset SHA-256 is invalid")
    if contract["files"] != EXPECTED_CONTRACT_FILES[expected_id]:
        raise ValueError(f"subject {expected_id} contract file list does not match the protocol")
    if contract["targets"] != EXPECTED_TARGETS[expected_id]:
        raise ValueError(f"subject {expected_id} contract target list does not match the protocol")
    if expected_id == 9 and contract["assets"] != ["persist.txt"]:
        raise ValueError("genann must declare persist.txt as its sole test asset")
    if expected_id != 9 and contract["assets"]:
        raise ValueError(f"subject {expected_id} has an unexpected test asset")
    if expected_id == 6:
        if executions != [{"target": "test_grabc", "args": ["-v"], "stdin": None}]:
            raise ValueError("grabc must use the deterministic headless version execution")
        if contract["assertion_credit"] != "unavailable":
            raise ValueError("grabc exact paper assertion credit must remain unavailable")
    elif expected_id == 10:
        if executions != [{"target": "demo", "args": [], "stdin": "alpha beta alpha\n"}]:
            raise ValueError("ht must use the deterministic stdin-driven demo execution")
        if contract["assertion_credit"] != "unavailable":
            raise ValueError("ht exact paper assertion credit must remain unavailable")
    elif executions:
        raise ValueError(f"subject {expected_id} has unexpected custom executions")
    if expected_id == 23:
        expected_external_paths = {
            "tests/untest.txt",
            "tests/atoz.txt",
            "tests/extra.txt",
            "tests/candles.txt",
            "third_party/tulipindicators-LICENSE-LGPL-3.0.txt",
        }
        if {asset["path"] for asset in external_assets} != expected_external_paths:
            raise ValueError("tulipindicator external fixture set is incomplete")
        if any(
            asset["source_commit"] != "be18abb13e075ba866898dcc7cb52399603302a6"
            for asset in external_assets
        ):
            raise ValueError("tulipindicator fixtures must use the pinned upstream commit")
    elif external_assets:
        raise ValueError(f"subject {expected_id} has unexpected external assets")
    if expected_id in (8, 19):
        if contract["kind"] != "none" or contract["assertion_credit"] != "not_applicable":
            raise ValueError("xzoom and snudown must be explicit no-test/N/A subjects")
        if any(assertions):
            raise ValueError("xzoom and snudown paper assertions must be null")
    elif expected_id == 21:
        if (
            contract["kind"] != "derived_cli_roundtrip"
            or contract["assertion_credit"] != "unavailable"
        ):
            raise ValueError("bzip2 must use the derived round-trip with unavailable exact credit")
    elif contract["kind"] != "rust_binary":
        raise ValueError(f"subject {expected_id} must use a Rust binary contract")
    if contract["kind"] == "rust_binary" and not contract["targets"]:
        raise ValueError(f"subject {expected_id} Rust contract has no target")
    if contract["assertion_credit"] == "ti_summary":
        if not contract.get("success_regex") or not contract.get("failure_regex"):
            raise ValueError("ti_summary requires success and failure regexes")


def validate_subject_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ValueError("Rustine config must be a JSON object")
    _require_keys(config, {"schema_version", "paper", "artifact", "protocol", "subjects"}, "config")
    if config["schema_version"] != 1:
        raise ValueError("unsupported Rustine config schema_version")
    paper = config["paper"]
    if paper != {
        "arxiv_id": "2511.20617v1",
        "title": "Translating Large-Scale C Repositories to Idiomatic Rust",
        "url": "https://arxiv.org/abs/2511.20617",
    }:
        raise ValueError("paper provenance does not match arXiv:2511.20617v1")
    artifact = config["artifact"]
    if artifact.get("commit") != "774ff51e48d4d3a6a73e4864689a042fc1028fc0":
        raise ValueError("official artifact commit is not pinned correctly")
    if artifact.get("license") != "MIT" or set(artifact) != {"commit", "license"}:
        raise ValueError("artifact metadata must contain only the MIT license and pinned commit")
    protocol = config["protocol"]
    required_protocol = {
        "model",
        "effort",
        "agent_timeout_seconds",
        "max_iter",
        "max_parity_rounds",
        "repetitions",
        "rust_toolchain",
        "cargo_llvm_cov_version",
        "cargo_newmetrics_sha256",
    }
    _require_keys(protocol, required_protocol, "protocol")
    expected_protocol = {
        "model": "gpt-5.6-sol",
        "effort": "max",
        "agent_timeout_seconds": 5000,
        "max_iter": 5,
        "max_parity_rounds": 3,
        "repetitions": 1,
        "rust_toolchain": "nightly-2025-05-13",
        "cargo_llvm_cov_version": "0.8.7",
        "cargo_newmetrics_sha256": "235e5515186bcbe1a455339c524a9e33f8223fffa5fec2f8293cee11c1afc2bb",
    }
    if protocol != expected_protocol:
        raise ValueError("protocol defaults drifted from the frozen GPT comparison protocol")
    subjects = config["subjects"]
    if not isinstance(subjects, list) or len(subjects) != 23:
        raise ValueError("Rustine config must declare exactly 23 subjects")
    for expected_id, subject in enumerate(subjects, start=1):
        if not isinstance(subject, dict):
            raise ValueError(f"subject {expected_id} must be an object")
        _validate_subject(subject, expected_id)
    for field in ("executed", "passed", "failed"):
        total = sum(
            subject["paper_validation"][f"assertions_{field}"] or 0
            for subject in subjects
        )
        expected = {
            "executed": 1_221_192,
            "passed": 1_063_099,
            "failed": 158_093,
        }[field]
        if total != expected:
            raise ValueError(
                f"paper assertion {field} total does not match the subject table"
            )
    if len({s["artifact_dir"] for s in subjects}) != 23:
        raise ValueError("artifact directory mappings must be unique")
    return config


def load_subject_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load Rustine config {config_path}: {exc}") from exc
    return validate_subject_config(config)


def subjects_by_id(config: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {subject["id"]: subject for subject in config["subjects"]}
