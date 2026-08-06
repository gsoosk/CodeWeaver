"""Tests for experiments/recodeagent/run.py: resumable/idempotent execution,
deterministic naming, full-graph stage-ablation wiring, the baseagent
no-`--agent` raw executor, dry-run planning, and CLI wiring. Every executed
"agent"/"cli" call goes through a fake Executor -- this test module never
shells out to `copilot`, `codeweaver`, or any real toolchain.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import prepare as P
from experiments.recodeagent import run as R

PROTOCOL = {
    "model": "claude-opus-4.8", "effort_default": "high",
    "max_iter": 5, "max_parity_rounds": 3, "agent_timeout_seconds": 5000, "repetitions": 1,
}
CRUST_SPEC = {
    "label": "CRUST", "source_language": "C", "target_language": "Rust",
    "build_cmd": ["cargo", "build"], "unit_test_cmd": ["cargo", "test"],
    "validate_cmd": ["cargo", "test", "{gate}"], "gate_template": "{tests_or}",
}


def _row(project_id_suffix: str = "bitset") -> dict:
    return {
        "id": f"crust__{project_id_suffix}", "tool": "crust", "project": project_id_suffix,
        "source_language": "C", "target_language": "Rust",
        "source_rel_path": str(Path(project_id_suffix) / "CBench"),
        "oracle_rel_path": None, "scaffold_rel_path": None, "ground_truth_target_rel_path": None,
        "loc_source": 1, "test_count_source": 0, "function_count_source": 1,
        "status": "ok", "notes": "", "discovered_at": C.utcnow_iso(),
    }


@pytest.fixture()
def prepared(tmp_path: Path):
    """A real, prepared (prepare.py-built) project workspace with a valid
    codeweaver.toml, so run.py can load it with the REAL codeweaver.config."""
    artifact_root = tmp_path / "artifact"
    src = artifact_root / "bitset" / "CBench"
    src.mkdir(parents=True)
    (src / "main.c").write_text("int f(void) { return 0; }\n", encoding="utf-8")

    workspace_root = tmp_path / "workspaces"
    result = P.prepare_project(_row(), artifact_root=artifact_root, workspace_root=workspace_root,
                               dataset_spec=CRUST_SPEC, protocol=PROTOCOL)
    return {"workspace_root": workspace_root, "prepared_dir": result.prepared_dir, "project_id": "crust__bitset"}


# --------------------------------------------------------------------------- #
# Fakes -- the only thing that ever "executes" anything in this test module
# --------------------------------------------------------------------------- #
@dataclass
class FakeAgentResult:
    agent: str
    ok: bool = True
    returncode: int = 0
    final_text: str = "done"
    duration_s: float = 1.0
    stdout_path: str | None = None
    events: list = field(default_factory=list)


class RecordingExecutor:
    def __init__(self, *, agent_ok=True, cli_ok=True, raw_ok=True,
                agent_timeout=False, cli_timeout=False, raise_on_agent=None,
                raise_on_cli=False):
        self.agent_calls: list[dict] = []
        self.cli_calls: list[dict] = []
        self.raw_calls: list[dict] = []
        self.agent_ok = agent_ok
        self.cli_ok = cli_ok
        self.raw_ok = raw_ok
        self.agent_timeout = agent_timeout
        self.cli_timeout = cli_timeout
        self.raise_on_agent = raise_on_agent  # agent name -> exception to raise
        self.raise_on_cli = raise_on_cli

    def run_cli(self, argv, *, cwd, timeout, env=None):
        if self.raise_on_cli:
            raise RuntimeError("simulated CLI launch failure")
        self.cli_calls.append({
            "argv": list(argv),
            "cwd": str(cwd),
            "timeout": timeout,
            "skip_stages": (env or {}).get("CODEWEAVER_SKIP_STAGES"),
            "ablation_variant": (env or {}).get("CODEWEAVER_ABLATION_VARIANT"),
        })
        if self.cli_timeout:
            return C.ExecResult(argv=list(argv), returncode=None, stdout="", stderr="", duration_s=1.0,
                                timed_out=True, started_at=C.utcnow_iso(), ended_at=C.utcnow_iso(),
                                error="timed out after 1.0s", cwd=str(cwd))
        rc = 0 if self.cli_ok else 1
        return C.ExecResult(argv=list(argv), returncode=rc, stdout="cli ok", stderr="", duration_s=1.0,
                            timed_out=False, started_at=C.utcnow_iso(), ended_at=C.utcnow_iso(), cwd=str(cwd))

    def run_agent(self, agent_name, prompt, *, cwd, model, effort, add_dirs, timeout, log_dir, cfg,
                 extra_env=None):
        if self.raise_on_agent and self.raise_on_agent == agent_name:
            raise RuntimeError(f"simulated failure invoking {agent_name}")
        self.agent_calls.append({"agent": agent_name, "prompt_len": len(prompt), "model": model,
                                 "effort": effort, "cwd": str(cwd)})
        rc = 124 if self.agent_timeout else (0 if self.agent_ok else 1)
        return FakeAgentResult(agent=agent_name, ok=(rc == 0 and not self.agent_timeout), returncode=rc)

    def run_raw(self, prompt, *, cwd, model, effort, timeout, log_dir, env=None):
        self.raw_calls.append({"prompt_len": len(prompt), "model": model, "effort": effort, "cwd": str(cwd)})
        rc = 0 if self.raw_ok else 1
        return C.ExecResult(argv=["copilot", "-p", "<prompt>"], returncode=rc, stdout="", stderr="",
                            duration_s=1.0, timed_out=False, started_at=C.utcnow_iso(),
                            ended_at=C.utcnow_iso(), cwd=str(cwd))


# --------------------------------------------------------------------------- #
# Deterministic naming
# --------------------------------------------------------------------------- #
def test_run_dir_for_is_deterministic():
    a = R.run_dir_for(Path("/runs"), "full", "crust__bitset", 0)
    b = R.run_dir_for(Path("/runs"), "full", "crust__bitset", 0)
    assert a == b == Path("/runs") / "full" / "crust__bitset" / "rep0"


def test_app_id_for_is_deterministic_and_stable():
    a = R.app_id_for("noanalyzer", "crust__bitset", 2)
    b = R.app_id_for("noanalyzer", "crust__bitset", 2)
    assert a == b
    assert "rep2" in a


def test_app_id_for_differs_across_variants_and_repetitions():
    ids = {R.app_id_for(v, "crust__bitset", r) for v in ("full", "noanalyzer") for r in (0, 1)}
    assert len(ids) == 4


# --------------------------------------------------------------------------- #
# Run state persistence + schema conformance
# --------------------------------------------------------------------------- #
def test_new_run_state_matches_schema(tmp_path: Path):
    state = R.new_run_state("full", "crust__bitset", 0, tmp_path / "run")
    schema = C.load_schema("run_state.schema.json")
    assert C.validate_schema(state, schema) == []
    assert state["status"] == "pending"


def test_save_and_load_run_state_roundtrip(tmp_path: Path):
    run_dir = tmp_path / "run"
    state = R.new_run_state("full", "crust__bitset", 0, run_dir)
    R.save_run_state(run_dir, state)
    loaded = R.load_run_state(run_dir)
    assert loaded["variant"] == "full"
    assert loaded["status"] == "pending"
    assert "updated_at" in loaded


def test_load_run_state_missing_returns_none(tmp_path: Path):
    assert R.load_run_state(tmp_path / "nope") is None


# --------------------------------------------------------------------------- #
# Full-variant argv construction (pure)
# --------------------------------------------------------------------------- #
def test_build_full_argv_uses_sys_executable_and_never_mocks():
    argv = R.build_full_argv(Path("/x/codeweaver.toml"), "app-123")
    assert argv[0] == sys.executable
    assert argv[1:4] == ["-m", "codeweaver", "run"]
    assert "--config" in argv and str(Path("/x/codeweaver.toml")) in argv
    assert "--app-id" in argv and "app-123" in argv
    assert "--mock" not in argv  # NEVER fake a real run


def test_build_raw_copilot_argv_never_includes_agent_flag():
    argv = R.build_raw_copilot_argv("do the whole translation yourself", model="claude-opus-4.8", effort="high")
    assert "--agent" not in argv
    assert "copilot" == argv[0]
    assert "--model" in argv and "claude-opus-4.8" in argv
    assert "--reasoning-effort" in argv and "high" in argv


# --------------------------------------------------------------------------- #
# AgentCallResult wrapping: timeout / ok semantics
# --------------------------------------------------------------------------- #
def test_agent_call_from_agent_result_ok():
    res = FakeAgentResult(agent="analyzer", ok=True, returncode=0)
    call = R._agent_call_from_agent_result("analyze", "analyzer", "prompt text", "m", "high", res, C.utcnow_iso())
    assert call.ok is True
    assert call.timed_out is False
    assert call.kind == "invoke"


def test_agent_call_from_agent_result_timeout_sentinel():
    res = FakeAgentResult(agent="translator", ok=False, returncode=124)
    call = R._agent_call_from_agent_result("translate", "translator", "p", "m", "high", res, C.utcnow_iso())
    assert call.timed_out is True
    assert call.ok is False


def test_agent_call_placeholder_is_ok_and_labeled():
    call = R._agent_call_placeholder("analyze", "noanalyzer ablation: analyzer stage skipped")
    assert call.kind == "placeholder"
    assert call.ok is True
    assert call.agent is None
    assert "noanalyzer" in call.events_summary["placeholder_reason"]


# --------------------------------------------------------------------------- #
# Placeholder artifact content
# --------------------------------------------------------------------------- #
def test_placeholder_report_json_is_valid_json_and_labeled():
    text = R.placeholder_report_json("FULL")
    data = json.loads(text)
    assert data["placeholder"] is True
    assert "novalidator" in data["reason"]
    assert data["passed"] is None  # never fabricate a pass/fail verdict


def test_placeholder_plan_json_is_valid_json_and_labeled():
    data = json.loads(R.placeholder_plan_json(cfg=None))
    assert data["placeholder"] is True
    assert "noplanning" in data["reason"]
    assert data["fragments"] == [] and data["name_map"] == {}


# --------------------------------------------------------------------------- #
# Full-graph ablation hook
# --------------------------------------------------------------------------- #
def _load_cfg(run_dir: Path):
    from codeweaver import config as cw_config
    return cw_config.load(run_dir / "codeweaver.toml")


@pytest.mark.parametrize(
    "variant,stage",
    [
        ("noanalyzer", "analyze"),
        ("noplanning", "plan"),
        ("novalidator", "validate"),
    ],
)
def test_stage_ablation_uses_full_cli_with_exact_skip(prepared, tmp_path: Path, variant: str, stage: str):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    state = R.run_one(
        variant,
        prepared["project_id"],
        0,
        workspace_root=prepared["workspace_root"],
        runs_root=tmp_path / "runs",
        protocol=PROTOCOL,
        executor=executor,
    )
    assert state["status"] == "completed"
    assert state["ablation"] == {"skipped_stage": stage, "execution_mode": "full_burr_graph"}
    assert len(rec.cli_calls) == 1
    assert rec.cli_calls[0]["skip_stages"] == stage
    assert rec.cli_calls[0]["ablation_variant"] == variant
    assert rec.agent_calls == []


def test_config_reads_stage_ablation_from_environment(prepared, monkeypatch):
    monkeypatch.setenv("CODEWEAVER_SKIP_STAGES", "analyze")
    cfg = _load_cfg(prepared["prepared_dir"])
    assert cfg.skip_stages == {"analyze"}


def test_config_rejects_unknown_stage_ablation(prepared, monkeypatch):
    monkeypatch.setenv("CODEWEAVER_SKIP_STAGES", "translate")
    with pytest.raises(ValueError, match="unsupported execution skip stage"):
        _load_cfg(prepared["prepared_dir"])


# --------------------------------------------------------------------------- #
# Baseagent variants: exactly one call, no --agent, same model/budget
# --------------------------------------------------------------------------- #
def test_baseagent_condensed_makes_exactly_one_raw_call(prepared, tmp_path: Path):
    run_dir = tmp_path / "run"
    P.materialize_run(prepared["prepared_dir"], run_dir)
    cfg = _load_cfg(run_dir)
    executor = RecordingExecutor()
    calls = R.run_baseagent_variant("baseagent-condensed", cfg, executor=executor, timeout=100)
    assert len(calls) == 1
    assert len(executor.raw_calls) == 1
    assert len(executor.agent_calls) == 0  # no per-stage agent invocation at all
    assert executor.raw_calls[0]["model"] == cfg.model.default
    assert executor.raw_calls[0]["effort"] == cfg.model.effort_default


def test_copilot_event_error_prefers_actionable_session_failure():
    events = [
        {
            "type": "model.call_failure",
            "data": {"errorMessage": '"stream ended without an assistant message"'},
        },
        {
            "type": "session.error",
            "data": {"message": "retried five times; transport failed"},
        },
        {"type": "result", "usage": {"filesModified": ["large", "tail"]}},
    ]
    assert R._copilot_event_error(events) == "retried five times; transport failed"


def test_copilot_event_error_falls_back_to_model_failure():
    assert R._copilot_event_error([
        {
            "type": "model.call_failure",
            "data": {"errorMessage": '"stream interrupted"'},
        }
    ]) == "stream interrupted"


def test_baseagent_concat_prompt_mentions_all_six_responsibilities(prepared, tmp_path: Path):
    run_dir = tmp_path / "run"
    P.materialize_run(prepared["prepared_dir"], run_dir)
    cfg = _load_cfg(run_dir)
    prompt = R.build_concat_prompt(cfg)
    for stage in ("analyze", "scope", "plan", "translate", "validate", "parity"):
        assert f"Responsibility: {stage}" in prompt


def test_baseagent_condensed_prompt_mentions_final_parity_check(prepared, tmp_path: Path):
    """Regression test: the condensed baseline must not stop at "translate +
    validate" -- it must also explicitly instruct a final source/target
    component-by-component parity comparison, mirroring what the dedicated
    Parity agent does in `full`, folded into the single compact prompt."""
    run_dir = tmp_path / "run"
    P.materialize_run(prepared["prepared_dir"], run_dir)
    cfg = _load_cfg(run_dir)
    prompt = R.build_condensed_prompt(cfg)
    assert "component by component" in prompt
    assert "parity" in prompt.lower()


def test_baseagent_condensed_and_concat_prompts_differ(prepared, tmp_path: Path):
    run_dir = tmp_path / "run"
    P.materialize_run(prepared["prepared_dir"], run_dir)
    cfg = _load_cfg(run_dir)
    assert R.build_condensed_prompt(cfg) != R.build_concat_prompt(cfg)


# --------------------------------------------------------------------------- #
# describe_plan (dry-run, pure, no execution)
# --------------------------------------------------------------------------- #
def test_describe_plan_full(prepared):
    plan = R.describe_plan("full", prepared["prepared_dir"] / "codeweaver.toml", "app-1")
    assert plan["kind"] == "cli"
    assert "--app-id" in plan["argv"]


def test_describe_plan_ablation_marks_skipped_stage(prepared):
    plan = R.describe_plan("noplanning", prepared["prepared_dir"] / "codeweaver.toml", "app-1")
    assert plan["kind"] == "cli"
    assert plan["skip_stage"] == "plan"
    assert plan["execution_mode"] == "full_burr_graph"


def test_describe_plan_baseagent(prepared):
    plan = R.describe_plan("baseagent-concat", prepared["prepared_dir"] / "codeweaver.toml", "app-1")
    assert plan["kind"] == "raw"
    assert plan["prompt_chars"] > 0


# --------------------------------------------------------------------------- #
# run_one: idempotency / resumability / status transitions
# --------------------------------------------------------------------------- #
def test_run_one_full_success_marks_completed(prepared, tmp_path: Path):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)

    state = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=tmp_path / "runs", protocol=PROTOCOL, executor=executor)
    assert state["status"] == "completed"
    assert len(rec.cli_calls) == 1
    assert rec.cli_calls[0]["skip_stages"] == ""
    reloaded = R.load_run_state(Path(state["workspace_dir"]))
    assert reloaded["status"] == "completed"


def test_run_one_is_idempotent_by_default(prepared, tmp_path: Path):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    runs_root = tmp_path / "runs"

    first = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=runs_root, protocol=PROTOCOL, executor=executor)
    assert first["status"] == "completed"
    second = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                       runs_root=runs_root, protocol=PROTOCOL, executor=executor)
    assert second.get("skipped") is True
    assert len(rec.cli_calls) == 1  # NOT re-invoked


@pytest.mark.parametrize("status", ["failed", "timeout"])
def test_run_one_preserves_terminal_non_success_by_default(
    prepared,
    tmp_path: Path,
    status: str,
):
    runs_root = tmp_path / "runs"
    run_dir = R.run_dir_for(runs_root, "full", prepared["project_id"], 0)
    state = R.new_run_state("full", prepared["project_id"], 0, run_dir)
    state["status"] = status
    R.save_run_state(run_dir, state)

    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    result = R.run_one(
        "full",
        prepared["project_id"],
        0,
        workspace_root=prepared["workspace_root"],
        runs_root=runs_root,
        protocol=PROTOCOL,
        executor=executor,
    )

    assert result["status"] == status
    assert result["skipped"] is True
    assert result["skip_reason"] == f"already {status}"
    assert rec.cli_calls == []


def test_run_one_does_not_restart_cell_already_marked_running(prepared, tmp_path: Path):
    runs_root = tmp_path / "runs"
    run_dir = R.run_dir_for(runs_root, "full", prepared["project_id"], 0)
    R.save_run_state(run_dir, R.new_run_state("full", prepared["project_id"], 0, run_dir))
    state = R.load_run_state(run_dir)
    state["status"] = "running"
    R.save_run_state(run_dir, state)

    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    result = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                       runs_root=runs_root, protocol=PROTOCOL, executor=executor)

    assert result["status"] == "running"
    assert result["skipped"] is True
    assert result["skip_reason"] == "already running"
    assert rec.cli_calls == []


def test_run_one_resume_running_is_explicit_opt_in(prepared, tmp_path: Path):
    runs_root = tmp_path / "runs"
    run_dir = R.run_dir_for(runs_root, "full", prepared["project_id"], 0)
    R.save_run_state(run_dir, R.new_run_state("full", prepared["project_id"], 0, run_dir))
    state = R.load_run_state(run_dir)
    state["status"] = "running"
    R.save_run_state(run_dir, state)

    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    result = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                       runs_root=runs_root, protocol=PROTOCOL, executor=executor, resume_running=True)

    assert result["status"] == "completed"
    assert len(rec.cli_calls) == 1


def test_run_one_never_resumes_a_shard_reservation(prepared, tmp_path: Path):
    runs_root = tmp_path / "runs"
    run_dir = R.run_dir_for(runs_root, "full", prepared["project_id"], 0)
    state = R.new_run_state("full", prepared["project_id"], 0, run_dir)
    state["status"] = "running"
    state["reservation"] = {
        "shard": "tail-shard-v1",
        "source_runs_root": str(tmp_path / "runs-shard2"),
    }
    R.save_run_state(run_dir, state)

    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    result = R.run_one(
        "full",
        prepared["project_id"],
        0,
        workspace_root=prepared["workspace_root"],
        runs_root=runs_root,
        protocol=PROTOCOL,
        executor=executor,
        resume_running=True,
    )

    assert result["status"] == "running"
    assert result["skipped"] is True
    assert result["skip_reason"] == "reserved for disjoint shard"
    assert rec.cli_calls == []


def test_run_one_force_re_executes(prepared, tmp_path: Path):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    runs_root = tmp_path / "runs"

    R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
             runs_root=runs_root, protocol=PROTOCOL, executor=executor)
    R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
             runs_root=runs_root, protocol=PROTOCOL, executor=executor, force=True)
    assert len(rec.cli_calls) == 2


def test_run_one_records_timeout_status(prepared, tmp_path: Path):
    rec = RecordingExecutor(cli_timeout=True)
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    state = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=tmp_path / "runs", protocol=PROTOCOL, executor=executor)
    assert state["status"] == "timeout"


def test_run_one_records_failed_status_on_nonzero_exit(prepared, tmp_path: Path):
    rec = RecordingExecutor(cli_ok=False)
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    state = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=tmp_path / "runs", protocol=PROTOCOL, executor=executor)
    assert state["status"] == "failed"


def test_run_one_ablation_success_marks_completed(prepared, tmp_path: Path):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    state = R.run_one("noanalyzer", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=tmp_path / "runs", protocol=PROTOCOL, executor=executor)
    assert state["status"] == "completed"
    assert state["num_calls"] == 1
    run_dir = Path(state["workspace_dir"])
    calls = C.read_jsonl(run_dir / R.CALLS_FILENAME)
    assert len(calls) == 1
    assert calls[0]["kind"] == "cli"


def test_run_one_ablation_retry_preserves_burr_state(prepared, tmp_path: Path):
    """Named stage ablations use the full persisted graph and must resume."""
    runs_root = tmp_path / "runs"

    failing_rec = RecordingExecutor(cli_ok=False)
    failing_executor = R.Executor(run_cli=failing_rec.run_cli, run_agent=failing_rec.run_agent,
                                  run_raw=failing_rec.run_raw)
    first = R.run_one("noplanning", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=runs_root, protocol=PROTOCOL, executor=failing_executor)
    assert first["status"] == "failed"
    run_dir = Path(first["workspace_dir"])

    # Simulate Burr's persisted state after a partial graph execution.
    dirty_marker = run_dir / "pipeline" / "sentinel_dirty.txt"
    dirty_marker.parent.mkdir(parents=True, exist_ok=True)
    dirty_marker.write_text("stray leftover from the failed attempt\n", encoding="utf-8")
    assert dirty_marker.exists()

    # Retry with a working executor without --force so Burr state survives.
    # Terminal retries are explicit to protect genuine model outcomes.
    good_rec = RecordingExecutor()
    good_executor = R.Executor(run_cli=good_rec.run_cli, run_agent=good_rec.run_agent, run_raw=good_rec.run_raw)
    second = R.run_one("noplanning", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                       runs_root=runs_root, protocol=PROTOCOL, executor=good_executor,
                       retry_terminal=True)

    assert second["status"] == "completed"
    assert second.get("skipped") is not True          # a genuine re-execution happened, not a stale skip
    assert dirty_marker.exists()
    assert len(good_rec.cli_calls) == 1
    assert good_rec.cli_calls[0]["skip_stages"] == "plan"


def test_run_one_full_variant_retry_preserves_existing_state_for_resumability(prepared, tmp_path: Path):
    """Full and stage-ablation CLI runs share Burr resume semantics."""
    runs_root = tmp_path / "runs"

    failing_rec = RecordingExecutor(cli_ok=False)
    failing_executor = R.Executor(run_cli=failing_rec.run_cli, run_agent=failing_rec.run_agent,
                                  run_raw=failing_rec.run_raw)
    first = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=runs_root, protocol=PROTOCOL, executor=failing_executor)
    assert first["status"] == "failed"
    run_dir = Path(first["workspace_dir"])

    # Simulate Burr's own persisted SQLite resume state living under pipeline/.
    resume_marker = run_dir / "pipeline" / "burr_state.sqlite"
    resume_marker.parent.mkdir(parents=True, exist_ok=True)
    resume_marker.write_text("pretend burr sqlite state\n", encoding="utf-8")

    good_rec = RecordingExecutor()
    good_executor = R.Executor(run_cli=good_rec.run_cli, run_agent=good_rec.run_agent, run_raw=good_rec.run_raw)
    second = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                       runs_root=runs_root, protocol=PROTOCOL, executor=good_executor,
                       retry_terminal=True)

    assert second["status"] == "completed"
    assert resume_marker.exists()   # "full"'s own resume state must survive a non-forced retry


def test_run_one_catches_orchestration_exceptions_as_failed(prepared, tmp_path: Path):
    rec = RecordingExecutor(raise_on_cli=True)
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    state = R.run_one("noplanning", prepared["project_id"], 1, workspace_root=prepared["workspace_root"],
                      runs_root=tmp_path / "runs", protocol=PROTOCOL, executor=executor)
    assert state["status"] == "failed"
    assert "simulated CLI launch failure" in state["error"]


def test_run_one_dry_run_touches_nothing(prepared, tmp_path: Path):
    runs_root = tmp_path / "runs"
    state = R.run_one("full", prepared["project_id"], 0, workspace_root=prepared["workspace_root"],
                      runs_root=runs_root, protocol=PROTOCOL, dry_run=True)
    assert state["status"] == "dry_run"
    assert "plan" in state
    assert not runs_root.exists()  # nothing materialized


def test_run_one_dry_run_unprepared_project_reports_error_not_raise(tmp_path: Path):
    state = R.run_one("full", "crust__doesnotexist", 0, workspace_root=tmp_path / "workspaces",
                      runs_root=tmp_path / "runs", protocol=PROTOCOL, dry_run=True)
    assert state["status"] == "dry_run"
    assert "error" in state


def test_run_one_unprepared_project_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        R.run_one("full", "crust__doesnotexist", 0, workspace_root=tmp_path / "workspaces",
                 runs_root=tmp_path / "runs", protocol=PROTOCOL)


# --------------------------------------------------------------------------- #
# Matrix selection + parallel execution
# --------------------------------------------------------------------------- #
def test_select_project_ids_filters_by_tool_and_id():
    manifest = {"projects": [_row("a"), {**_row("b"), "tool": "skel"}]}
    assert R.select_project_ids(manifest, tools={"skel"}) == ["crust__b"]
    assert R.select_project_ids(manifest, project_ids={"crust__a"}) == ["crust__a"]
    assert R.select_project_ids(manifest) == ["crust__a", "crust__b"]


def test_build_job_list_cartesian_product():
    jobs = R.build_job_list(["full", "noanalyzer"], ["p1", "p2"], 2)
    assert len(jobs) == 8
    assert ("full", "p1", 0) in jobs and ("noanalyzer", "p2", 1) in jobs


def test_run_matrix_sequential_preserves_order(prepared, tmp_path: Path):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    jobs = [("full", prepared["project_id"], 0)]
    results = R.run_matrix(jobs, workspace_root=prepared["workspace_root"], runs_root=tmp_path / "runs",
                           protocol=PROTOCOL, executor=executor, max_workers=1)
    assert len(results) == 1 and results[0]["status"] == "completed"


def test_run_matrix_parallel_runs_all_jobs(prepared, tmp_path: Path):
    rec = RecordingExecutor()
    executor = R.Executor(run_cli=rec.run_cli, run_agent=rec.run_agent, run_raw=rec.run_raw)
    jobs = [("full", prepared["project_id"], r) for r in range(3)]
    results = R.run_matrix(jobs, workspace_root=prepared["workspace_root"], runs_root=tmp_path / "runs",
                           protocol=PROTOCOL, executor=executor, max_workers=3)
    assert len(results) == 3
    assert all(r["status"] == "completed" for r in results)
    assert len(rec.cli_calls) == 3


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_parse_variants_all_expands_to_every_variant():
    assert R._parse_variants("all") == list(C.RUN_VARIANTS)


def test_parse_variants_comma_list():
    assert R._parse_variants("full, noanalyzer") == ["full", "noanalyzer"]


def test_parse_variants_rejects_unknown():
    with pytest.raises(ValueError):
        R._parse_variants("bogus-variant")


def test_cli_main_dry_run_all_variants_is_safe_and_writes_report(prepared, tmp_path: Path, capsys):
    out_path = tmp_path / "summary.json"
    rc = R.main([
        "--manifest", str(_write_manifest(tmp_path, prepared["project_id"])),
        "--workspace-root", str(prepared["workspace_root"]),
        "--runs-root", str(tmp_path / "runs"),
        "--variant", "all", "--project", "all", "--dry-run", "--out", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert summary["jobs"] == len(C.RUN_VARIANTS)
    assert all(r["status"] == "dry_run" for r in summary["results"])


def _write_manifest(tmp_path: Path, project_id: str) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"projects": [_row(project_id.split("__", 1)[1])]}), encoding="utf-8")
    return manifest_path
