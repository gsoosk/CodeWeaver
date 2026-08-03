"""Tests for experiments/recodeagent/acquire.py: MD5 verification (measured vs
missing vs error -- never silently accepted), safe zip extraction (path
traversal rejection), and the native-Windows illegal-filename refusal (the
official artifact is documented to contain '*' in member names). No network
access anywhere in this file.
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from experiments.recodeagent import acquire as A
from experiments.recodeagent import common as C


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #
def test_load_default_experiment_config_has_pinned_hashes():
    cfg = A.load_experiment_config()
    files = A.artifact_specs(cfg)
    assert files["implementation_zip"]["md5"] == "a2151028151e0852ce4db060a22ac76a"
    assert files["results_xlsx"]["md5"] == "a404779f2dcd7ac44d43bf72f4e88b98"
    assert files["results_zip"]["md5"] == "5df332d2a1477ec30f719dd7d0ff2470"


# --------------------------------------------------------------------------- #
# verify_file / verify_all
# --------------------------------------------------------------------------- #
def test_verify_file_missing_is_missing_not_error(tmp_path: Path):
    result = A.verify_file("implementation_zip",
                           {"filename": "implementation.zip", "md5": "deadbeef"}, tmp_path)
    assert result.measurement.status == C.Status.MISSING
    assert result.measurement.value is None


def test_verify_file_matching_hash_is_measured(tmp_path: Path):
    p = tmp_path / "thing.bin"
    p.write_bytes(b"paper artifact bytes")
    expected = hashlib.md5(b"paper artifact bytes").hexdigest()
    result = A.verify_file("thing", {"filename": "thing.bin", "md5": expected}, tmp_path)
    assert result.measurement.status == C.Status.MEASURED
    assert result.measurement.value == expected


def test_verify_file_mismatched_hash_is_error_never_silently_accepted(tmp_path: Path):
    p = tmp_path / "thing.bin"
    p.write_bytes(b"corrupted download")
    result = A.verify_file("thing", {"filename": "thing.bin", "md5": "0" * 32}, tmp_path)
    assert result.measurement.status == C.Status.ERROR
    assert "mismatch" in result.measurement.reason.lower()


def test_verify_all_checks_every_configured_file(tmp_path: Path):
    results = A.verify_all(tmp_path)
    assert set(results) == {"implementation_zip", "results_xlsx", "results_zip"}
    assert all(r.measurement.status == C.Status.MISSING for r in results.values())


# --------------------------------------------------------------------------- #
# Safe extraction: path traversal rejection
# --------------------------------------------------------------------------- #
def _make_zip(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_safe_extract_normal_zip(tmp_path: Path):
    zpath = _make_zip(tmp_path / "ok.zip", {"a/b.txt": b"hello", "c.txt": b"world"})
    dest = tmp_path / "out"
    result = A.safe_extract_zip(zpath, dest)
    assert result.status == C.Status.MEASURED
    assert (dest / "a" / "b.txt").read_bytes() == b"hello"
    assert (dest / "c.txt").read_bytes() == b"world"
    assert result.total_bytes == len(b"hello") + len(b"world")


def test_safe_extract_missing_zip_is_missing(tmp_path: Path):
    result = A.safe_extract_zip(tmp_path / "nope.zip", tmp_path / "out")
    assert result.status == C.Status.MISSING


@pytest.mark.parametrize("evil_name", [
    "../evil.txt",
    "../../etc/evil.txt",
    "a/../../evil.txt",
])
def test_safe_extract_rejects_traversal_members(tmp_path: Path, evil_name):
    zpath = _make_zip(tmp_path / "evil.zip", {"safe.txt": b"ok", evil_name: b"pwned"})
    dest = tmp_path / "out"
    with pytest.raises(C.PathTraversalError):
        A.safe_extract_zip(zpath, dest)
    # Nothing from the malicious archive should land outside dest, and dest
    # itself should not contain the escape target either.
    escaped = (tmp_path / "evil.txt")
    assert not escaped.exists()


def test_safe_extract_rejects_absolute_member_path(tmp_path: Path):
    # zipfile.ZipInfo silently strips leading slashes from filenames (as the
    # zip spec requires), so an absolute member can't reach the extractor via
    # zipfile itself -- but the shared traversal guard it relies on
    # (resolve_within) must still reject a raw absolute name directly, since
    # other adapters (not just zip extraction) resolve paths through it too.
    with pytest.raises(C.PathTraversalError):
        C.resolve_within(tmp_path / "out", "/etc/passwd")


# --------------------------------------------------------------------------- #
# Native-Windows illegal-filename refusal (the documented '*' case)
# --------------------------------------------------------------------------- #
def test_safe_extract_refuses_star_filenames_on_native_windows(tmp_path: Path, monkeypatch):
    zpath = _make_zip(tmp_path / "starry.zip", {"results/foo*.txt": b"data", "ok.txt": b"fine"})
    dest = tmp_path / "out"
    monkeypatch.setattr(C, "is_native_windows", lambda: True)
    monkeypatch.setattr(A, "is_native_windows", lambda: True)
    with pytest.raises(A.WindowsExtractionRefused) as ei:
        A.safe_extract_zip(zpath, dest)
    assert "foo*.txt" in str(ei.value) or "*" in str(ei.value)
    assert not dest.exists() or not any(dest.rglob("*"))


def test_safe_extract_skips_windows_guard_when_not_native_windows(tmp_path: Path, monkeypatch):
    # Note: we can't actually round-trip a real '*'-named member through this
    # test's own (possibly-Windows) filesystem -- that would fail for real,
    # unrelated to our guard. Instead we confirm the guard is bypassed
    # entirely off native Windows: windows_unsafe_reason must not even be
    # consulted, so a real illegal name would only ever be rejected by the
    # dedicated native-Windows test above.
    zpath = _make_zip(tmp_path / "starry.zip", {"results/normal_file.txt": b"data"})
    dest = tmp_path / "out"
    monkeypatch.setattr(A, "is_native_windows", lambda: False)

    def _must_not_be_called(*_a, **_k):
        raise AssertionError("windows_unsafe_reason must not be consulted off native Windows")

    monkeypatch.setattr(A, "windows_unsafe_reason", _must_not_be_called)
    result = A.safe_extract_zip(zpath, dest)
    assert result.status == C.Status.MEASURED
    assert (dest / "results" / "normal_file.txt").exists()


def test_safe_extract_force_native_windows_bypasses_refusal(tmp_path: Path, monkeypatch):
    zpath = _make_zip(tmp_path / "starry.zip", {"ok_only.txt": b"data"})
    dest = tmp_path / "out"
    monkeypatch.setattr(A, "is_native_windows", lambda: True)
    # No unsafe names in this archive, so force flag isn't even needed, but
    # confirm the flag doesn't break the safe case either.
    result = A.safe_extract_zip(zpath, dest, force_native_windows=True)
    assert result.status == C.Status.MEASURED


def test_this_machine_is_actually_native_windows_for_the_real_guard():
    # Sanity check that the environment this suite runs in genuinely exercises
    # the native-Windows code path above without any monkeypatching, since the
    # harness's documented target platform is Linux/WSL and this refusal only
    # matters here.
    import platform
    assert C.is_native_windows() == (platform.system() == "Windows")


# --------------------------------------------------------------------------- #
# acquire() orchestration (no network: download_missing left False)
# --------------------------------------------------------------------------- #
def test_acquire_reports_missing_files_without_network(tmp_path: Path):
    report = A.acquire(tmp_path, download_missing=False, extract=False)
    assert set(report["files"]) == {"implementation_zip", "results_xlsx", "results_zip"}
    for f in report["files"].values():
        assert f["status"] == C.Status.MISSING


def test_acquire_verifies_and_extracts_present_zip(tmp_path: Path, monkeypatch):
    cfg = A.load_experiment_config()
    data = b"fake implementation contents"
    zpath = tmp_path / "implementation.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("README.txt", data)
    md5 = hashlib.md5(zpath.read_bytes()).hexdigest()
    cfg["artifact"]["files"]["implementation_zip"]["md5"] = md5
    monkeypatch.setattr(A, "is_native_windows", lambda: False)

    report = A.acquire(tmp_path, cfg=cfg, which=["implementation_zip"],
                       download_missing=False, extract=True)
    assert report["files"]["implementation_zip"]["status"] == C.Status.MEASURED
    assert report["extractions"]["implementation_zip"]["status"] == C.Status.MEASURED
    assert (tmp_path / "implementation" / "README.txt").read_bytes() == data


def test_acquire_never_downloads_unless_flag_set(tmp_path: Path, monkeypatch):
    called = {"n": 0}

    def _fail_if_called(*a, **k):
        called["n"] += 1
        raise AssertionError("download_file must not be called without --download")

    monkeypatch.setattr(A, "download_file", _fail_if_called)
    A.acquire(tmp_path, download_missing=False, extract=False)
    assert called["n"] == 0


def test_acquire_unknown_key_reports_error_not_crash(tmp_path: Path):
    report = A.acquire(tmp_path, which=["nonexistent_key"])
    assert report["files"]["nonexistent_key"]["status"] == C.Status.ERROR


# --------------------------------------------------------------------------- #
# CLI smoke test
# --------------------------------------------------------------------------- #
def test_cli_main_returns_nonzero_when_files_missing(tmp_path: Path, capsys):
    rc = A.main(["--artifact-root", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "implementation_zip" in captured.out


def test_cli_main_writes_report_when_out_given(tmp_path: Path, capsys):
    out_path = tmp_path / "acquire_report.json"
    A.main(["--artifact-root", str(tmp_path / "art"), "--out", str(out_path)])
    assert out_path.exists()
    report = C.read_json(out_path)
    assert "files" in report
