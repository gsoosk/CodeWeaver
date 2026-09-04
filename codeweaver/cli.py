"""CodeWeaver command-line interface.

    codeweaver run       --config codeweaver.toml [--app-id ID] [--max-iter N] [--mock]
    codeweaver check     --config codeweaver.toml    # offline mock smoke tests
    codeweaver milestones --config codeweaver.toml    # print the milestone matrix
    codeweaver install-agents                          # mirror agent profiles to ~/.copilot/agents
    codeweaver init      [DIR]                          # scaffold a new codeweaver.toml + brief
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
def _cmd_run(args) -> int:
    # Set the mock flag BEFORE importing modules that read it, so `--mock` works
    # regardless of import order (is_mock() also re-checks at call time).
    if args.mock:
        os.environ["CODEWEAVER_MOCK"] = "1"

    from . import config as C
    from .app import build_application, state_from_existing_pipeline

    cfg = C.load(args.config)
    if args.pipeline_dir:
        os.environ["CODEWEAVER_PIPELINE_DIR"] = str(args.pipeline_dir)
        cfg.pipeline_dir = str(args.pipeline_dir)
    if args.max_parity_rounds is not None:
        cfg.max_parity_rounds = args.max_parity_rounds
    # let the mock discover the artifact names + pipeline dir
    os.environ.setdefault("CODEWEAVER_PIPELINE_DIR", str(cfg.pipeline_path))
    os.environ["CODEWEAVER_ANALYSIS_ARTIFACT"] = cfg.analysis_artifact
    os.environ["CODEWEAVER_PLAN_ARTIFACT"] = cfg.plan_artifact
    os.environ["CODEWEAVER_REPORT_ARTIFACT"] = cfg.report_artifact
    os.environ["CODEWEAVER_MILESTONES_ARTIFACT"] = cfg.milestones_artifact
    os.environ["CODEWEAVER_PARITY_ARTIFACT"] = cfg.parity_artifact
    os.environ["CODEWEAVER_SKIPS_ARTIFACT"] = cfg.skips_artifact

    app_id = args.app_id or f"{cfg.slug}-{uuid.uuid4().hex[:8]}"
    db_path = args.db or cfg.resolved_db_path
    max_iter = args.max_iter if args.max_iter is not None else cfg.max_iter

    bootstrap_state = None
    entrypoint = "analyze"

    # --- optimize phase (phase 2): OFF unless asked for -------------------- #
    # Two ways to ask: --optimize (intent, uses the configured/default budget) and
    # --max-opt-rounds N (the count). The count wins when both are given, so
    # `--optimize --max-opt-rounds 0` turns it back off.
    if args.max_opt_rounds is not None:
        max_opt_rounds = args.max_opt_rounds
        if max_opt_rounds < 0:
            print("[codeweaver] error: --max-opt-rounds must be >= 0", file=sys.stderr)
            return 2
    elif args.optimize or args.start_benchmark:
        max_opt_rounds = cfg.optimize.max_rounds or 5
    else:
        max_opt_rounds = cfg.opt_rounds          # config default (0 unless enabled)
    if max_opt_rounds > 0 and not cfg.optimize.benchmark_cmd:
        print("[codeweaver] error: the optimize phase needs [optimization].benchmark_cmd "
              "-- it has nothing to measure without it", file=sys.stderr)
        return 2
    if max_opt_rounds > 0 and not cfg.parity_check:
        print("[codeweaver] error: the optimize phase runs after parity confirms the "
              "translation is complete, but execution.parity_check is false",
              file=sys.stderr)
        return 2

    bench_scenarios = " ".join((args.benchmarks or "").replace(",", " ").split())
    if bench_scenarios and max_opt_rounds == 0:
        print("[codeweaver] error: --benchmarks only affects the optimize phase, which "
              "is off; add --optimize (or --max-opt-rounds N)", file=sys.stderr)
        return 2
    if not bench_scenarios:
        bench_scenarios = " ".join(cfg.optimize.scenarios.replace(",", " ").split())

    # --- partway-start entries (mutually exclusive) ------------------------- #
    starts = [(n, v) for n, v in (("--start-milestone", args.start_milestone),
                                  ("--start-parity", args.start_parity),
                                  ("--start-benchmark", args.start_benchmark)) if v]
    if len(starts) > 1:
        print(f"[codeweaver] error: {', '.join(n for n, _ in starts)} are mutually "
              "exclusive", file=sys.stderr)
        return 2
    if args.start_parity and not cfg.parity_check:
        print("[codeweaver] error: --start-parity needs the parity stage "
              "(execution.parity_check = true)", file=sys.stderr)
        return 2
    if args.start_benchmark and max_opt_rounds == 0:
        print("[codeweaver] error: --start-benchmark starts AT the optimize phase, so "
              "a zero round budget would leave nothing to run", file=sys.stderr)
        return 2

    entry = ("benchmark" if args.start_benchmark else
             "parity" if args.start_parity else "milestone")
    if starts:
        try:
            bootstrap_state = state_from_existing_pipeline(
                cfg, args.start_milestone, max_iter=max_iter,
                max_parity_rounds=cfg.max_parity_rounds, entry=entry,
                max_opt_rounds=max_opt_rounds, bench_scenarios=bench_scenarios)
        except ValueError as e:
            print(f"[codeweaver] error: {e}", file=sys.stderr)
            return 2
        entrypoint = {"benchmark": "benchmark", "parity": "parity",
                      "milestone": "select_milestone"}[entry]

    app = build_application(cfg, app_id, max_iter=max_iter, db_path=args.db,
                            bootstrap_state=bootstrap_state,
                            default_entrypoint=entrypoint,
                            max_opt_rounds=max_opt_rounds,
                            bench_scenarios=bench_scenarios)

    mock_on = os.environ.get("CODEWEAVER_MOCK") == "1"
    print(f"[codeweaver] project={cfg.name} app_id={app_id} mock={mock_on} db={db_path}")
    if max_opt_rounds > 0:
        focus = f" scenarios={bench_scenarios}" if bench_scenarios else " scenarios=(all)"
        print(f"[codeweaver] optimize phase ON: {max_opt_rounds} round(s){focus}; "
              "closes with a full-suite conformance milestone")
    if starts:
        where = {"benchmark": "the optimize phase (benchmark)",
                 "parity": "the parity verifier",
                 "milestone": f"milestone {args.start_milestone}"}[entry]
        if app.state["last_agent"] == "pipeline-bootstrap":
            skipped_stages = {
                "benchmark": "analyze/scope/plan, the milestone loop and parity",
                "parity": "analyze/scope/plan and the milestone loop",
                "milestone": "analyze/scope/plan",
            }[entry]
            print(f"[codeweaver] starting from existing artifacts at {where}; "
                  f"{skipped_stages} are skipped")
            if entry == "benchmark":
                print("[codeweaver] NOTE: --start-benchmark ASSERTS the translation is "
                      "complete and correct. Pointed at an unfinished one it optimises "
                      "code that is still going to change.")
        else:
            flag = starts[0][0]
            print(f"[codeweaver] persisted state exists for app_id={app_id}; resuming it "
                  f"({flag} only initializes a NEW app-id)")
    print(f"[codeweaver] loaded state at startup: milestone_idx={app.state['milestone_idx']} "
          f"history_len={len(app.state['history'])}  (idx>0 or history => resumed, not restarted)")
    last_action, _result, final_state = app.run(halt_after=["terminal"])
    skipped = final_state.get("skipped") or []
    print(f"[codeweaver] finished at {last_action}: done={final_state['done']} "
          f"milestone_idx={final_state['milestone_idx']} "
          f"parity_round={final_state.get('parity_round', 0)} "
          f"parity_complete={final_state.get('parity_complete', False)} "
          f"skipped={skipped or '[]'}")
    for h in final_state["history"]:
        flag = "  GAVE-UP/SKIPPED" if h.get("gave_up") else ""
        if h.get("retry_for"):
            flag += f"  [retry for {h['retry_for']}]"
        print(f"    {h['milestone']}  iter={h['iter']}  passed={h['passed']}{flag}")
    if max_opt_rounds > 0:
        rounds_done = max(0, final_state.get("opt_round", 1) - 1)
        trend = final_state.get("bench_history") or []
        print(f"[codeweaver] optimize: {rounds_done} round(s) run")
        if len(trend) >= 2:
            print(f"    first: {json.dumps(trend[0], sort_keys=True, default=str)}")
            print(f"    last : {json.dumps(trend[-1], sort_keys=True, default=str)}")
        if cfg.snapshot_path.exists():
            print(f"    pre-optimisation snapshot: {cfg.snapshot_path}")
    if skipped:
        print(f"[codeweaver] WARNING: {len(skipped)} milestone(s) skipped after exhausting the "
              f"repair budget: {skipped}. The parity verifier gave deferred tests one retry.")
    from .actions import _permanent_skips
    perm = _permanent_skips()
    if perm:
        print(f"[codeweaver] PERMANENTLY SKIPPED (failed even after a retry milestone): {perm}")
    return 0 if final_state["done"] else 1


# --------------------------------------------------------------------------- #
# check  (offline mock smoke: happy / repair / budget / resume)
# --------------------------------------------------------------------------- #
def _run_pipeline(config_path: str, app_id: str, extra_env: dict, max_iter=None,
                  extra_args: list[str] | None = None) -> int:
    env = dict(os.environ)
    env["CODEWEAVER_MOCK"] = "1"
    env.update({k: str(v) for k, v in extra_env.items()})
    cmd = [sys.executable, "-m", "codeweaver", "run", "--config", config_path,
           "--app-id", app_id, "--mock"]
    if max_iter is not None:
        cmd += ["--max-iter", str(max_iter)]
    cmd += extra_args or []
    return subprocess.run(cmd, env=env).returncode


def _assert_implement_first(pipeline) -> None:
    """Every milestone's FIRST translate must run in IMPLEMENT mode.

    A give-up leaves the failing report in state; if select_milestone does not clear
    it, the NEXT milestone's first translate wrongly starts in REPAIR mode.
    """
    marker = pipeline / "translate.marker"
    if not marker.exists():
        print("  [check] WARNING: no translate.marker to verify translate modes")
        return
    seen, bad = set(), []
    for line in marker.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        mid, mode = line.rsplit(":", 1)
        if mid not in seen:
            seen.add(mid)
            if mode != "IMPLEMENT":
                bad.append(line)
    if bad:
        print(f"  [check] FAIL: milestone(s) started in REPAIR mode (stale report): {bad}")
    else:
        print(f"  [check] OK: all {len(seen)} milestone(s) started in IMPLEMENT mode")


def _report_skips(cfg, label: str) -> None:
    """Show what a give-up actually deferred, and the gate clause it renders to."""
    from . import milestones as M

    try:
        data = json.loads((cfg.pipeline_path / cfg.skips_artifact).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        print(f"  [check] FAIL ({label}): no {cfg.skips_artifact} written by the give-up path")
        return
    ids = [t for t in data.get("tests_to_skip", []) if t] or \
          [t for t in data.get("retried", []) if t]
    if not ids:
        print(f"  [check] FAIL ({label}): {cfg.skips_artifact} recorded no deferred test")
        return
    clause = M.skip_exclusion(cfg, ids) or "(no skip_exclude_template -> agent-only)"
    print(f"  [check] OK ({label}): deferred {ids} -> gate clause: {clause}")


def _report_optimize(cfg, label: str, *, expect_rounds: int) -> None:
    """Assert the optimize phase ran the expected rounds, appended a full_suite
    conformance milestone, and left a snapshot + history behind."""
    ok = True
    hist_p = cfg.optimize_history_path
    try:
        rounds = json.loads(hist_p.read_text(encoding="utf-8")).get("rounds", [])
    except (ValueError, OSError):
        rounds, ok = [], False
        print(f"  [check] FAIL ({label}): no {cfg.optimize.history_artifact}")
    if rounds and len(rounds) != expect_rounds:
        ok = False
        print(f"  [check] FAIL ({label}): {len(rounds)} round(s) recorded, "
              f"expected {expect_rounds}")

    cfg.load_generated_milestones()
    full = [m for m in cfg.milestones if m.full_suite]
    if len(full) != 1:
        ok = False
        print(f"  [check] FAIL ({label}): expected exactly 1 full_suite milestone, "
              f"got {len(full)}")
    elif full[0].origin != "optimize":
        ok = False
        print(f"  [check] FAIL ({label}): conformance milestone origin is "
              f"{full[0].origin!r}, expected 'optimize'")

    if ok:
        mid = full[0].id if full else "?"
        print(f"  [check] OK ({label}): {len(rounds)} round(s), appended {mid} "
              f"(full_suite, origin=optimize)"
              + (f", snapshot at {cfg.optimize.snapshot_dir}"
                 if cfg.snapshot_path.exists() else ""))


def _optimize_config(cfg, path: Path, rounds: int) -> Path:
    """Write a sibling config with the optimize phase turned ON, so the default-off
    behaviour of the shipped example is never mutated by the check run."""
    import tomllib
    raw = path.read_text(encoding="utf-8")
    out = path.parent / "_check_optimize.toml"
    out.write_text(
        raw + "\n\n[optimization]\nenabled = true\n"
              f"max_rounds = {rounds}\n"
              'benchmark_cmd = "bash tools/bench.sh {working_copy} --out {bench} {scenarios}"\n'
              "scenario_template = '--scenario {scenarios_csv}'\n",
        encoding="utf-8")
    tomllib.loads(out.read_text(encoding="utf-8"))   # fail fast on a bad template
    return out


def _cmd_check(args) -> int:
    from . import config as C

    cfg = C.load(args.config)
    pipeline = cfg.pipeline_path
    ms = cfg.milestones
    if ms:
        first = ms[1].id if len(ms) > 1 else ms[0].id
        mid_ms = ms[min(3, len(ms) - 1)].id
    else:
        # auto-milestones: the mock scoper emits M0,M1,M2 by default.
        first, mid_ms = "M1", "M2"

    def reset():
        purge = [pipeline / "burr.db",
                 pipeline / "translate.marker",
                 pipeline / ".mock_parity_attempts",
                 pipeline / cfg.parity_artifact,
                 pipeline / cfg.skips_artifact,
                 pipeline / cfg.optimize.bench_artifact,
                 pipeline / cfg.optimize.optimize_artifact,
                 pipeline / cfg.optimize.history_artifact]
        purge += list(pipeline.glob(".mock_attempts_*"))
        # The milestone matrix is regenerated per run whenever scope is active
        # (auto milestones, or the parity loop that can append to it).
        if cfg.auto_milestones or cfg.parity_check:
            purge.append(pipeline / cfg.milestones_artifact)
        for f in purge:
            try:
                f.unlink()
            except OSError:
                pass
        shutil.rmtree(pipeline / cfg.optimize.snapshot_dir, ignore_errors=True)

    base_env = {"CODEWEAVER_PIPELINE_DIR": str(pipeline),
                "CODEWEAVER_ANALYSIS_ARTIFACT": cfg.analysis_artifact,
                "CODEWEAVER_PLAN_ARTIFACT": cfg.plan_artifact,
                "CODEWEAVER_REPORT_ARTIFACT": cfg.report_artifact,
                "CODEWEAVER_MILESTONES_ARTIFACT": cfg.milestones_artifact,
                "CODEWEAVER_PARITY_ARTIFACT": cfg.parity_artifact,
                "CODEWEAVER_SKIPS_ARTIFACT": cfg.skips_artifact}

    if cfg.auto_milestones:
        print(f"[check] config declares no milestones -> scope stage will generate them "
              f"(mock: M0..M{2})")
    if cfg.parity_check:
        print("[check] parity loop enabled -> a final parity check runs after the last milestone")

    print("\n===== 1) HAPPY PATH - all milestones pass =====")
    reset(); _run_pipeline(args.config, "chk-happy", base_env)

    print(f"\n===== 2) REPAIR LOOP - {first} fails once, then passes =====")
    reset(); _run_pipeline(args.config, "chk-repair", {**base_env, "CODEWEAVER_MOCK_FAIL": f"{first}:1"})

    print(f"\n===== 3) SKIP-ON-GIVE-UP - {mid_ms} always fails (max-iter 3) -> skipped, run continues =====")
    reset(); _run_pipeline(args.config, "chk-giveup", {**base_env, "CODEWEAVER_MOCK_FAIL": f"{mid_ms}:99"}, max_iter=3)
    _assert_implement_first(pipeline)
    _report_skips(cfg, "3")

    for style in ("nolayer", "string", "unit"):
        print(f"\n===== 3{style[0]}) FAILURE SHAPE '{style}' - {mid_ms} gives up; tests still deferred =====")
        reset(); _run_pipeline(args.config, f"chk-shape-{style}",
                               {**base_env, "CODEWEAVER_MOCK_FAIL": f"{mid_ms}:99",
                                "CODEWEAVER_MOCK_FAIL_STYLE": style}, max_iter=3)
        _assert_implement_first(pipeline)
        _report_skips(cfg, f"3{style[0]}")

    print(f"\n===== 4) CRASH-RESUME - crash at {mid_ms}, resume SAME app-id =====")
    reset()
    _run_pipeline(args.config, "chk-resume", {**base_env, "CODEWEAVER_CRASH_AT": mid_ms})
    print("  (process 1 crashed; starting process 2 to resume...)")
    _run_pipeline(args.config, "chk-resume", base_env)

    if cfg.parity_check:
        print("\n===== 5) PARITY LOOP - parity incomplete twice, adds milestones, then completes =====")
        reset(); _run_pipeline(args.config, "chk-parity", {**base_env, "CODEWEAVER_MOCK_PARITY_INCOMPLETE": "2"})

        print(f"\n===== 6) DEFERRED-TEST RETRY - {mid_ms} skipped -> parity retry milestone recovers it =====")
        reset(); _run_pipeline(args.config, "chk-retry", {**base_env, "CODEWEAVER_MOCK_FAIL": f"{mid_ms}:99"}, max_iter=3)

        print("\n===== 7) --start-parity - re-grade an existing pipeline at the parity verifier =====")
        # Produce a clean set of artifacts, then enter at parity only (no milestone loop).
        reset(); _run_pipeline(args.config, "chk-happy2", base_env)
        _run_pipeline(args.config, "chk-startparity", base_env, extra_args=["--start-parity"])

        # ---- OPTIMIZE phase (phase 2). Off by default, so first prove that. ----
        print("\n===== 8) OPTIMIZE OFF BY DEFAULT - no benchmark/optimize rows appear =====")
        reset(); _run_pipeline(args.config, "chk-optoff", base_env)
        if cfg.optimize_history_path.exists():
            print("  [check] FAIL (8): the optimize phase ran without being asked for")
        else:
            print("  [check] OK (8): no optimize artifacts -> phase is off by default")

        opt_cfg = _optimize_config(cfg, Path(args.config), rounds=3)
        try:
            print("\n===== 9) OPTIMIZE AFTER PARITY - 3 rounds, then a full-suite milestone =====")
            reset(); _run_pipeline(str(opt_cfg), "chk-opt", base_env)
            _report_optimize(cfg, "9", expect_rounds=3)

            print("\n===== 9b) --start-benchmark - enter AT the optimize phase =====")
            reset(); _run_pipeline(str(opt_cfg), "chk-optbase", base_env)
            _run_pipeline(str(opt_cfg), "chk-startbench", base_env,
                          extra_args=["--start-benchmark", "--max-opt-rounds", "2"])

            print("\n===== 9c) REPAIR NOT REVERT - conformance milestone fails once, is repaired =====")
            reset()
            # The appended milestone is M<len(matrix)>; fail it once so the repair
            # loop (not a revert) is what recovers the optimisation.
            _run_pipeline(str(opt_cfg), "chk-optrepair",
                          {**base_env, "CODEWEAVER_MOCK_FAIL": "M4:1,M5:1,M6:1"})

            print("\n===== 9d) FOCUSED BENCHMARKS + rejections =====")
            reset()
            _run_pipeline(str(opt_cfg), "chk-optfocus", base_env,
                          extra_args=["--benchmarks", "B4,B9"])
            print("  (--benchmarks without the phase, and --max-opt-rounds 0 with "
                  "--start-benchmark, must both be rejected:)")
            _run_pipeline(args.config, "chk-optrej1", base_env,
                          extra_args=["--benchmarks", "B4"])
            _run_pipeline(str(opt_cfg), "chk-optrej2", base_env,
                          extra_args=["--start-benchmark", "--max-opt-rounds", "0"])
        finally:
            opt_cfg.unlink(missing_ok=True)

    reset()
    print("\nAll orchestrator checks ran. Verify above:")
    print(f"  1 done=True (all pass)   2 {first} iter1=False then iter2=True")
    print(f"  3 {mid_ms} GAVE-UP/SKIPPED, run continues (skipped=[{mid_ms}])")
    print(f"  4 process-2 'loaded state ... milestone_idx>0' => resumed, not restarted")
    if cfg.parity_check:
        print("  5 two extra milestones appear, then done=True after parity completes")
        print(f"  6 {mid_ms} skipped -> a 'Retry deferred tests' milestone runs -> done=True")
        print("  7 history is PARITY only (no milestone rows) => the milestone loop was skipped")
        print("  8 no OPTIMIZE row and no optimize artifacts => phase 2 is OFF by default")
        print("  9 OPTIMIZE row + a 'Post-optimisation conformance' milestone -> done=True")
        print("  9b history is OPTIMIZE + the conformance milestone ONLY (no earlier milestones)")
        print("  9c the conformance milestone fails once then PASSES (repaired, not reverted)")
        print("  9d focused run reports scenarios=B4 B9; both rejections exit non-zero")
    return 0


# --------------------------------------------------------------------------- #
# milestones
# --------------------------------------------------------------------------- #
def _cmd_milestones(args) -> int:
    from . import config as C, milestones as M

    cfg = C.load(args.config)
    # If milestones are auto-generated, show any previously generated matrix on disk.
    if cfg.auto_milestones and not cfg.milestones:
        cfg.load_generated_milestones()
    if args.gate:
        print(M.gate_string(cfg, args.gate))
        return 0
    if not cfg.milestones:
        print(f"# {cfg.name}: no milestones declared -> generated at runtime by the "
              f"scope stage (between analyze and plan).")
        print(f"# After a run, they are written to {cfg.milestones_path}.")
        return 0
    origin = "generated" if cfg.auto_milestones else "declared"
    print(f"# {cfg.name}: {len(cfg.milestones)} milestones ({origin})")
    print(M.matrix(cfg))
    return 0


# --------------------------------------------------------------------------- #
# install-agents
# --------------------------------------------------------------------------- #
def _cmd_install_agents(args) -> int:
    from .copilot import ensure_agents_installed, AGENTS_SRC

    installed = ensure_agents_installed()
    if not installed:
        print(f"[codeweaver] no agent profiles found in {AGENTS_SRC}", file=sys.stderr)
        return 1
    dest = Path(os.environ.get("COPILOT_HOME", Path.home() / ".copilot")) / "agents"
    print(f"[codeweaver] installed {len(installed)} profile(s) into {dest}: {', '.join(installed)}")
    return 0


# --------------------------------------------------------------------------- #
# init  (scaffold a new project config)
# --------------------------------------------------------------------------- #
_TEMPLATE = '''\
# CodeWeaver project config. See docs/config.md for the full reference.

[project]
name = "{name}"
slug = "{slug}"
description = "Translate <what> from <source> to <target>."

[translation]
source_language = "Python"
target_language = "Rust"
brief = """
Project-specific knowledge every agent should honor: the architectural
constraints, provided scaffolding NOT to reinvent, the observable contract the
port must reproduce, and any hard boundaries (files that must never change).
"""

[paths]
source_dir = "source"              # what to translate
reference_dirs = []                # extra read-only --add-dir grants (e.g. an e2e test suite)
# immutable_input = "crate"        # optional: copied to working_copy, never edited
# working_copy = "pipeline/crate"  # optional: the mutable copy the agents translate into
pipeline_dir = "pipeline"          # runtime hand-off + artifacts + logs

[commands]
# Shell commands the agents run. {{milestone}} and {{gate}} are substituted by the
# agent from the prompt; keep these project-specific.
build_check = "bash tools/build_check.sh"
unit_test  = "bash tools/unit_test.sh"
validate   = "bash tools/validate.sh {{milestone}}"

[validation]
# How a milestone's cumulative test list becomes the gate string in `validate`.
# {{skip_exclude}} deselects tests deferred by skip-on-give-up (see below).
gate_template = '-k "({{tests_or}}){{skip_exclude}}"'
skip_exclude_template = ' and not ({{tests_or}})'
# Runner-specific regex recognising a GATE-LAYER test id in a validator report entry
# that did not label its layer, so ids from another layer (e.g. Rust unit-test paths)
# are never mistaken for gate selections. Empty -> accept any unlabelled id.
gate_test_id_pattern = '[\\w./\\\\-]+\\.py::[\\w\\[\\].-]+'
# Runner-specific regex extracting the selector TOKEN a deferred test id contributes
# to skip_exclude_template. pytest -k only accepts bare words, so map
# "tests/test_dom.py::test_x[case]" -> "test_x". Empty -> use ids verbatim.
skip_token_pattern = '([^:\\[/\\\\]+?)(?:\\[|$)'

[model]
default = "claude-opus-4.8"
effort_default = "high"
[model.effort]
analyzer = "max"
scoper = "max"
planner = "max"
translator = "max"
validator = "high"
parity = "max"

[execution]
max_iter = 5
# When a milestone exhausts max_iter, SKIP it (record its failing tests in
# skips.json, deselect them from later gates, advance) instead of hard-failing; the
# parity verifier gives each deferred test one retry milestone. false = hard fail.
skip_on_give_up = true
# After all milestones conclude, a parity verifier compares source vs. translation;
# if incomplete, the milestone generator schedules the gaps and the loop repeats
# until parity is verified complete. Set false for legacy finish-on-last-milestone.
parity_check = true
max_parity_rounds = 3

# ---------------------------------------------------------------------------
# PHASE 2 -- optimization. OFF BY DEFAULT.
# ---------------------------------------------------------------------------
# CodeWeaver runs two phases: translation (above) makes the port CORRECT, and
# this one makes it FASTER. It is entered only after the parity verifier reports
# the translation complete -- tuning a port with known gaps tunes code that is
# still going to change.
#
# Uncomment and set benchmark_cmd to enable it (or pass --optimize on the CLI).
# [optimization]
# enabled = true
# max_rounds = 5
# # Runs the project's benchmark harness. {{bench}} is the artifact to write,
# # {{working_copy}} the tree to measure, {{scenarios}} the focus clause below.
# benchmark_cmd = "bash tools/bench.sh {{working_copy}} --out {{bench}} {{scenarios}}"
# # How --benchmarks B4,B9 renders into {{scenarios}}. Omit if unsupported.
# scenario_template = "--scenario {{scenarios_csv}}"
# # Default focus; "" measures the whole suite.
# scenarios = ""
# # Runs the ENTIRE test suite for the closing conformance milestone. Defaults to
# # the validate command with an empty gate (no selector = everything).
# full_suite_cmd = "bash tools/validate.sh {{milestone}} --all"

# Milestones are OPTIONAL. Omit the [[milestones]] tables entirely to let Copilot
# generate a cumulative matrix at runtime (a `scope` stage runs between analyze and
# plan). Declare them here for full control:
[[milestones]]
id = "M0"
title = "Skeleton"
goal = "Project compiles and the entrypoint runs; no functional tests yet."
tests = []

[[milestones]]
id = "M1"
title = "First feature"
goal = "Implement the first slice of behavior."
tests = ["test_first"]
'''


def _cmd_init(args) -> int:
    target = Path(args.dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    cfg_path = target / "codeweaver.toml"
    if cfg_path.exists() and not args.force:
        print(f"[codeweaver] {cfg_path} exists (use --force to overwrite)", file=sys.stderr)
        return 1
    name = target.name
    slug = name.strip().replace(" ", "-").lower()
    cfg_path.write_text(_TEMPLATE.format(name=name, slug=slug), encoding="utf-8")
    print(f"[codeweaver] wrote {cfg_path}")
    print("[codeweaver] next: edit the [translation].brief, [paths], [commands] and [[milestones]],")
    print("             then `codeweaver check --config codeweaver.toml` to smoke-test offline.")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="codeweaver",
                                 description="ReCodeAgent-style multi-agent code translation, "
                                             "driven by GitHub Copilot CLI, orchestrated by Apache Burr.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the translation pipeline")
    r.add_argument("--config", "-c", required=True, help="project config (codeweaver.toml)")
    r.add_argument("--app-id", default=None, help="run id; reuse to resume a crashed run")
    r.add_argument("--max-iter", type=int, default=None, help="repair budget per milestone")
    r.add_argument("--max-parity-rounds", type=int, default=None,
                   help="outer-loop budget: max parity re-scope rounds before failing")
    r.add_argument("--pipeline-dir", default=None,
                   help="override the pipeline artifact directory")
    r.add_argument("--start-milestone", default=None, metavar="Mx",
                   help="start a NEW app-id from an existing pipeline at this milestone "
                        "(requires analysis/milestones/plan artifacts; skips analyze/scope/plan)")
    r.add_argument("--start-parity", action="store_true",
                   help="start a NEW app-id from an existing pipeline directly at the parity "
                        "verifier, skipping analyze/scope/plan AND the milestone loop "
                        "(re-grade a translation as it stands); excludes --start-milestone")
    r.add_argument("--start-benchmark", action="store_true",
                   help="start a NEW app-id from an existing pipeline directly at the "
                        "OPTIMIZE phase, skipping analyze/scope/plan, the milestone loop "
                        "AND parity. ASSERTS the translation is already complete and "
                        "correct. Implies --optimize.")
    # --- optimize phase (phase 2). OFF by default. ---
    r.add_argument("--optimize", action="store_true",
                   help="after parity completes, run the OPTIMIZE phase: benchmark<->optimize "
                        "rounds, then one full-suite conformance milestone that repairs any "
                        "regression. Off unless this flag or [optimization].enabled is set.")
    r.add_argument("--max-opt-rounds", type=int, default=None, metavar="N",
                   help="how many benchmark->optimize rounds to run; implies --optimize when "
                        "N > 0, and 0 disables the phase even with --optimize")
    r.add_argument("--benchmarks", default="", metavar="IDS",
                   help="focus the optimize phase on these benchmark scenario ids only "
                        "(e.g. B4,B9). The Benchmarker measures only these and the Optimizer "
                        "is told they are the only evidence it has")
    r.add_argument("--db", default=None, help="SQLite persistence path override")
    r.add_argument("--mock", action="store_true", help="offline: mock agents (no Copilot)")
    r.set_defaults(func=_cmd_run)

    c = sub.add_parser("check", help="offline mock smoke tests (happy/repair/budget/resume)")
    c.add_argument("--config", "-c", required=True)
    c.set_defaults(func=_cmd_check)

    m = sub.add_parser("milestones", help="print the milestone matrix / a resolved gate")
    m.add_argument("--config", "-c", required=True)
    m.add_argument("--gate", help="print the resolved cumulative gate for this milestone id")
    m.set_defaults(func=_cmd_milestones)

    ia = sub.add_parser("install-agents", help="mirror agent profiles to ~/.copilot/agents")
    ia.set_defaults(func=_cmd_install_agents)

    i = sub.add_parser("init", help="scaffold a new codeweaver.toml")
    i.add_argument("dir", nargs="?", default=".", help="target directory (default: .)")
    i.add_argument("--force", action="store_true", help="overwrite an existing config")
    i.set_defaults(func=_cmd_init)

    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as e:
        # Config validation and missing-artifact problems are user errors, not
        # bugs: report them plainly instead of dumping a traceback.
        print(f"[codeweaver] error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
