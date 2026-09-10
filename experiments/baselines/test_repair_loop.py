"""Offline coverage for the repair loops; invoked by test_continuation.py."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from backends.base import Completion, Usage
import repair_loop
import single_shot


MODULE = "src/main/pkg/Mod.py"


def reject(action, message):
    try:
        action()
    except (ValueError, SystemExit) as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected rejection containing {message}")


def make_source(root, tag="src-tag"):
    subject = root / "subjects" / "example"
    run = subject / f"pipeline-baseline-{tag}"
    module = run / "project" / "src" / "main" / "pkg" / "Mod.py"
    module.parent.mkdir(parents=True)
    module.write_text("value = 'original'\n")
    (run / "metadata.json").write_text(json.dumps({"baseline": "B0-single-shot", "granularity": "per-file"}))
    return subject, run, module


def completion(text, *, truncated=False):
    return Completion(text, Usage(prompt_tokens=10, completion_tokens=5),
                      "test-model", {"finish_reason": "length" if truncated else "stop",
                                     "truncated": truncated, "assistant_messages": [text]})


def block(path, body):
    return f"{{{{{path}}}}}\n```python\n{body}\n```"


def run_repair(root, argv, signals, responses, oracle="[oracle] result : 1 passed\n[oracle] exitcode : 0\n"):
    """Drive the loop with scripted signals; returns (run_dir, backend)."""
    calls = {"signal": 0}

    def fake_signal(*args, **kwargs):
        index = min(calls["signal"], len(signals) - 1)
        calls["signal"] += 1
        return signals[index]

    class Backend:
        name = "copilot-api"
        audit_records = []

        def __init__(self):
            self.sent = []

        def provenance(self):
            return {"transport": "loopback-http-openai-chat-completions"}

        def complete(self, system, user):
            self.sent.append((system, user))
            reply = responses[len(self.sent) - 1]
            if isinstance(reply, Exception):
                raise reply
            self.audit_records.append({"http_requests": 1})
            return reply

    backend = Backend()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=oracle, stderr="")

    with (
        patch.object(single_shot, "EXAMPLE", root),
        patch.object(single_shot, "REPO", root),
        patch.object(single_shot, "build_backend", return_value=backend),
        patch.object(single_shot, "code_provenance", return_value={"code_revision": "0" * 40}),
        patch.object(repair_loop, "build_signal", side_effect=fake_signal),
        patch.object(repair_loop, "test_signal", side_effect=fake_signal),
        patch("repair_loop.subprocess.run", side_effect=fake_run),
        patch.object(sys, "argv", argv),
    ):
        code = repair_loop.main()
    return code, backend


def check_build_arm(root):
    subject, source, original = make_source(root)
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "rep-build", "--arm", "build", "--iterations", "3",
            "--model", "test-model", "--max-output-tokens", "1000"]
    signals = [
        (False, "IMPORT pkg.Mod:1: NameError: name 'CR' is not defined", {"modules_ok": 0, "modules_total": 1, "syntax_or_import_failures": 1}),
        (True, "build_check: 1/1 modules parse and import", {"modules_ok": 1, "modules_total": 1, "syntax_or_import_failures": 0}),
    ]
    code, backend = run_repair(root, argv, signals, [completion(block(MODULE, "value = 'repaired'"))])
    assert code == 0
    run = subject / "pipeline-baseline-rep-build"
    assert (run / "project/src/main/pkg/Mod.py").read_text().strip() == "value = 'repaired'"
    assert original.read_text().strip() == "value = 'original'", "source artifact must not be mutated"
    meta = json.loads((run / "metadata.json").read_text())
    assert meta["test_blind"] is True and meta["oracle_seen"] is False
    assert meta["iterations_run"] == 1 and meta["best_iteration_by_metric"] == 1
    sent_system, sent_user = backend.sent[0]
    assert "NameError" in sent_user and "value = 'original'" in sent_user
    assert "test" not in sent_system.lower().split("suite")[0][:40]
    assert (run / "iteration-01-signal.txt").exists() and (run / "iteration-00-signal.txt").exists()
    print("PASS: build arm repairs from parse/import diagnostics only and never mutates the source run")


def check_test_arm_labelling(root):
    subject, source, _ = make_source(root / "t")
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "rep-test", "--arm", "test", "--iterations", "1",
            "--model", "test-model", "--max-output-tokens", "1000"]
    failing = {"score": {"passed": 1, "failed": 3, "skipped": 0, "deselected": 0,
                         "errors": 0, "exit_code": 1, "summary": "3 failed, 1 passed"}}
    better = {"score": {"passed": 4, "failed": 0, "skipped": 0, "deselected": 0,
                        "errors": 0, "exit_code": 0, "summary": "4 passed"}}
    signals = [(False, "FAILED pkg/ModTest.py::test_a - AssertionError: 1 != 2", failing),
               (True, "4 passed", better)]
    code, backend = run_repair(root / "t", argv, signals, [completion(block(MODULE, "value = 'fixed'"))])
    assert code == 0
    meta = json.loads((subject / "pipeline-baseline-rep-test" / "metadata.json").read_text())
    assert meta["test_blind"] is False and meta["oracle_seen"] is True
    assert "NOT test-blind" in meta["protocol"]
    assert "AssertionError" in backend.sent[0][1]
    print("PASS: test arm is recorded as oracle-seen and not test-blind")


def check_guards(root):
    subject, source, _ = make_source(root / "g")
    outsider = "src/test/pkg/ModTest.py"
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "rep-guard", "--arm", "build", "--iterations", "2",
            "--model", "test-model", "--max-output-tokens", "1000"]
    stuck = (False, "IMPORT pkg.Mod:1: NameError", {"modules_ok": 0, "modules_total": 1, "syntax_or_import_failures": 1})
    response = completion(
        block(outsider, "assert False") + "\n\n"
        + block("src/main/pkg/New.py", "value = 1") + "\n\n"
        + block(MODULE, "def broken(:"))
    code, backend = run_repair(root / "g", argv, [stuck], [response])
    assert code == 0
    run = subject / "pipeline-baseline-rep-guard"
    project = run / "project"
    assert not (project / outsider).exists() and not (run / outsider).exists(), "must not write outside src/main"
    assert not (project / "src/main/pkg/New.py").exists(), "must not invent new modules"
    assert (project / "src/main/pkg/Mod.py").read_text().strip() == "value = 'original'"
    meta = json.loads((run / "metadata.json").read_text())
    rejected = {r["path"]: r["reason"] for r in meta["history"][1]["files_rejected"]}
    assert len(rejected) == 3 and any("does not parse" in r for r in rejected.values())
    assert len(backend.sent) == 1, "an iteration that changes nothing must stop the loop"
    print("PASS: repair cannot touch tests, invent modules, or apply unparseable source")


def check_reverts_regression(root):
    """A no-op iteration ends the loop without spending another call."""
    subject, source, _ = make_source(root / "r")
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "rep-noop", "--arm", "build", "--iterations", "3",
            "--model", "test-model", "--max-output-tokens", "1000"]
    stuck = (False, "IMPORT a", {"modules_ok": 0, "modules_total": 2, "syntax_or_import_failures": 2})
    responses = [completion("I could not determine a fix."), completion(block(MODULE, "value = 'x'"))]
    code, backend = run_repair(root / "r", argv, [stuck], responses)
    assert code == 0
    run = subject / "pipeline-baseline-rep-noop"
    assert len(backend.sent) == 1, "an iteration emitting nothing applicable must stop the loop"
    assert (run / "project/src/main/pkg/Mod.py").read_text().strip() == "value = 'original'"
    meta = json.loads((run / "metadata.json").read_text())
    assert meta["history"][1]["files_changed"] == []
    print("PASS: an iteration with nothing applicable stops the loop without another call")


def check_cascading_progress_is_not_discarded(root):
    """The regression that motivated this: a correct fix that reveals the next error.

    csv's real repair resolved all four NameErrors and immediately surfaced a
    TypeError, leaving modules_ok unchanged. An earlier version treated that as
    failure, reverted the fix and stopped after one call.
    """
    subject, source, _ = make_source(root / "c")
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "rep-cascade", "--arm", "build", "--iterations", "3",
            "--model", "test-model", "--max-output-tokens", "1000"]
    flat = {"modules_ok": 7, "modules_total": 11, "syntax_or_import_failures": 4}
    signals = [
        (False, "IMPORT pkg.Mod:1: NameError: name 'CR' is not defined", flat),
        (False, "IMPORT pkg.Mod:1: TypeError: 'str' object cannot be interpreted as an integer", dict(flat)),
        (True, "build_check: 11/11 modules parse and import",
         {"modules_ok": 11, "modules_total": 11, "syntax_or_import_failures": 0}),
    ]
    responses = [completion(block(MODULE, "value = 'names_fixed'")),
                 completion(block(MODULE, "value = 'types_fixed'"))]
    code, backend = run_repair(root / "c", argv, signals, responses)
    assert code == 0
    run = subject / "pipeline-baseline-rep-cascade"
    assert len(backend.sent) == 2, "a flat metric must not stop the loop after one call"
    assert (run / "project/src/main/pkg/Mod.py").read_text().strip() == "value = 'types_fixed'"
    meta = json.loads((run / "metadata.json").read_text())
    assert meta["iterations_run"] == 2
    assert meta["history"][1]["improved"] is False, "the flat iteration is recorded honestly"
    assert meta["history"][1]["files_changed"] == [MODULE], "but its change is kept"
    assert meta["history"][2]["clean"] is True
    assert "final iteration" in meta["kept"]
    print("PASS: a fix that reveals the next error is kept, and the loop runs its budget")


def check_regression_is_visible_not_hidden(root):
    subject, source, _ = make_source(root / "v")
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "rep-visible", "--arm", "build", "--iterations", "2",
            "--model", "test-model", "--max-output-tokens", "1000"]
    signals = [
        (False, "IMPORT a", {"modules_ok": 5, "modules_total": 10, "syntax_or_import_failures": 5}),
        (False, "IMPORT b", {"modules_ok": 2, "modules_total": 10, "syntax_or_import_failures": 8}),
        (False, "IMPORT c", {"modules_ok": 1, "modules_total": 10, "syntax_or_import_failures": 9}),
    ]
    responses = [completion(block(MODULE, "value = 'worse'")),
                 completion(block(MODULE, "value = 'worst'"))]
    code, backend = run_repair(root / "v", argv, signals, responses)
    assert code == 0
    run = subject / "pipeline-baseline-rep-visible"
    meta = json.loads((run / "metadata.json").read_text())
    assert (run / "project/src/main/pkg/Mod.py").read_text().strip() == "value = 'worst'"
    assert meta["best_iteration_by_metric"] == 0
    assert [h["improved"] for h in meta["history"][1:]] == [False, False]
    print("PASS: a regressing final state is reported as-is, not replaced by a better intermediate")


def check_error_recovery_counts_as_progress():
    errored = {"score": {"passed": 20, "failed": 2, "errors": 5}}
    running = {"score": {"passed": 8, "failed": 40, "errors": 0}}
    assert repair_loop.better("test", running, errored) is True
    assert repair_loop.better("test", errored, running) is False
    assert repair_loop.better("test", {"score": None}, running) is False
    assert repair_loop.better("build", {"modules_ok": 3}, {"modules_ok": 3}) is False
    print("PASS: collection recovery counts as progress; a lower visible pass count does not mask it")

    # The crust build metric is a different shape: fewer rustc errors is better,
    # and a crate that compiles beats one that does not regardless of the count.
    broken = {"compile_errors": 145, "builds": False}
    fewer = {"compile_errors": 12, "builds": False}
    compiles = {"compile_errors": 0, "builds": True}
    assert repair_loop.better("build", fewer, broken) is True
    assert repair_loop.better("build", broken, fewer) is False
    assert repair_loop.better("build", compiles, fewer) is True
    assert repair_loop.better("build", fewer, compiles) is False
    assert repair_loop.better("build", broken, broken) is False
    # A metric of one shape must never be read with the other's keys.
    assert repair_loop.better("build", compiles, None) is True
    print("PASS: crust build metric ranks by compile errors and prefers a crate that builds")


def check_refuses_overwrite(root):
    subject, source, _ = make_source(root / "o")
    (subject / "pipeline-baseline-taken").mkdir()
    argv = ["repair_loop.py", "--project", "example", "--source-tag", "src-tag",
            "--tag", "taken", "--arm", "build", "--iterations", "1",
            "--model", "test-model", "--max-output-tokens", "1000"]
    with patch.object(single_shot, "EXAMPLE", root / "o"), patch.object(sys, "argv", argv):
        reject(repair_loop.main, "refusing to overwrite")
    argv[argv.index("--source-tag") + 1] = "missing"
    with patch.object(single_shot, "EXAMPLE", root / "o"), patch.object(sys, "argv", argv):
        reject(repair_loop.main, "No source artifact")
    print("PASS: existing tags and missing source artifacts are refused before any model call")


def check_diagnostic_digest():
    noisy = "\n".join(["irrelevant"] * 50 + ["FAILED pkg/T.py::test_x - AssertionError: 1 != 2"])
    digest = repair_loop.failure_digest(noisy)
    assert "FAILED" in digest and "irrelevant" not in digest
    huge = "\n".join(f"FAILED case_{i}" for i in range(20000))
    bounded = repair_loop.failure_digest(huge)
    assert len(bounded) <= repair_loop.MAX_DIAGNOSTIC_CHARS + 200
    assert "characters omitted" in bounded and "FAILED case_0" in bounded
    print("PASS: diagnostics keep actionable lines and stay bounded without hiding truncation")


def run_tests():
    with tempfile.TemporaryDirectory(prefix="offline_repair_") as temporary:
        root = Path(temporary)
        check_build_arm(root)
        check_test_arm_labelling(root)
        check_guards(root)
        check_reverts_regression(root)
        check_cascading_progress_is_not_discarded(root)
        check_regression_is_visible_not_hidden(root)
        check_error_recovery_counts_as_progress()
        check_refuses_overwrite(root)
        check_diagnostic_digest()


if __name__ == "__main__":
    run_tests()
