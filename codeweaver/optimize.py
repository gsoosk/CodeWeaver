"""Burr actions for the OPTIMIZE phase: benchmark <-> optimize, then one conformance milestone.

CodeWeaver runs two phases. The **translation phase** (analyze -> scope -> plan ->
milestone loop -> parity) makes the port *correct*. The **optimization phase**,
which this module implements, makes an already-correct port *faster*. It is
**off by default** -- enable it with ``[optimization].enabled`` or ``--optimize``.

  parity -> benchmark -> optimize -> benchmark -> ... (max_opt_rounds)
         -> opt_repair -> select_milestone -> translate <-> validate -> terminal

  benchmark    Benchmarker agent runs the project's benchmark command and writes
               the benchmark artifact                              (measures only)
  optimize     Optimizer agent makes ONE small focused change set to the working
               copy, guided by the measurements, and proves the UNIT tests pass
  opt_repair   appends a final milestone that re-runs the ENTIRE test suite
               through the normal translate <-> validate repair loop

Why the phase is gated on parity
--------------------------------
Tuning a translation with known gaps tunes code that is still going to change,
so the graph only enters here once the parity verifier reports complete.

Why the full-suite gate runs at the END, not per round
------------------------------------------------------
An earlier design validated every round against the full suite and REVERTED the
round on failure. Measured over 20 real rounds that was actively harmful: one
flaky test failed in 14 of them, **including 7 rounds where the optimizer changed
nothing at all** -- an empty change set cannot cause a regression, so those
reverts discarded work for a failure the round did not produce. 16 of 20 rounds
were thrown away.

So rounds ACCUMULATE. The Optimizer runs the (cheap, deterministic) unit tests
itself every round, and the expensive suite runs ONCE at the end as a normal
milestone -- where a failure is REPAIRED by the Translator over ``max_iter``
attempts instead of thrown away. A flaky failure then costs one repair attempt
that finds nothing, not an entire optimisation.

The working copy is snapshotted ONCE before the phase begins, so the
pre-optimisation tree stays recoverable if the conformance milestone cannot
converge.
"""
from __future__ import annotations

import json
import numbers
import os
import shutil
import time

from burr.core import action

from . import config as C
from . import prompts
from .actions import _invoke, _log_agent, _read_json
from .config import Milestone


def _is_mock() -> bool:
    from .copilot import is_mock
    return is_mock()


def scenarios_for(state) -> list[str]:
    """The scenario ids this run is focused on, or [] for the whole suite.

    Both the Benchmarker and the Optimizer resolve the set through here so they
    cannot disagree about the target: optimising for a scenario nobody measured,
    or measuring one nobody is optimising, is worse than not scoping at all.
    ``CODEWEAVER_BENCH_SCENARIOS`` overrides for one-off runs.
    """
    raw = os.environ.get("CODEWEAVER_BENCH_SCENARIOS", "") or (state["bench_scenarios"] or "")
    return [s for s in raw.replace(",", " ").split() if s]


# --------------------------------------------------------------------------- #
# Artifacts
# --------------------------------------------------------------------------- #
def _history(cfg) -> list:
    data = _read_json(cfg.optimize_history_path)
    return data.get("rounds", []) if isinstance(data, dict) else []


def _append_history(cfg, entry: dict) -> list:
    rounds = _history(cfg)
    rounds.append(entry)
    p = cfg.optimize_history_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"rounds": rounds}, indent=2), encoding="utf-8")
    return rounds


def bench_summary(bench: dict) -> dict:
    """Flatten a benchmark artifact into the few scalars the loop records per round.

    Deliberately generic and shallow -- the Optimizer reads the full artifact
    itself; this exists only so the orchestrator can record a trend WITHOUT
    interpreting results, which is the agents' job. It expects the conventional
    shape ``{"records": [{"scenario", "variant", "result": {...}}]}`` and lifts
    every numeric leaf of ``result`` to ``<scenario>.<metric>[.<variant>]``.
    Anything it does not recognise is simply not summarised; the artifact itself
    is still handed to the Optimizer in full.
    """
    if not isinstance(bench, dict):
        return {}
    out: dict = {}
    prov = bench.get("provenance")
    if isinstance(prov, dict):
        for k in ("target", "crate", "sha256_16", "sha"):
            if k in prov:
                out[f"provenance.{k}"] = prov[k]
    for rec in bench.get("records", []) or []:
        if not isinstance(rec, dict):
            continue
        scen = rec.get("scenario") or rec.get("name")
        res = rec.get("result")
        if not scen or not isinstance(res, dict):
            continue
        var = rec.get("variant")
        for metric, value in res.items():
            # bool is a numbers.Number subclass; a flag is not a measurement.
            if isinstance(value, bool) or not isinstance(value, numbers.Number):
                continue
            key = f"{scen}.{metric}" + (f".{var}" if var else "")
            out[key] = value
    return out


# --------------------------------------------------------------------------- #
# Working-copy snapshot
# --------------------------------------------------------------------------- #
# Directories that are build output, not source: large, regenerable, and
# restoring a stale one is worse than rebuilding.
_BUILD_DIRS = ("target", "build", "dist", "node_modules", "__pycache__",
               ".venv", ".gradle", ".mypy_cache", ".pytest_cache")


def snapshot_working_copy(cfg) -> bool:
    """Copy the working copy aside so the pre-optimisation tree stays recoverable."""
    wc = cfg.working_copy_path
    if wc is None or not wc.exists():
        return False
    dest = cfg.snapshot_path
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(wc, dest, ignore=shutil.ignore_patterns(*_BUILD_DIRS, "*.tmp"))
    return True


def restore_working_copy(cfg) -> bool:
    """Roll the working copy back to the pre-optimisation snapshot.

    Not used by the graph -- rounds accumulate and regressions are repaired, not
    reverted (see the module docstring). This is the manual escape hatch for when
    the conformance milestone cannot converge and the port must be recovered.
    """
    src, wc = cfg.snapshot_path, cfg.working_copy_path
    if wc is None or not src.exists():
        return False
    for item in wc.iterdir():
        # Leave build output in place: it is not in the snapshot, and deleting it
        # forces a full rebuild for no benefit.
        if item.name in _BUILD_DIRS:
            continue
        shutil.rmtree(item, ignore_errors=True) if item.is_dir() else item.unlink(missing_ok=True)
    for item in src.iterdir():
        dst = wc / item.name
        shutil.copytree(item, dst) if item.is_dir() else shutil.copy2(item, dst)
    return True


# --------------------------------------------------------------------------- #
# Mock (offline) responses
# --------------------------------------------------------------------------- #
def _mock_bench(cfg, round_no: int) -> dict:
    """Synthetic benchmark artifact that improves each round, so the loop wiring
    and the trend logic can be exercised without a real harness."""
    scale = max(0.55, 1.0 - 0.12 * round_no)
    doc = {
        "run": {"id": f"mock-{round_no}"},
        "provenance": {"target": "working_copy", "sha256_16": f"mock{round_no:012d}",
                       "built_this_run": True},
        "records": [
            {"scenario": "S1", "variant": "target",
             "result": {"ops": int(28000 * scale), "p50_ms": round(36.9 * scale, 2)}},
            {"scenario": "S1", "variant": "reference",
             "result": {"ops": 12900, "p50_ms": 21.4}},
        ],
    }
    cfg.bench_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.bench_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc


def _mock_optimize(cfg, round_no: int) -> dict:
    doc = {"round": round_no, "title": f"mock optimisation {round_no}",
           "files": ["src/hot_path"], "rationale": "mock",
           "expected_effect": "mock", "behaviour_risk": "none", "unit_tests": "passed"}
    cfg.optimize_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.optimize_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
@action(reads=["opt_round", "bench_scenarios"],
        writes=["bench", "bench_history", "last_agent"])
def benchmark(state, __tracer) -> dict:
    """Benchmarker Agent: run the project's benchmark command against the working
    copy and read back the artifact it wrote. Measures only -- it cannot edit."""
    cfg = C.active()
    round_no = state["opt_round"]

    if _is_mock():
        bench = _mock_bench(cfg, round_no)
        hist = list(state["bench_history"]) + [{"round": round_no, **bench_summary(bench)}]
        return state.update(bench=bench, bench_history=hist, last_agent="benchmarker")

    scen = scenarios_for(state)
    runtime = prompts.benchmark_runtime(cfg, round_no, scen)
    prompt = prompts.render("benchmark", cfg, **runtime)
    res = _invoke(cfg, "benchmarker", prompt)
    _log_agent(__tracer, stage=f"benchmark:round{round_no}", prompt=prompt, result=res)

    bench = _read_json(cfg.bench_path)
    if not bench:
        print(f"[codeweaver] optimize round {round_no}: benchmarker produced no "
              f"{cfg.optimize.bench_artifact}")
    hist = list(state["bench_history"]) + [{"round": round_no, **bench_summary(bench)}]
    return state.update(bench=bench, bench_history=hist, last_agent="benchmarker")


@action(reads=["opt_round", "max_opt_rounds", "bench", "bench_history", "bench_scenarios"],
        writes=["optimize", "opt_round", "last_agent"])
def optimize(state, __tracer) -> dict:
    """Optimizer Agent: ONE small focused change set to the working copy, guided by
    the measurements, without altering observable behaviour."""
    cfg = C.active()
    round_no = state["opt_round"]

    # Snapshot ONCE, before the first round touches anything. NOT per round:
    # rounds accumulate deliberately, so re-snapshotting would overwrite the only
    # pristine copy with an already-optimised one.
    if round_no <= 1:
        if snapshot_working_copy(cfg):
            print(f"[codeweaver] optimize: snapshotted the working copy to "
                  f"{cfg.snapshot_path}")

    if _is_mock():
        doc = _mock_optimize(cfg, round_no)
        _append_history(cfg, {"round": round_no, "title": doc["title"],
                              "files": doc["files"], "rationale": doc["rationale"],
                              "expected_effect": doc["expected_effect"],
                              "bench_before": (state["bench_history"] or [{}])[-1],
                              "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
        return state.update(optimize=doc, opt_round=round_no + 1, last_agent="optimizer")

    scen = scenarios_for(state)
    runtime = prompts.optimize_runtime(cfg, round_no, state["max_opt_rounds"], scen)
    prompt = prompts.render("optimize", cfg, **runtime)
    res = _invoke(cfg, "optimizer", prompt)
    _log_agent(__tracer, stage=f"optimize:round{round_no}", prompt=prompt, result=res)

    doc = _read_json(cfg.optimize_path)
    _append_history(cfg, {
        "round": round_no,
        "title": doc.get("title", "?"),
        "files": doc.get("files", []),
        "rationale": doc.get("rationale", ""),
        "expected_effect": doc.get("expected_effect", ""),
        "bench_before": (state["bench_history"] or [{}])[-1],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    if __tracer is not None:
        try:
            __tracer.log_attributes(opt_round=round_no, opt_title=doc.get("title", "?"),
                                    opt_files=doc.get("files", []),
                                    bench_history=state["bench_history"])
        except Exception:
            pass
    return state.update(optimize=doc, opt_round=round_no + 1, last_agent="optimizer")


@action(reads=["opt_round", "bench_history"],
        writes=["num_milestones", "last_idx", "milestone_idx", "milestone_passed",
                "milestone_concluded", "iter_count", "opt_repairing", "opt_done",
                "done", "history"])
def opt_repair(state, __tracer) -> dict:
    """Close the optimize phase by appending ONE milestone that re-proves the
    optimised working copy against the ENTIRE test suite.

    The rounds before this were gated only by the unit tests, so this is the first
    time the accumulated optimisations meet the authoritative oracle. Handing that
    to the normal translate <-> validate loop (rather than a bespoke check) buys the
    repair budget, the skips handling and the report format the translation phase
    already has -- and means a regression is FIXED rather than discarded, which is
    the whole reason the per-round revert was removed.

    ``full_suite=True``: the cumulative selector covers only tests some milestone
    listed, but a performance change can regress anything.
    """
    cfg = C.active()
    ms = list(cfg.milestones)
    base = len(ms)
    nid = f"M{base}"
    rounds_done = max(0, state["opt_round"] - 1)
    trend = state["bench_history"] or []

    ms.append(Milestone(
        nid, "Post-optimisation conformance",
        f"{rounds_done} optimisation round(s) changed the {cfg.target_language} "
        "implementation for performance while only the unit tests were gating. "
        "Re-prove the ENTIRE test suite against the optimised working copy and fix "
        "anything that regressed.\n\n"
        "Repair by correcting the implementation so the original behaviour is "
        "restored, keeping the performance work wherever that is possible. Where an "
        "optimisation cannot be made correct, undo THAT optimisation rather than "
        f"weakening a test -- {cfg.optimize_history_path} records what each round "
        "changed and why. Never edit the tests: they are the oracle the optimisation "
        "has to survive.",
        tests=[], origin="optimize", full_suite=True,
    ))
    cfg.milestones = ms
    cfg.save_milestones()

    print(f"[codeweaver] optimize: {rounds_done} round(s) done; appended {nid} "
          "(post-optimisation conformance, ENTIRE suite)")
    if trend:
        print(f"[codeweaver] optimize: first {json.dumps(trend[0], sort_keys=True, default=str)}")
        print(f"[codeweaver] optimize: last  {json.dumps(trend[-1], sort_keys=True, default=str)}")

    if __tracer is not None:
        try:
            __tracer.log_attributes(opt_rounds_done=rounds_done, repair_milestone=nid,
                                    bench_history=trend)
        except Exception:
            pass

    return state.update(
        num_milestones=base + 1,
        last_idx=base,           # the conformance milestone is now last
        milestone_idx=base,      # ...and is the one to run next
        milestone_passed=False,
        milestone_concluded=False,
        iter_count=0,
        opt_repairing=True,      # routes validate -> terminal instead of back to parity
        opt_done=True,           # parity must not re-enter the optimize phase
        done=False,              # not finished until the conformance milestone concludes
    ).append(history={"milestone": "OPTIMIZE", "iter": rounds_done, "passed": True})
