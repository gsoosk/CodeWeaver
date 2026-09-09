# Method — B0 via direct API, per-file and whole-repo

One-line summary for a report: **Translating one class per API request removed the
output-token ceiling entirely and replaced it with cross-module inconsistency;
damage tracked how tightly a repository's modules are coupled, not its size.**

## Question this arm answers

Two, separated deliberately:

1. **Granularity.** AlphaTrans's own ablation prompts one Java class per call.
   What happens when we do the same, with a held-out oracle and a typed interface
   contract? (Headline arm: **per-file**.)
2. **Output capacity.** Can a whole repository fit in one response at all?
   (Secondary arm: **whole-repo single call**.)

## Subjects and inputs

| | |
|---|---|
| Subjects | The same four AlphaTrans Tier A subjects |
| Dataset revision | `c1cabf93d41a153de207d6b098e1da7bbd79abab` |
| Per-file prompt | One Java class, plus that one skeleton module. Nothing about its siblings. |
| Whole-repo prompt | Every Java file, plus the full skeleton |
| Withheld | The oracle, in every form |

## Transport

Generation went through the **direct chat-completions API**, not the Copilot CLI,
using the user's Copilot subscription via a separately authenticated, user-run
instance of the unofficial `ericc-ch/copilot-api` proxy on loopback.

| Setting | Value |
|---|---|
| Model | `claude-sonnet-5`, `reasoning_effort: medium` |
| Streaming | Yes — the streaming cap is 64,000 output tokens; non-streaming is only 16,000 |
| `max_tokens` | 64,000 (the model's advertised cap on this route) |
| Tools | None sent; any returned tool call invalidates the request |
| Retries | None. One HTTP request per invocation. |
| Pacing | ≥ 30 s between request starts |

The proxy is unofficial and reverse-engineered. Results assume it forwards requests
faithfully. No proxy code, credentials or raw streams are published here.

Because the CLI's hidden system prompt is not observable, this arm is **not** the
same protocol as the Copilot CLI arm, and is not claimed to be.

## Per-file protocol

One independent HTTP request per module. Requests share **no conversation state**,
so nothing learned while translating one module can reach another. No continuation,
no retries, no feedback of any kind.

This matches the *granularity* of AlphaTrans's class-by-class ablation
(`src/translation/prompt_class_by_class.py`) but is **not** a byte-exact
replication: we keep the typed interface skeleton, which they do not, and we score
with a held-out oracle rather than their `#GS` metric.

## Result — per-file (headline)

| Subject | Modules | API calls | Oracle |
|---|---|---:|---|
| commons-cli | 22/22 | 22 | **110 / 381** |
| commons-csv | 11/11 | 11 | **collection failure** (1 passed, 6 failed, 19 errors) |
| commons-fileupload | 30/30 | 30 | **37 / 39** |
| commons-validator | 63/63 | 63 | 277 passed, 85 failed, **8 collection errors** |

126 requests, 643,313 prompt and 357,550 completion tokens. Every request
succeeded, every module was emitted, nothing truncated.

**Two of these are not pass rates.** commons-csv does not import at all.
commons-validator's 8 collection errors mean its counts are not on the 462
denominator the other arms use. Report both as errors.

### Why it failed

Isolation, not capacity. 243 of commons-cli's 271 failures are a single naming
split: the parsers call `CommandLine.addOption`, while the skeleton declares
`_addOption`. Each file is faithful to the inputs *it* was given; the assembly is
not. commons-csv fails to import because siblings reference `Constants` members as
bare names — a faithful reading of Java's `import static` — while the skeleton
declares them as class attributes.

commons-fileupload, which has the flattest dependency graph, is unaffected and
matches every other arm at 37/39.

## Result — whole-repo single call (secondary)

| Subject | Modules | Finish | Output tokens | Oracle |
|---|---|---|---:|---|
| commons-cli | 18/22 | `length` | 64,000 | 241 / 381 |
| commons-csv | 0/11 | `length` | 64,000 | no modules emitted |
| commons-fileupload | 30/30 | `stop` | 56,337 | **37 / 39** |
| commons-validator | 27/63 | `length` | 64,000 | 81 / 462 |

Three of four hit the cap exactly. Only fileupload finished naturally — and scored
identically to every other arm, which is the control that isolates the ceiling as
the cause elsewhere.

**Reasoning tokens are billed inside `completion_tokens`** and consumed 21–100% of
emitted characters. commons-csv spent its entire 64,000-token budget reasoning and
wrote no code at all.

## The two API arms are not consistently ordered

Per-file wins on validator (277 vs 81) because whole-repo lost 36 modules to
truncation there. Whole-repo wins on commons-cli (241 vs 110) because isolation
cost more than truncation did. Neither dominates; the failure modes are different.

## What this arm cannot support

- **N = 1 per subject.** No repetitions, no variance.
- **Cost is provider-reported tokens only.** This route reports no premium requests
  or AIU, and none are inferred.
- Not comparable to the Copilot CLI arm (different transport and system prompt,
  and that arm was allowed to continue), nor to AlphaTrans or CRUST-bench numbers.
- A hand-edited diagnostic copy of commons-csv exists locally and is deliberately
  **excluded** from this package: it was test-guided repair, not generation. It
  established that two edits — re-exporting `Constants` at module level, and fixing
  an `int` vs `str` assumption in `Lexer` — take csv from 1 to 185 passing,
  confirming the cause is cross-module disagreement rather than truncation.

## Reproducing

`reproduction/score.sh <subject> <per-file|whole-repo-single-call>`.
Scoring needs no API access, proxy, or model calls.
