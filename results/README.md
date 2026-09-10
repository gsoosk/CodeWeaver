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

## Rules for combining these numbers

1. **Scoring is uniform, protocols are not.** Every arm is scored the same way:
   independent recomputation, `--no-pipeline-skips` so repair deferrals cannot hide
   failures, fixed environment exclusions retained. What differs between arms is how
   the translation was produced, and that difference is the experiment.

2. **Do not pool arms with different feedback.** Arms differ in what the model was
   allowed to see:

   | Arm | Oracle source | Oracle pass/fail | Compiler / import |
   |---|---|---|---|
   | CodeWeaver | never | **counts only** | yes |
   | B0 (all generation variants) | never | never | never |
   | B0 + build repair | never | never | **yes, parse/import diagnostics** |
   | B0 + test repair | never | **full failure output** | yes |

   The last row is the only arm that saw oracle failures. Keep it out of any table
   containing the others.

3. **Do not compare across transports without saying so.** The Copilot CLI arm and
   the direct API arm use different clients and different hidden system prompts,
   and the CLI arm was permitted to continue one generation across responses.

4. **Do not place these beside AlphaTrans's or CRUST-bench's published tables.**
   AlphaTrans reports per-fragment statuses and `#GS`; CRUST-bench lets the model
   read and run the test suite. Our oracle is held out from every arm here.

5. **N = 1 per subject.** No repetitions, no variance, anywhere in this directory.

## Cost

Reported per package where it was actually measurable, and omitted where it was
not. CodeWeaver's per-run cost is **unrecoverable**: its role logs are overwritten
per CLI invocation, so no complete usage ledger exists. The direct-API arms report
provider token counts only, with no premium-request or AIU figure inferred from
them.
