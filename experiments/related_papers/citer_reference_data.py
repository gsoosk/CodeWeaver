"""Structured reference values for newly audited CRUST-Bench citers."""
from __future__ import annotations

from typing import Any


CITER_REFERENCE_TABLES: dict[str, list[dict[str, Any]]] = {
    "orbit_table1_scale.csv": [
        {"system": "RustMap", "dataset": "Rosetta Code, Bzip2", "programs": 126, "percent_over_1kloc": "~1", "median_loc": "~80", "mean_loc": "~145"},
        {"system": "Syzygy", "dataset": "Zopfli, URL parser", "programs": 2, "percent_over_1kloc": "50", "median_loc": "2700", "mean_loc": "2700"},
        {"system": "EvoC2Rust", "dataset": "C2R-Bench, Vivo-Bench", "programs": 25, "percent_over_1kloc": "~8", "median_loc": "~400", "mean_loc": "~600"},
        {"system": "RustAssure", "dataset": "5 C libraries", "programs": 5, "percent_over_1kloc": "20", "median_loc": "405", "mean_loc": "~900"},
        {"system": "SmartC2Rust", "dataset": "GitHub, prior studies", "programs": 21, "percent_over_1kloc": "~24", "median_loc": "502", "mean_loc": "~1000"},
        {"system": "VERT", "dataset": "TransCoder-IR", "programs": 534, "percent_over_1kloc": "0", "median_loc": "~100", "mean_loc": "~120"},
        {"system": "ORBIT", "dataset": "CRUST-Bench", "programs": 24, "percent_over_1kloc": "91.7", "median_loc": "1354", "mean_loc": "1603"},
    ],
    "orbit_table4_safety_summary.csv": [
        {"system": "C2Rust", "scope": "15 compiling projects", "mean_unsafe_percent": 69.6, "zero_unsafe_projects": "", "pointer_declarations": "", "pointer_dereferences": "", "note": "range 20.4%-97.4%"},
        {"system": "CRUST-Bench", "scope": "11 compiling projects", "mean_unsafe_percent": 0.68, "zero_unsafe_projects": 8, "pointer_declarations": "", "pointer_dereferences": "", "note": "nonzero: razz_simulation, lambda-calculus-eval, libm17"},
        {"system": "ORBIT expert", "scope": "24 projects", "mean_unsafe_percent": 0.06, "zero_unsafe_projects": 19, "pointer_declarations": 35, "pointer_dereferences": 5, "note": ""},
        {"system": "ORBIT generated", "scope": "24 projects", "mean_unsafe_percent": 0.11, "zero_unsafe_projects": 21, "pointer_declarations": 58, "pointer_dereferences": 6, "note": ""},
    ],
    "orbit_table5_tractor.csv": [
        {"kind": "exec", "program": "016_switch-arith", "performers_passing": 3, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "exec", "program": "042_float_union", "performers_passing": 3, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "exec", "program": "033_bitfield", "performers_passing": 3, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "exec", "program": "030_int_underflow", "performers_passing": 2, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "exec", "program": "002_stdin_echo", "performers_passing": 3, "performers_total": 6, "orbit_result": "Partial", "vector_pass_percent": 75},
        {"kind": "lib", "program": "read_scalefactors_lib", "performers_passing": 3, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "lib", "program": "004_loop_lib", "performers_passing": 2, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "lib", "program": "read_side_info_lib", "performers_passing": 4, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "lib", "program": "wcscat_lib", "performers_passing": 4, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "lib", "program": "update_frame_header_lib", "performers_passing": 4, "performers_total": 6, "orbit_result": "Pass", "vector_pass_percent": 100},
        {"kind": "lib", "program": "030_int_underflow_lib", "performers_passing": 2, "performers_total": 6, "orbit_result": "Fail", "vector_pass_percent": 0},
        {"kind": "lib", "program": "contrast_ratio_lib", "performers_passing": 3, "performers_total": 6, "orbit_result": "Partial", "vector_pass_percent": 62.5},
        {"kind": "lib", "program": "hex2bin_lib", "performers_passing": 2, "performers_total": 6, "orbit_result": "Fail", "vector_pass_percent": 0},
    ],
    "orbit_table6_ablation.csv": [
        {"project": "CircularBuffer", "configuration": "base", "function_coverage_percent": 100, "test_coverage_percent": 0, "build": True, "test": True},
        {"project": "CircularBuffer", "configuration": "without interface", "function_coverage_percent": 100, "test_coverage_percent": 90.9, "build": True, "test": True},
        {"project": "CircularBuffer", "configuration": "without mapping", "function_coverage_percent": 100, "test_coverage_percent": "", "build": True, "test": True},
        {"project": "CircularBuffer", "configuration": "full", "function_coverage_percent": 100, "test_coverage_percent": "", "build": True, "test": True},
        {"project": "LTRE", "configuration": "base", "function_coverage_percent": 64.4, "test_coverage_percent": 3.0, "build": True, "test": True},
        {"project": "LTRE", "configuration": "without interface", "function_coverage_percent": 82.2, "test_coverage_percent": 12.2, "build": True, "test": True},
        {"project": "LTRE", "configuration": "without mapping", "function_coverage_percent": 93.3, "test_coverage_percent": "", "build": True, "test": True},
        {"project": "LTRE", "configuration": "full", "function_coverage_percent": 100, "test_coverage_percent": "", "build": True, "test": False},
        {"project": "libm17", "configuration": "base", "function_coverage_percent": 84.1, "test_coverage_percent": 0, "build": False, "test": False},
        {"project": "libm17", "configuration": "without interface", "function_coverage_percent": 100, "test_coverage_percent": 100, "build": True, "test": True},
        {"project": "libm17", "configuration": "without mapping", "function_coverage_percent": 100, "test_coverage_percent": "", "build": True, "test": True},
        {"project": "libm17", "configuration": "full", "function_coverage_percent": 100, "test_coverage_percent": "", "build": True, "test": True},
    ],
    "actor_schesch_figure6_crust.csv": [
        {"system": "ACTOR Kiro", "setting": "no benchmark tests", "denominator": 87, "builds": 82, "tests": 56, "loc": 43000, "unsafe_percent": 1},
        {"system": "C2Rust/Laertes/C2SaferRust/SmartC2Rust", "setting": "no benchmark tests", "denominator": 87, "builds": 0, "tests": 0, "loc": "", "unsafe_percent": ""},
        {"system": "GPT-5.4", "setting": "no benchmark tests", "denominator": 87, "builds": 82, "tests": 50, "loc": 57000, "unsafe_percent": 0},
        {"system": "Kimi K2.5", "setting": "no benchmark tests", "denominator": 87, "builds": 46, "tests": 31, "loc": 28000, "unsafe_percent": 0},
        {"system": "Gemini 3.1 Pro", "setting": "no benchmark tests", "denominator": 87, "builds": 11, "tests": 8, "loc": 15000, "unsafe_percent": 0},
        {"system": "ACTOR Kiro", "setting": "test repair", "denominator": 87, "builds": 87, "tests": 82, "loc": 52000, "unsafe_percent": 1},
        {"system": "ACTOR Claude", "setting": "test repair", "denominator": 87, "builds": 85, "tests": 75, "loc": 45000, "unsafe_percent": 0},
        {"system": "ACTOR Codex", "setting": "test repair", "denominator": 87, "builds": 87, "tests": 81, "loc": 48000, "unsafe_percent": 1},
        {"system": "GPT-5.4", "setting": "test repair", "denominator": 87, "builds": 79, "tests": 64, "loc": 58000, "unsafe_percent": 0},
        {"system": "Kimi K2.5", "setting": "test repair", "denominator": 87, "builds": 45, "tests": 39, "loc": 28000, "unsafe_percent": 0},
        {"system": "Gemini 3.1 Pro", "setting": "test repair", "denominator": 87, "builds": 8, "tests": 7, "loc": 15000, "unsafe_percent": 0},
    ],
    "actor_schesch_figure3_tractor_totals.csv": [
        {"system": "ACTOR Kiro", "compiles": 338, "passes": 325, "denominator": 338, "loc": 47000, "unsafe_percent": 50},
        {"system": "ACTOR Claude", "compiles": 338, "passes": 319, "denominator": 338, "loc": 53000, "unsafe_percent": 53},
        {"system": "ACTOR Codex", "compiles": 337, "passes": 244, "denominator": 338, "loc": 36000, "unsafe_percent": 39},
        {"system": "ACTOR Kiro no validation", "compiles": 337, "passes": 230, "denominator": 338, "loc": 37000, "unsafe_percent": 50},
        {"system": "C2Rust", "compiles": 205, "passes": 204, "denominator": 338, "loc": 87000, "unsafe_percent": 70},
        {"system": "Laertes", "compiles": 202, "passes": 201, "denominator": 338, "loc": 88000, "unsafe_percent": 66},
        {"system": "C2SaferRust", "compiles": 193, "passes": 154, "denominator": 338, "loc": 82000, "unsafe_percent": 59},
        {"system": "SmartC2Rust", "compiles": 48, "passes": 40, "denominator": 338, "loc": 7000, "unsafe_percent": 2},
        {"system": "Kimi K2.5", "compiles": 157, "passes": 118, "denominator": 338, "loc": 25000, "unsafe_percent": 17},
        {"system": "GPT-5.4", "compiles": 189, "passes": 154, "denominator": 338, "loc": 28000, "unsafe_percent": 10},
        {"system": "Gemini 3.1 Pro", "compiles": 186, "passes": 156, "denominator": 338, "loc": 24000, "unsafe_percent": 15},
    ],
    "actor_schesch_figure4_failures.csv": [
        {"root_cause": "undefined behavior", "count": 3},
        {"root_cause": "macros", "count": 3},
        {"root_cause": "configuration", "count": 1},
        {"root_cause": "input processing", "count": 9},
        {"root_cause": "underspecified", "count": 2},
        {"root_cause": "truncated output", "count": 12},
    ],
    "actor_schesch_figure5_unsafe.csv": [
        {"root_cause": "C string/pointer conversion", "count": 2194},
        {"root_cause": "raw-pointer signatures/casts", "count": 5957},
        {"root_cause": "pointer arithmetic", "count": 3931},
        {"root_cause": "C ABI preservation", "count": 1648},
        {"root_cause": "ptr read/write/copy", "count": 527},
        {"root_cause": "FFI calls", "count": 208},
        {"root_cause": "mutable global", "count": 116},
        {"root_cause": "uninitialized structs", "count": 70},
        {"root_cause": "bridging raw pointers", "count": 60},
        {"root_cause": "function-pointer dispatch", "count": 36},
        {"root_cause": "other", "count": 44},
    ],
    "actor_schesch_figure7_prompts.csv": [
        {"configuration": "ACTOR Claude", "tractor_passes": 319, "tractor_denominator": 338, "crust_no_tests_passes": 56, "crust_test_repair_passes": 75, "crust_denominator": 87},
        {"configuration": "without subtask", "tractor_passes": 313, "tractor_denominator": 338, "crust_no_tests_passes": 56, "crust_test_repair_passes": 79, "crust_denominator": 87},
        {"configuration": "without iteration", "tractor_passes": 249, "tractor_denominator": 338, "crust_no_tests_passes": 31, "crust_test_repair_passes": 73, "crust_denominator": 87},
        {"configuration": "without features", "tractor_passes": 204, "tractor_denominator": 338, "crust_no_tests_passes": 55, "crust_test_repair_passes": 76, "crust_denominator": 87},
        {"configuration": "minimal", "tractor_passes": 171, "tractor_denominator": 338, "crust_no_tests_passes": 41, "crust_test_repair_passes": 75, "crust_denominator": 87},
    ],
    "actor_schesch_cost.csv": [
        {"system": "ACTOR Kiro", "scope": "CRUST-Bench", "cost_usd": 67, "minutes": "", "cost_per_kloc_usd": 1.57, "minutes_per_kloc": 19},
        {"system": "ACTOR Kiro", "scope": "TRACTOR", "cost_usd": 93, "minutes": "", "cost_per_kloc_usd": 1.97, "minutes_per_kloc": 34},
        {"system": "ACTOR Kiro", "scope": "largest P01 case", "cost_usd": 3.61, "minutes": 76, "cost_per_kloc_usd": "", "minutes_per_kloc": ""},
        {"system": "Claude Code", "scope": "TRACTOR", "cost_usd": 570, "minutes": "", "cost_per_kloc_usd": "", "minutes_per_kloc": ""},
        {"system": "all configurations", "scope": "full ablation", "cost_usd": 2900, "minutes": "", "cost_per_kloc_usd": "", "minutes_per_kloc": ""},
    ],
    "rustprint_reference.csv": [
        {"surface": "Table 1", "system": "RustPrint Kimi", "metric": "compiled repositories", "value": 8, "denominator": 8},
        {"surface": "Table 1", "system": "RustPrint GPT-5.4", "metric": "compiled repositories", "value": 8, "denominator": 8},
        {"surface": "Table 1", "system": "Self-Repair", "metric": "compiled repositories", "value": 0, "denominator": 8},
        {"surface": "Table 1", "system": "EvoC2Rust", "metric": "compiled repositories", "value": 0, "denominator": 8},
        {"surface": "Table 1", "system": "C2Rust", "metric": "compiled repositories", "value": 8, "denominator": 8},
        {"surface": "Table 1", "system": "Claude Code", "metric": "compiled repositories", "value": 8, "denominator": 8},
        {"surface": "Table 2", "system": "RustPrint GPT-5.4", "metric": "aggregate cross-test TPR percent", "value": 98.70, "denominator": "16 cells"},
        {"surface": "Table 2", "system": "RustPrint Kimi", "metric": "aggregate cross-test TPR percent", "value": 95.17, "denominator": "16 cells"},
        {"surface": "Table 2", "system": "Claude Code", "metric": "aggregate cross-test TPR percent", "value": 79.85, "denominator": "16 cells"},
        {"surface": "Figure 2", "system": "RustPrint Kimi", "metric": "feature conservation percent", "value": 93.26, "denominator": "8 repositories"},
        {"surface": "Figure 2", "system": "RustPrint GPT-5.4", "metric": "feature conservation percent", "value": 97.76, "denominator": "8 repositories"},
        {"surface": "Figure 2", "system": "Claude Code Kimi", "metric": "feature conservation percent", "value": 52.52, "denominator": "8 repositories"},
        {"surface": "Figure 2", "system": "Claude Code GPT-5.4", "metric": "feature conservation percent", "value": 48.87, "denominator": "8 repositories"},
        {"surface": "Figure 4", "system": "RustPrint Kimi", "metric": "SafeRate A/F percent", "value": "96.23/96.19", "denominator": "8 repositories"},
        {"surface": "Figure 4", "system": "RustPrint GPT-5.4", "metric": "SafeRate A/F percent", "value": "99.41/98.47", "denominator": "8 repositories"},
    ],
    "ptrtrans_reference.csv": [
        {"surface": "Table 3", "scope": "Crown-16 total", "system": "Crown", "metric": "lint alerts", "value": 6802},
        {"surface": "Table 3", "scope": "Crown-16 total", "system": "PR2", "metric": "lint alerts", "value": 4135},
        {"surface": "Table 3", "scope": "Crown-16 total", "system": "PtrTrans", "metric": "lint alerts", "value": 349},
        {"surface": "Table 3", "scope": "Crown-16 total", "system": "Crown", "metric": "unsafe usages", "value": 141866},
        {"surface": "Table 3", "scope": "Crown-16 total", "system": "PR2", "metric": "unsafe usages", "value": 134185},
        {"surface": "Table 3", "scope": "Crown-16 total", "system": "PtrTrans", "metric": "unsafe usages", "value": 85},
        {"surface": "Table 4", "scope": "small projects", "system": "FLOURINE", "metric": "compiled/equivalent percent", "value": "69.9/52.3"},
        {"surface": "Table 4", "scope": "small projects", "system": "PtrTrans", "metric": "compiled/equivalent percent", "value": "98.3/81.6"},
        {"surface": "Table 4", "scope": "large projects", "system": "FLOURINE", "metric": "compiled/equivalent percent", "value": "64.0/14.2"},
        {"surface": "Table 4", "scope": "large projects", "system": "PtrTrans", "metric": "compiled/equivalent percent", "value": "85.9/67.9"},
        {"surface": "Table 5", "scope": "small-10 average", "system": "PtrTrans_PS", "metric": "compiled/equivalent percent", "value": "89.3/59.5"},
        {"surface": "Table 5", "scope": "small-10 average", "system": "PtrTrans_PU", "metric": "compiled/equivalent percent", "value": "84.6/52.9"},
        {"surface": "Table 5", "scope": "small-10 average", "system": "PtrTrans_RA", "metric": "compiled/equivalent percent", "value": "87.9/61.9"},
        {"surface": "Table 5", "scope": "small-10 average", "system": "PtrTrans_EC", "metric": "compiled/equivalent percent", "value": "66.0/50.8"},
        {"surface": "Table 5", "scope": "small-10 average", "system": "PtrTrans", "metric": "compiled/equivalent percent", "value": "100/81.6"},
    ],
    "actor_li_reference.csv": [
        {"surface": "micro evaluation", "scope": "6 utilities / 3 runs", "system": "ACToR Claude Code Sonnet 4.5", "metric": "hidden-test pass percent", "value": 97.0, "uncertainty": "SD 1.9 pp"},
        {"surface": "micro evaluation", "scope": "6 utilities", "system": "naive Claude Code Sonnet 4.5", "metric": "hidden-test pass percent", "value": 89.2, "uncertainty": ""},
        {"surface": "micro evaluation", "scope": "6 utilities / 10 iterations", "system": "ACToR Claude Code Sonnet 4.5", "metric": "hidden-test pass percent", "value": 98.2, "uncertainty": ""},
        {"surface": "macro evaluation", "scope": "57 BSD utilities", "system": "coverage baseline", "metric": "relative pass percent", "value": 58.4, "uncertainty": ""},
        {"surface": "macro evaluation", "scope": "57 BSD utilities", "system": "ACToR", "metric": "relative pass percent", "value": 95.1, "uncertainty": ""},
        {"surface": "C2SaferRust augmentation", "scope": "7 executables", "system": "C2SaferRust", "metric": "pass percent", "value": 76.3, "uncertainty": ""},
        {"surface": "C2SaferRust augmentation", "scope": "7 executables", "system": "C2SaferRust + ACToR", "metric": "pass percent", "value": 92.9, "uncertainty": ""},
        {"surface": "cost", "scope": "57 BSD utilities", "system": "coverage baseline", "metric": "USD", "value": 808, "uncertainty": ""},
        {"surface": "cost", "scope": "57 BSD utilities", "system": "ACToR", "metric": "USD", "value": 1634, "uncertainty": ""},
    ],
    "blocked_aggregate_references.csv": [
        {"paper": "RustAssure", "scope": "5 applications/libraries", "metric": "compilable functions percent", "value": 89.8, "status": "abstract aggregate; project-level comparison incompatible"},
        {"paper": "RustAssure", "scope": "5 applications/libraries", "metric": "symbolically equivalent returns percent", "value": 69.9, "status": "abstract aggregate; project-level comparison incompatible"},
        {"paper": "DepTrans", "scope": "145 repository instances", "metric": "compilation success percent", "value": 60.7, "status": "abstract aggregate; benchmark unreleased"},
        {"paper": "DepTrans", "scope": "145 repository instances", "metric": "computational accuracy percent", "value": 43.5, "status": "abstract aggregate; benchmark unreleased"},
        {"paper": "DepTrans", "scope": "15 industrial projects", "metric": "successful builds", "value": 7, "status": "internal Huawei subjects unreleased"},
    ],
}


def validate_citer_reference_data() -> None:
    expected_lengths = {
        "orbit_table1_scale.csv": 7,
        "orbit_table4_safety_summary.csv": 4,
        "orbit_table5_tractor.csv": 13,
        "orbit_table6_ablation.csv": 12,
        "actor_schesch_figure6_crust.csv": 11,
        "actor_schesch_figure3_tractor_totals.csv": 11,
        "actor_schesch_figure4_failures.csv": 6,
        "actor_schesch_figure5_unsafe.csv": 11,
        "actor_schesch_figure7_prompts.csv": 5,
        "actor_schesch_cost.csv": 5,
        "rustprint_reference.csv": 15,
        "ptrtrans_reference.csv": 15,
        "actor_li_reference.csv": 9,
        "blocked_aggregate_references.csv": 5,
    }
    actual = {name: len(rows) for name, rows in CITER_REFERENCE_TABLES.items()}
    if actual != expected_lengths:
        raise ValueError(f"citer reference table drifted: {actual}")
    unsafe_total = sum(
        row["count"]
        for row in CITER_REFERENCE_TABLES["actor_schesch_figure5_unsafe.csv"]
    )
    if unsafe_total != 14791:
        raise ValueError(f"ACTOR unsafe taxonomy drifted: {unsafe_total}")


validate_citer_reference_data()
