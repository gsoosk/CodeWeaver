#!/usr/bin/env python3
"""Offline test of the block-aware continuation loop. No API, no cost.

Simulates a backend whose output cap forces the generation across several responses,
including the nasty case: a response that is cut off MID-FILE. Asserts that the loop
(a) discards the half-written block rather than splicing broken Python together,
(b) asks only for what is still missing, and (c) converges to every module.
"""
import pathlib
import sys
import json
import subprocess
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from backends.base import Completion, Usage  # noqa: E402
import single_shot  # noqa: E402
from backends.copilot import CopilotBackend  # noqa: E402
from run_one import parse_score, select_worst  # noqa: E402

MODULES = [f"src/main/pkg/Mod{i}.py" for i in range(1, 8)]


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
    with tempfile.TemporaryDirectory() as temporary:
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
    with tempfile.TemporaryDirectory() as temporary:
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


def main() -> int:
    test_backend_protocol()
    test_score_selection()
    test_existing_run_is_preserved()
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
