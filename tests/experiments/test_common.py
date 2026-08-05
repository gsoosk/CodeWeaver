"""Tests for experiments/recodeagent/common.py: hashing, atomic I/O, the
Measurement/Status value type, safe subprocess execution, path-safety guards
(traversal + the native-Windows illegal-filename guard), and the minimal
schema validator. No network/LLM/toolchain access.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

from experiments.recodeagent import common as C


# --------------------------------------------------------------------------- #
# Protocol constants
# --------------------------------------------------------------------------- #
def test_expected_dataset_counts_match_paper_protocol():
    assert C.EXPECTED_TOOL_COUNTS == {"crust": 100, "oxidizer": 6, "alphatrans": 4, "skel": 8}
    assert C.EXPECTED_TOTAL_PROJECTS == 118
    assert sum(C.EXPECTED_TOOL_COUNTS.values()) == C.EXPECTED_TOTAL_PROJECTS


def test_official_artifact_hashes_pinned():
    files = C.OFFICIAL_ARTIFACT_FILES
    assert files["implementation_zip"]["md5"] == "a2151028151e0852ce4db060a22ac76a"
    assert files["results_xlsx"]["md5"] == "a404779f2dcd7ac44d43bf72f4e88b98"
    assert files["results_zip"]["md5"] == "5df332d2a1477ec30f719dd7d0ff2470"
    for spec in files.values():
        assert spec["url"].startswith(f"https://zenodo.org/api/records/{C.ZENODO_RECORD_ID}/files/")


def test_run_variants_include_all_paper_ablations():
    assert C.RUN_VARIANTS == (
        "full", "noanalyzer", "noplanning", "novalidator",
        "baseagent-condensed", "baseagent-concat",
    )
    assert "full" not in C.ABLATION_VARIANTS


def test_paper_reference_validated_tests_by_tool_sums_to_totals():
    """The paper's exact validated-test denominator is 2,107 = 623 CRUST +
    229 Oxidizer + 1,181 AlphaTrans + 74 SKEL (per this task's own protocol
    correction). This per-tool breakdown must sum to both
    PAPER_REFERENCE_TOTALS["validated_tests"] (2107) and, restricted to the
    non-CRUST tools, to PAPER_REFERENCE_TOTALS["translated_tests"] (1484,
    CRUST excluded per the paper's own protocol)."""
    by_tool = C.PAPER_REFERENCE_VALIDATED_TESTS_BY_TOOL
    assert by_tool == {"crust": 623, "oxidizer": 229, "alphatrans": 1181, "skel": 74}
    assert sum(by_tool.values()) == C.PAPER_REFERENCE_TOTALS["validated_tests"] == 2107
    non_crust_sum = by_tool["oxidizer"] + by_tool["alphatrans"] + by_tool["skel"]
    assert non_crust_sum == C.PAPER_REFERENCE_TOTALS["translated_tests"] == 1484


def test_paper_exercised_function_inventory_matches_non_crust_denominator():
    assert len(C.PAPER_EXERCISED_FUNCTIONS_BY_PROJECT) == 18
    assert sum(C.PAPER_EXERCISED_FUNCTIONS_BY_PROJECT.values()) == 1397


# --------------------------------------------------------------------------- #
# Measurement / Status
# --------------------------------------------------------------------------- #
def test_measurement_ok_requires_a_value():
    m = C.Measurement.ok(42)
    assert m.is_measured
    assert m.to_dict() == {"value": 42, "status": "measured", "reason": ""}


def test_measurement_measured_none_is_rejected():
    # A "measured" Measurement with value=None is indistinguishable from
    # "missing" downstream -- the constructor must refuse it.
    with pytest.raises(ValueError):
        C.Measurement(value=None, status=C.Status.MEASURED)


def test_measurement_missing_is_not_zero():
    m = C.Measurement.missing("report.json not found")
    assert m.value is None
    assert m.status == C.Status.MISSING
    assert not m.is_measured
    assert m.value != 0  # sanity: None must never compare/serialize as 0


def test_measurement_unknown_status_rejected():
    with pytest.raises(ValueError):
        C.Measurement(value=1, status="bogus")


def test_measurement_flatten_produces_three_columns():
    m = C.Measurement.error("timeout")
    flat = m.flatten("coverage")
    assert flat == {"coverage": None, "coverage_status": "error", "coverage_reason": "timeout"}


def test_measurement_from_dict_roundtrip():
    m = C.Measurement.ok("x")
    back = C.measurement_from_dict(m.to_dict())
    assert back == m


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #
def test_file_md5_and_sha256(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"hello world")
    import hashlib
    assert C.file_md5(p) == hashlib.md5(b"hello world").hexdigest()
    assert C.file_sha256(p) == hashlib.sha256(b"hello world").hexdigest()


# --------------------------------------------------------------------------- #
# Atomic file I/O
# --------------------------------------------------------------------------- #
def test_atomic_write_json_writes_readable_file(tmp_path: Path):
    p = tmp_path / "sub" / "state.json"
    C.atomic_write_json(p, {"a": 1, "b": [1, 2, 3]})
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1, "b": [1, 2, 3]}


def test_atomic_write_leaves_no_tmp_file_behind(tmp_path: Path):
    p = tmp_path / "state.json"
    C.atomic_write_json(p, {"ok": True})
    leftovers = list(tmp_path.glob(".*.tmp"))
    assert leftovers == []


def test_atomic_write_failure_does_not_corrupt_existing_file(tmp_path: Path, monkeypatch):
    p = tmp_path / "state.json"
    C.atomic_write_json(p, {"version": 1})

    def _boom(*a, **k):
        raise OSError("simulated crash between write and replace")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError):
        C.atomic_write_json(p, {"version": 2})
    # original file must be untouched -- no torn/partial write.
    assert json.loads(p.read_text(encoding="utf-8")) == {"version": 1}
    assert list(tmp_path.glob(".*.tmp")) == []  # temp file cleaned up on failure


def test_read_json_or_returns_default_when_missing(tmp_path: Path):
    assert C.read_json_or(tmp_path / "nope.json", "default") == "default"


def test_read_json_or_returns_default_on_corrupt_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert C.read_json_or(p, {"fallback": True}) == {"fallback": True}


def test_append_and_read_jsonl(tmp_path: Path):
    p = tmp_path / "log.jsonl"
    C.append_jsonl(p, {"i": 1})
    C.append_jsonl(p, {"i": 2})
    assert C.read_jsonl(p) == [{"i": 1}, {"i": 2}]


def test_read_jsonl_skips_corrupt_lines(tmp_path: Path):
    p = tmp_path / "log.jsonl"
    p.write_text('{"i": 1}\nnot json\n{"i": 2}\n', encoding="utf-8")
    assert C.read_jsonl(p) == [{"i": 1}, {"i": 2}]


def test_read_jsonl_missing_file_returns_empty(tmp_path: Path):
    assert C.read_jsonl(tmp_path / "nope.jsonl") == []


# --------------------------------------------------------------------------- #
# Copilot CLI JSONL event parsing
# --------------------------------------------------------------------------- #
def test_parse_copilot_jsonl_skips_blank_and_invalid_lines():
    raw = '{"type": "user.message"}\n\n   \nnot json at all\n{"type": "assistant.message"}\n'
    events = C.parse_copilot_jsonl(raw)
    assert events == [{"type": "user.message"}, {"type": "assistant.message"}]


def test_parse_copilot_jsonl_empty_input():
    assert C.parse_copilot_jsonl("") == []
    assert C.parse_copilot_jsonl(None) == []


def test_summarize_copilot_events_counts_turns_and_tools():
    events = [
        {"type": "user.message"},
        {"type": "assistant.message", "data": {
            "toolRequests": [{"name": "view"}, {"name": "bash"}],
        }},
        {"type": "tool.execution_complete", "data": {"success": True}},
        {"type": "assistant.message"},
        {"type": "tool.execution_complete", "data": {"success": False}},
        {"type": "result", "exitCode": 0, "usage": {
            "premiumRequests": 3, "sessionDurationMs": 45000,
            "codeChanges": {"filesModified": ["a.py", "b.py"], "linesAdded": 10, "linesRemoved": 2},
        }},
    ]
    summary = C.summarize_copilot_events(events)
    assert summary.assistant_turns == 2
    assert summary.tool_invocations == 2
    assert summary.tool_counts == {"view": 1, "bash": 1}
    assert summary.exit_code == 0
    assert summary.premium_requests == 3
    assert summary.session_duration_ms == 45000
    assert summary.files_modified == ["a.py", "b.py"]
    assert summary.lines_added == 10
    assert summary.lines_removed == 2


def test_summarize_copilot_events_tokens_unavailable_when_absent():
    events = [{"type": "result", "exitCode": 0, "usage": {"premiumRequests": 1}}]
    summary = C.summarize_copilot_events(events)
    assert summary.input_tokens is None
    assert summary.output_tokens is None
    assert summary.tokens_status == C.Status.UNAVAILABLE
    assert summary.tokens_reason  # explains why, never silently 0


def test_summarize_copilot_events_tokens_measured_when_present_variant_keys():
    events = [{"type": "result", "usage": {"promptTokens": 120, "completionTokens": 80}}]
    summary = C.summarize_copilot_events(events)
    assert summary.input_tokens == 120
    assert summary.output_tokens == 80
    assert summary.tokens_status == C.Status.MEASURED
    assert summary.tokens_reason == ""


def test_summarize_copilot_events_sums_assistant_message_output_tokens():
    events = [
        {"type": "assistant.message", "data": {"outputTokens": 12}},
        {"type": "assistant.message", "data": {"outputTokens": 8}},
        {"type": "result", "usage": {"premiumRequests": 1}},
    ]
    summary = C.summarize_copilot_events(events)
    assert summary.input_tokens is None
    assert summary.output_tokens == 20
    assert summary.tokens_status == C.Status.MEASURED
    assert "input tokens" in summary.tokens_reason


def test_summarize_copilot_events_reads_usage_checkpoint():
    events = [
        {"type": "session.usage_checkpoint", "data": {
            "totalNanoAiu": 78137235000,
            "totalPremiumRequests": 1,
        }},
        {"type": "result", "usage": {}},
    ]
    summary = C.summarize_copilot_events(events)
    assert summary.nano_aiu == 78137235000
    assert summary.premium_requests == 1


def test_summarize_copilot_events_empty_list_is_all_defaults():
    summary = C.summarize_copilot_events([])
    assert summary.exit_code is None
    assert summary.assistant_turns == 0
    assert summary.tool_invocations == 0
    assert summary.tokens_status == C.Status.UNAVAILABLE


# --------------------------------------------------------------------------- #
# Safe subprocess execution
# --------------------------------------------------------------------------- #
def test_run_argv_rejects_shell_strings():
    with pytest.raises(TypeError):
        C.run_argv("echo hello; rm -rf /")  # type: ignore[arg-type]


def test_run_argv_executes_python_and_captures_stdout():
    res = C.run_argv([sys.executable, "-c", "print('hi')"])
    assert res.ok
    assert res.returncode == 0
    assert "hi" in res.stdout
    assert not res.timed_out


def test_run_argv_captures_nonzero_exit():
    res = C.run_argv([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert res.returncode == 3
    assert not res.ok


def test_run_argv_timeout_is_recorded_not_raised():
    res = C.run_argv([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)
    assert res.timed_out
    assert res.returncode is None
    assert "timed out" in res.error


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group semantics")
def test_run_argv_timeout_kills_descendants_holding_output_pipes(tmp_path: Path):
    pid_path = tmp_path / "child.pid"
    child = "import time; time.sleep(30)"
    parent = (
        "import pathlib,subprocess,sys,time; "
        f"p=subprocess.Popen([sys.executable,'-c',{child!r}]); "
        f"pathlib.Path({str(pid_path)!r}).write_text(str(p.pid)); "
        "time.sleep(30)"
    )
    started = time.monotonic()
    result = C.run_argv([sys.executable, "-c", parent], timeout=0.3)

    assert result.timed_out
    assert time.monotonic() - started < 3
    child_pid = int(pid_path.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and Path(f"/proc/{child_pid}").exists():
        time.sleep(0.02)
    assert not Path(f"/proc/{child_pid}").exists()


def test_run_argv_missing_executable_is_recorded_not_raised():
    res = C.run_argv(["this-binary-does-not-exist-xyz"])
    assert res.returncode is None
    assert res.error  # OSError repr captured, not propagated


# --------------------------------------------------------------------------- #
# Path safety: traversal rejection
# --------------------------------------------------------------------------- #
def test_resolve_within_accepts_normal_relative_path(tmp_path: Path):
    result = C.resolve_within(tmp_path, "a/b/c.txt")
    assert result == (tmp_path / "a" / "b" / "c.txt").resolve()


@pytest.mark.parametrize("member", [
    "../evil.txt",
    "a/../../evil.txt",
    "../../../../etc/passwd",
])
def test_resolve_within_rejects_dotdot_traversal(tmp_path: Path, member):
    with pytest.raises(C.PathTraversalError):
        C.resolve_within(tmp_path, member)


def test_resolve_within_rejects_absolute_posix_path(tmp_path: Path):
    with pytest.raises(C.PathTraversalError):
        C.resolve_within(tmp_path, "/etc/passwd")


def test_resolve_within_rejects_windows_drive_path(tmp_path: Path):
    with pytest.raises(C.PathTraversalError):
        C.resolve_within(tmp_path, "C:\\Windows\\System32\\evil.dll")


def test_resolve_within_rejects_unc_path(tmp_path: Path):
    with pytest.raises(C.PathTraversalError):
        C.resolve_within(tmp_path, "//server/share/evil.txt")


# --------------------------------------------------------------------------- #
# Windows-unsafe filename guard (the artifact is documented to contain '*')
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", [
    "results/foo*.txt",
    'weird"name.txt',
    "a<b>c.txt",
    "pipe|name.txt",
    "question?mark.txt",
    "CON.txt",
    "trailing.dot.",
    "trailing space ",
])
def test_windows_unsafe_reason_flags_illegal_names(name):
    assert C.windows_unsafe_reason(name) is not None


@pytest.mark.parametrize("name", [
    "normal/path/file.txt",
    "dir/sub-dir/name_1.2.rs",
    "a.b.c",
])
def test_windows_unsafe_reason_accepts_normal_names(name):
    assert C.windows_unsafe_reason(name) is None


def test_is_native_windows_reflects_platform():
    import platform
    assert C.is_native_windows() == (platform.system() == "Windows")


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #
def test_collect_provenance_has_measurement_shaped_fields():
    prov = C.collect_provenance(model="claude-sonnet-4.5", agent_timeout=5000, probe_toolchains=False)
    for key in ("model", "agent_timeout_seconds", "git_sha", "codeweaver_package_version",
               "copilot_cli_version", "python_version", "os", "hostname"):
        assert key in prov
        assert set(prov[key]) == {"value", "status", "reason"}
        assert prov[key]["status"] in C.Status.ALL
    assert prov["model"]["status"] == C.Status.MEASURED
    assert prov["model"]["value"] == "claude-sonnet-4.5"


def test_collect_provenance_without_model_is_not_applicable_not_fabricated():
    prov = C.collect_provenance(probe_toolchains=False)
    assert prov["model"]["status"] == C.Status.NOT_APPLICABLE
    assert prov["model"]["value"] is None


def test_probe_tool_version_unavailable_for_bogus_tool():
    m = C.probe_tool_version(["this-tool-does-not-exist-xyz", "--version"])
    assert m.status == C.Status.UNAVAILABLE
    assert m.value is None


def test_git_sha_measures_repo_root():
    m = C.git_sha()
    # This harness lives inside a git repo in CI/dev; if git is unavailable the
    # function must still degrade to an error Measurement, never raise.
    assert m.status in (C.Status.MEASURED, C.Status.ERROR)
    if m.status == C.Status.MEASURED:
        assert len(m.value) == 40


# --------------------------------------------------------------------------- #
# Optional dependency probing
# --------------------------------------------------------------------------- #
def test_optional_import_unknown_module_returns_none():
    assert C.optional_import("definitely_not_a_real_module_xyz") is None


def test_optional_dependency_report_shape():
    report = C.optional_dependency_report()
    assert set(report) == {"pandas", "matplotlib", "reportlab", "scipy", "sentence_transformers", "openpyxl"}
    assert all(isinstance(v, bool) for v in report.values())


# --------------------------------------------------------------------------- #
# Minimal schema validator
# --------------------------------------------------------------------------- #
SIMPLE_SCHEMA = {
    "type": "object",
    "required": ["id", "count"],
    "properties": {
        "id": {"type": "string"},
        "count": {"type": "integer"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


def test_validate_schema_accepts_valid_object():
    assert C.validate_schema({"id": "a", "count": 3, "tags": ["x", "y"]}, SIMPLE_SCHEMA) == []


def test_validate_schema_reports_missing_required():
    errors = C.validate_schema({"count": 3}, SIMPLE_SCHEMA)
    assert any("id" in e for e in errors)


def test_validate_schema_reports_wrong_type():
    errors = C.validate_schema({"id": "a", "count": "not an int"}, SIMPLE_SCHEMA)
    assert any("count" in e for e in errors)


def test_validate_schema_rejects_bool_as_integer():
    # bool is a subclass of int in Python; the validator must not accept it
    # where an "integer" is required (a common JSON-schema footgun).
    errors = C.validate_schema({"id": "a", "count": True}, SIMPLE_SCHEMA)
    assert any("count" in e for e in errors)


def test_validate_schema_reports_additional_properties():
    errors = C.validate_schema({"id": "a", "count": 1, "extra": True}, SIMPLE_SCHEMA)
    assert any("extra" in e for e in errors)


def test_validate_schema_validates_array_items():
    errors = C.validate_schema({"id": "a", "count": 1, "tags": ["ok", 5]}, SIMPLE_SCHEMA)
    assert any("tags[1]" in e for e in errors)


# --------------------------------------------------------------------------- #
# Misc formatting helpers
# --------------------------------------------------------------------------- #
def test_slugify_normalizes():
    assert C.slugify("Hello, World!  Weird//Name") == "hello-world-weird-name"


def test_dict_to_flat_row_expands_measurements_and_nesting():
    row = C.dict_to_flat_row({
        "loc": C.Measurement.ok(120),
        "nested": {"a": 1, "b": C.Measurement.missing("x")},
    })
    assert row["loc"] == 120
    assert row["loc_status"] == "measured"
    assert row["nested_a"] == 1
    assert row["nested_b"] is None
    assert row["nested_b_status"] == "missing"
