# Method — Iterative repair over the B0 API artifact

One-line summary for a report: **Three build-guided API calls, with no sight of any
test, turned two unscoreable translations into scoreable ones; test-guided repair
went further where the failure was invisible to a compiler-analogue check, and did
nothing at all on one subject.**

## Question this arm answers

CRUST-bench reports transpilation followed by two separate repair settings. This
package reproduces that split on our subjects, so we can ask:

1. How far does repair get when its only feedback is "does it parse and import" —
   i.e. still **test-blind**, still comparable to the generation arms?
2. How much further does it get when allowed to read the test failures — a setting
   that is **explicitly not test-blind**?

## What is being repaired

Both arms start from the **same frozen artifact**: the per-file B0 API translation
published in `results/alphatrans-b0-api-2026-09-09`. That artifact is copied, never
modified. Neither arm regenerates anything from the Java source.

| Subject | Starting point |
|---|---|
| commons-cli | 110 passed, 271 failed |
| commons-csv | collection failure — 1 passed, 6 failed, 19 errors |
| commons-fileupload | 37 passed, 2 failed |
| commons-validator | 277 passed, 85 failed, 8 errors |

## The two arms

| | `build` | `test` |
|---|---|---|
| Feedback | `build_check` output only: which modules fail to parse or import, and why | The oracle's own failure output |
| Sees test source | never | never |
| Sees test results | **never** | **yes** |
| Test-blind | **yes** | **no** |
| CRUST-bench analogue | transpile + compiler-guided repair | `repair_tests.py` |

`build_check` is the project's existing compiler analogue: it parses every module,
then imports it with the working copy on `sys.path`. It is the same signal
CodeWeaver's own pipeline uses, invoked unmodified.

## Loop mechanics

Each iteration is **one API request** carrying the current project source plus the
current diagnostics. Iterations share no conversation state.

| Setting | Value |
|---|---|
| Model | `claude-sonnet-5`, `reasoning_effort: medium`, streaming |
| `max_tokens` | 64,000 |
| Iterations | 3 maximum per run |
| Retries | none |
| Transport | the same loopback proxy as the generation arm |

Guards, all enforced and logged: writes are confined to modules that already exist
under `src/main`; attempts to touch `src/test`, invent new modules, or apply
source that does not parse are rejected and recorded. The loop stops early only
when the signal is clean or an iteration produces nothing applicable.

**The final iteration is kept, not the best-scoring one**, following CRUST-bench.
Per-iteration trajectories are in `report/scorecard.json` so regressions stay
visible rather than being hidden by cherry-picking.

> An earlier version of this loop gated on whether a coarse metric improved. On
> `commons-csv` that discarded a *correct* fix: iteration 1 resolved all four
> `NameError`s and immediately exposed the next-layer `TypeError`, leaving the
> module count flat, so the loop reverted it and stopped after one call. Cascading
> import errors do this routinely. The gating was removed before the published run.

## Result

| Subject | Start | `build` | calls | `test` | calls |
|---|---|---|---:|---|---:|
| commons-cli | 110/381 | 110/381 | **0** | **370/381** | 3 |
| commons-csv | error | 185 passed, 1 error | 2 | 189 passed, 1 error | 3 |
| commons-fileupload | 37/39 | 37/39 | **0** | 37/39 | 3 |
| commons-validator | 277 + 8 errors | **382/462** clean | 1 | **403/462** clean | 3 |

Build arm: **3 API calls total**. Test arm: **12**.

## Reading these numbers

**The two zero-call runs are correct, not failures.** commons-cli and
commons-fileupload already had every module parsing and importing, so a
build-guided arm has nothing to act on and spends nothing.

**commons-cli is the sharpest result here.** Build-guided repair could do nothing;
test-guided reached 370/381. Its dominant failure — 243 tests — is
`CommandLine.addOption` versus the skeleton's `_addOption`, an `AttributeError`
raised at **runtime**. A parse/import check structurally cannot see it. In a
statically typed target this would be a compile error; in Python it is not. That
is a genuine limit of compiler-guided repair on a dynamically typed language, and
it is why CRUST-bench's compiler-guided setting is not directly transferable here.

**commons-validator is the strongest case for the cheap arm.** One build-guided
call cleared all 8 collection errors and produced the subject's first clean
full-suite rate, 382/462 — while remaining test-blind, and therefore still
comparable to the generation arms.

**Repair is not universally effective.** commons-fileupload survived three
test-guided iterations with five files changed and did not move at all.

**commons-csv is still not a clean rate in either arm.** One collection error
remains, so its counts stay errors, not pass rates.

## What this package cannot support

- **N = 1 per run.** No repetitions, no variance.
- **The `test` arm must never be tabulated beside a test-blind arm** without
  stating the difference. It read the oracle's failure output.
- The `build` arm **is** comparable to the test-blind generation arms, because its
  only feedback is parse/import diagnostics.
- Even with 12 test-guided calls and full oracle visibility, no repaired arm
  reaches CodeWeaver on any subject.
- Cost is provider-reported tokens only; no premium-request or AIU figure is
  inferred.

## Contents

```
data/<subject>/<arm>/project/        repaired Python source
data/<subject>/<arm>/metadata.json   per-iteration trajectory, guards, usage
data/<subject>/<arm>/iteration-NN-signal.txt   the exact feedback each iteration saw
data/<subject>/<arm>/api-audit/      per-call audit records
report/scorecard.json                machine-readable results and caveats
```

Model responses and raw request/response streams are retained privately and not
redistributed; their hashes are in `metadata/publication-provenance.json`.

## Reproducing

`reproduction/score.sh <subject> <build|test>` re-scores a frozen repaired tree.
Scoring needs no API access or model calls.
