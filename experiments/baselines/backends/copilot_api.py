"""API-only B0 transport for a separately authenticated, user-run Copilot proxy.

One invocation sends exactly one chat completion request, optionally using SSE. There are
no CLI processes, model tools, retries, redirects, parameter fallbacks or hidden
client continuations. Raw private request/response artifacts must not be published.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from .base import Completion, Usage
from .copilot import checked_number, strict_json


DEFAULT_BASE_URL = "http://127.0.0.1:4141/v1"
TRANSPORT = "loopback-http-openai-chat-completions"
PROTOCOL = {
    "id": "b0-api-chat-completions-v1",
    "message_roles": "native system/user/assistant",
    "stream": False,
    "tools": "omitted; returned tool/function calls invalidate the request",
    "cli_invocations": 0,
    "implicit_cli_system_prompt": False,
    "client_auto_continuation": False,
    "proxy_auto_continuation": False,
    "continuation": "explicit harness requests for missing whole modules only",
    "upstream_requests_per_http_request": 1,
    "proxy_contract": "ericc-ch/copilot-api v0.7.0, 0ea08febdd7e3e055b03dd298bf57e669500b5c1",
    "proxy_version_verified_by_client": False,
    "provider_internal_prompts": "not observable; not claimed equivalent to CLI",
}


def loopback_base_url(value: str) -> str:
    """Use literal loopback addresses; canonicalize localhost without DNS."""
    if (not isinstance(value, str) or not value
            or any(ord(char) <= 32 or ord(char) == 127 for char in value)
            or any(char in value for char in "\\?#")):
        raise ValueError("API base URL must be a loopback /v1 URL without credentials, query or fragment")
    try:
        parts = urllib.parse.urlsplit(value)
        port = parts.port
        host = parts.hostname
        if (parts.scheme not in ("http", "https") or parts.username is not None
                or parts.password is not None or parts.path not in ("/v1", "/v1/")
                or not host or "%" in host):
            raise ValueError("Invalid API base URL")
        host = "127.0.0.1" if host.lower() == "localhost" else host
        address = ipaddress.ip_address(host)
        if not address.is_loopback or (port is not None and not 1 <= port <= 65535):
            raise ValueError("Not a loopback endpoint")
    except ValueError as exc:
        raise ValueError("API base URL requires http(s)://<literal-loopback-or-localhost>[:port]/v1") from exc
    authority = f"[{address}]" if address.version == 6 else str(address)
    if port is not None:
        authority += f":{port}"
    return f"{parts.scheme}://{authority}/v1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def filtered(value: object) -> bool:
    if isinstance(value, dict):
        return any((key in ("filtered", "blocked") and child is True) or filtered(child)
                   for key, child in value.items())
    return isinstance(value, list) and any(filtered(child) for child in value)


class CopilotAPIBackend:
    name = "copilot-api"

    def __init__(
        self, model: str, max_output_tokens: int, *,
        base_url: str | None = None, effort: str | None = None,
        token_limit_field: str = "max_tokens", temperature: float | None = None,
        timeout: float = 3600.0, audit_dir: str | Path | None = None,
        stream: bool = False,
    ):
        if not isinstance(model, str) or not model.strip() or model != model.strip():
            raise ValueError("API mode requires an explicit model ID from the proxy catalog")
        if type(max_output_tokens) is not int or max_output_tokens < 1:
            raise ValueError("API mode requires a positive explicit --max-output-tokens")
        if token_limit_field not in ("max_tokens", "max_completion_tokens"):
            raise ValueError("Unsupported API token limit field")
        if type(stream) is not bool:
            raise ValueError("API stream must be a boolean")
        if effort is not None and (not isinstance(effort, str) or not effort.strip()
                                   or effort != effort.strip()):
            raise ValueError("API reasoning effort must be an explicit nonempty value")
        for label, value in (("timeout", timeout), ("temperature", temperature)):
            if value is not None:
                checked_number(value, label)
        if timeout is None or timeout <= 0:
            raise ValueError("API timeout must be positive")
        self.model = model
        self.base_url = loopback_base_url(
            base_url if base_url is not None else os.environ.get("COPILOT_API_BASE_URL", DEFAULT_BASE_URL))
        self.endpoint = self.base_url + "/chat/completions"
        self.max_output_tokens = max_output_tokens
        self.token_limit_field = token_limit_field
        self.effort = effort
        self.temperature = temperature
        self.timeout = timeout
        self.stream = stream
        self.max_retries = 0
        self.audit_dir = Path(audit_dir) if audit_dir is not None else None
        self.audit_records: list[dict] = []
        self.calls = 0
        self._local_api_key = os.environ.get("COPILOT_API_KEY")
        if self._local_api_key is not None and (
            len(self._local_api_key) < 32
            or any(ord(char) <= 32 or ord(char) >= 127 for char in self._local_api_key)
        ):
            raise ValueError("COPILOT_API_KEY must be a nonempty local proxy key of at least 32 printable characters")
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def provenance(self) -> dict:
        config = {
            "base_url": self.base_url, "endpoint": self.endpoint, "model": self.model,
            self.token_limit_field: self.max_output_tokens,
            "timeout_s": self.timeout, "max_retries": 0, "redirects": "rejected",
            "environment_proxies": False,
            "authentication_to_loopback": "local-bearer-key" if self._local_api_key else "none",
        }
        if self.effort is not None:
            config["reasoning_effort"] = self.effort
        if self.temperature is not None:
            config["temperature"] = self.temperature
        config["stream"] = self.stream
        return {
            "transport": TRANSPORT, "api_configuration": config,
            "api_protocol": {**PROTOCOL, "stream": self.stream},
        }

    def request_payload(self, messages: list[dict]) -> dict:
        if not isinstance(messages, list) or not messages:
            raise ValueError("API messages must be a nonempty list")
        for index, message in enumerate(messages):
            if (not isinstance(message, dict) or set(message) != {"role", "content"}
                    or not isinstance(message["role"], str)
                    or message["role"] not in ("system", "user", "assistant")
                    or not isinstance(message["content"], str)
                    or (message["role"] == "system" and index != 0)):
                raise ValueError("API messages require text-only system/user/assistant roles and no tools")
        if messages[-1]["role"] != "user" or not messages[-1]["content"].strip():
            raise ValueError("API messages must end with a nonempty user request")
        payload = {
            "model": self.model, "messages": [dict(message) for message in messages],
            "stream": self.stream, self.token_limit_field: self.max_output_tokens,
        }
        if self.stream:
            payload["stream_options"] = {"include_usage": True}
        if self.effort is not None:
            payload["reasoning_effort"] = self.effort
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        return payload

    def complete(self, system: str, user: str) -> Completion:
        return self.complete_messages([
            {"role": "system", "content": system}, {"role": "user", "content": user},
        ])

    @staticmethod
    def _check_controls(container: dict) -> None:
        calls = container.get("tool_calls")
        if ((calls is not None and (not isinstance(calls, list) or bool(calls)))
                or container.get("function_call") is not None):
            raise ValueError("API protocol violation: returned tool/function call")
        if container.get("refusal") not in (None, ""):
            raise ValueError("API response contains a refusal")
        if any(filtered(container.get(key)) for key in ("content_filter_results", "prompt_filter_results")):
            raise ValueError("API response was content-filtered")

    def _decode(self, body: bytes, record: dict) -> Completion:
        response = strict_json(body)
        if not isinstance(response, dict):
            raise ValueError("API response must be a JSON object")
        # JSON exponents can overflow Python floats despite rejecting NaN literals.
        json.dumps(response, allow_nan=False)
        record["returned_model"] = response.get("model")
        record["token_usage"] = response.get("usage")
        choices = response.get("choices")
        if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
            record["finish_reason"] = choices[0].get("finish_reason")
        if "error" in response:
            raise ValueError("API returned an error object")
        if response.get("model") != self.model:
            raise ValueError(f"API returned model {response.get('model')!r}, requested {self.model!r}")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError("API response requires exactly one choice")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant" or "delta" in choice:
            raise ValueError("API response requires one non-streaming assistant message")
        for container in (response, choice, message):
            self._check_controls(container)
        finish = choice.get("finish_reason")
        if finish not in ("stop", "length"):
            raise ValueError(f"API response has missing/unsupported finish_reason: {finish!r}")
        text = message.get("content")
        if not isinstance(text, str) or (not text.strip() and finish != "length"):
            raise ValueError("API response has empty or non-text content")
        usage = Usage()
        raw_usage = response.get("usage")
        if raw_usage is not None:
            if not isinstance(raw_usage, dict):
                raise ValueError("API usage must be an object or null")
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if raw_usage.get(key) is not None:
                    setattr(usage, key, checked_number(raw_usage[key], f"usage.{key}", integer=True))
        return Completion(text, usage, response["model"], {
            "finish_reason": finish, "truncated": finish == "length",
            "assistant_messages": [text], "token_usage": raw_usage, "api_audit": record,
        })

    def _decode_stream(self, response, destination: Path, record: dict) -> Completion:
        content = []
        model = None
        response_id = None
        finish = None
        usage = None
        done = False
        event_count = 0

        def consume(data: str) -> None:
            nonlocal model, response_id, finish, usage, done, event_count
            if data.strip() == "[DONE]":
                done = True
                return
            chunk = strict_json(data.encode("utf-8"))
            if not isinstance(chunk, dict):
                raise ValueError("API stream event must be a JSON object")
            json.dumps(chunk, allow_nan=False)
            event_count += 1
            if "error" in chunk:
                raise ValueError("API stream returned an error object")
            self._check_controls(chunk)
            for key, previous in (("model", model), ("id", response_id)):
                value = chunk.get(key)
                if value is not None:
                    if not isinstance(value, str) or not value or (previous is not None and value != previous):
                        raise ValueError(f"API stream changed or invalidated {key}")
                    if key == "model":
                        model = value
                    else:
                        response_id = value
            if chunk.get("usage") is not None:
                usage = chunk["usage"]
            choices = chunk.get("choices")
            if not isinstance(choices, list) or len(choices) > 1:
                raise ValueError("API stream requires a single choice")
            if not choices:
                return
            choice = choices[0]
            if not isinstance(choice, dict) or type(choice.get("index")) is not int or choice["index"] != 0:
                raise ValueError("API stream choice index must be zero")
            self._check_controls(choice)
            delta = choice.get("delta")
            if not isinstance(delta, dict) or delta.get("role") not in (None, "assistant"):
                raise ValueError("API stream requires assistant deltas")
            self._check_controls(delta)
            text = delta.get("content")
            if text is not None:
                if not isinstance(text, str) or (finish is not None and text):
                    raise ValueError("Invalid text or content after stream completion")
                content.append(text)
            reason = choice.get("finish_reason")
            if reason is not None:
                if finish is not None and reason != finish:
                    raise ValueError("API stream changed finish_reason")
                if reason not in ("stop", "length"):
                    raise ValueError(f"Unsupported stream finish_reason: {reason!r}")
                finish = reason

        data_lines = []
        with destination.open("xb") as raw:
            for line in response:
                raw.write(line)
                raw.flush()
                decoded = line.decode("utf-8").rstrip("\r\n")
                if not decoded:
                    if data_lines:
                        consume("\n".join(data_lines))
                        data_lines.clear()
                        if done:
                            break
                elif decoded.startswith("data:"):
                    data_lines.append(decoded[5:].removeprefix(" "))
            if not done and data_lines:
                consume("\n".join(data_lines))
        if not done or finish is None:
            raise ValueError("API stream ended without [DONE] and a finish_reason")
        record["sse_events"] = event_count
        body = {
            "id": response_id, "model": model, "usage": usage,
            "choices": [{
                "index": 0, "message": {"role": "assistant", "content": "".join(content)},
                "finish_reason": finish,
            }],
        }
        return self._decode(json.dumps(body, allow_nan=False).encode("utf-8"), record)

    def complete_messages(self, messages: list[dict]) -> Completion:
        payload = self.request_payload(messages)
        if self.audit_dir is None:
            raise ValueError("API invocations require a private audit_dir")
        self.audit_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = self.audit_dir / f"round-{self.calls + 1:02d}"
        directory.mkdir(mode=0o700, exist_ok=False)
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        (directory / "request.json").write_bytes(body)
        self.calls += 1
        record = {
            "round": self.calls, "valid": False, **self.provenance(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "requested_model": self.model, "returned_model": None, "finish_reason": None,
            "token_usage": None, "http_status": None, "http_requests": 0,
            "request_sha256": hashlib.sha256(body).hexdigest(), "response_sha256": None,
            "audit_path": f"api-audit/{directory.name}",
        }
        response_body = None
        t0 = time.monotonic()
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if self.stream else "application/json",
            }
            if self._local_api_key:
                headers["Authorization"] = f"Bearer {self._local_api_key}"
            request = urllib.request.Request(self.endpoint, data=body, method="POST", headers=headers)
            record["http_requests"] = 1
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    record["http_status"] = response.status
                    if self.stream and response.status == 200:
                        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                        if content_type != "text/event-stream":
                            response_body = response.read()
                            raise ValueError("Streaming API response was not text/event-stream")
                        result = self._decode_stream(response, directory / "response.sse", record)
                    else:
                        response_body = b""
                        try:
                            response_body = response.read()
                        except http.client.IncompleteRead as exc:
                            response_body = exc.partial
                            raise
            except urllib.error.HTTPError as exc:
                record["http_status"] = exc.code
                with exc:
                    response_body = exc.read()
                raise
            if record["http_status"] != 200:
                raise ValueError(f"Unexpected API HTTP status: {record['http_status']}")
            if not self.stream:
                result = self._decode(response_body, record)
            result.usage.wall_clock_s = time.monotonic() - t0
            record.update(valid=True, model_tool_calls=0, usage=result.usage.as_dict())
            return result
        except (OSError, ValueError, http.client.HTTPException) as exc:
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            record["wall_clock_s"] = time.monotonic() - t0
            record["finished_at"] = datetime.now(timezone.utc).isoformat()
            if response_body is not None:
                (directory / "response.json").write_bytes(response_body)
                record["response_sha256"] = hashlib.sha256(response_body).hexdigest()
            elif (directory / "response.sse").exists():
                with (directory / "response.sse").open("rb") as raw:
                    record["response_sha256"] = hashlib.file_digest(raw, "sha256").hexdigest()
            self.audit_records.append(record)
            (directory / "audit.json").write_text(
                json.dumps(record, indent=2, allow_nan=False), encoding="utf-8")
