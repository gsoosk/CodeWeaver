"""invoke_agent(): the boundary between the deterministic orchestrator and the
GitHub Copilot CLI agent runtime.

Every Burr action that needs LLM work shells out to `copilot -p ... --agent NAME`.
Copilot owns the entire agent loop (reasoning, tools, MCP, LSP, file edits); this
wrapper only launches it, captures structured JSONL output, and returns a result.
Inter-stage STATE is passed via files in the pipeline dir (see actions.py), not by
parsing agent chatter -- the parsed output is used only for success/failure
detection and logging.

Verified against GitHub Copilot CLI 1.0.7x (`copilot --help`):
  -p/--prompt, --agent, --model, --reasoning-effort {none,minimal,low,medium,
  high,xhigh,max}, --allow-all (= --allow-all-tools --allow-all-paths
  --allow-all-urls; required for non-interactive autonomy incl. web fetch),
  --no-ask-user, --output-format {text,json(JSONL)}, --add-dir, --log-dir, --share.
Custom agents are discovered from ~/.copilot/agents/ (user level);
ensure_agents_installed() mirrors <repo>/agents/*.agent.md there before each run.
"""
from __future__ import annotations

import json
import os
import platform
import signal
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

# When set, skip Copilot entirely and return a canned response so the Burr graph,
# transitions and crash-resume can be exercised offline. Checked at CALL time (see
# is_mock) so `--mock` works regardless of import order.
MOCK = os.environ.get("CODEWEAVER_MOCK") == "1"


def is_mock() -> bool:
    """Whether to use the offline mock agent -- evaluated dynamically so setting
    CODEWEAVER_MOCK after this module is imported (e.g. by `codeweaver run
    --mock`) still takes effect."""
    return MOCK or os.environ.get("CODEWEAVER_MOCK") == "1"

# Canonical agent profiles: <repo>/agents/ by default; override with
# CODEWEAVER_AGENTS_DIR. The CLI discovers custom agents from ~/.copilot/agents/,
# so we mirror them there before running.
AGENTS_SRC = Path(
    os.environ.get(
        "CODEWEAVER_AGENTS_DIR",
        str(Path(__file__).resolve().parent.parent / "agents"),
    )
)


def _resolve_effort(agent_name: str, explicit: str | None, cfg=None) -> str:
    """Precedence: explicit arg > CODEWEAVER_EFFORT env (global) > per-agent
    config default > "high"."""
    if explicit:
        return explicit
    env = os.environ.get("CODEWEAVER_EFFORT")
    if env:
        return env
    if cfg is not None:
        return cfg.model.effort_for(agent_name)
    return "high"


def _resolve_model(explicit: str | None, cfg=None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("CODEWEAVER_MODEL")
    if env:
        return env
    if cfg is not None:
        return cfg.model.default
    return "claude-opus-4.8"


def ensure_agents_installed() -> list[str]:
    """Copy agents/*.agent.md into the Copilot user-level agents dir so
    `--agent NAME` resolves. Idempotent; returns the installed profile names."""
    dest = Path(os.environ.get("COPILOT_HOME", Path.home() / ".copilot")) / "agents"
    dest.mkdir(parents=True, exist_ok=True)
    installed = []
    if AGENTS_SRC.exists():
        for src in sorted(AGENTS_SRC.glob("*.agent.md")):
            (dest / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            installed.append(src.stem.replace(".agent", ""))
    return installed


def _truncate(s: str, limit: int) -> str:
    s = s or ""
    return s if len(s) <= limit else s[:limit] + f"\n…[truncated {len(s) - limit} chars]"


def transcript_from_events(events: list, max_chars: int = 60000) -> str:
    """Render Copilot's JSONL events into a readable chat transcript for the UI."""
    lines: list[str] = []
    results: dict = {}
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "tool.execution_complete":
            d = ev.get("data", {}) or {}
            res = (d.get("result") or {}).get("content") or ""
            results[d.get("toolCallId")] = (bool(d.get("success")), res)

    for ev in events:
        if not isinstance(ev, dict):
            continue
        etype = ev.get("type")
        d = ev.get("data", {}) or {}
        if etype == "user.message":
            txt = d.get("content") or d.get("text") or ""
            if txt.strip():
                lines.append(f"### 👤 user\n{txt.strip()}")
        elif etype == "assistant.message":
            reasoning = (d.get("reasoningText") or "").strip()
            content = (d.get("content") or "").strip()
            if reasoning:
                lines.append(f"### 🤖 assistant (thinking)\n{reasoning}")
            if content:
                lines.append(f"### 🤖 assistant\n{content}")
            for tr in d.get("toolRequests") or []:
                name = tr.get("name", "tool")
                intent = tr.get("intentionSummary") or ""
                args = tr.get("arguments") or {}
                cmd = args.get("command") or args.get("prompt") or args.get("path") or ""
                head = f"  ↳ 🔧 {name}" + (f": {intent}" if intent else "")
                lines.append(head)
                if cmd:
                    lines.append(f"     $ {_truncate(str(cmd), 800)}")
                ok, res = results.get(tr.get("toolCallId"), (None, ""))
                if res:
                    tag = "ok" if ok else "ERR"
                    lines.append(f"     ⤷ ({tag}) {_truncate(str(res), 800)}")
        elif etype == "result":
            u = ev.get("usage", {}) or {}
            cc = u.get("codeChanges", {}) or {}
            fm = cc.get("filesModified") or []
            lines.append(
                f"### ✅ result  exit={ev.get('exitCode')}  "
                f"files_modified={len(fm)} (+{cc.get('linesAdded', 0)}/-{cc.get('linesRemoved', 0)})  "
                f"premium_requests={u.get('premiumRequests')}  "
                f"duration={round((u.get('sessionDurationMs') or 0) / 1000, 1)}s"
            )
            if fm:
                lines.append("  changed: " + ", ".join(map(str, fm[:50])))
    return _truncate("\n\n".join(lines), max_chars)


def summary_from_events(events: list) -> dict:
    """Structured summary of a run for UI attributes."""
    out = {"exit_code": None, "files_modified": [], "lines_added": 0,
           "lines_removed": 0, "premium_requests": None, "duration_s": None}
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "result":
            u = ev.get("usage", {}) or {}
            cc = u.get("codeChanges", {}) or {}
            out.update(
                exit_code=ev.get("exitCode"),
                files_modified=cc.get("filesModified") or [],
                lines_added=cc.get("linesAdded", 0),
                lines_removed=cc.get("linesRemoved", 0),
                premium_requests=u.get("premiumRequests"),
                duration_s=round((u.get("sessionDurationMs") or 0) / 1000, 1),
            )
    return out


def _git_bash_dirs() -> list[str]:
    """On Windows, prepend Git-for-Windows bin dirs so `bash tools/...` in agent
    shells resolves to Git Bash (which reads the Windows ~/.ssh/config) rather
    than a foreign WSL bash. Empty on non-Windows."""
    if platform.system() != "Windows":
        return []
    roots: list[Path] = []
    git = shutil.which("git")
    if git:
        roots.append(Path(git).resolve().parent.parent)
    roots.append(Path(r"C:\Program Files\Git"))
    roots.append(Path(r"C:\Program Files (x86)\Git"))
    dirs: list[str] = []
    for root in roots:
        for sub in ("bin", os.path.join("usr", "bin")):
            d = root / sub
            if (d / "bash.exe").exists() and str(d) not in dirs:
                dirs.append(str(d))
    return dirs


@dataclass
class AgentResult:
    agent: str
    ok: bool
    returncode: int
    final_text: str            # last assistant message (best-effort from JSONL)
    duration_s: float
    stdout_path: str | None = None
    events: list = field(default_factory=list)


def _mock(agent_name: str, prompt: str) -> AgentResult:
    from .mock import respond  # lazy: only needed offline
    text = respond(agent_name, prompt)
    return AgentResult(agent=agent_name, ok=True, returncode=0,
                       final_text=text, duration_s=0.0, events=[])


def _parse_jsonl(raw: str) -> tuple[list, str]:
    """Return (events, final_assistant_text) from Copilot's --output-format json."""
    events: list = []
    final = ""
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        events.append(obj)
        if not isinstance(obj, dict):
            continue
        etype = obj.get("type")
        data = obj.get("data") if isinstance(obj.get("data"), dict) else {}
        if etype == "assistant.message":
            content = data.get("content")
            if isinstance(content, str) and content.strip():
                final = content
        elif etype is None:
            for key in ("result", "text", "content", "message"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    final = val
    return events, final


def _transcript_log_path(
    log_dir: str | os.PathLike,
    agent_name: str,
    *,
    timestamp_ns: int | None = None,
    pid: int | None = None,
) -> Path:
    """Return a collision-resistant path so repeated agent calls are retained."""
    timestamp_ns = time.time_ns() if timestamp_ns is None else timestamp_ns
    pid = os.getpid() if pid is None else pid
    return Path(log_dir) / f"{agent_name}.{timestamp_ns}-{pid}.stdout.jsonl"


def _run_copilot_process(
    cmd: list[str],
    *,
    cwd: str,
    env: dict[str, str],
    timeout: float | None,
) -> tuple[int, str, str]:
    """Run Copilot and terminate its whole POSIX process group on timeout."""
    kwargs = {
        "cwd": cwd,
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name != "posix":
        proc = subprocess.run(cmd, timeout=timeout, **kwargs)
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    proc = subprocess.Popen(cmd, start_new_session=True, **kwargs)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout or "", stderr or ""
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(
            cmd,
            timeout,
            output=stdout,
            stderr=stderr,
        )


def invoke_agent(
    agent_name: str,
    prompt: str,
    *,
    cwd: str | os.PathLike,
    model: str | None = None,
    effort: str | None = None,
    add_dirs: list[str] | None = None,
    timeout: float | None = None,
    log_dir: str | os.PathLike | None = None,
    share_path: str | os.PathLike | None = None,
    extra_env: dict | None = None,
    cfg=None,
) -> AgentResult:
    """Run one Copilot custom agent non-interactively to completion."""
    if is_mock():
        return _mock(agent_name, prompt)

    if timeout is None:
        if cfg is not None and cfg.agent_timeout:
            timeout = float(cfg.agent_timeout)
        else:
            _env_to = os.environ.get("CODEWEAVER_AGENT_TIMEOUT", "").strip()
            if _env_to:
                try:
                    timeout = float(_env_to)
                except ValueError:
                    timeout = None

    ensure_agents_installed()
    model = _resolve_model(model, cfg)
    effort = _resolve_effort(agent_name, effort, cfg)
    cwd = str(cwd)
    cmd = [
        "copilot", "-p", prompt,
        "--agent", agent_name,
        "--model", model,
        "--reasoning-effort", effort,
        "--allow-all",
        "--no-ask-user",
        "--output-format", "json",
        "--no-color",
    ]
    for d in (add_dirs or []):
        cmd += ["--add-dir", str(d)]
    if log_dir:
        cmd += ["--log-dir", str(log_dir)]
    if share_path:
        cmd += ["--share", str(share_path)]

    env = dict(os.environ)
    # Auth precedence documented by the CLI: COPILOT_GITHUB_TOKEN > GH_TOKEN >
    # GITHUB_TOKEN. We do not inject a token; the caller's environment must have one.
    gb = _git_bash_dirs()
    if gb:
        env["PATH"] = os.pathsep.join(gb) + os.pathsep + env.get("PATH", "")
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})

    t0 = time.monotonic()
    try:
        returncode, stdout, stderr = _run_copilot_process(
            cmd,
            cwd=cwd,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        stdout = (e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
        stderr = (e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")) \
            + f"\n[codeweaver] agent '{agent_name}' timed out after {timeout}s"
        returncode = 124
    except OSError as e:
        stdout, stderr, returncode = "", f"[codeweaver] failed to launch copilot: {e!r}", 1
    dt = time.monotonic() - t0

    events, final = _parse_jsonl(stdout)
    if not final:
        final = (stdout or stderr or "").strip()

    stdout_path = None
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        stdout_path = str(_transcript_log_path(log_dir, agent_name))
        try:
            Path(stdout_path).write_text(stdout, encoding="utf-8")
        except OSError:
            stdout_path = None

    return AgentResult(
        agent=agent_name,
        ok=(returncode == 0),
        returncode=returncode,
        final_text=final,
        duration_s=dt,
        stdout_path=stdout_path,
        events=events,
    )


def verify_cli() -> dict:
    """Best-effort preflight: confirm the CLI exists and report its version."""
    try:
        out = subprocess.run(["copilot", "--version"], capture_output=True,
                             text=True, timeout=30)
        return {"ok": out.returncode == 0, "version": out.stdout.strip()}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "error": repr(e)}
