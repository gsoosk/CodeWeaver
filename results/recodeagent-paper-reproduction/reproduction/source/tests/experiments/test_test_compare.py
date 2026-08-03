"""Tests for experiments/recodeagent/test_compare.py: per-language test
discovery + assertion extraction (regex-heuristic, adapter-based), literal
type inference, name-similarity mapping, optional embedding similarity
(injected fakes only -- never the real sentence-transformers/network path),
per-test comparison row assembly, aggregate RQ2 summary rates, per-run/matrix
orchestration (missing-vs-zero semantics mirroring collect.py), and output
writers/CLI. No network, LLM, or toolchain access anywhere in this file --
everything runs against synthetic fixtures created on the fly.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import run as R
from experiments.recodeagent import test_compare as TC
from experiments.recodeagent.common import Measurement, Status


# --------------------------------------------------------------------------- #
# Per-language assertion extraction (direct, classification-focused)
# --------------------------------------------------------------------------- #
def test_assertions_c_equal_true_false():
    body = "void test_x(void) { assert(r == 5); assert(is_ready()); assert(!is_broken()); }"
    out = TC._assertions_c(body)
    assert [a.kind for a in out] == ["equal", "true", "false"]
    assert out[0].expected_repr == "5"


def test_assertions_c_handles_nested_call_before_equality():
    body = "void test_x(void) { assert(compute(1, 2) == 5); }"
    out = TC._assertions_c(body)
    assert out == [TC.Assertion(kind="equal", expected_repr="5")]


def test_assertions_go_equal_true_false_other():
    body = (
        "func TestX(t *testing.T) {\n"
        "  assert.Equal(t, 5, r)\n"
        "  assert.True(t, ok)\n"
        "  assert.False(t, bad)\n"
        "  t.Errorf(\"boom\")\n"
        "}\n"
    )
    out = TC._assertions_go(body)
    assert [a.kind for a in out] == ["equal", "true", "false", "other"]
    assert out[0].expected_repr == "5"   # testify: assert.Equal(t, expected, actual)


def test_assertions_java_equal_true_false_other():
    body = (
        "@Test public void testX() {\n"
        "  assertEquals(5, r);\n"
        "  assertTrue(ok);\n"
        "  assertFalse(bad);\n"
        "  assertNotNull(obj);\n"
        "}\n"
    )
    out = TC._assertions_java(body)
    assert [a.kind for a in out] == ["equal", "true", "false", "other"]
    assert out[0].expected_repr == "5"   # JUnit: assertEquals(expected, actual)


def test_assertions_python_unittest_and_bare():
    body = (
        "def test_x(self):\n"
        "    self.assertEqual(result, 3)\n"
        "    self.assertTrue(ok)\n"
        "    self.assertFalse(bad)\n"
        "    self.assertRaises(ValueError)\n"
        "    assert other == 9\n"
        "    assert flag_only\n"
    )
    out = TC._assertions_python(body)
    assert [a.kind for a in out] == ["equal", "true", "false", "other", "equal", "true"]
    assert out[0].expected_repr == "3"
    assert out[4].expected_repr == "9"


def test_assertions_rust_equal_true_false_other():
    body = (
        "fn test_x() {\n"
        "  assert_eq!(r, 5);\n"
        "  assert!(ok);\n"
        "  assert!(!bad);\n"
        "  assert_ne!(a, b);\n"
        "}\n"
    )
    out = TC._assertions_rust(body)
    assert [a.kind for a in out] == ["equal", "true", "false", "other"]
    assert out[0].expected_repr == "5"


def test_assertions_js_equal_true_false_other_and_nested_receiver():
    body = (
        "test('x', () => {\n"
        "  expect(r).toBe(5);\n"
        "  expect(isReady()).toBeTruthy();\n"
        "  expect(isBroken(1, 2)).toBeFalsy();\n"
        "  expect(x).toContain(1);\n"
        "});\n"
    )
    out = TC._assertions_js(body)
    assert [a.kind for a in out] == ["equal", "true", "false", "other"]
    assert out[0].expected_repr == "5"


# --------------------------------------------------------------------------- #
# infer_literal
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,expected", [
    ("true", ("bool", True)),
    ("True", ("bool", True)),
    ("false", ("bool", False)),
    ('"hello"', ("string", "hello")),
    ("'hello'", ("string", "hello")),
    ("42", ("int", 42)),
    ("-3", ("int", -3)),
    ("3.14", ("float", 3.14)),
    ("some_var", (None, None)),
    (None, (None, None)),
])
def test_infer_literal(text, expected):
    assert TC.infer_literal(text) == expected


# --------------------------------------------------------------------------- #
# parse_tests: chunk boundaries, method-invocation counts, LoC
# --------------------------------------------------------------------------- #
def test_parse_tests_c_two_functions_chunk_correctly():
    src = (
        "void test_a(void) {\n"
        "    int r = add(2, 3);\n"
        "    assert(r == 5);\n"
        "}\n\n"
        "void test_b(void) {\n"
        "    assert(is_ready());\n"
        "}\n"
    )
    tests = TC.parse_tests(src, "t.c", "C")
    assert [t.name for t in tests] == ["test_a", "test_b"]
    assert tests[0].method_invocation_count == 1   # add(...) only; assert() itself excluded
    assert tests[0].assertions[0].expected_repr == "5"
    assert "test_b" not in tests[0].body   # chunking did not leak the next test into this one


def test_parse_tests_unknown_language_returns_empty():
    assert TC.parse_tests("whatever", "f.rb", "Ruby") == []


def test_parse_tests_language_lookup_is_case_insensitive():
    src = "void test_a(void) { assert(1 == 1); }\n"
    assert len(TC.parse_tests(src, "t.c", "c")) == 1
    assert len(TC.parse_tests(src, "t.c", "  C  ")) == 1


def test_parse_tests_python_excludes_test_own_name_from_invocation_count():
    src = "def test_a(self):\n    self.assertEqual(test_a, 1)\n"
    tests = TC.parse_tests(src, "t.py", "Python")
    assert tests[0].method_invocation_count == 0


def test_parse_tests_js_uses_description_string_as_name():
    src = "it('does the thing', () => { expect(1).toBe(1); });\n"
    tests = TC.parse_tests(src, "t.js", "JavaScript")
    assert tests[0].name == "does the thing"


def test_parse_tests_rust_multiple_tests_and_loc():
    src = (
        "#[test]\n"
        "fn test_a() {\n"
        "    let r = add(2, 3);\n"
        "    assert_eq!(r, 5);\n"
        "}\n\n"
        "#[test]\n"
        "fn test_b() {\n"
        "    assert!(true);\n"
        "}\n"
    )
    tests = TC.parse_tests(src, "t.rs", "Rust")
    assert [t.name for t in tests] == ["test_a", "test_b"]
    # body chunk includes the leading "#[test]" attribute line through the
    # closing brace: "#[test]", "fn test_a() {", "let r = ...", "assert_eq!(...)", "}" = 5 non-blank lines.
    assert tests[0].loc == 5
    assert tests[0].method_invocation_count == 1   # add(...) only; assert_eq! is excluded


# --------------------------------------------------------------------------- #
# find_test_files / parse_tests_in_tree (real filesystem fixtures)
# --------------------------------------------------------------------------- #
def test_find_test_files_only_matches_files_with_recognizable_tests(tmp_path: Path):
    (tmp_path / "lib.c").write_text("int add(int a, int b) { return a + b; }\n", encoding="utf-8")
    (tmp_path / "test_lib.c").write_text("void test_add(void) { assert(add(1, 2) == 3); }\n", encoding="utf-8")
    hits = TC.find_test_files(tmp_path, [".c"], "C")
    assert [p.name for p in hits] == ["test_lib.c"]


def test_parse_tests_in_tree_missing_root_returns_empty(tmp_path: Path):
    assert TC.parse_tests_in_tree(tmp_path / "nope", [".c"], "C") == []


def test_parse_tests_in_tree_aggregates_across_files(tmp_path: Path):
    (tmp_path / "a_test.py").write_text("def test_a(self):\n    self.assertTrue(1)\n", encoding="utf-8")
    (tmp_path / "b_test.py").write_text("def test_b(self):\n    self.assertTrue(1)\n", encoding="utf-8")
    tests = TC.parse_tests_in_tree(tmp_path, [".py"], "Python")
    assert sorted(t.name for t in tests) == ["test_a", "test_b"]


# --------------------------------------------------------------------------- #
# name_similarity / map_tests / unmapped_target_indices
# --------------------------------------------------------------------------- #
def test_name_similarity_exact_after_normalization():
    assert TC.name_similarity("test_add_numbers", "testAddNumbers") == pytest.approx(1.0)


def test_name_similarity_unrelated_names_score_low():
    assert TC.name_similarity("test_add", "test_totally_unrelated_thing_here") < 0.5


def _pt(name: str) -> TC.ParsedTest:
    return TC.ParsedTest(name=name, file="f", body="")


def test_map_tests_one_to_one_perfect_match():
    src = [_pt("test_add"), _pt("test_subtract")]
    tgt = [_pt("test_subtract"), _pt("test_add")]
    mapping = TC.map_tests(src, tgt)
    assert mapping[0] == {"target_index": 1, "score": pytest.approx(1.0), "mapped": True}
    assert mapping[1] == {"target_index": 0, "score": pytest.approx(1.0), "mapped": True}


def test_map_tests_below_threshold_is_not_mapped():
    src = [_pt("test_add")]
    tgt = [_pt("test_zzz_completely_different_xyz")]
    mapping = TC.map_tests(src, tgt)
    assert mapping[0]["mapped"] is False
    assert mapping[0]["target_index"] is None


def test_map_tests_greedy_prefers_higher_score_and_is_one_to_one():
    # Both source tests are similar to "test_add_two", but "test_add" is a
    # near-exact match for it and must claim it; "test_add_numbers" should
    # NOT also grab the same target.
    src = [_pt("test_add"), _pt("test_add_numbers")]
    tgt = [_pt("test_add")]
    mapping = TC.map_tests(src, tgt)
    assert mapping[0]["mapped"] is True and mapping[0]["target_index"] == 0
    assert mapping[1]["mapped"] is False


def test_map_tests_empty_lists():
    assert TC.map_tests([], []) == []
    assert TC.map_tests([_pt("test_a")], []) == [{"target_index": None, "score": None, "mapped": False}]


def test_unmapped_target_indices():
    src = [_pt("test_add")]
    tgt = [_pt("test_add"), _pt("test_generated_extra")]
    mapping = TC.map_tests(src, tgt)
    assert TC.unmapped_target_indices(tgt, mapping) == [1]


# --------------------------------------------------------------------------- #
# compute_embedding_similarity -- injected fakes only, never the real package
# --------------------------------------------------------------------------- #
def test_compute_embedding_similarity_unavailable_when_not_installed(monkeypatch):
    monkeypatch.setattr(TC.C, "optional_import", lambda name: None)
    m = TC.compute_embedding_similarity("a", "b")
    assert m.status == Status.UNAVAILABLE
    assert "not installed" in m.reason


def test_compute_embedding_similarity_measured_with_fake_model(monkeypatch):
    class FakeModel:
        def encode(self, texts):
            # Identical vectors for identical text -> cosine 1.0; deterministic fixture.
            return [[1.0, 0.0], [1.0, 0.0]] if texts[0] == texts[1] else [[1.0, 0.0], [0.0, 1.0]]

    class FakeModule:
        @staticmethod
        def SentenceTransformer(name):
            return FakeModel()

    monkeypatch.setattr(TC.C, "optional_import", lambda name: FakeModule())
    TC._EMBEDDING_MODEL_CACHE.clear()
    m = TC.compute_embedding_similarity("same text", "same text")
    assert m.status == Status.MEASURED
    assert m.value == pytest.approx(1.0)
    m2 = TC.compute_embedding_similarity("a", "b")
    assert m2.value == pytest.approx(0.0)


def test_compute_embedding_similarity_error_when_encode_raises(monkeypatch):
    class FakeModel:
        def encode(self, texts):
            raise RuntimeError("model not cached locally")

    class FakeModule:
        @staticmethod
        def SentenceTransformer(name):
            return FakeModel()

    monkeypatch.setattr(TC.C, "optional_import", lambda name: FakeModule())
    TC._EMBEDDING_MODEL_CACHE.clear()
    m = TC.compute_embedding_similarity("a", "b")
    assert m.status == Status.ERROR
    assert "model not cached" in m.reason


# --------------------------------------------------------------------------- #
# _build_row / build_comparison_rows
# --------------------------------------------------------------------------- #
def _parsed(name, *, assertions=None, loc=1, invocations=0, body="") -> TC.ParsedTest:
    return TC.ParsedTest(name=name, file="f", body=body, assertions=assertions or [],
                        method_invocation_count=invocations, loc=loc)


def test_build_row_mapped_translated_test_full_metrics():
    source = _parsed("test_add", assertions=[TC.Assertion(kind="equal", expected_repr="5")], loc=3, invocations=1)
    target = _parsed("test_add", assertions=[TC.Assertion(kind="equal", expected_repr="5")], loc=4, invocations=2)
    row = TC._build_row(source, target, {"mapped": True, "score": 1.0}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=None, test_origin="translated")
    assert row["mapping_status"] == Status.MEASURED
    assert row["test_origin"] == "translated"
    assert row["assertion_count_match"] is True
    assert row["assert_equal_expected_value_equivalent"] is True
    assert row["assert_equal_value_type"] == "int"
    assert row["assertion_type_match"] is True
    assert row["embedding_status"] == Status.UNAVAILABLE   # no embedding_fn configured


def test_build_row_missing_when_source_has_no_mapped_target():
    source = _parsed("test_add")
    row = TC._build_row(source, None, {"mapped": False, "score": None}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=None, test_origin=None)
    assert row["mapping_status"] == Status.MISSING
    assert row["translated_test_name"] is None
    assert row["assertion_count_translated"] is None
    assert row["assertion_count_match"] is None
    assert row["embedding_status"] == Status.UNAVAILABLE


def test_build_row_generated_when_target_has_no_source():
    target = _parsed("test_extra_edge_case")
    row = TC._build_row(None, target, {"mapped": False, "score": None}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=None, test_origin="generated")
    assert row["mapping_status"] == Status.NOT_APPLICABLE
    assert row["source_test_name"] is None
    assert row["test_origin"] == "generated"
    assert row["translated_test_name"] == "test_extra_edge_case"


def test_build_row_assertion_count_mismatch_detected():
    source = _parsed("test_x", assertions=[TC.Assertion(kind="true")])
    target = _parsed("test_x", assertions=[TC.Assertion(kind="true"), TC.Assertion(kind="equal", expected_repr="1")])
    row = TC._build_row(source, target, {"mapped": True, "score": 1.0}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=None, test_origin="translated")
    assert row["assertion_count_source"] == 1
    assert row["assertion_count_translated"] == 2
    assert row["assertion_count_match"] is False


def test_build_row_assert_equal_type_mismatch_is_not_equivalent():
    source = _parsed("test_x", assertions=[TC.Assertion(kind="equal", expected_repr="5")])
    target = _parsed("test_x", assertions=[TC.Assertion(kind="equal", expected_repr='"5"')])
    row = TC._build_row(source, target, {"mapped": True, "score": 1.0}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=None, test_origin="translated")
    assert row["assert_equal_expected_value_equivalent"] is False
    assert row["assert_equal_value_type"] is None   # types differ (int vs string) -> undetermined type


def test_build_row_assert_equal_undetermined_when_expression_not_literal():
    source = _parsed("test_x", assertions=[TC.Assertion(kind="equal", expected_repr="some_variable")])
    target = _parsed("test_x", assertions=[TC.Assertion(kind="equal", expected_repr="5")])
    row = TC._build_row(source, target, {"mapped": True, "score": 1.0}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=None, test_origin="translated")
    assert row["assert_equal_expected_value_equivalent"] is None
    assert row["assert_equal_expected_value_source"] == "some_variable"   # raw text preserved, not fabricated


def test_build_row_embedding_wired_via_injected_function():
    source = _parsed("test_x", body="source body")
    target = _parsed("test_x", body="target body")
    calls = []

    def fake_embed(a, b):
        calls.append((a, b))
        return Measurement.ok(0.87)

    row = TC._build_row(source, target, {"mapped": True, "score": 1.0}, project_id="p", tool="crust",
                       variant="full", repetition=0, embedding_fn=fake_embed, test_origin="translated")
    assert row["embedding_status"] == Status.MEASURED
    assert row["embedding_cosine_similarity"] == pytest.approx(0.87)
    assert calls == [("source body", "target body")]


def test_build_comparison_rows_includes_generated_tests_separately():
    source_tests = [_parsed("test_add")]
    target_tests = [_parsed("test_add"), _parsed("test_extra_generated")]
    rows = TC.build_comparison_rows(source_tests, target_tests, project_id="p", tool="crust")
    assert len(rows) == 2
    origins = {r["source_test_name"] or r["translated_test_name"]: r["test_origin"] for r in rows}
    assert origins["test_add"] == "translated"
    assert origins["test_extra_generated"] == "generated"


# --------------------------------------------------------------------------- #
# summarize_comparisons
# --------------------------------------------------------------------------- #
def test_summarize_comparisons_rates_and_denominators():
    rows = [
        {"test_origin": "translated", "mapped": True, "assertion_count_match": True,
         "assert_equal_expected_value_equivalent": True, "assertion_type_match": True,
         "embedding_status": Status.MEASURED, "embedding_cosine_similarity": 0.9},
        {"test_origin": "translated", "mapped": True, "assertion_count_match": False,
         "assert_equal_expected_value_equivalent": None, "assertion_type_match": None,
         "embedding_status": Status.UNAVAILABLE, "embedding_cosine_similarity": None},
        {"test_origin": None, "mapped": False, "assertion_count_match": None,
         "assert_equal_expected_value_equivalent": None, "assertion_type_match": None,
         "embedding_status": Status.UNAVAILABLE, "embedding_cosine_similarity": None},
        {"test_origin": "generated", "mapped": False, "assertion_count_match": None,
         "assert_equal_expected_value_equivalent": None, "assertion_type_match": None,
         "embedding_status": Status.UNAVAILABLE, "embedding_cosine_similarity": None},
    ]
    summary = TC.summarize_comparisons(rows)
    assert summary["total_source_tests"] == 3          # excludes the 1 generated row
    assert summary["total_mapped_tests"] == 2
    assert summary["total_generated_tests"] == 1
    assert summary["translation_rate"] == pytest.approx(2 / 3)
    assert summary["assertion_count_match_rate"] == pytest.approx(0.5)
    assert summary["assertion_count_match_denominator"] == 2
    assert summary["assert_equal_equivalence_rate"] == pytest.approx(1.0)
    assert summary["assert_equal_equivalence_denominator"] == 1
    assert summary["assertion_type_match_rate"] == pytest.approx(1.0)
    assert summary["embedding_similarity_status"] == Status.MEASURED
    assert summary["embedding_similarity_mean"] == pytest.approx(0.9)
    assert summary["embedding_similarity_count"] == 1


def test_summarize_comparisons_all_unavailable_embeddings():
    rows = [{"test_origin": "translated", "mapped": True, "assertion_count_match": None,
            "assert_equal_expected_value_equivalent": None, "assertion_type_match": None,
            "embedding_status": Status.UNAVAILABLE, "embedding_cosine_similarity": None}]
    summary = TC.summarize_comparisons(rows)
    assert summary["embedding_similarity_status"] == Status.UNAVAILABLE
    assert summary["embedding_similarity_mean"] is None


def test_summarize_comparisons_empty_rows_never_divides_by_zero():
    summary = TC.summarize_comparisons([])
    assert summary["translation_rate"] is None
    assert summary["total_source_tests"] == 0


# --------------------------------------------------------------------------- #
# compare_run: per-run orchestration over a fixture run directory
# --------------------------------------------------------------------------- #
CRUST_SPEC = {"source_language": "C", "target_language": "Rust", "source_extensions": [".c", ".h"]}
MANIFEST_ROW = {"id": "crust__bitset", "tool": "crust", "source_language": "C", "target_language": "Rust"}


def _write_state(run_dir: Path, *, status="completed") -> None:
    state = {
        "variant": "full", "project_id": "crust__bitset", "repetition": 0, "status": status,
        "app_id": "app1", "workspace_dir": str(run_dir), "argv": None, "returncode": 0, "attempt": 1,
        "created_at": "2024-01-01T00:00:00.000000Z", "updated_at": "2024-01-01T00:05:00.000000Z",
        "started_at": "2024-01-01T00:00:00.000000Z", "ended_at": "2024-01-01T00:05:00.000000Z",
        "timeout_seconds": None, "error": "",
    }
    C.atomic_write_json(run_dir / R.STATE_FILENAME, state)


def test_compare_run_raises_skip_when_run_dir_missing(tmp_path: Path):
    with pytest.raises(TC.ComparisonSkip, match="not_attempted"):
        TC.compare_run(tmp_path / "nope", variant="full", project_id="crust__bitset", tool="crust",
                       repetition=0, manifest_row=MANIFEST_ROW, dataset_spec=CRUST_SPEC)


def test_compare_run_raises_skip_when_no_state_file(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    with pytest.raises(TC.ComparisonSkip, match="no_state_file"):
        TC.compare_run(run_dir, variant="full", project_id="crust__bitset", tool="crust",
                       repetition=0, manifest_row=MANIFEST_ROW, dataset_spec=CRUST_SPEC)


def test_compare_run_raises_skip_when_not_terminal(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_state(run_dir, status="running")
    with pytest.raises(TC.ComparisonSkip, match="not_terminal"):
        TC.compare_run(run_dir, variant="full", project_id="crust__bitset", tool="crust",
                       repetition=0, manifest_row=MANIFEST_ROW, dataset_spec=CRUST_SPEC)


def test_compare_run_raises_skip_when_source_tree_missing(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_state(run_dir)
    with pytest.raises(TC.ComparisonSkip, match="missing_source"):
        TC.compare_run(run_dir, variant="full", project_id="crust__bitset", tool="crust",
                       repetition=0, manifest_row=MANIFEST_ROW, dataset_spec=CRUST_SPEC)


def test_compare_run_measures_translation_rate_for_completed_run(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "source").mkdir(parents=True)
    (run_dir / "source" / "test_lib.c").write_text(
        "void test_add(void) { assert(add(1, 2) == 3); }\n"
        "void test_flag(void) { assert(is_ready()); }\n",
        encoding="utf-8",
    )
    (run_dir / "pipeline" / "target").mkdir(parents=True)
    (run_dir / "pipeline" / "target" / "lib.rs").write_text(
        "#[test]\nfn test_add() { assert_eq!(add(1, 2), 3); }\n",
        encoding="utf-8",
    )
    _write_state(run_dir)

    rows = TC.compare_run(run_dir, variant="full", project_id="crust__bitset", tool="crust", repetition=0,
                         manifest_row=MANIFEST_ROW, dataset_spec=CRUST_SPEC)
    by_name = {r["source_test_name"]: r for r in rows}
    assert by_name["test_add"]["mapped"] is True
    assert by_name["test_add"]["mapping_status"] == Status.MEASURED
    assert by_name["test_flag"]["mapped"] is False
    assert by_name["test_flag"]["mapping_status"] == Status.MISSING


def test_compare_run_reports_zero_translation_when_nothing_produced(tmp_path: Path):
    """A REAL completed run that produced no target tests at all is a
    genuine measured zero, not missing data -- must not raise ComparisonSkip."""
    run_dir = tmp_path / "run"
    (run_dir / "source").mkdir(parents=True)
    (run_dir / "source" / "test_lib.c").write_text(
        "void test_add(void) { assert(1 == 1); }\n", encoding="utf-8",
    )
    _write_state(run_dir, status="failed")
    rows = TC.compare_run(run_dir, variant="full", project_id="crust__bitset", tool="crust", repetition=0,
                         manifest_row=MANIFEST_ROW, dataset_spec=CRUST_SPEC)
    assert len(rows) == 1
    assert rows[0]["mapped"] is False
    assert rows[0]["mapping_status"] == Status.MISSING


# --------------------------------------------------------------------------- #
# compare_all: matrix-wide orchestration
# --------------------------------------------------------------------------- #
def _manifest(project_ids: list[str]) -> dict:
    return {"projects": [
        {"id": pid, "tool": "crust", "source_language": "C", "target_language": "Rust"}
        for pid in project_ids
    ]}


def test_compare_all_reports_not_attempted_for_missing_run_dirs(tmp_path: Path):
    manifest = _manifest(["crust__a", "crust__b"])
    rows, failures = TC.compare_all(tmp_path / "runs", manifest, variants=["full"], repetitions=1,
                                   dataset_specs={"crust": CRUST_SPEC})
    assert rows == []
    assert len(failures) == 2
    assert all("not_attempted" in f["reason"] for f in failures)


def test_compare_all_partitions_measured_and_unattempted(tmp_path: Path):
    manifest = _manifest(["crust__a", "crust__b"])
    runs_root = tmp_path / "runs"
    run_dir_a = R.run_dir_for(runs_root, "full", "crust__a", 0)
    (run_dir_a / "source").mkdir(parents=True)
    (run_dir_a / "source" / "test_lib.c").write_text(
        "void test_add(void) { assert(1 == 1); }\n", encoding="utf-8",
    )
    _write_state(run_dir_a)

    rows, failures = TC.compare_all(runs_root, manifest, variants=["full"], repetitions=1,
                                   dataset_specs={"crust": CRUST_SPEC})
    assert len(rows) == 1
    assert rows[0]["project_id"] == "crust__a"
    assert len(failures) == 1
    assert failures[0]["project_id"] == "crust__b"


def test_compare_all_never_raises_on_a_single_bad_run(tmp_path: Path, monkeypatch):
    manifest = _manifest(["crust__a"])
    runs_root = tmp_path / "runs"
    run_dir_a = R.run_dir_for(runs_root, "full", "crust__a", 0)
    (run_dir_a / "source").mkdir(parents=True)
    _write_state(run_dir_a)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(TC, "parse_tests_in_tree", boom)
    rows, failures = TC.compare_all(runs_root, manifest, variants=["full"], repetitions=1,
                                   dataset_specs={"crust": CRUST_SPEC})
    assert rows == []
    assert len(failures) == 1
    assert "comparison_error" in failures[0]["reason"]


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #
def test_write_test_comparisons_creates_csv_and_jsonl(tmp_path: Path):
    rows = [{"project_id": "crust__a", "tool": "crust", "variant": "full", "repetition": 0,
            "source_test_name": "test_add", "source_test_file": "f.c", "mapped": True,
            "mapping_status": Status.MEASURED, "mapping_reason": "", "mapping_confidence": 1.0,
            "translated_test_name": "test_add", "translated_test_file": "f.rs", "test_origin": "translated"}]
    json_path, csv_path = TC.write_test_comparisons(rows, tmp_path)
    assert json_path.exists() and csv_path.exists()
    lines = json_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["project_id"] == "crust__a"
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "test_add" in csv_text
    assert "mapping_status" in csv_text.splitlines()[0]


def test_write_comparison_failures_creates_csv(tmp_path: Path):
    failures = [{"variant": "full", "project_id": "crust__a", "tool": "crust", "repetition": 0,
                "workspace_dir": "x", "reason": "not_attempted", "detected_at": C.utcnow_iso()}]
    path = TC.write_comparison_failures(failures, tmp_path)
    assert path.exists()
    assert "not_attempted" in path.read_text(encoding="utf-8")


def test_write_summary_writes_json(tmp_path: Path):
    summary = TC.summarize_comparisons([])
    path = TC.write_summary(summary, tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["total_source_tests"] == 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_parse_variants_all_and_explicit_list():
    assert TC._parse_variants("all") == list(C.RUN_VARIANTS)
    assert TC._parse_variants("full,noanalyzer") == ["full", "noanalyzer"]


def test_parse_variants_rejects_unknown():
    with pytest.raises(ValueError):
        TC._parse_variants("not-a-real-variant")


def test_build_parser_embeddings_flag_defaults_false():
    args = TC.build_parser().parse_args(["--manifest", "m.json", "--runs-root", "r", "--output-root", "o"])
    assert args.embeddings is False


def test_cli_main_smoke_no_toolchain_needed(tmp_path: Path):
    """No run directories exist at all -- compare_all must short-circuit to
    'not_attempted' failures without ever reading a real toolchain output, so
    this is safe to run with nothing installed."""
    manifest_path = tmp_path / "manifest.json"
    C.atomic_write_json(manifest_path, _manifest(["crust__a"]))
    output_root = tmp_path / "out"
    rc = TC.main([
        "--manifest", str(manifest_path), "--runs-root", str(tmp_path / "runs"),
        "--output-root", str(output_root), "--variant", "full", "--repetitions", "1",
    ])
    assert rc == 0
    assert (output_root / "test_comparisons.csv").exists()
    assert (output_root / "test_comparison_failures.csv").exists()
    assert (output_root / "test_comparison_summary.json").exists()
    failures_text = (output_root / "test_comparison_failures.csv").read_text(encoding="utf-8")
    assert "not_attempted" in failures_text
