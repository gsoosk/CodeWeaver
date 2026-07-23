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


def respond(agent_name: str, prompt: str) -> str:
    pdir = _pipeline_dir()
    names = _artifact_names()

    if agent_name == "analyzer":
        (pdir / names["analysis"]).write_text(
            "# (mock) source research\n\n- overview, structure, data models\n",
            encoding="utf-8")
        return f"mock analyzer: wrote {names['analysis']}"

    if agent_name == "planner":
        (pdir / names["plan"]).write_text(json.dumps({
            "name_mapping": {},
            "fragments": {"part_a": [], "part_b": []},
            "skeleton": {"compiles": True, "unit_tests_run": True},
            "milestones": [],
        }, indent=2), encoding="utf-8")
        return f"mock planner: wrote {names['plan']}"

    if agent_name == "translator":
        (pdir / "translate.marker").write_text("mock translated\n", encoding="utf-8")
        return "mock translator: filled skeleton"

    if agent_name == "validator":
        mid = _extract_milestone(prompt)
        if os.environ.get("CODEWEAVER_CRASH_AT") == mid:
            raise RuntimeError(f"(mock) simulated crash at {mid}")
        budget = _fail_budget().get(mid, 0)
        cnt_file = pdir / f".mock_attempts_{mid}"
        attempts = int(cnt_file.read_text()) if cnt_file.exists() else 0
        attempts += 1
        cnt_file.write_text(str(attempts))
        passed = attempts > budget
        report = {
            "milestone": mid,
            "passed": passed,
            "tests": {
                "unit": {"total": 3, "passed": 3 if passed else 1, "failed": 0 if passed else 2},
                "e2e": {"total": 2, "passed": 2 if passed else 1, "failed": 0 if passed else 1},
            },
            "failures": [] if passed else [
                {"layer": "unit", "test": f"{mid}::mock",
                 "symptom": f"(mock) {mid} attempt {attempts} <= budget {budget}",
                 "likely_cause": "scripted mock failure",
                 "repair_hint": "increment attempt counter"}
            ],
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
