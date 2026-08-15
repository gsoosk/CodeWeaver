"""acquire.py -- verify + safely extract the official ReCodeAgent artifact.

The official artifact (Zenodo record 21399688) ships three files:

    implementation.zip   MD5 a2151028151e0852ce4db060a22ac76a
    results.xlsx          MD5 a404779f2dcd7ac44d43bf72f4e88b98
    results.zip           MD5 5df332d2a1477ec30f719dd7d0ff2470

fetched from ``https://zenodo.org/api/records/21399688/files/<name>/content``.

This module NEVER fabricates a "verified" status: a file is only ever reported
``measured`` after this process itself has hashed the bytes on disk and found
an exact MD5 match against ``experiment.toml`` (or an explicit override). A
missing file is ``missing``; a hash mismatch is ``error`` (never silently
accepted, never silently re-labeled as success).

Safety invariants (both independently tested, see tests/experiments/test_acquire.py):

  * Extraction rejects any archive member whose resolved path would escape the
    destination directory (zip-slip / absolute paths / drive letters / UNC).
  * The official artifact is documented to contain member names with ``*`` in
    them. Those are illegal in Windows file/directory names. On **native**
    Windows (not WSL, which reports as Linux), extraction refuses to run at
    all and prints exactly which member(s) are unsafe and why, instead of
    silently mangling or truncating names. Reproduction is expected to run
    under Linux/WSL, per the harness's stated target platform.

This module performs network access only when explicitly invoked with
``--download`` (never implicitly, and never from tests).
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent.common import (
    ExecResult,
    Measurement,
    PathTraversalError,
    Status,
    atomic_write_json,
    file_md5,
    is_native_windows,
    resolve_within,
    utcnow_iso,
    windows_unsafe_reason,
)


def load_experiment_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else C.DEFAULT_EXPERIMENT_CONFIG
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)


def artifact_specs(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    cfg = cfg if cfg is not None else load_experiment_config()
    files = cfg.get("artifact", {}).get("files", {})
    return files or C.OFFICIAL_ARTIFACT_FILES


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
@dataclass
class VerifyResult:
    key: str
    filename: str
    path: Path
    measurement: Measurement

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "filename": self.filename, "path": str(self.path),
                **self.measurement.to_dict()}


def verify_file(key: str, spec: dict[str, str], artifact_root: Path) -> VerifyResult:
    """Hash the on-disk file and compare against the pinned MD5. Never trusts
    a file's presence alone -- always re-hashes."""
    path = artifact_root / spec["filename"]
    expected = spec.get("md5", "")
    if not path.exists():
        return VerifyResult(key, spec["filename"], path,
                             Measurement.missing(f"{path} not found; run with --download or place it there"))
    try:
        actual = file_md5(path)
    except OSError as e:
        return VerifyResult(key, spec["filename"], path, Measurement.error(f"could not hash {path}: {e!r}"))
    if expected and actual != expected:
        return VerifyResult(
            key, spec["filename"], path,
            Measurement.error(f"MD5 mismatch: expected {expected}, got {actual} (corrupt/incomplete download?)"),
        )
    return VerifyResult(key, spec["filename"], path, Measurement.ok(actual))


def verify_all(artifact_root: Path, cfg: dict[str, Any] | None = None) -> dict[str, VerifyResult]:
    specs = artifact_specs(cfg)
    return {key: verify_file(key, spec, artifact_root) for key, spec in specs.items()}


# --------------------------------------------------------------------------- #
# Download (network access -- only ever invoked explicitly, never from tests)
# --------------------------------------------------------------------------- #
def download_file(url: str, dest: Path, *, timeout: float = 120.0) -> Measurement:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp, open(tmp, "wb") as out:  # noqa: S310
            shutil.copyfileobj(resp, out)
        tmp.replace(dest)
        return Measurement.ok(str(dest))
    except Exception as e:  # noqa: BLE001 - report, never crash the CLI
        tmp.unlink(missing_ok=True)
        return Measurement.error(f"download failed for {url}: {e!r}")


# --------------------------------------------------------------------------- #
# Safe extraction
# --------------------------------------------------------------------------- #
@dataclass
class ExtractionResult:
    zip_path: Path
    dest_dir: Path
    extracted: list[str] = field(default_factory=list)
    total_bytes: int = 0
    status: str = Status.MISSING
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "zip_path": str(self.zip_path), "dest_dir": str(self.dest_dir),
            "extracted_count": len(self.extracted), "total_bytes": self.total_bytes,
            "status": self.status, "reason": self.reason,
        }


class WindowsExtractionRefused(RuntimeError):
    """Raised when extraction is refused on native Windows because the
    archive contains member names that are illegal Windows filenames (this
    artifact is documented to contain '*' in some names)."""


def safe_extract_zip(zip_path: str | Path, dest_dir: str | Path, *,
                      force_native_windows: bool = False) -> ExtractionResult:
    """Extract ``zip_path`` into ``dest_dir``, rejecting any member that would
    escape ``dest_dir`` (zip-slip / absolute / drive-letter / UNC paths).

    On native Windows, refuses outright (raising :class:`WindowsExtractionRefused`)
    if any member name is illegal on Windows filesystems, unless
    ``force_native_windows=True`` is explicitly passed (for callers that have
    already worked around it, e.g. by renaming members -- not done by default,
    since silently renaming would make the workspace diverge from the
    official artifact without an explicit, auditable decision).
    """
    zip_path = Path(zip_path)
    dest_dir = Path(dest_dir)
    if not zip_path.exists():
        return ExtractionResult(zip_path, dest_dir, status=Status.MISSING,
                                 reason=f"{zip_path} not found")

    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]

        if is_native_windows() and not force_native_windows:
            unsafe = [(m.filename, windows_unsafe_reason(m.filename)) for m in members]
            unsafe = [(name, reason) for name, reason in unsafe if reason]
            if unsafe:
                sample = "; ".join(f"{n!r} ({r})" for n, r in unsafe[:5])
                more = f" (+{len(unsafe) - 5} more)" if len(unsafe) > 5 else ""
                raise WindowsExtractionRefused(
                    f"Refusing to extract {zip_path.name} on native Windows: "
                    f"{len(unsafe)} member name(s) are illegal on Windows filesystems: "
                    f"{sample}{more}. This artifact must be extracted under Linux/WSL "
                    f"(the harness's documented target platform); re-run acquire.py there, "
                    f"or point --artifact-root at an already-extracted Linux/WSL copy."
                )

        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted: list[str] = []
        total_bytes = 0
        for member in members:
            target = resolve_within(dest_dir, member.filename)  # raises PathTraversalError
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            extracted.append(member.filename)
            total_bytes += member.file_size

    return ExtractionResult(zip_path, dest_dir, extracted=extracted, total_bytes=total_bytes,
                             status=Status.MEASURED, reason="")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def acquire(
    artifact_root: Path,
    *,
    cfg: dict[str, Any] | None = None,
    which: list[str] | None = None,
    download_missing: bool = False,
    extract: bool = False,
    force_native_windows: bool = False,
) -> dict[str, Any]:
    cfg = cfg if cfg is not None else load_experiment_config()
    specs = artifact_specs(cfg)
    selected = which or list(specs)
    artifact_root = Path(artifact_root)
    artifact_root.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {"artifact_root": str(artifact_root), "generated_at": utcnow_iso(),
                              "files": {}, "extractions": {}}

    for key in selected:
        if key not in specs:
            report["files"][key] = Measurement.error(f"unknown artifact key {key!r}").to_dict()
            continue
        spec = specs[key]
        result = verify_file(key, spec, artifact_root)
        if result.measurement.status == Status.MISSING and download_missing:
            dl = download_file(spec["url"], result.path)
            if dl.is_measured:
                result = verify_file(key, spec, artifact_root)
        report["files"][key] = result.to_dict()

        if extract and result.measurement.is_measured and spec["filename"].endswith(".zip"):
            dest = artifact_root / Path(spec["filename"]).stem
            try:
                ext = safe_extract_zip(result.path, dest, force_native_windows=force_native_windows)
                report["extractions"][key] = ext.to_dict()
            except WindowsExtractionRefused as e:
                report["extractions"][key] = {"status": Status.ERROR, "reason": str(e)}
            except PathTraversalError as e:
                report["extractions"][key] = {"status": Status.ERROR, "reason": f"path traversal rejected: {e}"}

    return report


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="acquire.py",
        description="Verify (and optionally download/extract) the official ReCodeAgent artifact "
                    "(Zenodo record 21399688). Never fabricates a verified/extracted status.",
    )
    ap.add_argument("--artifact-root", required=True, help="directory holding/receiving the artifact files")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--which", default=None,
                    help="comma-separated subset of implementation_zip,results_xlsx,results_zip (default: all)")
    ap.add_argument("--download", action="store_true",
                    help="fetch missing files over the network (never done implicitly)")
    ap.add_argument("--extract", action="store_true", help="safely extract verified .zip files")
    ap.add_argument("--force-native-windows", action="store_true",
                    help="bypass the native-Windows illegal-filename refusal (NOT recommended; "
                         "the harness's target platform is Linux/WSL)")
    ap.add_argument("--out", default=None, help="write the JSON report here (default: stdout only)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_experiment_config(args.config)
    which = args.which.split(",") if args.which else None
    report = acquire(
        Path(args.artifact_root), cfg=cfg, which=which,
        download_missing=args.download, extract=args.extract,
        force_native_windows=args.force_native_windows,
    )
    if args.out:
        atomic_write_json(args.out, report)
    import json
    print(json.dumps(report, indent=2))
    ok = all(f.get("status") == Status.MEASURED for f in report["files"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
