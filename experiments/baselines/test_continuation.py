#!/usr/bin/env python3
"""Offline test of the block-aware continuation loop. No API, no cost.

Simulates a backend whose output cap forces the generation across several responses,
including the nasty case: a response that is cut off MID-FILE. Asserts that the loop
(a) discards the half-written block rather than splicing broken Python together,
(b) asks only for what is still missing, and (c) converges to every module.
"""
import pathlib
from contextlib import redirect_stdout
import io
import sys
import json
import subprocess
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from backends.base import Completion, Usage  # noqa: E402
import single_shot  # noqa: E402
from backends.copilot import CopilotBackend, command, decode_events  # noqa: E402
import run_one  # noqa: E402
from test_copilot_api import run_tests as run_api_transport_tests  # noqa: E402
from test_repair_loop import run_tests as run_repair_loop_tests  # noqa: E402
from run_one import parse_score, select_worst  # noqa: E402

MODULES = [f"src/main/pkg/Mod{i}.py" for i in range(1, 8)]
CSV_MODULES = [f"src/main/pkg/{name}.py" for name in (
    "Constants", "CSVFormat", "CSVPrinter", "CSVRecord", "DuplicateHeaderMode",
    "ExtendedBufferedReader", "IOUtils", "Lexer", "QuoteMode", "Token", "CSVParser",
)]
REVISION = "6ef1855b665c2f447f596b810eca9b516e333246"


def scratch():
    return tempfile.TemporaryDirectory(prefix="offline_b0_", dir=pathlib.Path.cwd())


def block(name):
    return f"{{{{{name}}}}}\n```python\nvalue = {name!r}\n```"


def event_stream(parts):
    events = []
    for index, part in enumerate(parts):
        if index:
            events.append({"type": "user.message", "data": {"content": "Please continue from where you left off."}})
        events.extend([
            {"type": "model.call_start", "data": {}},
            {"type": "assistant.message", "data": {"content": part, "outputTokens": 32000}},
        ])
    events.append({"type": "session.usage_checkpoint",
                   "data": {"totalPremiumRequests": len(parts), "totalNanoAiu": 9}})
    return "\n".join(json.dumps(event) for event in events)


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")


def source_fixture(root, *, complete=False, extra=False):
    subject = root / "subjects/example"
    scaffold = subject / ".scaffold"
    modules = CSV_MODULES + (["src/main/pkg/Extra.py"] if extra else [])
    for name in modules:
        target = scaffold / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("value = None\n", encoding="utf-8")
    java = root / "java"
    java.mkdir()
    (java / "Example.java").write_text("class Example {}", encoding="utf-8")
    system, user = single_shot.build_prompt(
        "example", single_shot.collect_java(java), single_shot.collect_skeleton(scaffold))
    source = subject / "pipeline-baseline-original"
    audit_dir = source / "backend-audit/round-01"
    audit_dir.mkdir(parents=True)
    parts = ["", "\n\n".join(block(name) for name in CSV_MODULES[:10])
             + "\n\n{{src/main/pkg/CSVParser.py}}\n```python\nBROKEN_PARTIAL = (",
             block(CSV_MODULES[10]) if complete else "    tail_only)\nModel prose."]
    stream = event_stream(parts)
    decoded = decode_events(stream)
    audit = decoded.audit(1, 0)
    audit.pop("usage")  # The frozen pre-fix collector stored usage only in metadata.
    usage = {**decoded.usage.as_dict(), "wall_clock_s": 5.0}
    write_json(audit_dir / "audit.json", audit)
    prompt = f"{system}\n\n---\n\n{user}"
    write_json(audit_dir / "request.json", {
        "argv": command("copilot", "test-model", "medium", "long_context"),
        "cwd_policy": "empty temporary directory", "prompt_chars": len(prompt),
        "prompt_sha256": single_shot.sha256(prompt.encode("utf-8")),
    })
    (audit_dir / "stdout.jsonl").write_text(stream, encoding="utf-8", newline="\n")
    (audit_dir / "stderr.txt").write_text("", encoding="utf-8")
    (source / "prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
    (source / "response.md").write_text(parts[-1], encoding="utf-8")
    (source / "oracle_score.txt").write_text("FORBIDDEN CORRECTNESS FEEDBACK", encoding="utf-8")
    write_json(source / "score.json", {"error": "FORBIDDEN CORRECTNESS FEEDBACK"})
    write_json(source / "metadata.json", {
        "baseline": "B0-single-shot", "backend": "copilot", "project": "example",
        "model": "test-model", "effort": "medium", "context": "long_context",
        "usage_per_round": [usage], "continuation_rounds": 1, "copilot_audit": [audit],
        "oracle_seen": False, "oracle_tests_in_prompt": False,
        "oracle_feedback_during_generation": False,
    })
    write_json(subject / "pipeline-baseline-original.status.json", {
        "state": "scoring_failed", "code_revision": REVISION, "copilot_version": "test-cli",
        "error": "FORBIDDEN CORRECTNESS FEEDBACK",
    })
    return subject, source, system, user, set(modules), {
        "source_dir": java, "tier": "A", "model": "test-model", "effort": "medium",
    }


def recover(fixture, max_rounds=6, tag="original"):
    subject, _, system, user, expected, _ = fixture
    return single_shot.load_recovery(
        subject, tag, "example", system, user, expected, model="test-model",
        effort="medium", context="long_context", max_rounds=max_rounds)


def snapshot_source(fixture):
    subject, source, *_ = fixture
    return {path: path.read_bytes() for path in [*source.rglob("*"), subject / "pipeline-baseline-original.status.json"]
            if path.is_file()}


def invoke_main(root, config, tag, *, max_rounds=6, resume="original"):
    argv = ["single_shot.py", "--project", "example", "--tag", tag,
            "--context", "long_context", "--max-rounds", str(max_rounds)]
    if resume:
        argv.extend(["--resume-tag", resume])
    with (patch.object(single_shot, "EXAMPLE", root),
          patch.object(single_shot, "read_config", return_value=config),
          patch.object(single_shot, "code_provenance", return_value={"code_revision": REVISION}),
          patch.object(sys, "argv", argv),
          redirect_stdout(io.StringIO())):
        return single_shot.main()


class ChunkedBackend:
    """Emits at most `per_round` modules, and truncates the next one mid-body."""
    name, model = "fake", "fake-model"

    def __init__(self, per_round=3):
        self.per_round = per_round
        self.calls = 0

    def _emit(self, names, truncate_next):
        out = []
        for n in names:
            out.append(f"{{{{{n}}}}}\n```python\ndef f():\n    return {n!r}\n```")
        if truncate_next:
            # A block that opens but never closes -- exactly what a mid-file cut looks like.
            out.append("{{src/main/pkg/TRUNCATED.py}}\n```python\ndef broken(:\n")
        return "\n\n".join(out)

    def _respond(self, remaining):
        self.calls += 1
        batch = remaining[:self.per_round]
        more = len(remaining) > self.per_round
        text = self._emit(batch, truncate_next=more)
        return Completion(text=text, usage=Usage(completion_tokens=100),
                          model=self.model,
                          raw={"finish_reason": "length" if more else "stop",
                               "truncated": more})

    def complete(self, system, user):
        return self._respond(MODULES)

    def complete_messages(self, messages):
        # The harness lists what is still missing in the final user turn.
        asked = [m for m in MODULES if m in messages[-1]["content"]]
        return self._respond(asked)


def test_backend_protocol():
    message = {"type": "assistant.message", "data": {"content": "complete"}}
    usage = {"type": "session.usage_checkpoint", "data": {"totalPremiumRequests": 1, "totalNanoAiu": 5}}
    output = "\n".join(json.dumps(event) for event in (message, usage))
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        backend = CopilotBackend(audit_dir=root, context="long_context")
        completed = subprocess.CompletedProcess([], 0, stdout=output, stderr="")
        with patch("backends.copilot.subprocess.run", return_value=completed) as invoke:
            result = backend.complete("system", "x" * 250000)
            argv = invoke.call_args.args[0]
            assert "--available-tools=__b0_no_tools__" in argv
            assert all(f"--deny-tool={kind}" in argv for kind in ("read", "write", "shell"))
            assert "--no-custom-instructions" in argv and "--disable-builtin-mcps" in argv
            assert "--allow-all" not in argv and "-p" not in argv
            assert len(invoke.call_args.kwargs["input"]) > 250000
            assert argv[-2:] == ["--context", "long_context"]
            assert result.usage.premium_requests == 1
            assert (root / "round-01/stdout.jsonl").read_text() == output
            backend.complete_messages([{"role": "user", "content": "continue"}])
            assert (root / "round-02/audit.json").exists()
            assert len(backend.audit_records) == 2
        for event in (
            {"type": "tool.execution_start", "data": {"toolName": "read_file"}},
            {"type": "assistant.tool_call_delta", "data": {}},
            {"type": "assistant.message", "data": {"toolRequests": [{"name": "shell"}]}},
        ):
            completed.stdout = output + "\n" + json.dumps(event)
            with patch("backends.copilot.subprocess.run", return_value=completed):
                try:
                    backend.complete("", "input")
                except RuntimeError as exc:
                    assert "protocol violation" in str(exc)
                else:
                    raise AssertionError("Tool activity was accepted")
        completed.stdout = output
        completed.returncode = 1
        with patch("backends.copilot.subprocess.run", return_value=completed):
            try:
                backend.complete("", "input")
            except RuntimeError as exc:
                assert "exited 1" in str(exc)
            else:
                raise AssertionError("A failed CLI invocation was accepted")
        completed.returncode = 0
        for malformed in (
            "not JSON", "{broken", "[]", '{"type": "assistant.message", "data": []}',
            '{"type":"tool.execution_start","type":"ignored","data":{}}',
            '{"type":"result","usage":[]}', '{"type":"result","usage":{"premiumRequests":NaN}}',
        ):
            completed.stdout = output + "\n" + malformed
            with patch("backends.copilot.subprocess.run", return_value=completed):
                try:
                    backend.complete("", "input")
                except RuntimeError:
                    audit_path = root / f"round-{backend.calls:02d}"
                    assert (audit_path / "stdout.jsonl").read_text() == completed.stdout
                    assert json.loads((audit_path / "audit.json").read_text())["valid"] is False
                else:
                    raise AssertionError("Malformed JSONL was accepted")
        with patch("backends.copilot.subprocess.run", side_effect=subprocess.TimeoutExpired(
            "copilot", 1, output=b'{"type":"model.call_start","data":{}}\n', stderr=b"timeout")):
            try:
                backend.complete("", "input")
            except subprocess.TimeoutExpired:
                audit_path = root / f"round-{backend.calls:02d}"
                assert (audit_path / "stderr.txt").read_text() == "timeout"
                assert json.loads((audit_path / "audit.json").read_text())["valid"] is False
            else:
                raise AssertionError("Timeout not raised/audited")
    print("PASS: no-tool flags, stdin, immutable round audits and fail-closed tool detection")


def test_score_selection():
    reference = parse_score("[oracle] result : 13 failed, 368 passed, 56 skipped\n[oracle] exitcode : 1")
    worse = parse_score("[oracle] result : 20 failed, 361 passed, 56 skipped\n[oracle] exitcode : 1")
    better = parse_score("[oracle] result : 1 failed, 380 passed, 56 skipped\n[oracle] exitcode : 1")
    assert select_worst(worse, reference) == "current"
    assert select_worst(better, reference) == "reference"
    assert select_worst(reference, reference) == "reference"
    try:
        select_worst({**worse, "deselected": 1}, reference)
    except ValueError:
        pass
    else:
        raise AssertionError("Incomparable oracle denominators were accepted")
    print("PASS: transparent worst-of-two selection, including ties and exclusion mismatches")


def test_existing_run_is_preserved():
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        subject = root / "subjects/example"
        scaffold = subject / ".scaffold/src/main"
        scaffold.mkdir(parents=True)
        (scaffold / "Module.py").write_text("class Module:\n    pass\n")
        java = root / "java"
        java.mkdir()
        (java / "Module.java").write_text("class Module {}")
        existing = subject / "pipeline-baseline-existing"
        existing.mkdir()
        marker = existing / "metadata.json"
        marker.write_text('{"preserve": true}')
        config = {"source_dir": java, "tier": "A", "model": "fake", "effort": "medium"}
        with (
            patch.object(single_shot, "EXAMPLE", root),
            patch.object(single_shot, "read_config", return_value=config),
            patch.object(single_shot, "build_backend") as build,
            patch.object(sys, "argv", ["single_shot.py", "--project", "example", "--tag", "existing"]),
        ):
            try:
                single_shot.main()
            except SystemExit as exc:
                assert "refusing to overwrite" in str(exc)
            else:
                raise AssertionError("An existing run was overwritten")
            build.assert_not_called()
            assert marker.read_text() == '{"preserve": true}'
    print("PASS: an existing tagged result is preserved without spending a model call")


def test_internal_messages():
    first = block(MODULES[0]) + f"\n{{{{{MODULES[1]}}}}}\n```python\nbroken = ("
    tail = "tail)\n```\n" + block(MODULES[2])
    completed = subprocess.CompletedProcess([], 0, stdout=event_stream(["", first, tail]), stderr="")
    with scratch() as temporary:
        backend = CopilotBackend(audit_dir=pathlib.Path(temporary))
        with patch("backends.copilot.subprocess.run", return_value=completed):
            completion = backend.complete("system", "user")
        assert completion.raw["assistant_messages"] == [first, tail]
        assert first in completion.text and tail in completion.text
        assert completion.raw["event_counts"]["model.call_start"] == 3
        assert completion.raw["event_counts"]["assistant.message"] == 3
        assert len(completion.raw["transcript_messages"]) == 5
        backend.complete = Mock(return_value=completion)
        files, transcript, usages, rounds = single_shot.generate(
            backend, "system", "user", {MODULES[0], MODULES[2]}, 1)
        assert set(files) == {MODULES[0], MODULES[2]}  # No cross-message closing-fence stitching.
        assert "Please continue from where you left off." in transcript
        assert first in transcript and tail in transcript
        assert rounds == len(usages) == 1
    print("PASS: all assistant messages retained, internal calls counted, cross-message stitching forbidden")


def test_recovery_loop():
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        fixture = source_fixture(root)
        before = snapshot_source(fixture)
        recovered = recover(fixture)
        assert len(single_shot.completion_files(recovered.completions[0])) == 10
        assert recovered.provenance["source_backend_invocations"] == 1
        backend = Mock()
        backend.complete_messages.return_value = Completion(
            block(CSV_MODULES[-1]), Usage(premium_requests=2, nano_aiu=4, wall_clock_s=2), "test-model")
        files, transcript, usages, rounds = single_shot.generate(
            backend, fixture[2], fixture[3], fixture[4], 6, prior_completions=recovered.completions)
        backend.complete.assert_not_called()
        assert backend.complete_messages.call_count == 1
        messages = backend.complete_messages.call_args.args[0]
        assert "IN FULL" in messages[-1]["content"]
        assert [name for name in CSV_MODULES if name in messages[-1]["content"]] == [CSV_MODULES[-1]]
        sent = json.dumps(messages)
        assert "FORBIDDEN CORRECTNESS FEEDBACK" not in sent and "BROKEN_PARTIAL" not in sent
        assert set(files) == fixture[4] and rounds == 2
        assert "BROKEN_PARTIAL" in transcript and "tail_only" in transcript
        assert "BROKEN_PARTIAL" not in "".join(files.values())
        assert usages[0] == recovered.completions[0].usage.as_dict()
        assert sum(usage["premium_requests"] for usage in usages) == 5
        assert snapshot_source(fixture) == before
        backend.reset_mock()
        files, _, usages, rounds = single_shot.generate(
            backend, fixture[2], fixture[3], fixture[4], 1, prior_completions=recovered.completions)
        backend.complete_messages.assert_not_called()
        assert len(files) == 10 and rounds == len(usages) == 1
        try:
            recover(fixture, max_rounds=0)
        except ValueError as exc:
            assert "TOTAL budget" in str(exc)
        else:
            raise AssertionError("Source budget silently reset")
    with scratch() as temporary:
        fixture = source_fixture(pathlib.Path(temporary), extra=True)
        recovered = recover(fixture)
        backend = Mock()
        backend.complete_messages.return_value = Completion(block(CSV_MODULES[-1]), Usage(nano_aiu=1), "test-model")
        files, _, _, rounds = single_shot.generate(
            backend, fixture[2], fixture[3], fixture[4], 2, prior_completions=recovered.completions)
        assert backend.complete_messages.call_count == 1 and rounds == 2 and len(files) == 11
    print("PASS: 10 closed CSV blocks recovered; only full CSVParser requested, source usage and total budget retained")


def test_recovery_artifacts():
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        fixture = source_fixture(root)
        before = snapshot_source(fixture)
        completed = subprocess.CompletedProcess([], 0, stdout=event_stream([block(CSV_MODULES[-1])]), stderr="")
        with patch("backends.copilot.subprocess.run", return_value=completed) as invoke:
            assert invoke_main(root, fixture[-1], "recovered") == 0
            assert invoke.call_count == 1
        run = fixture[0] / "pipeline-baseline-recovered"
        metadata = json.loads((run / "metadata.json").read_text())
        assert metadata["complete"] is True
        assert metadata["observation_tag"] == "original" and not metadata["independent_sample"]
        assert metadata["backend_invocations"] == 2 and metadata["new_backend_invocations"] == 1
        assert metadata["observed_model_calls"] == metadata["observed_assistant_turns"] == 4
        assert metadata["usage"]["premium_requests"] == 4 and metadata["usage"]["nano_aiu"] == 18
        assert [audit["round"] for audit in metadata["copilot_audit"]] == [1, 2]
        assert [audit["origin_tag"] for audit in metadata["copilot_audit"]] == ["original", "recovered"]
        assert (run / "backend-audit/round-01/stdout.jsonl").read_bytes() == before[fixture[1] / "backend-audit/round-01/stdout.jsonl"]
        assert metadata["recovery"]["source_artifact_sha256"]
        assert snapshot_source(fixture) == before
        with (patch.object(single_shot, "build_backend") as build,
              redirect_stdout(io.StringIO())):
            assert invoke_main(root, fixture[-1], "replayed", resume="recovered") == 0
            build.assert_not_called()
        replayed = json.loads((fixture[0] / "pipeline-baseline-replayed/metadata.json").read_text())
        assert replayed["new_backend_invocations"] == 0
        assert replayed["backend_invocations"] == 2
        assert replayed["usage"] == metadata["usage"]
        assert replayed["observation_tag"] == "original"
        assert snapshot_source(fixture) == before
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        fixture = source_fixture(root, complete=True)
        with patch.object(single_shot, "build_backend") as build:
            assert invoke_main(root, fixture[-1], "all-closed") == 0
            build.assert_not_called()
        result = json.loads((fixture[0] / "pipeline-baseline-all-closed/metadata.json").read_text())
        assert result["complete"] and result["new_backend_invocations"] == 0
        assert result["observed_model_calls"] == 3
    print("PASS: linked artifacts preserve source bytes/hashes, usage, round identities; complete replay costs no call")


def test_recovery_rejections():
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        fixture = source_fixture(root)
        source = fixture[1]
        audit_dir = source / "backend-audit/round-01"
        status_path = fixture[0] / "pipeline-baseline-original.status.json"
        meta_path = source / "metadata.json"
        meta = json.loads(meta_path.read_text())
        request_path = audit_dir / "request.json"
        request = json.loads(request_path.read_text())
        audit_path = audit_dir / "audit.json"
        audit = json.loads(audit_path.read_text())
        stream_path = audit_dir / "stdout.jsonl"
        stream = stream_path.read_text()
        modifications = [
            (source / "prompt.md", b"wrong prompt"),
            (meta_path, []),
            (meta_path, {**meta, "model": "other"}),
            (meta_path, {**meta, "effort": "high"}),
            (meta_path, {**meta, "context": "default"}),
            (meta_path, {**meta, "usage_per_round": "invalid"}),
            (meta_path, {**meta, "usage_per_round": [{"nano_aiu": -1}]}),
            (meta_path, {**meta, "usage_per_round": [{"nano_aiu": 999, "premium_requests": 3}]}),
            (meta_path, {**meta, "continuation_rounds": True}),
            (meta_path, {**meta, "backend_invocations": 2}),
            (meta_path, {**meta, "copilot_audit": [{}]}),
            (meta_path, {**meta, "copilot_audit": [{**audit, "returncode": False}]}),
            (request_path, {**request, "argv": [arg for arg in request["argv"] if arg != "--deny-tool=shell"]}),
            (request_path, {**request, "prompt_sha256": "0" * 64}),
            (request_path, {**request, "cwd_policy": "repository"}),
            (audit_path, {**audit, "returncode": 1}),
            (audit_path, {**audit, "valid": False}),
            (audit_path, {**audit, "event_counts": {}}),
            (audit_path, {**audit, "tool_event_count": False}),
            (audit_path, []),
            (stream_path, (stream + "\nnot JSON").encode()),
            (stream_path, (stream + '\n{"type":"assistant.message","data":{"content":[]}}').encode()),
            (stream_path, (stream + '\n{"type":"user.message","data":{"content":"oracle feedback"}}').encode()),
            (status_path, {"state": "generating", "code_revision": REVISION}),
            (status_path, {"state": "scoring", "code_revision": REVISION}),
            (status_path, {"state": "unexpected", "code_revision": REVISION}),
            (status_path, {"state": []}),
            (status_path, None),
            (audit_path, None),
            (audit_dir / "stderr.txt", None),
        ]
        for event in (
            {"type": "tool.execution_start", "data": {"toolName": "read_file"}},
            {"type": "assistant.tool_call_delta", "data": {}},
            {"type": "assistant.message", "data": {"content": "", "toolRequests": [{"name": "shell"}]}},
        ):
            modifications.append((stream_path, (stream + "\n" + json.dumps(event)).encode()))
        before = snapshot_source(fixture)
        for path, replacement in modifications:
            original = path.read_bytes()
            try:
                if replacement is None:
                    path.unlink()
                elif isinstance(replacement, bytes):
                    path.write_bytes(replacement)
                else:
                    write_json(path, replacement)
                with patch.object(single_shot, "build_backend") as build:
                    try:
                        invoke_main(root, fixture[-1], "rejected")
                    except (ValueError, RuntimeError):
                        pass
                    else:
                        raise AssertionError(f"Invalid recovery accepted: {path.name}: {replacement!r}")
                    build.assert_not_called()
                    assert not (fixture[0] / "pipeline-baseline-rejected").exists()
            finally:
                path.write_bytes(original)
        assert snapshot_source(fixture) == before
    print("PASS: prompt/config mismatch, unaudited/tool/nonzero/malformed streams and active sources rejected before calls")


def test_failed_collector_recovery():
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        fixture = source_fixture(root)
        before = snapshot_source(fixture)
        completed = subprocess.CompletedProcess([], 0, stdout=event_stream([block(CSV_MODULES[-1])]), stderr="")
        with (patch("backends.copilot.subprocess.run", return_value=completed),
              patch.object(single_shot, "materialize", side_effect=OSError("synthetic collector failure"))):
            try:
                invoke_main(root, fixture[-1], "collector-failed")
            except OSError:
                pass
            else:
                raise AssertionError("Expected synthetic collector failure")
        failed = fixture[0] / "pipeline-baseline-collector-failed"
        assert json.loads((failed / "generation.json").read_text())["state"] == "failed"
        assert not (failed / "metadata.json").exists()
        with patch.object(single_shot, "build_backend") as build:
            assert invoke_main(root, fixture[-1], "collector-replayed", resume="collector-failed") == 0
            build.assert_not_called()
        result = json.loads((fixture[0] / "pipeline-baseline-collector-replayed/metadata.json").read_text())
        assert result["complete"] and result["backend_invocations"] == 2
        assert result["usage"]["premium_requests"] == 4
        assert snapshot_source(fixture) == before
    print("PASS: terminal manifest and invocation audits recover even a later collector failure without another draw")


def test_legacy_multi_invocation_replay():
    with scratch() as temporary:
        fixture = source_fixture(pathlib.Path(temporary))
        _, source, system, user, expected, _ = fixture
        streams = [
            event_stream([block(CSV_MODULES[0]), block(CSV_MODULES[1])]),
            event_stream(["\n\n".join(block(name) for name in CSV_MODULES if name != CSV_MODULES[1])]),
        ]
        audits, usages = [], []
        for index, stream in enumerate(streams, 1):
            directory = source / f"backend-audit/round-{index:02d}"
            directory.mkdir(exist_ok=True)
            decoded = decode_events(stream)
            audit = decoded.audit(index, 0)
            audit.pop("usage")
            audits.append(audit)
            usages.append({**decoded.usage.as_dict(), "wall_clock_s": 5.0})
            (directory / "stdout.jsonl").write_text(stream, encoding="utf-8", newline="\n")
            (directory / "stderr.txt").write_text("", encoding="utf-8")
            write_json(directory / "audit.json", audit)
        legacy_files = single_shot.parse_response(block(CSV_MODULES[1]))
        prompt = single_shot.flatten_messages(single_shot.continuation_messages(
            system, user, legacy_files, expected, legacy=True))
        write_json(source / "backend-audit/round-02/request.json", {
            "argv": command("copilot", "test-model", "medium", "long_context"),
            "cwd_policy": "empty temporary directory", "prompt_chars": len(prompt),
            "prompt_sha256": single_shot.sha256(prompt.encode("utf-8")),
        })
        meta = json.loads((source / "metadata.json").read_text())
        meta.update(continuation_rounds=2, copilot_audit=audits, usage_per_round=usages)
        write_json(source / "metadata.json", meta)
        recovered = recover(fixture, max_rounds=2)
        files, _, recovered_usage, count = single_shot.generate(
            None, system, user, expected, 2, prior_completions=recovered.completions)
        assert set(files) == expected and count == 2 and recovered_usage == usages
    print("PASS: legacy multi-invocation request hashes replay correctly with original usage and total budget")


def test_run_one_recovery():
    with scratch() as temporary:
        root = pathlib.Path(temporary)
        fixture = source_fixture(root, complete=True)
        before = snapshot_source(fixture)
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            if argv[0] == sys.executable:
                with patch.object(sys, "argv", argv[2:]):
                    code = single_shot.main()
                return subprocess.CompletedProcess(argv, code)
            assert argv[0] == "bash" and "--no-pipeline-skips" in argv
            assert "--working-copy" in argv and argv[-1] == "pipeline-baseline-scored/project"
            return subprocess.CompletedProcess(argv, 0, stdout="[oracle] result : 39 passed\n[oracle] exitcode : 0")

        with (patch.object(single_shot, "EXAMPLE", root),
              patch.object(single_shot, "read_config", return_value=fixture[-1]),
              patch.object(single_shot, "code_provenance", return_value={"code_revision": REVISION}),
              patch.object(single_shot, "build_backend") as build,
              patch.object(run_one.subprocess, "check_output", return_value=REVISION),
              patch.object(run_one.subprocess, "run", side_effect=run),
              patch.object(sys, "argv", ["run_one.py", "--project", "example", "--tag", "scored",
                                       "--resume-tag", "original"])):
            assert run_one.main() == 0
            build.assert_not_called()
        assert "--resume-tag" in calls[0]
        assert len(calls) == 2  # Generation/replay precedes the isolated oracle.
        run_dir = fixture[0] / "pipeline-baseline-scored"
        evidence = json.loads((run_dir / "run_evidence.json").read_text())
        state = json.loads((fixture[0] / "pipeline-baseline-scored.status.json").read_text())
        assert evidence["recovery"]["source_tag"] == state["resume_tag"] == "original"
        assert evidence["new_backend_invocations"] == 0 and not evidence["independent_sample"]
        assert state["state"] == "completed"
        assert snapshot_source(fixture) == before
        with (patch.object(single_shot, "EXAMPLE", root),
              patch.object(single_shot, "read_config", return_value=fixture[-1]),
              patch.object(run_one.subprocess, "run") as invoke,
              patch.object(sys, "argv", ["run_one.py", "--project", "example", "--tag", "same-sample",
                                       "--resume-tag", "original", "--compare-tag", "original"])):
            try:
                run_one.main()
            except SystemExit as exc:
                assert "SAME observation" in str(exc)
            else:
                raise AssertionError("Recovery treated as an independent observation")
            invoke.assert_not_called()
        with (patch.object(single_shot, "EXAMPLE", root),
              patch.object(single_shot, "read_config", return_value=fixture[-1]),
              patch.object(run_one.subprocess, "check_output", return_value=REVISION),
              patch.object(run_one.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as invoke,
              patch.object(sys, "argv", ["run_one.py", "--project", "example", "--tag", "failed-again",
                                       "--resume-tag", "original"])):
            assert run_one.main() == 7
            assert invoke.call_count == 1
        state = json.loads((fixture[0] / "pipeline-baseline-failed-again.status.json").read_text())
        assert state["state"] == "generation_failed" and state["resume_tag"] == "original"
        assert state["observation_tag"] == "original" and not state["independent_sample"]
        assert snapshot_source(fixture) == before
    print("PASS: run_one forwards linked recovery, scores afterward with no pipeline skips, preserves failed source status")


def main() -> int:
    run_api_transport_tests()
    run_repair_loop_tests()
    test_backend_protocol()
    test_score_selection()
    test_existing_run_is_preserved()
    test_internal_messages()
    test_recovery_loop()
    test_recovery_artifacts()
    test_recovery_rejections()
    test_failed_collector_recovery()
    test_legacy_multi_invocation_replay()
    test_run_one_recovery()
    backend = ChunkedBackend(per_round=3)
    files, transcript, usages, rounds = single_shot.generate(
        backend, "sys", "user", set(MODULES), max_rounds=6)

    ok = True

    if set(files) != set(MODULES):
        print(f"FAIL: expected {len(MODULES)} modules, got {sorted(files)}"); ok = False
    else:
        print(f"PASS: all {len(MODULES)} modules recovered across {rounds} rounds")

    if any("TRUNCATED" in f for f in files):
        print("FAIL: a half-written block was kept"); ok = False
    else:
        print("PASS: the truncated block was discarded, not spliced")

    if "def broken(:" in "".join(files.values()):
        print("FAIL: broken source leaked into a module"); ok = False
    else:
        print("PASS: no broken source in any module")

    if len(usages) != rounds:
        print(f"FAIL: {rounds} rounds but {len(usages)} usage records"); ok = False
    else:
        print(f"PASS: usage recorded per round ({len(usages)})")

    # A single-response backend must still work, and must not continue needlessly.
    one = ChunkedBackend(per_round=99)
    files2, _, _, rounds2 = single_shot.generate(one, "s", "u", set(MODULES), max_rounds=6)
    if rounds2 != 1 or set(files2) != set(MODULES):
        print(f"FAIL: single-response case took {rounds2} rounds, {len(files2)} files"); ok = False
    else:
        print("PASS: a response that fits uses exactly one round")

    print("\nOK" if ok else "\nFAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
