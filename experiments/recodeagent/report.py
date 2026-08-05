"""report.py -- the final reproducibility_report.pdf/.md, computed strictly
from already-produced harness artifacts:

  - manifest.json           (manifest.py)
  - raw_runs.jsonl/failures.csv           (collect.py)
  - test_comparisons.jsonl/comparison_failures.csv  (test_compare.py, optional)
  - analysis_provenance.json              (analyze.py, optional but strongly
    recommended -- reused for schema/completeness/provenance-consistency
    rather than recomputed, so this module never re-implements analyze.py's
    validation logic)

This module measures NOTHING itself. It reads what those stages already
wrote, aggregates it into an execution-coverage picture and a blocker
breakdown, and renders a human-readable report plus a machine-readable
manifest/checksum/provenance JSON.

The one hard rule this module enforces: **it must never claim the
reproduction is complete unless every requested (variant, project,
repetition) cell in the protocol matrix has a measured row** in raw_runs (as
reported by analyze.py's own completeness computation). Short of that, the
report is always, unambiguously labeled "INCOMPLETE" with an itemized list of
what's missing and why -- this holds regardless of ``--require-complete``,
which only controls the process's *exit code*, never the report's wording.

Unlike analyze.py (which can be told to abort on ``--on-empty=fail``), this
module ALWAYS writes a report, even with zero measured data: "nothing has
been run yet" is itself a valid, honest thing to report.
"""
from __future__ import annotations

import argparse
import csv
import io
from collections import Counter
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent import render as RD
from experiments.recodeagent.common import atomic_write_text, read_jsonl, utcnow_iso

SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_manifest(path: str | Path) -> dict[str, Any]:
    return C.read_json(path)


def load_raw_runs_or_empty(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return read_jsonl(p)


def load_analysis_provenance(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return C.read_json(p)


def load_json_object(
    path: str | Path | None,
    *,
    label: str,
) -> dict[str, Any] | None:
    """Load an optional JSON input, rejecting non-object comparison evidence."""
    if path is None:
        return None
    value = C.read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return value


def read_failures_csv(path: str | Path | None) -> list[dict[str, Any]]:
    """Both collect.py's failures.csv and test_compare.py's
    test_comparison_failures.csv share the same column set, so one reader
    covers both."""
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
# Blocker aggregation -- groups failure rows by REASON CATEGORY (the text
# before the first ':', matching collect.py's/test_compare.py's own
# "category: details" reason convention) so many differently-detailed
# reasons collapse into one actionable count.
# --------------------------------------------------------------------------- #
def aggregate_blockers(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    example: dict[str, str] = {}
    for row in failures:
        reason = (row.get("reason") or "").strip()
        category = reason.split(":", 1)[0].strip() or "unknown"
        counter[category] += 1
        example.setdefault(category, reason)
    return [
        {"category": cat, "count": counter[cat], "example_reason": example[cat]}
        for cat in sorted(counter, key=lambda c: (-counter[c], c))
    ]


# --------------------------------------------------------------------------- #
# Coverage breakdown (variant x tool), computed directly from raw_runs so the
# report can show a granular "what's left" table even though
# analysis_provenance.json only carries the aggregate fraction + a flat
# missing-cells list.
# --------------------------------------------------------------------------- #
def compute_coverage_breakdown(
    manifest: dict[str, Any], raw_rows: list[dict[str, Any]], *, variants: list[str], repetitions: int = 1
) -> list[dict[str, Any]]:
    tool_counts: dict[str, int] = {}
    for p in manifest.get("projects", []):
        tool_counts[p.get("tool", "")] = tool_counts.get(p.get("tool", ""), 0) + 1
    measured_counts: dict[tuple[str, str], int] = {}
    for r in raw_rows:
        key = (r.get("variant"), r.get("tool"))
        measured_counts[key] = measured_counts.get(key, 0) + 1
    rows = []
    for variant in variants:
        for tool in sorted(tool_counts):
            expected = tool_counts[tool] * repetitions
            measured = measured_counts.get((variant, tool), 0)
            rows.append({
                "variant": variant, "tool": tool, "expected": expected, "measured": measured,
                "coverage_fraction": (measured / expected) if expected else None,
            })
    return rows


# --------------------------------------------------------------------------- #
# Completion verdict -- the one place this module is allowed to say
# "complete", and only when every check passes.
# --------------------------------------------------------------------------- #
def compute_completion_verdict(manifest: dict[str, Any], analysis_provenance: dict[str, Any] | None) -> dict[str, Any]:
    project_count = len(manifest.get("projects", []))
    reasons: list[str] = []
    if project_count != C.EXPECTED_TOTAL_PROJECTS:
        reasons.append(f"manifest has {project_count} project(s), expected {C.EXPECTED_TOTAL_PROJECTS}")

    if analysis_provenance is None:
        reasons.append("analyze.py has not been run yet (no analysis_provenance.json supplied) -- "
                       "completeness/schema/provenance cannot be verified")
        return {"complete": False, "reasons": reasons, "coverage_fraction": None}

    completeness = analysis_provenance.get("completeness", {}) or {}
    coverage_fraction = completeness.get("coverage_fraction")
    if coverage_fraction is None or coverage_fraction < 1.0:
        missing = completeness.get("missing_cells", []) or []
        reasons.append(
            f"raw_runs coverage_fraction is {coverage_fraction!r} (need 1.0); "
            f"{len(missing)} (variant, project, repetition) cell(s) are missing"
        )
    for label, key in (
        ("paper-aligned RQ2", "paper_test_completeness"),
        ("CodeWeaver-generated-test execution", "generated_test_completeness"),
    ):
        auxiliary = analysis_provenance.get(key, {}) or {}
        auxiliary_fraction = auxiliary.get("coverage_fraction")
        if auxiliary_fraction is None or auxiliary_fraction < 1.0:
            reasons.append(
                f"{label} coverage_fraction is {auxiliary_fraction!r} (need 1.0); "
                f"{len(auxiliary.get('missing_cells', []) or [])} cell(s) are missing"
            )
        if int(auxiliary.get("duplicate_rows") or 0):
            reasons.append(
                f"{label} contains {auxiliary['duplicate_rows']} duplicate project row(s)"
            )
    if not analysis_provenance.get("schema_valid", False):
        reasons.append("raw_runs/test_comparisons rows failed schema validation (see analysis_provenance.json)")
    if not (analysis_provenance.get("provenance_consistency", {}) or {}).get("consistent", False):
        reasons.append("measured runs used inconsistent model/git/toolchain provenance "
                       "(see analysis_provenance.json.provenance_consistency)")
    if not analysis_provenance.get("paper_tables_side_by_side_available", False):
        reasons.append(
            "exact paper Tables 1/2 side-by-side comparison is unavailable; "
            "rerun analyze.py with the official --paper-results-workbook"
        )

    return {"complete": not reasons, "reasons": reasons, "coverage_fraction": coverage_fraction}


# --------------------------------------------------------------------------- #
# Checksums + provenance JSON
# --------------------------------------------------------------------------- #
def compute_checksums(paths: dict[str, str | Path | None]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for label, path in paths.items():
        if path is None or not Path(path).exists():
            result[label] = {"path": str(path) if path else None, "exists": False, "sha256": None}
            continue
        p = Path(path)
        result[label] = {"path": str(p), "exists": True, "sha256": C.file_sha256(p), "size_bytes": p.stat().st_size}
    return result


def build_manifest_checksum_provenance(
    *, manifest_path: str | Path, raw_runs_path: str | Path | None, test_comparisons_path: str | Path | None,
    system_comparison_path: str | Path | None = None,
    system_comparison_provenance_path: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utcnow_iso(),
        "checksums": compute_checksums({
            "manifest": manifest_path, "raw_runs": raw_runs_path, "test_comparisons": test_comparisons_path,
            "system_comparison": system_comparison_path,
            "system_comparison_provenance": system_comparison_provenance_path,
        }),
        "report_generation_provenance": C.collect_provenance(probe_toolchains=False),
        "note": (
            "report_generation_provenance describes the machine/software that RENDERED this report, "
            "NOT the machine(s) that ran the CodeWeaver experiments -- per-run provenance (model, git SHA, "
            "Copilot CLI version, agent timeout) is recorded independently for every row in "
            "raw_runs.csv/raw_runs.jsonl by collect.py."
        ),
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _comparison_rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def summarize_system_comparison(
    system_comparison: dict[str, Any] | None,
    system_comparison_provenance: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract report-safe evidence from system_compare.py without recomputing it."""
    if system_comparison is not None and not isinstance(system_comparison, dict):
        raise ValueError("system comparison JSON must be an object")
    if (
        system_comparison_provenance is not None
        and not isinstance(system_comparison_provenance, dict)
    ):
        raise ValueError("system comparison provenance must be an object")
    if system_comparison is None and system_comparison_provenance is None:
        return None
    data = system_comparison or {}
    provenance = system_comparison_provenance or {}
    confounding = provenance.get("model_and_execution_confounding")
    swe_agent = provenance.get("swe_agent")
    caveat = (
        confounding.get("statement")
        if isinstance(confounding, dict) and isinstance(confounding.get("statement"), str)
        else (
            "Cross-system results compare fresh CodeWeaver runs with released-artifact "
            "replay and are not fresh matched-model reruns."
        )
    )
    swe_agent_statement = (
        swe_agent.get("statement")
        if isinstance(swe_agent, dict) and isinstance(swe_agent.get("statement"), str)
        else (
            "Released SWE-agent CRUST targets were not replayed. Any workbook value is a "
            "separate published-reference, non-replayed track."
        )
    )
    input_hashes = provenance.get("inputs_sha256")
    return {
        "available": system_comparison is not None,
        "provenance_available": system_comparison_provenance is not None,
        "tracks": [
            "fresh GPT-5.6 Sol CodeWeaver runs",
            "released-artifact ReCodeAgent/prior replay",
            "workbook-only published reference (non-replayed)",
        ],
        "model_system_design_caveat": caveat,
        "swe_agent_caveat": swe_agent_statement,
        "protocol": data.get("protocol") if isinstance(data.get("protocol"), dict) else {},
        "input_row_accounting": (
            data.get("input_row_accounting")
            if isinstance(data.get("input_row_accounting"), dict)
            else {}
        ),
        "inventory": _comparison_rows(data.get("inventory")),
        "codeweaver_three_repetition_all_tools": [
            row for row in _comparison_rows(data.get("codeweaver_repetition_summary"))
            if row.get("tool") == "all"
        ],
        "primary_rep0_paired_all_tools": [
            row for row in _comparison_rows(data.get("primary_paired_comparisons"))
            if row.get("tool") == "all"
        ],
        "crust_three_system_overlap": (
            data.get("crust_three_system_overlap")
            if isinstance(data.get("crust_three_system_overlap"), dict)
            else {}
        ),
        "cost_correctness_frontier": (
            data.get("cost_correctness_frontier")
            if isinstance(data.get("cost_correctness_frontier"), dict)
            else {}
        ),
        "input_hashes": input_hashes if isinstance(input_hashes, dict) else {},
    }


def build_report(
    *,
    manifest: dict[str, Any],
    analysis_provenance: dict[str, Any] | None,
    failures: list[dict[str, Any]],
    comparison_failures: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    variants: list[str],
    repetitions: int = 1,
    system_comparison: dict[str, Any] | None = None,
    system_comparison_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utcnow_iso(),
        "verdict": compute_completion_verdict(manifest, analysis_provenance),
        "blockers": aggregate_blockers(failures),
        "comparison_blockers": aggregate_blockers(comparison_failures),
        "coverage_breakdown": compute_coverage_breakdown(manifest, raw_rows, variants=variants,
                                                        repetitions=repetitions),
        "project_count": len(manifest.get("projects", [])),
        "expected_total_projects": C.EXPECTED_TOTAL_PROJECTS,
        "raw_runs_row_count": len(raw_rows),
        "analysis_available": analysis_provenance is not None,
        "paper_tables_side_by_side_available": bool(
            (analysis_provenance or {}).get(
                "paper_tables_side_by_side_available", False
            )
        ),
        "system_comparison": summarize_system_comparison(
            system_comparison, system_comparison_provenance,
        ),
    }


def render_report_sections(report_data: dict[str, Any]) -> list[RD.ReportSection]:
    verdict = report_data["verdict"]
    status_word = "COMPLETE" if verdict["complete"] else "INCOMPLETE"
    verdict_text = f"Status: {status_word}\nCoverage fraction (raw_runs / full requested matrix): {verdict['coverage_fraction']!r}\n"
    if verdict["reasons"]:
        verdict_text += "\nUnmet criteria:\n" + "\n".join(f"  - {r}" for r in verdict["reasons"])
    else:
        verdict_text += "\nAll completion criteria met."

    sections = [
        RD.ReportSection("Completion Verdict", verdict_text, level=2),
        RD.ReportSection(
            "Manifest",
            f"{report_data['project_count']} / {report_data['expected_total_projects']} projects discovered.",
            level=2,
        ),
    ]

    if report_data["coverage_breakdown"]:
        headers = ["variant", "tool", "expected", "measured", "coverage_fraction"]
        rows = [[r[h] for h in headers] for r in report_data["coverage_breakdown"]]
        sections.append(RD.ReportSection("Execution Coverage (raw_runs, by variant x tool)",
                                        RD.markdown_table(headers, rows), level=2))
    else:
        sections.append(RD.ReportSection("Execution Coverage (raw_runs, by variant x tool)",
                                        "No raw_runs data supplied.", level=2))

    if report_data["blockers"]:
        headers = ["category", "count", "example_reason"]
        rows = [[r[h] for h in headers] for r in report_data["blockers"]]
        sections.append(RD.ReportSection("Blockers (collect.py failures.csv)",
                                        RD.markdown_table(headers, rows), level=2))
    else:
        sections.append(RD.ReportSection("Blockers (collect.py failures.csv)",
                                        "No failures recorded (or failures.csv was not supplied).", level=2))

    if report_data["comparison_blockers"]:
        headers = ["category", "count", "example_reason"]
        rows = [[r[h] for h in headers] for r in report_data["comparison_blockers"]]
        sections.append(RD.ReportSection("Blockers (test_compare.py comparison_failures.csv)",
                                        RD.markdown_table(headers, rows), level=2))
    else:
        sections.append(RD.ReportSection(
            "Blockers (test_compare.py comparison_failures.csv)",
            "No failures recorded (or test_compare.py has not been run / comparison_failures.csv "
            "was not supplied).", level=2,
        ))

    sections.append(RD.ReportSection(
        "Analysis Availability",
        ("analyze.py has been run; table1_effectiveness/table2_test_translation/figure7_ablation/"
        "figure8_cost_tools are available in the analysis output root. "
        + (
            "The exact paper_table1_side_by_side.csv, paper_table2_side_by_side.csv, and "
            "paper_tables_side_by_side.pdf comparison artifacts are also available."
            if report_data["paper_tables_side_by_side_available"]
            else
            "The exact paper Tables 1/2 side-by-side comparison is unavailable."
        )) if report_data["analysis_available"]
        else "analyze.py has NOT been run yet -- table1/table2/figure7/figure8 are not available.",
        level=2,
    ))
    comparison = report_data.get("system_comparison")
    if isinstance(comparison, dict):
        tracks = "\n".join(f"  - {track}" for track in comparison["tracks"])
        sections.append(RD.ReportSection(
            "Cross-System Comparison: Design and Tracks",
            (
                "Tracks:\n" + tracks + "\n\n"
                + comparison["model_system_design_caveat"] + "\n\n"
                + comparison["swe_agent_caveat"] + "\n\n"
                + "Unavailable costs remain unavailable and are never treated as zero."
            ),
            level=2,
        ))

        inventory = comparison["inventory"]
        inventory_headers = [
            "system", "tool", "repetition", "expected", "measured",
            "unavailable", "error", "missing", "accounted_missing",
            "unaccounted_missing", "status",
        ]
        sections.append(RD.ReportSection(
            "Cross-System Comparison: Inventory and Completeness",
            RD.markdown_table(
                inventory_headers,
                [[row.get(header, "") for header in inventory_headers] for row in inventory],
            ) if inventory else "No system-comparison inventory rows were available.",
            level=2,
        ))

        repetition_rows = comparison["codeweaver_three_repetition_all_tools"]
        repetition_headers = ["metric", "n", "mean", "sample_sd", "ci_95_t", "status", "reason"]
        sections.append(RD.ReportSection(
            "Cross-System Comparison: CodeWeaver Three-Repetition All-Tools Summary",
            RD.markdown_table(
                repetition_headers,
                [[row.get(header, "") for header in repetition_headers] for row in repetition_rows],
            ) if repetition_rows else "No all-tools CodeWeaver repetition summary was available.",
            level=2,
        ))

        paired_rows = comparison["primary_rep0_paired_all_tools"]
        paired_headers = [
            "metric", "n", "cw_yes_rca_no_wins", "rca_yes_cw_no_losses",
            "cw_wins", "rca_losses", "ties", "delta_percentage_points",
            "mean_delta_percentage_points", "exact_mcnemar_p_value",
        ]
        sections.append(RD.ReportSection(
            "Cross-System Comparison: Primary Rep-0 Paired All-Tools Results",
            RD.markdown_table(
                paired_headers,
                [[row.get(header, "") for header in paired_headers] for row in paired_rows],
            ) if paired_rows else "No paired all-tools CodeWeaver vs ReCodeAgent rows were available.",
            level=2,
        ))

        overlap = comparison["crust_three_system_overlap"]
        overlap_cells = _comparison_rows(overlap.get("cells")) if overlap else []
        overlap_headers = [
            "codeweaver_rep0", "recodeagent_replay", "swe_agent_workbook",
            "count", "swe_agent_track",
        ]
        overlap_text = (
            f"Status: {overlap.get('status', 'unavailable')}; "
            f"triples: {overlap.get('n_triples', 0)}. "
            f"{overlap.get('reason', '')}"
        ) if overlap else "No CRUST overlap result was available."
        if overlap_cells:
            overlap_text += "\n\n" + RD.markdown_table(
                overlap_headers,
                [[cell.get(header, "") for header in overlap_headers] for cell in overlap_cells],
            )
        sections.append(RD.ReportSection(
            "Cross-System Comparison: CRUST Three-System Overlap",
            overlap_text,
            level=2,
        ))

        frontier = comparison["cost_correctness_frontier"]
        frontier_rows = _comparison_rows(frontier.get("rows")) if frontier else []
        frontier_headers = [
            "system", "track", "cost_status", "mean_actual_cost",
            "n_cost_projects", "cost_missing_projects", "correctness_status",
            "project_pass_all_rate",
        ]
        frontier_text = (
            f"Status: {frontier.get('status', 'unavailable')}. "
            f"{frontier.get('reason', '')}"
        ) if frontier else "No measured cost/correctness frontier was available."
        if frontier_rows:
            frontier_text += "\n\n" + RD.markdown_table(
                frontier_headers,
                [[row.get(header, "") for header in frontier_headers] for row in frontier_rows],
            )
        sections.append(RD.ReportSection(
            "Cross-System Comparison: Measured Cost/Correctness Frontier",
            frontier_text + "\n\nMissing or unavailable cost is not zero and is excluded from the measured frontier.",
            level=2,
        ))
    return sections


def write_report(report_data: dict[str, Any], output_root: Path) -> dict[str, Path]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    sections = render_report_sections(report_data)
    title = "ReCodeAgent / CodeWeaver Reproducibility Report"
    md_path = RD.write_markdown_report(title, sections, output_root / "reproducibility_report.md")
    pdf_path = output_root / "reproducibility_report.pdf"
    RD.render_pdf_report(title, sections, pdf_path)
    data_path = output_root / "reproducibility_report_data.json"
    C.atomic_write_json(data_path, report_data)
    return {"markdown": md_path, "pdf": pdf_path, "data": data_path}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="report.py",
        description="Final reproducibility_report.pdf/.md + manifest/checksum/provenance JSON.",
    )
    ap.add_argument("--manifest", required=True, help="path to manifest.json (from manifest.py)")
    ap.add_argument("--raw-runs", default=None, help="path to raw_runs.jsonl (from collect.py); optional")
    ap.add_argument("--failures", default=None, help="path to failures.csv (from collect.py); optional")
    ap.add_argument("--test-comparisons", default=None,
                    help="path to test_comparisons.jsonl (from test_compare.py); optional, checksum only")
    ap.add_argument("--comparison-failures", default=None,
                    help="path to test_comparison_failures.csv (from test_compare.py); optional")
    ap.add_argument("--analysis-provenance", default=None,
                    help="path to analysis_provenance.json (from analyze.py); strongly recommended")
    ap.add_argument("--system-comparison", default=None,
                    help="path to system_comparison.json (from compare-systems); optional")
    ap.add_argument("--system-comparison-provenance", default=None,
                    help="path to system_comparison_provenance.json (from compare-systems); optional")
    ap.add_argument("--output-root", required=True, help="where the report + checksum JSON are written")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--variant", default="all", help="comma-separated variants, or 'all' (default)")
    ap.add_argument("--repetitions", type=int, default=None, help="default: [protocol].repetitions")
    ap.add_argument("--require-complete", action="store_true",
                    help="exit non-zero if the completion verdict is INCOMPLETE (the report's WORDING "
                        "already never claims completion regardless of this flag)")
    return ap


def _parse_variants(raw: str) -> list[str]:
    if raw == "all":
        return list(C.RUN_VARIANTS)
    variants = [v.strip() for v in raw.split(",") if v.strip()]
    for v in variants:
        if v not in C.RUN_VARIANTS:
            raise ValueError(f"unknown variant {v!r}; choose from {C.RUN_VARIANTS}")
    return variants


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from experiments.recodeagent import manifest as M
    cfg = M.load_experiment_config(args.config)
    manifest = load_manifest(args.manifest)
    raw_rows = load_raw_runs_or_empty(args.raw_runs)
    failures = read_failures_csv(args.failures)
    comparison_failures = read_failures_csv(args.comparison_failures)
    analysis_provenance = load_analysis_provenance(args.analysis_provenance)
    system_comparison = load_json_object(
        args.system_comparison, label="system comparison JSON",
    )
    system_comparison_provenance = load_json_object(
        args.system_comparison_provenance, label="system comparison provenance",
    )
    variants = _parse_variants(args.variant)
    repetitions = (args.repetitions if args.repetitions is not None
                  else int(cfg.get("protocol", {}).get("repetitions", 1)))

    report_data = build_report(
        manifest=manifest, analysis_provenance=analysis_provenance, failures=failures,
        comparison_failures=comparison_failures, raw_rows=raw_rows, variants=variants, repetitions=repetitions,
        system_comparison=system_comparison,
        system_comparison_provenance=system_comparison_provenance,
    )
    output_root = Path(args.output_root)
    paths = write_report(report_data, output_root)
    checksum_provenance = build_manifest_checksum_provenance(
        manifest_path=args.manifest, raw_runs_path=args.raw_runs, test_comparisons_path=args.test_comparisons,
        system_comparison_path=args.system_comparison,
        system_comparison_provenance_path=args.system_comparison_provenance,
    )
    checksum_path = output_root / "manifest_checksum_provenance.json"
    C.atomic_write_json(checksum_path, checksum_provenance)

    verdict = report_data["verdict"]
    status_word = "COMPLETE" if verdict["complete"] else "INCOMPLETE"
    print(f"[report] verdict={status_word} coverage_fraction={verdict['coverage_fraction']!r}")
    print(f"[report] wrote {paths['markdown']}")
    print(f"[report] wrote {paths['pdf']}")
    print(f"[report] wrote {checksum_path}")

    if args.require_complete and not verdict["complete"]:
        print("[report] --require-complete set and verdict is INCOMPLETE -- exiting non-zero")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
