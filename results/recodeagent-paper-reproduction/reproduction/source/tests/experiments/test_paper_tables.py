from __future__ import annotations

from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import paper_tables as PT


NON_CRUST_LOC = {
    ("oxidizer", "checkdigit"): 428,
    ("oxidizer", "go-edlib"): 639,
    ("oxidizer", "gohistogram"): 314,
    ("oxidizer", "gonameparts"): 413,
    ("oxidizer", "stats"): 1241,
    ("oxidizer", "textrank"): 1132,
    ("alphatrans", "commons-cli"): 37841,
    ("alphatrans", "commons-csv"): 33072,
    ("alphatrans", "commons-fileupload"): 3567,
    ("alphatrans", "commons-validator"): 41605,
    ("skel", "bst"): 123,
    ("skel", "colorsys"): 120,
    ("skel", "heapq"): 189,
    ("skel", "html"): 684,
    ("skel", "mathgen"): 735,
    ("skel", "rbt"): 366,
    ("skel", "strsim"): 654,
    ("skel", "toml"): 1206,
}


def _table1_row(
    tool: str,
    project: str,
    *,
    loc: int,
    expected: int,
    translated: int | None,
    functions: int | None,
    prior_compile: float,
    agent_compile: float,
) -> dict:
    prior_tool = "swe-agent" if tool == "crust" else tool
    row = {
        "table": "Table 1",
        "row_type": "category" if tool == "crust" else "project",
        "dataset_tool": tool,
        "paper_prior_tool": prior_tool,
        "tool_label": PT.TOOL_LABELS[tool],
        "project_key": project,
        "project": PT.CRUST_CATEGORY_PROJECTS.get(
            project, PT.PROJECT_LABELS.get(project, project)
        ),
        "source_language": C.DATASET_SPECS[tool]["source_language"].lower(),
        "target_language": C.DATASET_SPECS[tool]["target_language"].lower(),
        "paper_loc": loc,
        "paper_compilation_success_prior_tool_percent": prior_compile,
        "paper_compilation_success_recodeagent_percent": agent_compile,
        "paper_validated_tests_expected": expected,
        "paper_validated_prior_executed": expected,
        "paper_validated_prior_passed": expected,
        "paper_validated_prior_failed": 0,
        "paper_validated_recodeagent_executed": expected,
        "paper_validated_recodeagent_passed": expected,
        "paper_validated_recodeagent_failed": 0,
        "paper_translated_recodeagent_executed": translated,
        "paper_translated_recodeagent_passed": translated,
        "paper_translated_recodeagent_failed": 0 if translated is not None else None,
        "paper_generated_recodeagent_executed": 0,
        "paper_generated_recodeagent_passed": 0,
        "paper_generated_recodeagent_failed": 0,
        "paper_coverage_before_percent": 50,
        "paper_coverage_after_percent": 60,
        "paper_function_total": functions,
        "paper_function_prior_success": functions,
        "paper_function_recodeagent_success": functions,
        "paper_function_prior_failed": 0 if functions is not None else None,
        "paper_function_recodeagent_failed": 0 if functions is not None else None,
    }
    return row


def _official_shape_table1_rows() -> list[dict]:
    rows = []
    for (tool, project), expected in C.PAPER_RUNTIME_TESTS_BY_PROJECT.items():
        rows.append(_table1_row(
            tool,
            project,
            loc=NON_CRUST_LOC[(tool, project)],
            expected=expected,
            translated=expected,
            functions=C.PAPER_EXERCISED_FUNCTIONS_BY_PROJECT[(tool, project)],
            prior_compile=100,
            agent_compile=100,
        ))
    crust = (
        ("crust-bench (both compile)", 22961, 166, 673, 40, 40),
        ("crust-bench (agent compile only)", 66704, 321, 1900, 0, 49),
        ("crust-bench (tool compile only)", 3894, 1, 41, 1, 0),
        ("crust-bench (none compile)", 15169, 135, 572, 0, 0),
    )
    for project, loc, expected, functions, prior_compile, agent_compile in crust:
        rows.append(_table1_row(
            "crust",
            project,
            loc=loc,
            expected=expected,
            translated=None,
            functions=functions,
            prior_compile=prior_compile,
            agent_compile=agent_compile,
        ))
    return rows


def _table2_reference_rows() -> list[dict]:
    rows = []
    for (tool, project), tests in C.PAPER_RUNTIME_TESTS_BY_PROJECT.items():
        row = {
            "table": "Table 2",
            "row_type": "project",
            "dataset_tool": tool,
            "tool_label": PT.TOOL_LABELS[tool],
            "project_key": project,
            "project": PT.PROJECT_LABELS.get(project, project),
            "source_language": C.DATASET_SPECS[tool]["source_language"].lower(),
            "target_language": C.DATASET_SPECS[tool]["target_language"].lower(),
        }
        for field in PT.TABLE2_SUM_FIELDS:
            row[f"paper_{field}"] = tests if field in {
                "tests", "tests_translated", "assertion_count_matching_tests"
            } else 0
        for field in PT.TABLE2_MEAN_FIELDS:
            row[f"paper_{field}"] = 100 if field.endswith("_percent") else 1
        rows.append(row)
    return rows


def _raw_row(project_id: str, tool: str, *, unavailable: bool = False) -> dict:
    row = {
        "variant": "full",
        "repetition": 0,
        "project_id": project_id,
        "tool": tool,
        "build": True,
        "build_status": C.Status.MEASURED,
    }
    for field in (
        "validated_tests_expected",
        "validated_tests_executed",
        "validated_tests_passed",
        "translated_tests_total",
        "translated_tests_passed",
        "function_validation_expected",
        "function_validation_total",
        "function_validation_passed",
    ):
        row[field] = 1
        row[f"{field}_status"] = C.Status.MEASURED
    for field in (
        "validated_tests_failed",
        "translated_tests_failed",
        "function_validation_failed",
    ):
        row[field] = 0
        row[f"{field}_status"] = C.Status.MEASURED
    if tool == "crust":
        for field in (
            "function_validation_expected",
            "function_validation_total",
            "function_validation_passed",
            "function_validation_failed",
        ):
            row[field] = None
            row[f"{field}_status"] = C.Status.NOT_APPLICABLE
    if unavailable:
        row["validated_tests_executed"] = None
        row["validated_tests_executed_status"] = C.Status.UNAVAILABLE
    return row


def _generated_row(project_id: str, tool: str) -> dict:
    row = {
        "variant": "full",
        "repetition": 0,
        "project_id": project_id,
        "tool": tool,
    }
    for field, value in (
        ("generated_tests_expected", 1),
        ("generated_tests_executed", 1),
        ("generated_tests_passed", 1),
        ("generated_tests_failed", 0),
        ("coverage_before", 10),
        ("coverage_after", 20),
    ):
        row[field] = value
        row[f"{field}_status"] = C.Status.MEASURED
    return row


def test_table1_reference_rows_match_printed_totals() -> None:
    rows = PT.build_table1_reference_rows(_official_shape_table1_rows())

    assert len(rows) == 27
    grand = rows[-1]
    assert grand["paper_loc"] == 233057
    assert grand["paper_validated_tests_expected"] == 2107
    assert grand["paper_translated_recodeagent_executed"] == 1484
    assert grand["paper_function_total"] == 4583
    assert grand["paper_compilation_success_prior_tool_percent"] == 96.9
    assert grand["paper_compilation_success_recodeagent_percent"] == 99.4
    crust_total = next(
        row for row in rows
        if row["dataset_tool"] == "crust" and row["row_type"] == "subtotal"
    )
    assert crust_total["paper_compilation_success_prior_tool_percent"] == 41
    assert crust_total["paper_compilation_success_recodeagent_percent"] == 89


def test_table2_reference_rows_follow_paper_macro_averages() -> None:
    base = _table2_reference_rows()
    base[0]["paper_avg_cosine_similarity"] = 0
    base[1]["paper_avg_cosine_similarity"] = 1

    rows = PT.build_table2_reference_rows(base)

    assert len(rows) == 22
    oxidizer_total = next(
        row for row in rows
        if row["dataset_tool"] == "oxidizer" and row["row_type"] == "subtotal"
    )
    assert oxidizer_total["paper_avg_cosine_similarity"] == pytest.approx(5 / 6)
    assert rows[-1]["paper_tests"] == 1484


def test_table1_codeweaver_rows_preserve_partial_status() -> None:
    reference = _official_shape_table1_rows()
    crust_categories = {
        "both_compile": [f"both-{index}" for index in range(40)],
        "agent_only": [f"agent-{index}" for index in range(49)],
        "tool_only": ["tool-0"],
        "neither": [f"neither-{index}" for index in range(10)],
    }
    projects = []
    for tool, project in C.PAPER_RUNTIME_TESTS_BY_PROJECT:
        projects.append({
            "id": f"{tool}__{project}", "tool": tool, "loc_source": 1,
        })
    for names in crust_categories.values():
        projects.extend(
            {"id": f"crust__{name}", "tool": "crust", "loc_source": 1}
            for name in names
        )
    raw_rows = []
    generated_rows = []
    for index, project in enumerate(projects):
        raw_rows.append(_raw_row(
            project["id"],
            project["tool"],
            unavailable=index == 0,
        ))
        generated_rows.append(_generated_row(project["id"], project["tool"]))

    rows = PT.build_table1_side_by_side(
        reference_base_rows=reference,
        crust_categories=crust_categories,
        manifest={"projects": projects},
        raw_rows=raw_rows,
        generated_test_project_rows=generated_rows,
    )

    assert len(rows) == 27
    grand = rows[-1]
    assert grand["codeweaver_project_count"] == 118
    assert grand["codeweaver_loc"] == 118
    assert grand["codeweaver_compilation_success_percent"] == 100
    assert grand["codeweaver_validated_tests_expected"] == 118
    assert grand["codeweaver_validated_tests_executed"] == 117
    assert grand["codeweaver_validated_tests_executed_status"] == PT.PARTIAL
    assert grand["codeweaver_function_validation_expected"] == 18
    assert grand["codeweaver_function_validation_expected_status"] == C.Status.MEASURED


def _paper_test_row(tool: str, project: str, tests: int) -> dict:
    return {
        "variant": "full",
        "repetition": "0",
        "tool": tool,
        "project": project,
        "paper_runtime_tests": str(tests),
        "mapped_runtime_cases": str(tests),
        "assertion_count_runtime_matches": str(tests),
        "assertion_count_runtime_mismatches": "0",
        "assert_equal_comparable": str(tests),
        "assert_equal_matching": str(tests),
        "assert_equal_type_good": str(tests),
        "assert_equal_type_total": str(tests),
        "assert_true_type_good": "0",
        "assert_true_type_total": "0",
        "assert_false_type_good": "0",
        "assert_false_type_total": "0",
        "other_type_good": "0",
        "other_type_total": "0",
        "avg_cosine_similarity": "0.9",
        "avg_source_loc": "10",
        "avg_target_loc": "11",
        "avg_source_method_calls": "4",
        "avg_target_method_calls": "5",
    }


def test_table2_codeweaver_rows_use_same_project_structure() -> None:
    reference = _table2_reference_rows()
    measured = [
        _paper_test_row(tool, project, tests)
        for (tool, project), tests in C.PAPER_RUNTIME_TESTS_BY_PROJECT.items()
    ]

    rows = PT.build_table2_side_by_side(
        reference_base_rows=reference,
        paper_test_project_rows=measured,
    )

    assert len(rows) == 22
    grand = rows[-1]
    assert grand["paper_tests"] == 1484
    assert grand["codeweaver_tests"] == 1484
    assert grand["codeweaver_tests_translated"] == 1484
    assert grand["codeweaver_assert_equal_type_match_percent"] == 100
    assert grand["codeweaver_tests_status"] == C.Status.MEASURED


def test_table_comparison_rejects_cross_repetition_aggregation() -> None:
    with pytest.raises(ValueError, match="one explicit repetition"):
        PT.build_table2_side_by_side(
            reference_base_rows=_table2_reference_rows(),
            paper_test_project_rows=[],
            repetition=None,
        )


def test_load_reference_workbook_reads_first_duplicate_table2_headers(
    tmp_path: Path,
) -> None:
    openpyxl = C.optional_import("openpyxl")
    if openpyxl is None:
        pytest.skip("openpyxl is not installed")
    workbook = openpyxl.Workbook()
    table1 = workbook.active
    table1.title = PT.TABLE1_SHEET
    table1_headers = [
        "tool", "project", "source lang", "target lang", "LoC",
        "tool compile %", "agent compile %", "# executed tests",
        "TOOL (# test exec - tool)", "TOOL (# test pass - tool)",
        "TOOL (# test fail - tool)", "AGENT (# test exec - tool)",
        "AGENT (# test pass - tool)", "AGENT (# test fail - tool)",
        "AGENT (# test exec - trans)", "AGENT (# test pass - trans)",
        "AGENT (# test fail - trans)", "AGENT (# test exec - gen)",
        "AGENT (# test pass - gen)", "AGENT (# test fail - gen)",
        "test coverage %", "test coverage+ %", "Exercised",
        "tool FS", "agent FS", "tool FF", "agent FF",
    ]
    table1.append(table1_headers)
    tool_projects = [
        ("oxidizer", f"oxidizer-{index}") for index in range(6)
    ] + [
        ("alphatrans", f"alphatrans-{index}") for index in range(4)
    ] + [
        ("skel", f"skel-{index}") for index in range(8)
    ] + [
        ("swe-agent", project) for project in PT.CRUST_CATEGORY_PROJECTS
    ]
    for tool, project in tool_projects:
        values = {
            "tool": tool,
            "project": project,
            "source lang": "x",
            "target lang": "y",
            "LoC": 1,
            "tool compile %": 100,
            "agent compile %": 100,
            "# executed tests": 1,
        }
        table1.append([values.get(header, 0) for header in table1_headers])
    table1.append(["total"])

    table2 = workbook.create_sheet(PT.TABLE2_SHEET)
    table2_headers = [
        "tool", "project", "source lang", "target lang", "# tests",
        "# tests translated", "# tests not translated",
        "# tests w/ matching # assertions",
        "# tests w/ not matching # assertions", "avg cosine sim",
        "total comparable assertEquals", "total matching assertEquals",
        "avg source loc", "avg target loc", "avg method calls source",
        "avg method calls target", "assertEqual match %", "assertTrue match %",
        "assertFalse match %", "other match %", "# tests",
    ]
    table2.append(table2_headers)
    for tool, count in (("oxidizer", 6), ("alphatrans", 4), ("skel", 8)):
        for index in range(count):
            row = [tool, f"{tool}-{index}", "x", "y", 7]
            row.extend([7, 0, 7, 0, 0.9, 1, 1, 1, 1, 1, 1, 100, "-", "-", "-", 999])
            table2.append(row)
    table2.append(["swe-agent", "crust-bench"])

    crust = workbook.create_sheet(PT.CRUST_CLASSIFICATION_SHEET)
    crust.append([
        "project", "tool compile (1/0)", "agent compile (1/0)",
    ])
    categories = (
        ("both", 40, 1, 1),
        ("agent", 49, 0, 1),
        ("tool", 1, 1, 0),
        ("neither", 10, 0, 0),
    )
    for prefix, count, tool_compile, agent_compile in categories:
        for index in range(count):
            crust.append([
                f"{prefix}-{index}", tool_compile, agent_compile,
            ])
    path = tmp_path / "results.xlsx"
    workbook.save(path)

    loaded = PT.load_reference_workbook(path, verify_checksum=False)

    assert len(loaded["table1_base_rows"]) == 22
    assert len(loaded["table2_base_rows"]) == 18
    assert loaded["table2_base_rows"][0]["paper_tests"] == 7
    assert {
        key: len(value) for key, value in loaded["crust_categories"].items()
    } == PT.CRUST_CATEGORY_EXPECTED_COUNTS
