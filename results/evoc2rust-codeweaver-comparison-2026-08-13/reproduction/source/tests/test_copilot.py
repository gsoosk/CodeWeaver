import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from codeweaver.copilot import (
    _run_copilot_process,
    _transcript_log_path,
    transcript_from_events,
)


def test_transcript_log_path_is_unique_per_invocation():
    first = _transcript_log_path("logs", "translator", timestamp_ns=100, pid=7)
    second = _transcript_log_path("logs", "translator", timestamp_ns=101, pid=7)

    assert first == Path("logs") / "translator.100-7.stdout.jsonl"
    assert second == Path("logs") / "translator.101-7.stdout.jsonl"
    assert first != second


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"command": "cargo test"}, "cargo test"),
        ('{"command":"cargo test"}', "cargo test"),
        ("cargo test", "cargo test"),
    ],
)
def test_transcript_accepts_dict_and_string_tool_arguments(arguments, expected):
    transcript = transcript_from_events([
        {
            "type": "assistant.message",
            "data": {
                "toolRequests": [{
                    "toolCallId": "call-1",
                    "name": "powershell",
                    "arguments": arguments,
                }],
            },
        },
    ])

    assert expected in transcript


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group semantics")
def test_copilot_timeout_kills_descendants(tmp_path: Path):
    pid_path = tmp_path / "child.pid"
    child = "import time; time.sleep(30)"
    parent = (
        "import pathlib,subprocess,sys,time; "
        f"p=subprocess.Popen([sys.executable,'-c',{child!r}]); "
        f"pathlib.Path({str(pid_path)!r}).write_text(str(p.pid)); "
        "time.sleep(30)"
    )
    started = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired):
        _run_copilot_process(
            [sys.executable, "-c", parent],
            cwd=str(tmp_path),
            env=dict(os.environ),
            timeout=0.3,
        )

    assert time.monotonic() - started < 3
    child_pid = int(pid_path.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and Path(f"/proc/{child_pid}").exists():
        time.sleep(0.02)
    assert not Path(f"/proc/{child_pid}").exists()
