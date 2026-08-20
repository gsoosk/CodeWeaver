"""Build the citation-complete CRUST-Bench comparison artifact."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import statistics
from pathlib import Path
from typing import Any

from . import common as C
from .citation_catalog import (
    ACTOR_PUBLIC_MISSING_PROJECT_IDS,
    CENSUS_DATE,
    CITATION_RECORDS,
    CITER_SURFACES,
    INCLUSION_MATRIX,
    LAC2R_LAERTES_SUBJECTS,
    ORBIT_SUBJECTS,
    TACO_CRUST_REFERENCE,
)
from .config import PROTOCOL
from .citer_reference_data import CITER_REFERENCE_TABLES
from .package import _archive, _related_run_file
from .report import (
    RESULT_NAMES,
    _markdown_table,
    _percent,
    _render_figure,
    _render_pdf,
    _write_jsonl,
    _write_report_files,
)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _number(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    return int(float(value)) if value not in (None, "") else 0


def _credited_passes(row: dict[str, Any]) -> int:
    return min(
        _number(row, "validated_tests_passed"),
        _number(row, "validated_tests_expected_paper"),
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    C.write_csv(path, rows, fields)


def _orbit_rows(
    historical_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    crust = [
        row
        for row in historical_rows
        if row.get("variant") == "full" and row.get("tool") == "crust"
    ]
    if len(crust) != 300:
        raise ValueError(f"expected 300 reusable CRUST cells, found {len(crust)}")
    by_key = {
        (row["project_id"], int(row["repetition"])): row for row in crust
    }
    combined: list[dict[str, Any]] = []
    for subject in ORBIT_SUBJECTS:
        repetitions = [
            by_key[(subject["project_id"], repetition)] for repetition in range(3)
        ]
        combined.append(
            {
                **subject,
                "codeweaver_build_repetitions": sum(
                    _bool(row["build"]) for row in repetitions
                ),
                "codeweaver_pass_all_repetitions": sum(
                    _bool(row["project_pass_all"]) for row in repetitions
                ),
                "codeweaver_tests_passed": sum(
                    _credited_passes(row) for row in repetitions
                ),
                "codeweaver_tests_expected": sum(
                    _number(row, "validated_tests_expected_paper")
                    for row in repetitions
                ),
                **{
                    f"codeweaver_rep{repetition + 1}_build": _bool(
                        repetitions[repetition]["build"]
                    )
                    for repetition in range(3)
                },
                **{
                    f"codeweaver_rep{repetition + 1}_pass_all": _bool(
                        repetitions[repetition]["project_pass_all"]
                    )
                    for repetition in range(3)
                },
            }
        )
    summaries: list[dict[str, Any]] = []
    ids = {row["project_id"] for row in ORBIT_SUBJECTS}
    for repetition in range(3):
        selected = [
            row
            for row in crust
            if row["project_id"] in ids and int(row["repetition"]) == repetition
        ]
        passed = sum(_credited_passes(row) for row in selected)
        expected = sum(
            _number(row, "validated_tests_expected_paper") for row in selected
        )
        summaries.append(
            {
                "system": f"CodeWeaver repetition {repetition + 1}",
                "projects": 24,
                "build_successes": sum(_bool(row["build"]) for row in selected),
                "test_successes": sum(
                    _bool(row["project_pass_all"]) for row in selected
                ),
                "test_success_percent": (
                    100
                    * sum(_bool(row["project_pass_all"]) for row in selected)
                    / 24
                ),
                "fixed_tests_passed": passed,
                "fixed_tests_expected": expected,
                "fixed_test_rate_percent": 100 * passed / expected,
                "protocol": "CodeWeaver multi-stage, 5 repairs, 3 parity rounds",
            }
        )
    summaries = [
        {
            "system": "ORBIT expert interfaces",
            "projects": 24,
            "build_successes": 24,
            "test_successes": 22,
            "test_success_percent": 91.6666666667,
            "fixed_tests_passed": "",
            "fixed_tests_expected": "",
            "fixed_test_rate_percent": "",
            "protocol": "paper reference; apparent single run",
        },
        {
            "system": "ORBIT generated interfaces",
            "projects": 24,
            "build_successes": 24,
            "test_successes": 22,
            "test_success_percent": 91.6666666667,
            "fixed_tests_passed": "",
            "fixed_tests_expected": "",
            "fixed_test_rate_percent": "",
            "protocol": "paper reference; apparent single run",
        },
        *summaries,
    ]
    return combined, summaries


def _actor_public_95_rows(
    historical_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    crust = [
        row
        for row in historical_rows
        if row.get("variant") == "full" and row.get("tool") == "crust"
    ]
    all_ids = {row["project_id"] for row in crust}
    if len(crust) != 300 or len(all_ids) != 100:
        raise ValueError(
            f"expected 100 CRUST projects / 300 cells, found "
            f"{len(all_ids)} projects / {len(crust)} cells"
        )
    if not ACTOR_PUBLIC_MISSING_PROJECT_IDS <= all_ids:
        raise ValueError("ACTOR public-artifact missing-project lock drifted")
    public_ids = all_ids - ACTOR_PUBLIC_MISSING_PROJECT_IDS
    if len(public_ids) != 95:
        raise ValueError(f"expected ACTOR public overlap of 95, found {len(public_ids)}")
    by_key = {
        (row["project_id"], int(row["repetition"])): row for row in crust
    }
    projects: list[dict[str, Any]] = []
    for project_id in sorted(public_ids):
        repetitions = [by_key[(project_id, repetition)] for repetition in range(3)]
        projects.append(
            {
                "project_id": project_id,
                "project": project_id.split("__", 1)[1],
                "public_actor_result_directory": True,
                "paper_87_membership": "unresolved",
                "codeweaver_build_repetitions": sum(
                    _bool(row["build"]) for row in repetitions
                ),
                "codeweaver_pass_all_repetitions": sum(
                    _bool(row["project_pass_all"]) for row in repetitions
                ),
                "codeweaver_fixed_tests_passed": sum(
                    _credited_passes(row) for row in repetitions
                ),
                "codeweaver_fixed_tests_expected": sum(
                    _number(row, "validated_tests_expected_paper")
                    for row in repetitions
                ),
            }
        )
    summaries: list[dict[str, Any]] = []
    for repetition in range(3):
        selected = [
            row
            for row in crust
            if row["project_id"] in public_ids
            and int(row["repetition"]) == repetition
        ]
        passed = sum(_credited_passes(row) for row in selected)
        expected = sum(
            _number(row, "validated_tests_expected_paper") for row in selected
        )
        summaries.append(
            {
                "system": f"CodeWeaver repetition {repetition + 1}",
                "public_artifact_projects": 95,
                "paper_projects": 87,
                "paper_membership_status": (
                    "unresolved; not treated as the paper's 87-project slice"
                ),
                "build_successes": sum(_bool(row["build"]) for row in selected),
                "test_successes": sum(
                    _bool(row["project_pass_all"]) for row in selected
                ),
                "fixed_tests_passed": passed,
                "fixed_tests_expected": expected,
            }
        )
    return projects, summaries


def _lac2r_intersection(repository_root: Path) -> list[dict[str, Any]]:
    validation = _load_csv(
        repository_root
        / "results"
        / "rustine-codeweaver-comparison-2026-08-12"
        / "report"
        / "validation.csv"
    )
    aliases = {"tulip-indicators": "tulpindicator"}
    by_subject = {row["subject"]: row for row in validation}
    rows: list[dict[str, Any]] = []
    for lac2r_subject in LAC2R_LAERTES_SUBJECTS:
        rustine_subject = aliases.get(lac2r_subject, lac2r_subject)
        codeweaver = by_subject.get(rustine_subject)
        rows.append(
            {
                "lac2r_subject": lac2r_subject,
                "rustine_subject": rustine_subject if codeweaver else "",
                "name_overlap": codeweaver is not None,
                "identity_status": (
                    "name overlap only; revisions and contracts not proven identical"
                    if codeweaver
                    else "no retained Rustine subject"
                ),
                "codeweaver_compile": (
                    codeweaver["codeweaver_compilation"] if codeweaver else ""
                ),
                "codeweaver_fixed_contract": (
                    codeweaver["codeweaver_fixed_contract_tests"]
                    if codeweaver
                    else ""
                ),
            }
        )
    return rows


def _existing_evidence(repository_root: Path) -> list[dict[str, Any]]:
    crust = C.read_json(
        repository_root
        / "results"
        / "crust-bench-codeweaver-comparison-2026-08-14"
        / "data"
        / "summary.json"
    )
    sactor = C.read_json(
        repository_root
        / "results"
        / "sactor-codeweaver-comparison-2026-08-14"
        / "data"
        / "summary.json"
    )
    rustine = C.read_json(
        repository_root
        / "results"
        / "rustine-codeweaver-comparison-2026-08-12"
        / "report"
        / "aggregate.json"
    )["codeweaver"]
    evoc2rust = C.read_json(
        repository_root
        / "results"
        / "evoc2rust-codeweaver-comparison-2026-08-13"
        / "report"
        / "aggregate.json"
    )
    return [
        {
            "study": "ReCodeAgent",
            "scope": "118 projects / four language pairs",
            "measured_cells": "complete published reproduction",
            "headline": "full raw data, baselines, ablations, tables, figures, and PDF",
            "result_path": "results/recodeagent-gpt-5.6-sol-final-2026-08-11",
        },
        {
            "study": "CRUST-Bench",
            "scope": "100 projects x 3 repetitions",
            "measured_cells": crust["measured_rows"],
            "headline": (
                f"{crust['build_cells']}/300 build; "
                f"{crust['pass_all_cells']}/300 pass all"
            ),
            "result_path": "results/crust-bench-codeweaver-comparison-2026-08-14",
        },
        {
            "study": "SACTOR exact subset",
            "scope": "50 projects x 3 repetitions",
            "measured_cells": sactor["measured_rows"],
            "headline": (
                f"{sactor['build_cells']}/150 build; "
                f"{sactor['pass_all_cells']}/150 pass all"
            ),
            "result_path": "results/sactor-codeweaver-comparison-2026-08-14",
        },
        {
            "study": "Rustine",
            "scope": "23 projects x 1 repetition",
            "measured_cells": rustine["rows"],
            "headline": (
                f"{rustine['compiled']}/23 compile; "
                f"{rustine['fixed_contract_passed']}/"
                f"{rustine['fixed_contract_measured_rows']} fixed-contract pass"
            ),
            "result_path": "results/rustine-codeweaver-comparison-2026-08-12",
        },
        {
            "study": "EvoC2Rust public Vivo-Bench",
            "scope": "15 groups / 19 modules x 3 repetitions",
            "measured_cells": evoc2rust["runs_observed"],
            "headline": (
                "100% incremental compilation, fill compilation, and fixed-test "
                f"rate; mean SafeRate "
                f"{evoc2rust['distributions']['safe_rate_percent']['mean']:.2f}%"
            ),
            "result_path": "results/evoc2rust-codeweaver-comparison-2026-08-13",
        },
        {
            "study": "RepoTransBench historical slice",
            "scope": "3 projects x 3 repetitions",
            "measured_cells": 9,
            "headline": "9/9 independently build and pass all fixed tests",
            "result_path": "results/repotransbench-codeweaver-comparison-2026-08-14",
        },
        {
            "study": "RustRepoTrans language slice",
            "scope": "3 tasks x 3 repetitions",
            "measured_cells": 9,
            "headline": "9/9 independently build and pass all fixed tests",
            "result_path": "results/rustrepotrans-codeweaver-comparison-2026-08-14",
        },
    ]


def _copy_reused_summaries(root: Path, repository_root: Path) -> None:
    sources = {
        "crust_summary.json": (
            "crust-bench-codeweaver-comparison-2026-08-14/data/summary.json"
        ),
        "sactor_summary.json": (
            "sactor-codeweaver-comparison-2026-08-14/data/summary.json"
        ),
        "rustine_aggregate.json": (
            "rustine-codeweaver-comparison-2026-08-12/report/aggregate.json"
        ),
        "evoc2rust_aggregate.json": (
            "evoc2rust-codeweaver-comparison-2026-08-13/report/aggregate.json"
        ),
        "recodeagent_final_verification.json": (
            "recodeagent-gpt-5.6-sol-final-2026-08-11/"
            "metadata/final_verification.json"
        ),
    }
    for destination, source in sources.items():
        path = repository_root / "results" / source
        if not path.is_file():
            raise FileNotFoundError(path)
        destination_path = root / "data" / "reused" / destination
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination_path)


ACTOR_LI_DENOMINATORS = {
    "csplit": 70,
    "expr": 100,
    "fmt": 66,
    "join": 84,
    "printf": 83,
    "test": 89,
}


def _required_int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if value in (None, ""):
        raise ValueError(f"missing required integer {key}: {row}")
    return int(float(value))


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink rejected in published ACToR contract: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


SENSITIVE_BYTE_PATTERNS = (
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
)


def _assert_no_credentials(
    source: Path,
    *,
    predicate: Any | None = None,
) -> None:
    text_suffixes = {
        ".csv",
        ".json",
        ".jsonl",
        ".log",
        ".md",
        ".py",
        ".rs",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    for path in sorted(source.rglob("*")):
        if not (path.is_file() or path.is_symlink()):
            continue
        relative = path.relative_to(source)
        if predicate is not None and not predicate(relative):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink rejected from published evidence: {relative}")
        if path.suffix.lower() not in text_suffixes:
            continue
        payload = path.read_bytes()
        if any(pattern.search(payload) for pattern in SENSITIVE_BYTE_PATTERNS):
            raise ValueError(
                f"credential-shaped value rejected from published evidence: {relative}"
            )


def _validate_actor_li_evaluation(
    evaluation_root: Path,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    required_files = (
        "summary.json",
        "raw_runs.csv",
        "raw_runs.jsonl",
        "aggregate.csv",
        "negative_controls.csv",
        "oracle_contract_manifest.csv",
        "oracle-qualification/qualification.csv",
        "oracle-qualification/summary.json",
        "campaign-seal.json",
        "macro_experiment_status.json",
    )
    missing = [
        relative
        for relative in required_files
        if not (evaluation_root / relative).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"incomplete ACToR evaluation under {evaluation_root}: {missing}"
        )

    expected_keys = {
        (subject, repetition)
        for subject in ACTOR_LI_DENOMINATORS
        for repetition in range(PROTOCOL["repetitions"])
    }
    rows = _load_csv(evaluation_root / "raw_runs.csv")
    row_keys = [
        (row.get("subject", ""), _required_int(row, "repetition"))
        for row in rows
    ]
    if len(rows) != 18 or len(set(row_keys)) != 18 or set(row_keys) != expected_keys:
        raise ValueError(f"ACToR cell identity drift: {row_keys}")
    for row in rows:
        subject = row["subject"]
        expected = ACTOR_LI_DENOMINATORS[subject]
        if (
            row.get("evaluation_status") != "measured"
            or row.get("run_status") not in {"completed", "failed", "timeout"}
            or not _bool(row.get("contract_integrity"))
            or _required_int(row, "expected_tests") != expected
        ):
            raise ValueError(f"invalid ACToR measured cell: {row}")
        passed = _required_int(row, "tests_passed")
        failed = _required_int(row, "tests_failed")
        not_executed = _required_int(row, "tests_not_executed")
        if (
            min(passed, failed, not_executed) < 0
            or passed + failed + not_executed != expected
        ):
            raise ValueError(f"invalid ACToR test accounting: {row}")
        if _bool(row.get("pass_all")) and not (
            passed == expected
            and failed == 0
            and not_executed == 0
            and _bool(row.get("build"))
            and _bool(row.get("candidate_runtime_isolated"))
        ):
            raise ValueError(f"invalid ACToR pass-all claim: {row}")
        if _bool(row.get("safe_pass_all")) and not (
            _bool(row.get("pass_all"))
            and _bool(row.get("safe_rust"))
            and _bool(row.get("self_contained"))
        ):
            raise ValueError(f"invalid ACToR safe pass-all claim: {row}")

    with (evaluation_root / "raw_runs.jsonl").open(encoding="utf-8") as handle:
        jsonl_rows = [json.loads(line) for line in handle if line.strip()]
    jsonl_keys = {
        (str(row.get("subject", "")), int(row.get("repetition", -1)))
        for row in jsonl_rows
    }
    if len(jsonl_rows) != 18 or jsonl_keys != expected_keys:
        raise ValueError("ACToR JSONL cell evidence is incomplete")
    csv_by_key = dict(zip(row_keys, rows, strict=True))
    for jsonl_row in jsonl_rows:
        key = (str(jsonl_row["subject"]), int(jsonl_row["repetition"]))
        csv_row = csv_by_key[key]
        for field in (
            "expected_tests",
            "tests_loaded",
            "tests_passed",
            "tests_failed",
            "tests_not_executed",
            "unsafe_tokens",
            "delegation_tokens",
            "rust_source_files",
        ):
            if int(jsonl_row.get(field, 0)) != _required_int(csv_row, field):
                raise ValueError(f"ACToR CSV/JSONL mismatch for {key}: {field}")
        for field in (
            "build",
            "pass_all",
            "safe_rust",
            "self_contained",
            "safe_pass_all",
            "contract_integrity",
            "candidate_runtime_isolated",
        ):
            if bool(jsonl_row.get(field)) != _bool(csv_row.get(field)):
                raise ValueError(f"ACToR CSV/JSONL mismatch for {key}: {field}")
        for field in ("run_status", "evaluation_status", "candidate_status"):
            if str(jsonl_row.get(field, "")) != csv_row.get(field, ""):
                raise ValueError(f"ACToR CSV/JSONL mismatch for {key}: {field}")

    qualification = _load_csv(
        evaluation_root / "oracle-qualification" / "qualification.csv"
    )
    qualification_by_subject = {
        row.get("subject", ""): row for row in qualification
    }
    if set(qualification_by_subject) != set(ACTOR_LI_DENOMINATORS):
        raise ValueError("ACToR oracle qualification subject set drifted")
    for subject, expected in ACTOR_LI_DENOMINATORS.items():
        row = qualification_by_subject[subject]
        if not (
            _bool(row.get("qualified"))
            and _bool(row.get("candidate_runtime_isolated"))
            and _required_int(row, "expected_tests") == expected
            and _required_int(row, "loaded") == expected
            and _required_int(row, "passed") == expected
            and _required_int(row, "failed") == 0
            and _required_int(row, "total") == expected
        ):
            raise ValueError(f"invalid ACToR oracle qualification: {row}")
    qualification_summary = C.read_json(
        evaluation_root / "oracle-qualification" / "summary.json"
    )
    if (
        qualification_summary.get("status") != "passed"
        or qualification_summary.get("subjects") != 6
        or qualification_summary.get("expected_tests") != 492
        or qualification_summary.get("passed_tests") != 492
    ):
        raise ValueError("invalid ACToR qualification summary")

    controls = _load_csv(evaluation_root / "negative_controls.csv")
    controls_by_subject = {row.get("subject", ""): row for row in controls}
    if set(controls_by_subject) != set(ACTOR_LI_DENOMINATORS):
        raise ValueError("ACToR negative-control subject set drifted")
    for subject, expected in ACTOR_LI_DENOMINATORS.items():
        row = controls_by_subject[subject]
        if not (
            _bool(row.get("discriminating"))
            and _bool(row.get("candidate_runtime_isolated"))
            and _required_int(row, "expected_tests") == expected
            and _required_int(row, "loaded") == expected
            and _required_int(row, "total") == expected
            and _required_int(row, "passed") < expected
        ):
            raise ValueError(f"invalid ACToR negative control: {row}")

    seal = C.read_json(evaluation_root / "campaign-seal.json")
    seal_keys = {
        (row.get("subject_id", "").removeprefix("actor-li__"), row["repetition"])
        for row in seal.get("cells", [])
        if row.get("status") in {"completed", "failed", "timeout"}
        and row.get("state_sha256")
    }
    if seal.get("cell_count") != 18 or seal_keys != expected_keys:
        raise ValueError("ACToR campaign seal is incomplete")

    manifest_rows = _load_csv(
        evaluation_root / "oracle_contract_manifest.csv"
    )
    contracts = evaluation_root / "oracle-contracts"
    manifest_paths: set[str] = set()
    tree_hashes: dict[str, set[str]] = {
        subject: set() for subject in ACTOR_LI_DENOMINATORS
    }
    for row in manifest_rows:
        relative_text = row.get("relative_path", "")
        relative = Path(relative_text)
        subject = row.get("subject", "")
        if (
            not relative_text
            or relative.is_absolute()
            or ".." in relative.parts
            or subject not in ACTOR_LI_DENOMINATORS
            or not relative.parts
            or relative.parts[0] != subject
            or relative_text in manifest_paths
        ):
            raise ValueError(f"invalid ACToR contract manifest row: {row}")
        path = contracts / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != _required_int(row, "bytes")
            or C.sha256_file(path) != row.get("sha256")
        ):
            raise ValueError(f"ACToR contract hash mismatch: {relative_text}")
        manifest_paths.add(relative.as_posix())
        tree_hashes[subject].add(row.get("artifact_tree_sha256", ""))
    actual_paths = {
        path.relative_to(contracts).as_posix()
        for path in contracts.rglob("*")
        if path.is_file()
    }
    if actual_paths != manifest_paths:
        raise ValueError("ACToR contract manifest does not cover exact file set")
    for subject, hashes in tree_hashes.items():
        actual_tree_hash = _tree_sha256(contracts / subject)
        if hashes != {actual_tree_hash}:
            raise ValueError(f"ACToR contract tree hash mismatch: {subject}")

    aggregates = _load_csv(evaluation_root / "aggregate.csv")
    aggregate_by_subject = {row.get("subject", ""): row for row in aggregates}
    if set(aggregate_by_subject) != {*ACTOR_LI_DENOMINATORS, "ALL"}:
        raise ValueError("ACToR aggregate subject set drifted")
    recomputed_groups: dict[str, dict[str, Any]] = {}
    for subject in [*ACTOR_LI_DENOMINATORS, "ALL"]:
        selected = (
            rows if subject == "ALL" else [row for row in rows if row["subject"] == subject]
        )
        expected_total = sum(
            _required_int(row, "expected_tests") for row in selected
        )
        group: dict[str, Any] = {
            "cells": len(selected),
            "measured_cells": len(selected),
            "build_cells": sum(_bool(row.get("build")) for row in selected),
            "pass_all_cells": sum(
                _bool(row.get("pass_all")) for row in selected
            ),
            "safe_cells": sum(
                _bool(row.get("safe_rust")) for row in selected
            ),
            "self_contained_cells": sum(
                _bool(row.get("self_contained")) for row in selected
            ),
            "safe_pass_all_cells": sum(
                _bool(row.get("safe_pass_all")) for row in selected
            ),
            "tests_passed": sum(
                _required_int(row, "tests_passed") for row in selected
            ),
            "tests_expected": expected_total,
        }
        aggregate_row = aggregate_by_subject[subject]
        if any(
            _required_int(aggregate_row, key) != value
            for key, value in group.items()
        ):
            raise ValueError(
                f"ACToR {subject} aggregate does not match raw cell evidence"
            )
        expected_rate = (
            100 * group["tests_passed"] / expected_total
            if expected_total
            else 0.0
        )
        if abs(float(aggregate_row["test_rate_percent"]) - expected_rate) > 1e-9:
            raise ValueError(f"ACToR {subject} aggregate rate mismatch")
        for aggregate_field, raw_field in (
            ("elapsed_seconds", "elapsed_seconds"),
            ("output_tokens", "total_output_tokens"),
            ("nano_aiu", "total_nano_aiu"),
            ("premium_requests", "total_premium_requests"),
        ):
            values = [
                float(row[raw_field])
                for row in selected
                if row.get(raw_field) not in ("", None)
            ]
            expected_status = (
                "measured"
                if len(values) == len(selected)
                else "partial"
                if values
                else "unavailable"
            )
            actual_value = aggregate_row.get(aggregate_field)
            if (
                aggregate_row.get(f"{aggregate_field}_status")
                != expected_status
                or _required_int(
                    aggregate_row, f"{aggregate_field}_measured_cells"
                )
                != len(values)
                or (
                    values
                    and abs(float(actual_value) - sum(values)) > 1e-6
                )
                or (not values and actual_value not in ("", None))
            ):
                raise ValueError(
                    f"ACToR {subject} telemetry aggregate mismatch: "
                    f"{aggregate_field}"
                )
        recomputed_groups[subject] = group
    recomputed = recomputed_groups["ALL"]

    summary = C.read_json(evaluation_root / "summary.json")
    expected_summary = {
        "rows": 18,
        "expected_rows": 18,
        "measured": 18,
        "build_passed": recomputed["build_cells"],
        "pass_all": recomputed["pass_all_cells"],
        "safe_rust": recomputed["safe_cells"],
        "self_contained": recomputed["self_contained_cells"],
        "safe_pass_all": recomputed["safe_pass_all_cells"],
        "tests_passed": recomputed["tests_passed"],
        "tests_expected": 1476,
        "negative_control_subjects": 6,
        "negative_control_discriminating_subjects": 6,
        "negative_control_tests_expected": 492,
        "published_oracle_contract_files": len(manifest_rows),
        "published_oracle_contract_subjects": 6,
        "sealed_cells": 18,
    }
    if (
        not summary.get("complete")
        or summary.get("oracle_qualification") != "passed"
        or summary.get("candidate_runtime_isolation")
        != "mount-pid-namespace-chroot-no-capabilities"
        or any(summary.get(key) != value for key, value in expected_summary.items())
    ):
        raise ValueError(f"ACToR summary does not match raw evidence: {summary}")
    if summary.get("negative_control_tests_passed") != sum(
        _required_int(row, "passed") for row in controls
    ):
        raise ValueError("ACToR negative-control summary mismatch")
    summary_aggregate = summary.get("aggregate") or {}
    if any(summary_aggregate.get(key) != value for key, value in recomputed.items()):
        raise ValueError("ACToR summary aggregate mismatch")

    macro = C.read_json(evaluation_root / "macro_experiment_status.json")
    if (
        macro.get("status") != "blocked_reference_only"
        or macro.get("subject_count") != 57
        or len(macro.get("subjects", [])) != 57
    ):
        raise ValueError("ACToR macro blocker record drifted")
    return summary, aggregates


def _copy_actor_li_evidence(
    root: Path,
    *,
    evaluation_root: Path | None,
    runs_root: Path | None,
) -> tuple[dict[str, Any] | None, list[dict[str, str]], dict[str, Any] | None]:
    def verify_archive(inventory: dict[str, Any], label: str) -> None:
        if inventory.get("file_count", 0) <= 0:
            raise ValueError(f"ACToR {label} archive is empty")
        for part in inventory.get("parts", []):
            path = root / part["path"]
            if (
                not path.is_file()
                or path.stat().st_size != int(part["bytes"])
                or C.sha256_file(path) != part["sha256"]
            ):
                raise ValueError(f"invalid ACToR {label} archive part: {path}")

    if evaluation_root is None:
        return None, [], None
    summary, aggregates = _validate_actor_li_evaluation(evaluation_root)
    _assert_no_credentials(evaluation_root)
    destination = root / "data" / "actor-li"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(evaluation_root, destination)
    license_path = evaluation_root / "metadata" / "ACToR-MIT.txt"
    if not license_path.is_file():
        raise FileNotFoundError(license_path)
    (root / "licenses").mkdir(parents=True, exist_ok=True)
    shutil.copy2(license_path, root / "licenses" / "ACToR-MIT.txt")
    archive_inventory = None
    if runs_root is not None:
        _assert_no_credentials(runs_root, predicate=_related_run_file)
        archive_inventory = _archive(
            runs_root,
            root / "raw-run-archives" / "actor-li.tar.gz",
            prefix="actor-li-runs",
            max_part_bytes=90_000_000,
            predicate=_related_run_file,
        )
        verify_archive(archive_inventory, "filtered run")
        infrastructure = runs_root.parent / "infrastructure-failures"
        if infrastructure.is_dir():
            _assert_no_credentials(
                infrastructure,
                predicate=_related_run_file,
            )
            infrastructure_archive = _archive(
                infrastructure,
                root
                / "infrastructure-failure-archives"
                / "actor-li-pre-model.tar.gz",
                prefix="actor-li-infrastructure-failures",
                max_part_bytes=90_000_000,
                predicate=_related_run_file,
            )
            verify_archive(infrastructure_archive, "infrastructure-failure")
            archive_inventory["infrastructure_failures"] = infrastructure_archive
        C.atomic_write_json(
            root / "metadata" / "actor_li_archive_inventory.json",
            archive_inventory,
        )
    return summary, aggregates, archive_inventory


def _profile_reference_tables(key: str) -> list[tuple[str, list[dict[str, Any]]]]:
    prefixes = {
        "orbit": ("orbit_",),
        "actor-schesch-ernst": ("actor_schesch_",),
        "rustprint": ("rustprint_",),
        "ptrtrans": ("ptrtrans_",),
        "actor-li": ("actor_li_",),
    }
    tables = [
        (name, rows)
        for name, rows in CITER_REFERENCE_TABLES.items()
        if name.startswith(prefixes.get(key, (f"{key}_",)))
    ]
    blocked_name = {"rustassure": "RustAssure", "deptrans": "DepTrans"}.get(key)
    if blocked_name:
        blocked = [
            row
            for row in CITER_REFERENCE_TABLES["blocked_aggregate_references.csv"]
            if row["paper"] == blocked_name
        ]
        if blocked:
            tables.append(("blocked_aggregate_references.csv", blocked))
    return tables


def _display_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[str], list[list[Any]]]:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return fields, [[row.get(field, "") for field in fields] for row in rows]


def _write_paper_profiles(
    root: Path,
    *,
    evidence: list[dict[str, Any]],
    orbit_summary: list[dict[str, Any]],
    actor_public_summary: list[dict[str, Any]],
    actor_li_aggregate: list[dict[str, Any]],
    lac2r: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_study = {row["study"].lower(): row for row in evidence}
    extra: dict[str, list[tuple[str, list[dict[str, Any]]]]] = {
        "orbit": [("CodeWeaver exact 24-project summary", orbit_summary)],
        "actor-schesch-ernst": [
            ("CodeWeaver public-artifact 95-project overlap", actor_public_summary)
        ],
        "actor-li": (
            [("CodeWeaver six-program hidden-oracle result", actor_li_aggregate)]
            if actor_li_aggregate
            else []
        ),
        "lac2r": [("CodeWeaver name-overlap audit", lac2r)],
        "taco": [("CRUST-Bench terminal-agent reference", [TACO_CRUST_REFERENCE])],
    }
    profiles: list[dict[str, Any]] = []
    for inclusion in INCLUSION_MATRIX:
        key = inclusion["key"]
        citation = next(
            row for row in CITATION_RECORDS if row["canonical_key"] == key
        )
        profile_root = root / "paper-profiles" / key
        surfaces = [row for row in CITER_SURFACES if row["key"] == key]
        _write_csv(profile_root / "surface_inventory.csv", surfaces)
        reference_tables = _profile_reference_tables(key)
        for filename, rows in reference_tables:
            _write_csv(profile_root / "reference" / filename, rows)
        tables: list[tuple[str, list[str], list[list[Any]]]] = []
        surface_headers, surface_rows = _display_rows(surfaces)
        tables.append(("Complete empirical-surface audit", surface_headers, surface_rows))
        decision = {
            "paper_id": inclusion["paper_id"],
            "source_url": citation["source_url"],
            "empirical_scope": inclusion["empirical_scope"],
            "crust_role": inclusion["crust_role"],
            "codeweaver_status": inclusion["codeweaver_status"],
            "reason": inclusion["reason"],
            "existing_result": inclusion["existing_result"],
        }
        inclusion_headers, inclusion_rows = _display_rows([decision])
        tables.append(
            ("Inclusion and execution decision", inclusion_headers, inclusion_rows)
        )
        for filename, rows in [*reference_tables, *extra.get(key, [])]:
            if not rows:
                continue
            headers, display = _display_rows(rows)
            tables.append((filename.removesuffix(".csv"), headers, display))
        existing = next(
            (
                row
                for label, row in evidence_by_study.items()
                if key in label
                or inclusion["title"].lower() in label
            ),
            None,
        )
        abstract = (
            f"This profile audits every empirical surface identified for "
            f"{inclusion['title']} and records the maximum scientifically "
            "defensible CodeWeaver comparison. "
            f"Status: {inclusion['codeweaver_status']}. "
            f"{inclusion['reason']}."
        )
        sections = [
            (
                "Evidence boundary",
                "Paper values and CodeWeaver measurements remain separate unless "
                "subject identity, revision, denominator, and fixed oracle are "
                "verified. Missing values are not converted to zeros.",
            ),
            (
                "Existing result",
                (
                    f"{existing['headline']} ({existing['result_path']})."
                    if existing
                    else (
                        inclusion["existing_result"]
                        or "No separate compatible CodeWeaver result package."
                    )
                ),
            ),
        ]
        markdown = [f"# {inclusion['title']}: CodeWeaver evidence profile", ""]
        markdown += ["## Abstract", "", abstract, ""]
        for heading, body in sections:
            markdown += [f"## {heading}", "", body, ""]
        for heading, headers, rows in tables:
            markdown += [f"## {heading}", "", _markdown_table(headers, rows), ""]
        C.atomic_write_text(profile_root / "comparison.md", "\n".join(markdown))
        _render_pdf(
            profile_root / "comparison.pdf",
            title=f"{inclusion['title']}: CodeWeaver evidence profile",
            abstract=abstract,
            sections=sections,
            tables=tables,
        )
        metadata = {
            "schema_version": 1,
            "generated_at": C.utcnow_iso(),
            "key": key,
            "paper_id": inclusion["paper_id"],
            "source_url": citation["source_url"],
            "status": inclusion["codeweaver_status"],
            "surface_rows": len(surfaces),
            "structured_reference_tables": len(reference_tables),
            "pdf": "comparison.pdf",
        }
        C.atomic_write_json(profile_root / "metadata.json", metadata)
        profiles.append(metadata)
    _write_csv(root / "paper-profiles" / "index.csv", profiles)
    return profiles


def build(
    *,
    historical_raw: Path,
    output_root: Path,
    actor_li_evaluation: Path | None = None,
    actor_li_runs: Path | None = None,
) -> Path:
    if actor_li_runs is not None and actor_li_evaluation is None:
        raise ValueError("--actor-li-runs requires --actor-li-evaluation")
    repository_root = Path(__file__).resolve().parents[2]
    root = output_root / RESULT_NAMES["citations"]
    historical_rows = _load_csv(historical_raw)
    orbit_rows, orbit_summary = _orbit_rows(historical_rows)
    actor_public_rows, actor_public_summary = _actor_public_95_rows(
        historical_rows
    )
    lac2r = _lac2r_intersection(repository_root)
    evidence = _existing_evidence(repository_root)
    actor_li_summary, actor_li_aggregate, actor_li_archive = (
        _copy_actor_li_evidence(
            root,
            evaluation_root=actor_li_evaluation,
            runs_root=actor_li_runs,
        )
    )
    _write_csv(root / "data" / "citation_census.csv", CITATION_RECORDS)
    _write_jsonl(root / "data" / "citation_census.jsonl", CITATION_RECORDS)
    _write_csv(root / "data" / "inclusion_matrix.csv", INCLUSION_MATRIX)
    _write_csv(root / "data" / "paper_surface_inventory.csv", CITER_SURFACES)
    _write_csv(root / "data" / "orbit_24_subject_comparison.csv", orbit_rows)
    _write_csv(root / "data" / "orbit_summary.csv", orbit_summary)
    _write_csv(
        root / "data" / "actor_public_95_project_overlap.csv",
        actor_public_rows,
    )
    _write_csv(
        root / "data" / "actor_public_95_codeweaver_summary.csv",
        actor_public_summary,
    )
    _write_csv(root / "data" / "lac2r_name_intersection.csv", lac2r)
    _write_csv(root / "data" / "existing_evidence.csv", evidence)
    _write_csv(
        root / "data" / "taco_crust_reference.csv",
        [TACO_CRUST_REFERENCE],
    )
    _copy_reused_summaries(root, repository_root)
    for filename, reference_rows in CITER_REFERENCE_TABLES.items():
        _write_csv(root / "data" / "paper-reference" / filename, reference_rows)
    profiles = _write_paper_profiles(
        root,
        evidence=evidence,
        orbit_summary=orbit_summary,
        actor_public_summary=actor_public_summary,
        actor_li_aggregate=actor_li_aggregate,
        lac2r=lac2r,
    )
    counts: dict[str, int] = {}
    for row in CITATION_RECORDS:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    orbit_codeweaver_rates = [
        float(row["test_success_percent"]) for row in orbit_summary[2:]
    ]
    summary = {
        "census_date": CENSUS_DATE,
        "semantic_scholar_records": len(CITATION_RECORDS),
        "classification_counts": counts,
        "unique_in_scope_works": 19,
        "taco_included_as_empirical_tangential_work": True,
        "comparison_matrix_rows": len(INCLUSION_MATRIX),
        "empirical_surface_rows": len(CITER_SURFACES),
        "structured_reference_tables": len(CITER_REFERENCE_TABLES),
        "paper_profiles": len(profiles),
        "orbit": {
            "subjects": 24,
            "orbit_expert_builds": 24,
            "orbit_expert_test_successes": 22,
            "orbit_generated_builds": 24,
            "orbit_generated_test_successes": 22,
            "codeweaver_build_cells": sum(
                int(row["build_successes"]) for row in orbit_summary[2:]
            ),
            "codeweaver_pass_all_cells": sum(
                int(row["test_successes"]) for row in orbit_summary[2:]
            ),
            "codeweaver_mean_project_pass_percent": statistics.mean(
                orbit_codeweaver_rates
            ),
        },
        "actor_schesch_ernst": {
            "paper_crust_denominator": 87,
            "paper_membership_recoverable": False,
            "public_result_directories": 95,
            "public_overlap_codeweaver_cells": 285,
            "excluded_from_public_overlap": sorted(
                ACTOR_PUBLIC_MISSING_PROJECT_IDS
            ),
            "comparison_policy": (
                "paper-87 references and public-artifact-95 CodeWeaver overlap "
                "are reported separately"
            ),
        },
        "actor_li": (
            actor_li_summary
            if actor_li_summary is not None
            else {
                "status": "not_supplied",
                "absolute_micro_campaign": "pending",
                "macro_campaign": "blocked_relative_oracle",
            }
        ),
        "actor_li_raw_archive": actor_li_archive,
        "policy": (
            "new scores are published only for exact retained subjects with fixed "
            "oracles; all other works are explicit reference-only, not-comparable, "
            "or blocked records"
        ),
    }
    C.atomic_write_json(root / "data" / "summary.json", summary)

    orbit_display = [
        [
            row["system"],
            f"{row['build_successes']}/{row['projects']}",
            (
                f"{row['test_successes']}/{row['projects']} "
                f"({_percent(float(row['test_success_percent']))})"
            ),
            (
                f"{row['fixed_tests_passed']}/{row['fixed_tests_expected']}"
                if row["fixed_tests_expected"] != ""
                else "not reported"
            ),
            row["protocol"],
        ]
        for row in orbit_summary
    ]
    subject_display = [
        [
            row["project"],
            row["loc"],
            "pass" if row["orbit_ext_test"] else "fail",
            "pass" if row["orbit_gen_test"] else "fail",
            f"{row['codeweaver_pass_all_repetitions']}/3",
            f"{row['codeweaver_tests_passed']}/{row['codeweaver_tests_expected']}",
        ]
        for row in orbit_rows
    ]
    actor_public_display = [
        [
            row["system"],
            f"{row['build_successes']}/{row['public_artifact_projects']}",
            f"{row['test_successes']}/{row['public_artifact_projects']}",
            f"{row['fixed_tests_passed']}/{row['fixed_tests_expected']}",
            row["paper_membership_status"],
        ]
        for row in actor_public_summary
    ]
    actor_li_display = [
        [
            row["subject"],
            f"{row['build_cells']}/{row['cells']}",
            f"{row['pass_all_cells']}/{row['cells']}",
            f"{row['safe_pass_all_cells']}/{row['cells']}",
            f"{row['tests_passed']}/{row['tests_expected']}",
            _percent(float(row["test_rate_percent"])),
        ]
        for row in actor_li_aggregate
    ]

    def actor_telemetry(
        row: dict[str, str],
        field: str,
        *,
        scale: float = 1.0,
        digits: int | None = None,
    ) -> str:
        value = row.get(field)
        status = row.get(f"{field}_status", "unavailable")
        if value in (None, ""):
            return f"unavailable ({status})"
        numeric = float(value) / scale
        rendered = f"{numeric:.{digits}f}" if digits is not None else str(int(numeric))
        if status != "measured":
            measured = row.get(f"{field}_measured_cells", "0")
            rendered += f" ({status} {measured}/{row['cells']})"
        return rendered

    actor_li_telemetry_display = [
        [
            row["subject"],
            actor_telemetry(
                row, "elapsed_seconds", scale=3600, digits=2
            ),
            actor_telemetry(row, "output_tokens"),
            actor_telemetry(row, "nano_aiu", scale=1_000_000_000, digits=3),
            actor_telemetry(row, "premium_requests"),
        ]
        for row in actor_li_aggregate
    ]
    inclusion_display = [
        [
            row["title"],
            row["empirical_scope"],
            row["codeweaver_status"],
            row["reason"],
        ]
        for row in INCLUSION_MATRIX
    ]
    census_display = [
        [
            "Semantic Scholar records",
            30,
            "19 unique in-scope + 8 tangential + 1 out-of-scope + 2 duplicates",
        ],
        ["Unique in-scope works", 19, "all included in the decision matrix"],
        ["Tangential works", 8, "TACO retained because it evaluates CRUST-Bench"],
        ["Duplicate index records", 2, "resolved to Hayroll and Schesch/Ernst ACTOR"],
    ]
    evidence_display = [
        [row["study"], row["scope"], row["headline"], row["result_path"]]
        for row in evidence
    ]
    tables = [
        (
            "Citation reconciliation",
            ["Population", "Count", "Disposition"],
            census_display,
        ),
        (
            "Exact ORBIT 24-project comparison",
            ["System", "Build", "Pass all", "Fixed tests", "Protocol"],
            orbit_display,
        ),
        (
            "ORBIT per-subject outcomes",
            [
                "Project",
                "LoC",
                "ORBIT expert",
                "ORBIT generated",
                "CW passing reps",
                "CW fixed tests",
            ],
            subject_display,
        ),
        (
            "Existing publication-ready CodeWeaver evidence",
            ["Study", "Scope", "Headline", "Result path"],
            evidence_display,
        ),
        (
            "Schesch/Ernst ACTOR public-artifact 95-project overlap",
            ["System", "Build", "Pass all", "Fixed tests", "Boundary"],
            actor_public_display,
        ),
        (
            "Li et al. ACToR six-program absolute hidden-oracle result",
            [
                "Subject",
                "Build",
                "Pass all",
                "Safe pass",
                "Hidden tests",
                "Test rate",
            ],
            actor_li_display
            or [
                [
                    "not supplied",
                    "not measured",
                    "not measured",
                    "not measured",
                    "not measured",
                    "not measured",
                ]
            ],
        ),
        (
            "Li et al. ACToR CodeWeaver execution telemetry",
            ["Subject", "Elapsed hours", "Output tokens", "AIU", "Premium requests"],
            actor_li_telemetry_display
            or [
                [
                    "not supplied",
                    "not measured",
                    "not measured",
                    "not measured",
                    "not measured",
                ]
            ],
        ),
        (
            "Li et al. ACToR published reference results",
            ["Surface", "Scope", "System", "Metric", "Value", "Uncertainty"],
            [
                [
                    row["surface"],
                    row["scope"],
                    row["system"],
                    row["metric"],
                    row["value"],
                    row["uncertainty"] or "not reported",
                ]
                for row in CITER_REFERENCE_TABLES["actor_li_reference.csv"]
            ],
        ),
        (
            "Complete inclusion and execution matrix",
            ["Paper", "Empirical scope", "Status", "Reason"],
            inclusion_display,
        ),
        (
            "ACTOR CRUST-Bench reference (Figure 6)",
            ["System", "Setting", "Build", "Pass all", "LoC", "Unsafe"],
            [
                [
                    row["system"],
                    row["setting"],
                    f"{row['builds']}/{row['denominator']}",
                    f"{row['tests']}/{row['denominator']}",
                    row["loc"] or "not reported",
                    (
                        f"{row['unsafe_percent']}%"
                        if row["unsafe_percent"] != ""
                        else "not reported"
                    ),
                ]
                for row in CITER_REFERENCE_TABLES[
                    "actor_schesch_figure6_crust.csv"
                ]
            ],
        ),
        (
            "Public-artifact reference highlights",
            ["Paper", "Scope", "System", "Metric", "Value"],
            [
                [
                    "RustPrint",
                    row["denominator"],
                    row["system"],
                    row["metric"],
                    row["value"],
                ]
                for row in CITER_REFERENCE_TABLES["rustprint_reference.csv"]
            ]
            + [
                [
                    "PtrTrans",
                    row["scope"],
                    row["system"],
                    row["metric"],
                    row["value"],
                ]
                for row in CITER_REFERENCE_TABLES["ptrtrans_reference.csv"]
            ],
        ),
    ]
    actor_li_abstract = (
        "and ACToR's six-program absolute experiment is newly evaluated with a "
        "qualified 492-case hidden differential oracle over 18 CodeWeaver cells"
        if actor_li_summary is not None
        else "and ACToR's six-program absolute experiment is wired to a qualified "
        "492-case hidden differential oracle (the optional 18-cell result was "
        "not supplied to this render)"
    )
    abstract = (
        "We reconciled all 30 Semantic Scholar citation records for CRUST-Bench "
        "into 19 unique migration-relevant works, eight tangential works, one "
        "out-of-scope work, and two duplicate records. Every in-scope work and "
        "every empirical surface found in its paper is inventoried. ORBIT's exact "
        "24-project subset is newly evaluated from the frozen CodeWeaver "
        f"three-repetition campaign, {actor_li_abstract}. Schesch/Ernst ACTOR's "
        "paper-87 values are separated "
        "from the pinned public artifact's 95 project directories. Other scores "
        "are reused only where subject "
        "identity and fixed contracts were already verified. Unreleased or "
        "metric-incompatible studies remain explicit blockers, never synthetic "
        "zeros or inferred wins."
    )
    sections = [
        (
            "Census method",
            "The primary citation graph was Semantic Scholar's complete 30-record "
            "edge list as of 18 August 2026, cross-checked against OpenAlex, arXiv, "
            "publisher pages, and artifact repositories. InariRoll was resolved as "
            "a Hayroll duplicate, and two title variants were resolved as one "
            "Schesch/Ernst ACTOR paper.",
        ),
        (
            "Measurement rule",
            "A CodeWeaver score is included only when the exact retained subject "
            "and a fixed independent oracle are available. Shared names without "
            "revision/hash equality, function-level validation metrics, interface "
            "inference, annotation synthesis, and terminal-agent task accuracy are "
            "not relabeled as repository pass-all.",
        ),
        (
            "ORBIT result",
            f"ORBIT reports 22/24 test-successful projects in both interface modes. "
            f"Across the same 24 named projects, CodeWeaver's three repetitions "
            f"average {statistics.mean(orbit_codeweaver_rates):.2f}% project "
            "pass-all. ORBIT is an apparent single run while CodeWeaver retains "
            "all three outcomes, so this is an exact-subject descriptive "
            "comparison rather than a controlled architecture ablation.",
        ),
        (
            "ACToR absolute micro result",
            (
                "The pinned Li et al. artifact exposes six micro utilities, 15 "
                "seed tests per utility, and a separate fixed validation suite "
                "of 70, 100, 66, 84, 83, and 89 cases (492 total). Each C "
                "reference passed its own full contract before the validation "
                "files were kept outside all model-readable workspaces. "
                + (
                    f"Across 18 CodeWeaver cells, "
                    f"{actor_li_summary['pass_all']}/18 passed every hidden case "
                    f"and {actor_li_summary['safe_pass_all']}/18 also contained "
                    "no candidate-owned `unsafe` token or process delegation. "
                    "Candidate binaries ran in a mount/PID-namespace chroot "
                    "where reference and contract contents were masked by "
                    "read-only empty mounts, Linux capabilities were cleared, "
                    "and system executables were absent. All six compiling stub "
                    "negative controls failed the full contract "
                    f"({actor_li_summary['negative_control_tests_passed']}/"
                    f"{actor_li_summary['negative_control_tests_expected']} "
                    "cases passed), confirming that pass-all is non-vacuous."
                    if actor_li_summary is not None
                    else "The optional 18-cell CodeWeaver result was not supplied "
                    "to this render."
                )
                + (
                    " The public fixed contracts are included in the result "
                    "package only after execution, with per-file checksums."
                    if actor_li_summary is not None
                    else ""
                )
                + (
                    " A fully pre-model unauthenticated launcher attempt is "
                    "archived as infrastructure evidence and excluded from all "
                    "18 measured cells."
                    if actor_li_archive
                    and actor_li_archive.get("infrastructure_failures")
                    else ""
                )
                + " The shared fixed oracle supports a same-subject descriptive "
                "comparison, not a controlled ACToR architecture ablation: "
                "CodeWeaver uses its frozen five-repair, three-parity protocol, "
                "whereas the paper reports naive, collaborative, and ten-iteration "
                "ACToR configurations."
            ),
        ),
        (
            "ACTOR denominator boundary",
            "Schesch and Ernst report Figure 6 over 87 CRUST-Bench projects, "
            "but the pinned public results submodule contains 95 CRUST project "
            "directories and does not encode the paper's 13-project exclusion "
            "set. The paper's 87-denominator values therefore remain exact "
            "references only. CodeWeaver outcomes over the independently "
            "verifiable 95-directory overlap are a separate table and are never "
            "labeled as a reproduction of Figure 6.",
        ),
        (
            "Availability boundary",
            "RustPrint, DepTrans, PtrTrans, RustAssure, and "
            "several adjacent systems do not expose the exact evaluated revisions "
            "and fixed contracts needed for leakage-safe execution. Li et al. "
            "ACToR's 57-program macro metric remains blocked because it is "
            "cross-testing against unreleased system-generated outputs/tests, "
            + (
                "while its six-program absolute experiment is measured here. "
                if actor_li_summary is not None
                else "while its six-program absolute result was not supplied "
                "to this render. "
            )
            + "Schesch/Ernst ACTOR's exact paper-87 membership remains unresolved. "
            "EvoC2Rust's "
            "C2R-Bench/industrial set and DepTrans's Huawei set are explicitly "
            "unreleased. The package records these blockers and the maximum public "
            "comparison for each paper.",
        ),
        (
            "Prior-result audit",
            "The five earlier paper packages now include a complete source-paper "
            "surface inventory, structured reference tables for previously omitted "
            "dataset/error/cost/ablation results, CodeWeaver cost and coverage "
            "telemetry, corrected version labels, and final-output Clippy analysis "
            "where executable.",
        ),
        (
            "Per-paper publication profiles",
            "The `paper-profiles/` directory contains one human-readable PDF, "
            "Markdown report, complete empirical-surface inventory, decision "
            "record, and available structured reference tables for each of the "
            "20 included works. These profiles link compatible standalone "
            "CodeWeaver packages and retain blockers for incompatible surfaces.",
        ),
    ]
    _write_report_files(
        root,
        key="citations",
        abstract=abstract,
        sections=sections,
        tables=tables,
        figure=(
            ["ORBIT expert", "ORBIT generated", "CW rep 1", "CW rep 2", "CW rep 3"],
            [
                (
                    "Project pass-all",
                    [91.6666666667, 91.6666666667, *orbit_codeweaver_rates],
                    "#f58518",
                )
            ],
        ),
        provenance={
            "generated_at": C.utcnow_iso(),
            "census_date": CENSUS_DATE,
            "citation_source": (
                "Semantic Scholar graph API for arXiv:2504.15254; "
                "30 records reconciled with primary papers and artifacts"
            ),
            "historical_raw": str(historical_raw),
            "historical_raw_sha256": C.sha256_file(historical_raw),
            "protocol": PROTOCOL,
            "orbit_source": "https://arxiv.org/abs/2604.12048",
            "taco_source": "https://arxiv.org/abs/2604.19572",
            "actor_schesch_artifact": {
                "repository": "https://github.com/UW-HARVEST/ACTOR",
                "commit": "55502661b2bff3019d3c1e72481f7b99cc247aaa",
                "results_submodule_commit": (
                    "b3fd93fcff6da0570ca00d59223b3edac15077eb"
                ),
                "public_crust_result_directories": 95,
                "paper_crust_denominator": 87,
            },
            "actor_li_evaluation": (
                {
                    "path": str(actor_li_evaluation),
                    "summary_sha256": C.sha256_file(
                        actor_li_evaluation / "summary.json"
                    ),
                    "artifact_commit": actor_li_summary["artifact_commit"],
                }
                if actor_li_evaluation is not None
                and actor_li_summary is not None
                else None
            ),
        },
        availability=[
            {
                "surface": "30-record citation census",
                "status": "measured",
                "reason": "complete Semantic Scholar citation graph and deduplication",
                "measurement_track": "citation census",
            },
            {
                "surface": "ORBIT 24-project CRUST-Bench subset",
                "status": "measured_existing_slice",
                "reason": "all names map exactly to frozen CodeWeaver rows",
                "measurement_track": "CodeWeaver three-repetition",
            },
            {
                "surface": "existing ReCodeAgent/SACTOR/Rustine/EvoC2Rust evidence",
                "status": "reused_verified",
                "reason": "previous packages contain provenance and independent oracles",
                "measurement_track": "published CodeWeaver artifacts",
            },
            {
                "surface": "Li et al. ACToR six-program absolute experiment",
                "status": (
                    "measured"
                    if actor_li_summary is not None
                    else "not_supplied"
                ),
                "reason": (
                    "18 independently evaluated cells against a qualified "
                    "492-case fixed differential oracle"
                    if actor_li_summary is not None
                    else "evaluation path was not supplied to this render"
                ),
                "measurement_track": "CodeWeaver three-repetition hidden oracle",
            },
            {
                "surface": "Li et al. ACToR 57-program macro experiment",
                "status": "blocked",
                "reason": (
                    "relative cross-testing requires unreleased ACToR and "
                    "coverage-baseline outputs and their generated tests"
                ),
                "measurement_track": "reference only",
            },
            {
                "surface": "Schesch/Ernst ACTOR CRUST result",
                "status": "reference_87_and_measured_public_95_overlap",
                "reason": (
                    "paper denominator is 87 but pinned artifact exposes 95 "
                    "directories without the exact paper exclusion set"
                ),
                "measurement_track": "separate paper reference / public overlap",
            },
            {
                "surface": "unreleased citer benchmarks",
                "status": "blocked",
                "reason": "exact sources, revisions, or fixed contracts unavailable",
                "measurement_track": "reference only",
            },
            {
                "surface": "task-incompatible citer evaluations",
                "status": "not_comparable",
                "reason": "different output unit or validation metric",
                "measurement_track": "reference only",
            },
        ],
    )
    _render_figure(
        root / "report" / "actor_public_95_figure.pdf",
        root / "report" / "actor_public_95_figure.svg",
        title="CodeWeaver on ACTOR's 95 public result directories",
        categories=[f"Rep {index}" for index in range(1, 4)],
        series=[
            (
                "Build",
                [
                    100
                    * float(row["build_successes"])
                    / float(row["public_artifact_projects"])
                    for row in actor_public_summary
                ],
                "#4c78a8",
            ),
            (
                "Pass all",
                [
                    100
                    * float(row["test_successes"])
                    / float(row["public_artifact_projects"])
                    for row in actor_public_summary
                ],
                "#f58518",
            ),
        ],
    )
    if actor_li_aggregate:
        subject_aggregates = [
            row for row in actor_li_aggregate if row["subject"] != "ALL"
        ]
        _render_figure(
            root / "report" / "actor_li_figure.pdf",
            root / "report" / "actor_li_figure.svg",
            title="CodeWeaver on ACToR's fixed hidden oracle",
            categories=[row["subject"] for row in subject_aggregates],
            series=[
                (
                    "Hidden-test rate",
                    [
                        float(row["test_rate_percent"])
                        for row in subject_aggregates
                    ],
                    "#4c78a8",
                ),
                (
                    "Pass-all cells",
                    [
                        100
                        * float(row["pass_all_cells"])
                        / float(row["cells"])
                        for row in subject_aggregates
                    ],
                    "#f58518",
                ),
                (
                    "Safe pass-all cells",
                    [
                        100
                        * float(row["safe_pass_all_cells"])
                        / float(row["cells"])
                        for row in subject_aggregates
                    ],
                    "#54a24b",
                ),
            ],
        )
    report_manifest_path = root / "metadata" / "report_manifest.json"
    report_manifest = C.read_json(report_manifest_path)
    report_manifest["artifact_files"].update(
        {
            "paper_profiles": "paper-profiles/",
            "actor_public_95_figure_pdf": (
                "report/actor_public_95_figure.pdf"
            ),
            "actor_public_95_figure_svg": (
                "report/actor_public_95_figure.svg"
            ),
        }
    )
    if actor_li_summary is not None:
        report_manifest["artifact_files"].update(
            {
                "actor_li_data": "data/actor-li/",
                "actor_li_figure_pdf": "report/actor_li_figure.pdf",
                "actor_li_figure_svg": "report/actor_li_figure.svg",
                "actor_li_raw_runs": "raw-run-archives/",
            }
        )
    C.atomic_write_json(report_manifest_path, report_manifest)
    required = [
        "data/citation_census.csv",
        "data/inclusion_matrix.csv",
        "data/paper_surface_inventory.csv",
        "data/orbit_24_subject_comparison.csv",
        "data/orbit_summary.csv",
        "data/actor_public_95_project_overlap.csv",
        "data/actor_public_95_codeweaver_summary.csv",
        "data/paper-reference/actor_schesch_figure6_crust.csv",
        "data/summary.json",
        "report/comparison.pdf",
        "report/figure.pdf",
        "report/actor_public_95_figure.pdf",
        "report/actor_public_95_figure.svg",
        "metadata/source_provenance.json",
        "paper-profiles/index.csv",
    ]
    required.extend(
        [
            f"paper-profiles/{row['key']}/comparison.md"
            for row in INCLUSION_MATRIX
        ]
        + [
            f"paper-profiles/{row['key']}/comparison.pdf"
            for row in INCLUSION_MATRIX
        ]
        + [
            f"paper-profiles/{row['key']}/surface_inventory.csv"
            for row in INCLUSION_MATRIX
        ]
    )
    if actor_li_summary is not None:
        required.extend(
            [
                "data/actor-li/raw_runs.csv",
                "data/actor-li/raw_runs.jsonl",
                "data/actor-li/aggregate.csv",
                "data/actor-li/summary.json",
                "data/actor-li/campaign-seal.json",
                "data/actor-li/macro_experiment_status.json",
                "data/actor-li/oracle_contract_manifest.csv",
                "data/actor-li/negative_controls.csv",
                "data/actor-li/oracle-qualification/qualification.csv",
                "data/actor-li/oracle-qualification/summary.json",
                "licenses/ACToR-MIT.txt",
                "report/actor_li_figure.pdf",
                "report/actor_li_figure.svg",
            ]
        )
        required.extend(
            "data/actor-li/oracle-contracts/" + row["relative_path"]
            for row in _load_csv(
                root / "data" / "actor-li" / "oracle_contract_manifest.csv"
            )
        )
        if actor_li_runs is not None:
            required.append("metadata/actor_li_archive_inventory.json")
            required.extend(
                str(part["path"]) for part in actor_li_archive["parts"]
            )
            infrastructure_archive = actor_li_archive.get(
                "infrastructure_failures"
            )
            if infrastructure_archive:
                required.extend(
                    str(part["path"])
                    for part in infrastructure_archive["parts"]
                )
    missing = [relative for relative in required if not (root / relative).is_file()]
    pdf_paths = [
        root / "report" / "comparison.pdf",
        root / "report" / "figure.pdf",
        root / "report" / "actor_public_95_figure.pdf",
        *[
            root / "paper-profiles" / row["key"] / "comparison.pdf"
            for row in INCLUSION_MATRIX
        ],
    ]
    if actor_li_summary is not None:
        pdf_paths.append(root / "report" / "actor_li_figure.pdf")
    pdf_valid = all(
        path.is_file() and path.read_bytes().startswith(b"%PDF-")
        for path in pdf_paths
    )
    verification = {
        "generated_at": C.utcnow_iso(),
        "status": "passed" if not missing and pdf_valid else "failed",
        "missing": missing,
        "pdf_valid": pdf_valid,
        "citation_records": len(CITATION_RECORDS),
        "inclusion_rows": len(INCLUSION_MATRIX),
        "orbit_rows": len(orbit_rows),
        "actor_public_overlap_rows": len(actor_public_rows),
        "actor_li_rows": (
            int(actor_li_summary["rows"]) if actor_li_summary is not None else 0
        ),
        "actor_li_evidence_verified": actor_li_summary is not None,
        "surface_rows": len(CITER_SURFACES),
        "paper_profiles": len(profiles),
        "pdf_files": len(pdf_paths),
    }
    C.atomic_write_json(root / "metadata" / "final_verification.json", verification)
    C.checksums(root, output=root / "metadata" / "checksums.sha256")
    if verification["status"] != "passed":
        raise RuntimeError(f"citation artifact verification failed: {verification}")
    return root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-raw", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--actor-li-evaluation",
        help="completed ACToR evaluation directory (18 measured cells)",
    )
    parser.add_argument(
        "--actor-li-runs",
        help="optional ACToR runs directory to archive with the result",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = build(
        historical_raw=Path(args.historical_raw),
        output_root=Path(args.output_root),
        actor_li_evaluation=(
            Path(args.actor_li_evaluation)
            if args.actor_li_evaluation
            else None
        ),
        actor_li_runs=Path(args.actor_li_runs) if args.actor_li_runs else None,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
