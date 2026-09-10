# METHOD — xcvrd Python→Rust, CodeWeaver, with a benchmark/optimize extension

**Read this before quoting any number from this package.**

This package is different in kind from the others in `results/`. Those score
translations of benchmark subjects against a benchmark's held-out test suite. This
one records a translation of a **production daemon** against **an oracle we wrote
ourselves**, and its generation arm was **not test-blind**. Both differences change
what the numbers mean.

## Subject

`sonic-xcvrd`, the SONiC transceiver daemon: ~6,500 lines of Python that polls
optical modules over a platform API and publishes their state to a Redis STATE_DB.
It is a long-running supervised daemon with hardware I/O, not a library.

Output: ~24,300 lines of Rust across two crates — the daemon, plus a PyO3 bridge to
the existing Python `sonic_platform` plugin. The CMIS/SFF decode stack was
deliberately **not** translated; it stays in Python behind the bridge. So this is a
port of the daemon's control logic, not of everything the daemon depends on.

## Two arms, one artifact

| Arm | What it is |
|---|---|
| `codeweaver` | the pipeline run to correctness: `analyze → scope → plan → (translate ⇄ validate)×milestone → parity_verify` |
| `codeweaver-optimized` | continues from that crate: `benchmark ⇄ optimize` rounds, then one full-suite conformance milestone |

They are a **before/after pair on one artifact**, not two independent samples. The
second arm's crate is the first arm's crate with four accepted performance changes
applied.

## The oracle

`xcvrd-tests`: 41 test modules that drive the real supervised daemon on a SONiC KVM
testbed against an emulated transceiver plant, and assert on what reaches STATE_DB.
It never imports the daemon, so the same suite grades the Python and Rust
implementations identically — that independence is what makes it usable as a verdict.

Two things it is not:

- **Not a benchmark's suite.** We wrote it. There is no external party that fixed it
  in advance, and it was developed alongside the Python daemon it characterises. It
  is a strong oracle for *behavioural equivalence with the Python daemon*; it is not
  a neutral third-party yardstick.
- **Not held out from the agents.** See below. This is the most important limitation
  in this package.

## ⚠ This arm is test-INFORMED, not test-blind

`results/README.md` describes CodeWeaver's arm elsewhere in this directory as seeing
**"counts only"** — gated pass/fail at milestone boundaries, never the tests. **That
description does not hold for this run.** In this pipeline:

1. The Validator writes `report.json` containing, per failure, the **pytest node id**
   and structured repair guidance derived from the run's output.
2. The Translator is invoked in repair mode with that failure list **inlined into its
   prompt**, and is explicitly instructed to *"re-read the failing tests to see what
   behaviour and STATE_DB fields they require."*
3. Every agent runs with read access to the suite directory.

So the generation loop saw which named tests failed, why, and was told to read them.
That is a legitimate protocol — it is how a human developer works, and the agents
still never *edit* the oracle — but it is **not** the test-blind protocol the other
packages here report.

**Consequence: do not place these numbers in any table with the test-blind arms.**
In the vocabulary of `results/README.md`'s feedback table, this arm belongs with
"B0 + test repair" on oracle exposure, not with "CodeWeaver".

There is no access audit for these runs. The agent logs were retained but carry no
tool-call ledger targeting the oracle, so the extent of reading is *known to be
non-zero by design* and otherwise unquantified.

## Results

### Correctness — `codeweaver`

| layer | result |
|---|---|
| Rust unit tests (mocked HAL/DB) | 312 / 312 |
| e2e oracle | 103 passed, 0 failed, 1 skipped, 1 deselected (of 104 selected) |
| parity | complete, 0 gaps, 18 source modules covered |

18 milestones: 13 from the Scoper, 3 appended by the parity loop, 1 deferred-test
retry, 1 user-added.

The **skipped** test (`test_sff_high_power_class_enabled`) is environmental, not a
defect: the emulator module advertises SFF-8636 power class 4, and the code path
under test is a no-op below class 5. No class-5 module can be provisioned on this
testbed. It is not counted as a pass.

The **deselected** test (`test_link_change_triggers_fast_flag_recapture`) was
deferred by the pipeline's give-up path after exhausting its repair budget, and
recorded in `skips.json`. It is not counted as a pass either. It was later found to
be cadence-sensitive and was rewritten in sonic-dev; that rewrite is not in this
package.

### Performance — `codeweaver-optimized`

| layer | result |
|---|---|
| Rust unit tests | 320 / 320 |
| e2e oracle (entire suite, no gate) | 104 / 105 |

**The denominators differ between arms** (104 vs 105) and neither is a pass rate over
the same set: the first arm ran the cumulative milestone gate with deferred tests
deselected; the second ran the whole suite ungated. Do not compute a delta between
those two fractions.

The single failure is `test_dom_gating::test_dom_gated_during_cmis_init`. Evidence
that it is flaky rather than a regression: across the campaign's 20 rounds it failed
in **14**, including **7 rounds in which the optimizer changed no code at all**
(`"files": []`). An empty change set cannot cause a regression. It is reported as a
failure anyway rather than filtered out.

### What the optimize stage moved

20 rounds, **4 changes kept**. All four are in the platform bridge or the CMIS API
surface: avoiding a per-call Python `bytes()` round trip, caching two
process-lifetime Python objects, and memoising two per-handle values that are static
for a bring-up step.

| metric | pre | post (mean) | change | noise (cv) | real? |
|---|---:|---:|---:|---:|:--:|
| EEPROM reads / cycle (B9, rust) | 21,918 | 15,899 | **−27.5%** | 1.8% | yes |
| idle CPU (B5, rust) | 43.4% | 37.0% | **−14.7%** | 2.9% | yes |
| DOM sweep (B4, config a) | 52.9 ms | 55.0 ms | +4.0% | 14.1% | **no** |

### This package has a noise floor — the others do not

Everything else in `results/` is N=1. Here, the campaign's second half accepted no
changes, so its **10 benchmark rounds are repeated measurements of one unchanged
crate**. That yields a measured coefficient of variation per metric, which is what
the "real?" column above is decided against (threshold: |Δ| > 3σ).

This is why the B4 movement is reported as **not** a regression: it is well inside a
14% noise band. Reading it as a regression — as a single before/after pair would
invite — would have been wrong.

Two cells to distrust: `b5_cpu_python` has one outlier (2.0% against a ~18.5%
typical) because that run measured the Python reference at its 60 s default DOM
interval instead of the 5 s the Rust daemon used; and `b9_events_python` is
identical in all ten runs (6,456) because EEPROM work per cycle is deterministic —
which is precisely why B9 is used as the validity gate rather than as a timing.

## What this package cannot support

1. **No stub baseline.** There is no unimplemented-daemon control scored through this
   oracle, so nothing here says what a no-op would score. (A no-op daemon *was* run
   separately in sonic-dev and fails the STATE_DB-backed tests, but it was not scored
   through this pipeline and is not reported as a number.)
2. **N = 1 for correctness.** One run per arm. The n=10 noise floor covers the
   *benchmark*, not the translation: nothing here estimates how a second CodeWeaver
   run would differ.
3. **Cost is unrecoverable**, as for every CodeWeaver run in this directory. The
   per-agent logs are overwritten per invocation and carry no usage records. No
   premium-request or AIU figure is inferred.
4. **Not reproducible from this package.** Scoring needs a SONiC KVM testbed, the
   `xcvr-emu` emulator, and a `pmon` container with `libswsscommon` and CPython 3.13.
   `reproduction/README.md` explains what would be required; unlike the other
   packages here, **no self-contained `score.sh` is possible**.
5. **Not this repository's engine.** The runs were executed by `recodeAgent`, the
   xcvrd-specific ancestor of CodeWeaver — same agent methodology and same graph,
   before the generalisation into a config-driven engine. This is evidence for the
   method, not a reproduction of the current code.

## Rules for combining these numbers

- Never in a table with the AlphaTrans or CRUST-bench columns. Different suite,
  different oracle provenance, different oracle exposure.
- Never as a peer of a test-blind arm (see the warning above).
- The two arms here are before/after on one artifact — not independent samples.
- The performance deltas are only quotable **with** their noise floor. A bare
  "−27.5%" that omits the 1.8% cv is a weaker claim than the data supports, and a
  bare "+4.0%" that omits the 14.1% cv is a claim the data does not support at all.
