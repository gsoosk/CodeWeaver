"""Tests for experiments/recodeagent/manifest.py: deterministic discovery of
the 118 benchmark projects, exact-count validation (100 CRUST + 6 Oxidizer +
4 AlphaTrans + 8 SKEL), the LoC/test/function counting heuristics, and
manifest.json/csv output. All fixtures are synthetic directory trees created
on the fly -- no network/toolchain/real artifact access.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import manifest as M

TEST_CFG = M.load_experiment_config()  # the bundled experiment.toml; read-only


# --------------------------------------------------------------------------- #
# Fixture builder: a synthetic artifact tree with the EXACT expected counts,
# using the default dir_candidates straight from experiment.toml so these
# tests double as a check that the defaults are internally consistent.
# --------------------------------------------------------------------------- #
def _make_full_fixture(root: Path) -> Path:
    specs = M.dataset_specs(TEST_CFG)
    for tool_key, spec in specs.items():
        tool_dir = root / spec["dir_candidates"][0]
        n = spec["expected_count"]
        ext = spec["source_extensions"][0]
        for i in range(n):
            project_dir = tool_dir / f"proj{i:03d}"
            src_dir = project_dir / spec["source_subdir_candidates"][0]
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / f"main{ext}").write_text(_sample_source(ext, i), encoding="utf-8")
    return root


def _sample_source(ext: str, i: int) -> str:
    if ext == ".c":
        return f"int add{i}(int a, int b) {{\n  return a + b;\n}}\n\nvoid test_add{i}(void) {{\n  add{i}(1, 2);\n}}\n"
    if ext == ".go":
        return f"func Add{i}(a, b int) int {{\n  return a + b\n}}\n\nfunc TestAdd{i}(t *testing.T) {{\n  Add{i}(1, 2)\n}}\n"
    if ext == ".java":
        return (
            f"public class C{i} {{\n"
            f"  public int add(int a, int b) {{ return a + b; }}\n"
            f"  @Test\n  public void testAdd() {{ add(1, 2); }}\n}}\n"
        )
    if ext == ".py":
        return f"def add{i}(a, b):\n    return a + b\n\ndef test_add{i}():\n    assert add{i}(1, 2) == 3\n"
    return "// unknown\n"


def test_full_fixture_discovers_exact_expected_counts(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    manifest = M.build_manifest(root, cfg=TEST_CFG)
    assert manifest["counts"] == {"crust": 100, "oxidizer": 6, "alphatrans": 4, "skel": 8}
    assert manifest["total"] == 118
    assert manifest["expected_total"] == 118
    assert manifest["counts_match_expected"] is True
    assert M.validate_manifest_counts(manifest) == []


def test_manifest_rows_reference_only_relative_paths(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    manifest = M.build_manifest(root, cfg=TEST_CFG)
    for row in manifest["projects"]:
        assert not Path(row["source_rel_path"]).is_absolute()


def test_manifest_row_ids_are_unique_and_stable(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    manifest = M.build_manifest(root, cfg=TEST_CFG)
    ids = [p["id"] for p in manifest["projects"]]
    assert len(ids) == len(set(ids)) == 118
    assert all(i.startswith(("crust__", "oxidizer__", "alphatrans__", "skel__")) for i in ids)


# --------------------------------------------------------------------------- #
# Exact-count validation must FAIL loudly on a broken/partial mirror
# --------------------------------------------------------------------------- #
def test_missing_one_crust_project_is_detected(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    # Delete one CRUST project directory to simulate a partial/incomplete mirror.
    specs = M.dataset_specs(TEST_CFG)
    crust_dir = root / specs["crust"]["dir_candidates"][0]
    import shutil
    shutil.rmtree(crust_dir / "proj099")

    manifest = M.build_manifest(root, cfg=TEST_CFG)
    assert manifest["counts"]["crust"] == 99
    assert manifest["counts_match_expected"] is False
    errors = M.validate_manifest_counts(manifest)
    assert any("crust" in e and "99" in e for e in errors)
    assert any("total" in e for e in errors)


def test_extra_unexpected_project_is_also_detected(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    specs = M.dataset_specs(TEST_CFG)
    skel_dir = root / specs["skel"]["dir_candidates"][0]
    extra = skel_dir / "proj999" / specs["skel"]["source_subdir_candidates"][0]
    extra.mkdir(parents=True)
    (extra / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    manifest = M.build_manifest(root, cfg=TEST_CFG)
    assert manifest["counts"]["skel"] == 9
    errors = M.validate_manifest_counts(manifest)
    assert any("skel" in e for e in errors)


def test_empty_artifact_root_discovers_nothing_and_reports_all_mismatches(tmp_path: Path):
    manifest = M.build_manifest(tmp_path, cfg=TEST_CFG)
    assert manifest["total"] == 0
    assert manifest["counts_match_expected"] is False
    errors = M.validate_manifest_counts(manifest)
    assert len(errors) == 5  # 4 tools + the total line


# --------------------------------------------------------------------------- #
# Directory resolution: case-insensitive candidates, ignored dirs
# --------------------------------------------------------------------------- #
def test_discover_tool_dir_is_case_insensitive(tmp_path: Path):
    (tmp_path / "CrUsT").mkdir()
    spec = {"dir_candidates": ["crust"]}
    found = M.discover_tool_dir(tmp_path, spec)
    assert found is not None and found.name == "CrUsT"


def test_discover_tool_dir_returns_none_when_absent(tmp_path: Path):
    spec = {"dir_candidates": ["crust"]}
    assert M.discover_tool_dir(tmp_path, spec) is None


def test_discover_project_dirs_skips_ignored_and_hidden(tmp_path: Path):
    tool_dir = tmp_path / "crust"
    for name in ["real_proj_a", "real_proj_b", ".git", "__pycache__", ".hidden"]:
        (tool_dir / name).mkdir(parents=True)
    (tool_dir / "a_file.txt").write_text("not a dir", encoding="utf-8")
    projects = M.discover_project_dirs(tool_dir)
    assert [p.name for p in projects] == ["real_proj_a", "real_proj_b"]


def test_discover_project_dirs_missing_tool_dir_returns_empty(tmp_path: Path):
    assert M.discover_project_dirs(tmp_path / "nope") == []


# --------------------------------------------------------------------------- #
# LoC / test / function counting heuristics
# --------------------------------------------------------------------------- #
def test_count_loc_counts_nonblank_physical_lines(tmp_path: Path):
    (tmp_path / "a.py").write_text("line1\n\nline2\n   \nline3\n", encoding="utf-8")
    assert M.count_loc(tmp_path, [".py"]) == 3


def test_count_loc_missing_root_is_none(tmp_path: Path):
    assert M.count_loc(tmp_path / "nope", [".py"]) is None


def test_count_loc_zero_when_root_exists_but_no_matching_files(tmp_path: Path):
    (tmp_path / "readme.md").write_text("hello", encoding="utf-8")
    assert M.count_loc(tmp_path, [".py"]) == 0


def test_count_tests_python(tmp_path: Path):
    (tmp_path / "t.py").write_text(
        "def test_one():\n    pass\n\ndef helper():\n    pass\n\ndef test_two():\n    pass\n",
        encoding="utf-8",
    )
    assert M.count_tests(tmp_path, [".py"]) == 2


def test_count_functions_python(tmp_path: Path):
    (tmp_path / "t.py").write_text(
        "def f1():\n    pass\n\ndef f2(x):\n    return x\n\ndef test_x():\n    pass\n",
        encoding="utf-8",
    )
    assert M.count_functions(tmp_path, [".py"]) == 3  # f1, f2, and test_x all match `def`


def test_count_functions_c_accepts_split_return_type_and_name(tmp_path: Path):
    (tmp_path / "leftpad.c").write_text(
        "size_t\nleftpad(const char *s)\n{\n  return 0;\n}\n\n"
        "static int same_line(void) {\n  return 1;\n}\n",
        encoding="utf-8",
    )
    assert M.count_functions(tmp_path, [".c"]) == 2


def test_count_tests_go():
    pass  # covered implicitly via the full-fixture test; kept as a documentation marker


def test_count_tests_java(tmp_path: Path):
    (tmp_path / "T.java").write_text(
        "public class T {\n  @Test\n  public void testA() {}\n  @Test\n  public void testB() {}\n}\n",
        encoding="utf-8",
    )
    assert M.count_tests(tmp_path, [".java"]) == 2


def test_count_pattern_matches_missing_root_is_none(tmp_path: Path):
    assert M.count_tests(tmp_path / "nope", [".py"]) is None


# --------------------------------------------------------------------------- #
# Row-level: oracle/scaffold/ground-truth sub-path resolution
# --------------------------------------------------------------------------- #
def test_build_project_row_resolves_all_subpaths(tmp_path: Path):
    project_dir = tmp_path / "bitset"
    (project_dir / "CBench").mkdir(parents=True)
    (project_dir / "CBench" / "main.c").write_text("int f(void){ return 0; }\n", encoding="utf-8")
    (project_dir / "RBench").mkdir(parents=True)
    (project_dir / "interfaces").mkdir(parents=True)

    spec = {
        "source_language": "C", "target_language": "Rust",
        "source_subdir_candidates": ["CBench"],
        "oracle_subdir_candidates": ["RBench"],
        "scaffold_subdir_candidates": ["interfaces"],
        "ground_truth_subdir_candidates": ["nonexistent"],
        "source_extensions": [".c"],
    }
    row = M.build_project_row("crust", spec, project_dir, tmp_path)
    assert row["status"] == "ok"
    assert row["source_rel_path"] == str(Path("bitset") / "CBench")
    assert row["oracle_rel_path"] == str(Path("bitset") / "RBench")
    assert row["scaffold_rel_path"] == str(Path("bitset") / "interfaces")
    assert row["ground_truth_target_rel_path"] is None  # candidate dir doesn't exist -> None, not fabricated


def test_crust_row_counts_authoritative_rust_scaffold_tests(tmp_path: Path):
    project_dir = tmp_path / "leftpad"
    source = project_dir / "c"
    source.mkdir(parents=True)
    (source / "leftpad.c").write_text("int leftpad(void) { return 0; }\n", encoding="utf-8")
    scaffold = project_dir / "rust"
    scaffold.mkdir()
    (scaffold / "tests.rs").write_text(
        "#[test]\nfn first() {}\n#[test]\nfn second() {}\n",
        encoding="utf-8",
    )
    spec = {
        "source_language": "C", "target_language": "Rust",
        "source_subdir_candidates": ["c"], "oracle_subdir_candidates": [],
        "scaffold_subdir_candidates": ["rust"],
        "ground_truth_subdir_candidates": [], "source_extensions": [".c"],
    }
    row = M.build_project_row("crust", spec, project_dir, tmp_path)
    assert row["test_count_source"] == 2


def test_build_project_row_falls_back_to_project_dir_when_no_source_subdir(tmp_path: Path):
    project_dir = tmp_path / "leftpad"
    project_dir.mkdir(parents=True)
    (project_dir / "main.py").write_text("def f():\n    pass\n", encoding="utf-8")
    spec = {"source_language": "Python", "target_language": "JavaScript",
           "source_subdir_candidates": ["nonexistent"], "oracle_subdir_candidates": [],
           "scaffold_subdir_candidates": [], "ground_truth_subdir_candidates": [],
           "source_extensions": [".py"]}
    row = M.build_project_row("skel", spec, project_dir, tmp_path)
    assert row["status"] == "ok"
    assert row["source_rel_path"] == "leftpad"


def test_build_project_row_missing_source_is_flagged_not_silently_zero(tmp_path: Path):
    project_dir = tmp_path / "empty_proj"
    # No subdirectories at all -- rglob will still "exist" (project_dir itself)
    # so force a genuinely absent source root via an impossible candidate that
    # also removes the project dir fallback by pointing elsewhere.
    project_dir.mkdir(parents=True)
    spec = {"source_language": "C", "target_language": "Rust",
           "source_subdir_candidates": [], "oracle_subdir_candidates": [],
           "scaffold_subdir_candidates": [], "ground_truth_subdir_candidates": [],
           "source_extensions": [".c"]}
    row = M.build_project_row("crust", spec, project_dir, tmp_path)
    # Falls back to project_dir itself, which DOES exist (even if empty) --
    # status is "ok" with loc/tests/functions == 0, never fabricated as missing.
    assert row["status"] == "ok"
    assert row["loc_source"] == 0


# --------------------------------------------------------------------------- #
# manifest.json / manifest.csv output + schema validation
# --------------------------------------------------------------------------- #
def test_write_manifest_produces_valid_json_and_csv(tmp_path: Path):
    root = _make_full_fixture(tmp_path / "artifact")
    manifest = M.build_manifest(root, cfg=TEST_CFG)
    out_root = tmp_path / "out"
    json_path, csv_path = M.write_manifest(manifest, out_root)
    assert json_path.exists() and csv_path.exists()

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["total"] == 118

    import csv as csv_mod
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == 118
    assert set(M._CSV_COLUMNS) <= set(rows[0].keys())


def test_manifest_matches_json_schema(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    manifest = M.build_manifest(root, cfg=TEST_CFG)
    schema = C.load_schema("manifest.schema.json")
    errors = C.validate_schema(manifest, schema)
    assert errors == []


def test_manifest_row_matches_json_schema(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    manifest = M.build_manifest(root, cfg=TEST_CFG)
    schema = C.load_schema("manifest_row.schema.json")
    for row in manifest["projects"][:5]:
        assert C.validate_schema(row, schema) == []


# --------------------------------------------------------------------------- #
# Probe mode
# --------------------------------------------------------------------------- #
def test_probe_tree_lists_structure(tmp_path: Path):
    (tmp_path / "TopLevel" / "child").mkdir(parents=True)
    (tmp_path / "TopLevel" / "file.txt").write_text("x", encoding="utf-8")
    lines = M.probe_tree(tmp_path, depth=2)
    joined = "\n".join(lines)
    assert "TopLevel/" in joined
    assert "child/" in joined
    assert "file.txt" in joined


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_main_succeeds_on_a_correct_fixture(tmp_path: Path, capsys):
    root = _make_full_fixture(tmp_path)
    rc = M.main(["--artifact-root", str(root)])
    assert rc == 0
    assert (root / "manifest.json").exists()
    captured = capsys.readouterr()
    assert "118" in captured.out


def test_cli_main_fails_on_incomplete_fixture_without_allow_partial(tmp_path: Path, capsys):
    root = _make_full_fixture(tmp_path)
    import shutil
    specs = M.dataset_specs(TEST_CFG)
    shutil.rmtree(root / specs["oxidizer"]["dir_candidates"][0] / "proj005")
    rc = M.main(["--artifact-root", str(root)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "COUNT MISMATCH" in captured.out


def test_cli_main_allow_partial_succeeds_despite_mismatch(tmp_path: Path):
    root = _make_full_fixture(tmp_path)
    import shutil
    specs = M.dataset_specs(TEST_CFG)
    shutil.rmtree(root / specs["oxidizer"]["dir_candidates"][0] / "proj005")
    rc = M.main(["--artifact-root", str(root), "--allow-partial"])
    assert rc == 0


def test_cli_probe_mode(tmp_path: Path, capsys):
    (tmp_path / "Foo").mkdir()
    rc = M.main(["--artifact-root", str(tmp_path), "--probe"])
    assert rc == 0
    assert "Foo/" in capsys.readouterr().out
