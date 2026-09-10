# Results index

Every package here scores Java → Python translations of AlphaTrans Tier A subjects
against the **same held-out oracle**: AlphaTrans's manually verified Python test
suite, at dataset revision `c1cabf93d41a153de207d6b098e1da7bbd79abab`.

Each package has a `METHOD.md` describing how that experiment was conducted, what
it can support, and what it cannot. **Read the method file before quoting a number.**

## Packages

| Package | Arm | Model | METHOD |
|---|---|---|---|
| `alphatrans-commons-cli-2026-09-03` | CodeWeaver, single subject | `claude-opus-4.8` | [METHOD](alphatrans-commons-cli-2026-09-03/METHOD.md) |
| `alphatrans-sonnet5-med-2026-09-04` | CodeWeaver, four subjects | `claude-sonnet-5` | [METHOD](alphatrans-sonnet5-med-2026-09-04/METHOD.md) |
| `alphatrans-b0-sonnet5-med-2026-09-08` | B0 single-shot, Copilot CLI | `claude-sonnet-5` | [METHOD](alphatrans-b0-sonnet5-med-2026-09-08/METHOD.md) |
| `alphatrans-b0-api-2026-09-09` | B0 via direct API, per-file and whole-repo | `claude-sonnet-5` | [METHOD](alphatrans-b0-api-2026-09-09/METHOD.md) |
| `alphatrans-b0-repair-2026-09-09` | Repair over the B0 API per-file artifact, build-guided and test-guided | `claude-sonnet-5` | [METHOD](alphatrans-b0-repair-2026-09-09/METHOD.md) |
| `crust-b0-2026-09-10` | **CRUST-bench C→Rust**: B0 via CLI, whole-repo and per-file, both repair arms, and CodeWeaver | `claude-sonnet-5` | [METHOD](crust-b0-2026-09-10/METHOD.md) |
| `xcvrd-codeweaver-2026-09-10` | **SONiC xcvrd Python→Rust**: CodeWeaver, correctness arm and a benchmark/optimize arm | `claude-opus-4.8` | [METHOD](xcvrd-codeweaver-2026-09-10/METHOD.md) |

The CRUST package is a **second suite in a different language pair** (C→Rust), not
another AlphaTrans arm. Its oracle is much weaker and was LLM-generated rather than
human-verified. Never place its numbers in a table with the AlphaTrans numbers; see
its `METHOD.md` before quoting anything from it.

The xcvrd package is a **third suite, and the only one whose generation arm was not
test-blind.** Its oracle is one we wrote rather than a benchmark's, and its repair
loop hands the Translator the failing test ids and tells it to read those tests. On
oracle exposure it belongs beside "B0 + test repair" below, never beside the
CodeWeaver column. It is also the only package here that measures a **noise floor**
rather than reporting N=1 points. Read its `METHOD.md` before quoting anything.

Generation is reproduced by `experiments/baselines/campaigns/README.md`, which
records the exact invocation behind each package. Scoring needs no model access:
every package ships a self-contained `reproduction/score.sh`.

## Headline numbers, test-blind arms only (`claude-sonnet-5`)

Every column below was produced without the model seeing the oracle.

| Subject | CodeWeaver | B0 CLI | B0 API per-file | B0 API whole-repo | + build repair |
|---|---:|---:|---:|---:|---:|
| commons-cli | 380 / 381 | 368 / 381 | 110 / 381 | 241 / 381 | 110 / 381 |
| commons-csv | 296 / 298 | error | error | error | error |
| commons-fileupload | 38 / 39 | 37 / 39 | 37 / 39 | 37 / 39 | 37 / 39 |
| commons-validator | 452 / 462 | 381 / 462 | error | 81 / 462 | 382 / 462 |

"error" means the arm produced no scoreable artifact — the suite failed to collect.
Those cells are **not** zero and **not** a pass rate; see the relevant `METHOD.md`.

The "+ build repair" column continues from the B0 API per-file column, so those two
are a before/after pair on one artifact, not two independent samples.

### Test-guided repair — reported separately, never in the table above

| Subject | from B0 API per-file | after test-guided repair | calls |
|---|---:|---:|---:|
| commons-cli | 110 / 381 | 370 / 381 | 3 |
| commons-csv | error | error | 3 |
| commons-fileupload | 37 / 39 | 37 / 39 | 3 |
| commons-validator | error | 403 / 462 | 3 |

This arm read the oracle's failure output. It is an upper bound on what repair can
recover given perfect feedback, **not** a peer of any column above.

## Second suite: CRUST-bench (C→Rust)

Different language pair, different benchmark, much weaker oracle (63 tests across four
subjects). Reported for the mechanisms it isolates, not as scores comparable to the
AlphaTrans table.

| Subject | stubs | B0 CLI | B0 whole-repo | B0 per-file | + build repair | **CodeWeaver** |
|---|---:|---:|---:|---:|---:|---:|
| cset | 0/15 | FAIL(4) | FAIL(4) | FAIL(4) | FAIL(4) | **15/15** |
| c-aces | 0/11 | 11/11 | 11/11 | FAIL(145) | FAIL(145) | **11/11** |
| lambda-calculus-eval | 0/22 | FAIL(3) | 22/22 | FAIL(127) | FAIL(45) | **22/22** |
| inversion_list | 1/15 | 14/15 | 15/15 | 14/15 | 14/15 | **15/15** |

`FAIL(n)` means the crate did not compile, with n `rustc` errors; no tests ran. Rust
gives no partial credit, so that is its own state, not a zero. "stubs" is the negative
control — `inversion_list` has 1 test that passes on unimplemented stubs.

CodeWeaver is the only arm that solves every subject, and the only one that compiles
`cset` at all: every single-shot arm fails it on `casting &T to &mut T is undefined
behavior`, a soundness defect that needs restructuring rather than retranslation.

B0 CLI and B0 whole-repo differ only in transport — both whole-crate, one round, zero
tool calls — yet they disagree on two subjects. With N=1 that is unmeasured
run-to-run variance, not a transport effect, and it is a reason to read any single
cell here cautiously.

**Whole-repo beats per-file decisively here, the reverse of the AlphaTrans result.**
Same mechanism, different dominant term: these crates are small enough that the output
cap never binds, so what remains is cross-module contract disagreement — which per-file
creates and whole-repo avoids. In AlphaTrans the cap dominated instead. Damage tracks
inter-module coupling, not repository size.

Test-guided repair is reported separately in that package's `METHOD.md`; it saw oracle
failure text and does not belong in the table above.

### Denominators here are not cargo's defaults

`cargo` counts a test twice when a file is both an auto-discovered binary and a
declared `[[test]]` target, and a bare `cargo test` also runs agent-written unit tests.
An earlier revision of that package published the raw counts and was wrong (`c-aces`
22 instead of 11, `inversion_list` 30 instead of 15). The oracle now synthesizes its
own manifest so each held-out test is counted exactly once. See its `METHOD.md`.

## Third suite: SONiC xcvrd (Python→Rust)

A production daemon rather than a benchmark subject: ~6,500 lines of Python to
~24,300 lines of Rust, graded by a black-box suite that drives the real supervised
daemon on a virtual switch and asserts on Redis STATE_DB.

| Arm | unit | e2e | note |
|---|---:|---:|---|
| `codeweaver` | 312 / 312 | 103 passed of 104 selected | 1 skipped (environmental), 1 deferred; parity complete, 0 gaps |
| `codeweaver-optimized` | 320 / 320 | 104 / 105 | whole suite, ungated; the 1 failure is flaky (see below) |

**The two e2e denominators are not the same set** — 104 is the cumulative milestone
gate with deferred tests deselected, 105 is the whole suite. They are before/after on
one artifact. Do not difference those fractions.

The optimized arm's single failure (`test_dom_gating`) failed in 14 of the campaign's
20 rounds, **including 7 rounds in which no code changed at all**. An empty change set
cannot cause a regression, so it is reported as flaky rather than as a defect — and
reported rather than filtered.

### The only measured noise floor in this directory

That campaign's second half accepted no changes, so its 10 benchmark rounds are
repeated measurements of one unchanged crate:

| metric | pre | post | change | noise (cv) | real? |
|---|---:|---:|---:|---:|:--:|
| EEPROM reads/cycle | 21,918 | 15,899 | −27.5% | 1.8% | yes |
| idle CPU | 43.4% | 37.0% | −14.7% | 2.9% | yes |
| DOM sweep | 52.9 ms | 55.0 ms | +4.0% | 14.1% | **no** |

The last row is why this matters: as a bare before/after pair it reads as a 4%
regression, and it is nothing — well inside a 14% band. Quote the deltas only with
their cv.

## Rules for combining these numbers

1. **Scoring is uniform, protocols are not.** Every arm is scored the same way:
   independent recomputation, `--no-pipeline-skips` so repair deferrals cannot hide
   failures, fixed environment exclusions retained. What differs between arms is how
   the translation was produced, and that difference is the experiment.

   The `reproduction/oracle.sh` bundled in each package is deliberately **not** the
   same file as `examples/alphatrans/tools/oracle.sh`, and its pinned hash will not
   match. The bundled copy predates the `--no-pipeline-skips` flag: the wrappers get
   the same guarantee structurally, by staging a fresh tree that has no
   `pipeline/skips.json` in it at all, so there is nothing for the flag to suppress.
   Both paths deselect exactly the fixed environment-broken tests and nothing else.

2. **Do not pool arms with different feedback.** Arms differ in what the model was
   allowed to see:

   | Arm | Oracle source | Oracle pass/fail | Compiler / import |
   |---|---|---|---|
   | CodeWeaver | never | **counts only** | yes |
   | B0 (all generation variants) | never | never | never |
   | B0 + build repair | never | never | **yes, diagnostics** |
   | B0 + test repair | never | **full failure output** | yes |
   | xcvrd CodeWeaver | **read by the agent** | **failing test ids + diagnostics** | yes |

   The last row is the only arm that saw oracle failure text. CodeWeaver sees gated
   pass/fail counts at milestone boundaries and never the tests themselves. Keep both
   distinctions visible in any table that mixes them.

   **"Held out" is verified, not assumed.** CodeWeaver runs its agents with
   `--allow-all`, so nothing at the filesystem level prevents them reading an oracle
   that is present. In the CRUST suite an agent did exactly that, twice, before the
   oracle was moved out of the working tree entirely and an access audit was added
   (`examples/crust/tools/oracle_audit.sh`). Published CRUST CodeWeaver runs show zero
   tool calls targeting the oracle. The AlphaTrans example still stores its oracle
   inside the subject directory; its agent logs were not retained, so that arm rests on
   the prompt contract rather than on an audit.

3. **Do not compare across transports without saying so.** The Copilot CLI arm and
   the direct API arm use different clients and different hidden system prompts,
   and the CLI arm was permitted to continue one generation across responses.

4. **Do not place these beside AlphaTrans's or CRUST-bench's published tables.**
   AlphaTrans reports per-fragment statuses and `#GS`; CRUST-bench lets the model
   read and run the test suite. Our oracle is held out from every arm here.

5. **N = 1 per subject.** No repetitions, no variance, anywhere in this directory —
   with one exception: the xcvrd package measures benchmark noise over 10 repeated
   measurements of a fixed crate. That is a floor for its *timings only*; its
   translation arms are still N = 1.

## Cost

Reported per package where it was actually measurable, and omitted where it was
not. CodeWeaver's per-run cost is **unrecoverable**: its role logs are overwritten
per CLI invocation, so no complete usage ledger exists. The direct-API arms report
provider token counts only, with no premium-request or AIU figure inferred from
them.
