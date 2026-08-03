"""Tests for experiments/recodeagent/cli.py: the unified
``python -m experiments.recodeagent <stage> ...`` dispatcher. This module
defines no experiment arguments of its own -- it only decides which stage
module to import and forwards argv verbatim -- so these tests focus on
dispatch correctness (help text, unknown-stage errors, alias normalization,
argv forwarding, and return-code passthrough) rather than re-testing any
individual stage's own argparse surface (covered by that stage's own test
file).
"""
from __future__ import annotations

import importlib

import pytest

from experiments.recodeagent import cli as CLI


# --------------------------------------------------------------------------- #
# Internal consistency of the stage tables themselves
# --------------------------------------------------------------------------- #
def test_stage_modules_and_summaries_have_identical_keys():
    assert set(CLI._STAGE_MODULES) == set(CLI._STAGE_SUMMARIES)


def test_stage_modules_are_all_importable():
    for module_path in CLI._STAGE_MODULES.values():
        module = importlib.import_module(module_path)
        assert hasattr(module, "main")
        assert hasattr(module, "build_parser")


def test_stage_aliases_map_to_known_canonical_stage_names():
    for alias, canonical in CLI._STAGE_ALIASES.items():
        assert canonical in CLI._STAGE_MODULES
        assert alias not in CLI._STAGE_MODULES  # aliases must not shadow a canonical name


def test_expected_stages_present_in_expected_order():
    assert list(CLI._STAGE_MODULES) == [
        "acquire", "manifest", "prepare", "run", "collect", "merge-collections", "test-compare",
        "paper-test-compare", "merge-paper", "analyze", "report", "package",
    ]


# --------------------------------------------------------------------------- #
# _resolve_stage
# --------------------------------------------------------------------------- #
def test_resolve_stage_known_name():
    assert CLI._resolve_stage("acquire") == "acquire"


def test_resolve_stage_alias_normalizes_to_canonical():
    assert CLI._resolve_stage("test_compare") == "test-compare"


def test_resolve_stage_unknown_returns_none():
    assert CLI._resolve_stage("not-a-stage") is None


# --------------------------------------------------------------------------- #
# main(): help / no-args / unknown-stage paths
# --------------------------------------------------------------------------- #
def test_main_no_args_prints_help_and_returns_zero(capsys):
    rc = CLI.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ReCodeAgent-paper reproduction harness" in out
    assert "acquire" in out and "report" in out


def test_main_help_flag_prints_help_and_returns_zero(capsys):
    rc = CLI.main(["--help"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage: python -m experiments.recodeagent" in out


def test_main_short_help_flag_also_recognized(capsys):
    rc = CLI.main(["-h"])
    assert rc == 0
    assert "usage:" in capsys.readouterr().out


def test_main_lists_every_stage_in_help_text(capsys):
    CLI.main(["--help"])
    out = capsys.readouterr().out
    for stage in CLI._STAGE_MODULES:
        assert stage in out


def test_main_unknown_stage_returns_two_and_reports_valid_stages(capsys):
    rc = CLI.main(["bogus-stage"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown stage 'bogus-stage'" in err
    assert "acquire" in err


def test_main_reads_sys_argv_when_argv_is_none(monkeypatch, capsys):
    monkeypatch.setattr(CLI.sys, "argv", ["prog"])
    rc = CLI.main(None)
    assert rc == 0
    assert "usage:" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# main(): dispatch / forwarding / return-code passthrough
# --------------------------------------------------------------------------- #
def test_main_dispatches_to_stage_module_and_forwards_argv(monkeypatch):
    import experiments.recodeagent.acquire as acquire_mod

    captured: dict = {}

    def fake_main(argv):
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(acquire_mod, "main", fake_main)
    rc = CLI.main(["acquire", "--artifact-root", "X", "--extract"])
    assert rc == 0
    assert captured["argv"] == ["--artifact-root", "X", "--extract"]


def test_main_returns_stage_module_exit_code_verbatim(monkeypatch):
    import experiments.recodeagent.manifest as manifest_mod

    monkeypatch.setattr(manifest_mod, "main", lambda argv: 7)
    rc = CLI.main(["manifest"])
    assert rc == 7


def test_main_coerces_non_int_return_value_to_int(monkeypatch):
    import experiments.recodeagent.report as report_mod

    monkeypatch.setattr(report_mod, "main", lambda argv: False)   # falsy, non-int
    rc = CLI.main(["report"])
    assert rc == 0
    assert isinstance(rc, int)


def test_main_dispatches_via_hyphenated_alias(monkeypatch):
    import experiments.recodeagent.test_compare as tc_mod

    captured: dict = {}

    def fake_main(argv):
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(tc_mod, "main", fake_main)
    rc = CLI.main(["test-compare", "--embeddings"])
    assert rc == 0
    assert captured["argv"] == ["--embeddings"]


def test_main_dispatches_via_underscore_alias(monkeypatch):
    import experiments.recodeagent.test_compare as tc_mod

    captured: dict = {}

    def fake_main(argv):
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(tc_mod, "main", fake_main)
    rc = CLI.main(["test_compare", "--embeddings"])
    assert rc == 0
    assert captured["argv"] == ["--embeddings"]


def test_main_empty_forwarded_argv_when_stage_only():
    import experiments.recodeagent.run as run_mod

    captured: dict = {}

    def fake_main(argv):
        captured["argv"] = list(argv)
        return 0

    import experiments.recodeagent.cli as cli_mod
    orig = run_mod.main
    try:
        run_mod.main = fake_main
        rc = cli_mod.main(["run"])
        assert rc == 0
        assert captured["argv"] == []
    finally:
        run_mod.main = orig


@pytest.mark.parametrize("stage", list(CLI._STAGE_MODULES))
def test_every_stage_help_dispatch_exits_zero(stage, capsys):
    # Each stage's own argparse parser handles --help by calling
    # parser.exit(0), i.e. raising SystemExit(0) -- the same behavior as
    # running that stage's script directly. This is normal, expected CLI
    # behavior (not an error path), so we assert on the SystemExit code
    # rather than a plain return value.
    with pytest.raises(SystemExit) as exc_info:
        CLI.main([stage, "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "usage:" in out


# --------------------------------------------------------------------------- #
# __main__.py wiring
# --------------------------------------------------------------------------- #
def test_dunder_main_module_exposes_cli_main():
    dunder_main = importlib.import_module("experiments.recodeagent.__main__")
    assert dunder_main.main is CLI.main
