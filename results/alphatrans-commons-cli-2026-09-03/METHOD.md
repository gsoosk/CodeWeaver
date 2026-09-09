# Method — CodeWeaver on AlphaTrans `commons-cli`

One-line summary for a report: **CodeWeaver translated Apache Commons CLI from Java
to Python and passed 380 of 381 hidden-oracle tests, one short of AlphaTrans's own
human-written translation.**

## Question this run answers

Can an agentic, milestone-decomposed pipeline translate a real repository well
enough to pass a held-out human test suite it never sees?

## Subject and inputs

| | |
|---|---|
| Subject | `commons-cli`, from AlphaTrans (Tier A) |
| Dataset revision | `c1cabf93d41a153de207d6b098e1da7bbd79abab` |
| Given to the agents | Java `src/main`, and a Python interface skeleton (typed signatures, `pass` bodies) |
| Withheld | The oracle test suite, in source form, at all times |

## System under test

CodeWeaver: six Copilot CLI agents orchestrated by a deterministic Apache Burr
state machine. Milestones are derived mechanically from the interface skeleton
(`Foo.py` → gate token `FooTest`), never by reading the oracle. Each milestone runs
a repair loop; a parity verifier then checks that every source component has a
translated counterpart.

| Setting | Value |
|---|---|
| Model | `claude-opus-4.8` |
| `max_iter` | 6 |
| `max_parity_rounds` | 4 |
| Run id | `alphatrans-cli-azure-001` |

## Feedback the agents received

The Python interpreter (`build_check`: parse + import), their own self-authored
tests, and the oracle's **pass/fail counts** — never the oracle's source. This is
the one arm in this repository that is not fully test-blind: it sees counts, not
test code.

## Scoring

The oracle is AlphaTrans's manually verified Python test suite. Each scored run
verifies a SHA256 manifest over the oracle, stages `src/main` (working copy) plus
`src/test` (pristine master) into a throwaway tree, runs pytest, and deletes it.
Post-run audit confirmed zero oracle test files anywhere under the working copy.

Environment-broken tests — those that fail against AlphaTrans's *own* golden
translation in this environment — are deselected in every configuration, including
the golden and skeleton baselines, so they cannot flatter any arm.

## Result

| Configuration | Oracle tests passed |
|---|---|
| CodeWeaver (this run) | **380 / 381** |
| AlphaTrans golden, human-written — ceiling | 381 / 381 |
| Unimplemented skeleton — floor | 1 / 381 |

56 tests are self-skipped by the suite in every configuration and are excluded
from the denominator on all sides.

The single failure is `BugsTest::test11458`, a `-Dkey=value` parsing edge case.
It is a genuine behavioural gap: the golden translation passes it on the identical
harness.

## What this run cannot support

- **N = 1 project, 1 repetition.** No variance is measurable.
- **Cost is unavailable.** The Copilot CLI role logs are overwritten per
  invocation, so no complete usage ledger exists for this run. Any per-run cost
  figure would be fabricated.
- The model here (`claude-opus-4.8`) differs from the later campaign
  (`claude-sonnet-5`), so this number is not model-matched to the B0 arms.
  Use `results/alphatrans-sonnet5-med-2026-09-04` for model-matched comparison.

## Reproducing

See `reproduction/COMMANDS.md`. Scoring a frozen translation needs no model access.
