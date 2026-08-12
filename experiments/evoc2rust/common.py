"""Standard-library helpers shared by the EvoC2Rust harness."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PACKAGE_DIR / "subjects.json"

MEASURED = "measured"
INFERRED = "inferred"
MISSING = "missing"
UNAVAILABLE = "unavailable"
ERROR = "error"
NOT_APPLICABLE = "not_applicable"
SKIPPED = "skipped"
STATUSES = {
    MEASURED,
    INFERRED,
    MISSING,
    UNAVAILABLE,
    ERROR,
    NOT_APPLICABLE,
    SKIPPED,
}


def measurement(status: str, value: Any = None, reason: str = "") -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"unknown measurement status: {status}")
    if status not in {MEASURED, INFERRED} and value is not None:
        raise ValueError(f"{status} measurements cannot carry a value")
    return {"status": status, "value": value, "reason": reason}


def utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write_text(path: str | Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
    return path


def atomic_write_json(path: str | Path, value: Any) -> Path:
    return atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(root: str | Path) -> str:
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def flatten_measurement(
    row: dict[str, Any], prefix: str, value: dict[str, Any]
) -> None:
    row[prefix] = value.get("value")
    row[f"{prefix}_status"] = value.get("status")
    row[f"{prefix}_reason"] = value.get("reason", "")


def write_csv(
    path: str | Path,
    rows: Iterable[dict[str, Any]],
    fieldnames: list[str],
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def collect_provenance(*, artifact_root: Path | None = None) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "generated_at": utcnow_iso(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "harness_config_sha256": file_sha256(DEFAULT_CONFIG),
    }
    if artifact_root is not None:
        result = subprocess.run(
            ["git", "-C", str(artifact_root), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        provenance["artifact_git_commit"] = (
            result.stdout.strip() if result.returncode == 0 else None
        )
    return provenance

