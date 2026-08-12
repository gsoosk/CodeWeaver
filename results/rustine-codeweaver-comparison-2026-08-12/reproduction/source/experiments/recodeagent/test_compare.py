"""test_compare.py -- RQ2: map every SOURCE developer test to a translated
target test (never silently drop a source test) and compute per-test +
aggregate test-comparison metrics.

Per the paper's RQ2 protocol this module computes, for each (variant,
project, repetition) run:

  - a translation rate: fraction of source developer tests that have a
    corresponding translated target test (name-similarity mapped, see
    :func:`map_tests`);
  - a matching assertion-count rate between a mapped source/target pair;
  - ``assertEqual`` expected-output equivalence for literal string/int/float/
    bool expected values (variable/expression expected values are reported as
    "undetermined", never guessed);
  - assertion-TYPE match (paper's four buckets: equal/true/false/other);
  - optional Qwen embedding cosine similarity (via ``sentence-transformers``
    if installed AND explicitly opted into with ``--embeddings`` -- this
    harness never installs the dependency, downloads a model, or calls out to
    a network on its own; :func:`compute_embedding_similarity` reports
    ``Status.UNAVAILABLE`` with an explicit reason whenever it is not
    installed, and the CLI only wires it in when asked);
  - LoC and (heuristic) method-invocation counts per test.

Every target-tree test with NO source counterpart is still reported (as a
row with ``test_origin="generated"``) -- CodeWeaver-generated tests are a
distinct RQ1 concept the paper also tracks, and must never be silently merged
into "translated" counts nor dropped.

ADAPTER-BASED, NOT A REAL PARSER (documented, testable): test discovery and
assertion extraction for all six languages involved (C, Go, Java, Python,
Rust, JavaScript) are regex heuristics, exactly like manifest.py's own
LoC/test/function counters -- good enough for structural comparison at scale,
not a substitute for a real AST-based comparison. A test's "body" is
approximated as the text from its own definition to the next test
definition (or EOF), which may include a little trailing non-test code
shared between two test functions -- a documented limitation of a
regex-only, non-parsing adapter.

INTEGRATION ASSUMPTION (documented, needs verification against the real
official artifact once acquired): source developer tests are discovered from
each project's ``source/`` tree (as materialized into a run directory by
prepare.py's ``materialize_run`` -- i.e. the SAME tree manifest.py's own
``test_count_source`` is computed against), not from the separate
``oracle/`` tree. Some datasets' oracle-directory candidate names (e.g.
CRUST's ``RBench``, see experiment.toml) suggest the oracle tree may hold
TARGET-language evaluator content rather than source-language developer
tests for that family, so this module deliberately does not assume
``oracle/`` is source-language content. If the real artifact's ``oracle/``
turns out to also hold additional source tests for some dataset, extend
:func:`compare_run` to union it in -- that is a config/adapter change, not a
protocol change.

Like collect.py, this module only ever INGESTS a run.py/materialize_run
output; it never mutates a run directory (besides writing its own separate
output files under ``--output-root``), and a run that has not reached a
terminal state (or was never attempted) is routed to
``test_comparison_failures.csv`` with a reason -- never fabricated as an
all-zero/all-missing comparison row.

NOTE ON PYTEST COLLECTION: this file's name matches pytest's default
``test_*.py`` discovery glob. See ``experiments/recodeagent/conftest.py``
(``collect_ignore = ["test_compare.py"]``) -- this repository has no
``pytest.ini``/``testpaths`` restricting discovery to ``tests/``, so without
that guard a bare ``pytest`` invocation from the repository root would
attempt to import this module as a test suite. The actual automated tests
for this module live at ``tests/experiments/test_test_compare.py``.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from experiments.recodeagent import common as C
from experiments.recodeagent import manifest as M
from experiments.recodeagent import run as R
from experiments.recodeagent.collect import TARGET_LANGUAGE_EXTENSIONS
from experiments.recodeagent.common import (
    Measurement,
    Status,
    atomic_write_text,
    read_json_or,
    utcnow_iso,
)

SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Assertion:
    kind: str                          # "equal" | "true" | "false" | "other"
    expected_repr: str | None = None   # raw text of the RHS/expected-value argument, if kind == "equal"


@dataclass
class ParsedTest:
    name: str
    file: str
    body: str
    assertions: list[Assertion] = field(default_factory=list)
    method_invocation_count: int = 0
    loc: int = 0


# --------------------------------------------------------------------------- #
# Per-language test-definition (chunk-boundary) patterns. Every pattern uses a
# named group ``name`` so callers need no per-language special-casing.
# --------------------------------------------------------------------------- #
TEST_NAME_PATTERNS: dict[str, re.Pattern[str]] = {
    "C": re.compile(r"^\s*(?:static\s+)?(?:void|int)\s+(?P<name>test_\w+)\s*\(", re.MULTILINE | re.IGNORECASE),
    "Go": re.compile(r"^func\s+(?P<name>Test\w+)\s*\(", re.MULTILINE),
    "Java": re.compile(r"@Test\b[^\n]*\n[^\n]*?\b(?P<name>\w+)\s*\(", re.MULTILINE),
    "Python": re.compile(r"^\s*def\s+(?P<name>test_\w+)\s*\(", re.MULTILINE),
    "Rust": re.compile(r"#\[test\]\s*\r?\n\s*(?:pub\s+)?(?:async\s+)?fn\s+(?P<name>\w+)", re.MULTILINE),
    "JavaScript": re.compile(r"\b(?:it|test)\s*\(\s*['\"](?P<name>.*?)['\"]", re.MULTILINE),
}


def _language_key(language: str) -> str:
    normalized = (language or "").strip()
    for key in TEST_NAME_PATTERNS:
        if key.lower() == normalized.lower():
            return key
    return normalized


# --------------------------------------------------------------------------- #
# Per-language assertion-callsite extraction. Each language uses ONE combined,
# ordered alternation regex per callsite so a given source position is
# classified exactly once (no double-counting from overlapping patterns).
# --------------------------------------------------------------------------- #
_C_CALL_RE = re.compile(r"\bassert\s*\(\s*(?P<args>.+?)\s*\)\s*;", re.DOTALL)


def _assertions_c(body: str) -> list[Assertion]:
    # Plain assert(actual == expected) has no framework-enforced argument
    # order; by convention (and this adapter's choice) the RHS of == is
    # treated as the expected literal.
    out: list[Assertion] = []
    for m in _C_CALL_RE.finditer(body):
        args = m.group("args").strip()
        eq = re.match(r"^(.+?)\s*==\s*(.+)$", args, re.DOTALL)
        if eq:
            out.append(Assertion(kind="equal", expected_repr=eq.group(2).strip()))
        elif args.startswith("!"):
            out.append(Assertion(kind="false"))
        else:
            out.append(Assertion(kind="true"))
    return out


_GO_CALL_RE = re.compile(
    r"assert\.Equal\s*\(\s*t\s*,\s*(?P<eq_a>[^,]+?)\s*,\s*(?P<eq_b>[^,\)]+?)\s*[,\)]"
    r"|assert\.True\s*\(\s*t\s*,"
    r"|assert\.False\s*\(\s*t\s*,"
    r"|\bt\.(?:Errorf|Fatalf|Fatal|Error)\s*\(",
)


def _assertions_go(body: str) -> list[Assertion]:
    # testify's documented signature is assert.Equal(t, expected, actual, ...)
    # -- eq_a (the first non-t argument) is the expected literal.
    out: list[Assertion] = []
    for m in _GO_CALL_RE.finditer(body):
        text = m.group(0)
        if m.group("eq_a") is not None:
            out.append(Assertion(kind="equal", expected_repr=m.group("eq_a").strip()))
        elif text.startswith("assert.True"):
            out.append(Assertion(kind="true"))
        elif text.startswith("assert.False"):
            out.append(Assertion(kind="false"))
        else:
            out.append(Assertion(kind="other"))
    return out


_JAVA_CALL_RE = re.compile(
    r"assertEquals\s*\(\s*(?P<eq_a>[^,]+?)\s*,\s*(?P<eq_b>[^,\)]+?)\s*[,\)]"
    r"|assertTrue\s*\("
    r"|assertFalse\s*\("
    r"|assert(?:NotNull|Null|Throws|Same|NotSame|ArrayEquals)\s*\(",
)


def _assertions_java(body: str) -> list[Assertion]:
    # JUnit's documented signature is assertEquals(expected, actual) -- eq_a
    # (the first argument) is the expected literal.
    out: list[Assertion] = []
    for m in _JAVA_CALL_RE.finditer(body):
        text = m.group(0)
        if m.group("eq_a") is not None:
            out.append(Assertion(kind="equal", expected_repr=m.group("eq_a").strip()))
        elif text.startswith("assertTrue"):
            out.append(Assertion(kind="true"))
        elif text.startswith("assertFalse"):
            out.append(Assertion(kind="false"))
        else:
            out.append(Assertion(kind="other"))
    return out


_PY_CALL_RE = re.compile(
    r"self\.assertEqual\s*\(\s*(?P<eq_a>[^,]+?)\s*,\s*(?P<eq_b>[^,\)]+?)\s*[,\)]"
    r"|self\.assertTrue\s*\("
    r"|self\.assertFalse\s*\("
    r"|self\.assert(?:Raises|In|NotIn|IsNone|IsNotNone|IsInstance|Is)\s*\("
    r"|^[ \t]*assert\s+(?!self\.)(?P<bare_a>[^\n=!<>]+?)\s*==\s*(?P<bare_b>[^\n]+?)\s*$"
    r"|^[ \t]*assert\s+(?!self\.)[^\n]+$",
    re.MULTILINE,
)


def _assertions_python(body: str) -> list[Assertion]:
    # unittest's assertEqual(first, second) has no framework-enforced
    # expected/actual order; by convention (and this adapter's choice) the
    # SECOND argument -- typically the literal in `assertEqual(computed,
    # literal)` style -- is treated as the expected value, matching bare
    # `assert computed == literal` too.
    out: list[Assertion] = []
    for m in _PY_CALL_RE.finditer(body):
        text = m.group(0)
        if m.group("eq_b") is not None:
            out.append(Assertion(kind="equal", expected_repr=m.group("eq_b").strip()))
        elif m.group("bare_b") is not None:
            out.append(Assertion(kind="equal", expected_repr=m.group("bare_b").strip()))
        elif "assertTrue" in text:
            out.append(Assertion(kind="true"))
        elif "assertFalse" in text:
            out.append(Assertion(kind="false"))
        elif text.lstrip().startswith("assert "):
            out.append(Assertion(kind="true"))
        else:
            out.append(Assertion(kind="other"))
    return out


_RUST_CALL_RE = re.compile(r"\b(assert_eq|assert_ne|assert)!\s*\(")


def _assertions_rust(body: str) -> list[Assertion]:
    # assert_eq!(left, right) is symmetric in the std library; by convention
    # (matching the Python adapter above) the SECOND argument is treated as
    # the expected value.
    out: list[Assertion] = []
    for m in _RUST_CALL_RE.finditer(body):
        macro = m.group(1)
        rest = body[m.end():]
        if macro == "assert_eq":
            args_m = re.match(r"\s*(.+?)\s*,\s*(.+?)\s*[,\)]", rest, re.DOTALL)
            out.append(Assertion(kind="equal", expected_repr=args_m.group(2).strip()) if args_m
                      else Assertion(kind="other"))
        elif macro == "assert_ne":
            out.append(Assertion(kind="other"))
        else:
            out.append(Assertion(kind="false") if rest.lstrip().startswith("!") else Assertion(kind="true"))
    return out


# Jest's `expect(...)` receiver commonly itself contains a call, e.g.
# `expect(isReady()).toBeTruthy()` -- allow one level of nested parens inside
# the receiver argument so that common pattern is not silently unmatched.
_JS_RECEIVER = r"\([^()]*(?:\([^()]*\)[^()]*)*\)"
_JS_CALL_RE = re.compile(
    r"expect\s*" + _JS_RECEIVER + r"\s*\.\s*(?:toBe|toEqual|toStrictEqual)\s*\(\s*(?P<eq>[^()]*)\)"
    r"|expect\s*" + _JS_RECEIVER + r"\s*\.\s*toBeTruthy\s*\(\s*\)"
    r"|expect\s*" + _JS_RECEIVER + r"\s*\.\s*toBeFalsy\s*\(\s*\)"
    r"|expect\s*" + _JS_RECEIVER + r"\s*\.\s*\w+\s*\(",
)


def _assertions_js(body: str) -> list[Assertion]:
    out: list[Assertion] = []
    for m in _JS_CALL_RE.finditer(body):
        text = m.group(0)
        if m.group("eq") is not None:
            out.append(Assertion(kind="equal", expected_repr=m.group("eq").strip()))
        elif "toBeTruthy" in text:
            out.append(Assertion(kind="true"))
        elif "toBeFalsy" in text:
            out.append(Assertion(kind="false"))
        else:
            out.append(Assertion(kind="other"))
    return out


ASSERTION_EXTRACTORS: dict[str, Callable[[str], list[Assertion]]] = {
    "C": _assertions_c,
    "Go": _assertions_go,
    "Java": _assertions_java,
    "Python": _assertions_python,
    "Rust": _assertions_rust,
    "JavaScript": _assertions_js,
}


# --------------------------------------------------------------------------- #
# Method-invocation heuristic: generic "identifier(" call-site count, minus
# the assertion-framework calls themselves, control-flow keywords, and the
# test's own name. Deliberately coarse/cross-language (documented) -- not a
# real call-graph analysis.
# --------------------------------------------------------------------------- #
_ASSERTION_CALL_NAMES = {
    "assert", "assertEqual", "assertEquals", "assertTrue", "assertFalse",
    "assertRaises", "assertIn", "assertNotIn", "assertIsNone", "assertIsNotNone",
    "assertIsInstance", "assertIs", "assertNotNull", "assertNull", "assertThrows",
    "assertSame", "assertNotSame", "assertArrayEquals", "assert_eq", "assert_ne",
    "expect", "toBe", "toEqual", "toStrictEqual", "toBeTruthy", "toBeFalsy",
    "Equal", "True", "False", "Errorf", "Fatalf", "Fatal", "Error",
}
_CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "new"}
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _count_method_invocations(body: str, test_name: str) -> int:
    count = 0
    for m in _CALL_RE.finditer(body):
        name = m.group(1)
        if name == test_name or name in _ASSERTION_CALL_NAMES or name.lower() in _CONTROL_KEYWORDS:
            continue
        count += 1
    return count


# --------------------------------------------------------------------------- #
# Literal expected-value type inference/normalization (string/int/float/bool
# only -- anything else, e.g. a variable or expression, is left undetermined,
# never guessed).
# --------------------------------------------------------------------------- #
def infer_literal(repr_text: str | None) -> tuple[str | None, Any]:
    if repr_text is None:
        return None, None
    text = repr_text.strip().rstrip(";")
    if text in ("true", "True"):
        return "bool", True
    if text in ("false", "False"):
        return "bool", False
    for quote in ('"', "'", "`"):
        if len(text) >= 2 and text.startswith(quote) and text.endswith(quote):
            return "string", text[1:-1]
    if re.fullmatch(r"-?\d+", text):
        return "int", int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return "float", float(text)
    return None, None


# --------------------------------------------------------------------------- #
# Test discovery / parsing for one file's text, and for a whole tree.
# --------------------------------------------------------------------------- #
def parse_tests(text: str, file_rel: str, language: str) -> list[ParsedTest]:
    """Adapter-based test discovery + assertion/LoC/method-invocation
    extraction for one source file's text. A test's body is approximated as
    the text from its own definition to the NEXT test definition (or EOF) --
    see module docstring for the documented limitation this implies."""
    key = _language_key(language)
    name_pattern = TEST_NAME_PATTERNS.get(key)
    extractor = ASSERTION_EXTRACTORS.get(key)
    if name_pattern is None or extractor is None:
        return []
    matches = list(name_pattern.finditer(text))
    tests: list[ParsedTest] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        name = m.group("name")
        tests.append(ParsedTest(
            name=name, file=file_rel, body=body, assertions=extractor(body),
            method_invocation_count=_count_method_invocations(body, name),
            loc=sum(1 for line in body.splitlines() if line.strip()),
        ))
    return tests


def find_test_files(root: Path, extensions: list[str], language: str) -> list[Path]:
    key = _language_key(language)
    pattern = TEST_NAME_PATTERNS.get(key)
    if pattern is None or not extensions:
        return []
    hits: list[Path] = []
    for f in M.iter_source_files(root, extensions):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            hits.append(f)
    return hits


def parse_tests_in_tree(root: Path, extensions: list[str], language: str) -> list[ParsedTest]:
    tests: list[ParsedTest] = []
    if not root.exists():
        return tests
    for f in find_test_files(root, extensions, language):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(f.relative_to(root))
        except ValueError:
            rel = str(f)
        tests.extend(parse_tests(text, rel, language))
    return tests


# --------------------------------------------------------------------------- #
# Mapping: greedy, one-to-one, name-similarity based (stdlib difflib only --
# no dependency). Every source test is represented in the output (mapped or
# explicitly not-mapped); target tests no source test claims are reported
# separately as "generated", never merged into "translated" counts.
# --------------------------------------------------------------------------- #
MAPPING_SIMILARITY_THRESHOLD = 0.35


def _normalize_test_name(name: str) -> str:
    name = re.sub(r"^test[_]?", "", name, flags=re.IGNORECASE)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)   # split camelCase
    name = re.sub(r"[^A-Za-z0-9]+", " ", name)
    return name.strip().lower()


def name_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize_test_name(a), _normalize_test_name(b)).ratio()


def map_tests(source_tests: list[ParsedTest], target_tests: list[ParsedTest]) -> list[dict[str, Any]]:
    pairs: list[tuple[float, int, int]] = []
    for si, s in enumerate(source_tests):
        for ti, t in enumerate(target_tests):
            pairs.append((name_similarity(s.name, t.name), si, ti))
    pairs.sort(key=lambda p: p[0], reverse=True)

    matched_source: dict[int, int] = {}
    matched_target: set[int] = set()
    for score, si, ti in pairs:
        if si in matched_source or ti in matched_target or score < MAPPING_SIMILARITY_THRESHOLD:
            continue
        matched_source[si] = ti
        matched_target.add(ti)

    results: list[dict[str, Any]] = []
    for si in range(len(source_tests)):
        if si in matched_source:
            ti = matched_source[si]
            results.append({"target_index": ti, "score": name_similarity(source_tests[si].name,
                                                                          target_tests[ti].name), "mapped": True})
        else:
            results.append({"target_index": None, "score": None, "mapped": False})
    return results


def unmapped_target_indices(target_tests: list[ParsedTest], mapping: list[dict[str, Any]]) -> list[int]:
    mapped = {m["target_index"] for m in mapping if m["mapped"]}
    return [i for i in range(len(target_tests)) if i not in mapped]


# --------------------------------------------------------------------------- #
# Optional Qwen embedding cosine similarity -- opt-in only, never installs a
# dependency or triggers a network call by default.
# --------------------------------------------------------------------------- #
_EMBEDDING_MODEL_CACHE: dict[str, Any] = {}


def compute_embedding_similarity(text_a: str, text_b: str, *,
                                 model_name: str = "Qwen/Qwen3-Embedding-0.6B") -> Measurement:
    """Real Qwen sentence-embedding cosine similarity via sentence-transformers,
    IF installed. Returns Status.UNAVAILABLE (never a fabricated number) when
    the package is not installed; Status.ERROR if it is installed but loading
    or encoding fails for any reason (e.g. model weights not cached locally
    and no network access here). Callers (the CLI's ``--embeddings`` flag)
    decide whether to invoke this at all -- it is never called by default."""
    st = C.optional_import("sentence_transformers")
    if st is None:
        return Measurement.unavailable("sentence-transformers is not installed in this environment")
    try:
        model = _EMBEDDING_MODEL_CACHE.get(model_name)
        if model is None:
            model = st.SentenceTransformer(model_name)
            _EMBEDDING_MODEL_CACHE[model_name] = model
        vectors = model.encode([text_a, text_b])
        a, b = vectors[0], vectors[1]
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        norm_a = sum(float(x) * float(x) for x in a) ** 0.5
        norm_b = sum(float(y) * float(y) for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return Measurement.error("zero-norm embedding vector")
        return Measurement.ok(dot / (norm_a * norm_b))
    except Exception as e:  # noqa: BLE001 - an optional path must never crash the harness
        return Measurement.error(f"embedding computation failed: {e!r}")


EmbeddingFn = Callable[[str, str], Measurement]


# --------------------------------------------------------------------------- #
# Per-test comparison row assembly
# --------------------------------------------------------------------------- #
def _build_row(
    source: ParsedTest | None,
    target: ParsedTest | None,
    mapping_entry: dict[str, Any],
    *,
    project_id: str,
    tool: str,
    variant: str,
    repetition: int,
    embedding_fn: EmbeddingFn | None,
    test_origin: str | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "project_id": project_id, "tool": tool, "variant": variant, "repetition": repetition,
        "source_test_name": source.name if source else None,
        "source_test_file": source.file if source else None,
        "mapped": bool(mapping_entry.get("mapped")),
        "mapping_confidence": mapping_entry.get("score"),
        "translated_test_name": target.name if target else None,
        "translated_test_file": target.file if target else None,
        "test_origin": test_origin,
    }
    if source is None:
        row["mapping_status"] = Status.NOT_APPLICABLE
        row["mapping_reason"] = "generated test: no corresponding source developer test"
    elif target is not None:
        row["mapping_status"] = Status.MEASURED
        row["mapping_reason"] = ""
    else:
        row["mapping_status"] = Status.MISSING
        row["mapping_reason"] = "no target test met the minimum name-similarity threshold"

    row["assertion_count_source"] = len(source.assertions) if source else None
    row["loc_source"] = source.loc if source else None
    row["method_invocation_count_source"] = source.method_invocation_count if source else None
    row["assertion_count_translated"] = len(target.assertions) if target else None
    row["loc_translated"] = target.loc if target else None
    row["method_invocation_count_translated"] = target.method_invocation_count if target else None
    row["assertion_count_match"] = (
        row["assertion_count_source"] == row["assertion_count_translated"]
        if source is not None and target is not None else None
    )

    src_eq = next((a for a in (source.assertions if source else []) if a.kind == "equal"), None)
    tgt_eq = next((a for a in (target.assertions if target else []) if a.kind == "equal"), None)
    src_type, src_val = infer_literal(src_eq.expected_repr if src_eq else None)
    tgt_type, tgt_val = infer_literal(tgt_eq.expected_repr if tgt_eq else None)
    row["assert_equal_expected_value_source"] = (
        src_val if src_type is not None else (src_eq.expected_repr if src_eq else None)
    )
    row["assert_equal_expected_value_translated"] = (
        tgt_val if tgt_type is not None else (tgt_eq.expected_repr if tgt_eq else None)
    )
    if src_eq is not None and tgt_eq is not None and src_type is not None and tgt_type is not None:
        row["assert_equal_value_type"] = src_type if src_type == tgt_type else None
        row["assert_equal_expected_value_equivalent"] = (src_type == tgt_type and src_val == tgt_val)
    else:
        row["assert_equal_value_type"] = None
        row["assert_equal_expected_value_equivalent"] = None

    src_kind = source.assertions[0].kind if source and source.assertions else None
    tgt_kind = target.assertions[0].kind if target and target.assertions else None
    row["assertion_type_source"] = src_kind
    row["assertion_type_translated"] = tgt_kind
    row["assertion_type_match"] = (src_kind == tgt_kind) if (src_kind and tgt_kind) else None

    if embedding_fn is not None and source is not None and target is not None:
        m = embedding_fn(source.body, target.body)
    else:
        reason = ("no embedding function configured (pass --embeddings to opt in)" if source and target
                 else "embedding similarity requires both a mapped source and target test")
        m = Measurement.unavailable(reason)
    row["embedding_cosine_similarity"] = m.value
    row["embedding_status"] = m.status if m.status in (Status.MEASURED, Status.ERROR) else Status.UNAVAILABLE
    row["embedding_reason"] = m.reason
    return row


def build_comparison_rows(
    source_tests: list[ParsedTest],
    target_tests: list[ParsedTest],
    *,
    project_id: str,
    tool: str,
    variant: str = "",
    repetition: int = 0,
    embedding_fn: EmbeddingFn | None = None,
) -> list[dict[str, Any]]:
    mapping = map_tests(source_tests, target_tests)
    rows: list[dict[str, Any]] = []
    for si, source in enumerate(source_tests):
        entry = mapping[si]
        target = target_tests[entry["target_index"]] if entry["mapped"] else None
        rows.append(_build_row(source, target, entry, project_id=project_id, tool=tool, variant=variant,
                               repetition=repetition, embedding_fn=embedding_fn,
                               test_origin="translated" if entry["mapped"] else None))
    for ti in unmapped_target_indices(target_tests, mapping):
        rows.append(_build_row(None, target_tests[ti], {"mapped": False, "score": None}, project_id=project_id,
                               tool=tool, variant=variant, repetition=repetition, embedding_fn=embedding_fn,
                               test_origin="generated"))
    return rows


# --------------------------------------------------------------------------- #
# Per-run orchestration
# --------------------------------------------------------------------------- #
class ComparisonSkip(Exception):
    """Raised internally to route a run to test_comparison_failures.csv with
    a reason, instead of writing a fabricated (all-missing) comparison row."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def compare_run(
    run_dir: Path,
    *,
    variant: str,
    project_id: str,
    tool: str,
    repetition: int,
    manifest_row: dict[str, Any] | None,
    dataset_spec: dict[str, Any],
    embedding_fn: EmbeddingFn | None = None,
) -> list[dict[str, Any]]:
    """Compare ONE run's produced target tests against its project's source
    developer tests. Raises :class:`ComparisonSkip` (never returns a
    fabricated row) when the run cannot be objectively evaluated yet."""
    if not run_dir.exists():
        raise ComparisonSkip("not_attempted: no run directory found")
    state = read_json_or(run_dir / R.STATE_FILENAME, None)
    if state is None:
        raise ComparisonSkip("no_state_file: recodeagent_run_state.json missing or unparseable")
    run_status = state.get("status")
    if run_status not in ("completed", "failed", "timeout"):
        raise ComparisonSkip(f"not_terminal: run status is {run_status!r} (has not finished)")

    source_root = run_dir / "source"
    if not source_root.exists():
        raise ComparisonSkip("missing_source: run directory has no source/ tree "
                             "(materialize_run may not have completed)")

    source_language = (manifest_row or {}).get("source_language") or dataset_spec.get("source_language", "")
    target_language = (manifest_row or {}).get("target_language") or dataset_spec.get("target_language", "")
    source_extensions = dataset_spec.get("source_extensions", [])
    target_extensions = TARGET_LANGUAGE_EXTENSIONS.get(target_language, [])

    source_tests = parse_tests_in_tree(source_root, source_extensions, source_language)
    target_tests = parse_tests_in_tree(run_dir / "pipeline" / "target", target_extensions, target_language)

    return build_comparison_rows(
        source_tests, target_tests, project_id=project_id, tool=tool, variant=variant,
        repetition=repetition, embedding_fn=embedding_fn,
    )


def compare_all(
    runs_root: Path,
    manifest: dict[str, Any],
    *,
    variants: list[str],
    project_ids: list[str] | None = None,
    repetitions: int = 1,
    dataset_specs: dict[str, dict[str, Any]] | None = None,
    embedding_fn: EmbeddingFn | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Walks the FULL expected (variant, project, repetition) matrix (like
    collect.py's collect_all) so a never-attempted job is reported in
    test_comparison_failures.csv rather than silently absent."""
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    dataset_specs = dataset_specs or {}
    rows_by_id = {r["id"]: r for r in manifest.get("projects", [])}
    ids = project_ids if project_ids is not None else list(rows_by_id.keys())

    for variant in variants:
        for project_id in ids:
            manifest_row = rows_by_id.get(project_id)
            tool = (manifest_row or {}).get("tool", "")
            spec = dataset_specs.get(tool, {})
            for repetition in range(repetitions):
                run_dir = R.run_dir_for(runs_root, variant, project_id, repetition)
                try:
                    rows.extend(compare_run(
                        run_dir, variant=variant, project_id=project_id, tool=tool, repetition=repetition,
                        manifest_row=manifest_row, dataset_spec=spec, embedding_fn=embedding_fn,
                    ))
                except ComparisonSkip as e:
                    failures.append({"variant": variant, "project_id": project_id, "tool": tool,
                                     "repetition": repetition, "workspace_dir": str(run_dir),
                                     "reason": e.reason, "detected_at": utcnow_iso()})
                except Exception as e:  # noqa: BLE001 - never let one bad run abort the whole matrix
                    failures.append({"variant": variant, "project_id": project_id, "tool": tool,
                                     "repetition": repetition, "workspace_dir": str(run_dir),
                                     "reason": f"comparison_error: {e!r}", "detected_at": utcnow_iso()})
    return rows, failures


# --------------------------------------------------------------------------- #
# Aggregate RQ2 summary
# --------------------------------------------------------------------------- #
def _rate(numerator: int, denominator: int) -> float | None:
    return (numerator / denominator) if denominator else None


def summarize_comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate RQ2 rates. Every rate also reports its OWN denominator so a
    reader can tell a 100% rate over 2 tests from one over 200 -- and rates
    are computed only over rows where the relevant field is determinable
    (None values are excluded from both numerator and denominator, never
    coerced to a failing 0)."""
    source_rows = [r for r in rows if r.get("test_origin") != "generated"]
    generated_rows = [r for r in rows if r.get("test_origin") == "generated"]
    mapped_rows = [r for r in source_rows if r.get("mapped")]

    count_known = [r for r in mapped_rows if r.get("assertion_count_match") is not None]
    count_matches = [r for r in count_known if r["assertion_count_match"]]
    equiv_known = [r for r in mapped_rows if r.get("assert_equal_expected_value_equivalent") is not None]
    equiv_true = [r for r in equiv_known if r["assert_equal_expected_value_equivalent"]]
    type_known = [r for r in mapped_rows if r.get("assertion_type_match") is not None]
    type_matches = [r for r in type_known if r["assertion_type_match"]]
    embedding_measured = [r for r in mapped_rows if r.get("embedding_status") == Status.MEASURED
                         and r.get("embedding_cosine_similarity") is not None]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utcnow_iso(),
        "total_source_tests": len(source_rows),
        "total_mapped_tests": len(mapped_rows),
        "total_generated_tests": len(generated_rows),
        "translation_rate": _rate(len(mapped_rows), len(source_rows)),
        "assertion_count_match_rate": _rate(len(count_matches), len(count_known)),
        "assertion_count_match_denominator": len(count_known),
        "assert_equal_equivalence_rate": _rate(len(equiv_true), len(equiv_known)),
        "assert_equal_equivalence_denominator": len(equiv_known),
        "assertion_type_match_rate": _rate(len(type_matches), len(type_known)),
        "assertion_type_match_denominator": len(type_known),
        "embedding_similarity_status": Status.MEASURED if embedding_measured else Status.UNAVAILABLE,
        "embedding_similarity_mean": (
            sum(r["embedding_cosine_similarity"] for r in embedding_measured) / len(embedding_measured)
            if embedding_measured else None
        ),
        "embedding_similarity_count": len(embedding_measured),
    }


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
_TEST_COMPARISON_CSV_COLUMNS = [
    "project_id", "tool", "variant", "repetition",
    "source_test_name", "source_test_file", "mapped", "mapping_status", "mapping_reason", "mapping_confidence",
    "translated_test_name", "translated_test_file", "test_origin",
    "assertion_count_source", "assertion_count_translated", "assertion_count_match",
    "assert_equal_expected_value_source", "assert_equal_expected_value_translated",
    "assert_equal_expected_value_equivalent", "assert_equal_value_type",
    "assertion_type_source", "assertion_type_translated", "assertion_type_match",
    "embedding_cosine_similarity", "embedding_status", "embedding_reason",
    "loc_source", "loc_translated",
    "method_invocation_count_source", "method_invocation_count_translated",
]
_COMPARISON_FAILURES_CSV_COLUMNS = [
    "variant", "project_id", "tool", "repetition", "workspace_dir", "reason", "detected_at",
]


def _write_csv(rows: list[dict[str, Any]], columns: list[str], path: Path) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    atomic_write_text(path, buf.getvalue())


def write_test_comparisons(rows: list[dict[str, Any]], output_root: Path) -> tuple[Path, Path]:
    output_root = Path(output_root)
    json_path = output_root / "test_comparisons.jsonl"
    csv_path = output_root / "test_comparisons.csv"
    buf = io.StringIO()
    for row in rows:
        buf.write(json.dumps(row, default=str) + "\n")
    atomic_write_text(json_path, buf.getvalue())
    _write_csv(rows, _TEST_COMPARISON_CSV_COLUMNS, csv_path)
    return json_path, csv_path


def write_comparison_failures(failures: list[dict[str, Any]], output_root: Path) -> Path:
    csv_path = Path(output_root) / "test_comparison_failures.csv"
    _write_csv(failures, _COMPARISON_FAILURES_CSV_COLUMNS, csv_path)
    return csv_path


def write_summary(summary: dict[str, Any], output_root: Path) -> Path:
    path = Path(output_root) / "test_comparison_summary.json"
    C.atomic_write_json(path, summary)
    return path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="test_compare.py",
        description="RQ2: map every source developer test to a translated target test; "
                   "write per-test + aggregate comparison metrics.",
    )
    ap.add_argument("--manifest", required=True, help="path to manifest.json (from manifest.py)")
    ap.add_argument("--runs-root", required=True, help="the --out root run.py wrote runs under")
    ap.add_argument("--output-root", required=True, help="where test_comparisons.csv/jsonl are written")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--variant", default="all", help="comma-separated variants, or 'all' (default)")
    ap.add_argument("--project", default=None, help="comma-separated project ids (default: all in manifest)")
    ap.add_argument("--repetitions", type=int, default=None, help="default: [protocol].repetitions")
    ap.add_argument("--embeddings", action="store_true",
                   help="opt-in: attempt real Qwen embedding cosine similarity via sentence-transformers "
                       "if installed. Never enabled by default; never installs the dependency or "
                       "downloads a model on its own.")
    return ap


def _parse_variants(raw: str) -> list[str]:
    if raw == "all":
        return list(C.RUN_VARIANTS)
    variants = [v.strip() for v in raw.split(",") if v.strip()]
    for v in variants:
        if v not in C.RUN_VARIANTS:
            raise ValueError(f"unknown variant {v!r}; choose from {C.RUN_VARIANTS}")
    return variants


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = M.load_experiment_config(args.config)
    manifest = C.read_json(args.manifest)
    variants = _parse_variants(args.variant)
    project_ids = args.project.split(",") if args.project else None
    repetitions = (args.repetitions if args.repetitions is not None
                  else int(cfg.get("protocol", {}).get("repetitions", 1)))
    embedding_fn = compute_embedding_similarity if args.embeddings else None

    rows, failures = compare_all(
        Path(args.runs_root), manifest, variants=variants, project_ids=project_ids,
        repetitions=repetitions, dataset_specs=cfg.get("datasets", {}), embedding_fn=embedding_fn,
    )
    summary = summarize_comparisons(rows)

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    _json_path, csv_path = write_test_comparisons(rows, output_root)
    failures_path = write_comparison_failures(failures, output_root)
    summary_path = write_summary(summary, output_root)

    print(f"[test_compare] {len(rows)} per-test comparison row(s) -> {csv_path}")
    print(f"[test_compare] {len(failures)} unresolved run(s) -> {failures_path}")
    print(f"[test_compare] translation_rate={summary['translation_rate']} -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
