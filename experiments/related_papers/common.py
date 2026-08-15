"""Shared helpers for the related-paper reproduction campaign."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_text(path: str | Path, value: str) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=destination.parent,
    ) as handle:
        handle.write(value)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return destination


def atomic_write_json(path: str | Path, value: Any) -> Path:
    return atomic_write_text(
        path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    )


def read_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=destination.parent,
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return destination


def copytree_clean(source: Path, destination: Path, *, force: bool = False) -> None:
    if destination.exists():
        if not force:
            raise FileExistsError(destination)
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git", "target", "__pycache__", ".pytest_cache", "*.pyc"
        ),
    )


def run_command(
    argv: list[str],
    *,
    cwd: str | Path,
    timeout: float = 1200,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = utcnow_iso()
    try:
        completed = subprocess.run(
            argv,
            cwd=Path(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, **(env or {})},
        )
        return {
            "argv": argv,
            "cwd": str(cwd),
            "started_at": started,
            "ended_at": utcnow_iso(),
            "returncode": completed.returncode,
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "argv": argv,
            "cwd": str(cwd),
            "started_at": started,
            "ended_at": utcnow_iso(),
            "returncode": 124,
            "timed_out": True,
            "stdout": stdout,
            "stderr": stderr,
        }


def git_output(repository: Path, *args: str) -> str:
    result = run_command(["git", "-C", str(repository), *args], cwd=repository, timeout=120)
    if result["returncode"] != 0:
        diagnostic = (result["stdout"] + "\n" + result["stderr"])[-4000:]
        raise RuntimeError(f"git {' '.join(args)} failed in {repository}:\n{diagnostic}")
    return result["stdout"].strip()


def verify_git_commit(repository: Path, expected: str) -> None:
    actual = git_output(repository, "rev-parse", "HEAD")
    if actual != expected:
        raise ValueError(f"{repository}: expected commit {expected}, found {actual}")


def checksums(root: Path, *, output: Path) -> Path:
    entries: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() == output.resolve():
            continue
        entries.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    return atomic_write_text(output, "\n".join(entries) + "\n")
