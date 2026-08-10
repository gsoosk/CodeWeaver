"""Render a conference-style narrative from the verified reproduction outputs.

This stage does not recompute measurements. It combines the completeness-gated
report, cross-system statistics, and analysis provenance into human-readable
Markdown/PDF plus a compilation-ready LaTeX draft.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent import render as RD


DEFAULT_TITLE = (
    "CodeWeaver with GPT-5.6 Sol: A Reproducible Evaluation on the "
    "ReCodeAgent Benchmark"
)


def _load_object(path: str | Path, *, label: str) -> dict[str, Any]:
    value = C.read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _percent(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "--"
    return f"{100.0 * float(value):.1f}%"


def _interval(value: Any) -> str:
    if not isinstance(value, list) or len(value) != 2:
        return "--"
    return f"[{_percent(value[0])}, {_percent(value[1])}]"


def _primary_metrics(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in comparison.get("codeweaver_per_repetition_metrics", [])
        if row.get("tool") == "all" and row.get("repetition") == 0
    ]


def _variability_metrics(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in comparison.get("codeweaver_repetition_summary", [])
        if row.get("tool") == "all"
    ]


def _paired_metrics(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in comparison.get("primary_paired_comparisons", [])
        if row.get("tool") == "all"
    ]


def _inventory_totals(comparison: dict[str, Any]) -> list[list[Any]]:
    totals: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    for row in comparison.get("inventory", []):
        key = (str(row.get("system")), int(row.get("repetition", 0)))
        for field in (
            "expected",
            "measured",
            "accounted_missing",
            "unaccounted_missing",
            "error",
        ):
            totals[key][field] += int(row.get(field, 0))
    return [
        [
            system,
            repetition,
            counts["expected"],
            counts["measured"],
            counts["accounted_missing"],
            counts["unaccounted_missing"],
            counts["error"],
        ]
        for (system, repetition), counts in sorted(totals.items())
    ]


def build_sections(
    report_data: dict[str, Any],
    comparison: dict[str, Any],
    analysis_provenance: dict[str, Any],
) -> list[RD.ReportSection]:
    verdict = report_data.get("verdict") or {}
    complete = bool(verdict.get("complete"))
    project_count = report_data.get("project_count")
    protocol = comparison.get("protocol") or {}
    repetitions = protocol.get("configured_codeweaver_repetitions")
    primary = _primary_metrics(comparison)
    variability = _variability_metrics(comparison)
    paired = _paired_metrics(comparison)

    abstract = (
        f"We evaluate CodeWeaver with GPT-5.6 Sol on the {project_count}-project "
        "benchmark released with ReCodeAgent (arXiv:2604.07341). The protocol "
        f"uses {repetitions} repetitions; repetition 0 is preregistered as the "
        "primary comparison and repetitions 0--2 estimate variability. Every "
        "CodeWeaver output is evaluated by a fixed post-hoc oracle, while "
        "ReCodeAgent and prior systems are replayed from released artifacts. "
        f"Artifact completeness status: {'COMPLETE' if complete else 'INCOMPLETE'}. "
        "No best-of-three selection, unavailable artifact substitution, or "
        "success-shaped fallback is used."
    )

    primary_rows = [
        [
            row.get("metric"),
            row.get("n_projects"),
            _percent(row.get("value")),
            _interval((row.get("bootstrap") or {}).get("ci_95")),
            row.get("excluded_projects"),
            row.get("status"),
        ]
        for row in primary
    ]
    variability_rows = [
        [
            row.get("metric"),
            row.get("n"),
            _percent(row.get("mean")),
            _percent(row.get("sample_sd")),
            _interval(row.get("ci_95_t")),
            row.get("status"),
        ]
        for row in variability
    ]
    paired_rows = []
    for row in paired:
        delta = (
            row.get("delta_percentage_points")
            if row.get("metric_kind") == "binary"
            else row.get("mean_delta_percentage_points")
        )
        paired_rows.append(
            [
                row.get("metric"),
                row.get("n"),
                row.get("cw_yes_rca_no_wins", row.get("cw_wins")),
                row.get("rca_yes_cw_no_losses", row.get("rca_losses")),
                row.get("ties"),
                "--" if delta is None else f"{float(delta):.1f}",
                row.get("exact_mcnemar_p_value")
                if row.get("metric_kind") == "binary"
                else (row.get("wilcoxon") or {}).get("p_value"),
            ]
        )

    completeness = comparison.get("inventory_completeness") or {}
    overlap = comparison.get("crust_three_system_overlap") or {}
    frontier = comparison.get("cost_correctness_frontier") or {}
    unmet = verdict.get("reasons") or []
    verdict_body = (
        f"Status: {'COMPLETE' if complete else 'INCOMPLETE'}\n"
        f"Coverage fraction: {verdict.get('coverage_fraction')!r}\n"
        f"Unaccounted system cells: "
        f"{completeness.get('unaccounted_missing', '--')}\n"
        f"System error cells: {completeness.get('error', '--')}"
    )
    if unmet:
        verdict_body += "\n\nUnmet criteria:\n" + "\n".join(f"- {reason}" for reason in unmet)

    return [
        RD.ReportSection("Abstract", abstract),
        RD.ReportSection(
            "Evaluation design",
            "Benchmark: 100 CRUST, 6 Oxidizer, 4 AlphaTrans, and 8 SKEL "
            "projects across C-to-Rust, Go-to-Rust, Java-to-Python, and "
            "Python-to-JavaScript. CodeWeaver runs use gpt-5.6-sol with maximum "
            "reasoning effort, five repair iterations, three parity rounds, "
            "and a 5,000-second agent timeout. Released baseline outputs are "
            "evaluated by the same normalized collector where artifacts exist.",
        ),
        RD.ReportSection("Artifact completion and claim boundary", verdict_body),
        RD.ReportSection(
            "Evidence inventory",
            RD.markdown_table(
                [
                    "system",
                    "rep",
                    "expected",
                    "measured",
                    "accounted missing",
                    "unaccounted missing",
                    "error",
                ],
                _inventory_totals(comparison),
            ),
        ),
        RD.ReportSection(
            "RQ1: Primary CodeWeaver effectiveness (repetition 0)",
            RD.markdown_table(
                ["metric", "n", "value", "95% bootstrap CI", "excluded", "status"],
                primary_rows,
            ),
        ),
        RD.ReportSection(
            "RQ1: Three-repetition variability",
            RD.markdown_table(
                ["metric", "n reps", "mean", "sample SD", "95% t CI", "status"],
                variability_rows,
            ),
        ),
        RD.ReportSection(
            "RQ1: Primary paired comparison with ReCodeAgent",
            RD.markdown_table(
                ["metric", "n", "CW wins", "RCA wins", "ties", "delta pp", "p"],
                paired_rows,
            ),
        ),
        RD.ReportSection(
            "RQ2: Test translation and exact paper tables",
            "The package includes project-level official-comparator evidence, "
            "heuristic per-test mappings, translated/generated-test summaries, "
            "and paper_tables_side_by_side.pdf. Paper and CodeWeaver values "
            "retain separate provenance/status fields. Exact-table availability: "
            f"{analysis_provenance.get('paper_tables_side_by_side_available', False)}.",
        ),
        RD.ReportSection(
            "RQ3 and RQ4",
            "The Full CodeWeaver protocol is the measured cross-system treatment. "
            "No missing CodeWeaver ablation is inferred from the ReCodeAgent paper. "
            "Cost, duration, token, premium-request, tool-use, and coverage evidence "
            "appear in figure8_cost_tools and the normalized raw rows. Measured "
            f"cost/correctness frontier status: {frontier.get('status', 'unavailable')}.",
        ),
        RD.ReportSection(
            "CRUST three-system overlap",
            f"Status: {overlap.get('status', 'unavailable')}; "
            f"triples: {overlap.get('n_triples', 0)}. "
            f"{overlap.get('reason', '')}",
        ),
        RD.ReportSection(
            "Threats to validity",
            "CodeWeaver and the released baselines are not model-matched fresh "
            "reruns; the comparison is observational at the system level. "
            "Released SWE-agent CRUST targets are unavailable, so workbook values "
            "are labeled published_reference_non_replayed and never treated as "
            "replayed artifacts. Missing and unavailable costs are not zero. "
            "The preregistered repetition prevents post-hoc run selection.",
        ),
        RD.ReportSection(
            "Artifact and reproducibility",
            "The result tree contains normalized CSV/JSON/JSONL data, exact paper "
            "tables, figures, statistical tests, LaTeX, PDFs, source snapshot, "
            "filtered raw-run archives, infrastructure-failure audits, campaign "
            "metadata, and SHA-256 checksums. Official benchmark artifacts are "
            "referenced by pinned identifiers and checksums rather than redistributed.",
        ),
    ]


def _latex_escape(value: Any) -> str:
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
    return "".join(replacements.get(character, character) for character in str(value))


def build_latex(
    *,
    title: str,
    report_data: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    verdict = report_data.get("verdict") or {}
    rows = _primary_metrics(comparison)
    table_rows = "\n".join(
        f"{_latex_escape(row.get('metric'))} & {row.get('n_projects', '--')} & "
        f"{_latex_escape(_percent(row.get('value')))} & "
        f"{_latex_escape(_interval((row.get('bootstrap') or {}).get('ci_95')))} \\\\"
        for row in rows
    )
    return rf"""\documentclass[10pt,twocolumn]{{article}}
\usepackage[margin=0.75in]{{geometry}}
\usepackage{{booktabs,graphicx,hyperref,xcolor}}
\title{{{_latex_escape(title)}}}
\author{{CodeWeaver Evaluation Artifact}}
\date{{}}
\begin{{document}}
\maketitle
\begin{{abstract}}
We reproduce the 118-project ReCodeAgent evaluation for CodeWeaver with
GPT-5.6 Sol using three repetitions and independent fixed-oracle validation.
Artifact status is \textbf{{{'COMPLETE' if verdict.get('complete') else 'INCOMPLETE'}}};
repetition 0 is the preregistered primary result and no best-of-three selection
is performed.
\end{{abstract}}
\section{{Evaluation Design}}
The benchmark contains CRUST, Oxidizer, AlphaTrans, and SKEL projects spanning
four source-target language pairs. Released baseline artifacts are replayed
through the same normalized evaluator; unavailable evidence remains explicit.
\section{{Primary Results}}
\begin{{table}}[t]
\centering
\small
\begin{{tabular}}{{lrrr}}
\toprule
Metric & $n$ & Value & 95\% CI \\
\midrule
{table_rows}
\bottomrule
\end{{tabular}}
\caption{{Preregistered CodeWeaver repetition-0 results.}}
\end{{table}}
\IfFileExists{{../system-comparison/system_comparison_tables.tex}}{{%
\input{{../system-comparison/system_comparison_tables.tex}}}}{{}}
\section{{Test Translation, Cost, and Process Evidence}}
Exact paper Tables 1 and 2 with distinct CodeWeaver provenance are distributed
as \texttt{{../analysis/paper\_tables\_side\_by\_side.pdf}}. RQ2 project-level
evidence, RQ4 token/cost/tool summaries, and all normalized rows are included
in the artifact.
\section{{Threats to Validity}}
The systems are not model-matched fresh reruns. SWE-agent released targets are
unavailable; workbook values are reference-only. Missing costs are not zero.
\section{{Reproducibility}}
The package contains source, raw normalized evidence, filtered run archives,
provenance, infrastructure audits, and SHA-256 checksums.
\begin{{thebibliography}}{{1}}
\bibitem{{recodeagent}} A. R. Ibrahimzada, B. Paulsen, D. Kroening, and
R. Jabbarvand. ReCodeAgent: A Multi-Agent Workflow for Language-agnostic
Translation and Validation of Large-scale Repositories. arXiv:2604.07341, 2026.
\end{{thebibliography}}
\end{{document}}
"""


def generate_conference_paper(
    *,
    report_data_path: str | Path,
    system_comparison_path: str | Path,
    analysis_provenance_path: str | Path,
    output_root: str | Path,
    title: str = DEFAULT_TITLE,
    require_complete: bool = False,
) -> dict[str, Any]:
    report_path = Path(report_data_path)
    comparison_path = Path(system_comparison_path)
    analysis_path = Path(analysis_provenance_path)
    output = Path(output_root)
    report_data = _load_object(report_path, label="report data")
    comparison = _load_object(comparison_path, label="system comparison")
    analysis = _load_object(analysis_path, label="analysis provenance")
    complete = bool((report_data.get("verdict") or {}).get("complete"))
    if require_complete and not complete:
        reasons = (report_data.get("verdict") or {}).get("reasons") or []
        raise RuntimeError(
            "refusing to render a complete conference paper from incomplete evidence: "
            + "; ".join(str(reason) for reason in reasons)
        )

    sections = build_sections(report_data, comparison, analysis)
    output.mkdir(parents=True, exist_ok=True)
    markdown_path = output / "conference_paper.md"
    pdf_path = output / "conference_paper.pdf"
    latex_path = output / "conference_paper.tex"
    data_path = output / "conference_paper_data.json"
    provenance_path = output / "conference_paper_provenance.json"
    RD.write_markdown_report(title, sections, markdown_path)
    if not RD.render_pdf_report(title, sections, pdf_path):
        raise RuntimeError("reportlab is required to render conference_paper.pdf")
    C.atomic_write_text(
        latex_path,
        build_latex(title=title, report_data=report_data, comparison=comparison),
    )
    C.atomic_write_json(
        data_path,
        {
            "schema_version": 1,
            "title": title,
            "complete": complete,
            "primary_metrics": _primary_metrics(comparison),
            "variability_metrics": _variability_metrics(comparison),
            "paired_metrics": _paired_metrics(comparison),
            "inventory_completeness": comparison.get("inventory_completeness"),
            "crust_three_system_overlap": comparison.get("crust_three_system_overlap"),
            "cost_correctness_frontier": comparison.get("cost_correctness_frontier"),
        },
    )
    C.atomic_write_json(
        provenance_path,
        {
            "schema_version": 1,
            "generated_at": C.utcnow_iso(),
            "inputs_sha256": {
                "report_data": C.file_sha256(report_path),
                "system_comparison": C.file_sha256(comparison_path),
                "analysis_provenance": C.file_sha256(analysis_path),
            },
            "outputs": {
                "markdown": markdown_path.name,
                "pdf": pdf_path.name,
                "latex": latex_path.name,
                "data": data_path.name,
            },
            "claim_boundary": (
                "Complete is asserted only when the upstream report verdict is complete; "
                "all measurements and statistical results are copied, not recomputed."
            ),
        },
    )
    return {
        "complete": complete,
        "markdown": markdown_path,
        "pdf": pdf_path,
        "latex": latex_path,
        "data": data_path,
        "provenance": provenance_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render conference_paper.{md,pdf,tex} from verified reproduction outputs."
    )
    parser.add_argument("--report-data", required=True)
    parser.add_argument("--system-comparison", required=True)
    parser.add_argument("--analysis-provenance", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = generate_conference_paper(
        report_data_path=args.report_data,
        system_comparison_path=args.system_comparison,
        analysis_provenance_path=args.analysis_provenance,
        output_root=args.output_root,
        title=args.title,
        require_complete=args.require_complete,
    )
    print(
        f"[conference-paper] complete={result['complete']} -> "
        f"{result['pdf']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
