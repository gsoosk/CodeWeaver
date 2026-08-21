"""Generate five separate paper-style result artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import shutil
import statistics
import sys
from pathlib import Path
from typing import Any

from . import common as C
from .config import (
    ALPHATRANS_REFERENCE,
    CRUST_TABLE4,
    PROTOCOL,
    REPOTRANSBENCH_ORACLE_AUDIT,
    REPOTRANSBENCH_PYTHON_JAVA,
    REPOTRANSBENCH_SUBJECTS,
    REPOTRANSBENCH_V1_RESULTS,
    RUSTREPOTRANS_SUBJECTS,
    RUSTREPOTRANS_RQ1_REFERENCE,
    SACTOR_REFERENCE,
    SACTOR_SUBJECTS,
    UPSTREAM_COMMITS,
    UPSTREAM_REPOSITORIES,
)
from .paper_reference_data import PAPER_SURFACES, REFERENCE_TABLES

RESULT_NAMES = {
    "crust": "crust-bench-codeweaver-comparison-2026-08-14",
    "alphatrans": "alphatrans-codeweaver-comparison-2026-08-14",
    "sactor": "sactor-codeweaver-comparison-2026-08-14",
    "repotransbench": "repotransbench-codeweaver-comparison-2026-08-14",
    "rustrepotrans": "rustrepotrans-codeweaver-comparison-2026-08-14",
    "citations": "crust-citation-complete-codeweaver-2026-08-20",
}

PAPER_METADATA = {
    "crust": {
        "title": "CRUST-Bench",
        "paper_url": "https://arxiv.org/abs/2504.15254",
        "paper_id": "arXiv:2504.15254",
    },
    "alphatrans": {
        "title": "AlphaTrans",
        "paper_url": "https://arxiv.org/abs/2410.24117",
        "paper_id": "arXiv:2410.24117 / DOI 10.1145/3729379",
    },
    "sactor": {
        "title": "SACTOR",
        "paper_url": "https://arxiv.org/abs/2503.12511",
        "paper_id": "arXiv:2503.12511",
    },
    "repotransbench": {
        "title": "RepoTransBench",
        "paper_url": "https://arxiv.org/abs/2412.17744",
        "paper_id": "arXiv:2412.17744",
    },
    "rustrepotrans": {
        "title": "RustRepoTrans",
        "paper_url": "https://arxiv.org/abs/2411.13990",
        "paper_id": "arXiv:2411.13990",
    },
    "citations": {
        "title": "the complete CRUST-Bench citation corpus",
        "paper_url": "https://arxiv.org/abs/2504.15254",
        "paper_id": "30-record citation census as of 2026-08-20",
    },
}


def _load_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    C.atomic_write_text(
        path,
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
    )


def _bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _number(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    return int(float(value)) if value not in (None, "") else 0


def _percent(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}%"


def _mean_sd(values: list[float]) -> tuple[float, float, float]:
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    multiplier = 4.303 if len(values) == 3 else 1.96
    ci = multiplier * sd / math.sqrt(len(values)) if len(values) > 1 else 0.0
    return mean, sd, ci


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return fields


def _tree_identity(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest(), len(files)


def _write_paper_reference_bundle(root: Path, key: str) -> list[dict[str, str]]:
    surfaces = PAPER_SURFACES[key]
    C.write_csv(
        root / "data" / "paper_surface_inventory.csv",
        surfaces,
        ["surface", "caption", "denominator", "metrics", "artifact_status"],
    )
    for filename, rows in REFERENCE_TABLES[key].items():
        C.write_csv(
            root / "data" / "paper-reference" / filename,
            rows,
            _fieldnames(rows),
        )
    return surfaces


TELEMETRY_STATUS_FIELDS = {
    "elapsed_seconds": "elapsed_seconds_status",
    "total_input_tokens": "input_tokens_status",
    "total_output_tokens": "output_tokens_status",
    "total_nano_aiu": "nano_aiu_status",
}


def _measured_numbers(rows: list[dict[str, Any]], field: str) -> list[float]:
    status_field = TELEMETRY_STATUS_FIELDS.get(field, f"{field}_status")
    return [
        float(row[field])
        for row in rows
        if row.get(field) not in ("", None)
        and row.get(status_field, "measured") == "measured"
    ]


def _availability(measured: int, total: int) -> str:
    if measured == total:
        return "measured"
    if measured:
        return "partial"
    return "unavailable"


def _telemetry_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    repetitions = sorted({int(row["repetition"]) for row in rows})
    selections = [
        (f"repetition_{repetition + 1}", [
            row for row in rows if int(row["repetition"]) == repetition
        ])
        for repetition in repetitions
    ]
    selections.append(("all_measured_cells", rows))
    for label, selected in selections:
        elapsed = _measured_numbers(selected, "elapsed_seconds")
        output_tokens = _measured_numbers(selected, "total_output_tokens")
        nano_aiu = _measured_numbers(selected, "total_nano_aiu")
        input_tokens = _measured_numbers(selected, "total_input_tokens")
        premium_requests = [
            _number(row, "total_premium_requests")
            for row in selected
            if row.get("total_premium_requests") not in ("", None)
        ]
        assistant_turns = [
            _number(row, "total_assistant_turns")
            for row in selected
            if row.get("total_assistant_turns") not in ("", None)
        ]
        tool_invocations = [
            _number(row, "total_tool_invocations")
            for row in selected
            if row.get("total_tool_invocations") not in ("", None)
            and row.get("tool_invocations_precision") == "exact"
        ]
        summaries.append(
            {
                "scope": label,
                "cells": len(selected),
                "elapsed_hours": sum(elapsed) / 3600 if elapsed else None,
                "elapsed_measured_cells": len(elapsed),
                "elapsed_status": _availability(len(elapsed), len(selected)),
                "mean_elapsed_minutes": (
                    statistics.mean(elapsed) / 60 if elapsed else None
                ),
                "assistant_turns": (
                    sum(assistant_turns) if assistant_turns else None
                ),
                "assistant_turn_measured_cells": len(assistant_turns),
                "assistant_turn_status": _availability(
                    len(assistant_turns), len(selected)
                ),
                "tool_invocations": (
                    sum(tool_invocations) if tool_invocations else None
                ),
                "tool_invocation_exact_cells": len(tool_invocations),
                "tool_invocation_status": _availability(
                    len(tool_invocations), len(selected)
                ),
                "premium_requests": (
                    sum(premium_requests) if premium_requests else None
                ),
                "premium_request_measured_cells": len(premium_requests),
                "premium_request_status": _availability(
                    len(premium_requests), len(selected)
                ),
                "aiu": sum(nano_aiu) / 1_000_000_000 if nano_aiu else None,
                "aiu_measured_cells": len(nano_aiu),
                "aiu_status": _availability(len(nano_aiu), len(selected)),
                "output_tokens": int(sum(output_tokens)) if output_tokens else None,
                "output_token_measured_cells": len(output_tokens),
                "output_token_status": _availability(
                    len(output_tokens), len(selected)
                ),
                "input_tokens": int(sum(input_tokens)) if input_tokens else None,
                "input_token_status": (
                    _availability(len(input_tokens), len(selected))
                ),
                "input_token_measured_cells": len(input_tokens),
            }
        )
    return summaries


def _coverage_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    fields = (
        "coverage_before",
        "coverage_after",
        "standardized_coverage_before",
        "standardized_coverage_after",
    )
    for repetition in sorted({int(row["repetition"]) for row in rows}):
        selected = [
            row for row in rows if int(row["repetition"]) == repetition
        ]
        for field in fields:
            values = _measured_numbers(selected, field)
            if values:
                result.append(
                    {
                        "repetition": repetition + 1,
                        "metric": field,
                        "measured_cells": len(values),
                        "mean_percent": statistics.mean(values),
                        "minimum_percent": min(values),
                        "maximum_percent": max(values),
                    }
                )
    return result


def _write_derived_telemetry(
    root: Path, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    telemetry = _telemetry_summaries(rows)
    coverage = _coverage_summaries(rows)
    C.write_csv(
        root / "data" / "codeweaver_telemetry.csv",
        telemetry,
        _fieldnames(telemetry),
    )
    C.write_csv(
        root / "data" / "codeweaver_coverage.csv",
        coverage,
        _fieldnames(coverage),
    )
    return telemetry, coverage


def _telemetry_display(rows: list[dict[str, Any]]) -> list[list[Any]]:
    def display(
        value: Any,
        status: str,
        *,
        digits: int | None = None,
    ) -> str:
        if value is None:
            return f"N/A ({status})"
        rendered = f"{float(value):.{digits}f}" if digits is not None else str(value)
        return rendered if status == "measured" else f"{rendered} ({status})"

    return [
        [
            row["scope"].replace("_", " "),
            row["cells"],
            display(row["elapsed_hours"], row["elapsed_status"], digits=2),
            display(row["assistant_turns"], row["assistant_turn_status"]),
            display(row["tool_invocations"], row["tool_invocation_status"]),
            display(row["premium_requests"], row["premium_request_status"]),
            display(row["aiu"], row["aiu_status"], digits=2),
            display(row["output_tokens"], row["output_token_status"]),
            display(row["input_tokens"], row["input_token_status"]),
        ]
        for row in rows
    ]


def _coverage_display(rows: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            row["repetition"],
            row["metric"],
            row["measured_cells"],
            f"{row['mean_percent']:.2f}%",
            f"{row['minimum_percent']:.2f}%",
            f"{row['maximum_percent']:.2f}%",
        ]
        for row in rows
    ]


def _attach_clippy(
    root: Path,
    rows: list[dict[str, str]] | None,
    *,
    project_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[list[Any]]]:
    if rows is None:
        return [], []
    selected = [
        row
        for row in rows
        if project_ids is None or row["project_id"] in project_ids
    ]
    sanitized_fields = [
        "project_id",
        "repetition",
        "status",
        "returncode",
        "timed_out",
        "target_function_count",
        "warnings",
        "errors",
        "lint_alerts",
        "lint_alerts_per_function",
        "diagnostic_codes_json",
    ]
    C.write_csv(
        root / "data" / "codeweaver_clippy.csv",
        selected,
        sanitized_fields,
    )
    summaries: list[dict[str, Any]] = []
    for repetition in sorted({int(row["repetition"]) for row in selected}):
        repetition_rows = [
            row
            for row in selected
            if int(row["repetition"]) == repetition
        ]
        measured = [
            row
            for row in repetition_rows
            if row.get("status") == "measured"
        ]
        incomplete = [
            row for row in repetition_rows if row.get("status") != "measured"
        ]
        functions = sum(_number(row, "target_function_count") for row in measured)
        alerts = sum(_number(row, "lint_alerts") for row in measured)
        summaries.append(
            {
                "repetition": repetition + 1,
                "complete_cells": len(measured),
                "incomplete_cells": len(incomplete),
                "warning_free_cells": sum(
                    _number(row, "warnings") == 0
                    and _number(row, "errors") == 0
                    for row in measured
                ),
                "warnings": sum(_number(row, "warnings") for row in measured),
                "errors": sum(_number(row, "errors") for row in measured),
                "excluded_incomplete_warnings": sum(
                    _number(row, "warnings") for row in incomplete
                ),
                "excluded_incomplete_errors": sum(
                    _number(row, "errors") for row in incomplete
                ),
                "mean_alerts_per_project": (
                    statistics.mean(_number(row, "lint_alerts") for row in measured)
                    if measured
                    else None
                ),
                "alerts_per_function": alerts / functions if functions else None,
            }
        )
    C.write_csv(
        root / "data" / "codeweaver_clippy_summary.csv",
        summaries,
        _fieldnames(summaries),
    )
    display = [
        [
            row["repetition"],
            row["complete_cells"],
            row["incomplete_cells"],
            row["warning_free_cells"],
            row["warnings"],
            row["errors"],
            (
                f"{row['mean_alerts_per_project']:.2f}"
                if row["mean_alerts_per_project"] is not None
                else "N/A"
            ),
            (
                f"{row['alerts_per_function']:.3f}"
                if row["alerts_per_function"] is not None
                else "N/A"
            ),
        ]
        for row in summaries
    ]
    return summaries, display


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(cell(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(cell(value) for value in row) + " |" for row in rows
    )
    return "\n".join(lines)


def _latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _latex_table(headers: list[str], rows: list[list[Any]]) -> str:
    columns = "l" + "r" * (len(headers) - 1)
    lines = [
        r"\begin{tabular}{" + columns + "}",
        r"\toprule",
        " & ".join(_latex_escape(value) for value in headers) + r" \\",
        r"\midrule",
    ]
    lines.extend(
        " & ".join(_latex_escape(value) for value in row) + r" \\" for row in rows
    )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def _render_pdf(
    path: Path,
    *,
    title: str,
    abstract: str,
    sections: list[tuple[str, str]],
    tables: list[tuple[str, list[str], list[list[Any]]]],
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=title,
    )
    story: list[Any] = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 10),
        Paragraph(abstract, styles["BodyText"]),
        Spacer(1, 12),
    ]
    for heading, body in sections:
        story += [
            Paragraph(heading, styles["Heading2"]),
            Paragraph(body, styles["BodyText"]),
            Spacer(1, 9),
        ]
    for heading, headers, rows in tables:
        story += [Paragraph(heading, styles["Heading2"])]
        data = [[Paragraph(str(value), styles["BodyText"]) for value in headers]]
        data.extend(
            [Paragraph(str(value), styles["BodyText"]) for value in row] for row in rows
        )
        width = 7.4 * inch / max(1, len(headers))
        table = Table(data, colWidths=[width] * len(headers), repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f8")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story += [table, Spacer(1, 12)]
    document.build(story)


def _render_figure(
    pdf_path: Path,
    svg_path: Path,
    *,
    title: str,
    categories: list[str],
    series: list[tuple[str, list[float], str]],
    y_label: str = "Percent",
) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.pdfgen import canvas

    width, height = landscape(letter)
    chart_left, chart_bottom = 80, 70
    chart_width, chart_height = width - 125, height - 135
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    drawing = canvas.Canvas(str(pdf_path), pagesize=(width, height))
    drawing.setTitle(title)
    drawing.setFont("Helvetica-Bold", 15)
    drawing.drawString(chart_left, height - 35, title)
    drawing.setFont("Helvetica", 8)
    for tick in range(0, 101, 20):
        y = chart_bottom + chart_height * tick / 100
        drawing.setStrokeColor(HexColor("#d9d9d9"))
        drawing.line(chart_left, y, chart_left + chart_width, y)
        drawing.setFillColor(HexColor("#333333"))
        drawing.drawRightString(chart_left - 8, y - 3, str(tick))
    group_width = chart_width / max(1, len(categories))
    bar_width = group_width * 0.72 / max(1, len(series))
    for series_index, (label, values, color) in enumerate(series):
        drawing.setFillColor(HexColor(color))
        for category_index, value in enumerate(values):
            x = (
                chart_left
                + category_index * group_width
                + group_width * 0.14
                + series_index * bar_width
            )
            bar_height = chart_height * max(0.0, min(100.0, value)) / 100
            drawing.rect(x, chart_bottom, bar_width * 0.9, bar_height, fill=1, stroke=0)
            drawing.setFillColor(HexColor("#222222"))
            drawing.setFont("Helvetica", 6.5)
            drawing.drawCentredString(
                x + bar_width * 0.45, chart_bottom + bar_height + 4, f"{value:.1f}"
            )
            drawing.setFillColor(HexColor(color))
    drawing.setFillColor(HexColor("#222222"))
    for index, category in enumerate(categories):
        drawing.setFont("Helvetica", 7)
        drawing.drawCentredString(
            chart_left + (index + 0.5) * group_width, chart_bottom - 14, category
        )
    legend_x = chart_left
    for label, _, color in series:
        drawing.setFillColor(HexColor(color))
        drawing.rect(legend_x, height - 58, 10, 8, fill=1, stroke=0)
        drawing.setFillColor(HexColor("#222222"))
        drawing.setFont("Helvetica", 8)
        drawing.drawString(legend_x + 14, height - 57, label)
        legend_x += 20 + drawing.stringWidth(label, "Helvetica", 8)
    drawing.save()

    svg_width, svg_height = 1000, 620
    left, bottom, plot_width, plot_height = 90, 90, 850, 450
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="35" font-family="sans-serif" font-size="22" font-weight="bold">{title}</text>',
    ]
    for tick in range(0, 101, 20):
        y = bottom + plot_height - plot_height * tick / 100
        svg.append(
            f'<line x1="{left}" y1="{y}" x2="{left + plot_width}" y2="{y}" stroke="#d9d9d9"/>'
        )
        svg.append(
            f'<text x="{left - 12}" y="{y + 4}" text-anchor="end" font-family="sans-serif" font-size="12">{tick}</text>'
        )
    group = plot_width / max(1, len(categories))
    bar = group * 0.72 / max(1, len(series))
    for series_index, (label, values, color) in enumerate(series):
        for category_index, value in enumerate(values):
            x = left + category_index * group + group * 0.14 + series_index * bar
            height_value = plot_height * max(0.0, min(100.0, value)) / 100
            y = bottom + plot_height - height_value
            svg.append(
                f'<rect x="{x}" y="{y}" width="{bar * 0.9}" height="{height_value}" fill="{color}"/>'
            )
            svg.append(
                f'<text x="{x + bar * 0.45}" y="{y - 5}" text-anchor="middle" font-family="sans-serif" font-size="10">{value:.1f}</text>'
            )
    for index, category in enumerate(categories):
        x = left + (index + 0.5) * group
        svg.append(
            f'<text x="{x}" y="{bottom + plot_height + 24}" text-anchor="middle" font-family="sans-serif" font-size="11">{category}</text>'
        )
    legend_x = left
    for label, _, color in series:
        svg.append(
            f'<rect x="{legend_x}" y="52" width="13" height="10" fill="{color}"/>'
        )
        svg.append(
            f'<text x="{legend_x + 18}" y="62" font-family="sans-serif" font-size="12">{label}</text>'
        )
        legend_x += 30 + len(label) * 8
    svg.append("</svg>")
    C.atomic_write_text(svg_path, "\n".join(svg) + "\n")


def _write_report_files(
    root: Path,
    *,
    key: str,
    abstract: str,
    sections: list[tuple[str, str]],
    tables: list[tuple[str, list[str], list[list[Any]]]],
    figure: tuple[list[str], list[tuple[str, list[float], str]]],
    provenance: dict[str, Any],
    availability: list[dict[str, Any]],
) -> None:
    metadata = PAPER_METADATA[key]
    tables = list(tables)
    if key in PAPER_SURFACES:
        surfaces = _write_paper_reference_bundle(root, key)
        tables.append(
            (
                "Complete source-paper surface audit",
                ["Surface", "Denominator", "Metrics", "Artifact status"],
                [
                    [
                        row["surface"],
                        row["denominator"],
                        row["metrics"],
                        row["artifact_status"],
                    ]
                    for row in surfaces
                ],
            )
        )
    repository_root = Path(__file__).resolve().parents[2]
    worktree_status = C.git_output(
        repository_root,
        "-c",
        "core.autocrlf=true",
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        "agents",
        "codeweaver",
        "experiments/recodeagent",
        "experiments/related_papers",
        "tests/experiments/test_related_papers.py",
        "LICENSE",
        "README.md",
        "pyproject.toml",
    )
    tracked_patch = C.git_output(
        repository_root,
        "-c",
        "core.autocrlf=true",
        "diff",
        "--binary",
        "HEAD",
        "--",
        "agents",
        "codeweaver",
        "experiments/recodeagent",
        "experiments/related_papers",
        "tests/experiments/test_related_papers.py",
        "LICENSE",
        "README.md",
        "pyproject.toml",
    )
    provenance = {
        **provenance,
        "codeweaver_source": {
            "repository": "https://github.com/gsoosk/CodeWeaver",
            "base_git_commit": C.git_output(
                repository_root, "rev-parse", "HEAD"
            ),
            "source_worktree_clean": not bool(worktree_status),
            "source_worktree_entry_count": len(worktree_status.splitlines()),
            "source_worktree_status_sha256": C.sha256_text(worktree_status),
            "tracked_source_patch_sha256": C.sha256_text(tracked_patch),
            "identity_policy": (
                "the reproduction snapshot tree hash identifies the exact "
                "evaluated harness; the Git commit is its base revision"
            ),
        },
    }
    if key in {"crust", "alphatrans", "sactor"}:
        historical_root = (
            repository_root
            / "results"
            / "recodeagent-gpt-5.6-sol-final-2026-08-11"
        )
        verification = historical_root / "metadata" / "final_verification.json"
        raw = historical_root / "data" / "collected" / "raw_runs.csv"
        if verification.is_file() and raw.is_file():
            provenance["reused_campaign_evidence"] = {
                "status": "verified",
                "artifact": str(historical_root.relative_to(repository_root)),
                "final_verification_sha256": C.sha256_file(verification),
                "normalized_raw_runs_sha256": C.sha256_file(raw),
            }
        else:
            provenance["reused_campaign_evidence"] = {
                "status": "external_inputs",
                "reason": (
                    "standalone snapshot does not embed the prior campaign; "
                    "input-file checksums are captured by this artifact"
                ),
            }
    title = f"CodeWeaver comparison with {metadata['title']}"
    markdown = [f"# {title}", "", "## Abstract", "", abstract, ""]
    for heading, body in sections:
        markdown += [f"## {heading}", "", body, ""]
    for heading, headers, rows in tables:
        markdown += [f"## {heading}", "", _markdown_table(headers, rows), ""]
    markdown += [
        "## Artifact map",
        "",
        "- `data/`: normalized measurements and paper reference values.",
        "- `data/paper-reference/`: structured references for omitted source-paper tables.",
        "- `data/paper_surface_inventory.csv`: every source-paper evaluation surface and status.",
        "- `report/comparison.pdf`: human-readable result paper.",
        "- `report/figure.pdf` and `report/figure.svg`: publication figure.",
        "- `metadata/`: provenance, availability, and checksums.",
        "- `reproduction/`: commands and harness snapshot.",
    ]
    if key in {"repotransbench", "rustrepotrans"}:
        markdown.append(
            "- `raw-run-archives/`: filtered run states and agent artifacts; "
            "benchmark inputs and full project trees are withheld."
        )
    markdown.append("")
    C.atomic_write_text(root / "report" / "comparison.md", "\n".join(markdown))
    latex_parts = [
        r"\documentclass{article}",
        r"\usepackage[margin=0.7in]{geometry}",
        r"\usepackage{booktabs}",
        r"\begin{document}",
        r"\section*{" + _latex_escape(title) + "}",
        _latex_escape(abstract),
    ]
    for heading, headers, rows in tables:
        latex_parts += [
            r"\subsection*{" + _latex_escape(heading) + "}",
            _latex_table(headers, rows),
        ]
    latex_parts.append(r"\end{document}")
    C.atomic_write_text(
        root / "report" / "comparison.tex", "\n\n".join(latex_parts) + "\n"
    )
    _render_pdf(
        root / "report" / "comparison.pdf",
        title=title,
        abstract=abstract,
        sections=sections,
        tables=tables,
    )
    categories, series = figure
    _render_figure(
        root / "report" / "figure.pdf",
        root / "report" / "figure.svg",
        title=title,
        categories=categories,
        series=series,
    )
    try:
        reportlab_version = importlib.metadata.version("reportlab")
    except importlib.metadata.PackageNotFoundError:
        reportlab_version = "unavailable"
    C.atomic_write_json(
        root / "metadata" / "rendering_environment.json",
        {
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "reportlab": reportlab_version,
        },
    )
    availability_fields = [
        "surface",
        "status",
        "reason",
        "measurement_track",
    ]
    C.write_csv(
        root / "metadata" / "availability.csv", availability, availability_fields
    )
    C.atomic_write_json(
        root / "metadata" / "report_manifest.json",
        {
            "schema_version": 1,
            "generated_at": C.utcnow_iso(),
            "paper": metadata,
            "protocol": PROTOCOL,
            "artifact_files": {
                "comparison_pdf": "report/comparison.pdf",
                "figure_pdf": "report/figure.pdf",
                "figure_svg": "report/figure.svg",
                "normalized_data": "data/",
            },
        },
    )
    raw_archive_note = ""
    if key in {"repotransbench", "rustrepotrans"}:
        raw_archive_note = r"""
Filtered raw run states and agent artifacts are under `raw-run-archives/`.
Generated Java files or Rust functions are exported separately under
`data/generated/`. Benchmark inputs and full external project trees are omitted;
their hashes are recorded in `metadata/withheld_scaffold_manifest.csv`.
Pre-model launcher failures are preserved under
`infrastructure-failure-archives/` and excluded from measured cells.

If the archive is split, concatenate `full.tar.gz.part-*` in lexical order
before extracting it:

```sh
cat raw-run-archives/full.tar.gz.part-* > full.tar.gz
tar -xzf full.tar.gz
```

```powershell
$parts = Get-ChildItem raw-run-archives\full.tar.gz.part-* | Sort-Object Name
$out = [IO.File]::Create('full.tar.gz')
try { foreach ($part in $parts) { $bytes = [IO.File]::ReadAllBytes($part); $out.Write($bytes) } }
finally { $out.Dispose() }
tar -xzf full.tar.gz
```
"""
    elif key == "citations":
        raw_archive_note = r"""
The `paper-profiles/` directory contains one PDF/Markdown evidence profile and
complete empirical-surface inventory for each included work. When the ACToR
campaign is supplied, `data/actor-li/` contains all normalized measurements,
generated candidates, post-run public oracle snapshots, and qualification
logs; `raw-run-archives/` contains filtered run states and agent trajectories.
Benchmark inputs are excluded from model-readable workspaces during execution.
"""
    readme = f"""\
# {title}

Read `report/comparison.pdf` first. This directory separates measured
CodeWeaver outcomes, published reference values, and unavailable surfaces.

Paper: [{metadata["paper_id"]}]({metadata["paper_url"]})
{raw_archive_note}

Verify this artifact with:

```sh
sha256sum -c metadata/checksums.sha256
```
"""
    C.atomic_write_text(root / "README.md", readme)
    snapshot = root / "reproduction" / "source"
    if snapshot.exists():
        shutil.rmtree(snapshot)
    for relative in (
        Path("agents"),
        Path("codeweaver"),
        Path("experiments") / "recodeagent",
        Path("experiments") / "related_papers",
    ):
        shutil.copytree(
            repository_root / relative,
            snapshot / relative,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".pytest_cache", ".coverage"
            ),
        )
    test_source = (
        repository_root / "tests" / "experiments" / "test_related_papers.py"
    )
    test_destination = (
        snapshot / "tests" / "experiments" / "test_related_papers.py"
    )
    test_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_source, test_destination)
    for name in ("LICENSE", "README.md", "pyproject.toml"):
        shutil.copy2(repository_root / name, snapshot / name)
    C.atomic_write_text(
        root / "reproduction" / "README.md",
        "The exact CodeWeaver, runner, agent-profile, and related-paper harness "
        "sources are under `source/`. See "
        "`source/experiments/related_papers/README.md`, then run "
        "`python -m experiments.related_papers --help` from that snapshot. "
        "External benchmark repositories and licensed contracts are acquired "
        "separately and verified by commit/hash.\n",
    )
    snapshot_sha256, snapshot_files = _tree_identity(snapshot)
    provenance["codeweaver_source"].update(
        {
            "snapshot_tree_sha256": snapshot_sha256,
            "snapshot_files": snapshot_files,
        }
    )
    C.atomic_write_json(root / "metadata" / "source_provenance.json", provenance)
    codeweaver_license = repository_root / "LICENSE"
    if not codeweaver_license.is_file():
        raise FileNotFoundError(f"CodeWeaver license missing: {codeweaver_license}")
    license_destination = root / "licenses" / "CodeWeaver-MIT.txt"
    license_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(codeweaver_license, license_destination)
    C.checksums(root, output=root / "metadata" / "checksums.sha256")


def _copy_campaign_metadata_and_licenses(
    root: Path,
    campaign_root: Path,
    subjects: list[dict[str, Any]],
) -> None:
    for subject in subjects:
        workspace = campaign_root / "workspaces" / subject["id"]
        prepared = workspace / "prepared.json"
        if not prepared.is_file():
            raise FileNotFoundError(f"prepared metadata missing: {prepared}")
        prepared_destination = (
            root / "metadata" / "prepared" / f"{subject['id']}.json"
        )
        prepared_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prepared, prepared_destination)
        licenses = sorted(
            path for path in (workspace / "licenses").glob("*") if path.is_file()
        )
        if not licenses:
            raise FileNotFoundError(f"workspace license missing: {workspace}")
        for license_path in licenses:
            destination = (
                root
                / "licenses"
                / "subjects"
                / subject["id"]
                / license_path.name
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(license_path, destination)


def _historical_rows(raw_rows: list[dict[str, str]], tool: str) -> list[dict[str, str]]:
    return [
        row
        for row in raw_rows
        if row.get("variant") == "full" and row.get("tool") == tool
    ]


def _rep_summaries(rows: list[dict[str, str]], expected_key: str) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for repetition in range(3):
        selected = [row for row in rows if int(row["repetition"]) == repetition]
        expected = sum(_number(row, expected_key) for row in selected)
        observed_passed = sum(
            _number(row, "validated_tests_passed") for row in selected
        )
        passed = sum(
            min(
                _number(row, "validated_tests_passed"),
                _number(row, expected_key),
            )
            for row in selected
        )
        summaries.append(
            {
                "repetition": repetition + 1,
                "projects": len(selected),
                "builds": sum(_bool(row.get("build")) for row in selected),
                "pass_all": sum(_bool(row.get("project_pass_all")) for row in selected),
                "tests_passed": passed,
                "tests_observed_passed": observed_passed,
                "tests_expected": expected,
                "test_rate_percent": 100.0 * passed / expected if expected else None,
            }
        )
    return summaries


def build_crust(
    output_root: Path,
    raw_rows: list[dict[str, str]],
    manifest: dict[str, Any],
    clippy_rows: list[dict[str, str]] | None = None,
) -> Path:
    root = output_root / RESULT_NAMES["crust"]
    rows = _historical_rows(raw_rows, "crust")
    if len(rows) != 300:
        raise ValueError(f"expected 300 reusable CRUST rows, found {len(rows)}")
    summaries = _rep_summaries(rows, "validated_tests_expected_paper")
    rates = [100.0 * row["pass_all"] / row["projects"] for row in summaries]
    mean, sd, ci = _mean_sd(rates)
    exact_headers = [
        "Run",
        "Build",
        "Pass all",
        "Fixed tests",
        "Test rate",
    ]
    exact_rows = [
        [
            f"CodeWeaver rep {row['repetition']}",
            f"{row['builds']}/{row['projects']}",
            f"{row['pass_all']}/{row['projects']} ({100*row['pass_all']/row['projects']:.2f}%)",
            f"{row['tests_passed']}/{row['tests_expected']}",
            _percent(row["test_rate_percent"]),
        ]
        for row in summaries
    ]
    exact_rows.append(
        [
            "CodeWeaver mean",
            "100.00%",
            f"{mean:.2f}% +/- {sd:.2f} pp",
            "three independent repetitions",
            f"95% t-CI +/- {ci:.2f} pp",
        ]
    )
    paper_headers = [
        "System",
        "Base build",
        "Base test",
        "Compiler-repair build",
        "Compiler-repair test",
        "Test-repair build",
        "Test-repair test",
    ]
    paper_rows = [
        [
            row["model"],
            _percent(row["base_build"]),
            _percent(row["base_test"]),
            _percent(row["compiler_build"]),
            _percent(row["compiler_test"]),
            _percent(row["test_build"]),
            _percent(row["test_test"]),
        ]
        for row in CRUST_TABLE4
    ]
    C.write_csv(root / "data" / "raw_runs.csv", rows, list(rows[0]))
    _write_jsonl(root / "data" / "raw_runs.jsonl", rows)
    C.write_csv(
        root / "data" / "repetition_summary.csv",
        summaries,
        list(summaries[0]),
    )
    C.write_csv(
        root / "data" / "paper_table4.csv",
        CRUST_TABLE4,
        list(CRUST_TABLE4[0]),
    )
    stability: list[dict[str, Any]] = []
    projects = sorted({row["project_id"] for row in rows})
    for project in projects:
        selected = [row for row in rows if row["project_id"] == project]
        stability.append(
            {
                "project_id": project,
                "passing_repetitions": sum(
                    _bool(row["project_pass_all"]) for row in selected
                ),
                "build_repetitions": sum(_bool(row["build"]) for row in selected),
            }
        )
    C.write_csv(
        root / "data" / "project_stability.csv",
        stability,
        list(stability[0]),
    )
    C.atomic_write_json(
        root / "data" / "summary.json",
        {
            "measured_rows": len(rows),
            "projects": 100,
            "repetitions": 3,
            "build_cells": sum(_bool(row["build"]) for row in rows),
            "pass_all_cells": sum(_bool(row["project_pass_all"]) for row in rows),
            "projects_passing_any": sum(row["passing_repetitions"] > 0 for row in stability),
            "projects_passing_all": sum(row["passing_repetitions"] == 3 for row in stability),
            "mean_project_pass_rate_percent": mean,
            "sample_sd_pp": sd,
            "confidence_interval_95_pp": ci,
        },
    )
    telemetry, coverage = _write_derived_telemetry(root, rows)
    _, clippy_display = _attach_clippy(root, clippy_rows)
    abstract = (
        f"On all 100 exact CRUST-Bench subjects, 300/300 CodeWeaver cells "
        f"compiled and {sum(row['pass_all'] for row in summaries)}/300 passed "
        f"every fixed project test. Mean project success was {mean:.2f}% "
        f"(sample SD {sd:.2f} pp). The paper's single-shot and three-round "
        "repair settings are preserved as references; CodeWeaver's multi-stage "
        "five-repair/three-parity protocol is not relabeled as those settings."
    )
    sections = [
        (
            "Method",
            "This exact-subject re-analysis imports the published CodeWeaver "
            "campaign's independently restored CRUST interfaces and fixed tests. "
            "All three terminal outcomes are retained; no best-of-three selection "
            "is used.",
        ),
        (
            "Validity boundary",
            "CRUST-Bench's Table 4 reports pass rates under single-shot, compiler "
            "repair, test repair, and an adapted SWE-agent. CodeWeaver uses a "
            "different architecture and larger repair budget. Comparison is "
            "descriptive, not a controlled model ablation.",
        ),
    ]
    tables = [
        ("Exact CodeWeaver measurements", exact_headers, exact_rows),
        ("Published CRUST-Bench Table 4", paper_headers, paper_rows),
        (
            "CodeWeaver execution and model-use telemetry",
            [
                "Scope",
                "Cells",
                "Elapsed h",
                "Assistant turns",
                "Tool calls",
                "Premium requests",
                "AIU",
                "Output tokens",
                "Input tokens",
            ],
            _telemetry_display(telemetry),
        ),
        (
            "CodeWeaver coverage measurements",
            ["Rep", "Metric", "Cells", "Mean", "Min", "Max"],
            _coverage_display(coverage),
        ),
    ]
    if clippy_display:
        tables.append(
            (
                "CodeWeaver final-output Clippy measurements",
                [
                    "Rep",
                    "Complete",
                    "Incomplete",
                    "Warning-free",
                    "Warnings",
                    "Errors",
                    "Alerts/project",
                    "Alerts/function",
                ],
                clippy_display,
            )
        )
    _write_report_files(
        root,
        key="crust",
        abstract=abstract,
        sections=sections,
        tables=tables,
        figure=(
            ["Rep 1", "Rep 2", "Rep 3"],
            [
                ("Build", [100.0, 100.0, 100.0], "#4c78a8"),
                ("Pass all", rates, "#f58518"),
                (
                    "Fixed tests",
                    [row["test_rate_percent"] for row in summaries],
                    "#54a24b",
                ),
            ],
        ),
        provenance={
            "generated_at": C.utcnow_iso(),
            "paper": PAPER_METADATA["crust"],
            "upstream_repository": UPSTREAM_REPOSITORIES["crust_bench"],
            "upstream_commit": UPSTREAM_COMMITS["crust_bench"],
            "reused_campaign": "results/recodeagent-gpt-5.6-sol-final-2026-08-11",
            "protocol": PROTOCOL,
            "manifest_projects": len(
                [row for row in manifest["projects"] if row["tool"] == "crust"]
            ),
        },
        availability=[
            {
                "surface": "100-project build and fixed tests",
                "status": "measured",
                "reason": "exact subjects and fixed project contracts",
                "measurement_track": "CodeWeaver three-repetition",
            },
            {
                "surface": "paper single-shot/compiler/test-repair controls",
                "status": "reference_only",
                "reason": "different model and protocol",
                "measurement_track": "published Table 4",
            },
            {
                "surface": "manual error taxonomy",
                "status": "not_recreated",
                "reason": "would require new blinded human coding",
                "measurement_track": "unavailable",
            },
        ],
    )
    return root


def build_alphatrans(output_root: Path, raw_rows: list[dict[str, str]]) -> Path:
    root = output_root / RESULT_NAMES["alphatrans"]
    rows = _historical_rows(raw_rows, "alphatrans")
    if len(rows) != 12:
        raise ValueError(f"expected 12 reusable AlphaTrans rows, found {len(rows)}")
    summaries = _rep_summaries(rows, "validated_tests_expected")
    project_rows: list[dict[str, Any]] = []
    for project_id in sorted({row["project_id"] for row in rows}):
        name = project_id.split("__", 1)[1]
        reference = ALPHATRANS_REFERENCE[name]
        selected = sorted(
            (row for row in rows if row["project_id"] == project_id),
            key=lambda row: int(row["repetition"]),
        )
        project_rows.append(
            {
                "project": name,
                "paper_subject": reference["paper_subject"],
                "paper_amf": reference["amf"],
                "paper_syntax_percent": reference["syntax_percent"],
                "paper_fragment_tpr_percent": reference["tpr_percent"],
                "codeweaver_build_cells": sum(_bool(row["build"]) for row in selected),
                "codeweaver_pass_all_cells": sum(
                    _bool(row["project_pass_all"]) for row in selected
                ),
                "codeweaver_tests_passed": sum(
                    _number(row, "validated_tests_passed") for row in selected
                ),
                "codeweaver_tests_expected": sum(
                    _number(row, "validated_tests_expected") for row in selected
                ),
            }
        )
    display_rows = [
        [
            row["project"],
            _percent(row["paper_syntax_percent"]),
            _percent(row["paper_fragment_tpr_percent"]),
            f"{row['codeweaver_build_cells']}/3",
            (
                f"{row['codeweaver_tests_passed']}/"
                f"{row['codeweaver_tests_expected']} "
                f"({_percent(100*row['codeweaver_tests_passed']/row['codeweaver_tests_expected'])})"
            ),
        ]
        for row in project_rows
    ]
    rep_rows = [
        [
            row["repetition"],
            f"{row['builds']}/{row['projects']}",
            f"{row['pass_all']}/{row['projects']}",
            f"{row['tests_passed']}/{row['tests_expected']}",
            _percent(row["test_rate_percent"]),
        ]
        for row in summaries
    ]
    C.write_csv(root / "data" / "raw_runs.csv", rows, list(rows[0]))
    _write_jsonl(root / "data" / "raw_runs.jsonl", rows)
    C.write_csv(
        root / "data" / "project_comparison.csv",
        project_rows,
        list(project_rows[0]),
    )
    C.write_csv(
        root / "data" / "repetition_summary.csv",
        summaries,
        list(summaries[0]),
    )
    paper_rows = [
        {"project": key, **value} for key, value in ALPHATRANS_REFERENCE.items()
    ]
    C.write_csv(
        root / "data" / "paper_reference.csv",
        paper_rows,
        list(paper_rows[0]),
    )
    total_passed = sum(_number(row, "validated_tests_passed") for row in rows)
    total_expected = sum(_number(row, "validated_tests_expected") for row in rows)
    C.atomic_write_json(
        root / "data" / "summary.json",
        {
            "exact_subjects": 4,
            "paper_subjects_total": 10,
            "measured_rows": 12,
            "build_cells": sum(_bool(row["build"]) for row in rows),
            "pass_all_cells": sum(_bool(row["project_pass_all"]) for row in rows),
            "fixed_runtime_cases_passed": total_passed,
            "fixed_runtime_cases_expected": total_expected,
        },
    )
    telemetry, coverage = _write_derived_telemetry(root, rows)
    abstract = (
        "Four of AlphaTrans's ten exact Java projects were already measured in "
        "the published CodeWeaver matrix. All 12 translations compiled; none "
        f"passed every available fixed runtime case. Across repetitions, "
        f"{total_passed}/{total_expected} fixed cases passed. AlphaTrans's "
        "fragment-level TPR is preserved separately because it is not the same "
        "unit or denominator as CodeWeaver's project-test execution."
    )
    sections = [
        (
            "Scope",
            "The exact common subjects are commons-cli, commons-csv, "
            "commons-fileupload, and commons-validator. Six paper subjects were "
            "not run, so this artifact makes no ten-project aggregate claim.",
        ),
        (
            "Unavailable surface",
            "AlphaTrans's manual type-map completion, manual repair effort, "
            "GraalVM fragment validation, and human bug taxonomy cannot be "
            "recovered from CodeWeaver's end-to-end project outputs and are "
            "reported as unavailable rather than zero.",
        ),
    ]
    tables = [
        (
            "Exact-subject comparison",
            ["Project", "AlphaTrans syntax", "AlphaTrans TPR", "CW builds", "CW fixed tests"],
            display_rows,
        ),
        (
            "CodeWeaver repetitions",
            ["Rep", "Build", "Pass all", "Fixed tests", "Test rate"],
            rep_rows,
        ),
        (
            "CodeWeaver execution and model-use telemetry",
            [
                "Scope",
                "Cells",
                "Elapsed h",
                "Assistant turns",
                "Tool calls",
                "Premium requests",
                "AIU",
                "Output tokens",
                "Input tokens",
            ],
            _telemetry_display(telemetry),
        ),
        (
            "CodeWeaver standardized coverage measurements",
            ["Rep", "Metric", "Cells", "Mean", "Min", "Max"],
            _coverage_display(coverage),
        ),
    ]
    _write_report_files(
        root,
        key="alphatrans",
        abstract=abstract,
        sections=sections,
        tables=tables,
        figure=(
            [row["project"] for row in project_rows],
            [
                (
                    "AlphaTrans fragment TPR",
                    [row["paper_fragment_tpr_percent"] for row in project_rows],
                    "#4c78a8",
                ),
                (
                    "CodeWeaver fixed tests",
                    [
                        100
                        * row["codeweaver_tests_passed"]
                        / row["codeweaver_tests_expected"]
                        for row in project_rows
                    ],
                    "#f58518",
                ),
            ],
        ),
        provenance={
            "generated_at": C.utcnow_iso(),
            "paper": PAPER_METADATA["alphatrans"],
            "upstream_repository": UPSTREAM_REPOSITORIES["alphatrans"],
            "upstream_commit": UPSTREAM_COMMITS["alphatrans"],
            "reused_campaign": "results/recodeagent-gpt-5.6-sol-final-2026-08-11",
            "protocol": PROTOCOL,
        },
        availability=[
            {
                "surface": "four exact projects, build/fixed tests",
                "status": "measured",
                "reason": "compatible historical CodeWeaver cells",
                "measurement_track": "CodeWeaver three-repetition",
            },
            {
                "surface": "remaining six projects",
                "status": "not_measured",
                "reason": "outside prior exact-subject campaign",
                "measurement_track": "unavailable",
            },
            {
                "surface": "manual type mapping and human repair",
                "status": "unavailable",
                "reason": "human intervention cannot be inferred from terminal outputs",
                "measurement_track": "paper reference only",
            },
        ],
    )
    return root


def _sactor_safety_rows(historical_runs_root: Path) -> list[dict[str, Any]]:
    from experiments.evoc2rust.evaluator import unsafe_line_metrics

    rows: list[dict[str, Any]] = []
    for subject in SACTOR_SUBJECTS:
        for repetition in range(3):
            target = (
                historical_runs_root
                / f"crust__{subject}"
                / f"rep{repetition}"
                / "pipeline"
                / "target"
            )
            paths = [
                path
                for path in (target / "src").rglob("*.rs")
                if "bin" not in path.relative_to(target / "src").parts
                and "test" not in path.name.lower()
            ]
            metrics = unsafe_line_metrics(paths)
            rows.append(
                {
                    "subject": subject,
                    "repetition": repetition + 1,
                    "production_files": len(paths),
                    "total_nonblank_lines": metrics["total_lines"],
                    "unsafe_lines": metrics["unsafe_lines"],
                    "safe_lines": metrics["safe_lines"],
                    "safe_rate_percent": metrics["safe_rate_percent"],
                    "unsafe_free": metrics["unsafe_lines"] == 0,
                }
            )
    return rows


def build_sactor(
    output_root: Path,
    raw_rows: list[dict[str, str]],
    historical_runs_root: Path,
    clippy_rows: list[dict[str, str]] | None = None,
) -> Path:
    root = output_root / RESULT_NAMES["sactor"]
    ids = {f"crust__{subject}" for subject in SACTOR_SUBJECTS}
    rows = [
        row
        for row in _historical_rows(raw_rows, "crust")
        if row["project_id"] in ids
    ]
    if len(rows) != 150:
        raise ValueError(f"expected 150 SACTOR-subset rows, found {len(rows)}")
    summaries = _rep_summaries(rows, "validated_tests_expected_paper")
    safety = _sactor_safety_rows(historical_runs_root)
    for summary in summaries:
        rep_safety = [
            row for row in safety if row["repetition"] == summary["repetition"]
        ]
        total = sum(row["total_nonblank_lines"] for row in rep_safety)
        unsafe = sum(row["unsafe_lines"] for row in rep_safety)
        summary["unsafe_free_projects"] = sum(row["unsafe_free"] for row in rep_safety)
        summary["safe_rate_percent"] = 100.0 * (total - unsafe) / total
    display_rows = [
        [
            f"CodeWeaver rep {row['repetition']}",
            f"{row['builds']}/{row['projects']}",
            f"{row['pass_all']}/{row['projects']} ({100*row['pass_all']/row['projects']:.2f}%)",
            f"{row['tests_passed']}/{row['tests_expected']} ({_percent(row['test_rate_percent'])})",
            f"{row['unsafe_free_projects']}/{row['projects']}",
            _percent(row["safe_rate_percent"]),
        ]
        for row in summaries
    ]
    reference_rows = [
        ["SACTOR unidiomatic", "function", "81.57%", "32/50 (64.00%)", "0%", "heavy unsafe"],
        ["SACTOR idiomatic", "function, conditional", "42.93%", "8/32 (25.00%)", "100%", "32 survivors only"],
        ["CodeWeaver rep 1", "whole project", "N/A", f"{summaries[0]['pass_all']}/50", f"{summaries[0]['unsafe_free_projects']}/50", _percent(summaries[0]["safe_rate_percent"])],
        ["CodeWeaver rep 2", "whole project", "N/A", f"{summaries[1]['pass_all']}/50", f"{summaries[1]['unsafe_free_projects']}/50", _percent(summaries[1]["safe_rate_percent"])],
        ["CodeWeaver rep 3", "whole project", "N/A", f"{summaries[2]['pass_all']}/50", f"{summaries[2]['unsafe_free_projects']}/50", _percent(summaries[2]["safe_rate_percent"])],
    ]
    C.write_csv(root / "data" / "raw_runs.csv", rows, list(rows[0]))
    _write_jsonl(root / "data" / "raw_runs.jsonl", rows)
    C.write_csv(
        root / "data" / "safety.csv", safety, list(safety[0])
    )
    C.write_csv(
        root / "data" / "repetition_summary.csv",
        summaries,
        list(summaries[0]),
    )
    C.write_csv(
        root / "data" / "paper_reference.csv",
        [{"metric": key, "value": value} for key, value in SACTOR_REFERENCE.items()],
        ["metric", "value"],
    )
    C.atomic_write_json(
        root / "data" / "summary.json",
        {
            "subjects": 50,
            "measured_rows": 150,
            "build_cells": sum(_bool(row["build"]) for row in rows),
            "pass_all_cells": sum(_bool(row["project_pass_all"]) for row in rows),
            "projects_passing_any": len(
                {row["project_id"] for row in rows if _bool(row["project_pass_all"])}
            ),
            "projects_passing_all": sum(
                all(
                    _bool(row["project_pass_all"])
                    for row in rows
                    if row["project_id"] == project
                )
                for project in ids
            ),
        },
    )
    telemetry, coverage = _write_derived_telemetry(root, rows)
    _, clippy_display = _attach_clippy(root, clippy_rows, project_ids=ids)
    abstract = (
        "SACTOR's Appendix Table 14 identifies an exact 50-project CRUST-Bench "
        "subset, enabling an exact-subject CodeWeaver re-analysis. All 150 "
        "CodeWeaver cells compiled; 92/150 passed every fixed project test. "
        "CodeWeaver's end-to-end project metric and static safety scan are not "
        "pooled with SACTOR's function-level, two-stage, conditionally evaluated "
        "idiomatic metric."
    )
    sections = [
        (
            "Denominator discipline",
            "SACTOR evaluates 966 functions in its unidiomatic stage, then only "
            "the 32 fully successful samples in its idiomatic stage. CodeWeaver "
            "evaluates all 50 projects in every repetition against 319 fixed "
            "project tests. These denominators remain explicit.",
        ),
        (
            "Safety metric",
            "CodeWeaver SafeRate is the line-weighted fraction of nonblank "
            "production Rust outside unsafe functions or blocks. SACTOR reports "
            "unsafe-free programs and average unsafe fraction with its own "
            "analyzer. The intent overlaps, but the implementations are not "
            "assumed identical.",
        ),
    ]
    tables = [
        (
            "Exact CodeWeaver measurements",
            ["Run", "Build", "Pass all", "Fixed tests", "Unsafe-free", "SafeRate"],
            display_rows,
        ),
        (
            "SACTOR v3 CRUST-Bench function-level comparison boundary",
            ["System", "Unit", "Function success", "Complete samples", "Unsafe-free", "Note"],
            reference_rows,
        ),
        (
            "CodeWeaver execution and model-use telemetry",
            [
                "Scope",
                "Cells",
                "Elapsed h",
                "Assistant turns",
                "Tool calls",
                "Premium requests",
                "AIU",
                "Output tokens",
                "Input tokens",
            ],
            _telemetry_display(telemetry),
        ),
        (
            "CodeWeaver coverage measurements",
            ["Rep", "Metric", "Cells", "Mean", "Min", "Max"],
            _coverage_display(coverage),
        ),
    ]
    if clippy_display:
        tables.append(
            (
                "CodeWeaver final-output Clippy comparison",
                [
                    "Rep",
                    "Complete",
                    "Incomplete",
                    "Warning-free",
                    "Warnings",
                    "Errors",
                    "Alerts/project",
                    "Alerts/function",
                ],
                clippy_display,
            )
        )
    _write_report_files(
        root,
        key="sactor",
        abstract=abstract,
        sections=sections,
        tables=tables,
        figure=(
            ["Rep 1", "Rep 2", "Rep 3"],
            [
                (
                    "Pass all",
                    [100 * row["pass_all"] / row["projects"] for row in summaries],
                    "#f58518",
                ),
                (
                    "Unsafe-free",
                    [
                        100 * row["unsafe_free_projects"] / row["projects"]
                        for row in summaries
                    ],
                    "#54a24b",
                ),
                (
                    "Fixed tests",
                    [row["test_rate_percent"] for row in summaries],
                    "#4c78a8",
                ),
            ],
        ),
        provenance={
            "generated_at": C.utcnow_iso(),
            "paper": PAPER_METADATA["sactor"],
            "upstream_repository": UPSTREAM_REPOSITORIES["sactor"],
            "upstream_commit": UPSTREAM_COMMITS["sactor"],
            "subset_source": "paper Appendix Table 14",
            "reused_campaign": "results/recodeagent-gpt-5.6-sol-final-2026-08-11",
            "protocol": PROTOCOL,
        },
        availability=[
            {
                "surface": "50 exact subjects, build/fixed tests/safety",
                "status": "measured",
                "reason": "exact Appendix Table 14 subject intersection",
                "measurement_track": "CodeWeaver three-repetition",
            },
            {
                "surface": "SACTOR function-level stages",
                "status": "reference_only",
                "reason": "different unit and conditional denominator",
                "measurement_track": "published Table 2",
            },
            {
                "surface": "libogg and SACTOR ablations",
                "status": "not_recreated",
                "reason": "outside compatible CodeWeaver subject evidence",
                "measurement_track": "paper reference only",
            },
        ],
    )
    return root


def _load_new_rows(path: Path, expected: int) -> list[dict[str, str]]:
    rows = _load_csv(path)
    if len(rows) != expected:
        raise ValueError(f"{path}: expected {expected} rows, found {len(rows)}")
    if any(row.get("evaluation_status") != "measured" for row in rows):
        raise ValueError(f"{path}: contains non-measured rows")
    return rows


def _new_repetition_summary(
    rows: list[dict[str, str]], subjects: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for repetition in range(3):
        selected = [row for row in rows if int(row["repetition"]) == repetition]
        test_rates = [
            100.0 * _number(row, "tests_passed") / _number(row, "expected_tests")
            for row in selected
        ]
        module_rates = [
            100.0
            * _number(row, "test_modules_passed")
            / _number(row, "test_modules_total")
            for row in selected
            if _number(row, "test_modules_total")
        ]
        summaries.append(
            {
                "repetition": repetition + 1,
                "subjects": len(selected),
                "pipeline_terminal": sum(
                    row.get("run_status") == "completed" for row in selected
                ),
                "builds": sum(_bool(row["build"]) for row in selected),
                "pass_all": sum(_bool(row["pass_all"]) for row in selected),
                "tests_passed": sum(_number(row, "tests_passed") for row in selected),
                "tests_expected": sum(
                    _number(row, "expected_tests") for row in selected
                ),
                "average_pass_rate_percent": statistics.mean(test_rates),
                "average_module_pass_rate_percent": (
                    statistics.mean(module_rates) if module_rates else None
                ),
            }
        )
    return summaries


def build_repotransbench(output_root: Path, campaign_root: Path) -> Path:
    root = output_root / RESULT_NAMES["repotransbench"]
    rows = _load_new_rows(campaign_root / "evaluation" / "raw_runs.csv", 9)
    summaries = _new_repetition_summary(rows, REPOTRANSBENCH_SUBJECTS)
    prepared = {
        subject["id"]: C.read_json(
            campaign_root
            / "workspaces"
            / subject["id"]
            / "prepared.json"
        )
        for subject in REPOTRANSBENCH_SUBJECTS
    }
    leakage_audit: list[dict[str, Any]] = []
    for row in rows:
        released = {
            path.removeprefix("src/main/java/"): digest
            for path, digest in prepared[row["subject_id"]][
                "released_implementation_hashes"
            ].items()
        }
        generated_root = (
            campaign_root
            / "evaluation"
            / "generated"
            / row["subject_id"]
            / f"rep{row['repetition']}"
        )
        generated = {
            path.relative_to(generated_root).as_posix(): C.sha256_file(path)
            for path in sorted(generated_root.rglob("*.java"))
        } if generated_root.is_dir() else {}
        exact_files = sum(
            generated.get(path) == digest for path, digest in released.items()
        )
        leakage_audit.append(
            {
                "subject_id": row["subject_id"],
                "repetition": row["repetition"],
                "released_files": len(released),
                "generated_files": len(generated),
                "byte_identical_files": exact_files,
                "full_implementation_byte_identical": (
                    generated.keys() == released.keys()
                    and all(generated[path] == digest for path, digest in released.items())
                ),
            }
        )
    exact_full_cells = sum(
        bool(row["full_implementation_byte_identical"]) for row in leakage_audit
    )
    display_rows = [
        [
            f"CodeWeaver rep {row['repetition']}",
            f"{row['pipeline_terminal']}/{row['subjects']}",
            f"{row['pass_all']}/{row['subjects']} ({100*row['pass_all']/row['subjects']:.2f}%)",
            f"{row['builds']}/{row['subjects']} ({100*row['builds']/row['subjects']:.2f}%)",
            _percent(row["average_pass_rate_percent"]),
            _percent(row["average_module_pass_rate_percent"]),
        ]
        for row in summaries
    ]
    historical_rows = [
        [
            row["model"],
            _percent(row["success_at_1"]),
            _percent(row["build_at_1"]),
            _percent(row["apr"]),
        ]
        for row in REPOTRANSBENCH_V1_RESULTS
    ]
    current_rows = [
        [row["model"], _percent(row["sr"]), _percent(row["cr"]), _percent(row["apr"]), _percent(row["ampr"])]
        for row in REPOTRANSBENCH_PYTHON_JAVA
    ]
    C.write_csv(root / "data" / "raw_runs.csv", rows, list(rows[0]))
    C.write_csv(
        root / "data" / "repetition_summary.csv",
        summaries,
        list(summaries[0]),
    )
    C.write_csv(
        root / "data" / "paper_current_python_java.csv",
        REPOTRANSBENCH_PYTHON_JAVA,
        list(REPOTRANSBENCH_PYTHON_JAVA[0]),
    )
    C.write_csv(
        root / "data" / "historical_v1_reference.csv",
        REPOTRANSBENCH_V1_RESULTS,
        list(REPOTRANSBENCH_V1_RESULTS[0]),
    )
    C.write_csv(
        root / "data" / "oracle_audit.csv",
        REPOTRANSBENCH_ORACLE_AUDIT,
        list(REPOTRANSBENCH_ORACLE_AUDIT[0]),
    )
    C.write_csv(
        root / "data" / "leakage_audit.csv",
        leakage_audit,
        list(leakage_audit[0]),
    )
    C.write_csv(
        root / "data" / "subject_lock.csv",
        REPOTRANSBENCH_SUBJECTS,
        sorted({key for row in REPOTRANSBENCH_SUBJECTS for key in row}),
    )
    C.atomic_write_json(
        root / "data" / "summary.json",
        {
            "selected_subjects": len(REPOTRANSBENCH_SUBJECTS),
            "released_historical_subjects": 100,
            "current_paper_subjects": 1897,
            "measured_rows": len(rows),
            "build_cells": sum(_bool(row["build"]) for row in rows),
            "pass_all_cells": sum(_bool(row["pass_all"]) for row in rows),
            "pipeline_terminal_cells": sum(
                row.get("run_status") == "completed" for row in rows
            ),
            "fixed_tests_per_repetition": 37,
            "full_implementation_byte_identical_cells": exact_full_cells,
            "released_implementations_exposed_to_model": False,
        },
    )
    for source_name, destination_name in (
        ("raw_runs.jsonl", "raw_runs.jsonl"),
        ("summary.json", "evaluation_summary.json"),
    ):
        source = campaign_root / "evaluation" / source_name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, root / "data" / destination_name)
    source_generated = campaign_root / "evaluation" / "generated"
    if source_generated.exists():
        shutil.copytree(source_generated, root / "data" / "generated", dirs_exist_ok=True)
    source_logs = campaign_root / "evaluation" / "logs"
    if source_logs.exists():
        shutil.copytree(source_logs, root / "data" / "evaluation-logs", dirs_exist_ok=True)
    _copy_campaign_metadata_and_licenses(
        root, campaign_root, REPOTRANSBENCH_SUBJECTS
    )
    abstract = (
        "RepoTransBench's currently advertised 1,897-repository asset returned "
        "HTTP 404, and its historical Python source archive was unavailable. "
        "We reconstructed three licensed historical v1.0 Python-to-Java subjects "
        "from pinned upstream repositories and evaluated nine CodeWeaver cells "
        "against 37 released fixed tests. Seven cells reached CodeWeaver's own "
        "terminal-success state; all nine independently built and passed every "
        "fixed test. Results are a measured, stratified subset—not a "
        "full-current-benchmark claim."
    )
    sections = [
        (
            "Release audit",
            "Seven small historical candidates were calibrated. Three had "
            "meaningful passing goldens and were selected. Three released goldens "
            "failed their own tests; one passing oracle never called the translated "
            "class. The complete audit is in data/oracle_audit.csv.",
        ),
        (
            "Comparison tracks",
            "The historical v1 README's 100-project table is the nearest benchmark "
            "family reference. The current paper's 1,897-project Python-to-Java "
            "Table V values are also preserved, but neither is pooled with the "
            "three-project CodeWeaver subset.",
        ),
        (
            "Outcome interpretation",
            "The two nonterminal-success cells exhausted the parity loop after "
            "all generated milestones passed. Their extracted Java outputs "
            "nevertheless pass the independently restored pristine oracle. "
            "Pipeline terminal status and external functional success are "
            "therefore reported separately.",
        ),
        (
            "Leakage audit",
            f"{exact_full_cells}/9 generated implementations are byte-identical "
            "to the withheld released Java file set. The released Java files "
            "were hashed and removed before model access; per-cell file-level "
            "comparisons are in data/leakage_audit.csv.",
        ),
        (
            "Redistribution",
            "The reconstructed Python sources and generated Java files are "
            "covered by their upstream MIT licenses. RepoTransBench has no "
            "visible repository-level license, so released scaffold and test "
            "bytes are omitted from the result package; a path/hash manifest "
            "preserves their exact evaluated identity.",
        ),
    ]
    tables = [
        (
            "Measured three-project subset",
            ["Run", "Pipeline terminal", "SR", "CR", "APR", "AMPR"],
            display_rows,
        ),
        (
            "Historical v1 full-benchmark references",
            ["Model", "Success@1", "Build@1", "APR"],
            historical_rows,
        ),
        (
            "Current paper Python-to-Java references",
            ["Model", "SR", "CR", "APR", "AMPR"],
            current_rows,
        ),
    ]
    _write_report_files(
        root,
        key="repotransbench",
        abstract=abstract,
        sections=sections,
        tables=tables,
        figure=(
            ["Rep 1", "Rep 2", "Rep 3"],
            [
                (
                    "SR",
                    [100 * row["pass_all"] / row["subjects"] for row in summaries],
                    "#f58518",
                ),
                (
                    "CR",
                    [100 * row["builds"] / row["subjects"] for row in summaries],
                    "#4c78a8",
                ),
                (
                    "APR",
                    [row["average_pass_rate_percent"] for row in summaries],
                    "#54a24b",
                ),
            ],
        ),
        provenance={
            "generated_at": C.utcnow_iso(),
            "paper": PAPER_METADATA["repotransbench"],
            "artifact_repository": UPSTREAM_REPOSITORIES["repotransbench"],
            "artifact_head": UPSTREAM_COMMITS["repotransbench"],
            "artifact_v1_tag_commit": UPSTREAM_COMMITS["repotransbench_v1"],
            "source_commits": {
                row["name"]: row["source_commit"] for row in REPOTRANSBENCH_SUBJECTS
            },
            "source_repositories": {
                row["name"]: f"https://github.com/{row['name']}"
                for row in REPOTRANSBENCH_SUBJECTS
            },
            "protocol": PROTOCOL,
            "current_release_asset": "HTTP 404 during acquisition",
            "historical_source_archive": "Google Drive object unavailable",
        },
        availability=[
            {
                "surface": "three historical Python-to-Java subjects",
                "status": "measured",
                "reason": "licensed sources and meaningful released fixed tests",
                "measurement_track": "CodeWeaver three-repetition",
            },
            {
                "surface": "historical 100-project benchmark",
                "status": "subset_only",
                "reason": "advertised source archive unavailable",
                "measurement_track": "published v1 reference",
            },
            {
                "surface": "current 1,897-project benchmark",
                "status": "unavailable",
                "reason": "advertised release asset returned HTTP 404",
                "measurement_track": "published current-paper reference",
            },
            {
                "surface": "released scaffold/test redistribution",
                "status": "withheld",
                "reason": "no visible RepoTransBench repository-level license",
                "measurement_track": "path/hash manifest only",
            },
            {
                "surface": "pre-model launcher failures",
                "status": "excluded_with_evidence",
                "reason": "interpreter/wrapper failures occurred before model access",
                "measurement_track": "infrastructure-failure archive",
            },
        ],
    )
    return root


def build_rustrepotrans(output_root: Path, campaign_root: Path) -> Path:
    root = output_root / RESULT_NAMES["rustrepotrans"]
    rows = _load_new_rows(campaign_root / "evaluation" / "raw_runs.csv", 9)
    summaries = _new_repetition_summary(rows, RUSTREPOTRANS_SUBJECTS)
    prepared = {
        subject["id"]: C.read_json(
            campaign_root
            / "workspaces"
            / subject["id"]
            / "prepared.json"
        )
        for subject in RUSTREPOTRANS_SUBJECTS
    }
    exact_golden_cells = sum(
        bool(row.get("generated_function_sha256"))
        and row["generated_function_sha256"]
        == prepared[row["subject_id"]]["golden_target_sha256"]
        for row in rows
    )
    display_rows = [
        [
            f"CodeWeaver rep {row['repetition']}",
            f"{row['pipeline_terminal']}/{row['subjects']}",
            f"{row['pass_all']}/{row['subjects']} ({100*row['pass_all']/row['subjects']:.2f}%)",
            f"{row['builds']}/{row['subjects']} ({100*row['builds']/row['subjects']:.2f}%)",
            f"{row['tests_passed']}/{row['tests_expected']}",
            _percent(100 * row["tests_passed"] / row["tests_expected"]),
        ]
        for row in summaries
    ]
    paper_rows = [
        [row["model"], _percent(row["pass_at_1"]), _percent(row["dsr_at_1"])]
        for row in RUSTREPOTRANS_RQ1_REFERENCE
    ]
    artifact_reference_rows = [
        {
            **row,
            "source_kind": "released artifact RQ1 aggregation",
            "source_url": (
                "https://github.com/SYSUSELab/RustRepoTrans/tree/"
                f"{UPSTREAM_COMMITS['rustrepotrans']}/results/rq1"
            ),
            "paper_mapping": (
                "main RQ1 figure; Figure 5 in the cached 2026 paper revision "
                "and Figure 4 in arXiv v4"
            ),
        }
        for row in RUSTREPOTRANS_RQ1_REFERENCE
    ]
    subject_rows: list[list[Any]] = []
    for subject in RUSTREPOTRANS_SUBJECTS:
        selected = [row for row in rows if row["subject_id"] == subject["id"]]
        exact_matches = sum(
            bool(row.get("generated_function_sha256"))
            and row["generated_function_sha256"]
            == prepared[subject["id"]]["golden_target_sha256"]
            for row in selected
        )
        subject_rows.append(
            [
                subject["source_language"],
                subject["name"],
                f"{sum(_bool(row['build']) for row in selected)}/3",
                f"{sum(_bool(row['pass_all']) for row in selected)}/3",
                f"{sum(_number(row, 'tests_passed') for row in selected)}/{3*subject['expected_tests']}",
                f"{exact_matches}/3",
                subject["negative_control_failed_tests"],
            ]
        )
    C.write_csv(root / "data" / "raw_runs.csv", rows, list(rows[0]))
    C.write_csv(
        root / "data" / "repetition_summary.csv",
        summaries,
        list(summaries[0]),
    )
    obsolete_reference = root / "data" / "paper_table3.csv"
    if obsolete_reference.is_file():
        obsolete_reference.unlink()
    C.write_csv(
        root / "data" / "artifact_rq1_main_results.csv",
        artifact_reference_rows,
        _fieldnames(artifact_reference_rows),
    )
    C.write_csv(
        root / "data" / "subject_lock.csv",
        RUSTREPOTRANS_SUBJECTS,
        sorted({key for row in RUSTREPOTRANS_SUBJECTS for key in row}),
    )
    C.atomic_write_json(
        root / "data" / "summary.json",
        {
            "benchmark_tasks": 375,
            "selected_tasks": 3,
            "source_languages": ["C", "Java", "Python"],
            "measured_rows": len(rows),
            "build_cells": sum(_bool(row["build"]) for row in rows),
            "pass_all_cells": sum(_bool(row["pass_all"]) for row in rows),
            "pipeline_terminal_cells": sum(
                row.get("run_status") == "completed" for row in rows
            ),
            "byte_identical_to_withheld_golden_cells": exact_golden_cells,
            "golden_target_bodies_exposed_to_model": False,
        },
    )
    for source_name, destination_name in (
        ("raw_runs.jsonl", "raw_runs.jsonl"),
        ("summary.json", "evaluation_summary.json"),
    ):
        source = campaign_root / "evaluation" / source_name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, root / "data" / destination_name)
    generated = campaign_root / "evaluation" / "generated"
    if generated.exists():
        shutil.copytree(generated, root / "data" / "generated", dirs_exist_ok=True)
    logs = campaign_root / "evaluation" / "logs"
    if logs.exists():
        shutil.copytree(logs, root / "data" / "evaluation-logs", dirs_exist_ok=True)
    _copy_campaign_metadata_and_licenses(
        root, campaign_root, RUSTREPOTRANS_SUBJECTS
    )
    abstract = (
        "We selected one leakage-safe RustRepoTrans task per source language "
        "(C, Java, Python), ran three CodeWeaver repetitions, and evaluated each "
        "by replacing only the target function in a pristine licensed Rust "
        "project. Golden target bodies were hashed and excluded from every "
        "model-visible workspace. This 3/375-task slice measures feasibility and "
        "is not presented as a full-benchmark estimate."
    )
    sections = [
        (
            "Oracle calibration",
            "The pristine goldens pass 284, 284, and 64 fixed tests. Replacing "
            "the selected functions with compiling panic stubs causes 50, 73, "
            "and at least 13 failures respectively, demonstrating non-vacuous "
            "coverage of each selected function.",
        ),
        (
            "Metric boundary",
            "RustRepoTrans reports Pass@1 and one-round DSR@1 over 375 tasks. "
            "CodeWeaver is a multi-stage system with up to five repairs and three "
            "parity rounds. Its fixed-oracle pass-all rate is shown beside, but "
            "not relabeled as, Pass@1 or DSR@1.",
        ),
        (
            "Leakage audit",
            f"{exact_golden_cells}/9 generated functions are byte-identical to "
            "the withheld golden body. This is disclosed as an output property, "
            "not evidence of exposure: every golden was hashed and removed "
            "before model access, and the actual workspace exclusion check is "
            "recorded in prepared metadata.",
        ),
        (
            "Redistribution",
            "The RustRepoTrans repository has no visible repository-level "
            "license, so benchmark task text and full external projects are not "
            "redistributed. This artifact contains hashes, normalized outcomes, "
            "evaluation logs, and generated target functions under the target "
            "projects' MIT/Apache-2.0 licenses.",
        ),
    ]
    tables = [
        (
            "Measured stratified slice",
            [
                "Run",
                "Pipeline terminal",
                "Pass all",
                "Build",
                "Fixed tests",
                "Test rate",
            ],
            display_rows,
        ),
        (
            "Per-language selected tasks",
            [
                "Source",
                "Task",
                "Build cells",
                "Pass-all cells",
                "Tests",
                "Exact golden",
                "Stub failures",
            ],
            subject_rows,
        ),
        (
            "Released artifact RQ1 / paper main-figure references",
            ["Model", "Pass@1", "DSR@1"],
            paper_rows,
        ),
    ]
    _write_report_files(
        root,
        key="rustrepotrans",
        abstract=abstract,
        sections=sections,
        tables=tables,
        figure=(
            ["Rep 1", "Rep 2", "Rep 3"],
            [
                (
                    "Pass all",
                    [100 * row["pass_all"] / row["subjects"] for row in summaries],
                    "#f58518",
                ),
                (
                    "Build",
                    [100 * row["builds"] / row["subjects"] for row in summaries],
                    "#4c78a8",
                ),
                (
                    "Fixed tests",
                    [
                        100 * row["tests_passed"] / row["tests_expected"]
                        for row in summaries
                    ],
                    "#54a24b",
                ),
            ],
        ),
        provenance={
            "generated_at": C.utcnow_iso(),
            "paper": PAPER_METADATA["rustrepotrans"],
            "artifact_repository": UPSTREAM_REPOSITORIES["rustrepotrans"],
            "artifact_commit": UPSTREAM_COMMITS["rustrepotrans"],
            "reference_source": (
                "released results/rq1 aggregation at the pinned artifact commit; "
                "not paper Table 3"
            ),
            "protocol": PROTOCOL,
            "golden_target_policy": "hash then exclude before model access",
            "toolchain_note": (
                "incubator-milagro-crypto was evaluated with "
                "nightly-2025-09-15 because its artifact omitted Cargo.lock and "
                "current resolution exceeds declared rustc 1.77.1"
            ),
        },
        availability=[
            {
                "surface": "three language-stratified tasks",
                "status": "measured",
                "reason": "licensed target projects and non-vacuous fixed tests",
                "measurement_track": "CodeWeaver three-repetition",
            },
            {
                "surface": "full 375-task benchmark",
                "status": "not_measured",
                "reason": "bounded stratified reproduction",
                "measurement_track": "published reference only",
            },
            {
                "surface": "benchmark task redistribution",
                "status": "withheld",
                "reason": "no visible repository-level license",
                "measurement_track": "hash/provenance only",
            },
            {
                "surface": "pre-model launcher failures",
                "status": "excluded_with_evidence",
                "reason": "interpreter/wrapper failures occurred before model access",
                "measurement_track": "infrastructure-failure archive",
            },
        ],
    )
    return root


def build_all(
    *,
    historical_raw: Path,
    historical_manifest: Path,
    historical_runs_root: Path,
    campaign_root: Path,
    output_root: Path,
    clippy_csv: Path | None = None,
) -> list[Path]:
    raw_rows = _load_csv(historical_raw)
    manifest = C.read_json(historical_manifest)
    clippy_rows = _load_csv(clippy_csv) if clippy_csv is not None else None
    roots = [
        build_crust(output_root, raw_rows, manifest, clippy_rows),
        build_alphatrans(output_root, raw_rows),
        build_sactor(
            output_root,
            raw_rows,
            historical_runs_root,
            clippy_rows,
        ),
        build_repotransbench(output_root, campaign_root / "repotransbench"),
        build_rustrepotrans(output_root, campaign_root / "rustrepotrans"),
    ]
    return roots


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-raw", required=True)
    parser.add_argument("--historical-manifest", required=True)
    parser.add_argument("--historical-runs-root", required=True)
    parser.add_argument("--campaign-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--clippy-csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    roots = build_all(
        historical_raw=Path(args.historical_raw),
        historical_manifest=Path(args.historical_manifest),
        historical_runs_root=Path(args.historical_runs_root),
        campaign_root=Path(args.campaign_root),
        output_root=Path(args.output_root),
        clippy_csv=Path(args.clippy_csv) if args.clippy_csv else None,
    )
    print("\n".join(str(root) for root in roots))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
