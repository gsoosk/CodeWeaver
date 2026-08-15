"""Publication-grade, cross-system comparison of normalized ReCodeAgent runs.

This stage only reads normalized output from :mod:`collect` and
:mod:`baseline_replay`.  It does not run an evaluator, modify an artifact, or
infer an outcome from a paper aggregate.  In particular, a released
SWE-agent CRUST target is not available for replay; it remains an explicit
unavailable result.  The optional workbook is used only as a separately
labelled published-reference track, and only when it contains an
authoritative per-project CRUST outcome inventory.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

from experiments.recodeagent import common as C
from experiments.recodeagent import render as RD

SCHEMA_VERSION = 1
PRIMARY_REPETITION = 0
DEFAULT_REPETITIONS = 3
DEFAULT_RESAMPLES = 5_000
DEFAULT_BOOTSTRAP_SEED = 20_260_805
DEFAULT_RATE_TOLERANCE = 1e-12
CODEWEAVER_SYSTEM = "codeweaver"
REPLAY_SYSTEMS = ("recodeagent", "prior")
ALL_SYSTEMS = (CODEWEAVER_SYSTEM, *REPLAY_SYSTEMS)
TOOLS = tuple(C.DATASET_SPECS)

METRICS = {
    "compilation_success": "Compilation success",
    "project_pass_all": "Project pass-all",
    "validated_test_micro_pass_rate": "Validated-test micro pass rate",
    "validated_test_macro_pass_rate": "Validated-test macro pass rate",
}


# --------------------------------------------------------------------------- #
# Strict input handling
# --------------------------------------------------------------------------- #
def _strict_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer, not a boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.lstrip("+-").isdigit():
            return int(text)
    raise ValueError(f"{field} must be an integer, got {value!r}")


def _strict_float(value: Any, *, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number, not a boolean")
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            result = float(value.strip())
        except ValueError as exc:
            raise ValueError(f"{field} must be numeric, got {value!r}") from exc
    else:
        raise ValueError(f"{field} must be numeric, got {value!r}")
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite, got {value!r}")
    return result


def _strict_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError(
        f"{field} must be a literal boolean/CSV True or False, got {value!r}; "
        "success-shaped strings and numeric flags are not accepted"
    )


def _read_records(path: Path, *, label: str) -> list[dict[str, Any]]:
    """Read CSV or JSONL without the silent malformed-line skipping used for logs."""
    if not path.is_file():
        raise FileNotFoundError(f"{label} input does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"{label} CSV has no header: {path}")
            return [dict(row) for row in reader]
    if suffix not in (".jsonl", ".ndjson"):
        raise ValueError(f"{label} must be a .csv, .jsonl, or .ndjson file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} JSONL line {line_number} is malformed: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} JSONL line {line_number} is not an object")
        records.append(value)
    return records


def _input_hash(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "sha256": None,
            "status": Status.UNAVAILABLE,
            "reason": "optional input was not supplied",
        }
    if not path.is_file():
        return {
            "path": str(path),
            "sha256": None,
            "status": Status.MISSING,
            "reason": "input file does not exist",
        }
    return {
        "path": str(path.resolve()),
        "sha256": C.file_sha256(path),
        "size_bytes": path.stat().st_size,
        "status": Status.MEASURED,
        "reason": "",
    }


def _input_paths(
    value: Path | str | Iterable[Path | str] | None,
    *,
    label: str,
    required: bool,
) -> list[Path]:
    """Accept a single path for legacy callers or a non-empty path sequence."""
    if value is None:
        if required:
            raise ValueError(f"{label} requires at least one input path")
        return []
    if isinstance(value, (str, Path)):
        paths = [Path(value)]
    else:
        try:
            paths = [Path(item) for item in value]
        except TypeError as exc:
            raise ValueError(f"{label} must be a path or iterable of paths") from exc
    if required and not paths:
        raise ValueError(f"{label} requires at least one input path")
    if any(not str(path) for path in paths):
        raise ValueError(f"{label} contains an empty path")
    return paths


def _provenance_input_hashes(paths: list[Path]) -> dict[str, Any] | list[dict[str, Any]]:
    """Keep the legacy single-path shape while recording every repeated input."""
    records = [
        {"input_index": index, **_input_hash(path)}
        for index, path in enumerate(paths)
    ]
    if not records:
        return _input_hash(None)
    if len(records) == 1:
        return records[0]
    return records


Status = C.Status


def _metric_status(
    row: dict[str, Any],
    field: str,
    *,
    status_field: str | None = None,
) -> tuple[str, str]:
    status_name = status_field or f"{field}_status"
    status = row.get(status_name)
    reason = row.get(f"{field}_reason")
    if not isinstance(reason, str):
        reason = "" if reason is None else str(reason)
    if not isinstance(status, str) or status not in Status.ALL:
        return (
            Status.ERROR,
            f"invalid or absent {status_name} {status!r}; value was not used",
        )
    return status, reason


def _normal_metric(
    row: dict[str, Any],
    field: str,
    parser: Callable[..., Any],
    *,
    nonnegative: bool = False,
    status_field: str | None = None,
) -> dict[str, Any]:
    status, reason = _metric_status(row, field, status_field=status_field)
    if status != Status.MEASURED:
        return {"value": None, "status": status, "reason": reason}
    try:
        value = parser(row.get(field), field=field)
        if nonnegative and value < 0:
            raise ValueError(f"{field} must be non-negative, got {value!r}")
    except ValueError as exc:
        return {"value": None, "status": Status.ERROR, "reason": str(exc)}
    return {"value": value, "status": Status.MEASURED, "reason": reason}


def _normalise_raw_rows(
    records: list[dict[str, Any]],
    *,
    system: str,
    manifest_by_id: dict[str, dict[str, Any]],
    variant: str,
    source_label: str,
) -> tuple[list[dict[str, Any]], int]:
    """Normalize values while retaining rows with invalid metric fields as evidence."""
    normalized: list[dict[str, Any]] = []
    excluded_variant_rows = 0
    seen: set[tuple[str, str, int]] = set()
    for index, raw in enumerate(records):
        raw_variant = raw.get("variant")
        if raw_variant != variant:
            excluded_variant_rows += 1
            continue
        if system == CODEWEAVER_SYSTEM:
            supplied = raw.get("system")
            if supplied not in (None, "", CODEWEAVER_SYSTEM):
                raise ValueError(
                    f"{source_label} row {index} has system={supplied!r}; expected "
                    f"no system or {CODEWEAVER_SYSTEM!r}"
                )
        else:
            supplied = raw.get("system")
            if supplied != system:
                raise ValueError(
                    f"{source_label} row {index} has system={supplied!r}; expected {system!r}"
                )
        project_id = raw.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError(f"{source_label} row {index} has invalid project_id {project_id!r}")
        if project_id not in manifest_by_id:
            raise ValueError(f"{source_label} row {index} project_id is absent from manifest: {project_id!r}")
        tool = raw.get("tool")
        if tool != manifest_by_id[project_id]["tool"]:
            raise ValueError(
                f"{source_label} row {index} tool {tool!r} conflicts with manifest "
                f"tool {manifest_by_id[project_id]['tool']!r} for {project_id!r}"
            )
        repetition = _strict_int(raw.get("repetition"), field=f"{source_label}.repetition")
        if repetition < 0:
            raise ValueError(f"{source_label} row {index} has negative repetition")
        key = (system, project_id, repetition)
        if key in seen:
            raise ValueError(
                f"duplicate normalized raw-run key (duplicate system/project/repetition key): {key!r}"
            )
        seen.add(key)

        metrics = {
            "compilation_success": _normal_metric(raw, "build", _strict_bool),
            "project_pass_all": _normal_metric(raw, "project_pass_all", _strict_bool),
            "validated_tests_expected": _normal_metric(
                raw, "validated_tests_expected", _strict_int, nonnegative=True
            ),
            "validated_tests_passed": _normal_metric(
                raw, "validated_tests_passed", _strict_int, nonnegative=True
            ),
            "validated_test_rate": _normal_metric(
                raw, "validated_tests_pass_rate", _strict_float, nonnegative=True
            ),
            "actual_cost_nano_aiu": _normal_metric(
                raw, "total_nano_aiu", _strict_float, nonnegative=True,
                status_field="nano_aiu_status",
            ),
        }
        normalized.append(
            {
                "system": system,
                "project_id": project_id,
                "tool": tool,
                "repetition": repetition,
                "raw": raw,
                "metrics": metrics,
                "source": source_label,
            }
        )
    return normalized, excluded_variant_rows


def _normalise_failure_rows(
    records: list[dict[str, Any]],
    *,
    default_system: str | None,
    manifest_by_id: dict[str, dict[str, Any]],
    variant: str,
    source_label: str,
) -> tuple[list[dict[str, Any]], int]:
    """Keep every failure row; collect.py's legacy failures lack failure_status."""
    normalized: list[dict[str, Any]] = []
    excluded_variant_rows = 0
    seen: set[tuple[str, str, int]] = set()
    for index, raw in enumerate(records):
        if raw.get("variant") not in (None, "", variant):
            excluded_variant_rows += 1
            continue
        system = default_system if default_system is not None else raw.get("system")
        if system not in ALL_SYSTEMS:
            raise ValueError(f"{source_label} failure {index} has invalid system {system!r}")
        project_id = raw.get("project_id")
        if not isinstance(project_id, str) or project_id not in manifest_by_id:
            raise ValueError(
                f"{source_label} failure {index} has project_id absent from manifest: {project_id!r}"
            )
        tool = raw.get("tool")
        if tool != manifest_by_id[project_id]["tool"]:
            raise ValueError(
                f"{source_label} failure {index} tool {tool!r} conflicts with manifest for {project_id!r}"
            )
        repetition = _strict_int(raw.get("repetition"), field=f"{source_label}.repetition")
        status = raw.get("failure_status")
        inferred = status in (None, "")
        if inferred:
            # collect.py failure rows predate the baseline replay's explicit field.
            status = Status.ERROR
        if not isinstance(status, str) or status not in Status.ALL:
            status = Status.ERROR
            inferred = True
        if status == Status.MEASURED:
            status = Status.ERROR
            inferred = True
        key = (system, project_id, repetition)
        if key in seen:
            raise ValueError(f"duplicate failure system/project/repetition key: {key!r}")
        seen.add(key)
        normalized.append(
            {
                "system": system,
                "project_id": project_id,
                "tool": tool,
                "repetition": repetition,
                "failure_status": status,
                "reason": str(raw.get("reason") or ""),
                "inferred_failure_status": inferred,
                "source": source_label,
            }
        )
    return normalized, excluded_variant_rows


def _load_manifest(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = C.read_json(path)
    projects = manifest.get("projects")
    if not isinstance(projects, list):
        raise ValueError("manifest.projects must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise ValueError(f"manifest project row {index} is not an object")
        project_id = project.get("id")
        tool = project.get("tool")
        name = project.get("project")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError(f"manifest project row {index} has invalid id")
        if tool not in TOOLS:
            raise ValueError(f"manifest project row {index} has unsupported tool {tool!r}")
        if not isinstance(name, str) or not name:
            raise ValueError(f"manifest project row {index} has invalid project name")
        expected_id = f"{tool}__{name}"
        if project_id != expected_id:
            raise ValueError(
                f"manifest project row {index} id must be {expected_id!r}, got {project_id!r}"
            )
        if project_id in by_id:
            raise ValueError(f"manifest has duplicate project id {project_id!r}")
        by_id[project_id] = dict(project)
    return manifest, by_id


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def _regularized_beta(a: float, b: float, x: float) -> float:
    """Numerically stable regularized incomplete beta for Student-t quantiles."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d, h = 1.0, 1.0 - qab * x / qap, 1.0
    if abs(d) < 3e-30:
        d = 3e-30
    d = 1.0 / d
    h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 3e-30:
            d = 3e-30
        c = 1.0 + aa / c
        if abs(c) < 3e-30:
            c = 3e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 3e-30:
            d = 3e-30
        c = 1.0 + aa / c
        if abs(c) < 3e-30:
            c = 3e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    log_bt = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * h / a

    # Re-evaluate the continued fraction with exchanged parameters.
    return 1.0 - _regularized_beta(b, a, 1.0 - x)


def _student_t_cdf(value: float, degrees_of_freedom: int) -> float:
    x = degrees_of_freedom / (degrees_of_freedom + value * value)
    tail = 0.5 * _regularized_beta(degrees_of_freedom / 2.0, 0.5, x)
    return 1.0 - tail if value >= 0 else tail


def _student_t_critical_95(degrees_of_freedom: int) -> float:
    if degrees_of_freedom < 1:
        raise ValueError("Student-t degrees of freedom must be positive")
    # Bisection avoids depending on scipy for the protocol-mandated t interval.
    low, high = 0.0, 1.0
    while _student_t_cdf(high, degrees_of_freedom) < 0.975:
        high *= 2.0
    for _ in range(80):
        middle = (low + high) / 2.0
        if _student_t_cdf(middle, degrees_of_freedom) < 0.975:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def t_summary(values: list[float]) -> dict[str, Any]:
    """Mean, sample SD, and a two-sided 95% Student-t interval."""
    n = len(values)
    if not n:
        return {
            "status": Status.MISSING,
            "n": 0,
            "mean": None,
            "sample_sd": None,
            "ci_95_t": None,
            "variability_status": Status.MISSING,
            "reason": "no measured repetitions",
        }
    mean = statistics.fmean(values)
    if n < 2:
        return {
            "status": Status.MEASURED,
            "n": 1,
            "mean": mean,
            "sample_sd": None,
            "ci_95_t": None,
            "variability_status": Status.MISSING,
            "reason": "sample SD and t interval require at least two repetitions",
        }
    sample_sd = statistics.stdev(values)
    critical = _student_t_critical_95(n - 1)
    half_width = critical * sample_sd / math.sqrt(n)
    return {
        "status": Status.MEASURED,
        "n": n,
        "mean": mean,
        "sample_sd": sample_sd,
        "ci_95_t": [mean - half_width, mean + half_width],
        "variability_status": Status.MEASURED,
        "reason": "",
    }


def bootstrap_mean_ci(
    values: list[float],
    *,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if len(values) < 2:
        return {
            "status": Status.MISSING,
            "ci_95": None,
            "resamples": resamples,
            "seed": seed,
            "reason": "bootstrap CI requires at least two projects",
        }
    rng = random.Random(seed)
    n = len(values)
    means = [
        statistics.fmean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(resamples)
    ]
    means.sort()
    return {
        "status": Status.MEASURED,
        "ci_95": [
            means[int(0.025 * resamples)],
            means[min(int(0.975 * resamples), resamples - 1)],
        ],
        "resamples": resamples,
        "seed": seed,
        "reason": "",
    }


def _bootstrap_ratio_ci(
    values: list[tuple[float, float]],
    *,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    if len(values) < 2:
        return {
            "status": Status.MISSING,
            "ci_95": None,
            "resamples": resamples,
            "seed": seed,
            "reason": "project-cluster bootstrap CI requires at least two projects",
        }
    rng = random.Random(seed)
    n = len(values)
    samples: list[float] = []
    for _ in range(resamples):
        chosen = [values[rng.randrange(n)] for _ in range(n)]
        denominator = sum(pair[1] for pair in chosen)
        if denominator <= 0:
            continue
        samples.append(sum(pair[0] for pair in chosen) / denominator)
    if not samples:
        return {
            "status": Status.MISSING,
            "ci_95": None,
            "resamples": resamples,
            "seed": seed,
            "reason": "bootstrap samples had no positive denominator",
        }
    samples.sort()
    return {
        "status": Status.MEASURED,
        "ci_95": [
            samples[int(0.025 * len(samples))],
            samples[min(int(0.975 * len(samples)), len(samples) - 1)],
        ],
        "resamples": resamples,
        "seed": seed,
        "reason": "",
    }


def exact_mcnemar_p_value(wins: int, losses: int) -> float:
    """Exact two-sided binomial McNemar p value, including all edge cases."""
    if wins < 0 or losses < 0:
        raise ValueError("McNemar discordant counts cannot be negative")
    discordant = wins + losses
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(wins, losses) + 1))
    return min(1.0, 2.0 * tail / (2 ** discordant))


def paired_binary_stats(
    codeweaver: list[bool],
    recodeagent: list[bool],
    *,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if len(codeweaver) != len(recodeagent):
        raise ValueError("paired binary inputs have different lengths")
    n = len(codeweaver)
    if not n:
        return {
            "status": Status.MISSING,
            "n": 0,
            "cw_yes_rca_no_wins": 0,
            "rca_yes_cw_no_losses": 0,
            "ties": 0,
            "delta_percentage_points": None,
            "exact_mcnemar_p_value": None,
            "paired_bootstrap_ci_percentage_points": None,
            "bootstrap_status": Status.MISSING,
            "reason": "no genuinely measured paired projects",
        }
    wins = sum(cw and not rca for cw, rca in zip(codeweaver, recodeagent))
    losses = sum(rca and not cw for cw, rca in zip(codeweaver, recodeagent))
    ties = n - wins - losses
    differences = [float(cw) - float(rca) for cw, rca in zip(codeweaver, recodeagent)]
    bootstrap = bootstrap_mean_ci(differences, resamples=resamples, seed=seed)
    ci = bootstrap["ci_95"]
    return {
        "status": Status.MEASURED,
        "n": n,
        "cw_yes_rca_no_wins": wins,
        "rca_yes_cw_no_losses": losses,
        "ties": ties,
        "delta_percentage_points": 100.0 * statistics.fmean(differences),
        "exact_mcnemar_p_value": exact_mcnemar_p_value(wins, losses),
        "exact_test": "two-sided exact binomial McNemar test",
        "paired_bootstrap_ci_percentage_points": (
            [100.0 * ci[0], 100.0 * ci[1]] if ci is not None else None
        ),
        "bootstrap_status": bootstrap["status"],
        "bootstrap_reason": bootstrap["reason"],
        "reason": "",
    }


def paired_rate_stats(
    codeweaver: list[float],
    recodeagent: list[float],
    *,
    tolerance: float = DEFAULT_RATE_TOLERANCE,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if len(codeweaver) != len(recodeagent):
        raise ValueError("paired rate inputs have different lengths")
    if tolerance < 0:
        raise ValueError("rate tolerance must not be negative")
    n = len(codeweaver)
    if not n:
        return {
            "status": Status.MISSING,
            "n": 0,
            "cw_wins": 0,
            "ties": 0,
            "rca_losses": 0,
            "mean_delta": None,
            "mean_delta_percentage_points": None,
            "paired_bootstrap_ci_percentage_points": None,
            "wilcoxon": {
                "status": Status.MISSING,
                "reason": "no genuinely measured paired projects",
            },
            "reason": "no genuinely measured paired projects",
        }
    diffs = [cw - rca for cw, rca in zip(codeweaver, recodeagent)]
    wins = sum(diff > tolerance for diff in diffs)
    losses = sum(diff < -tolerance for diff in diffs)
    bootstrap = bootstrap_mean_ci(diffs, resamples=resamples, seed=seed)
    ci = bootstrap["ci_95"]
    scipy_stats = C.optional_import("scipy.stats")
    if scipy_stats is None:
        wilcoxon = {
            "status": Status.UNAVAILABLE,
            "reason": "scipy.stats is not installed; Wilcoxon was not fabricated",
        }
    elif n < 2 or not any(abs(diff) > tolerance for diff in diffs):
        wilcoxon = {
            "status": Status.UNAVAILABLE,
            "reason": "Wilcoxon is undefined for fewer than two or all-tied paired differences",
        }
    else:
        try:
            statistic, p_value = scipy_stats.wilcoxon(codeweaver, recodeagent)
            wilcoxon = {
                "status": Status.MEASURED,
                "statistic": float(statistic),
                "p_value": float(p_value),
                "reason": "",
            }
        except Exception as exc:  # scipy may reject degenerate tie patterns
            wilcoxon = {
                "status": Status.UNAVAILABLE,
                "reason": f"scipy Wilcoxon could not be computed: {exc}",
            }
    return {
        "status": Status.MEASURED,
        "n": n,
        "cw_wins": wins,
        "ties": n - wins - losses,
        "rca_losses": losses,
        "mean_delta": statistics.fmean(diffs),
        "mean_delta_percentage_points": 100.0 * statistics.fmean(diffs),
        "paired_bootstrap_ci_percentage_points": (
            [100.0 * ci[0], 100.0 * ci[1]] if ci is not None else None
        ),
        "bootstrap_status": bootstrap["status"],
        "bootstrap_reason": bootstrap["reason"],
        "numerical_tolerance": tolerance,
        "wilcoxon": wilcoxon,
        "reason": "",
    }


# --------------------------------------------------------------------------- #
# Aggregate metrics and completeness
# --------------------------------------------------------------------------- #
def _metric(row: dict[str, Any], name: str) -> dict[str, Any]:
    return row["metrics"][name]


def _micro_pair(row: dict[str, Any]) -> tuple[float, float, bool, bool] | None:
    expected = _metric(row, "validated_tests_expected")
    passed = _metric(row, "validated_tests_passed")
    rate = _metric(row, "validated_test_rate")
    if expected["status"] != Status.MEASURED or expected["value"] <= 0:
        return None
    if passed["status"] == Status.MEASURED:
        expected_value = float(expected["value"])
        passed_value = float(passed["value"])
        return min(passed_value, expected_value), expected_value, False, passed_value > expected_value
    # collect.compute_paper_pass_rate deliberately records blocked execution as
    # a *measured* zero rate against a measured oracle denominator.  Honor that
    # explicit evaluator semantics, but record every such zero substitution.
    if rate["status"] == Status.MEASURED and rate["value"] == 0.0:
        return 0.0, float(expected["value"]), True, False
    return None


def _aggregate_rate(
    rows: list[dict[str, Any]],
    metric_name: str,
    *,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    total_rows = len(rows)
    capped_pass_counts = 0
    if metric_name in ("compilation_success", "project_pass_all"):
        values = [
            float(_metric(row, metric_name)["value"])
            for row in rows
            if _metric(row, metric_name)["status"] == Status.MEASURED
        ]
        numerator = sum(values)
        denominator = len(values)
        ci = bootstrap_mean_ci(values, resamples=resamples, seed=seed)
        zero_substitutions = 0
    elif metric_name == "validated_test_macro_pass_rate":
        values = [
            min(float(_metric(row, "validated_test_rate")["value"]), 1.0)
            for row in rows
            if _metric(row, "validated_test_rate")["status"] == Status.MEASURED
        ]
        capped_pass_counts = sum(
            float(_metric(row, "validated_test_rate")["value"]) > 1.0
            for row in rows
            if _metric(row, "validated_test_rate")["status"] == Status.MEASURED
        )
        numerator = sum(values)
        denominator = len(values)
        ci = bootstrap_mean_ci(values, resamples=resamples, seed=seed)
        zero_substitutions = 0
    elif metric_name == "validated_test_micro_pass_rate":
        pairs = [pair for row in rows if (pair := _micro_pair(row)) is not None]
        numerator = sum(pair[0] for pair in pairs)
        denominator = sum(pair[1] for pair in pairs)
        values = [(pair[0], pair[1]) for pair in pairs]
        ci = _bootstrap_ratio_ci(values, resamples=resamples, seed=seed)
        zero_substitutions = sum(pair[2] for pair in pairs)
        capped_pass_counts = sum(pair[3] for pair in pairs)
    else:
        raise ValueError(f"unknown metric {metric_name!r}")
    eligible = len(values)
    if not eligible or not denominator:
        return {
            "status": Status.MISSING,
            "value": None,
            "n_projects": 0,
            "input_rows": total_rows,
            "excluded_projects": total_rows,
            "partial": total_rows > 0,
            "numerator": None,
            "denominator": None,
            "bootstrap": ci,
            "zero_numerator_substitutions": zero_substitutions,
            "capped_pass_counts": capped_pass_counts,
            "reason": f"no genuinely measured {metric_name} values",
        }
    value = numerator / denominator
    return {
        "status": Status.MEASURED,
        "value": value,
        "n_projects": eligible,
        "input_rows": total_rows,
        "excluded_projects": total_rows - eligible,
        "partial": eligible != total_rows,
        "numerator": numerator,
        "denominator": denominator,
        "bootstrap": ci,
        "zero_numerator_substitutions": zero_substitutions,
        "capped_pass_counts": capped_pass_counts,
        "reason": (
            f"{total_rows - eligible} project(s) excluded because their metric was not genuinely measured"
            if eligible != total_rows else ""
        ),
    }


def _codeweaver_metrics(
    rows: list[dict[str, Any]],
    *,
    repetitions: int,
    resamples: int,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    per_repetition: list[dict[str, Any]] = []
    for tool in (*TOOLS, "all"):
        for repetition in range(repetitions):
            selected = [
                row for row in rows
                if row["repetition"] == repetition and (tool == "all" or row["tool"] == tool)
            ]
            for metric_index, metric in enumerate(METRICS):
                aggregate = _aggregate_rate(
                    selected,
                    metric,
                    resamples=resamples,
                    seed=seed + repetition * 100 + metric_index,
                )
                per_repetition.append(
                    {
                        "system": CODEWEAVER_SYSTEM,
                        "tool": tool,
                        "repetition": repetition,
                        "metric": metric,
                        **aggregate,
                    }
                )
    summaries: list[dict[str, Any]] = []
    for tool in (*TOOLS, "all"):
        for metric in METRICS:
            by_rep = [
                row for row in per_repetition
                if row["tool"] == tool and row["metric"] == metric
            ]
            measured = [row["value"] for row in by_rep if row["status"] == Status.MEASURED]
            summary = t_summary(measured)
            summaries.append(
                {
                    "system": CODEWEAVER_SYSTEM,
                    "tool": tool,
                    "metric": metric,
                    "expected_repetitions": repetitions,
                    "measured_repetitions": [row["repetition"] for row in by_rep if row["status"] == Status.MEASURED],
                    "missing_repetitions": [row["repetition"] for row in by_rep if row["status"] != Status.MEASURED],
                    "partial": len(measured) != repetitions,
                    **summary,
                }
            )
    return per_repetition, summaries


def _failure_bucket(failures: list[dict[str, Any]]) -> str:
    statuses = {failure["failure_status"] for failure in failures}
    if Status.ERROR in statuses:
        return Status.ERROR
    if Status.UNAVAILABLE in statuses:
        return Status.UNAVAILABLE
    if Status.MISSING in statuses:
        return Status.MISSING
    return Status.ERROR


def _inventory(
    manifest_by_id: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    *,
    repetitions: int,
) -> list[dict[str, Any]]:
    raw_keys = {(row["system"], row["project_id"], row["repetition"]) for row in rows}
    failures_by_key: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for failure in failures:
        failures_by_key[(failure["system"], failure["project_id"], failure["repetition"])].append(failure)
    repetitions_by_system = {
        CODEWEAVER_SYSTEM: list(range(repetitions)),
        "recodeagent": sorted({0, *(row["repetition"] for row in rows if row["system"] == "recodeagent"),
                               *(failure["repetition"] for failure in failures if failure["system"] == "recodeagent")}),
        "prior": sorted({0, *(row["repetition"] for row in rows if row["system"] == "prior"),
                          *(failure["repetition"] for failure in failures if failure["system"] == "prior")}),
    }
    output: list[dict[str, Any]] = []
    for system in ALL_SYSTEMS:
        for repetition in repetitions_by_system[system]:
            for tool in TOOLS:
                projects = [project_id for project_id, row in manifest_by_id.items() if row["tool"] == tool]
                categories: Counter[str] = Counter()
                conflict_evidence = 0
                failure_evidence = 0
                for project_id in projects:
                    key = (system, project_id, repetition)
                    row_present = key in raw_keys
                    matching_failures = failures_by_key.get(key, [])
                    failure_evidence += len(matching_failures)
                    if row_present:
                        categories[Status.MEASURED] += 1
                        conflict_evidence += len(matching_failures)
                    elif matching_failures:
                        failure_bucket = _failure_bucket(matching_failures)
                        categories[failure_bucket] += 1
                        if failure_bucket == Status.MISSING:
                            categories["accounted_missing"] += 1
                    else:
                        categories[Status.MISSING] += 1
                        categories["unaccounted_missing"] += 1
                missing = categories[Status.MISSING]
                accounted_missing = categories["accounted_missing"]
                unaccounted_missing = categories["unaccounted_missing"]
                output.append(
                    {
                        "system": system,
                        "tool": tool,
                        "repetition": repetition,
                        "expected": len(projects),
                        "measured": categories[Status.MEASURED],
                        "unavailable": categories[Status.UNAVAILABLE],
                        "error": categories[Status.ERROR],
                        # Backward-compatible total. The two components
                        # distinguish a retained missing-artifact failure
                        # from a matrix cell with no evidence at all.
                        "missing": missing,
                        "accounted_missing": accounted_missing,
                        "unaccounted_missing": unaccounted_missing,
                        "all_expected_cells_accounted_for": unaccounted_missing == 0,
                        "accounting_status": (
                            Status.MEASURED if unaccounted_missing == 0 else Status.MISSING
                        ),
                        "failure_evidence_rows": failure_evidence,
                        "conflicting_failure_evidence_rows": conflict_evidence,
                        "status": (
                            Status.MEASURED
                            if categories[Status.MEASURED] == len(projects) and not conflict_evidence
                            else Status.MISSING
                        ),
                    }
                )
    return output


def _inventory_completeness(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize whether every expected matrix cell has raw or failure evidence.

    ``accounted_missing`` is an explicit released-artifact absence and is
    therefore eligible for a package-level accounted-completeness policy.
    ``unaccounted_missing`` is a cell with neither a raw row nor a retained
    failure record and must fail that policy.
    """
    fields = (
        "expected", "measured", "unavailable", "error", "missing",
        "accounted_missing", "unaccounted_missing",
    )
    totals = {field: sum(int(row.get(field, 0)) for row in inventory) for field in fields}
    totals.update(
        {
            "accounted_cells": totals["expected"] - totals["unaccounted_missing"],
            "all_expected_cells_accounted_for": totals["unaccounted_missing"] == 0,
            "accounting_status": (
                Status.MEASURED
                if totals["unaccounted_missing"] == 0
                else Status.MISSING
            ),
            "policy_statement": (
                "Explicit missing failure evidence is accounted_missing and may be accepted "
                "for released-artifact completeness; unaccounted_missing must be rejected."
            ),
        }
    )
    return totals


# --------------------------------------------------------------------------- #
# Paired and workbook-reference comparisons
# --------------------------------------------------------------------------- #
def _by_key(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {(row["system"], row["project_id"], row["repetition"]): row for row in rows}


def _primary_paired_comparisons(
    manifest_by_id: dict[str, dict[str, Any]],
    row_by_key: dict[tuple[str, str, int], dict[str, Any]],
    *,
    resamples: int,
    seed: int,
    tolerance: float,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for tool in (*TOOLS, "all"):
        project_ids = [
            project_id for project_id, project in manifest_by_id.items()
            if tool == "all" or project["tool"] == tool
        ]
        for metric_index, (label, internal_name) in enumerate((
            ("compilation_success", "compilation_success"),
            ("project_pass_all", "project_pass_all"),
        )):
            cw_values: list[bool] = []
            rca_values: list[bool] = []
            raw_intersection = 0
            for project_id in project_ids:
                cw = row_by_key.get((CODEWEAVER_SYSTEM, project_id, PRIMARY_REPETITION))
                rca = row_by_key.get(("recodeagent", project_id, PRIMARY_REPETITION))
                if cw is None or rca is None:
                    continue
                raw_intersection += 1
                cw_metric, rca_metric = _metric(cw, internal_name), _metric(rca, internal_name)
                if cw_metric["status"] == rca_metric["status"] == Status.MEASURED:
                    cw_values.append(cw_metric["value"])
                    rca_values.append(rca_metric["value"])
            stats = paired_binary_stats(
                cw_values, rca_values, resamples=resamples, seed=seed + metric_index
            )
            output.append(
                {
                    "comparison": "CodeWeaver rep0 vs released ReCodeAgent replay",
                    "tool": tool,
                    "metric": label,
                    "metric_kind": "binary",
                    "manifest_projects": len(project_ids),
                    "raw_intersection_projects": raw_intersection,
                    "excluded_not_genuinely_measured": raw_intersection - len(cw_values),
                    **stats,
                }
            )

        cw_rates: list[float] = []
        rca_rates: list[float] = []
        raw_intersection = 0
        for project_id in project_ids:
            cw = row_by_key.get((CODEWEAVER_SYSTEM, project_id, PRIMARY_REPETITION))
            rca = row_by_key.get(("recodeagent", project_id, PRIMARY_REPETITION))
            if cw is None or rca is None:
                continue
            raw_intersection += 1
            cw_metric, rca_metric = _metric(cw, "validated_test_rate"), _metric(rca, "validated_test_rate")
            if cw_metric["status"] == rca_metric["status"] == Status.MEASURED:
                cw_rates.append(cw_metric["value"])
                rca_rates.append(rca_metric["value"])
        stats = paired_rate_stats(
            cw_rates,
            rca_rates,
            tolerance=tolerance,
            resamples=resamples,
            seed=seed + 2,
        )
        output.append(
            {
                "comparison": "CodeWeaver rep0 vs released ReCodeAgent replay",
                "tool": tool,
                "metric": "validated_test_project_rate",
                "metric_kind": "continuous_rate",
                "manifest_projects": len(project_ids),
                "raw_intersection_projects": raw_intersection,
                "excluded_not_genuinely_measured": raw_intersection - len(cw_rates),
                **stats,
            }
        )
    return output


def _normalise_project_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _workbook_binary_outcome(value: Any) -> bool:
    """Parse only an authoritative Excel 0/1 outcome cell.

    This is intentionally separate from normalized-run parsing: openpyxl
    returns numeric Excel cells as floats, so an actual workbook ``0`` may be
    represented as ``0.0``.  Booleans and success-shaped text remain invalid.
    """
    if isinstance(value, bool):
        raise ValueError("workbook binary outcome must be numeric 0/1, not a boolean")
    if isinstance(value, int):
        numeric = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"workbook binary outcome must be finite integer-valued 0/1, got {value!r}")
        numeric = int(value)
    elif isinstance(value, str) and value.strip():
        try:
            parsed = _strict_float(value, field="workbook binary outcome")
        except ValueError as exc:
            raise ValueError(f"workbook binary outcome must be strict numeric 0/1, got {value!r}") from exc
        if not parsed.is_integer():
            raise ValueError(f"workbook binary outcome must be integer-valued 0/1, got {value!r}")
        numeric = int(parsed)
    else:
        raise ValueError(f"workbook binary outcome must be numeric 0/1, got {value!r}")
    if numeric not in (0, 1):
        raise ValueError(f"workbook binary outcome must be 0 or 1, got {value!r}")
    return bool(numeric)


def extract_swe_agent_workbook_outcomes(
    workbook_path: Path | None,
    crust_projects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract only exact, per-project SWE-agent compilation outcomes.

    Aggregate workbook values are intentionally insufficient.  This function
    returns unavailable unless the classification sheet maps one-to-one to all
    100 CRUST manifest projects and every outcome is an actual binary cell.
    """
    if workbook_path is None:
        return {
            "status": Status.UNAVAILABLE,
            "reason": "official results.xlsx was not supplied; no SWE-agent overlap was inferred",
            "outcomes": {},
        }
    if not workbook_path.is_file():
        return {
            "status": Status.MISSING,
            "reason": f"official results workbook does not exist: {workbook_path}",
            "outcomes": {},
        }
    if len(crust_projects) != C.EXPECTED_TOOL_COUNTS["crust"]:
        return {
            "status": Status.UNAVAILABLE,
            "reason": (
                "authoritative SWE-agent overlap extraction requires the exact 100-project "
                f"CRUST manifest, got {len(crust_projects)}"
            ),
            "outcomes": {},
        }
    openpyxl = C.optional_import("openpyxl")
    if openpyxl is None:
        return {
            "status": Status.UNAVAILABLE,
            "reason": "openpyxl is unavailable, so workbook outcomes were not fabricated",
            "outcomes": {},
        }
    sheet_name = "sweagent crust - tool test"
    try:
        workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        try:
            if sheet_name not in workbook.sheetnames:
                return {
                    "status": Status.UNAVAILABLE,
                    "reason": f"workbook has no authoritative {sheet_name!r} sheet",
                    "outcomes": {},
                }
            values = list(workbook[sheet_name].iter_rows(values_only=True))
        finally:
            workbook.close()
    except Exception as exc:
        return {
            "status": Status.UNAVAILABLE,
            "reason": f"could not read official workbook: {exc}",
            "outcomes": {},
        }
    if not values:
        return {
            "status": Status.UNAVAILABLE,
            "reason": f"authoritative sheet {sheet_name!r} is empty",
            "outcomes": {},
        }
    headers = [_normalise_project_key(str(value or "")) for value in values[0]]
    try:
        project_column = headers.index("project")
        outcome_column = headers.index("toolcompile10")
    except ValueError:
        return {
            "status": Status.UNAVAILABLE,
            "reason": (
                "authoritative sheet lacks exact project and 'tool compile (1/0)' columns; "
                "aggregate workbook values cannot supply per-project outcomes"
            ),
            "outcomes": {},
        }
    manifest_names = {_normalise_project_key(str(project["project"])): project["id"] for project in crust_projects}
    if len(manifest_names) != len(crust_projects):
        return {
            "status": Status.UNAVAILABLE,
            "reason": "CRUST manifest names collide under workbook matching normalization",
            "outcomes": {},
        }
    outcomes: dict[str, bool] = {}
    for row in values[1:]:
        if project_column >= len(row) or outcome_column >= len(row):
            continue
        project = row[project_column]
        outcome = row[outcome_column]
        if project in (None, ""):
            continue
        normalized = _normalise_project_key(str(project))
        # This sheet has one final aggregate "total" row.  It is not a
        # project outcome and must not be matched or treated as evidence.
        if normalized == "total":
            continue
        if normalized not in manifest_names:
            return {
                "status": Status.UNAVAILABLE,
                "reason": f"workbook CRUST project cannot be matched to manifest: {project!r}",
                "outcomes": {},
            }
        try:
            binary_outcome = _workbook_binary_outcome(outcome)
        except ValueError:
            return {
                "status": Status.UNAVAILABLE,
                "reason": f"workbook outcome is not a strict binary value for {project!r}: {outcome!r}",
                "outcomes": {},
            }
        project_id = manifest_names[normalized]
        if project_id in outcomes:
            return {
                "status": Status.UNAVAILABLE,
                "reason": f"workbook has duplicate per-project SWE-agent outcome for {project!r}",
                "outcomes": {},
            }
        outcomes[project_id] = binary_outcome
    expected_ids = {project["id"] for project in crust_projects}
    if set(outcomes) != expected_ids:
        return {
            "status": Status.UNAVAILABLE,
            "reason": (
                "workbook did not provide a complete one-to-one 100-project SWE-agent outcome inventory; "
                f"matched {len(outcomes)} of {len(expected_ids)}"
            ),
            "outcomes": {},
        }
    return {
        "status": Status.MEASURED,
        "reason": "",
        "track": "published_reference_non_replayed",
        "outcomes": outcomes,
    }


def _crust_overlap(
    manifest_by_id: dict[str, dict[str, Any]],
    row_by_key: dict[tuple[str, str, int], dict[str, Any]],
    workbook_outcomes: dict[str, Any],
) -> dict[str, Any]:
    cells = [
        {
            "codeweaver_rep0": bool(cw),
            "recodeagent_replay": bool(rca),
            "swe_agent_workbook": bool(swe),
            "count": 0,
            "swe_agent_track": "published_reference_non_replayed",
        }
        for cw in (False, True) for rca in (False, True) for swe in (False, True)
    ]
    if workbook_outcomes["status"] != Status.MEASURED:
        return {
            "status": workbook_outcomes["status"],
            "reason": workbook_outcomes["reason"],
            "n_triples": 0,
            "cells": cells,
            "swe_agent_track": "published_reference_non_replayed",
        }
    lookup = {(cell["codeweaver_rep0"], cell["recodeagent_replay"], cell["swe_agent_workbook"]): cell for cell in cells}
    excluded = 0
    for project_id, project in manifest_by_id.items():
        if project["tool"] != "crust":
            continue
        cw = row_by_key.get((CODEWEAVER_SYSTEM, project_id, PRIMARY_REPETITION))
        rca = row_by_key.get(("recodeagent", project_id, PRIMARY_REPETITION))
        if cw is None or rca is None:
            excluded += 1
            continue
        cw_outcome = _metric(cw, "compilation_success")
        rca_outcome = _metric(rca, "compilation_success")
        if cw_outcome["status"] != Status.MEASURED or rca_outcome["status"] != Status.MEASURED:
            excluded += 1
            continue
        lookup[(cw_outcome["value"], rca_outcome["value"], workbook_outcomes["outcomes"][project_id])]["count"] += 1
    n_triples = sum(cell["count"] for cell in cells)
    return {
        "status": Status.MEASURED if n_triples else Status.MISSING,
        "reason": "" if n_triples else "no CRUST projects had all three genuinely measured outcomes",
        "n_triples": n_triples,
        "excluded_projects": excluded,
        "cells": cells,
        "swe_agent_track": "published_reference_non_replayed",
    }


def _cost_frontier(
    rows: list[dict[str, Any]],
    *,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    output_rows: list[dict[str, Any]] = []
    for system in ALL_SYSTEMS:
        selected = [row for row in rows if row["system"] == system and row["repetition"] == PRIMARY_REPETITION]
        costs = [
            _metric(row, "actual_cost_nano_aiu")["value"]
            for row in selected
            if _metric(row, "actual_cost_nano_aiu")["status"] == Status.MEASURED
        ]
        correctness = _aggregate_rate(
            selected,
            "project_pass_all",
            resamples=resamples,
            seed=seed + len(output_rows),
        )
        output_rows.append(
            {
                "system": system,
                "track": "measured" if system == CODEWEAVER_SYSTEM else "released_artifact_replay",
                "repetition": PRIMARY_REPETITION,
                "actual_cost_metric": "total_nano_aiu",
                "actual_cost_unit": "nano_aiu",
                "cost_status": Status.MEASURED if costs else Status.UNAVAILABLE,
                "mean_actual_cost": statistics.fmean(costs) if costs else None,
                "n_cost_projects": len(costs),
                "cost_missing_projects": len(selected) - len(costs),
                "cost_partial": bool(costs) and len(costs) != len(selected),
                "project_pass_all_rate": correctness["value"],
                "correctness_status": correctness["status"],
                "correctness_n_projects": correctness["n_projects"],
                "correctness_excluded_projects": correctness["excluded_projects"],
                "correctness_partial": correctness["partial"],
                "published_reference_cost_status": Status.UNAVAILABLE,
                "published_reference_cost_reason": (
                    "Workbook/paper cost is not an actual replay cost and is intentionally "
                    "kept off this measured-cost frontier"
                ),
            }
        )
    comparable = [row for row in output_rows if row["cost_status"] == Status.MEASURED]
    return {
        "status": Status.MEASURED if len(comparable) >= 2 else Status.UNAVAILABLE,
        "reason": (
            "" if len(comparable) >= 2 else
            "fewer than two systems have genuinely measured, same-unit actual costs; "
            "missing replay costs were not mapped to zero"
        ),
        "cost_unit": "nano_aiu",
        "rows": output_rows,
    }


# --------------------------------------------------------------------------- #
# Artifact rendering
# --------------------------------------------------------------------------- #
def _write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    columns = sorted({key for row in rows for key in row})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        flattened = {
            key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
            for key, value in row.items()
        }
        writer.writerow(flattened)
    C.atomic_write_text(path, buffer.getvalue())
    return path


def _latex_escape(value: Any) -> str:
    if value is None:
        return "--"
    text = str(value)
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def _format_rate(value: Any) -> str:
    return "--" if value is None else f"{100.0 * float(value):.1f}\\%"


def _format_ci(value: Any, *, percentage: bool = False) -> str:
    if not value:
        return "--"
    if percentage:
        return f"[{100.0 * value[0]:.1f}, {100.0 * value[1]:.1f}] pp"
    return f"[{value[0]:.3f}, {value[1]:.3f}]"


def _latex_tables(data: dict[str, Any]) -> str:
    summary_rows = [
        row for row in data["codeweaver_repetition_summary"]
        if row["tool"] == "all"
    ]
    paired_rows = [
        row for row in data["primary_paired_comparisons"]
        if row["tool"] == "all"
    ]
    lines = [
        "% Generated by experiments.recodeagent.system_compare; do not treat missing as zero.",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{CodeWeaver variability across preregistered repetitions.}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Metric & $n$ & Mean & Sample SD & 95\% t CI \\",
        r"\midrule",
    ]
    for row in summary_rows:
        lines.append(
            f"{_latex_escape(METRICS[row['metric']])} & {row['n']} & "
            f"{_format_rate(row['mean'])} & "
            f"{_format_rate(row['sample_sd']) if row['sample_sd'] is not None else '--'} & "
            f"{_format_ci(row['ci_95_t'], percentage=True)} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\label{tab:codeweaver-variability}",
        r"\end{table}",
        "",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Primary paired comparison: CodeWeaver repetition 0 versus released ReCodeAgent artifacts.}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Metric & $n$ & CW wins & RCA wins & Ties & $\Delta$ (pp) & Exact/paired result \\",
        r"\midrule",
    ]
    for row in paired_rows:
        if row["metric_kind"] == "binary":
            last = (
                f"$p={row['exact_mcnemar_p_value']:.4g}$"
                if row["exact_mcnemar_p_value"] is not None else "--"
            )
            wins, losses, ties = (
                row["cw_yes_rca_no_wins"], row["rca_yes_cw_no_losses"], row["ties"]
            )
            delta = row["delta_percentage_points"]
        else:
            wilcoxon = row["wilcoxon"]
            last = (
                f"Wilcoxon $p={wilcoxon['p_value']:.4g}$"
                if wilcoxon.get("status") == Status.MEASURED else
                _latex_escape(wilcoxon.get("status"))
            )
            wins, losses, ties = row["cw_wins"], row["rca_losses"], row["ties"]
            delta = row["mean_delta_percentage_points"]
        lines.append(
            f"{_latex_escape(row['metric'])} & {row['n']} & {wins} & {losses} & {ties} & "
            f"{'--' if delta is None else f'{delta:.1f}'} & {last} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\label{tab:primary-paired}",
        r"\end{table}",
        "",
        "% All CIs use a deterministic project-cluster percentile bootstrap "
        f"(seed={data['protocol']['bootstrap_seed']}, resamples={data['protocol']['bootstrap_resamples']}).",
    ]
    return "\n".join(lines) + "\n"


def _pdf_sections(data: dict[str, Any]) -> list[RD.ReportSection]:
    inventory = data["inventory"]
    paired = [row for row in data["primary_paired_comparisons"] if row["tool"] == "all"]
    inventory_rows = [
        [row[key] for key in ("system", "tool", "repetition", "expected", "measured", "unavailable", "error", "missing")]
        for row in inventory
        if row["tool"] == "all"
    ]
    # The inventory is tool-level; construct system/repetition totals for a concise PDF.
    totals: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    for row in inventory:
        bucket = totals[(row["system"], row["repetition"])]
        for key in (
            "expected", "measured", "unavailable", "error", "missing",
            "accounted_missing", "unaccounted_missing",
        ):
            bucket[key] += row[key]
    inventory_rows = [
        [
            system, repetition, counts["expected"], counts["measured"],
            counts["unavailable"], counts["error"], counts["missing"],
            counts["accounted_missing"], counts["unaccounted_missing"],
        ]
        for (system, repetition), counts in sorted(totals.items())
    ]
    paired_rows = []
    for row in paired:
        if row["metric_kind"] == "binary":
            paired_rows.append([
                row["metric"], row["n"], row["cw_yes_rca_no_wins"],
                row["rca_yes_cw_no_losses"], row["ties"],
                "" if row["delta_percentage_points"] is None else f"{row['delta_percentage_points']:.1f}",
                "" if row["exact_mcnemar_p_value"] is None else f"{row['exact_mcnemar_p_value']:.4g}",
            ])
        else:
            paired_rows.append([
                row["metric"], row["n"], row["cw_wins"], row["rca_losses"], row["ties"],
                "" if row["mean_delta_percentage_points"] is None else f"{row['mean_delta_percentage_points']:.1f}",
                row["wilcoxon"]["status"],
            ])
    overlap = data["crust_three_system_overlap"]
    return [
        RD.ReportSection(
            "Design and scope",
            "Primary analysis is preregistered CodeWeaver repetition 0; repetitions 0--2 "
            "characterize variability and are never selected best-of-three. CodeWeaver uses "
            "GPT-5.6 Sol; original paper systems/models and released-artifact replay are "
            "confounded comparisons, not fresh matched-model reruns.",
        ),
        RD.ReportSection(
            "Completeness audit",
            RD.markdown_table(
                [
                    "system", "rep", "expected", "measured", "unavailable", "error",
                    "missing", "accounted missing", "unaccounted missing",
                ],
                inventory_rows,
            ),
        ),
        RD.ReportSection(
            "Primary paired comparison (all tools)",
            RD.markdown_table(
                ["metric", "n", "CW win", "RCA win", "ties", "delta pp", "test"],
                paired_rows,
            ),
        ),
        RD.ReportSection(
            "CRUST three-system overlap",
            (
                f"Status: {overlap['status']}; triples: {overlap['n_triples']}. "
                f"{overlap['reason'] or 'SWE-agent values are labelled published_reference_non_replayed.'}"
            ),
        ),
        RD.ReportSection(
            "Costs",
            f"Measured-cost frontier status: {data['cost_correctness_frontier']['status']}. "
            f"{data['cost_correctness_frontier']['reason'] or 'Only actual same-unit measured costs are shown.'}",
        ),
    ]


# --------------------------------------------------------------------------- #
# Public orchestration
# --------------------------------------------------------------------------- #
def compare_systems(
    *,
    codeweaver_raw_path: Path | str,
    baseline_raw_path: Path | str | Iterable[Path | str],
    manifest_path: Path | str,
    output_root: Path | str,
    codeweaver_failures_path: Path | str | None = None,
    baseline_failures_path: Path | str | Iterable[Path | str] | None = None,
    official_results_workbook: Path | str | None = None,
    variant: str = "full",
    repetitions: int = DEFAULT_REPETITIONS,
    resamples: int = DEFAULT_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    rate_tolerance: float = DEFAULT_RATE_TOLERANCE,
) -> dict[str, Any]:
    """Build all system-comparison artifacts from already normalized records."""
    if repetitions < 1:
        raise ValueError("repetitions must be at least one")
    if resamples < 100:
        raise ValueError("resamples must be at least 100")
    if rate_tolerance < 0:
        raise ValueError("rate_tolerance must not be negative")
    cw_path = Path(codeweaver_raw_path)
    baseline_paths = _input_paths(
        baseline_raw_path, label="baseline_raw_path", required=True
    )
    manifest_file = Path(manifest_path)
    cw_failure_file = Path(codeweaver_failures_path) if codeweaver_failures_path else None
    baseline_failure_files = _input_paths(
        baseline_failures_path, label="baseline_failures_path", required=False
    )
    workbook_file = Path(official_results_workbook) if official_results_workbook else None
    output = Path(output_root)
    manifest, manifest_by_id = _load_manifest(manifest_file)

    cw_records = _read_records(cw_path, label="CodeWeaver raw")
    baseline_records = [
        record
        for index, path in enumerate(baseline_paths, start=1)
        for record in _read_records(path, label=f"baseline replay raw input {index}")
    ]
    cw_rows, cw_excluded = _normalise_raw_rows(
        cw_records, system=CODEWEAVER_SYSTEM, manifest_by_id=manifest_by_id,
        variant=variant, source_label="CodeWeaver raw",
    )
    baseline_by_system = {}
    baseline_excluded = 0
    for system in REPLAY_SYSTEMS:
        subset = [row for row in baseline_records if row.get("system") == system]
        rows, excluded = _normalise_raw_rows(
            subset, system=system, manifest_by_id=manifest_by_id,
            variant=variant, source_label=f"baseline replay raw ({system})",
        )
        baseline_by_system[system] = rows
        baseline_excluded += excluded
    unknown_system_rows = [
        row for row in baseline_records if row.get("system") not in REPLAY_SYSTEMS
    ]
    if unknown_system_rows:
        raise ValueError("baseline replay raw contains row(s) without recodeagent/prior system")

    cw_failure_records = _read_records(cw_failure_file, label="CodeWeaver failures") if cw_failure_file else []
    baseline_failure_records = [
        record
        for index, path in enumerate(baseline_failure_files, start=1)
        for record in _read_records(path, label=f"baseline replay failures input {index}")
    ]
    cw_failures, cw_failure_excluded = _normalise_failure_rows(
        cw_failure_records, default_system=CODEWEAVER_SYSTEM,
        manifest_by_id=manifest_by_id, variant=variant, source_label="CodeWeaver failures",
    )
    baseline_failures, baseline_failure_excluded = _normalise_failure_rows(
        baseline_failure_records, default_system=None,
        manifest_by_id=manifest_by_id, variant=variant, source_label="baseline replay failures",
    )
    rows = [*cw_rows, *baseline_by_system["recodeagent"], *baseline_by_system["prior"]]
    failures = [*cw_failures, *baseline_failures]
    raw_keys = [(row["system"], row["project_id"], row["repetition"]) for row in rows]
    if len(raw_keys) != len(set(raw_keys)):
        raise ValueError("duplicate system/project/repetition key across normalized raw inputs")

    inventory = _inventory(manifest_by_id, rows, failures, repetitions=repetitions)
    inventory_completeness = _inventory_completeness(inventory)
    per_repetition, summaries = _codeweaver_metrics(
        cw_rows, repetitions=repetitions, resamples=resamples, seed=bootstrap_seed
    )
    row_by_key = _by_key(rows)
    paired = _primary_paired_comparisons(
        manifest_by_id, row_by_key, resamples=resamples, seed=bootstrap_seed + 10_000,
        tolerance=rate_tolerance,
    )
    crust_projects = [project for project in manifest_by_id.values() if project["tool"] == "crust"]
    workbook_outcomes = extract_swe_agent_workbook_outcomes(workbook_file, crust_projects)
    overlap = _crust_overlap(manifest_by_id, row_by_key, workbook_outcomes)
    frontier = _cost_frontier(rows, resamples=resamples, seed=bootstrap_seed + 20_000)

    input_hashes = {
        "manifest": _input_hash(manifest_file),
        "codeweaver_raw": _input_hash(cw_path),
        "codeweaver_failures": _input_hash(cw_failure_file),
        "baseline_raw": _provenance_input_hashes(baseline_paths),
        "baseline_failures": _provenance_input_hashes(baseline_failure_files),
        "official_results_workbook_reference_only": _input_hash(workbook_file),
    }
    data = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": C.utcnow_iso(),
        "protocol": {
            "benchmark_expected_projects": C.EXPECTED_TOTAL_PROJECTS,
            "manifest_projects": len(manifest_by_id),
            "tool_counts": {
                tool: sum(project["tool"] == tool for project in manifest_by_id.values())
                for tool in TOOLS
            },
            "variant": variant,
            "primary_codeweaver_repetition": PRIMARY_REPETITION,
            "configured_codeweaver_repetitions": repetitions,
            "bootstrap_resamples": resamples,
            "bootstrap_seed": bootstrap_seed,
            "rate_tolerance": rate_tolerance,
        },
        "input_row_accounting": {
            "codeweaver_raw_selected": len(cw_rows),
            "codeweaver_raw_excluded_nonselected_variant": cw_excluded,
            "baseline_raw_selected": len(baseline_by_system["recodeagent"]) + len(baseline_by_system["prior"]),
            "baseline_raw_excluded_nonselected_variant": baseline_excluded,
            "baseline_raw_input_count": len(baseline_paths),
            "baseline_failure_input_count": len(baseline_failure_files),
            "failure_rows_retained": len(failures),
            "failure_rows_excluded_nonselected_variant": cw_failure_excluded + baseline_failure_excluded,
        },
        "inventory": inventory,
        "inventory_completeness": inventory_completeness,
        "codeweaver_per_repetition_metrics": per_repetition,
        "codeweaver_repetition_summary": summaries,
        "primary_paired_comparisons": paired,
        "crust_three_system_overlap": overlap,
        "cost_correctness_frontier": frontier,
    }
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": C.utcnow_iso(),
        "inputs_sha256": input_hashes,
        "primary_analysis": {
            "codeweaver_repetition": PRIMARY_REPETITION,
            "statement": (
                "Repetition 0 is the preregistered primary comparison. Repetitions 0, 1, and 2 "
                "are summarized as variability; no best-of-three selection is performed."
            ),
        },
        "model_and_execution_confounding": {
            "codeweaver_model": "GPT-5.6 Sol",
            "original_paper_reference_model": C.PAPER_REFERENCE_MODEL,
            "statement": (
                "CodeWeaver GPT-5.6 Sol is not model-matched to the original systems/models. "
                "Released ReCodeAgent/prior outputs are post-hoc artifact replay measurements, "
                "not fresh runs. Results are cross-system observational comparisons."
            ),
        },
        "swe_agent": {
            "released_artifacts_available": False,
            "statement": (
                "Released SWE-agent CRUST targets are unavailable and were never fabricated. "
                "The optional workbook can appear only as the separate "
                "published_reference_non_replayed per-project compilation track."
            ),
            "workbook_overlap_status": overlap["status"],
            "workbook_overlap_reason": overlap["reason"],
        },
        "denominators": {
            "binary_rates": "genuinely measured project-level binary values only",
            "validated_micro": (
                "sum(min(validated_tests_passed, validated_tests_expected)) / "
                "sum(validated_tests_expected) over eligible projects; "
                "an explicitly measured zero paper-rate with unavailable passed count is retained as a "
                "documented zero numerator per collect.compute_paper_pass_rate; passes above the fixed "
                "denominator are retained in raw counts but cannot produce a rate above 1"
            ),
            "validated_macro": (
                "mean of genuinely measured per-project validated_tests_pass_rate values, "
                "bounded to [0, 1]"
            ),
            "paired": "intersection of genuinely measured CodeWeaver rep0 and replayed ReCodeAgent projects",
        },
        "methods": {
            "repetition_summary": "mean, sample SD (n-1), two-sided 95% Student-t interval",
            "primary_rate_ci": (
                f"deterministic percentile project-cluster bootstrap, {resamples} resamples, "
                f"seed {bootstrap_seed}"
            ),
            "binary_test": "two-sided exact binomial McNemar test on discordant pairs",
            "continuous_test": "SciPy Wilcoxon signed-rank only when available; otherwise explicit unavailable",
        },
        "rendering": {
            "pdf": "reportlab when installed; otherwise a .pdf.unavailable.txt marker",
            "latex": "system_comparison_tables.tex",
        },
        "environment": C.collect_provenance(model="GPT-5.6 Sol", probe_toolchains=False),
    }

    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "analysis_json": output / "system_comparison.json",
        "inventory_csv": output / "system_comparison_inventory.csv",
        "metrics_csv": output / "system_comparison_metrics.csv",
        "paired_csv": output / "system_comparison_paired.csv",
        "crust_overlap_csv": output / "system_comparison_crust_overlap.csv",
        "frontier_csv": output / "system_comparison_cost_frontier.csv",
        "failure_evidence_csv": output / "system_comparison_failure_evidence.csv",
        "latex": output / "system_comparison_tables.tex",
        "pdf": output / "system_comparison.pdf",
        "provenance": output / "system_comparison_provenance.json",
    }
    C.atomic_write_json(paths["analysis_json"], data)
    _write_csv(inventory, paths["inventory_csv"])
    _write_csv([*per_repetition, *summaries], paths["metrics_csv"])
    _write_csv(paired, paths["paired_csv"])
    _write_csv(overlap["cells"], paths["crust_overlap_csv"])
    _write_csv(frontier["rows"], paths["frontier_csv"])
    _write_csv(failures, paths["failure_evidence_csv"])
    C.atomic_write_text(paths["latex"], _latex_tables(data))
    pdf_rendered = RD.render_pdf_report(
        "Cross-System ReCodeAgent Comparison",
        _pdf_sections(data),
        paths["pdf"],
    )
    provenance["rendering"]["pdf_rendered"] = pdf_rendered
    provenance["outputs"] = {name: str(path.name) for name, path in paths.items()}
    C.atomic_write_json(paths["provenance"], provenance)
    return {
        "data": data,
        "provenance": provenance,
        "paths": paths,
        "pdf_rendered": pdf_rendered,
    }


run_system_comparison = compare_systems


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m experiments.recodeagent compare-systems",
        description=(
            "Compare normalized CodeWeaver runs with released ReCodeAgent/prior artifact replays; "
            "never fabricates missing SWE-agent outputs or costs."
        ),
    )
    parser.add_argument("--codeweaver-raw", required=True, help="collect.py raw_runs.csv or raw_runs.jsonl")
    parser.add_argument(
        "--baseline-raw", action="append", required=True,
        help="baseline_replay.py baseline_raw_runs.csv or .jsonl; repeat for disjoint outputs",
    )
    parser.add_argument("--manifest", required=True, help="exact benchmark manifest.json")
    parser.add_argument("--output-root", required=True, help="comparison artifact directory")
    parser.add_argument("--codeweaver-failures", default=None, help="optional collect.py failures.csv")
    parser.add_argument(
        "--baseline-failures", action="append", default=None,
        help="optional baseline_replay.py baseline_failures.csv; repeat for disjoint outputs",
    )
    parser.add_argument(
        "--official-results-workbook", default=None,
        help=(
            "optional official results.xlsx, reference-only; SWE-agent overlap is emitted only "
            "when exact per-project workbook outcomes can be extracted"
        ),
    )
    parser.add_argument("--variant", default="full", help="normalized variant to compare (default: full)")
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS,
                        help="expected CodeWeaver repetitions for the audit (default: 3)")
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES,
                        help=f"deterministic bootstrap resamples (default: {DEFAULT_RESAMPLES})")
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED,
                        help=f"deterministic bootstrap seed (default: {DEFAULT_BOOTSTRAP_SEED})")
    parser.add_argument("--rate-tolerance", type=float, default=DEFAULT_RATE_TOLERANCE,
                        help="absolute tie tolerance for paired project test rates")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compare_systems(
        codeweaver_raw_path=args.codeweaver_raw,
        baseline_raw_path=args.baseline_raw,
        manifest_path=args.manifest,
        output_root=args.output_root,
        codeweaver_failures_path=args.codeweaver_failures,
        baseline_failures_path=args.baseline_failures,
        official_results_workbook=args.official_results_workbook,
        variant=args.variant,
        repetitions=args.repetitions,
        resamples=args.resamples,
        bootstrap_seed=args.bootstrap_seed,
        rate_tolerance=args.rate_tolerance,
    )
    print(
        "[compare-systems] "
        f"{len(result['data']['primary_paired_comparisons'])} paired summaries; "
        f"PDF {'rendered' if result['pdf_rendered'] else 'unavailable (marker written)'} -> {args.output_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
