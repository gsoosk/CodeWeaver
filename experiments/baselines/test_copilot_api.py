"""Offline coverage for the API transport; invoked by test_continuation.py."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

from backends.copilot_api import CopilotAPIBackend, NoRedirect, loopback_base_url
import run_one
import single_shot


MODEL = "test-api-model"
KEY = "test-only-local-proxy-key-00000000000000000000"


class Response:
    def __init__(self, body, *, stream=False, status=200):
        self.body = body
        self.status = status
        self.headers = {"Content-Type": "text/event-stream" if stream else "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body

    def __iter__(self):
        return iter(self.body.splitlines(keepends=True))


def reply(text="complete", finish="stop"):
    return {
        "model": MODEL,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                     "finish_reason": finish}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }


def sse(text="complete", finish="stop", *, done=True):
    midpoint = len(text) // 2
    chunks = [
        {"id": "test-response", "model": MODEL, "choices": [{
            "index": 0, "delta": {"role": "assistant", "content": text[:midpoint]},
            "finish_reason": None,
        }]},
        {"id": "test-response", "model": MODEL, "choices": [{
            "index": 0, "delta": {"content": text[midpoint:]}, "finish_reason": finish,
        }]},
        {"model": MODEL, "choices": [], "usage": reply()["usage"]},
    ]
    return (
        "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
        + ("data: [DONE]\n\n" if done else "")
    ).encode("utf-8")


def backend(root, *, stream=False):
    result = CopilotAPIBackend(
        MODEL, 64000, effort="medium", stream=stream,
        audit_dir=root, base_url="http://localhost:4141/v1",
    )
    result._opener = Mock(spec=["open"])
    return result


def reject(action, message):
    try:
        action()
    except (ValueError, OSError) as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected rejection containing {message}")


def check_payload_and_audits(root):
    client = backend(root / "json")
    client._opener.open.return_value = Response(json.dumps(reply()).encode())
    result = client.complete("system", "user")
    request = client._opener.open.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["messages"] == [{"role": "system", "content": "system"}, {"role": "user", "content": "user"}]
    assert payload["max_tokens"] == 64000 and payload["reasoning_effort"] == "medium"
    assert payload["stream"] is False and "tools" not in payload and "functions" not in payload
    assert "temperature" not in payload and request.get_header("Authorization") == "Bearer " + KEY
    assert request.full_url == "http://127.0.0.1:4141/v1/chat/completions"
    assert result.usage.prompt_tokens == 11 and result.usage.completion_tokens == 7
    assert result.usage.nano_aiu is None and result.usage.premium_requests is None
    client._opener.open.assert_called_once()
    for path in (root / "json").rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()
    assert KEY not in json.dumps(client.provenance())
    client.complete_messages([
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
        {"role": "assistant", "content": "previous output"},
        {"role": "user", "content": "remaining files"},
    ])
    assert (root / "json" / "round-02" / "audit.json").exists()
    reject(lambda: client.request_payload([{"role": "tool", "content": "result"}]), "no tools")
    print("PASS: API native roles, explicit limits/effort, token usage, immutable audits and credential redaction")


def check_failures(root):
    cases = []
    changed = reply(); changed["model"] = "wrong-model"; cases.append((changed, "requested"))
    changed = reply(); changed["choices"].append(deepcopy(changed["choices"][0])); cases.append((changed, "exactly one"))
    changed = reply(); changed["choices"][0]["message"]["tool_calls"] = [{"id": "call"}]; cases.append((changed, "tool/function"))
    changed = reply(); changed["choices"][0]["message"]["function_call"] = {}; cases.append((changed, "tool/function"))
    changed = reply(); changed["choices"][0]["message"]["refusal"] = "no"; cases.append((changed, "refusal"))
    changed = reply(); changed["choices"][0]["finish_reason"] = "content_filter"; cases.append((changed, "finish_reason"))
    changed = reply(); changed["choices"][0].pop("finish_reason"); cases.append((changed, "finish_reason"))
    changed = reply(""); cases.append((changed, "empty"))
    changed = reply(); changed["usage"]["prompt_tokens"] = -1; cases.append((changed, "usage.prompt_tokens"))
    for index, (payload, message) in enumerate(cases):
        client = backend(root / f"invalid-{index}")
        client._opener.open.return_value = Response(json.dumps(payload).encode())
        reject(lambda: client.complete("s", "u"), message)
        client._opener.open.assert_called_once()
        audit = json.loads((client.audit_dir / "round-01" / "audit.json").read_text())
        assert audit["valid"] is False and audit["http_requests"] == 1
    client = backend(root / "malformed")
    client._opener.open.return_value = Response(b'{"broken":')
    reject(lambda: client.complete("s", "u"), "Expecting")
    client = backend(root / "http-error")
    client._opener.open.side_effect = urllib.error.HTTPError(
        client.endpoint, 429, "Too Many Requests", {}, io.BytesIO(b'{"error":"rate limited"}'),
    )
    reject(lambda: client.complete("s", "u"), "429")
    client._opener.open.assert_called_once()
    audit = json.loads((client.audit_dir / "round-01" / "audit.json").read_text())
    assert audit["http_status"] == 429 and audit["valid"] is False
    assert (client.audit_dir / "round-01" / "response.json").read_bytes() == b'{"error":"rate limited"}'
    client = backend(root / "network-error")
    client._opener.open.side_effect = urllib.error.URLError("connection refused")
    reject(lambda: client.complete("s", "u"), "connection refused")
    client._opener.open.assert_called_once()
    print("PASS: malformed/tool/refusal/model/HTTP/network errors fail closed without retry")


def check_streaming(root):
    module_a = "src/main/pkg/A.py"
    module_b = "src/main/pkg/B.py"
    first = f"{{{{{module_a}}}}}\n```python\nvalue = 1\n```\n{{{{{module_b}}}}}\n```python\npartial"
    second = f"{{{{{module_b}}}}}\n```python\nvalue = 2\n```"
    client = backend(root / "stream", stream=True)
    client._opener.open.side_effect = [Response(sse(first, "length"), stream=True),
                                     Response(sse(second), stream=True)]
    files, _, usage, rounds = single_shot.generate(client, "s", "u", {module_a, module_b}, 2)
    assert rounds == 2 and set(files) == {module_a, module_b}
    assert files[module_b].strip() == "value = 2" and len(usage) == 2
    requests = [json.loads(call.args[0].data) for call in client._opener.open.call_args_list]
    assert all(request["stream"] is True and request["stream_options"]["include_usage"] for request in requests)
    assert module_b in requests[1]["messages"][-1]["content"]
    assert "partial" not in requests[1]["messages"][-2]["content"]
    assert (client.audit_dir / "round-01" / "response.sse").read_bytes() == sse(first, "length")
    assert client.audit_records[0]["finish_reason"] == "length"
    assert client.audit_records[0]["usage"]["total_tokens"] == 18
    broken = backend(root / "broken-stream", stream=True)
    broken._opener.open.return_value = Response(sse(done=False), stream=True)
    reject(lambda: broken.complete("s", "u"), "[DONE]")
    assert (broken.audit_dir / "round-01" / "response.sse").exists()
    malicious = backend(root / "tool-stream", stream=True)
    chunk = {"model": MODEL, "choices": [{"index": 0, "delta": {"tool_calls": [{"id": "call"}]},
                                        "finish_reason": None}]}
    malicious._opener.open.return_value = Response(
        ("data: " + json.dumps(chunk) + "\n\n").encode(), stream=True,
    )
    reject(lambda: malicious.complete("s", "u"), "tool/function")
    empty = backend(root / "length-only", stream=True)
    empty._opener.open.return_value = Response(sse("", "length"), stream=True)
    result = empty.complete("s", "u")
    assert result.text == "" and result.raw["truncated"] is True
    print("PASS: SSE is one request/message, usage is preserved, truncated files never splice across requests")


def check_configuration():
    for url in (
        "https://example.com/v1", "http://localhost.evil/v1", "http://127.1/v1",
        "http://user:password@127.0.0.1/v1", "http://127.0.0.1/v1?key=secret",
        "http://127.0.0.1/v1#fragment", "http://127.0.0.1\\@example.com/v1",
        "http://127.0.0.1/v1\n",
    ):
        reject(lambda: loopback_base_url(url), "API base URL")
    assert loopback_base_url("http://localhost:4141/v1/") == "http://127.0.0.1:4141/v1"
    assert loopback_base_url("http://[::1]:4141/v1") == "http://[::1]:4141/v1"
    with patch.dict(os.environ, {"HTTP_PROXY": "http://untrusted.invalid:8080"}):
        client = CopilotAPIBackend(MODEL, 1)
        assert any(isinstance(handler, NoRedirect) for handler in client._opener.handlers)
        assert all(not handler.proxies for handler in client._opener.handlers
                   if isinstance(handler, urllib.request.ProxyHandler))
    assert NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://example.com") is None
    reject(lambda: CopilotAPIBackend(MODEL, 0), "positive")
    reject(lambda: CopilotAPIBackend(None, 1), "explicit model")
    print("PASS: loopback-only URLs, no environment proxies, no redirects, and explicit API configuration")


def check_api_worker(root):
    example = root / "worker"
    subject = example / "subjects" / "example"
    subject.mkdir(parents=True)
    run = subject / "pipeline-baseline-api-test"
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0] == sys.executable:
            assert "--backend" in command and command[command.index("--backend") + 1] == "copilot-api"
            assert "--api-stream" in command and "--context" not in command and "--effort" not in command
            assert command[command.index("--max-output-tokens") + 1] == "64000"
            source = run / "project" / "src" / "main"
            source.mkdir(parents=True)
            (source / "Module.py").write_text("value = 1\n")
            metadata = {
                "complete": True, "observation_tag": "api-test", "independent_sample": True,
                "recovery": None, "backend_invocations": 1, "new_backend_invocations": 1,
                "observed_model_calls": None, "observed_assistant_turns": 1,
                "api_audit": [{"valid": True, "http_requests": 1}],
                "returned_models": [MODEL], "explicit_http_model_requests": 1,
            }
            (run / "metadata.json").write_text(json.dumps(metadata))
            return subprocess.CompletedProcess(command, 0)
        assert command[0] == "bash" and "--no-pipeline-skips" in command
        return subprocess.CompletedProcess(command, 0, stdout="[oracle] result : 1 passed\n[oracle] exitcode : 0\n")

    def fake_check_output(command, **kwargs):
        assert command[0] == "git", "API worker must not invoke Copilot CLI"
        return "0" * 40

    argv = [
        "run_one.py", "--project", "example", "--tag", "api-test", "--backend", "copilot-api",
        "--model", MODEL, "--max-output-tokens", "64000", "--api-stream",
    ]
    with (
        patch.object(single_shot, "EXAMPLE", example),
        patch.object(single_shot, "read_config", return_value={"model": "cli-model", "effort": "medium"}),
        patch.object(sys, "argv", argv),
        patch("run_one.subprocess.run", side_effect=fake_run),
        patch("run_one.subprocess.check_output", side_effect=fake_check_output),
    ):
        assert run_one.main() == 0
    evidence = json.loads((run / "run_evidence.json").read_text())
    assert len(calls) == 2 and "copilot_version" not in evidence and "copilot_audit" not in evidence
    assert evidence["effort"] is None and evidence["explicit_http_model_requests"] == 1
    assert KEY not in json.dumps(evidence)
    print("PASS: API worker uses no Copilot CLI, does not inherit CLI effort/context, and scores afterward")


def run_tests():
    with tempfile.TemporaryDirectory(prefix="offline_api_b0_") as temporary:
        root = Path(temporary)
        with patch.dict(os.environ, {"COPILOT_API_KEY": KEY, "COPILOT_API_BASE_URL": "http://127.0.0.1:4141/v1"}):
            check_payload_and_audits(root)
            check_failures(root)
            check_streaming(root)
            check_configuration()
            check_api_worker(root)


def test_api_transport():
    run_tests()


if __name__ == "__main__":
    run_tests()
