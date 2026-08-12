"""manifest.py -- deterministically discover the 118 benchmark projects from an
extracted official-artifact directory tree and emit manifest.json / manifest.csv.

Expected shape (validated, never assumed): 100 CRUST (C->Rust) + 6 Oxidizer
(Go->Rust) + 4 AlphaTrans (Java->Python) + 8 SKEL (Python->JavaScript) = 118.

CALIBRATED against a real, extracted official artifact (verified read-only in
a WSL integration pass; see README "Integration assumptions"): the 118
projects live one level below the extracted ``implementation.zip`` root, at
``data/tool_projects/{crust,oxidizer,alphatrans,skel}/<project>/``.
``resolve_project_root()`` below tries ``--artifact-root`` itself first (so
pointing directly at ``data/tool_projects``, or any layout where the dataset
dirs sit at the root, keeps working unchanged), then descends into each of
``experiment.toml``'s ``[artifact].project_root_subdir_candidates`` (a
relative, artifact-structure fact, never a machine-specific absolute path)
looking for the first level containing at least one dataset's
``dir_candidates``. Discovery below that root is still **adapter-based**:
``experiment.toml``'s ``[datasets.<tool>]`` tables list plausible directory
names (``dir_candidates``, matched case-insensitively) and per-project
sub-path candidates for the source tree, the oracle/tests tree, the
CRUST-only interface/test scaffold, and (if the artifact ships one) an
evaluator-only ground-truth target tree. Use ``--probe`` against any
extracted artifact to print its actual top-level structure and correct
``experiment.toml`` if directory names ever differ (e.g. a future artifact
version) -- that is a config edit, never a code change.

Verified per-dataset quirks (informational, not code branches -- discovery
already handles these gracefully since ``oracle_rel_path`` is optional and
``source_rel_path`` is always walked recursively):
- CRUST: developer tests are NESTED inside the source dir itself
  (``c/test/*_spec.c``, sibling of ``c/src/``), not a separate oracle
  directory -- ``oracle_rel_path`` is expected to be null; the tests are
  still included (and counted) because they are part of ``c/``, which is
  copied/counted wholesale as ``source_rel_path``.
- Oxidizer: same pattern for Go's own convention (``go/*_test.go`` alongside
  ``go/*.go``, no separate oracle dir).
- AlphaTrans: developer tests live at ``java/src/test/`` (nested in the
  source dir, same pattern); the ``python/`` ground-truth tree ships
  ``conftest.py``/``pytest.ini`` but no test files of its own -- those are
  expected to be produced by translation, not pre-supplied.
- SKEL: projects are single files (``python/source.py`` ->
  ``javascript/translated.js``) with no separate oracle *directory* --
  developer tests are embedded directly inside ``source.py`` itself as
  ``test_*``-prefixed functions co-located with the algorithm (e.g.
  ``test_put``/``test_search`` in the ``bst`` project), one file-granularity
  step further than CRUST/Oxidizer/AlphaTrans's "tests nested in the source
  dir" pattern. They are still counted/copied correctly because
  ``source_rel_path`` is the whole ``python/`` dir. The ground-truth
  ``javascript/translated.js`` is solution-only (verified: no test-shaped
  functions) -- CodeWeaver translating ``source.py``'s embedded tests into a
  new JS test file is exactly the RQ2 "source test -> translated test"
  mapping this dataset exercises.

LoC / test-count / function-count are computed with small, explicitly
heuristic, per-language regexes (documented in this module, not a real
parser). They are good enough for scale/coverage reporting and are homogeneous
across projects, but are not a substitute for the paper's own counts -- see
``PAPER_REFERENCE_TOTALS`` in common.py for those, kept clearly separate. Note
that for CRUST/Oxidizer/AlphaTrans, ``loc_source``/``test_count_source`` are
computed over the whole recursively-walked ``source_rel_path`` tree, which
(per the nesting quirk above) includes the nested developer-test files --
this heuristic total is therefore "source + its own nested tests" LoC, not a
tests-excluded figure; treat it as a scale indicator, not a precise match to
the paper's own LoC methodology.
"""
from __future__ import annotations

import argparse
import csv
import re
import tomllib
from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent.common import atomic_write_json, atomic_write_text, utcnow_iso

SCHEMA_VERSION = 1

PROJECT_DIR_IGNORE = {
    ".git", ".github", ".svn", ".hg", "__pycache__", ".vs", ".idea", ".vscode",
    "node_modules", "target", "build", "dist", ".pytest_cache", ".mypy_cache",
}

# --------------------------------------------------------------------------- #
# Heuristic, per-extension regexes for LoC/test/function counting. Documented
# as heuristics: physical non-blank-line LoC, and regex-based test/function
# detection (not a real parser for any of the four languages involved).
# --------------------------------------------------------------------------- #
FUNCTION_DEF_PATTERNS: dict[str, re.Pattern[str]] = {
    # C permits the return type and function name on separate lines (a style
    # used throughout CRUST, e.g. ``size_t\nleftpad(...)``). Require at least
    # two identifier-like tokens before ``(`` so control-flow statements are
    # not mistaken for definitions, while allowing horizontal/newline space.
    ".c": re.compile(
        r"^(?:[A-Za-z_]\w*(?:[ \t]+|\s*\*+[ \t]*|\s*\n[ \t]*))+"
        r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
        re.MULTILINE,
    ),
    ".h": re.compile(
        r"^(?:[A-Za-z_]\w*(?:[ \t]+|\s*\*+[ \t]*|\s*\n[ \t]*))+"
        r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
        re.MULTILINE,
    ),
    ".go": re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(", re.MULTILINE),
    ".java": re.compile(
        r"\b(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
        r"[\w<>\[\],\s]+?\s(\w+)\s*\([^;{}]*\)\s*\{",
        re.MULTILINE,
    ),
    ".py": re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE),
    ".js": re.compile(r"^\s*function\s+(\w+)\s*\(", re.MULTILINE),
    # Rust is never a *source* language in the paper's protocol (only a
    # translation *target*, for CRUST/Oxidizer) -- included here so collect.py
    # can reuse this exact module's counting heuristics/functions for the
    # produced *target* tree too, instead of duplicating pattern definitions.
    ".rs": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),
}

TEST_DEF_PATTERNS: dict[str, re.Pattern[str]] = {
    ".c": re.compile(r"^(?:void|int)\s+(test_\w*)\s*\(", re.MULTILINE | re.IGNORECASE),
    ".h": re.compile(r"^(?:void|int)\s+(test_\w*)\s*\(", re.MULTILINE | re.IGNORECASE),
    ".go": re.compile(r"^func\s+(Test\w*)\s*\(", re.MULTILINE),
    ".java": re.compile(r"@Test\b"),
    ".py": re.compile(r"^\s*def\s+(test_\w*)\s*\(", re.MULTILINE),
    ".js": re.compile(r"\b(?:it|test)\s*\(\s*['\"]"),
    # See note above -- Rust is target-only; kept here for collect.py's reuse.
    ".rs": re.compile(r"#\[test\]"),
}



def load_experiment_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else C.DEFAULT_EXPERIMENT_CONFIG
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)


def dataset_specs(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    cfg = cfg if cfg is not None else load_experiment_config()
    specs = cfg.get("datasets", {})
    if not specs:
        raise RuntimeError("experiment.toml has no [datasets.*] tables")
    return specs


# --------------------------------------------------------------------------- #
# Directory resolution
# --------------------------------------------------------------------------- #
def _find_case_insensitive(parent: Path, candidates: list[str]) -> Path | None:
    if not parent.is_dir():
        return None
    try:
        children = {p.name.lower(): p for p in parent.iterdir() if p.is_dir()}
    except OSError:
        return None
    for cand in candidates:
        hit = children.get(cand.lower())
        if hit is not None:
            return hit
    return None


def discover_tool_dir(artifact_root: Path, spec: dict[str, Any]) -> Path | None:
    return _find_case_insensitive(artifact_root, spec.get("dir_candidates", []))


def discover_project_dirs(tool_dir: Path) -> list[Path]:
    if not tool_dir.is_dir():
        return []
    out = []
    for p in sorted(tool_dir.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and p.name not in PROJECT_DIR_IGNORE and not p.name.startswith("."):
            out.append(p)
    return out


def _resolve_subpath(project_dir: Path, candidates: list[str]) -> Path | None:
    if not candidates:
        return None
    hit = _find_case_insensitive(project_dir, candidates)
    return hit


# --------------------------------------------------------------------------- #
# Counting heuristics
# --------------------------------------------------------------------------- #
def iter_source_files(root: Path, extensions: list[str]):
    if not root.exists():
        return
    exts = {e.lower() for e in extensions}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def count_loc(root: Path, extensions: list[str]) -> int | None:
    if not root.exists():
        return None
    total = 0
    seen_any = False
    for f in iter_source_files(root, extensions):
        seen_any = True
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += sum(1 for line in text.splitlines() if line.strip())
    return total if seen_any else 0


def count_pattern_matches(root: Path, extensions: list[str],
                          patterns: dict[str, re.Pattern[str]]) -> int | None:
    if not root.exists():
        return None
    total = 0
    for f in iter_source_files(root, extensions):
        pattern = patterns.get(f.suffix.lower())
        if pattern is None:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += len(pattern.findall(text))
    return total


def count_tests(root: Path, extensions: list[str]) -> int | None:
    return count_pattern_matches(root, extensions, TEST_DEF_PATTERNS)


def count_functions(root: Path, extensions: list[str]) -> int | None:
    return count_pattern_matches(root, extensions, FUNCTION_DEF_PATTERNS)


# --------------------------------------------------------------------------- #
# Row construction
# --------------------------------------------------------------------------- #
def _rel(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def build_project_row(tool_key: str, spec: dict[str, Any], project_dir: Path,
                      artifact_root: Path) -> dict[str, Any]:
    source_root = _resolve_subpath(project_dir, spec.get("source_subdir_candidates", [])) or project_dir
    oracle_root = _resolve_subpath(project_dir, spec.get("oracle_subdir_candidates", []))
    scaffold_root = _resolve_subpath(project_dir, spec.get("scaffold_subdir_candidates", []))
    ground_truth_root = _resolve_subpath(project_dir, spec.get("ground_truth_subdir_candidates", []))

    extensions = spec.get("source_extensions", [])
    notes = ""
    status = "ok"
    if not source_root.exists():
        status, notes = "missing_source", f"no source root resolved under {project_dir}"

    source_test_count = count_tests(source_root, extensions)
    # CRUST's authoritative unit tests live in the supplied Rust scaffold.
    # Counting those #[test] entries is both more faithful and more robust
    # than guessing C harness conventions such as a single main() containing
    # many assert() calls.
    if tool_key == "crust" and scaffold_root is not None:
        scaffold_test_count = count_tests(scaffold_root, [".rs"])
        if scaffold_test_count is not None:
            source_test_count = scaffold_test_count

    return {
        "id": f"{tool_key}__{project_dir.name}",
        "tool": tool_key,
        "project": project_dir.name,
        "source_language": spec.get("source_language", ""),
        "target_language": spec.get("target_language", ""),
        "source_rel_path": _rel(source_root, artifact_root),
        "oracle_rel_path": _rel(oracle_root, artifact_root),
        "scaffold_rel_path": _rel(scaffold_root, artifact_root),
        "ground_truth_target_rel_path": _rel(ground_truth_root, artifact_root),
        "loc_source": count_loc(source_root, extensions),
        "test_count_source": source_test_count,
        "function_count_source": count_functions(source_root, extensions),
        "status": status,
        "notes": notes,
        "discovered_at": utcnow_iso(),
    }


# --------------------------------------------------------------------------- #
# Top-level discovery
# --------------------------------------------------------------------------- #
def discover_tool(tool_key: str, spec: dict[str, Any], search_root: Path,
                  rel_root: Path) -> tuple[Path | None, list[dict[str, Any]]]:
    """``search_root`` is where dataset dirs are actually looked for (the
    resolved effective project root); ``rel_root`` is what every discovered
    path is recorded relative to (always the original ``--artifact-root``,
    so manifest.json stays interpretable/portable regardless of how deep the
    real dataset dirs turned out to be nested)."""
    tool_dir = discover_tool_dir(search_root, spec)
    if tool_dir is None:
        return None, []
    rows = [build_project_row(tool_key, spec, pd, rel_root) for pd in discover_project_dirs(tool_dir)]
    return tool_dir, rows


def resolve_project_root(artifact_root: Path, specs: dict[str, dict[str, Any]],
                         subdir_candidates: list[str] | None = None) -> Path:
    """Finds the directory that directly contains the dataset dirs (the ones
    named by each dataset's ``dir_candidates``, e.g. ``crust/``). Some
    official-artifact layouts nest the 118 benchmark projects below the
    extracted archive root (verified: ``data/tool_projects/{crust,oxidizer,
    alphatrans,skel}`` inside the real ``implementation.zip``); others may
    ship them directly at the root. Tries ``artifact_root`` itself first
    (the common/backward-compatible case), then each relative entry in
    ``subdir_candidates`` in order, returning the first location where at
    least one dataset resolves. Falls back to ``artifact_root`` unchanged if
    none match -- callers then see the ordinary "0 discovered" per-dataset
    result, never a fabricated location."""
    for candidate in [""] + list(subdir_candidates or []):
        root = (artifact_root / candidate) if candidate else artifact_root
        if any(discover_tool_dir(root, spec) is not None for spec in specs.values()):
            return root
    return artifact_root


def build_manifest(artifact_root: str | Path, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact_root = Path(artifact_root)
    cfg = cfg if cfg is not None else load_experiment_config()
    specs = dataset_specs(cfg)
    project_root_candidates = cfg.get("artifact", {}).get("project_root_subdir_candidates", [])
    effective_root = resolve_project_root(artifact_root, specs, project_root_candidates)

    projects: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    tool_dirs: dict[str, str | None] = {}
    for tool_key, spec in specs.items():
        tool_dir, rows = discover_tool(tool_key, spec, effective_root, artifact_root)
        tool_dirs[tool_key] = str(tool_dir) if tool_dir else None
        counts[tool_key] = len(rows)
        projects.extend(rows)

    expected_counts = {k: v.get("expected_count") for k, v in specs.items()}
    counts_match = counts == expected_counts
    total = sum(counts.values())
    expected_total = sum(v for v in expected_counts.values() if v is not None)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utcnow_iso(),
        "artifact_root": str(artifact_root),
        "effective_project_root": str(effective_root),
        "tool_dirs": tool_dirs,
        "counts": counts,
        "expected_counts": expected_counts,
        "total": total,
        "expected_total": expected_total,
        "counts_match_expected": counts_match and total == expected_total,
        "projects": projects,
    }


def validate_manifest_counts(manifest: dict[str, Any]) -> list[str]:
    """Return a list of human-readable mismatch descriptions (empty == the
    exact 100/6/4/8/118 protocol counts were discovered)."""
    errors = []
    for tool, expected in manifest["expected_counts"].items():
        actual = manifest["counts"].get(tool, 0)
        if expected is not None and actual != expected:
            errors.append(f"{tool}: expected {expected} projects, discovered {actual}")
    if manifest["total"] != manifest["expected_total"]:
        errors.append(f"total: expected {manifest['expected_total']} projects, discovered {manifest['total']}")
    return errors


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
_CSV_COLUMNS = [
    "id", "tool", "project", "source_language", "target_language",
    "source_rel_path", "oracle_rel_path", "scaffold_rel_path", "ground_truth_target_rel_path",
    "loc_source", "test_count_source", "function_count_source", "status", "notes", "discovered_at",
]


def write_manifest(manifest: dict[str, Any], output_root: str | Path) -> tuple[Path, Path]:
    output_root = Path(output_root)
    json_path = output_root / "manifest.json"
    csv_path = output_root / "manifest.csv"
    atomic_write_json(json_path, manifest)

    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in manifest["projects"]:
        writer.writerow(row)
    atomic_write_text(csv_path, buf.getvalue())
    return json_path, csv_path


# --------------------------------------------------------------------------- #
# Probe mode: print the artifact's real top-level structure for calibration
# --------------------------------------------------------------------------- #
def probe_tree(artifact_root: str | Path, depth: int = 2) -> list[str]:
    artifact_root = Path(artifact_root)
    lines: list[str] = []

    def _walk(d: Path, prefix: str, level: int) -> None:
        if level > depth or not d.is_dir():
            return
        try:
            children = sorted(d.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as e:
            lines.append(f"{prefix}<error: {e}>")
            return
        for child in children:
            marker = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{child.name}{marker}")
            if child.is_dir() and level < depth:
                _walk(child, prefix + "  ", level + 1)

    lines.append(f"{artifact_root}/")
    _walk(artifact_root, "  ", 1)
    return lines


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="manifest.py",
        description="Deterministically discover the 118 ReCodeAgent benchmark projects "
                    "(100 CRUST + 6 Oxidizer + 4 AlphaTrans + 8 SKEL) and emit manifest.json/csv.",
    )
    ap.add_argument("--artifact-root", required=True, help="extracted official-artifact directory")
    ap.add_argument("--output-root", default=None, help="where to write manifest.json/csv (default: --artifact-root)")
    ap.add_argument("--config", default=None, help="experiment.toml path (default: bundled one)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="do not fail the CLI if discovered counts != expected 100/6/4/8/118")
    ap.add_argument("--probe", action="store_true",
                    help="print the artifact root's top-level directory structure and exit "
                         "(use this to calibrate experiment.toml's [datasets.*].dir_candidates)")
    ap.add_argument("--probe-depth", type=int, default=2)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.probe:
        for line in probe_tree(args.artifact_root, depth=args.probe_depth):
            print(line)
        return 0

    cfg = load_experiment_config(args.config)
    manifest = build_manifest(args.artifact_root, cfg=cfg)
    errors = validate_manifest_counts(manifest)
    output_root = Path(args.output_root) if args.output_root else Path(args.artifact_root)
    output_root.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = write_manifest(manifest, output_root)

    if manifest["effective_project_root"] != manifest["artifact_root"]:
        print(f"[manifest] resolved dataset root at {manifest['effective_project_root']} "
             f"(one or more levels below --artifact-root {manifest['artifact_root']})")

    print(f"[manifest] discovered {manifest['total']} projects (expected {manifest['expected_total']}): "
         f"{manifest['counts']}")
    print(f"[manifest] wrote {json_path}")
    print(f"[manifest] wrote {csv_path}")
    if errors:
        for e in errors:
            print(f"[manifest] COUNT MISMATCH: {e}")
        if not args.allow_partial:
            print("[manifest] failing (pass --allow-partial to proceed anyway with a partial/miscounted set)")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
