"""Exact paper Tables 1 and 2 with measured CodeWeaver values beside them.

The paper values are read from the pinned official ``results.xlsx`` artifact.
They are never inferred from CodeWeaver measurements. CodeWeaver values are
computed from the Full-variant raw/project rows and placed in distinct columns.
"""
from __future__ import annotations

import csv
import io
import statistics
from pathlib import Path
from typing import Any, Iterable

from experiments.recodeagent import common as C

TABLE1_SHEET = "results (claude-4.5-sonnet)"
TABLE2_SHEET = "test-translation-comparison"
CRUST_CLASSIFICATION_SHEET = "sweagent crust - tool test"
PARTIAL = "partial"

TABLE1_TOOL_ORDER = ("oxidizer", "alphatrans", "skel", "crust")
TABLE2_TOOL_ORDER = ("oxidizer", "alphatrans", "skel")
WORKBOOK_TO_DATASET_TOOL = {
    "oxidizer": "oxidizer",
    "alphatrans": "alphatrans",
    "skel": "skel",
    "swe-agent": "crust",
}
TOOL_LABELS = {
    "oxidizer": "Oxidizer (Go->Rust)",
    "alphatrans": "AlphaTrans (Java->Python)",
    "skel": "SKEL (Python->JavaScript)",
    "crust": "SWE-agent (C->Rust)",
    "ALL": "Total",
}
PROJECT_LABELS = {
    "gohistogram": "histogram",
    "gonameparts": "nameparts",
    "commons-cli": "cli",
    "commons-csv": "csv",
    "commons-fileupload": "fileupload",
    "commons-validator": "validator",
}
CRUST_CATEGORY_PROJECTS = {
    "crust-bench (both compile)": "Crust-\N{GREEK SMALL LETTER ALPHA}",
    "crust-bench (agent compile only)": "Crust-\N{GREEK SMALL LETTER BETA}",
    "crust-bench (tool compile only)": "Crust-\N{GREEK SMALL LETTER SIGMA}",
    "crust-bench (none compile)": "Crust-\N{GREEK SMALL LETTER GAMMA}",
}
CRUST_CATEGORY_KEYS = {
    "crust-bench (both compile)": "both_compile",
    "crust-bench (agent compile only)": "agent_only",
    "crust-bench (tool compile only)": "tool_only",
    "crust-bench (none compile)": "neither",
}
CRUST_CATEGORY_EXPECTED_COUNTS = {
    "both_compile": 40,
    "agent_only": 49,
    "tool_only": 1,
    "neither": 10,
}

TABLE1_PAPER_SUM_FIELDS = (
    "paper_loc",
    "paper_validated_tests_expected",
    "paper_validated_prior_executed",
    "paper_validated_prior_passed",
    "paper_validated_prior_failed",
    "paper_validated_recodeagent_executed",
    "paper_validated_recodeagent_passed",
    "paper_validated_recodeagent_failed",
    "paper_translated_recodeagent_executed",
    "paper_translated_recodeagent_passed",
    "paper_translated_recodeagent_failed",
    "paper_generated_recodeagent_executed",
    "paper_generated_recodeagent_passed",
    "paper_generated_recodeagent_failed",
    "paper_function_total",
    "paper_function_prior_success",
    "paper_function_recodeagent_success",
    "paper_function_prior_failed",
    "paper_function_recodeagent_failed",
)
TABLE1_PAPER_MEAN_FIELDS = (
    "paper_coverage_before_percent",
    "paper_coverage_after_percent",
)
TABLE1_CODEWEAVER_SUM_FIELDS = (
    "codeweaver_project_count",
    "codeweaver_loc",
    "codeweaver_validated_tests_expected",
    "codeweaver_validated_tests_executed",
    "codeweaver_validated_tests_passed",
    "codeweaver_validated_tests_failed",
    "codeweaver_translated_tests_executed",
    "codeweaver_translated_tests_passed",
    "codeweaver_translated_tests_failed",
    "codeweaver_generated_tests_expected",
    "codeweaver_generated_tests_executed",
    "codeweaver_generated_tests_passed",
    "codeweaver_generated_tests_failed",
    "codeweaver_function_validation_expected",
    "codeweaver_function_validation_executed",
    "codeweaver_function_validation_passed",
    "codeweaver_function_validation_failed",
)
TABLE1_CODEWEAVER_MEAN_FIELDS = (
    "codeweaver_compilation_success_percent",
    "codeweaver_coverage_before_percent",
    "codeweaver_coverage_after_percent",
)
TABLE2_SUM_FIELDS = (
    "tests",
    "tests_translated",
    "tests_not_translated",
    "assertion_count_matching_tests",
    "assertion_count_nonmatching_tests",
    "assert_equal_output_total",
    "assert_equal_output_matching",
)
TABLE2_MEAN_FIELDS = (
    "assert_equal_type_match_percent",
    "assert_true_type_match_percent",
    "assert_false_type_match_percent",
    "other_type_match_percent",
    "avg_cosine_similarity",
    "avg_source_loc",
    "avg_target_loc",
    "avg_source_method_calls",
    "avg_target_method_calls",
)


def _normalize(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _number(value: Any) -> float | int | None:
    if value in (None, "", "-"):
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _mean(values: Iterable[Any]) -> float | None:
    usable = [float(value) for value in values if _number(value) is not None]
    return statistics.fmean(usable) if usable else None


def _sum(values: Iterable[Any]) -> float | int | None:
    usable = [_number(value) for value in values]
    usable = [value for value in usable if value is not None]
    if not usable:
        return None
    total = sum(usable)
    return int(total) if float(total).is_integer() else total


def _header_map(row: Iterable[Any]) -> dict[str, int]:
    columns: dict[str, int] = {}
    for index, value in enumerate(row):
        if value is not None:
            columns.setdefault(str(value), index)
    return columns


def _cell(row: tuple[Any, ...], columns: dict[str, int], name: str) -> Any:
    index = columns.get(name)
    return row[index] if index is not None and index < len(row) else None


def _workbook_md5(path: Path, *, verify_checksum: bool) -> str:
    digest = C.file_md5(path)
    expected = C.OFFICIAL_ARTIFACT_FILES["results_xlsx"]["md5"]
    if verify_checksum and digest != expected:
        raise ValueError(
            f"official results workbook checksum mismatch: expected {expected}, got {digest}"
        )
    return digest


def _load_table1_base_rows(workbook: Any) -> list[dict[str, Any]]:
    worksheet = workbook[TABLE1_SHEET]
    rows = worksheet.iter_rows(values_only=True)
    columns = _header_map(next(rows))
    out: list[dict[str, Any]] = []
    for raw in rows:
        workbook_tool = str(_cell(raw, columns, "tool") or "").strip().lower()
        if workbook_tool == "total":
            break
        dataset_tool = WORKBOOK_TO_DATASET_TOOL.get(workbook_tool)
        if dataset_tool is None:
            continue
        project_key = str(_cell(raw, columns, "project") or "")
        out.append({
            "table": "Table 1",
            "row_type": "category" if dataset_tool == "crust" else "project",
            "dataset_tool": dataset_tool,
            "paper_prior_tool": workbook_tool,
            "tool_label": TOOL_LABELS[dataset_tool],
            "project_key": project_key,
            "project": CRUST_CATEGORY_PROJECTS.get(
                project_key, PROJECT_LABELS.get(project_key, project_key)
            ),
            "source_language": _cell(raw, columns, "source lang"),
            "target_language": _cell(raw, columns, "target lang"),
            "paper_loc": _number(_cell(raw, columns, "LoC")),
            "paper_compilation_success_prior_tool_percent": _number(
                _cell(raw, columns, "tool compile %")
            ),
            "paper_compilation_success_recodeagent_percent": _number(
                _cell(raw, columns, "agent compile %")
            ),
            "paper_validated_tests_expected": _number(
                _cell(raw, columns, "# executed tests")
            ),
            "paper_validated_prior_executed": _number(
                _cell(raw, columns, "TOOL (# test exec - tool)")
            ),
            "paper_validated_prior_passed": _number(
                _cell(raw, columns, "TOOL (# test pass - tool)")
            ),
            "paper_validated_prior_failed": _number(
                _cell(raw, columns, "TOOL (# test fail - tool)")
            ),
            "paper_validated_recodeagent_executed": _number(
                _cell(raw, columns, "AGENT (# test exec - tool)")
            ),
            "paper_validated_recodeagent_passed": _number(
                _cell(raw, columns, "AGENT (# test pass - tool)")
            ),
            "paper_validated_recodeagent_failed": _number(
                _cell(raw, columns, "AGENT (# test fail - tool)")
            ),
            "paper_translated_recodeagent_executed": _number(
                _cell(raw, columns, "AGENT (# test exec - trans)")
            ),
            "paper_translated_recodeagent_passed": _number(
                _cell(raw, columns, "AGENT (# test pass - trans)")
            ),
            "paper_translated_recodeagent_failed": _number(
                _cell(raw, columns, "AGENT (# test fail - trans)")
            ),
            "paper_generated_recodeagent_executed": _number(
                _cell(raw, columns, "AGENT (# test exec - gen)")
            ),
            "paper_generated_recodeagent_passed": _number(
                _cell(raw, columns, "AGENT (# test pass - gen)")
            ),
            "paper_generated_recodeagent_failed": _number(
                _cell(raw, columns, "AGENT (# test fail - gen)")
            ),
            "paper_coverage_before_percent": _number(
                _cell(raw, columns, "test coverage %")
            ),
            "paper_coverage_after_percent": _number(
                _cell(raw, columns, "test coverage+ %")
            ),
            "paper_function_total": _number(_cell(raw, columns, "Exercised")),
            "paper_function_prior_success": _number(_cell(raw, columns, "tool FS")),
            "paper_function_recodeagent_success": _number(_cell(raw, columns, "agent FS")),
            "paper_function_prior_failed": _number(_cell(raw, columns, "tool FF")),
            "paper_function_recodeagent_failed": _number(_cell(raw, columns, "agent FF")),
        })
    if len(out) != 22:
        raise ValueError(f"{TABLE1_SHEET!r} yielded {len(out)} rows, expected 22")
    return out


def _load_crust_categories(workbook: Any) -> dict[str, list[str]]:
    worksheet = workbook[CRUST_CLASSIFICATION_SHEET]
    rows = worksheet.iter_rows(values_only=True)
    columns = _header_map(next(rows))
    result = {key: [] for key in CRUST_CATEGORY_EXPECTED_COUNTS}
    seen: set[str] = set()
    for raw in rows:
        project = str(_cell(raw, columns, "project") or "").strip()
        if not project or _normalize(project) in seen:
            continue
        tool_compile = _number(_cell(raw, columns, "tool compile (1/0)"))
        agent_compile = _number(_cell(raw, columns, "agent compile (1/0)"))
        if tool_compile not in (0, 1) or agent_compile not in (0, 1):
            continue
        seen.add(_normalize(project))
        if tool_compile and agent_compile:
            category = "both_compile"
        elif agent_compile:
            category = "agent_only"
        elif tool_compile:
            category = "tool_only"
        else:
            category = "neither"
        result[category].append(project)
        if len(seen) == C.EXPECTED_TOOL_COUNTS["crust"]:
            break
    observed = {key: len(value) for key, value in result.items()}
    if observed != CRUST_CATEGORY_EXPECTED_COUNTS:
        raise ValueError(
            f"{CRUST_CLASSIFICATION_SHEET!r} category counts {observed}, "
            f"expected {CRUST_CATEGORY_EXPECTED_COUNTS}"
        )
    return result


def _load_table2_base_rows(workbook: Any) -> list[dict[str, Any]]:
    worksheet = workbook[TABLE2_SHEET]
    rows = worksheet.iter_rows(values_only=True)
    columns = _header_map(next(rows))
    out: list[dict[str, Any]] = []
    for raw in rows:
        workbook_tool = str(_cell(raw, columns, "tool") or "").strip().lower()
        if workbook_tool in ("swe-agent", "total"):
            break
        if workbook_tool not in TABLE2_TOOL_ORDER:
            continue
        project_key = str(_cell(raw, columns, "project") or "")
        out.append({
            "table": "Table 2",
            "row_type": "project",
            "dataset_tool": workbook_tool,
            "tool_label": TOOL_LABELS[workbook_tool],
            "project_key": project_key,
            "project": PROJECT_LABELS.get(project_key, project_key),
            "source_language": _cell(raw, columns, "source lang"),
            "target_language": _cell(raw, columns, "target lang"),
            "paper_tests": _number(_cell(raw, columns, "# tests")),
            "paper_tests_translated": _number(_cell(raw, columns, "# tests translated")),
            "paper_tests_not_translated": _number(
                _cell(raw, columns, "# tests not translated")
            ),
            "paper_assertion_count_matching_tests": _number(
                _cell(raw, columns, "# tests w/ matching # assertions")
            ),
            "paper_assertion_count_nonmatching_tests": _number(
                _cell(raw, columns, "# tests w/ not matching # assertions")
            ),
            "paper_assert_equal_output_total": _number(
                _cell(raw, columns, "total comparable assertEquals")
            ),
            "paper_assert_equal_output_matching": _number(
                _cell(raw, columns, "total matching assertEquals")
            ),
            "paper_assert_equal_type_match_percent": _number(
                _cell(raw, columns, "assertEqual match %")
            ),
            "paper_assert_true_type_match_percent": _number(
                _cell(raw, columns, "assertTrue match %")
            ),
            "paper_assert_false_type_match_percent": _number(
                _cell(raw, columns, "assertFalse match %")
            ),
            "paper_other_type_match_percent": _number(
                _cell(raw, columns, "other match %")
            ),
            "paper_avg_cosine_similarity": _number(
                _cell(raw, columns, "avg cosine sim")
            ),
            "paper_avg_source_loc": _number(_cell(raw, columns, "avg source loc")),
            "paper_avg_target_loc": _number(_cell(raw, columns, "avg target loc")),
            "paper_avg_source_method_calls": _number(
                _cell(raw, columns, "avg method calls source")
            ),
            "paper_avg_target_method_calls": _number(
                _cell(raw, columns, "avg method calls target")
            ),
        })
    if len(out) != 18:
        raise ValueError(f"{TABLE2_SHEET!r} yielded {len(out)} rows, expected 18")
    return out


def load_reference_workbook(
    path: str | Path, *, verify_checksum: bool = True,
) -> dict[str, Any]:
    workbook_path = Path(path)
    if not workbook_path.is_file():
        raise FileNotFoundError(workbook_path)
    openpyxl = C.optional_import("openpyxl")
    if openpyxl is None:
        raise RuntimeError(
            "openpyxl is required to reproduce the exact paper tables; "
            "install experiments/recodeagent/requirements-analysis.txt"
        )
    md5 = _workbook_md5(workbook_path, verify_checksum=verify_checksum)
    workbook = openpyxl.load_workbook(
        workbook_path, read_only=True, data_only=True
    )
    try:
        missing = {
            TABLE1_SHEET, TABLE2_SHEET, CRUST_CLASSIFICATION_SHEET
        } - set(workbook.sheetnames)
        if missing:
            raise ValueError(f"official workbook is missing sheet(s): {sorted(missing)}")
        return {
            "workbook_md5": md5,
            "table1_base_rows": _load_table1_base_rows(workbook),
            "table2_base_rows": _load_table2_base_rows(workbook),
            "crust_categories": _load_crust_categories(workbook),
        }
    finally:
        workbook.close()


def _paper_table1_total(
    rows: list[dict[str, Any]], *, dataset_tool: str, grand: bool = False,
) -> dict[str, Any]:
    total = {
        "table": "Table 1",
        "row_type": "grand_total" if grand else "subtotal",
        "dataset_tool": "ALL" if grand else dataset_tool,
        "paper_prior_tool": "ALL" if grand else rows[0]["paper_prior_tool"],
        "tool_label": TOOL_LABELS["ALL" if grand else dataset_tool],
        "project_key": "Total",
        "project": "Total",
        "source_language": None if grand else rows[0]["source_language"],
        "target_language": None if grand else rows[0]["target_language"],
    }
    for field in TABLE1_PAPER_SUM_FIELDS:
        total[field] = _sum(row.get(field) for row in rows)
    for field in TABLE1_PAPER_MEAN_FIELDS:
        total[field] = _mean(row.get(field) for row in rows)
    if grand:
        # These are the values printed in Table 1. The workbook's cached
        # SUBTOTAL average differs from the paper for these two cells.
        total["paper_compilation_success_prior_tool_percent"] = 96.9
        total["paper_compilation_success_recodeagent_percent"] = 99.4
    elif dataset_tool == "crust":
        # CRUST rows store each category's contribution to the 100-project
        # benchmark, so the printed subtotal is a sum (41 and 89).
        total["paper_compilation_success_prior_tool_percent"] = _sum(
            row.get("paper_compilation_success_prior_tool_percent") for row in rows
        )
        total["paper_compilation_success_recodeagent_percent"] = _sum(
            row.get("paper_compilation_success_recodeagent_percent") for row in rows
        )
    else:
        total["paper_compilation_success_prior_tool_percent"] = _mean(
            row.get("paper_compilation_success_prior_tool_percent") for row in rows
        )
        total["paper_compilation_success_recodeagent_percent"] = _mean(
            row.get("paper_compilation_success_recodeagent_percent") for row in rows
        )
    return total


def build_table1_reference_rows(base_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for tool in TABLE1_TOOL_ORDER:
        rows = [row for row in base_rows if row["dataset_tool"] == tool]
        output.extend(rows)
        output.append(_paper_table1_total(rows, dataset_tool=tool))
    output.append(_paper_table1_total(base_rows, dataset_tool="ALL", grand=True))
    grand = output[-1]
    expected = {
        "paper_loc": C.PAPER_REFERENCE_TOTALS["total_loc_precise"],
        "paper_validated_tests_expected": C.PAPER_REFERENCE_TOTALS["validated_tests"],
        "paper_translated_recodeagent_executed": C.PAPER_REFERENCE_TOTALS["translated_tests"],
        "paper_function_total": C.PAPER_REFERENCE_TOTALS["functions"],
    }
    mismatches = {
        field: (grand.get(field), value)
        for field, value in expected.items()
        if grand.get(field) != value
    }
    if mismatches:
        raise ValueError(f"paper Table 1 totals do not match pinned references: {mismatches}")
    return output


def _manifest_project_maps(
    manifest: dict[str, Any],
) -> tuple[dict[tuple[str, str], str], dict[str, Any]]:
    by_tool_name: dict[tuple[str, str], str] = {}
    by_id: dict[str, Any] = {}
    for project in manifest.get("projects", []):
        project_id = str(project.get("id") or "")
        tool = str(project.get("tool") or "")
        suffix = project_id.split("__", 1)[-1]
        by_tool_name[(tool, _normalize(suffix))] = project_id
        by_id[project_id] = project
    return by_tool_name, by_id


def _reference_members(
    row: dict[str, Any],
    project_lookup: dict[tuple[str, str], str],
    crust_categories: dict[str, list[str]],
) -> list[str]:
    if row["dataset_tool"] != "crust":
        project_id = project_lookup.get(
            (row["dataset_tool"], _normalize(row["project_key"]))
        )
        return [project_id] if project_id else []
    category = CRUST_CATEGORY_KEYS[row["project_key"]]
    members = []
    for project in crust_categories[category]:
        project_id = project_lookup.get(("crust", _normalize(project)))
        if project_id:
            members.append(project_id)
    return members


def _aggregate_source_metric(
    member_ids: list[str],
    rows_by_id: dict[str, dict[str, Any]],
    *,
    field: str,
    status_field: str,
    reducer: str,
    transform=None,
) -> tuple[float | int | None, str]:
    values: list[Any] = []
    non_applicable = 0
    incomplete = 0
    for project_id in member_ids:
        row = rows_by_id.get(project_id)
        if row is None:
            incomplete += 1
            continue
        status = row.get(status_field)
        value = row.get(field)
        if status == C.Status.NOT_APPLICABLE:
            non_applicable += 1
        elif status == C.Status.MEASURED and value is not None:
            values.append(transform(value) if transform else value)
        else:
            incomplete += 1
    if not values:
        if member_ids and non_applicable == len(member_ids):
            return None, C.Status.NOT_APPLICABLE
        return None, C.Status.UNAVAILABLE if incomplete else C.Status.MISSING
    value = _sum(values) if reducer == "sum" else _mean(values)
    status = PARTIAL if incomplete else C.Status.MEASURED
    return value, status


def _put_metric(
    output: dict[str, Any], key: str, result: tuple[Any, str],
) -> None:
    output[key], output[f"{key}_status"] = result


def _codeweaver_table1_project_row(
    member_ids: list[str],
    *,
    raw_by_id: dict[str, dict[str, Any]],
    generated_by_id: dict[str, dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "codeweaver_project_count": len(member_ids),
        "codeweaver_project_count_status": (
            C.Status.MEASURED if member_ids else C.Status.MISSING
        ),
    }
    loc_values = [
        manifest_by_id[project_id].get("loc_source")
        for project_id in member_ids
        if project_id in manifest_by_id
        and manifest_by_id[project_id].get("loc_source") is not None
    ]
    output["codeweaver_loc"] = _sum(loc_values)
    output["codeweaver_loc_status"] = (
        C.Status.MEASURED
        if len(loc_values) == len(member_ids) and member_ids
        else (PARTIAL if loc_values else C.Status.MISSING)
    )
    raw_specs = {
        "codeweaver_compilation_success_percent": (
            "build", "build_status", "mean", lambda value: 100.0 if value else 0.0
        ),
        "codeweaver_validated_tests_expected": (
            "validated_tests_expected", "validated_tests_expected_status", "sum", None
        ),
        "codeweaver_validated_tests_executed": (
            "validated_tests_executed", "validated_tests_executed_status", "sum", None
        ),
        "codeweaver_validated_tests_passed": (
            "validated_tests_passed", "validated_tests_passed_status", "sum", None
        ),
        "codeweaver_validated_tests_failed": (
            "validated_tests_failed", "validated_tests_failed_status", "sum", None
        ),
        "codeweaver_translated_tests_executed": (
            "translated_tests_total", "translated_tests_total_status", "sum", None
        ),
        "codeweaver_translated_tests_passed": (
            "translated_tests_passed", "translated_tests_passed_status", "sum", None
        ),
        "codeweaver_translated_tests_failed": (
            "translated_tests_failed", "translated_tests_failed_status", "sum", None
        ),
        "codeweaver_function_validation_expected": (
            "function_validation_expected", "function_validation_expected_status", "sum", None
        ),
        "codeweaver_function_validation_executed": (
            "function_validation_total", "function_validation_total_status", "sum", None
        ),
        "codeweaver_function_validation_passed": (
            "function_validation_passed", "function_validation_passed_status", "sum", None
        ),
        "codeweaver_function_validation_failed": (
            "function_validation_failed", "function_validation_failed_status", "sum", None
        ),
    }
    for key, (field, status_field, reducer, transform) in raw_specs.items():
        _put_metric(output, key, _aggregate_source_metric(
            member_ids,
            raw_by_id,
            field=field,
            status_field=status_field,
            reducer=reducer,
            transform=transform,
        ))
    generated_specs = {
        "codeweaver_generated_tests_expected": (
            "generated_tests_expected", "generated_tests_expected_status", "sum"
        ),
        "codeweaver_generated_tests_executed": (
            "generated_tests_executed", "generated_tests_executed_status", "sum"
        ),
        "codeweaver_generated_tests_passed": (
            "generated_tests_passed", "generated_tests_passed_status", "sum"
        ),
        "codeweaver_generated_tests_failed": (
            "generated_tests_failed", "generated_tests_failed_status", "sum"
        ),
        "codeweaver_coverage_before_percent": (
            "coverage_before", "coverage_before_status", "mean"
        ),
        "codeweaver_coverage_after_percent": (
            "coverage_after", "coverage_after_status", "mean"
        ),
    }
    for key, (field, status_field, reducer) in generated_specs.items():
        _put_metric(output, key, _aggregate_source_metric(
            member_ids,
            generated_by_id,
            field=field,
            status_field=status_field,
            reducer=reducer,
        ))
    return output


def _aggregate_paired_metric(
    rows: list[dict[str, Any]], field: str, *, reducer: str,
) -> tuple[Any, str]:
    values = []
    incomplete = False
    applicable = False
    for row in rows:
        status = row.get(f"{field}_status")
        if status == C.Status.NOT_APPLICABLE:
            continue
        applicable = True
        if status == C.Status.MEASURED and row.get(field) is not None:
            values.append(row[field])
        elif status == PARTIAL and row.get(field) is not None:
            values.append(row[field])
            incomplete = True
        else:
            incomplete = True
    if not applicable:
        return None, C.Status.NOT_APPLICABLE
    if not values:
        return None, C.Status.UNAVAILABLE
    value = _sum(values) if reducer == "sum" else _mean(values)
    return value, PARTIAL if incomplete else C.Status.MEASURED


def _add_codeweaver_table1_total(
    reference_total: dict[str, Any], child_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    output = dict(reference_total)
    for field in TABLE1_CODEWEAVER_SUM_FIELDS:
        _put_metric(output, field, _aggregate_paired_metric(
            child_rows, field, reducer="sum"
        ))
    for field in TABLE1_CODEWEAVER_MEAN_FIELDS:
        _put_metric(output, field, _aggregate_paired_metric(
            child_rows, field, reducer="mean"
        ))
    return output


def build_table1_side_by_side(
    *,
    reference_base_rows: list[dict[str, Any]],
    crust_categories: dict[str, list[str]],
    manifest: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    generated_test_project_rows: list[dict[str, Any]],
    variant: str = "full",
    repetition: int | None = 0,
) -> list[dict[str, Any]]:
    if repetition is None:
        raise ValueError(
            "paper table comparison requires one explicit repetition; "
            "cross-repetition aggregation would not match the paper's single-run table"
        )
    project_lookup, manifest_by_id = _manifest_project_maps(manifest)
    selected_raw = [
        row for row in raw_rows
        if row.get("variant") == variant
        and (repetition is None or int(row.get("repetition") or 0) == repetition)
    ]
    selected_generated = [
        row for row in generated_test_project_rows
        if row.get("variant") == variant
        and (repetition is None or int(row.get("repetition") or 0) == repetition)
    ]
    raw_by_id = {str(row.get("project_id")): row for row in selected_raw}
    generated_by_id = {
        str(row.get("project_id")): row for row in selected_generated
    }
    base_rows: list[dict[str, Any]] = []
    for reference in reference_base_rows:
        members = _reference_members(reference, project_lookup, crust_categories)
        combined = dict(reference)
        combined["codeweaver_variant"] = variant
        combined["codeweaver_repetition"] = repetition
        combined["codeweaver_member_project_ids"] = ";".join(members)
        combined.update(_codeweaver_table1_project_row(
            members,
            raw_by_id=raw_by_id,
            generated_by_id=generated_by_id,
            manifest_by_id=manifest_by_id,
        ))
        base_rows.append(combined)

    output: list[dict[str, Any]] = []
    for tool in TABLE1_TOOL_ORDER:
        children = [row for row in base_rows if row["dataset_tool"] == tool]
        output.extend(children)
        reference_total = _paper_table1_total(children, dataset_tool=tool)
        output.append(_add_codeweaver_table1_total(reference_total, children))
    grand_reference = _paper_table1_total(base_rows, dataset_tool="ALL", grand=True)
    output.append(_add_codeweaver_table1_total(grand_reference, base_rows))
    return output


def _paper_table2_total(
    rows: list[dict[str, Any]], *, dataset_tool: str, grand: bool = False,
) -> dict[str, Any]:
    output = {
        "table": "Table 2",
        "row_type": "grand_total" if grand else "subtotal",
        "dataset_tool": "ALL" if grand else dataset_tool,
        "tool_label": TOOL_LABELS["ALL" if grand else dataset_tool],
        "project_key": "Total",
        "project": "Total",
        "source_language": None if grand else rows[0]["source_language"],
        "target_language": None if grand else rows[0]["target_language"],
    }
    for field in TABLE2_SUM_FIELDS:
        output[f"paper_{field}"] = _sum(row.get(f"paper_{field}") for row in rows)
    for field in TABLE2_MEAN_FIELDS:
        output[f"paper_{field}"] = _mean(row.get(f"paper_{field}") for row in rows)
    return output


def build_table2_reference_rows(base_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for tool in TABLE2_TOOL_ORDER:
        rows = [row for row in base_rows if row["dataset_tool"] == tool]
        output.extend(rows)
        output.append(_paper_table2_total(rows, dataset_tool=tool))
    output.append(_paper_table2_total(base_rows, dataset_tool="ALL", grand=True))
    grand = output[-1]
    if grand["paper_tests"] != C.PAPER_REFERENCE_TOTALS["translated_tests"]:
        raise ValueError(
            f"paper Table 2 total tests {grand['paper_tests']}, "
            f"expected {C.PAPER_REFERENCE_TOTALS['translated_tests']}"
        )
    return output


def _numeric_csv(row: dict[str, Any], field: str) -> float | None:
    return float(row[field]) if _number(row.get(field)) is not None else None


def _ratio_percent(good: float | None, total: float | None) -> float | None:
    return 100.0 * good / total if good is not None and total not in (None, 0) else None


def _codeweaver_table2_project(row: dict[str, Any] | None) -> dict[str, Any]:
    fields = TABLE2_SUM_FIELDS + TABLE2_MEAN_FIELDS
    if row is None:
        output: dict[str, Any] = {}
        for field in fields:
            output[f"codeweaver_{field}"] = None
            output[f"codeweaver_{field}_status"] = C.Status.MISSING
        return output
    tests = _numeric_csv(row, "paper_runtime_tests")
    translated = _numeric_csv(row, "mapped_runtime_cases")
    values = {
        "tests": tests,
        "tests_translated": translated,
        "tests_not_translated": (
            tests - translated if tests is not None and translated is not None else None
        ),
        "assertion_count_matching_tests": _numeric_csv(
            row, "assertion_count_runtime_matches"
        ),
        "assertion_count_nonmatching_tests": _numeric_csv(
            row, "assertion_count_runtime_mismatches"
        ),
        "assert_equal_output_total": _numeric_csv(row, "assert_equal_comparable"),
        "assert_equal_output_matching": _numeric_csv(row, "assert_equal_matching"),
        "assert_equal_type_match_percent": _ratio_percent(
            _numeric_csv(row, "assert_equal_type_good"),
            _numeric_csv(row, "assert_equal_type_total"),
        ),
        "assert_true_type_match_percent": _ratio_percent(
            _numeric_csv(row, "assert_true_type_good"),
            _numeric_csv(row, "assert_true_type_total"),
        ),
        "assert_false_type_match_percent": _ratio_percent(
            _numeric_csv(row, "assert_false_type_good"),
            _numeric_csv(row, "assert_false_type_total"),
        ),
        "other_type_match_percent": _ratio_percent(
            _numeric_csv(row, "other_type_good"),
            _numeric_csv(row, "other_type_total"),
        ),
        "avg_cosine_similarity": _numeric_csv(row, "avg_cosine_similarity"),
        "avg_source_loc": _numeric_csv(row, "avg_source_loc"),
        "avg_target_loc": _numeric_csv(row, "avg_target_loc"),
        "avg_source_method_calls": _numeric_csv(row, "avg_source_method_calls"),
        "avg_target_method_calls": _numeric_csv(row, "avg_target_method_calls"),
    }
    output = {}
    for field, value in values.items():
        output[f"codeweaver_{field}"] = value
        output[f"codeweaver_{field}_status"] = (
            C.Status.MEASURED if value is not None else C.Status.NOT_APPLICABLE
        )
    return output


def _add_codeweaver_table2_total(
    reference_total: dict[str, Any], children: list[dict[str, Any]],
) -> dict[str, Any]:
    output = dict(reference_total)
    for field in TABLE2_SUM_FIELDS:
        key = f"codeweaver_{field}"
        _put_metric(output, key, _aggregate_paired_metric(children, key, reducer="sum"))
    for field in TABLE2_MEAN_FIELDS:
        key = f"codeweaver_{field}"
        _put_metric(output, key, _aggregate_paired_metric(children, key, reducer="mean"))
    return output


def build_table2_side_by_side(
    *,
    reference_base_rows: list[dict[str, Any]],
    paper_test_project_rows: list[dict[str, Any]],
    variant: str = "full",
    repetition: int | None = 0,
) -> list[dict[str, Any]]:
    if repetition is None:
        raise ValueError(
            "paper table comparison requires one explicit repetition; "
            "cross-repetition aggregation would not match the paper's single-run table"
        )
    selected = [
        row for row in paper_test_project_rows
        if row.get("variant") == variant
        and (repetition is None or int(row.get("repetition") or 0) == repetition)
    ]
    measured = {
        (str(row.get("tool")), _normalize(row.get("project"))): row
        for row in selected
    }
    base_rows = []
    for reference in reference_base_rows:
        combined = dict(reference)
        combined["codeweaver_variant"] = variant
        combined["codeweaver_repetition"] = repetition
        combined.update(_codeweaver_table2_project(measured.get(
            (reference["dataset_tool"], _normalize(reference["project_key"]))
        )))
        base_rows.append(combined)
    output: list[dict[str, Any]] = []
    for tool in TABLE2_TOOL_ORDER:
        children = [row for row in base_rows if row["dataset_tool"] == tool]
        output.extend(children)
        output.append(_add_codeweaver_table2_total(
            _paper_table2_total(children, dataset_tool=tool), children
        ))
    output.append(_add_codeweaver_table2_total(
        _paper_table2_total(base_rows, dataset_tool="ALL", grand=True), base_rows
    ))
    return output


def _all_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)
    return columns


def write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_all_columns(rows))
    writer.writeheader()
    writer.writerows(rows)
    C.atomic_write_text(path, buffer.getvalue())
    return path


def _display_number(
    value: Any, *, decimals: int = 0, status: str | None = None,
) -> str:
    if value is None or status in {
        C.Status.MISSING,
        C.Status.UNAVAILABLE,
        C.Status.ERROR,
        C.Status.NOT_APPLICABLE,
        C.Status.SKIPPED,
    }:
        return "-"
    number = float(value)
    if decimals == 0 or number.is_integer():
        text = f"{number:,.0f}"
    else:
        text = f"{number:,.{decimals}f}"
    return text + ("*" if status == PARTIAL else "")


def _cw(row: dict[str, Any], field: str, *, decimals: int = 0) -> str:
    return _display_number(
        row.get(field), decimals=decimals, status=row.get(f"{field}_status")
    )


def _paper(row: dict[str, Any], field: str, *, decimals: int = 0) -> str:
    return _display_number(row.get(field), decimals=decimals)


def _joined(values: Iterable[str]) -> str:
    parts = list(values)
    return "-" if all(value == "-" for value in parts) else "/".join(parts)


def _table1_pdf_rows(rows: list[dict[str, Any]]) -> tuple[list[str], list[list[str]]]:
    headers = [
        "Tool (PL)",
        "Project",
        "LoC",
        "CS %<br/>P-Tool",
        "CS %<br/>P-RCA",
        "CS %<br/>CW",
        "Validated developer tests E/TE/TP/TF<br/>P-Tool",
        "Validated developer tests E/TE/TP/TF<br/>P-RCA",
        "Validated developer tests E/TE/TP/TF<br/>CW",
        "Translated developer tests TE/TP/TF<br/>P-RCA",
        "Translated developer tests TE/TP/TF<br/>CW",
        "Generated tests TE/TP/TF<br/>P-RCA",
        "Generated tests TE/TP/TF<br/>CW",
        "Coverage C/C+ %<br/>P-RCA",
        "Coverage C/C+ %<br/>CW",
        "Function validation T/S/F<br/>P-Tool",
        "Function validation T/S/F<br/>P-RCA",
        "Function validation E/TE/S/F<br/>CW",
    ]
    output = []
    for row in rows:
        paper_expected = _paper(row, "paper_validated_tests_expected")
        output.append([
            row["tool_label"],
            row["project"],
            _paper(row, "paper_loc"),
            _paper(row, "paper_compilation_success_prior_tool_percent", decimals=1),
            _paper(row, "paper_compilation_success_recodeagent_percent", decimals=1),
            _cw(row, "codeweaver_compilation_success_percent", decimals=1),
            _joined([
                paper_expected,
                _paper(row, "paper_validated_prior_executed"),
                _paper(row, "paper_validated_prior_passed"),
                _paper(row, "paper_validated_prior_failed"),
            ]),
            _joined([
                paper_expected,
                _paper(row, "paper_validated_recodeagent_executed"),
                _paper(row, "paper_validated_recodeagent_passed"),
                _paper(row, "paper_validated_recodeagent_failed"),
            ]),
            _joined([
                _cw(row, "codeweaver_validated_tests_expected"),
                _cw(row, "codeweaver_validated_tests_executed"),
                _cw(row, "codeweaver_validated_tests_passed"),
                _cw(row, "codeweaver_validated_tests_failed"),
            ]),
            _joined([
                _paper(row, "paper_translated_recodeagent_executed"),
                _paper(row, "paper_translated_recodeagent_passed"),
                _paper(row, "paper_translated_recodeagent_failed"),
            ]),
            _joined([
                _cw(row, "codeweaver_translated_tests_executed"),
                _cw(row, "codeweaver_translated_tests_passed"),
                _cw(row, "codeweaver_translated_tests_failed"),
            ]),
            _joined([
                _paper(row, "paper_generated_recodeagent_executed"),
                _paper(row, "paper_generated_recodeagent_passed"),
                _paper(row, "paper_generated_recodeagent_failed"),
            ]),
            _joined([
                _cw(row, "codeweaver_generated_tests_executed"),
                _cw(row, "codeweaver_generated_tests_passed"),
                _cw(row, "codeweaver_generated_tests_failed"),
            ]),
            _joined([
                _paper(row, "paper_coverage_before_percent", decimals=1),
                _paper(row, "paper_coverage_after_percent", decimals=1),
            ]),
            _joined([
                _cw(row, "codeweaver_coverage_before_percent", decimals=1),
                _cw(row, "codeweaver_coverage_after_percent", decimals=1),
            ]),
            _joined([
                _paper(row, "paper_function_total"),
                _paper(row, "paper_function_prior_success"),
                _paper(row, "paper_function_prior_failed"),
            ]),
            _joined([
                _paper(row, "paper_function_total"),
                _paper(row, "paper_function_recodeagent_success"),
                _paper(row, "paper_function_recodeagent_failed"),
            ]),
            _joined([
                _cw(row, "codeweaver_function_validation_expected"),
                _cw(row, "codeweaver_function_validation_executed"),
                _cw(row, "codeweaver_function_validation_passed"),
                _cw(row, "codeweaver_function_validation_failed"),
            ]),
        ])
    return headers, output


def _table2_pdf_rows(rows: list[dict[str, Any]]) -> tuple[list[str], list[list[str]]]:
    metric_specs = [
        ("Tests", "tests", 0, False),
        ("Translated/Not", ("tests_translated", "tests_not_translated"), 0, True),
        ("Assertion count M/N", (
            "assertion_count_matching_tests", "assertion_count_nonmatching_tests"
        ), 0, True),
        ("assertEqual output T/M", (
            "assert_equal_output_total", "assert_equal_output_matching"
        ), 0, True),
        ("Type match Equal %", "assert_equal_type_match_percent", 2, False),
        ("Type match True %", "assert_true_type_match_percent", 2, False),
        ("Type match False %", "assert_false_type_match_percent", 2, False),
        ("Type match Other %", "other_type_match_percent", 2, False),
        ("Avg cosine", "avg_cosine_similarity", 2, False),
        ("Avg LoC S/T", ("avg_source_loc", "avg_target_loc"), 2, True),
        ("Avg calls S/T", (
            "avg_source_method_calls", "avg_target_method_calls"
        ), 2, True),
    ]
    headers = ["Tool (PL)", "Project"]
    for label, _fields, _decimals, _joined_metric in metric_specs:
        headers.extend([f"{label}<br/>Paper", f"{label}<br/>CW"])
    output = []
    for row in rows:
        values = [row["tool_label"], row["project"]]
        for _label, fields, decimals, joined_metric in metric_specs:
            field_names = fields if isinstance(fields, tuple) else (fields,)
            paper_values = [
                _paper(row, f"paper_{field}", decimals=decimals)
                for field in field_names
            ]
            cw_values = [
                _cw(row, f"codeweaver_{field}", decimals=decimals)
                for field in field_names
            ]
            values.extend([
                _joined(paper_values) if joined_metric else paper_values[0],
                _joined(cw_values) if joined_metric else cw_values[0],
            ])
        output.append(values)
    return headers, output


def _register_pdf_font() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = (
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    )
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont("PaperTable", str(regular)))
            pdfmetrics.registerFont(TTFont("PaperTable-Bold", str(bold)))
            return "PaperTable", "PaperTable-Bold"
    return "Helvetica", "Helvetica-Bold"


def render_pdf(
    table1_rows: list[dict[str, Any]],
    table2_rows: list[dict[str, Any]],
    path: Path,
    *,
    variant: str,
    repetition: int | None,
    workbook_md5: str,
) -> bool:
    if C.optional_import("reportlab") is None:
        C.atomic_write_text(
            Path(str(path) + ".unavailable.txt"),
            "Paper Tables 1 and 2 side-by-side\n\n"
            "PDF not rendered: reportlab is not installed. See the sibling CSV files.\n",
        )
        return False
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        LongTable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        TableStyle,
    )

    regular_font, bold_font = _register_pdf_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PaperTitle",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=17,
        leading=20,
    )
    heading_style = ParagraphStyle(
        "PaperHeading",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=12,
        leading=14,
    )
    normal_style = ParagraphStyle(
        "PaperNormal",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=7.5,
        leading=9,
    )
    header_style = ParagraphStyle(
        "PaperHeader",
        parent=normal_style,
        fontName=bold_font,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontSize=5.1,
        leading=5.8,
    )
    cell_style = ParagraphStyle(
        "PaperCell",
        parent=normal_style,
        alignment=TA_CENTER,
        fontSize=5.2,
        leading=6.1,
    )

    document = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A3),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title="ReCodeAgent paper Tables 1 and 2 with CodeWeaver results",
        author="CodeWeaver reproduction harness",
    )
    elements: list[Any] = [
        Paragraph(
            "ReCodeAgent paper Tables 1 and 2 with CodeWeaver results",
            title_style,
        ),
        Paragraph(
            "Paper values: arXiv:2604.07341 and the official results.xlsx "
            f"(MD5 {workbook_md5}). CodeWeaver values: variant={variant!r}, "
            f"repetition={repetition!r}. P-Tool is the paper's comparison tool; "
            "P-RCA is the paper's ReCodeAgent result; CW is independently measured "
            "CodeWeaver. A trailing * marks a partial measured sum/mean where one or "
            "more constituent CodeWeaver cells were unavailable. '-' means unavailable "
            "or not applicable and is never converted to zero.",
            normal_style,
        ),
        Spacer(1, 4 * mm),
    ]

    def add_table(
        title: str,
        caption: str,
        headers: list[str],
        data_rows: list[list[str]],
        source_rows: list[dict[str, Any]],
    ) -> None:
        elements.append(Paragraph(title, heading_style))
        elements.append(Paragraph(caption, normal_style))
        elements.append(Spacer(1, 2 * mm))
        table_data = [
            [Paragraph(header, header_style) for header in headers]
        ] + [
            [Paragraph(str(value), cell_style) for value in row]
            for row in data_rows
        ]
        available_width = landscape(A3)[0] - 16 * mm
        column_width = available_width / len(headers)
        table = LongTable(
            table_data,
            repeatRows=1,
            colWidths=[column_width] * len(headers),
        )
        commands: list[tuple[Any, ...]] = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243447")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9aa5b1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 1.2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1.2),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white, colors.HexColor("#f4f6f8")
            ]),
        ]
        for index, source_row in enumerate(source_rows, start=1):
            if source_row["row_type"] == "subtotal":
                commands.append((
                    "BACKGROUND", (0, index), (-1, index),
                    colors.HexColor("#dce6f1"),
                ))
            elif source_row["row_type"] == "grand_total":
                commands.extend([
                    (
                        "BACKGROUND", (0, index), (-1, index),
                        colors.HexColor("#516b86"),
                    ),
                    ("TEXTCOLOR", (0, index), (-1, index), colors.white),
                ])
        table.setStyle(TableStyle(commands))
        elements.append(table)

    table1_headers, table1_data = _table1_pdf_rows(table1_rows)
    add_table(
        "Table 1 - Effectiveness",
        "Effectiveness of ReCodeAgent in repository-level code translation and "
        "validation in terms of test and function validation. Tuple components "
        "from the paper are expanded into P-Tool and P-RCA columns; CodeWeaver is "
        "placed immediately beside the corresponding paper metric. E=expected, "
        "TE=executed, TP=passing, TF=failing, C=coverage before generated tests, "
        "C+=coverage after generated tests, T=total, S=success, F=fail.",
        table1_headers,
        table1_data,
        table1_rows,
    )
    elements.append(PageBreak())
    table2_headers, table2_data = _table2_pdf_rows(table2_rows)
    add_table(
        "Table 2 - Test Translation",
        "Comparison between ReCodeAgent translated tests and original source-language "
        "tests, with the same official AST/runtime protocol applied to CodeWeaver. "
        "Paper subtotal means follow the workbook's SUBTOTAL(AVERAGE) formulas. "
        "M/N=matching/non-matching, T/M=total/matching, S/T=source/target.",
        table2_headers,
        table2_data,
        table2_rows,
    )

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont(regular_font, 6)
        canvas.setFillColor(colors.HexColor("#52606d"))
        canvas.drawRightString(
            landscape(A3)[0] - 8 * mm,
            4 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    document.build(elements, onFirstPage=footer, onLaterPages=footer)
    return True


def build_artifacts(
    *,
    workbook_path: str | Path,
    manifest: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    paper_test_project_rows: list[dict[str, Any]],
    generated_test_project_rows: list[dict[str, Any]],
    output_root: Path,
    variant: str = "full",
    repetition: int | None = 0,
    verify_workbook_checksum: bool = True,
) -> dict[str, Any]:
    reference = load_reference_workbook(
        workbook_path, verify_checksum=verify_workbook_checksum
    )
    table1_rows = build_table1_side_by_side(
        reference_base_rows=reference["table1_base_rows"],
        crust_categories=reference["crust_categories"],
        manifest=manifest,
        raw_rows=raw_rows,
        generated_test_project_rows=generated_test_project_rows,
        variant=variant,
        repetition=repetition,
    )
    table2_rows = build_table2_side_by_side(
        reference_base_rows=reference["table2_base_rows"],
        paper_test_project_rows=paper_test_project_rows,
        variant=variant,
        repetition=repetition,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    table1_path = write_csv(
        table1_rows, output_root / "paper_table1_side_by_side.csv"
    )
    table2_path = write_csv(
        table2_rows, output_root / "paper_table2_side_by_side.csv"
    )
    pdf_path = output_root / "paper_tables_side_by_side.pdf"
    rendered = render_pdf(
        table1_rows,
        table2_rows,
        pdf_path,
        variant=variant,
        repetition=repetition,
        workbook_md5=reference["workbook_md5"],
    )
    provenance = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "available": rendered,
        "paper_arxiv_id": C.PAPER_ARXIV_ID,
        "paper_table1_page": 7,
        "paper_table2_page": 8,
        "official_workbook_filename": C.OFFICIAL_ARTIFACT_FILES["results_xlsx"]["filename"],
        "official_workbook_md5": reference["workbook_md5"],
        "official_workbook_expected_md5": C.OFFICIAL_ARTIFACT_FILES["results_xlsx"]["md5"],
        "official_workbook_url": C.OFFICIAL_ARTIFACT_FILES["results_xlsx"]["url"],
        "official_workbook_sheets": [
            TABLE1_SHEET, TABLE2_SHEET, CRUST_CLASSIFICATION_SHEET
        ],
        "codeweaver_variant": variant,
        "codeweaver_repetition": repetition,
        "paper_table1_rows": len(table1_rows),
        "paper_table2_rows": len(table2_rows),
        "paper_table1_csv": table1_path.name,
        "paper_table2_csv": table2_path.name,
        "comparison_pdf": pdf_path.name,
        "partial_marker": "*",
        "partial_definition": (
            "numeric result aggregates the measured subset, but one or more "
            "applicable constituent CodeWeaver measurements were unavailable"
        ),
    }
    C.atomic_write_json(
        output_root / "paper_tables_side_by_side_provenance.json", provenance
    )
    return provenance
