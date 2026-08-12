"""Render Rustine paper-reference versus CodeWeaver measured comparison reports."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

from experiments.recodeagent import render as RD
from experiments.rustine import common as C
from experiments.rustine.config import load_subject_config

SAFETY_FIELDS = (
    "pointer_arithmetic",
    "raw_pointer_declarations",
    "raw_pointer_dereferences",
    "unsafe_lines",
    "unsafe_type_casts",
    "unsafe_calls",
)
RUSTINE_ARTIFACT_REPOSITORY = "https://github.com/Intelligent-CAT-Lab/Rustine"
PAPER_BENCHMARK_TEST_FUNCTION_COVERAGE_PERCENT = 74.7
PAPER_BENCHMARK_TEST_LINE_COVERAGE_PERCENT = 72.2


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return [100.0 * max(0.0, center - radius), 100.0 * min(1.0, center + radius)]


def _mcnemar_exact(rustine_only: int, codeweaver_only: int) -> float | None:
    discordant = rustine_only + codeweaver_only
    if discordant == 0:
        return None
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(rustine_only, codeweaver_only) + 1)
    ) / (2**discordant)
    return min(1.0, 2.0 * tail)


def _metric_text(metric: dict[str, Any], *, percent: bool = False) -> str:
    status = metric.get("status")
    value = metric.get("value")
    if status == C.MEASURED:
        if isinstance(value, bool):
            return "pass" if value else "fail"
        if percent and isinstance(value, (int, float)):
            return f"{value:.1f}%"
        return str(value)
    if status == C.INFERRED:
        return f"{value}*"
    return status or "missing"


def _paper_text(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:g}%" if percent else str(value)


def aggregate_results(config: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    rows = evaluation.get("rows", [])
    subjects = config["subjects"]
    paper_function = [
        subject["paper_validation"]["function_coverage_percent"]
        for subject in subjects
        if subject["paper_validation"]["function_coverage_percent"] is not None
    ]
    paper_line = [
        subject["paper_validation"]["line_coverage_percent"]
        for subject in subjects
        if subject["paper_validation"]["line_coverage_percent"] is not None
    ]
    paper_assertions = {
        field: sum(
            subject["paper_validation"][f"assertions_{field}"] or 0 for subject in subjects
        )
        for field in ("executed", "passed", "failed")
    }
    paper_testable_subjects = sum(
        subject["paper_validation"]["assertions_executed"] is not None
        for subject in subjects
    )
    paper_fixed_contract_passed = sum(
        subject["paper_validation"]["assertions_executed"] is not None
        and subject["paper_validation"]["assertions_failed"] == 0
        and subject["paper_validation"]["assertions_passed"]
        == subject["paper_validation"]["assertions_executed"]
        for subject in subjects
    )

    def true_count(field: str) -> int:
        return sum(
            row[field].get("status") == C.MEASURED and row[field].get("value") is True
            for row in rows
        )

    def measured_values(field: str) -> list[float]:
        return [
            float(row[field]["value"])
            for row in rows
            if field in row
            and row[field].get("status") == C.MEASURED
            and isinstance(row[field].get("value"), (int, float))
            and not isinstance(row[field].get("value"), bool)
        ]

    safety: dict[str, Any] = {}
    for field in SAFETY_FIELDS:
        values = [
            row["safety"][field]["value"]
            for row in rows
            if row["safety"][field].get("status") == C.MEASURED
        ]
        safety[field] = {
            "measured_rows": len(values),
            "total_rows": len(rows),
            "sum": sum(values) if values else None,
            "status": "complete" if len(values) == len(rows) and rows else "partial",
        }
    function_values = measured_values("function_coverage_percent")
    line_values = measured_values("line_coverage_percent")
    coverage_counts = []
    for row in rows:
        metric = row.get("coverage_details", {}).get("paper_comparable", {})
        value = metric.get("value")
        if metric.get("status") != C.MEASURED or not isinstance(value, dict):
            continue
        required = {
            "functions_count",
            "functions_covered",
            "lines_count",
            "lines_covered",
        }
        if required <= set(value):
            coverage_counts.append(value)
    functions_count = sum(value["functions_count"] for value in coverage_counts)
    functions_covered = sum(value["functions_covered"] for value in coverage_counts)
    lines_count = sum(value["lines_count"] for value in coverage_counts)
    lines_covered = sum(value["lines_covered"] for value in coverage_counts)
    codeweaver_assertions = {}
    for field in ("executed", "passed", "failed"):
        metrics = [row["assertions"][field] for row in rows]
        credited = [
            metric["value"]
            for metric in metrics
            if metric.get("status") in {C.MEASURED, C.INFERRED}
            and isinstance(metric.get("value"), (int, float))
        ]
        codeweaver_assertions[field] = {
            "sum": sum(credited) if credited else None,
            "credited_rows": len(credited),
            "measured_rows": sum(
                metric.get("status") == C.MEASURED for metric in metrics
            ),
            "inferred_rows": sum(
                metric.get("status") == C.INFERRED for metric in metrics
            ),
            "total_rows": len(metrics),
        }
    codeweaver_assertion_rate = None
    if (
        codeweaver_assertions["executed"]["sum"]
        and codeweaver_assertions["passed"]["sum"] is not None
    ):
        codeweaver_assertion_rate = (
            100.0
            * codeweaver_assertions["passed"]["sum"]
            / codeweaver_assertions["executed"]["sum"]
        )
    elapsed_values = measured_values("elapsed_seconds")
    output_token_values = measured_values("output_tokens")
    nano_aiu_values = measured_values("nano_aiu")
    premium_request_values = measured_values("premium_requests")
    compiled = true_count("compilation")
    fixed_contract_passed = true_count("fixed_contract_tests")
    rows_by_subject = {row["subject_id"]: row for row in rows}
    compilation_pairs = []
    contract_pairs = []
    for subject in subjects:
        row = rows_by_subject.get(subject["id"], {})
        codeweaver_compiled = (
            row.get("compilation", {}).get("status") == C.MEASURED
            and row.get("compilation", {}).get("value") is True
        )
        compilation_pairs.append((True, codeweaver_compiled))
        if subject["paper_validation"]["assertions_executed"] is not None:
            rustine_passed = (
                subject["paper_validation"]["assertions_failed"] == 0
                and subject["paper_validation"]["assertions_passed"]
                == subject["paper_validation"]["assertions_executed"]
            )
            codeweaver_passed = (
                row.get("fixed_contract_tests", {}).get("status") == C.MEASURED
                and row.get("fixed_contract_tests", {}).get("value") is True
            )
            contract_pairs.append((rustine_passed, codeweaver_passed))

    def paired_summary(pairs):
        rustine_only = sum(rustine and not codeweaver for rustine, codeweaver in pairs)
        codeweaver_only = sum(codeweaver and not rustine for rustine, codeweaver in pairs)
        return {
            "pairs": len(pairs),
            "both_pass": sum(rustine and codeweaver for rustine, codeweaver in pairs),
            "both_fail": sum(not rustine and not codeweaver for rustine, codeweaver in pairs),
            "rustine_only": rustine_only,
            "codeweaver_only": codeweaver_only,
            "mcnemar_exact_p": _mcnemar_exact(rustine_only, codeweaver_only),
        }

    return {
        "paper": {
            "subjects": 23,
            "compilation_success": 23,
            "testable_subjects": paper_testable_subjects,
            "fixed_contract_passed": paper_fixed_contract_passed,
            "benchmark_test_function_coverage_percent": (
                PAPER_BENCHMARK_TEST_FUNCTION_COVERAGE_PERCENT
            ),
            "benchmark_test_line_coverage_percent": (
                PAPER_BENCHMARK_TEST_LINE_COVERAGE_PERCENT
            ),
            "unweighted_subject_mean_function_coverage_percent": statistics.mean(
                paper_function
            ),
            "unweighted_subject_mean_line_coverage_percent": statistics.mean(
                paper_line
            ),
            "assertions": paper_assertions,
            "assertion_pass_rate_percent": (
                100.0
                * paper_assertions["passed"]
                / paper_assertions["executed"]
            ),
            "safety": {
                field: sum(subject["paper_safety"][field] for subject in subjects)
                for field in SAFETY_FIELDS
            },
        },
        "codeweaver": {
            "rows": len(rows),
            "run_completed": true_count("run_completion"),
            "contract_integrity_passed": true_count("contract_integrity"),
            "compiled": compiled,
            "compilation_rate_percent": 100.0 * compiled / 23 if rows else None,
            "compilation_rate_wilson_95_percent": _wilson_interval(compiled, 23),
            "fixed_contract_passed": fixed_contract_passed,
            "fixed_contract_rate_percent": (
                100.0 * fixed_contract_passed / paper_testable_subjects
                if rows and paper_testable_subjects
                else None
            ),
            "fixed_contract_rate_wilson_95_percent": _wilson_interval(
                fixed_contract_passed, paper_testable_subjects
            ),
            "fixed_contract_measured_rows": sum(
                row["fixed_contract_tests"].get("status") == C.MEASURED
                for row in rows
            ),
            "mean_function_coverage_percent": (
                statistics.mean(function_values) if function_values else None
            ),
            "function_coverage_measured_rows": len(function_values),
            "mean_line_coverage_percent": (
                statistics.mean(line_values) if line_values else None
            ),
            "line_coverage_measured_rows": len(line_values),
            "aggregate_function_coverage_percent": (
                100.0 * functions_covered / functions_count
                if functions_count
                else None
            ),
            "aggregate_line_coverage_percent": (
                100.0 * lines_covered / lines_count if lines_count else None
            ),
            "aggregate_coverage_measured_rows": len(coverage_counts),
            "functions_count": functions_count or None,
            "functions_covered": functions_covered if functions_count else None,
            "lines_count": lines_count or None,
            "lines_covered": lines_covered if lines_count else None,
            "assertions": codeweaver_assertions,
            "assertion_pass_rate_percent": codeweaver_assertion_rate,
            "elapsed_seconds_sum": sum(elapsed_values) if elapsed_values else None,
            "elapsed_seconds_median": (
                statistics.median(elapsed_values) if elapsed_values else None
            ),
            "elapsed_measured_rows": len(elapsed_values),
            "output_tokens_sum": (
                int(sum(output_token_values)) if output_token_values else None
            ),
            "output_tokens_measured_rows": len(output_token_values),
            "nano_aiu_sum": int(sum(nano_aiu_values)) if nano_aiu_values else None,
            "nano_aiu_measured_rows": len(nano_aiu_values),
            "premium_requests_sum": (
                int(sum(premium_request_values))
                if premium_request_values
                else None
            ),
            "premium_requests_measured_rows": len(premium_request_values),
            "safety": safety,
            "paired_statistics": {
                "compilation": paired_summary(compilation_pairs),
                "fixed_contract": paired_summary(contract_pairs),
            },
        },
    }


def validation_csv_rows(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for row in evaluation.get("rows", []):
        paper = row["paper_validation"]
        item = {
            "subject_id": row["subject_id"],
            "subject": row["subject"],
            "variant": row["variant"],
            "repetition": row["repetition"],
            "codeweaver_pipeline_status": row.get("pipeline_status"),
            "codeweaver_pipeline_error": row.get("pipeline_error", ""),
            "paper_compilation_percent": paper["compilation_percent"],
            "paper_function_coverage_percent": paper["function_coverage_percent"],
            "paper_line_coverage_percent": paper["line_coverage_percent"],
            "paper_assertions_executed": paper["assertions_executed"],
            "paper_assertions_passed": paper["assertions_passed"],
            "paper_assertions_failed": paper["assertions_failed"],
        }
        for field in (
            "run_completion",
            "contract_integrity",
            "compilation",
            "fixed_contract_tests",
            "function_coverage_percent",
            "line_coverage_percent",
        ):
            C.flatten_measurement(item, f"codeweaver_{field}", row[field])
        for field in ("executed", "passed", "failed"):
            C.flatten_measurement(
                item, f"codeweaver_assertions_{field}", row["assertions"][field]
            )
        output.append(item)
    return output


def safety_csv_rows(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for row in evaluation.get("rows", []):
        item = {
            "subject_id": row["subject_id"],
            "subject": row["subject"],
            "variant": row["variant"],
            "repetition": row["repetition"],
            "codeweaver_pipeline_status": row.get("pipeline_status"),
        }
        for field in SAFETY_FIELDS:
            item[f"paper_{field}"] = row["paper_safety"][field]
            C.flatten_measurement(item, f"codeweaver_{field}", row["safety"][field])
        output.append(item)
    return output


def statistics_csv_rows(aggregate: dict[str, Any]) -> list[dict[str, Any]]:
    paper = aggregate["paper"]
    codeweaver = aggregate["codeweaver"]
    definitions = (
        (
            "compilation",
            paper["compilation_success"],
            paper["subjects"],
            codeweaver["compiled"],
            codeweaver["compilation_rate_percent"],
            codeweaver["compilation_rate_wilson_95_percent"],
        ),
        (
            "fixed_contract",
            paper["fixed_contract_passed"],
            paper["testable_subjects"],
            codeweaver["fixed_contract_passed"],
            codeweaver["fixed_contract_rate_percent"],
            codeweaver["fixed_contract_rate_wilson_95_percent"],
        ),
    )
    rows = []
    for outcome, paper_successes, total, successes, rate, interval in definitions:
        paired = codeweaver["paired_statistics"][outcome]
        rows.append(
            {
                "outcome": outcome,
                "subjects": total,
                "rustine_successes": paper_successes,
                "codeweaver_successes": successes,
                "codeweaver_rate_percent": rate,
                "codeweaver_wilson_95_lower_percent": interval[0],
                "codeweaver_wilson_95_upper_percent": interval[1],
                "both_pass": paired["both_pass"],
                "both_fail": paired["both_fail"],
                "rustine_only": paired["rustine_only"],
                "codeweaver_only": paired["codeweaver_only"],
                "mcnemar_exact_p": paired["mcnemar_exact_p"],
            }
        )
    return rows


def _validation_markdown(evaluation: dict[str, Any]) -> str:
    headers = [
        "ID",
        "Subject",
        "CW pipeline",
        "Rustine compile",
        "CW compile",
        "Rustine func",
        "CW func",
        "Rustine line",
        "CW line",
        "Rustine assertions E/P/F",
        "CW assertions E/P/F",
        "Fixed contract",
    ]
    rows = []
    for row in evaluation["rows"]:
        paper = row["paper_validation"]
        paper_assertions = (
            "N/A"
            if paper["assertions_executed"] is None
            else f"{paper['assertions_executed']}/{paper['assertions_passed']}/"
            f"{paper['assertions_failed']}"
        )
        measured_assertions = "/".join(
            _metric_text(row["assertions"][field])
            for field in ("executed", "passed", "failed")
        )
        label = str(row["subject_id"])
        if len(evaluation["rows"]) > 23:
            label += f".r{row['repetition']}"
        rows.append(
            [
                label,
                row["subject"],
                row.get("pipeline_status") or _metric_text(row["run_completion"]),
                _paper_text(paper["compilation_percent"], percent=True),
                _metric_text(row["compilation"]),
                _paper_text(paper["function_coverage_percent"], percent=True),
                _metric_text(row["function_coverage_percent"], percent=True),
                _paper_text(paper["line_coverage_percent"], percent=True),
                _metric_text(row["line_coverage_percent"], percent=True),
                paper_assertions,
                measured_assertions,
                _metric_text(row["fixed_contract_tests"]),
            ]
        )
    return RD.markdown_table(headers, rows)


def _safety_markdown(evaluation: dict[str, Any]) -> str:
    short = {
        "pointer_arithmetic": "Ptr arith",
        "raw_pointer_declarations": "Raw decl",
        "raw_pointer_dereferences": "Raw deref",
        "unsafe_lines": "Unsafe lines",
        "unsafe_type_casts": "Unsafe casts",
        "unsafe_calls": "Unsafe calls",
    }
    headers = ["ID", "Subject"]
    for field in SAFETY_FIELDS:
        headers.extend([f"Rustine {short[field]}", f"CW {short[field]}"])
    rows = []
    for row in evaluation["rows"]:
        values: list[Any] = [row["subject_id"], row["subject"]]
        for field in SAFETY_FIELDS:
            values.extend(
                [row["paper_safety"][field], _metric_text(row["safety"][field])]
            )
        rows.append(values)
    return RD.markdown_table(headers, rows)


def _safety_summary_markdown(aggregate: dict[str, Any]) -> str:
    labels = {
        "pointer_arithmetic": "Pointer arithmetic",
        "raw_pointer_declarations": "Raw pointer declarations",
        "raw_pointer_dereferences": "Raw pointer dereferences",
        "unsafe_lines": "Unsafe lines",
        "unsafe_type_casts": "Unsafe type casts",
        "unsafe_calls": "Unsafe calls",
    }
    rows = []
    for field in SAFETY_FIELDS:
        measured = aggregate["codeweaver"]["safety"][field]
        rows.append(
            [
                labels[field],
                aggregate["paper"]["safety"][field],
                (
                    f"{measured['sum']} ({measured['measured_rows']}/"
                    f"{measured['total_rows']} measured)"
                    if measured["sum"] is not None
                    else f"unavailable (0/{measured['total_rows']} measured)"
                ),
            ]
        )
    return RD.markdown_table(
        ["Safety metric", "Rustine paper total", "CodeWeaver measured total"],
        rows,
    )


def _summary_markdown(aggregate: dict[str, Any]) -> str:
    paper = aggregate["paper"]
    codeweaver = aggregate["codeweaver"]
    compilation_ci = codeweaver["compilation_rate_wilson_95_percent"]
    contract_ci = codeweaver["fixed_contract_rate_wilson_95_percent"]
    rows = [
        ["Subjects/runs", paper["subjects"], codeweaver["rows"]],
        [
            "CodeWeaver pipeline terminal success",
            "not applicable",
            f"{codeweaver['run_completed']}/{codeweaver['rows']}",
        ],
        [
            "Immutable-contract integrity",
            "paper reference",
            f"{codeweaver['contract_integrity_passed']}/{codeweaver['rows']}",
        ],
        [
            "Compilation successes",
            f"{paper['compilation_success']}/{paper['subjects']} (100.0%)",
            (
                f"{codeweaver['compiled']}/{paper['subjects']} "
                f"({codeweaver['compilation_rate_percent']:.1f}%; "
                f"95% Wilson CI {compilation_ci[0]:.1f}-{compilation_ci[1]:.1f}%)"
            ),
        ],
        [
            "Fixed-contract passes",
            f"{paper['fixed_contract_passed']}/{paper['testable_subjects']} testable",
            (
                f"{codeweaver['fixed_contract_passed']}/{paper['testable_subjects']} "
                f"({codeweaver['fixed_contract_rate_percent']:.1f}%); "
                f"95% Wilson CI {contract_ci[0]:.1f}-{contract_ci[1]:.1f}%; "
                f"{codeweaver['fixed_contract_measured_rows']} measured"
            ),
        ],
        [
            "Paired exact McNemar p (compilation/fixed contract)",
            "reference",
            "/".join(
                (
                    (
                        f"{codeweaver['paired_statistics'][field]['mcnemar_exact_p']:.4g}"
                        if codeweaver["paired_statistics"][field][
                            "mcnemar_exact_p"
                        ]
                        is not None
                        else "N/A"
                    )
                    for field in ("compilation", "fixed_contract")
                )
            ),
        ],
        [
            "Translation function coverage (unweighted subject mean)",
            f"{paper['unweighted_subject_mean_function_coverage_percent']:.1f}%",
            (
                f"{codeweaver['mean_function_coverage_percent']:.1f}% "
                f"({codeweaver['function_coverage_measured_rows']} measured)"
                if codeweaver["mean_function_coverage_percent"] is not None
                else "unavailable"
            ),
        ],
        [
            "Translation line coverage (unweighted subject mean)",
            f"{paper['unweighted_subject_mean_line_coverage_percent']:.1f}%",
            (
                f"{codeweaver['mean_line_coverage_percent']:.1f}% "
                f"({codeweaver['line_coverage_measured_rows']} measured)"
                if codeweaver["mean_line_coverage_percent"] is not None
                else "unavailable"
            ),
        ],
        [
            "Benchmark test-suite coverage (function/line)",
            (
                f"{paper['benchmark_test_function_coverage_percent']:.1f}%/"
                f"{paper['benchmark_test_line_coverage_percent']:.1f}% "
                "(paper Table 1)"
            ),
            "reference characteristic, not a system outcome",
        ],
        [
            "CodeWeaver count-weighted coverage (function/line)",
            "not derivable from published Rustine counts",
            (
                f"{codeweaver['aggregate_function_coverage_percent']:.1f}%/"
                f"{codeweaver['aggregate_line_coverage_percent']:.1f}% "
                f"({codeweaver['aggregate_coverage_measured_rows']} measured)"
                if codeweaver["aggregate_function_coverage_percent"] is not None
                and codeweaver["aggregate_line_coverage_percent"] is not None
                else "unavailable"
            ),
        ],
        [
            "Assertions E/P/F",
            "{executed}/{passed}/{failed}".format(**paper["assertions"]),
            "/".join(
                (
                    str(codeweaver["assertions"][field]["sum"])
                    if codeweaver["assertions"][field]["sum"] is not None
                    else "unavailable"
                )
                for field in ("executed", "passed", "failed")
            )
            + " (measured or explicitly inferred credits only)",
        ],
        [
            "Assertion pass rate",
            f"{paper['assertion_pass_rate_percent']:.1f}%",
            (
                f"{codeweaver['assertion_pass_rate_percent']:.1f}% "
                f"({codeweaver['assertions']['executed']['credited_rows']} credited runs)"
                if codeweaver["assertion_pass_rate_percent"] is not None
                else "unavailable"
            ),
        ],
        [
            "Output tokens",
            "not reported",
            (
                f"{codeweaver['output_tokens_sum']:,} "
                f"({codeweaver['output_tokens_measured_rows']} measured runs)"
                if codeweaver["output_tokens_sum"] is not None
                else "unavailable"
            ),
        ],
        [
            "AI credits / premium requests",
            "not reported",
            (
                f"{codeweaver['nano_aiu_sum'] / 1e9:.1f} / "
                f"{codeweaver['premium_requests_sum']} "
                f"({codeweaver['nano_aiu_measured_rows']} measured runs)"
                if codeweaver["nano_aiu_sum"] is not None
                and codeweaver["premium_requests_sum"] is not None
                else "unavailable"
            ),
        ],
        [
            "Cumulative/median elapsed time",
            "not reported",
            (
                f"{codeweaver['elapsed_seconds_sum'] / 3600:.2f} h / "
                f"{codeweaver['elapsed_seconds_median'] / 60:.1f} min "
                f"({codeweaver['elapsed_measured_rows']} measured runs)"
                if codeweaver["elapsed_seconds_sum"] is not None
                else "unavailable"
            ),
        ],
    ]
    return RD.markdown_table(["Metric", "Rustine paper", "CodeWeaver measured"], rows)


def _abstract_markdown(aggregate: dict[str, Any]) -> str:
    paper = aggregate["paper"]
    codeweaver = aggregate["codeweaver"]
    return (
        "We evaluate CodeWeaver with GPT-5.6 Sol on the same 23 C-to-Rust "
        "subjects used by Rustine. To prevent target leakage, CodeWeaver receives "
        "only disclosed C inputs, Rust skeletons, and immutable test contracts; "
        "Rustine production translations remain excluded. Independent evaluation "
        f"finds {codeweaver['compiled']}/23 compiling CodeWeaver translations and "
        f"{codeweaver['fixed_contract_passed']}/{paper['testable_subjects']} "
        "fixed-contract passes. Rustine's published reference reports "
        f"{paper['compilation_success']}/23 compilation and "
        f"{paper['fixed_contract_passed']}/{paper['testable_subjects']} complete "
        "test-suite passes. Exact measured, inferred, unavailable, and not-applicable "
        "states remain distinct throughout the artifact."
    )


def _interpretation_markdown(aggregate: dict[str, Any]) -> str:
    paper = aggregate["paper"]
    codeweaver = aggregate["codeweaver"]
    paper_contract_rate = (
        100.0 * paper["fixed_contract_passed"] / paper["testable_subjects"]
    )
    compilation_gap = codeweaver["compilation_rate_percent"] - 100.0
    contract_gap = codeweaver["fixed_contract_rate_percent"] - paper_contract_rate

    def gap_text(label: str, gap: float) -> str:
        if gap < 0:
            return f"trails the Rustine paper reference by {abs(gap):.1f} percentage points in {label}"
        if gap > 0:
            return f"exceeds the Rustine paper reference by {gap:.1f} percentage points in {label}"
        return f"matches the Rustine paper reference in {label}"

    coverage = (
        f"Across {codeweaver['function_coverage_measured_rows']} translations with "
        "measured coverage, CodeWeaver's unweighted mean is "
        f"{codeweaver['mean_function_coverage_percent']:.1f}% function and "
        f"{codeweaver['mean_line_coverage_percent']:.1f}% line."
        if codeweaver["mean_function_coverage_percent"] is not None
        and codeweaver["mean_line_coverage_percent"] is not None
        else "CodeWeaver coverage was unavailable for every translation."
    )
    return (
        f"CodeWeaver {gap_text('compilation', compilation_gap)} and "
        f"{gap_text('complete fixed-contract pass rate', contract_gap)}. "
        f"{coverage} Coverage is conditioned on measurable builds and is therefore "
        "reported with its row count rather than imputed for failures. Assertion "
        "credits marked with an asterisk use the paper denominator only after all "
        "disclosed checks pass; surrogate checks with unavailable exact oracles are "
        "never promoted to measured assertion totals. These results compare complete "
        "systems under different model/tool designs and do not isolate any single "
        "architectural cause."
    )


def _latex_escape(value: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in str(value))


def render_latex(evaluation: dict[str, Any], aggregate: dict[str, Any]) -> str:
    paper = aggregate["paper"]
    codeweaver = aggregate["codeweaver"]
    lines = [
        r"\documentclass{article}",
        r"\usepackage[margin=0.5in]{geometry}",
        r"\usepackage{booktabs}",
        r"\usepackage{longtable}",
        r"\usepackage{pdflscape}",
        r"\begin{document}",
        r"\section*{CodeWeaver on Rustine's 23-repository C-to-Rust benchmark}",
        (
            r"Source: \texttt{https://arxiv.org/abs/2511.20617}. "
            r"Only this 23-subject paired experiment is compared; the older "
            r"118-project matrix is not directly comparable."
        ),
        r"\begin{abstract}",
        _latex_escape(_abstract_markdown(aggregate)),
        r"\end{abstract}",
        r"\subsection*{Aggregate summary}",
        r"\begin{tabular}{lrr}",
        r"\toprule Metric & Rustine paper & CodeWeaver measured\\\midrule",
        (
            f"Compilation & {paper['compilation_success']}/{paper['subjects']} "
            f"& {codeweaver['compiled']}/{paper['subjects']}\\\\"
        ),
        (
            f"Fixed-contract pass & {paper['fixed_contract_passed']}/"
            f"{paper['testable_subjects']} & {codeweaver['fixed_contract_passed']}/"
            f"{paper['testable_subjects']}\\\\"
        ),
        (
            f"Mean function coverage & "
            f"{paper['unweighted_subject_mean_function_coverage_percent']:.1f}\\% "
            f"& "
            + (
                f"{codeweaver['mean_function_coverage_percent']:.1f}\\%"
                if codeweaver["mean_function_coverage_percent"] is not None
                else "unavailable"
            )
            + r"\\"
        ),
        (
            f"Mean line coverage & "
            f"{paper['unweighted_subject_mean_line_coverage_percent']:.1f}\\% "
            f"& "
            + (
                f"{codeweaver['mean_line_coverage_percent']:.1f}\\%"
                if codeweaver["mean_line_coverage_percent"] is not None
                else "unavailable"
            )
            + r"\\"
        ),
        r"\bottomrule",
        r"\end{tabular}",
        r"\subsection*{Validation: paper Table 2 extended with CodeWeaver}",
        r"\scriptsize",
        r"\begin{longtable}{r l r l r l r l l l}",
        r"ID & Subject & R comp & CW comp & R func & CW func & R line & CW line & R E/P/F & CW E/P/F\\\hline",
    ]
    for row in evaluation["rows"]:
        paper = row["paper_validation"]
        paper_assertions = (
            "N/A"
            if paper["assertions_executed"] is None
            else f"{paper['assertions_executed']}/{paper['assertions_passed']}/{paper['assertions_failed']}"
        )
        measured = "/".join(
            _metric_text(row["assertions"][field])
            for field in ("executed", "passed", "failed")
        )
        values = [
            row["subject_id"],
            row["subject"],
            paper["compilation_percent"],
            _metric_text(row["compilation"]),
            _paper_text(paper["function_coverage_percent"]),
            _metric_text(row["function_coverage_percent"]),
            _paper_text(paper["line_coverage_percent"]),
            _metric_text(row["line_coverage_percent"]),
            paper_assertions,
            measured,
        ]
        lines.append(" & ".join(_latex_escape(value) for value in values) + r"\\")
    lines.extend(
        [
            r"\end{longtable}",
            r"\subsection*{Safety: paper Table 3 extended with CodeWeaver}",
            r"\begin{landscape}",
            r"\begin{longtable}{r l " + "r r " * 6 + "}",
            (
                r"ID & Subject & \multicolumn{2}{c}{Ptr arith} & "
                r"\multicolumn{2}{c}{Raw decl} & \multicolumn{2}{c}{Raw deref} & "
                r"\multicolumn{2}{c}{Unsafe lines} & \multicolumn{2}{c}{Unsafe casts} & "
                r"\multicolumn{2}{c}{Unsafe calls}\\\hline"
            ),
        ]
    )
    for row in evaluation["rows"]:
        values = [row["subject_id"], row["subject"]]
        for field in SAFETY_FIELDS:
            values.extend([row["paper_safety"][field], _metric_text(row["safety"][field])])
        lines.append(" & ".join(_latex_escape(value) for value in values) + r"\\")
    lines.extend(
        [
            r"\end{longtable}",
            r"\end{landscape}",
            r"\end{document}",
            "",
        ]
    )
    return "\n".join(lines)


def render_summary_figure(aggregate: dict[str, Any], path: Path) -> bool:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
    except ImportError:
        C.atomic_write_text(
            Path(str(path) + ".unavailable.txt"),
            "Summary figure PDF unavailable: reportlab is not installed.\n",
        )
        return False

    paper = aggregate["paper"]
    codeweaver = aggregate["codeweaver"]
    paper_contract_rate = (
        100.0 * paper["fixed_contract_passed"] / paper["testable_subjects"]
    )
    metrics = [
        ("Compilation", 100.0, codeweaver["compilation_rate_percent"]),
        (
            "Fixed-contract pass",
            paper_contract_rate,
            codeweaver["fixed_contract_rate_percent"],
        ),
        (
            "Function coverage",
            paper["unweighted_subject_mean_function_coverage_percent"],
            codeweaver["mean_function_coverage_percent"],
        ),
        (
            "Line coverage",
            paper["unweighted_subject_mean_line_coverage_percent"],
            codeweaver["mean_line_coverage_percent"],
        ),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = landscape(letter)
    figure = canvas.Canvas(str(path), pagesize=(width, height))
    figure.setTitle("Rustine paper reference versus CodeWeaver")
    figure.setFont("Helvetica-Bold", 16)
    figure.drawString(48, height - 42, "Rustine paper reference versus CodeWeaver")
    figure.setFont("Helvetica", 9)
    figure.drawString(
        48,
        height - 58,
        "Same 23 subjects; coverage is the unweighted mean over measured per-subject values.",
    )

    left, bottom, chart_width, chart_height = 72, 105, width - 110, height - 195
    for tick in range(0, 101, 20):
        y = bottom + chart_height * tick / 100
        figure.setStrokeColor(colors.HexColor("#d9d9d9"))
        figure.line(left, y, left + chart_width, y)
        figure.setFillColor(colors.black)
        figure.setFont("Helvetica", 8)
        figure.drawRightString(left - 8, y - 3, f"{tick}%")

    group_width = chart_width / len(metrics)
    bar_width = min(42, group_width * 0.28)
    rustine_color = colors.HexColor("#4c78a8")
    codeweaver_color = colors.HexColor("#f58518")
    for index, (label, rustine_value, codeweaver_value) in enumerate(metrics):
        center = left + group_width * (index + 0.5)
        for x, value, color in (
            (center - bar_width - 3, rustine_value, rustine_color),
            (center + 3, codeweaver_value, codeweaver_color),
        ):
            if value is None:
                figure.setFillColor(colors.black)
                figure.setFont("Helvetica", 8)
                figure.drawCentredString(x + bar_width / 2, bottom + 6, "N/A")
                continue
            bar_height = chart_height * max(0.0, min(100.0, value)) / 100
            figure.setFillColor(color)
            figure.rect(x, bottom, bar_width, bar_height, stroke=0, fill=1)
            figure.setFillColor(colors.black)
            figure.setFont("Helvetica-Bold", 8)
            figure.drawCentredString(
                x + bar_width / 2, bottom + bar_height + 5, f"{value:.1f}%"
            )
        figure.setFont("Helvetica", 8)
        figure.drawCentredString(center, bottom - 18, label)

    legend_y = 55
    for x, color, label in (
        (left, rustine_color, "Rustine published reference"),
        (left + 205, codeweaver_color, "CodeWeaver measured"),
    ):
        figure.setFillColor(color)
        figure.rect(x, legend_y, 12, 12, stroke=0, fill=1)
        figure.setFillColor(colors.black)
        figure.setFont("Helvetica", 9)
        figure.drawString(x + 17, legend_y + 2, label)
    figure.drawRightString(
        width - 38,
        legend_y + 2,
        (
            "Coverage measured rows: "
            f"{codeweaver['function_coverage_measured_rows']}/23"
        ),
    )
    figure.save()
    return True


def write_reports(
    *,
    config: dict[str, Any],
    evaluation: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = aggregate_results(config, evaluation)
    validation = validation_csv_rows(evaluation)
    safety = safety_csv_rows(evaluation)
    C.write_csv(
        output_dir / "validation.csv",
        validation,
        list(validation[0]) if validation else [],
    )
    C.write_csv(
        output_dir / "safety.csv",
        safety,
        list(safety[0]) if safety else [],
    )
    statistics_rows = statistics_csv_rows(aggregate)
    C.write_csv(
        output_dir / "statistics.csv",
        statistics_rows,
        list(statistics_rows[0]),
    )
    summary_rows = [
        {"section": section, "metric": metric, "value": json.dumps(value, sort_keys=True)}
        for section, values in aggregate.items()
        for metric, value in values.items()
    ]
    C.write_csv(output_dir / "summary.csv", summary_rows, ["section", "metric", "value"])

    sections = [
        RD.ReportSection(
            "Abstract",
            _abstract_markdown(aggregate),
        ),
        RD.ReportSection(
            "Aggregate summary",
            _summary_markdown(aggregate),
        ),
        RD.ReportSection(
            "Validation: Rustine paper Table 2 extended with CodeWeaver",
            _validation_markdown(evaluation),
        ),
        RD.ReportSection(
            "Safety aggregate",
            _safety_summary_markdown(aggregate),
        ),
        RD.ReportSection(
            "Safety: Rustine paper Table 3 extended with CodeWeaver",
            _safety_markdown(evaluation),
        ),
        RD.ReportSection(
            "Methodology",
            (
                "Compilation uses `cargo build --all-targets`. Fixed contract binaries are restored "
                "into a temporary target copy before execution. Paper-comparable coverage is "
                "measured with cargo-llvm-cov over the production library graph plus immutable "
                "Rust contract files; production-only values remain in the raw evaluation. "
                "Rustine's reported 74.7% function and 72.2% line values characterize the "
                "benchmark test suites in paper Table 1, not Rustine's translated outputs; they "
                "are preserved exactly but never used as a system outcome. Comparable system "
                "coverage uses unweighted means of the per-subject Table 2 values. CodeWeaver's "
                "count-weighted llvm-cov aggregate is shown only as a separate diagnostic. "
                "Rustine cargo-newmetrics runs with nightly-2025-05-13; contract and "
                "generated tests are excluded through its built-in library-only check. "
                "Pointer arithmetic uses only its rustc-HIR result; a source-pattern count is "
                "retained solely as a raw diagnostic. Assertion values marked `*` are inferred "
                "from the paper denominator only after every disclosed fixed check passes; they "
                "are not runtime counts. Missing capabilities remain explicitly unavailable "
                "rather than becoming zero or success. Token and AI-credit totals include only "
                "values exposed by Copilot usage checkpoints; absent fields remain unavailable."
            ),
        ),
        RD.ReportSection(
            "Comparability caveats",
            (
                "This report pairs CodeWeaver only with the same 23 Rustine subjects. The older "
                "118-project ReCodeAgent matrix uses different subjects and is not directly "
                "comparable. Rustine is a paper-reference single run; CodeWeaver repetitions are "
                "reported separately. xzoom and snudown have no test contract and remain N/A. "
                "The artifact withholds bzip2's augmented 36-assertion module, so the measured "
                "bzip2 status is a deterministic CLI round trip and exact assertion credit is "
                "unavailable. The disclosed grabc driver cannot execute its four X11 assertions "
                "headlessly, and the HT artifact exposes samples rather than its one-assertion "
                "oracle; both use labeled derived checks with unavailable exact assertion credit. "
                "Tulip Indicators fixtures are restored from its pinned upstream commit with "
                "SHA-256 verification. Calibration reproduced qsort's published 100% function "
                "and 92% line translation coverage, but several larger official translations no "
                "longer compile under current dependencies/compiler behavior. Rustine values "
                "therefore remain the published paper reference rather than a selectively repaired "
                "modern rerun. Paper-reference and newly measured values are never blended."
            ),
        ),
        RD.ReportSection(
            "Interpretation",
            _interpretation_markdown(aggregate),
        ),
        RD.ReportSection(
            "Provenance and source",
            (
                f"- Paper: [{config['paper']['title']}]({config['paper']['url']}) "
                f"({config['paper']['arxiv_id']})\n"
                f"- Official artifact: [{RUSTINE_ARTIFACT_REPOSITORY}]"
                f"({RUSTINE_ARTIFACT_REPOSITORY}) at `{config['artifact']['commit']}`\n"
                f"- Protocol: `{json.dumps(evaluation.get('protocol', {}), sort_keys=True)}`\n"
                f"- Preparation provenance: "
                f"`{json.dumps(evaluation.get('preparation_provenance', {}), sort_keys=True)}`\n"
                f"- Evaluation provenance: "
                f"`{json.dumps(evaluation.get('provenance', {}), sort_keys=True)}`"
            ),
        ),
    ]
    title = "CodeWeaver on Rustine's 23-repository C-to-Rust benchmark"
    markdown_path = RD.write_markdown_report(title, sections, output_dir / "comparison.md")
    latex_path = C.atomic_write_text(
        output_dir / "comparison.tex", render_latex(evaluation, aggregate)
    )
    pdf_path = output_dir / "comparison.pdf"
    pdf_written = RD.render_pdf_report(title, sections, pdf_path)
    figure_path = output_dir / "summary_figure.pdf"
    figure_written = render_summary_figure(aggregate, figure_path)
    aggregate_path = C.atomic_write_json(output_dir / "aggregate.json", aggregate)
    report_manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "paper_url": config["paper"]["url"],
        "files": {
            "markdown": markdown_path.name,
            "latex": latex_path.name,
            "pdf": pdf_path.name if pdf_written else None,
            "summary_figure_pdf": figure_path.name if figure_written else None,
            "validation_csv": "validation.csv",
            "safety_csv": "safety.csv",
            "summary_csv": "summary.csv",
            "statistics_csv": "statistics.csv",
            "aggregate_json": aggregate_path.name,
        },
        "pdf_status": C.MEASURED if pdf_written else C.UNAVAILABLE,
        "summary_figure_pdf_status": (
            C.MEASURED if figure_written else C.UNAVAILABLE
        ),
        "provenance": C.collect_provenance(),
    }
    report_manifest["sha256"] = {
        name: C.file_sha256(path)
        for name, path in {
            "markdown": markdown_path,
            "latex": latex_path,
            "validation_csv": output_dir / "validation.csv",
            "safety_csv": output_dir / "safety.csv",
            "summary_csv": output_dir / "summary.csv",
            "statistics_csv": output_dir / "statistics.csv",
            "aggregate_json": aggregate_path,
            **({"pdf": pdf_path} if pdf_written else {}),
            **({"summary_figure_pdf": figure_path} if figure_written else {}),
        }.items()
    }
    C.atomic_write_json(output_dir / "report_manifest.json", report_manifest)
    return report_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(C.DEFAULT_CONFIG))
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_subject_config(args.config)
    evaluation = C.read_json(args.evaluation)
    manifest = write_reports(
        config=config, evaluation=evaluation, output_dir=Path(args.out)
    )
    print(f"wrote Rustine comparison reports under {Path(args.out).resolve()}")
    if manifest["pdf_status"] == C.UNAVAILABLE:
        print("PDF unavailable: reportlab is not installed; Markdown/CSV/LaTeX were written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
