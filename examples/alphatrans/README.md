# AlphaTrans example — repository-level Java → Python with a held-out oracle

Run CodeWeaver on an [**AlphaTrans**](https://github.com/Intelligent-CAT-Lab/AlphaTrans)
subject project (FSE 2025, arXiv:[2410.24117](https://arxiv.org/abs/2410.24117)):
translate a real Java repository into Python that conforms to a provided interface
skeleton and passes a **fixed, human-written** Python test suite.

This example uses AlphaTrans as a **data source, not as a pipeline**. We do not run
CodeQL, GraalVM, Maven or their fragment translator — we borrow three assets and
score with plain `pytest`.

## Why this benchmark

| Property | Why it matters |
|---|---|
| **Whole-repository** translation (22–71 modules) | The scoper, milestone loop and parity verifier all have real work to do. |
| **Fixed, human-written oracle** | AlphaTrans's own pipeline *translates the tests itself*; we instead use its **manually verified** suites, so the oracle is not self-authored. |
| **Held out from the agents** | The tests never exist in the working copy (see below), so the headline metric is test-blind. |
| **Runs anywhere** | Pure Python + pytest. No JDK, GraalVM, CodeQL, Maven or Docker. |

## Subjects

Only the four projects with a manually verified translation are usable:

| Project | Interface modules | Oracle tests (golden ceiling, measured) |
|---|---|---|
| `commons-cli` | 22 | **381 passed**, 56 skipped |
| `commons-csv` | 11 | **298 passed**, 13 skipped |
| `commons-fileupload` | 30 | **39 passed** |
| `commons-validator` | 63 | **453 passed** (10 env-broken tests deselected — see below) |

⚠️ **`commons-validator` needs an environment baseline.** Ten currency/date tests are
locale- and timezone-sensitive and fail *even against AlphaTrans's own manually
verified translation*. `setup` runs the golden translation once and records those
node ids to `.oracle-master/baseline_excluded.txt`; every scored run then
`--deselect`s them, so they are charged to the environment and never to CodeWeaver.
With that baseline in place, `commons-validator`'s ceiling is a clean
**453 passed, 10 deselected, exit 0**. (`commons-cli` records 0 exclusions.)

The other six AlphaTrans projects ship only model-generated translations, so they
have no trustworthy fixed oracle and are excluded.

## Prerequisites

1. **Python 3.11+** with `pytest` (`pip install pytest tzdata`).
2. A clone of AlphaTrans (the artifact carries the data we need):
   ```bash
   git clone https://github.com/Intelligent-CAT-Lab/AlphaTrans.git
   # On Windows, long paths are required:
   #   git config --global core.longpaths true
   ```

## Set up a target project

```powershell
./setup.ps1 -Project commons-cli -Dataset C:\path\to\AlphaTrans   # Windows
```
```bash
./setup.sh commons-cli /path/to/AlphaTrans                         # macOS / Linux
```

`setup` materializes three things from the AlphaTrans artifact:

| Generated | From | Role |
|---|---|---|
| `.scaffold/src/main/**` | `data/skeletons/<proj>/src/main` | the **interface**: typed signatures with `pass` bodies |
| `.oracle-master/` | `.../manual_translation/src/test` + `pytest.ini` + `conftest.py` | the **oracle**, plus a `SHA256SUMS.txt` tamper manifest |
| `codeweaver.toml` | `codeweaver.template.toml` | resolved paths |

## Verify the harness before spending anything

```powershell
./tools/oracle.ps1 -Baseline golden     # ceiling -> 381 passed, exit 0
./tools/oracle.ps1 -Baseline skeleton   # floor   -> 380 failed, 1 passed, exit 1
```

Establishing both ends proves the oracle is wired correctly and is not tautological.
(One `commons-cli` test passes against a completely unimplemented skeleton — treat
that as the baseline offset, not as a point scored.)

## Run

```bash
cd ../..    # CodeWeaver repo root
python -m codeweaver check --config examples/alphatrans/codeweaver.toml   # offline, free
python -m codeweaver run   --config examples/alphatrans/codeweaver.toml --app-id alphatrans-commons-cli-001
```

## How the oracle stays hidden

The tests are **never placed in the working copy**. Every scored run
(`tools/oracle.ps1`):

1. **verifies** `.oracle-master` against its SHA256 manifest — a mismatch, missing
   or extra file aborts with `ORACLE-TAMPERED` (exit 3), so an agent editing the
   oracle is a *reported failure*, never a silent pass;
2. builds a **throwaway staging tree** — `src/main` copied from the working copy,
   `src/test` copied from the pristine master;
3. runs `pytest` there with `PYTHONPATH` set to the staging root;
4. deletes the staging tree.

`reference_dirs` deliberately excludes the oracle, and the skeleton's own
`src/test` directory (which holds AlphaTrans's translated-test *skeletons*) is
dropped by `setup` — its method names would leak the oracle's surface.

> `--add-dir` is an access grant, not a read-only enforcement, and agents run under
> `--allow-all`. Restore-then-verify is the only real guarantee.

## Two validation layers

| Layer | Command | Written by |
|---|---|---|
| **1 — fast** | `python -m pytest pipeline/project/tests -q` | the **agents**, freely editable, no bearing on the score |
| **2 — oracle** | `pwsh tools/oracle.ps1 -Gate "{gate}"` | **humans**, fixed, hidden, authoritative |

`build_check` (`tools/build_check.py`) is the Python analogue of "it compiles":
every module under `src/main` must parse *and* import cleanly. Import errors are
exactly what break the oracle run, so this is a fast oracle-free signal.

An **empty gate** (milestone M0, which declares no tests) means *"no oracle
obligation yet"* — the harness returns success rather than running the whole suite,
which would otherwise fail M0 forever and burn its repair budget. Use `-All` to
force the full suite for final scoring.

## Milestone gates are mechanical, not oracle-derived

Gates use a **blind naming convention**: a milestone implementing `src/main/**/Foo.py`
contributes the selector token `FooTest`. The scoper derives these from the interface
skeleton alone — it never inspects the oracle to choose them. A token that matches
nothing selects no tests, and pytest's "no tests collected" (exit 5) is translated to
*no obligation* rather than a failure.

This preserves CodeWeaver's cumulative-gate mechanism while keeping the protocol
test-blind: the gate reveals a naming convention any developer would assume, never
test content.

## How it maps to CodeWeaver

| CodeWeaver concept | AlphaTrans |
|---|---|
| `source_dir` | `java_projects/cleaned_final_projects_decomposed_tests/<proj>/src/main` (read-only) |
| `immutable_input` | `.scaffold/` — the interface skeleton; copied, never edited |
| `working_copy` | `pipeline/project/` — where agents write `src/main/**` bodies |
| `build_check` | `tools/build_check.py` (parse + import) |
| `unit_test` | the agents' own tests under `pipeline/project/tests/` |
| `validate` | `tools/oracle.ps1` — the hidden, human-written suite |
| milestones | auto-generated from the **Java source + interface**, never the tests |
| parity | every Java class has a faithful Python counterpart, no `pass` stubs left |

See `brief.md` for the full contract handed to every agent.

## Notes and caveats

- `codeweaver.toml`, `.scaffold/`, `.oracle-master/` and `pipeline/` are
  **generated/local** and gitignored — only the template, brief, README, setup and
  tools are committed.
- **The subjects are reduced projects**, not upstream Apache Commons: third-party
  libraries were stripped and overloaded methods renamed with numeric suffixes
  (`hasOption1` / `hasOption2`). The skeleton is authoritative about which is which.
- **`commons-validator` needs environment pinning**: `pip install tzdata`, and
  several currency/date tests are locale-sensitive. Pin the locale before treating
  its numbers as comparable.
- **Leakage risk is high** — Apache Commons is certainly in every model's training
  data. Any published result needs an explicit leakage audit.
- This is **not** a head-to-head reproduction of AlphaTrans's Table 2. Their metrics
  are per-fragment counts read out of their CodeQL-derived schema JSON
  (`src/postprocessing/print_results.py`), not a project-level test-pass rate. Any
  comparison must state the differing denominators in the caption.
