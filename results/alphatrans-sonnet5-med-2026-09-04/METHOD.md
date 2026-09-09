# Method — CodeWeaver, four subjects, model-matched

One-line summary for a report: **CodeWeaver, run on four AlphaTrans subjects with
Claude Sonnet 5, scored 380/381, 296/298, 38/39 and 452/462 on held-out oracles.**

## Question this run answers

How does CodeWeaver perform across several repositories, using the same model and
effort later used for every baseline arm, so that differences reflect scaffolding
rather than model choice?

## Subjects and inputs

| | |
|---|---|
| Subjects | `commons-cli`, `commons-csv`, `commons-fileupload`, `commons-validator` (AlphaTrans Tier A) |
| Dataset revision | `c1cabf93d41a153de207d6b098e1da7bbd79abab` |
| Given to the agents | Java `src/main`, and a Python interface skeleton per subject |
| Withheld | The oracle test suite, in source form, at all times |

## System under test

CodeWeaver, as in `results/alphatrans-commons-cli-2026-09-03`, but model-matched
to the baselines.

| Setting | Value |
|---|---|
| Model | `claude-sonnet-5` |
| Reasoning effort | `medium` |
| `max_iter` | 6 |
| `max_parity_rounds` | 4 |
| Campaign id | `sonnet5-med-20260904` |

## Feedback the agents received

`build_check` (parse + import), self-authored tests, and the oracle's pass/fail
counts. Never the oracle's source.

## Scoring — read this before quoting any number

Scores here are **recomputed independently**, not read from the pipeline's own
`report.json`, and are produced with `oracle.sh --no-pipeline-skips`.

That flag matters. During a run, CodeWeaver may exhaust a milestone's repair budget
and *defer* the offending tests, recording them in `pipeline/skips.json`; ordinary
scoring then deselects them. Deferred tests are real failures, so every number in
this package was produced with deferrals **disabled**. Consequently these scores can
be lower than the pipeline's own self-reported figures, and they are the ones to
cite.

The fixed environment-broken exclusion is retained (one `CurrencyValidator` test on
`commons-validator`), because it fails against AlphaTrans's own golden translation
in this environment and is deselected for every arm equally.

## Result

| Subject | Oracle passed | Pipeline self-report | Milestones skipped |
|---|---|---|---|
| commons-cli | **380 / 381** | M13, passed | 1 (`M4`) |
| commons-csv | **296 / 298** | M8, passed | 0 |
| commons-fileupload | **38 / 39** | M7, passed | 0 |
| commons-validator | **452 / 462** | M14, **not** passed | 5 (`M4`, `M11`–`M14`) |

`commons-validator` terminated with `done=True` after exhausting repair budgets on
five milestones. **Termination is not success**: its ten remaining failures cluster
into a timezone-dispatch bug in `AbstractCalendarValidator`, two `FloatValidator`
bounds problems, and one test the Java source itself marks `@Ignore`.

## What this run cannot support

- **N = 1 per subject, 1 repetition.** No variance.
- **Cost is unavailable.** Role stdout logs retain only the last of roughly 50
  CLI invocations per subject, so no complete usage ledger exists. Summing what
  survives would understate the true cost by more than an order of magnitude, and
  is deliberately not reported.
- Numbers here are not comparable to AlphaTrans's published tables, which report
  per-fragment statuses and `#GS` rather than oracle pass counts.

## Reproducing

`reproduction/score.sh <subject> codeweaver` re-scores the frozen translation.
It verifies the dataset revision, oracle manifest and package manifest first, and
needs no model access.
