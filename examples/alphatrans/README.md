# AlphaTrans example — repository-level Java → Python with a held-out oracle

Run CodeWeaver on the [**AlphaTrans**](https://github.com/Intelligent-CAT-Lab/AlphaTrans)
subject projects (FSE 2025, arXiv:[2410.24117](https://arxiv.org/abs/2410.24117)):
translate a real Java repository into Python that conforms to a provided interface
skeleton and passes a **fixed, human-written** Python test suite.

This example uses AlphaTrans as a **data source, not as a pipeline**. We do not run
CodeQL, GraalVM, Maven or their fragment translator — we borrow three assets per
subject and score with plain `pytest`.

## Why this benchmark

| Property | Why it matters |
|---|---|
| **Whole-repository** translation (11–63 modules) | The scoper, milestone loop and parity verifier all have real work to do. |
| **Fixed, human-written oracle** | AlphaTrans's own pipeline *translates the tests itself*; we instead use its **manually verified** suites, so the oracle is not self-authored. |
| **Held out from the agents** | The tests never exist in the working copy (see below), so the headline metric is test-blind. |
| **Runs anywhere** | Pure Python + pytest. No JDK, GraalVM, CodeQL, Maven or Docker. |

## Subjects

| Project | Java files | Interface modules | Oracle ceiling (measured) |
|---|---|---|---|
| `commons-cli` | 23 | 22 | **381 passed**, 56 skipped |
| `commons-csv` | 12 | 11 | **298 passed**, 13 skipped |
| `commons-fileupload` | 36 | 30 | **39 passed** |
| `commons-validator` | 63 | 63 | **462 passed**, 1 skipped |

The "ceiling" is AlphaTrans's own manually verified translation scored through *this*
harness — the practical upper bound for any system on this setup.

### Why only four projects

AlphaTrans ships **ten** Java subjects, but only these four carry a
`manually_verified_translations/<project>/` directory. For the other six
(`JavaFastPFOR`, `commons-codec`, `commons-exec`, `commons-graph`, `commons-pool`,
`jansi`) the only Python that exists is:

- **test *skeletons*** under `data/skeletons/<p>/src/test` — method signatures with
  `pass` bodies and essentially no assertions (`commons-codec`: 14 asserts across
  4,204 `pass` bodies, versus 655 asserts in `commons-cli`'s manual suite); and
- **model-generated translations** under `data/schemas_decomposed_tests/translations/`
  — `.json` fragment schemas produced by DeepSeek/GPT-4o, i.e. *system output*, not
  ground truth.

Using either as an oracle would be circular: we would be grading a translation
against tests that a model wrote. **The four-project limit is a property of the
AlphaTrans artifact, not a choice.**

## Prerequisites

1. **Python 3.11+** with `pytest` and `tzdata`.
2. **A full locale set** — several `commons-validator` tests exercise German/UK
   locales. On a minimal Linux image only 4 locales exist and **40 tests fail even
   against the golden translation**; installing them recovers all but one:
   ```bash
   sudo apt-get install -y locales-all     # 4 locales -> 511; validator ceiling 415 -> 462
   ```
3. A clone of AlphaTrans (the artifact carries the data we need):
   ```bash
   git clone https://github.com/Intelligent-CAT-Lab/AlphaTrans.git
   # On Windows, long paths are required:  git config --global core.longpaths true
   ```

## Set up

```powershell
./setup.ps1 -All -Dataset C:\path\to\AlphaTrans      # Windows: all four subjects
./setup.ps1 -Project commons-cli                     # or just one
```
```bash
./setup.sh --all /path/to/AlphaTrans                 # macOS / Linux
./setup.sh commons-cli /path/to/AlphaTrans
```

Each subject is materialized **in its own directory**, so a campaign over several
projects never clobbers a previous subject's artifacts:

```
subjects/<project>/
  .scaffold/          interface skeleton: typed signatures, `pass` bodies
  .oracle-master/     pristine human-written tests + pytest harness
                        + SHA256SUMS.txt        (tamper manifest)
                        + baseline_excluded.txt (environment-broken tests)
  codeweaver.toml     generated; [paths].root = this dir = the agents' cwd
  pipeline/           run artifacts (created by the run)
```

`setup` also records the **environment-broken baseline**: it scores AlphaTrans's own
golden translation once, and any test that fails *there* is deselected from every
subsequent run. Those tests measure the environment (locale, timezone, platform),
not the translation under test.

## Verify before spending anything

```bash
bash tools/smoke_all.sh          # every subject, offline, free
```

Per subject this checks: config loads, the **ceiling** (golden passes), the **floor**
(unimplemented skeleton fails), **gate resolution**, **tamper detection** (exit 3),
and `build_check`; then exercises the whole Burr graph once against mock agents.
Expect **25 passed, 0 failed** with all four subjects materialized.

## Run

```bash
cd ../..    # CodeWeaver repo root
python -m codeweaver check --config examples/alphatrans/subjects/commons-cli/codeweaver.toml
python -m codeweaver run   --config examples/alphatrans/subjects/commons-cli/codeweaver.toml \
                           --app-id alphatrans-commons-cli-001
```

Progress (works whether or not the Burr tracker was enabled):

```powershell
pwsh tools/status.ps1 -All
pwsh tools/status.ps1 -Project commons-cli -Watch
```

Final independent score:

```bash
bash tools/oracle.sh --project commons-cli --all
```

## How the oracle stays hidden

The tests are **never placed in the working copy**. Every scored run:

1. **verifies** `.oracle-master` against its SHA256 manifest — a mismatch, missing or
   extra file aborts with `ORACLE-TAMPERED` (exit 3), so an agent editing the oracle
   is a *reported failure*, never a silent pass;
2. builds a **throwaway staging tree** — `src/main` from the working copy,
   `src/test` from the pristine master;
3. runs `pytest` there with `PYTHONPATH` set to the staging root;
4. deletes the staging tree.

`reference_dirs` deliberately excludes the oracle, and the skeleton's own `src/test`
directory (AlphaTrans's translated-test *skeletons*) is dropped by `setup` — its
method names would leak the oracle's surface.

> `--add-dir` is an access grant, not a read-only enforcement, and agents run under
> `--allow-all`. Restore-then-verify is the only real guarantee.

## Milestone gates are mechanical, not oracle-derived

A milestone implementing `src/main/**/Foo.py` contributes the selector token
`FooTest`. The scoper derives these from the interface skeleton alone — it never
inspects the oracle to choose them.

The harness resolves each token to an **exact oracle test file**. It deliberately
does *not* use `pytest -k`, whose **substring** matching would let `OptionTest` also
select `ArgumentIsOptionTest` and `PatternOptionBuilderTest` — dragging a later
milestone's tests into an earlier gate and failing it for work it was never asked to
do. (That bug cost a full run before it was found.)

A token matching nothing, and pytest's "no tests collected" (exit 5), are both
translated to *no obligation* rather than a failure — as is M0's empty gate.

## Two validation layers

| Layer | Command | Written by |
|---|---|---|
| **1 — fast** | `python -m pytest pipeline/project/tests -q` | the **agents**, freely editable, no bearing on the score |
| **2 — oracle** | `tools/oracle.{ps1,sh} --project <p> --gate "{gate}"` | **humans**, fixed, hidden, authoritative |

`build_check` (`tools/build_check.py`) is the Python analogue of "it compiles": every
module under `src/main` must parse *and* import cleanly. Import errors are exactly
what break the oracle run, so this is a fast oracle-free signal.

## How it maps to CodeWeaver

| CodeWeaver concept | AlphaTrans |
|---|---|
| `source_dir` | `java_projects/cleaned_final_projects_decomposed_tests/<p>/src/main` (read-only) |
| `immutable_input` | `.scaffold/` — the interface skeleton; copied, never edited |
| `working_copy` | `pipeline/project/` — where agents write `src/main/**` bodies |
| `build_check` | `tools/build_check.py` (parse + import) |
| `unit_test` | the agents' own tests under `pipeline/project/tests/` |
| `validate` | `tools/oracle.*` — the hidden, human-written suite |
| milestones | auto-generated from the **Java source + interface**, never the tests |
| parity | every Java class has a faithful Python counterpart, no `pass` stubs left |

See `brief.md` for the full contract handed to every agent.

## Notes and caveats

- `subjects/` is **generated/local** and gitignored — only the template, brief,
  README, setup and tools are committed.
- **The subjects are reduced projects**, not upstream Apache Commons: third-party
  libraries were stripped and overloaded methods renamed with numeric suffixes
  (`hasOption1` / `hasOption2`). The skeleton is authoritative about which is which.
- **Leakage risk is high** — Apache Commons is certainly in every model's training
  data. Any published result needs an explicit leakage audit.
- **The floors are not zero.** `commons-cli` scores 1, `commons-fileupload` 2,
  `commons-validator` 47 against a completely unimplemented skeleton (tests that only
  assert on constructors, constants or exception types). Treat these as baseline
  offsets, not as points scored.
- **The deprecated parsers are weakly covered.** In `commons-cli`, `BasicParserTest`
  (26), `GnuParserTest` (21) and `PosixParserTest` (9) are entirely
  `@pytest.mark.skip` with empty bodies — inherited from `@Ignore` in upstream Apache.
  Those 56 skips are identical in every configuration (golden, CodeWeaver, skeleton)
  and are excluded from the denominator, but it does mean defects in
  `BasicParser`/`GnuParser`/`PosixParser` are only caught indirectly via
  `ParserTestCase`.
- This is **not** a head-to-head reproduction of AlphaTrans's Table 2. Their metrics
  are per-fragment counts read out of their CodeQL-derived schema JSON
  (`src/postprocessing/print_results.py`), not a project-level test-pass rate. Any
  comparison must state the differing denominators in the caption.
