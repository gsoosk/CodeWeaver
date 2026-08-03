from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.recodeagent import paper_test_compare as P


def test_paper_runtime_inventory_matches_published_denominators():
    assert sum(P.PAPER_RUNTIME_COUNTS.values()) == 1484
    assert sum(P.PAPER_STATIC_COUNTS.values()) == 1472


def test_assertion_type_groups_preserve_weighted_counts():
    summary = {
        "assertion_match_percentages": {
            "assertEquals": {"good_match_count": 8, "total_source": 10},
            "assertTrue": {"good_match_count": 3, "total_source": 4},
            "assertFalse": {"good_match_count": 2, "total_source": 5},
            "assertNull": {"good_match_count": 6, "total_source": 7},
        }
    }
    assert P._assertion_type_group_counts(summary) == {
        "assert_equal": (8, 10),
        "assert_true": (3, 4),
        "assert_false": (2, 5),
        "other": (6, 7),
    }


def test_runtime_assertion_counts_apply_parameter_weights():
    metadata = [{"runtime_weight": 7}, {"runtime_weight": 1}]
    report = {"test_pairs": [
        {"metrics": {"assertions_match": True}},
        {"metrics": {"assertions_match": False}},
    ]}
    assert P._runtime_assertion_match_counts(metadata, report) == (7, 1)
    assert sum(weight - 1 for weight in P.PARAMETERIZED_RUNTIME_WEIGHTS.values()) == 12


def test_runtime_weight_expands_only_parameterized_commons_csv_methods():
    assert P.runtime_weight(
        "alphatrans",
        "commons-csv",
        "org.apache.commons.csv.CSVFileParserTest",
        "testCSVFile",
    ) == 7
    assert P.runtime_weight(
        "alphatrans", "commons-cli", "org.example.Test", "testPlain"
    ) == 1


def test_map_reference_rows_normalizes_camel_and_snake_case():
    rows = [
        {
            "project": "checkdigit",
            "go test path": "checkdigit_test.go",
            "go test name": "TestNewLuhn",
            "rust test path": "tests/checkdigit_test.rs",
            "rust test name": "TestNewLuhn",
        }
    ]
    candidates = [
        P.TargetTest("tests/integration_test.rs", "test_new_luhn"),
        P.TargetTest("tests/generated.rs", "test_extra_case"),
    ]
    mapped, metadata, generated = P.map_reference_rows(
        rows,
        candidates,
        source_language="go",
        target_language="rust",
    )
    assert mapped[0]["rust test path"] == "tests/integration_test.rs"
    assert mapped[0]["rust test name"] == "test_new_luhn"
    assert metadata[0]["mapped"] is True
    assert metadata[0]["mapping_score"] == pytest.approx(
        P._target_score(
            "tests/checkdigit_test.rs",
            "TestNewLuhn",
            P.TargetTest("tests/integration_test.rs", "test_new_luhn"),
        )
    )
    assert generated == [P.TargetTest("tests/generated.rs", "test_extra_case")]


def test_map_reference_rows_preserves_explicit_missing_rows():
    rows = [
        {
            "project": "stats",
            "go test path": "mean_test.go",
            "go test name": "TestMean",
            "rust test path": "",
            "rust test name": "",
        }
    ]
    mapped, metadata, generated = P.map_reference_rows(
        rows, [], source_language="go", target_language="rust"
    )
    assert mapped[0]["rust test path"] == ""
    assert mapped[0]["rust test name"] == ""
    assert metadata[0]["mapped"] is False
    assert generated == []


def test_uninventoried_source_orchestrator_is_not_classified_as_generated():
    generated = [
        P.TargetTest("index.js", "test"),
        P.TargetTest("index.js", "test_new_edge_case"),
    ]
    source = [P.TargetTest("source.py", "test")]
    assert P.exclude_uninventoried_source_tests(generated, source) == [
        P.TargetTest("index.js", "test_new_edge_case")
    ]


def test_project_summary_uses_runtime_weights_not_static_count(tmp_path):
    metadata = [
        {
            "source_path": "org.apache.commons.csv.CSVFileParserTest",
            "source_name": "testCSVFile",
            "mapped": True,
        },
        {
            "source_path": "org.apache.commons.csv.CSVFileParserTest",
            "source_name": "testCSVUrl",
            "mapped": False,
        },
    ]
    row = P._project_summary(
        variant="full",
        repetition=0,
        project_id="alphatrans__commons-csv",
        tool="alphatrans",
        project="commons-csv",
        metadata=metadata,
        generated=[],
        generated_execution=P._generated_execution(0, 0, 0, 0),
        report={"summary": {}},
        report_path=tmp_path / "report.json",
    )
    assert row["mapped_static_methods"] == 1
    assert row["mapped_runtime_cases"] == 7
    assert row["paper_runtime_tests"] == 298


def test_filter_generated_target_tests_removes_python_helpers():
    generated = [
        P.TargetTest("tests/test_a.py", "get_fixture"),
        P.TargetTest("tests/test_a.py", "test_generated"),
    ]
    assert P.filter_generated_target_tests(generated, "python") == [
        P.TargetTest("tests/test_a.py", "test_generated")
    ]


def test_python_generated_execution_counts_parameterized_runtime_cases(tmp_path: Path):
    target = tmp_path / "target"
    tests = target / "tests"
    tests.mkdir(parents=True)
    (tests / "test_generated.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', [1, 2])\n"
        "def test_generated_many(value):\n"
        "    assert value > 0\n"
        "def test_generated_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )
    result = P.evaluate_codeweaver_generated_tests(
        "alphatrans",
        target,
        [
            P.TargetTest("tests/test_generated.py", "test_generated_many"),
            P.TargetTest("tests/test_generated.py", "test_generated_failure"),
        ],
        timeout=60,
    )
    assert result.expected.value == 3
    assert result.executed.value == 3
    assert result.passed.value == 2
    assert result.failed.value == 1
    assert result.not_executed.value == 0


def test_javascript_generated_execution_calls_only_selected_functions(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "package.json").write_text(
        json.dumps({"type": "module"}), encoding="utf-8"
    )
    (target / "index.js").write_text(
        "function test_generated_pass() { return true; }\n"
        "function test_generated_fail() { return false; }\n"
        "function test_translated() { throw new Error('must not run'); }\n",
        encoding="utf-8",
    )
    result = P.evaluate_codeweaver_generated_tests(
        "skel",
        target,
        [
            P.TargetTest("index.js", "test_generated_pass"),
            P.TargetTest("index.js", "test_generated_fail"),
        ],
        timeout=60,
    )
    assert result.expected.value == 2
    assert result.executed.value == 2
    assert result.passed.value == 1
    assert result.failed.value == 1


def test_generated_project_row_keeps_coverage_beside_execution():
    row = P.generated_project_row(
        variant="full",
        repetition=0,
        manifest_row={
            "id": "skel__bst",
            "tool": "skel",
            "project": "bst",
        },
        generated=[P.TargetTest("index.js", "test_generated")],
        execution=P._generated_execution(1, 1, 1, 0),
        coverage_before=P.C.Measurement.ok(40.0),
        coverage_after=P.C.Measurement.ok(75.0),
    )

    assert row["generated_tests_passed"] == 1
    assert row["coverage_before"] == pytest.approx(40.0)
    assert row["coverage_after"] == pytest.approx(75.0)
    assert row["coverage_after_status"] == P.C.Status.MEASURED


def test_cargo_target_and_listing_helpers():
    assert P._cargo_target_args("tests/generated.rs") == (
        "cargo", "test", "--test", "generated",
    )
    assert P._cargo_target_args("src/lib.rs") == ("cargo", "test", "--lib")
    assert P._cargo_listed_tests("alpha::test_one: test\nother: benchmark\n") == [
        "alpha::test_one"
    ]
