"""CodeWeaver command-line interface.

    codeweaver run       --config codeweaver.toml [--app-id ID] [--max-iter N] [--mock]
    codeweaver check     --config codeweaver.toml    # offline mock smoke tests
    codeweaver milestones --config codeweaver.toml    # print the milestone matrix
    codeweaver install-agents                          # mirror agent profiles to ~/.copilot/agents
    codeweaver init      [DIR]                          # scaffold a new codeweaver.toml + brief
"""
from __future__ import annotations

import argparse
import os
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
    if args.start_milestone:
        try:
            bootstrap_state = state_from_existing_pipeline(
                cfg, args.start_milestone, max_iter=max_iter,
                max_parity_rounds=cfg.max_parity_rounds)
        except ValueError as e:
            print(f"[codeweaver] error: {e}", file=sys.stderr)
            return 2
        entrypoint = "select_milestone"

    app = build_application(cfg, app_id, max_iter=max_iter, db_path=args.db,
                            bootstrap_state=bootstrap_state,
                            default_entrypoint=entrypoint)

    mock_on = os.environ.get("CODEWEAVER_MOCK") == "1"
    print(f"[codeweaver] project={cfg.name} app_id={app_id} mock={mock_on} db={db_path}")
    if args.start_milestone:
        if app.state["last_agent"] == "pipeline-bootstrap":
            print(f"[codeweaver] starting from existing artifacts at {args.start_milestone}; "
                  "analyze/scope/plan are skipped")
        else:
            print(f"[codeweaver] persisted state exists for app_id={app_id}; resuming it "
                  f"(--start-milestone only initializes a NEW app-id)")
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
def _run_pipeline(config_path: str, app_id: str, extra_env: dict, max_iter=None) -> int:
    env = dict(os.environ)
    env["CODEWEAVER_MOCK"] = "1"
    env.update({k: str(v) for k, v in extra_env.items()})
    cmd = [sys.executable, "-m", "codeweaver", "run", "--config", config_path,
           "--app-id", app_id, "--mock"]
    if max_iter is not None:
        cmd += ["--max-iter", str(max_iter)]
    return subprocess.run(cmd, env=env).returncode


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
                 pipeline / ".mock_parity_attempts",
                 pipeline / cfg.parity_artifact,
                 pipeline / cfg.skips_artifact]
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

    reset()
    print("\nAll orchestrator checks ran. Verify above:")
    print(f"  1 done=True (all pass)   2 {first} iter1=False then iter2=True")
    print(f"  3 {mid_ms} GAVE-UP/SKIPPED, run continues (skipped=[{mid_ms}])")
    print(f"  4 process-2 'loaded state ... milestone_idx>0' => resumed, not restarted")
    if cfg.parity_check:
        print("  5 two extra milestones appear, then done=True after parity completes")
        print(f"  6 {mid_ms} skipped -> a 'Retry deferred tests' milestone runs -> done=True")
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
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
