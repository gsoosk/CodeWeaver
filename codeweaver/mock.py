"""Offline mock for invoke_agent(): drive the Burr graph + crash-resume WITHOUT
Copilot. Enabled with CODEWEAVER_MOCK=1.

The mock writes the same pipeline artifacts a real agent would (analysis, plan,
report), so the file-based state hand-off in actions.py works unchanged.
Validator outcomes are scriptable so the repair loop and milestone advancement
can be exercised:

  CODEWEAVER_MOCK_FAIL   comma-separated "milestone:attempts" pairs that should
                         FAIL the first N validate attempts, e.g. "M1:1,M3:2" ->
                         M1 fails once then passes, M3 fails twice then passes.
                         Default: all pass.
  CODEWEAVER_MOCK_FAIL_STYLE  shape of the validator's failure entries:
                         labelled (default) | nolayer | string | unit. Drives the
                         tolerant gate-layer id extraction in actions.py.
  CODEWEAVER_CRASH_AT    a milestone id: raise before writing the verdict (to
                         exercise crash-resume).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _pipeline_dir() -> Path:
    d = Path(os.environ.get("CODEWEAVER_PIPELINE_DIR", "pipeline"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _artifact_names() -> dict[str, str]:
    return {
        "analysis": os.environ.get("CODEWEAVER_ANALYSIS_ARTIFACT", "analysis.md"),
        "plan": os.environ.get("CODEWEAVER_PLAN_ARTIFACT", "plan.json"),
        "report": os.environ.get("CODEWEAVER_REPORT_ARTIFACT", "report.json"),
        "milestones": os.environ.get("CODEWEAVER_MILESTONES_ARTIFACT", "milestones.json"),
        "parity": os.environ.get("CODEWEAVER_PARITY_ARTIFACT", "parity.json"),
        "skips": os.environ.get("CODEWEAVER_SKIPS_ARTIFACT", "skips.json"),
    }


def _fail_budget() -> dict[str, int]:
    out: dict[str, int] = {}
    for pair in os.environ.get("CODEWEAVER_MOCK_FAIL", "").split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        mid, n = pair.split(":", 1)
        try:
            out[mid.strip()] = int(n)
        except ValueError:
            continue
    return out


def _load_milestones(path) -> list:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return raw.get("milestones") if isinstance(raw, dict) else (raw or [])


def _failure_entries(fail_tests: list[str], mid: str, attempts: int, budget: int) -> list:
    """Validator failure entries in one of several real-world shapes.

    CODEWEAVER_MOCK_FAIL_STYLE exercises the tolerant extractor in actions.py:
      labelled (default)  {"layer": "e2e", "test": ...}   -- the well-formed shape
      nolayer             {"nodeid": ...} with no "layer" -- id must be recognised
      string              a plain string per failure      -- id must be mined out
      unit                {"layer": "unit", ...}          -- must be IGNORED
    """
    style = os.environ.get("CODEWEAVER_MOCK_FAIL_STYLE", "labelled").strip().lower()
    symptom = f"(mock) {mid} attempt {attempts} <= budget {budget}"
    if style == "string":
        return [f"FAILED {t} - {symptom}" for t in fail_tests]
    out = []
    for t in fail_tests:
        if style == "nolayer":
            out.append({"nodeid": t, "symptom": symptom,
                        "repair_hint": "increment attempt counter"})
        elif style == "unit":
            out.append({"layer": "unit", "test": f"mod::tests::{mid}",
                        "symptom": symptom, "repair_hint": "increment attempt counter"})
        else:
            out.append({"layer": "e2e", "test": t, "symptom": symptom,
                        "likely_cause": "scripted mock failure",
                        "repair_hint": "increment attempt counter"})
    return out


def respond(agent_name: str, prompt: str) -> str:
    pdir = _pipeline_dir()
    names = _artifact_names()

    if agent_name == "analyzer":
        (pdir / names["analysis"]).write_text(
            "# (mock) source research\n\n- overview, structure, data models\n",
            encoding="utf-8")
        return f"mock analyzer: wrote {names['analysis']}"

    if agent_name == "scoper":
        mfile = pdir / names["milestones"]
        pfile = pdir / names["parity"]
        # Incremental (parity re-entry): the milestones + a parity report already
        # exist and parity said incomplete -> append one new milestone for the gap.
        incremental = False
        if mfile.exists() and pfile.exists():
            try:
                incremental = not json.loads(pfile.read_text(encoding="utf-8")).get("complete", True)
            except (ValueError, OSError):
                incremental = False
        if incremental:
            arr = _load_milestones(mfile)
            k = len(arr)
            arr.append({"id": f"M{k}", "title": f"Parity gap {k}",
                        "goal": "Translate the remaining gap the parity check found.",
                        "tests": [f"test_gap_{k}"]})
            mfile.write_text(json.dumps(arr, indent=2), encoding="utf-8")
            return f"mock scoper: appended M{k} (parity gap)"
        # Initial: emit a small generic matrix. Overridable via CODEWEAVER_MOCK_MILESTONES.
        try:
            k = int(os.environ.get("CODEWEAVER_MOCK_MILESTONES", "3"))
        except ValueError:
            k = 3
        k = max(k, 1)
        gen = [{"id": "M0", "title": "Skeleton",
                "goal": "Compiles and runs; no features yet.", "tests": []}]
        for i in range(1, k):
            gen.append({"id": f"M{i}", "title": f"Feature {i}",
                        "goal": f"Implement feature {i}.", "tests": [f"test_feature_{i}"]})
        mfile.write_text(json.dumps(gen, indent=2), encoding="utf-8")
        return f"mock scoper: wrote {names['milestones']} ({k} milestones)"

    if agent_name == "parity":
        # Report incomplete for the first N checks (each triggering a scope
        # re-entry that appends a milestone), then complete. N via
        # CODEWEAVER_MOCK_PARITY_INCOMPLETE (default 0 -> complete immediately).
        budget = 0
        try:
            budget = int(os.environ.get("CODEWEAVER_MOCK_PARITY_INCOMPLETE", "0"))
        except ValueError:
            budget = 0
        cnt_file = pdir / ".mock_parity_attempts"
        attempts = int(cnt_file.read_text()) if cnt_file.exists() else 0
        attempts += 1
        cnt_file.write_text(str(attempts))
        complete = attempts > budget
        report = {
            "complete": complete,
            "translated": ["(mock) all components"] if complete else ["(mock) some components"],
            "missing": [] if complete else [
                {"component": f"gap_{attempts}", "source_ref": "(mock)",
                 "reason": "not yet translated (mock)",
                 "suggested_milestone": f"translate gap_{attempts}"}
            ],
            "notes": f"(mock) parity attempt {attempts}, budget {budget}",
        }
        (pdir / names["parity"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return f"mock parity: {'COMPLETE' if complete else 'INCOMPLETE'} (attempt {attempts})"

    if agent_name == "planner":
        (pdir / names["plan"]).write_text(json.dumps({
            "name_mapping": {},
            "fragments": {"part_a": [], "part_b": []},
            "skeleton": {"compiles": True, "unit_tests_run": True},
            "milestones": [],
        }, indent=2), encoding="utf-8")
        return f"mock planner: wrote {names['plan']}"

    if agent_name == "translator":
        # Record "<milestone>:<mode>" per invocation so a check scenario can assert
        # that every milestone STARTS in IMPLEMENT mode (a stale report leaking from
        # a previous give-up would wrongly show REPAIR on the first attempt).
        mid = _extract_milestone(prompt)
        mode = "REPAIR" if re.search(r"\bMode:\s*REPAIR\b", prompt or "") else "IMPLEMENT"
        with (pdir / "translate.marker").open("a", encoding="utf-8") as fh:
            fh.write(f"{mid}:{mode}\n")
        return f"mock translator: filled skeleton ({mid}:{mode})"

    # The optimize phase's two agents are driven by codeweaver.optimize, which
    # writes their artifacts directly in mock mode (so the round trend is
    # deterministic). These branches exist so a mock invocation is still logged
    # with a sensible reply if the actions are ever wired to call through.
    if agent_name == "benchmarker":
        return "mock benchmarker: measured the working copy"

    if agent_name == "optimizer":
        return "mock optimizer: applied one focused change set"

    if agent_name == "validator":
        mid = _extract_milestone(prompt)
        if os.environ.get("CODEWEAVER_CRASH_AT") == mid:
            raise RuntimeError(f"(mock) simulated crash at {mid}")
        # A "Retry deferred tests" milestone can be forced to keep failing (to
        # exercise the permanent-skip path) via CODEWEAVER_MOCK_RETRY_FAIL=1.
        is_retry = "retry deferred tests" in (prompt or "").lower()
        retry_fail = is_retry and os.environ.get("CODEWEAVER_MOCK_RETRY_FAIL") == "1"
        budget = _fail_budget().get(mid, 0)
        cnt_file = pdir / f".mock_attempts_{mid}"
        attempts = int(cnt_file.read_text()) if cnt_file.exists() else 0
        attempts += 1
        cnt_file.write_text(str(attempts))
        passed = (attempts > budget) and not retry_fail
        # On failure, emit an e2e failure carrying a pytest-style node id so the
        # skip-on-give-up path can record it in skips.json. For a FAILING retry
        # milestone, report the deferred test ids being retried (read from
        # skips.json 'retried') so they become PERMANENT skips.
        fail_tests = [f"test_{mid}.py::test_{mid}"]
        if is_retry and retry_fail:
            try:
                sk = json.loads((pdir / names["skips"]).read_text(encoding="utf-8"))
                retried = [t for t in sk.get("retried", []) if isinstance(t, str) and t]
                if retried:
                    fail_tests = retried
            except (ValueError, OSError):
                pass
        report = {
            "milestone": mid,
            "passed": passed,
            "tests": {
                "unit": {"total": 3, "passed": 3 if passed else 1, "failed": 0 if passed else 2},
                "e2e": {"total": 2, "passed": 2 if passed else 1, "failed": 0 if passed else 1},
            },
            "failures": [] if passed else _failure_entries(fail_tests, mid, attempts, budget),
        }
        (pdir / names["report"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return f"mock validator: {mid} {'PASS' if passed else 'FAIL'} (attempt {attempts})"

    return f"mock {agent_name}: ok"


def _extract_milestone(prompt: str) -> str:
    """Pull the milestone id (e.g. M0..M99) out of the prompt the action passed."""
    m = re.search(r"\bmilestone\s+([A-Za-z][\w-]*)", prompt or "", re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\b(M\d+)\b", prompt or "")
    return m.group(1) if m else "M0"
