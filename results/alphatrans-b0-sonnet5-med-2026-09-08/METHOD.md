# Method — B0 single-shot via the Copilot CLI

One-line summary for a report: **A no-feedback baseline driven through the same
Copilot CLI and model CodeWeaver uses scored 368/381, 37/39 and 381/462, and failed
outright on `commons-csv`.**

## Question this arm answers

How much of CodeWeaver's result comes from its scaffolding rather than from the
model? This arm holds the model, effort and client fixed and removes everything
else: no milestones, no parity loop, no repair.

## Subjects and inputs

| | |
|---|---|
| Subjects | The same four AlphaTrans Tier A subjects |
| Dataset revision | `c1cabf93d41a153de207d6b098e1da7bbd79abab` |
| In the prompt | Every Java source file, plus the full Python interface skeleton |
| Withheld | The oracle, in every form — source, counts, and pass/fail |

Prompt construction follows CRUST-bench's whole-repository single-shot setting
(arXiv:2504.15254): all source files and all interface files in one prompt, with
`{{filename}}` headers and fenced blocks. It is **not** AlphaTrans's baseline,
which prompts one Java class at a time.

## System under test

| Setting | Value |
|---|---|
| Client | GitHub Copilot CLI 1.0.84-1, prompt on stdin |
| Model | `claude-sonnet-5`, effort `medium`, `long_context` |
| Tools | Disabled — `--available-tools=__b0_no_tools__`, plus read/write/shell denials, no MCP servers, no custom instructions |
| Retries | None |

Tool isolation was verified live, not assumed. An empty `--available-tools` list is
silently ignored by this CLI version and still offers shell access; an explicit
non-matching allowlist removes every tool. Each response is audited and **any**
tool-call event invalidates the run. Model text claiming it ran a command is not
evidence that it did — only the event stream is.

## The continuation deviation — important

This arm is **not** a literal one-call baseline. Whole-repo output exceeds what one
response can hold, so the harness continues the *same* generation across responses.
Continuation is block-aware: only fully closed file blocks are kept, a half-written
trailing block is discarded, and the next request asks for the modules still
missing.

The model receives **no correctness information** at any point — only bookkeeping
about which files it has not yet written. `continuation_rounds` and per-round usage
are recorded so the deviation is always visible.

A module the model never writes stays an unimplemented skeleton stub, so the suite
still imports and fails those tests honestly rather than failing to collect.

## Scoring

Identical to the CodeWeaver arms: independent recomputation with
`--no-pipeline-skips`, fixed environment exclusions retained.

## Result

| Subject | Oracle passed | CodeWeaver reference |
|---|---|---|
| commons-cli | **368 / 381** *(selected, see below)* | 380 / 381 |
| commons-csv | **collection failure** | 296 / 298 |
| commons-fileupload | **37 / 39** | 38 / 39 |
| commons-validator | **381 / 462** | 452 / 462 |

### The commons-cli selection

Two observations exist: the original at 368/381 and a rerun at 370/381. The
**worst** is reported, by request. That is a deliberately conservative choice, not
an unselected `pass@1` estimate, and both artifacts are retained in `data/`.

The two are also **not identical-protocol repetitions**: the original predates the
tool-access audit and did not record its context tier. `selection.json` states this.

### commons-csv

Produced no scoreable artifact. Its counts are not a pass rate. Note that csv also
fails in other arms but for different reasons, so the failures are not the same
phenomenon and should not be pooled.

## What this arm cannot support

- **N = 1 per subject**, except commons-cli which has two and reports the worse.
- Cost is recorded as premium requests and AIU where the CLI reported them.
- Not comparable to CRUST-bench's published numbers: their setting lets the model
  read and run the test suite; ours never does.

## Reproducing

`reproduction/score.sh <subject> <b0|b0-rerun>`. Scoring needs no model access.
