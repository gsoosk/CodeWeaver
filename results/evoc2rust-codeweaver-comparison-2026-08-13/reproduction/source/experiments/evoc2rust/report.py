"""Render a publication-ready EvoC2Rust versus CodeWeaver report."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from experiments.evoc2rust import common as C
from experiments.evoc2rust.config import load_config
from experiments.recodeagent import render as RD


def _measured_true(metric: dict[str, Any]) -> bool:
    return metric.get("status") == C.MEASURED and metric.get("value") is True


def _numeric(metric: dict[str, Any]) -> float | None:
    value = metric.get("value")
    if (
        metric.get("status") == C.MEASURED
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return float(value)
    return None


def repetition_metrics(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    integrations = {
        int(row["repetition"]): row for row in evaluation.get("integration", [])
    }
    repetitions = int(evaluation["protocol"]["evaluated_repetitions"])
    for repetition in range(repetitions):
        rows = [
            row
            for row in evaluation["rows"]
            if int(row["repetition"]) == repetition
        ]
        compiling_modules = sum(
            int(row["module_count"])
            for row in rows
            if _measured_true(row["compilation"])
        )
        test_expected = sum(int(row["fixed_tests"]["expected"]) for row in rows)
        test_passed = sum(int(row["fixed_tests"]["passed"]) for row in rows)
        safety_values = [
            row["safety"]["value"]
            for row in rows
            if row["safety"].get("status") == C.MEASURED
            and isinstance(row["safety"].get("value"), dict)
        ]
        total_lines = sum(int(value["total_lines"]) for value in safety_values)
        safe_lines = sum(int(value["safe_lines"]) for value in safety_values)
        integration = integrations.get(repetition)
        output.append(
            {
                "repetition": repetition,
                "terminal_runs": sum(
                    _measured_true(row["terminal_run"]) for row in rows
                ),
                "integrity_passed": sum(
                    _measured_true(row["contract_integrity"]) for row in rows
                ),
                "compiling_groups": sum(
                    _measured_true(row["compilation"]) for row in rows
                ),
                "groups": len(rows),
                "compiling_modules": compiling_modules,
                "module_denominator": 19,
                "fill_compilation_percent": 100.0
                * compiling_modules
                / 19,
                "fixed_contract_groups_passed": sum(
                    _measured_true(row["fixed_contract_tests"]) for row in rows
                ),
                "tests_passed": test_passed,
                "test_denominator": test_expected,
                "test_rate_percent": (
                    100.0 * test_passed / test_expected
                    if test_expected
                    else None
                ),
                "safe_lines": safe_lines,
                "total_rust_lines": total_lines,
                "safe_rate_percent": (
                    100.0 * safe_lines / total_lines if total_lines else None
                ),
                "incremental_compilation_percent": (
                    integration["incremental_compilation_percent"]
                    if integration
                    else None
                ),
                "incrementally_accepted_modules": (
                    integration["accepted_module_count"] if integration else None
                ),
                "elapsed_seconds": sum(
                    value
                    for value in (
                        _numeric(row["elapsed_seconds"]) for row in rows
                    )
                    if value is not None
                ),
                "output_tokens": sum(
                    int(value)
                    for value in (
                        _numeric(row["output_tokens"]) for row in rows
                    )
                    if value is not None
                ),
                "nano_aiu": sum(
                    int(value)
                    for value in (
                        _numeric(row["nano_aiu"]) for row in rows
                    )
                    if value is not None
                ),
                "premium_requests": sum(
                    int(value)
                    for value in (
                        _numeric(row["premium_requests"]) for row in rows
                    )
                    if value is not None
                ),
            }
        )
    return output


def _distribution(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [
        float(row[field])
        for row in rows
        if isinstance(row.get(field), (int, float))
    ]
    return {
        "values": values,
        "mean": statistics.mean(values) if values else None,
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def aggregate_results(evaluation: dict[str, Any]) -> dict[str, Any]:
    repetitions = repetition_metrics(evaluation)
    fields = (
        "incremental_compilation_percent",
        "fill_compilation_percent",
        "test_rate_percent",
        "safe_rate_percent",
    )
    return {
        "schema_version": 1,
        "runs_expected": 45,
        "runs_observed": len(evaluation["rows"]),
        "terminal_runs": sum(
            _measured_true(row["terminal_run"]) for row in evaluation["rows"]
        ),
        "integrity_passed": sum(
            _measured_true(row["contract_integrity"])
            for row in evaluation["rows"]
        ),
        "repetitions": repetitions,
        "distributions": {
            field: _distribution(repetitions, field) for field in fields
        },
        "cost": {
            field: sum(int(row[field]) for row in repetitions)
            for field in ("output_tokens", "nano_aiu", "premium_requests")
        },
        "elapsed_seconds_sum": sum(
            float(row["elapsed_seconds"]) for row in repetitions
        ),
    }


def _percent(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.2f}%"


def _mean_sd(distribution: dict[str, Any]) -> str:
    if distribution["mean"] is None:
        return "N/A"
    if distribution["sample_sd"] is None:
        return _percent(distribution["mean"])
    return (
        f"{distribution['mean']:.2f}% +/- "
        f"{distribution['sample_sd']:.2f} pp"
    )


def table4_rows(
    config: dict[str, Any],
    repetitions: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [dict(row, provenance="paper") for row in config["paper"]["table4_rows"]]
    for row in repetitions:
        rows.append(
            {
                "dataset": "Vivo-Bench (pinned revision)",
                "category": "llm",
                "model": config["protocol"]["model"],
                "method": f"CodeWeaver repetition {row['repetition'] + 1}",
                "incremental_compilation_percent": row[
                    "incremental_compilation_percent"
                ],
                "acceptance_precision_percent": None,
                "acceptance_recall_percent": None,
                "safe_rate_percent": row["safe_rate_percent"],
                "provenance": "measured",
            }
        )
    rows.append(
        {
            "dataset": "Vivo-Bench (pinned revision)",
            "category": "llm",
            "model": config["protocol"]["model"],
            "method": "CodeWeaver mean",
            "incremental_compilation_percent": aggregate["distributions"][
                "incremental_compilation_percent"
            ]["mean"],
            "acceptance_precision_percent": None,
            "acceptance_recall_percent": None,
            "safe_rate_percent": aggregate["distributions"][
                "safe_rate_percent"
            ]["mean"],
            "provenance": "derived from measured repetitions",
        }
    )
    return rows


def table5_rows(
    config: dict[str, Any],
    repetitions: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for key, model in (
        ("deepseek_v3", "DeepSeek-V3"),
        ("qwen3_32b", "Qwen3-32B"),
    ):
        values = config["paper"]["vivo_table5"][key]
        rows.append(
            {
                "dataset": "Vivo-Bench",
                "model": model,
                "project": "19 projects",
                **values,
                "provenance": "paper",
            }
        )
    rows.extend(
        {
            "dataset": "C2R-Bench",
            **row,
            "provenance": "paper",
        }
        for row in config["paper"]["table5_c2r_rows"]
    )
    for row in repetitions:
        rows.append(
            {
                "dataset": "Vivo-Bench (pinned revision)",
                "model": config["protocol"]["model"],
                "project": f"CodeWeaver repetition {row['repetition'] + 1}",
                "fill_compilation_percent": row["fill_compilation_percent"],
                "test_rate_percent": row["test_rate_percent"],
                "provenance": "measured",
            }
        )
    rows.append(
        {
            "dataset": "Vivo-Bench (pinned revision)",
            "model": config["protocol"]["model"],
            "project": "CodeWeaver mean",
            "fill_compilation_percent": aggregate["distributions"][
                "fill_compilation_percent"
            ]["mean"],
            "test_rate_percent": aggregate["distributions"][
                "test_rate_percent"
            ]["mean"],
            "provenance": "derived from measured repetitions",
        }
    )
    return rows


def availability_rows() -> list[dict[str, Any]]:
    unavailable_c2r = (
        "C2R-Bench sources, tests, and corrected Rust references are unreleased"
    )
    return [
        {
            "rq": "RQ1",
            "surface": "Vivo-Bench ICompRate",
            "status": "measured",
            "reason": "cumulative replacement with C fallback",
        },
        {
            "rq": "RQ1",
            "surface": "Vivo-Bench AccRate-P/R",
            "status": "unavailable",
            "reason": "human-corrected Rust references are unreleased",
        },
        {
            "rq": "RQ1",
            "surface": "Vivo-Bench SafeRate",
            "status": "measured",
            "reason": "candidate production Rust only",
        },
        {
            "rq": "RQ2",
            "surface": "Vivo-Bench FCompRate/TestRate",
            "status": "measured",
            "reason": "19 modules and 125 active pinned tests",
        },
        {
            "rq": "RQ1/RQ2",
            "surface": "C2R-Bench",
            "status": "unavailable",
            "reason": unavailable_c2r,
        },
        {
            "rq": "RQ3",
            "surface": "EvoC2Rust ablations",
            "status": "reference_only",
            "reason": (
                "implementation, feature mappings, repairs, and C2R-Bench "
                "are unreleased"
            ),
        },
        {
            "rq": "RQ4",
            "surface": "scale and time figures",
            "status": "reference_only",
            "reason": (
                "requires unreleased C2R projects and EvoC2Rust runtime traces"
            ),
        },
    ]


def _table4_markdown(rows: list[dict[str, Any]]) -> str:
    selected = [
        row
        for row in rows
        if row["dataset"].startswith("Vivo-Bench")
        and (
            row["method"] == "EvoC2Rust"
            or row["method"].startswith("CodeWeaver")
        )
    ]
    return RD.markdown_table(
        ["Dataset", "Model", "Method", "ICompRate", "AccRate-P", "AccRate-R", "SafeRate"],
        [
            [
                row["dataset"],
                row["model"],
                row["method"],
                _percent(row["incremental_compilation_percent"]),
                _percent(row["acceptance_precision_percent"]),
                _percent(row["acceptance_recall_percent"]),
                _percent(row["safe_rate_percent"]),
            ]
            for row in selected
        ],
    )


def _table5_markdown(rows: list[dict[str, Any]]) -> str:
    selected = [
        row
        for row in rows
        if row["dataset"].startswith("Vivo-Bench")
    ]
    return RD.markdown_table(
        ["Dataset", "Model", "System/run", "FCompRate", "TestRate"],
        [
            [
                row["dataset"],
                row["model"],
                row["project"],
                _percent(row["fill_compilation_percent"]),
                _percent(row["test_rate_percent"]),
            ]
            for row in selected
        ],
    )


def _repetition_markdown(rows: list[dict[str, Any]]) -> str:
    return RD.markdown_table(
        [
            "Rep",
            "Terminal",
            "Integrity",
            "IComp",
            "FComp",
            "Tests",
            "TestRate",
            "SafeRate",
            "Elapsed",
        ],
        [
            [
                row["repetition"] + 1,
                f"{row['terminal_runs']}/15",
                f"{row['integrity_passed']}/15",
                (
                    f"{row['incrementally_accepted_modules']}/19 "
                    f"({_percent(row['incremental_compilation_percent'])})"
                ),
                (
                    f"{row['compiling_modules']}/19 "
                    f"({_percent(row['fill_compilation_percent'])})"
                ),
                f"{row['tests_passed']}/{row['test_denominator']}",
                _percent(row["test_rate_percent"]),
                _percent(row["safe_rate_percent"]),
                f"{row['elapsed_seconds'] / 3600:.2f} h",
            ]
            for row in rows
        ],
    )


def _availability_markdown(rows: list[dict[str, Any]]) -> str:
    return RD.markdown_table(
        ["RQ", "Surface", "Status", "Reason"],
        [[row["rq"], row["surface"], row["status"], row["reason"]] for row in rows],
    )


def _abstract(
    config: dict[str, Any], aggregate: dict[str, Any]
) -> str:
    distributions = aggregate["distributions"]
    return (
        "We reproduce the publicly executable portion of EvoC2Rust on the "
        "paper's disclosed Vivo-Bench repository and compare three independent "
        f"CodeWeaver {config['protocol']['model']} runs. Across repetitions, "
        f"mean ICompRate is {_mean_sd(distributions['incremental_compilation_percent'])}, "
        f"mean FCompRate is {_mean_sd(distributions['fill_compilation_percent'])}, "
        f"mean TestRate is {_mean_sd(distributions['test_rate_percent'])}, and "
        f"mean SafeRate is {_mean_sd(distributions['safe_rate_percent'])}. "
        "AccRate-P/R, the six-project C2R-Bench experiment, ablations, and "
        "scale experiments cannot be independently rerun because their required "
        "artifacts are not public; published values remain reference-only."
    )


def _methodology(config: dict[str, Any]) -> str:
    return (
        "The benchmark is pinned at AtomGit commit "
        f"`{config['artifact']['commit']}`. C2Rust 0.22.1 derives only ABI "
        "signatures and immutable Rust test contracts; all generated production "
        "bodies are stripped before model access. The contracts were calibrated "
        "against both the original C and full C2Rust implementations (125/125 "
        "active functions), while stripped scaffolds pass 0/125. Each fixed test "
        "runs in a separate process. FCompRate credits every module in a group "
        "only when the independently restored crate builds. ICompRate follows "
        "the paper's incremental strategy: groups are inserted in frozen order "
        "into a cumulative project, and failed groups fall back to original C. "
        "SafeRate is the line-weighted share of nonblank production Rust lines "
        "outside unsafe functions or blocks. Three repetitions use GPT-5.6 Sol "
        "at maximum effort, five repair iterations, three parity rounds, and a "
        "5,000-second agent timeout."
    )


def _threats(config: dict[str, Any]) -> str:
    stats = config["paper"]["dataset_statistics"]
    return (
        f"The paper reports {stats['vivo_bench_paper_test_cases']} Vivo-Bench "
        f"test cases, while the pinned public revision enables "
        f"{stats['vivo_bench_pinned_active_test_functions']} test functions and "
        f"disables {stats['vivo_bench_pinned_disabled_test_functions']} additional "
        "`rb-tree` functions. CodeWeaver therefore uses a 125-test denominator "
        "and does not relabel it as the paper's 113-test denominator. Models also "
        "differ (GPT-5.6 Sol versus DeepSeek-V3/Qwen3-32B), and the CodeWeaver "
        "architecture is not an EvoC2Rust implementation. SafeRate is comparable "
        "in intent but the paper does not release its exact analyzer. Published "
        "reference values and new measurements are never pooled."
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
    return "".join(replacements.get(char, char) for char in str(value))


def render_latex(
    config: dict[str, Any],
    aggregate: dict[str, Any],
    table4: list[dict[str, Any]],
    table5: list[dict[str, Any]],
) -> str:
    repetitions = aggregate["repetitions"]
    lines = [
        r"\documentclass{article}",
        r"\usepackage[margin=0.7in]{geometry}",
        r"\usepackage{booktabs,longtable,graphicx}",
        r"\title{Leakage-Safe Reproduction of EvoC2Rust with CodeWeaver}",
        r"\author{CodeWeaver Experimental Artifact}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{abstract}",
        _latex_escape(_abstract(config, aggregate)),
        r"\end{abstract}",
        r"\section{Method}",
        _latex_escape(_methodology(config)),
        r"\section{Results}",
        r"\begin{table}[h]\centering",
        r"\caption{EvoC2Rust Table 4 extension on Vivo-Bench.}",
        r"\begin{tabular}{llrrr}\toprule",
        r"Model & Method & IComp & Acc-P/R & Safe\\\midrule",
    ]
    for row in table4:
        if not row["dataset"].startswith("Vivo-Bench") or (
            row["method"] != "EvoC2Rust"
            and not row["method"].startswith("CodeWeaver")
        ):
            continue
        values = [
            row["model"],
            row["method"],
            _percent(row["incremental_compilation_percent"]),
            (
                f"{_percent(row['acceptance_precision_percent'])}/"
                f"{_percent(row['acceptance_recall_percent'])}"
            ),
            _percent(row["safe_rate_percent"]),
        ]
        lines.append(" & ".join(_latex_escape(value) for value in values) + r"\\")
    lines.extend(
        [
            r"\bottomrule\end{tabular}\end{table}",
            r"\begin{table}[h]\centering",
            r"\caption{EvoC2Rust Table 5 extension on Vivo-Bench.}",
            r"\begin{tabular}{llrr}\toprule",
            r"Model & System/run & FComp & Test\\\midrule",
        ]
    )
    for row in table5:
        if not row["dataset"].startswith("Vivo-Bench"):
            continue
        values = [
            row["model"],
            row["project"],
            _percent(row["fill_compilation_percent"]),
            _percent(row["test_rate_percent"]),
        ]
        lines.append(" & ".join(_latex_escape(value) for value in values) + r"\\")
    lines.extend(
        [
            r"\bottomrule\end{tabular}\end{table}",
            r"\section{Repetitions}",
            r"\begin{tabular}{rrrrr}\toprule",
            r"Rep & IComp & FComp & Test & Safe\\\midrule",
        ]
    )
    for row in repetitions:
        values = [
            row["repetition"] + 1,
            _percent(row["incremental_compilation_percent"]),
            _percent(row["fill_compilation_percent"]),
            _percent(row["test_rate_percent"]),
            _percent(row["safe_rate_percent"]),
        ]
        lines.append(" & ".join(_latex_escape(value) for value in values) + r"\\")
    lines.extend(
        [
            r"\bottomrule\end{tabular}",
            r"\section{Threats to Validity}",
            _latex_escape(_threats(config)),
            r"\end{document}",
            "",
        ]
    )
    return "\n".join(lines)


def render_summary_figure(
    config: dict[str, Any], aggregate: dict[str, Any], path: Path
) -> bool:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
    except ImportError:
        return False
    deepseek = {
        "IComp": config["paper"]["vivo_table4"]["deepseek_v3"][
            "incremental_compilation_percent"
        ],
        "FComp": config["paper"]["vivo_table5"]["deepseek_v3"][
            "fill_compilation_percent"
        ],
        "Test": config["paper"]["vivo_table5"]["deepseek_v3"][
            "test_rate_percent"
        ],
        "Safe": config["paper"]["vivo_table4"]["deepseek_v3"][
            "safe_rate_percent"
        ],
    }
    qwen = {
        "IComp": config["paper"]["vivo_table4"]["qwen3_32b"][
            "incremental_compilation_percent"
        ],
        "FComp": config["paper"]["vivo_table5"]["qwen3_32b"][
            "fill_compilation_percent"
        ],
        "Test": config["paper"]["vivo_table5"]["qwen3_32b"][
            "test_rate_percent"
        ],
        "Safe": config["paper"]["vivo_table4"]["qwen3_32b"][
            "safe_rate_percent"
        ],
    }
    codeweaver = {
        "IComp": aggregate["distributions"][
            "incremental_compilation_percent"
        ]["mean"],
        "FComp": aggregate["distributions"]["fill_compilation_percent"][
            "mean"
        ],
        "Test": aggregate["distributions"]["test_rate_percent"]["mean"],
        "Safe": aggregate["distributions"]["safe_rate_percent"]["mean"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = landscape(letter)
    figure = canvas.Canvas(str(path), pagesize=(width, height))
    figure.setTitle("EvoC2Rust published references and CodeWeaver")
    figure.setFont("Helvetica-Bold", 16)
    figure.drawString(
        42, height - 40, "Vivo-Bench: published references and CodeWeaver"
    )
    figure.setFont("Helvetica", 8)
    figure.drawString(
        42,
        height - 56,
        "Paper models differ; CodeWeaver values are means of three measured GPT-5.6 Sol repetitions.",
    )
    left, bottom = 68, 105
    chart_width, chart_height = width - 105, height - 190
    for tick in range(0, 101, 20):
        y = bottom + chart_height * tick / 100
        figure.setStrokeColor(colors.HexColor("#dddddd"))
        figure.line(left, y, left + chart_width, y)
        figure.setFillColor(colors.black)
        figure.drawRightString(left - 7, y - 3, f"{tick}%")
    metrics = list(deepseek)
    colors_by_system = (
        colors.HexColor("#4c78a8"),
        colors.HexColor("#72b7b2"),
        colors.HexColor("#f58518"),
    )
    series = (("EvoC2Rust DeepSeek-V3", deepseek), ("EvoC2Rust Qwen3-32B", qwen), ("CodeWeaver mean", codeweaver))
    group_width = chart_width / len(metrics)
    bar_width = min(32, group_width / 4)
    for index, metric in enumerate(metrics):
        center = left + group_width * (index + 0.5)
        for offset, ((_, values), color) in enumerate(
            zip(series, colors_by_system, strict=True)
        ):
            value = values[metric]
            x = center + (offset - 1.5) * bar_width
            bar_height = chart_height * float(value) / 100
            figure.setFillColor(color)
            figure.rect(x, bottom, bar_width - 2, bar_height, stroke=0, fill=1)
            figure.setFillColor(colors.black)
            figure.setFont("Helvetica", 7)
            figure.drawCentredString(
                x + (bar_width - 2) / 2,
                bottom + bar_height + 4,
                f"{float(value):.1f}",
            )
        figure.setFont("Helvetica-Bold", 9)
        figure.drawCentredString(center, bottom - 18, metric)
    for index, ((label, _), color) in enumerate(
        zip(series, colors_by_system, strict=True)
    ):
        x = left + index * 205
        figure.setFillColor(color)
        figure.rect(x, 50, 12, 12, stroke=0, fill=1)
        figure.setFillColor(colors.black)
        figure.setFont("Helvetica", 8)
        figure.drawString(x + 17, 52, label)
    figure.save()
    return True


def render_repetition_figure(
    aggregate: dict[str, Any], path: Path
) -> bool:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
    except ImportError:
        return False
    rows = aggregate["repetitions"]
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = landscape(letter)
    figure = canvas.Canvas(str(path), pagesize=(width, height))
    figure.setTitle("CodeWeaver repetition results")
    figure.setFont("Helvetica-Bold", 16)
    figure.drawString(42, height - 40, "CodeWeaver repetition stability")
    left, bottom = 68, 95
    chart_width, chart_height = width - 110, height - 170
    for tick in range(0, 101, 20):
        y = bottom + chart_height * tick / 100
        figure.setStrokeColor(colors.HexColor("#dddddd"))
        figure.line(left, y, left + chart_width, y)
        figure.setFillColor(colors.black)
        figure.drawRightString(left - 7, y - 3, f"{tick}%")
    series = (
        ("IComp", "incremental_compilation_percent", colors.HexColor("#4c78a8")),
        ("FComp", "fill_compilation_percent", colors.HexColor("#f58518")),
        ("Test", "test_rate_percent", colors.HexColor("#54a24b")),
        ("Safe", "safe_rate_percent", colors.HexColor("#b279a2")),
    )
    for series_index, (label, field, color) in enumerate(series):
        points = []
        for index, row in enumerate(rows):
            x = left + chart_width * (index + 1) / (len(rows) + 1)
            y = bottom + chart_height * float(row[field]) / 100
            points.append((x, y))
        figure.setStrokeColor(color)
        figure.setLineWidth(2)
        for first, second in zip(points, points[1:]):
            figure.line(*first, *second)
        figure.setFillColor(color)
        for x, y in points:
            figure.circle(x, y, 4, stroke=0, fill=1)
        x = left + series_index * 130
        figure.rect(x, 45, 12, 12, stroke=0, fill=1)
        figure.setFillColor(colors.black)
        figure.drawString(x + 17, 47, label)
    for index in range(len(rows)):
        x = left + chart_width * (index + 1) / (len(rows) + 1)
        figure.drawCentredString(x, bottom - 18, f"Repetition {index + 1}")
    figure.save()
    return True


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    return C.write_csv(path, rows, list(rows[0]) if rows else [])


def write_reports(
    *,
    config: dict[str, Any],
    evaluation: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = aggregate_results(evaluation)
    repetitions = aggregate["repetitions"]
    table4 = table4_rows(config, repetitions, aggregate)
    table5 = table5_rows(config, repetitions, aggregate)
    availability = availability_rows()
    table6 = [
        {**row, "provenance": "paper reference"}
        for row in config["paper"]["table6_rows"]
    ]
    csv_outputs = {
        "repetition_metrics.csv": repetitions,
        "table4_extended.csv": table4,
        "table5_extended.csv": table5,
        "table6_reference.csv": table6,
        "availability.csv": availability,
        "module_results.csv": [
            {
                "repetition": row["repetition"],
                "subject_id": row["subject_id"],
                "subject": row["subject"],
                "modules": ",".join(row["modules"]),
                "module_count": row["module_count"],
                "pipeline_status": row["pipeline_status"],
                "compilation": row["compilation"].get("value"),
                "compilation_status": row["compilation"].get("status"),
                "tests_passed": row["fixed_tests"]["passed"],
                "tests_expected": row["fixed_tests"]["expected"],
                "safe_rate_percent": (
                    row["safety"].get("value", {}).get("safe_rate_percent")
                    if isinstance(row["safety"].get("value"), dict)
                    else None
                ),
            }
            for row in evaluation["rows"]
        ],
        "fixed_tests.csv": [
            {
                "repetition": row["repetition"],
                "subject_id": row["subject_id"],
                "subject": row["subject"],
                "test": test["name"],
                "passed": test["passed"],
                "returncode": test["returncode"],
                "timed_out": test["timed_out"],
            }
            for row in evaluation["rows"]
            for test in row.get("fixed_test_results", [])
        ],
        "integration_steps.csv": [
            {
                "repetition": integration["repetition"],
                **step,
                "modules": ",".join(step["modules"]),
            }
            for integration in evaluation.get("integration", [])
            for step in integration["steps"]
        ],
    }
    for name, rows in csv_outputs.items():
        _write_csv(output_dir / name, rows)

    sections = [
        RD.ReportSection("Abstract", _abstract(config, aggregate)),
        RD.ReportSection(
            "Experimental coverage and artifact availability",
            _availability_markdown(availability),
        ),
        RD.ReportSection(
            "Table 4 extension: project translation",
            _table4_markdown(table4),
        ),
        RD.ReportSection(
            "Table 5 extension: module translation",
            _table5_markdown(table5),
        ),
        RD.ReportSection(
            "Exact CodeWeaver repetitions", _repetition_markdown(repetitions)
        ),
        RD.ReportSection("Methodology", _methodology(config)),
        RD.ReportSection("Threats to validity", _threats(config)),
        RD.ReportSection(
            "Reference-only experiments",
            (
                "The complete published Table 4, C2R-Bench portion of Table 5, "
                "and Table 6 ablation values are preserved in the companion CSV "
                "files. They are not presented as reruns. RQ4's scale and timing "
                "figures cannot be regenerated without the six unreleased "
                "industrial projects and original execution traces."
            ),
        ),
        RD.ReportSection(
            "Provenance",
            (
                f"- Paper DOI: `{config['paper']['doi']}`\n"
                f"- Paper version: `{config['paper']['arxiv']}`\n"
                f"- Public benchmark: `{config['artifact']['repository']}` at "
                f"`{config['artifact']['commit']}`\n"
                f"- Protocol: `{json.dumps(evaluation['protocol'], sort_keys=True)}`\n"
                f"- Evaluation provenance: "
                f"`{json.dumps(evaluation.get('provenance', {}), sort_keys=True)}`"
            ),
        ),
    ]
    title = "Leakage-Safe Reproduction of EvoC2Rust with CodeWeaver"
    markdown = RD.write_markdown_report(
        title, sections, output_dir / "comparison.md"
    )
    latex = C.atomic_write_text(
        output_dir / "comparison.tex",
        render_latex(config, aggregate, table4, table5),
    )
    pdf = output_dir / "comparison.pdf"
    pdf_written = RD.render_pdf_report(title, sections, pdf)
    summary_figure = output_dir / "summary_figure.pdf"
    summary_written = render_summary_figure(
        config, aggregate, summary_figure
    )
    repetition_figure = output_dir / "repetitions_figure.pdf"
    repetition_written = render_repetition_figure(
        aggregate, repetition_figure
    )
    aggregate_path = C.atomic_write_json(
        output_dir / "aggregate.json", aggregate
    )
    files = {
        "comparison.md": markdown,
        "comparison.tex": latex,
        "aggregate.json": aggregate_path,
        **{
            name: output_dir / name
            for name in csv_outputs
        },
        **({"comparison.pdf": pdf} if pdf_written else {}),
        **(
            {"summary_figure.pdf": summary_figure}
            if summary_written
            else {}
        ),
        **(
            {"repetitions_figure.pdf": repetition_figure}
            if repetition_written
            else {}
        ),
    }
    manifest = {
        "schema_version": 1,
        "generated_at": C.utcnow_iso(),
        "paper_doi": config["paper"]["doi"],
        "files": sorted(files),
        "pdf_status": C.MEASURED if pdf_written else C.UNAVAILABLE,
        "summary_figure_pdf_status": (
            C.MEASURED if summary_written else C.UNAVAILABLE
        ),
        "repetitions_figure_pdf_status": (
            C.MEASURED if repetition_written else C.UNAVAILABLE
        ),
        "sha256": {
            name: C.file_sha256(path) for name, path in files.items()
        },
        "provenance": C.collect_provenance(),
    }
    C.atomic_write_json(output_dir / "report_manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(C.DEFAULT_CONFIG))
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = write_reports(
        config=load_config(args.config),
        evaluation=C.read_json(args.evaluation),
        output_dir=Path(args.out).resolve(),
    )
    print(f"wrote EvoC2Rust comparison reports under {Path(args.out).resolve()}")
    return 0 if manifest["pdf_status"] == C.MEASURED else 1


if __name__ == "__main__":
    raise SystemExit(main())
