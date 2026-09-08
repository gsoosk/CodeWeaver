# Baseline harnesses

Comparison arms for the AlphaTrans Java → Python campaign. Every arm produces a
`src/main/**` tree in the same shape CodeWeaver's working copy has, so **one oracle
scores them all**:

```bash
bash examples/alphatrans/tools/oracle.sh \
     --project commons-cli --all \
     --working-copy pipeline-baseline-<tag>/project
```

| Arm | Status | Protocol |
|---|---|---|
| **CodeWeaver** | running | 6 agents, milestone loop + parity loop |
| **B0 — single-shot** | ✅ implemented | one test-blind generation, whole repo prompt, output-only continuations |
| **B1 — SWE-agent** | planned | agentic loop, dollar-budgeted |

## B0 — single-shot

Mirrors CRUST-Bench's `pass@1` setting (arXiv:2504.15254), adapted from C→Rust to
Java→Python and to our interface-skeleton contract. It is the **lower bound**: one
generation, no compiler feedback, no test feedback, no correctness-driven iteration.
This is not a literal one-model-call protocol when output limits require continuation.

```bash
# free: build the prompt and report its size, call nothing
python experiments/baselines/single_shot.py --project commons-cli --dry-run

# model-matched with CodeWeaver (same binary, model and effort)
python experiments/baselines/single_shot.py --project commons-cli --tag b0-20260904

# Azure AI Foundry instead
export AZURE_AI_ENDPOINT=https://<resource>.services.ai.azure.com/models
export AZURE_AI_API_KEY=<key>
python experiments/baselines/single_shot.py --project commons-cli \
       --backend foundry --model gpt-5.4 --tag b0-foundry-20260904
```

For a persistent repetition followed by independent scoring:

```bash
python -u experiments/baselines/run_one.py --project commons-cli \
       --tag b0-sonnet5-med-20260908 \
       --compare-tag b0-sonnet5-med-20260904
```

`run_one.py` defaults to explicit `long_context`, records the CLI/code versions,
and uses the oracle's `--no-pipeline-skips` mode so CodeWeaver's deferred tests
cannot hide baseline failures. Each subject gets an adjacent `.status.json`;
finished runs retain `score.json`, `oracle_score.txt`, and `run_evidence.json`.
Existing run tags are never overwritten.
`--resume-tag OLD --tag NEW` instead recovers/continues the **same observation**;
it is not a repetition or an additional independent sample.

`--compare-tag` retains both observations and records the lower pass count in
`selection.json` as **worst-of-two**, not an unselected `pass@1` result. The
September 4 run used permissive tool flags and did not record its context tier;
it must not be described as an identical-protocol repetition of the hardened run.

### What the model sees

- every Java source file of the subject
- the Python interface skeleton (typed signatures, `pass` bodies)

The oracle is excluded from the prompt. Copilot is additionally launched with an
non-matching tool allowlist, explicit read/write/shell denials, no custom instructions, and no
built-in MCP servers. Any tool-call/execution event invalidates the run.
The CLI treats an empty `--available-tools` value as its defaults, so the explicit
allowlist `__b0_no_tools__` matches no registered tool instead. The live preflight
confirmed that empty lists still offered shell calls, while the explicit filter
produced no tool-call/execution events; model text claiming execution is not evidence
that a tool actually ran.
`backend-audit/round-*/` retains the invocation arguments and prompt hash,
stdout/stderr and parsed audit for every backend invocation. `"oracle_seen": false` alone in older metadata is not
proof of access isolation.

### What it writes

```
subjects/<project>/pipeline-baseline-<tag>/
  project/src/main/**.py    the translation (scored by the oracle)
  prompt.md                 the exact prompt sent
  response.md               transcript with invocation and internal message boundaries
  metadata.json             configuration, total/per-invocation usage, files and lineage
  generation.json           pre-generation manifest and terminal state, also retained on failure
  backend-audit/round-*/     invocation hashes, event stream, stderr and tool-access audit
```

The working copy **starts from the skeleton** and is overwritten with generated
bodies. A module the model forgets therefore stays an unimplemented stub rather than
vanishing — the run fails those tests honestly instead of failing to import at all,
which would understate the baseline.

### Output limits and continuation

The binding constraint on whole-repo single-shot is **`max_output_tokens`, not the
context window**. Measured against the golden translations:

| Project | Input | Output required |
|---|---|---|
| commons-fileupload | ~57K | ~16K |
| commons-cli | ~59K | ~23K |
| commons-csv | ~58K | ~25K |
| **commons-validator** | **~188K** | **~80K** |

188K of input is comfortable for a large-context model; emitting 80K of Python in
*one response* is not, on most models.

So when one response cannot hold every module, the harness **continues the same
generation** rather than giving up or keeping a truncated result. Continuation is
**block-aware**: only file blocks that closed cleanly are kept, any half-written
trailing block is discarded, and the next turn asks for the modules still outstanding.
Each assistant message is parsed **independently**, even within one CLI invocation.
A later message's tail or closing fence never completes an earlier partial block.
Outstanding modules are requested **IN FULL**, not stitched together.

Copilot can internally continue after its output cap in one CLI subprocess. For
example, an empty reasoning-only assistant turn, a translation and a trailing
fragment can represent **one backend invocation but three model calls/assistant
turns**. All messages and raw events are retained; the collector no longer keeps
only the final assistant message.

**This stays within the single-shot protocol in the sense that matters: the model gets
no feedback.** It never learns whether anything compiled, imported, or passed a test.
It is told only which files it has not yet written — bookkeeping about its own output,
not information about correctness. `metadata.json` records `backend_invocations`
(`continuation_rounds` remains its compatibility alias), `new_backend_invocations`,
`observed_model_calls` (the number of `model.call_start` events), and
`observed_assistant_turns` (including empty turns). Observed event counts are not
estimates of unreported provider calls. Usage is retained per invocation and totaled
only for fields reported by every invocation.

Tune with `--max-output-tokens` (Foundry per-response limit) and `--max-rounds`
(default 6, a **total backend-invocation budget**, not an internal-model-call budget).
Copilot's output cap is provider-controlled; the metadata's
`max_output_tokens` is not an enforced Copilot limit. Use `--context long_context`
when the input plus accumulated continuation output exceeds the default context.
`--dry-run` predicts how many rounds a subject will need before you spend anything.

### Linked artifact recovery

For a terminal audited Copilot run whose collector lost complete blocks:

```bash
python -u experiments/baselines/run_one.py --project commons-csv \
       --resume-tag OLD --tag NEW --context long_context --max-rounds 6
```

The same arguments work with `single_shot.py` for generation/replay only; add
`--dry-run` to validate the source and report recovered modules without writing or
calling a model. Model, effort and context must match the source. `run_one.py`
continues to score **after** generation using `oracle.sh --no-pipeline-skips`;
the oracle's isolated staging and fixed environment exclusions are unchanged.

Recovery rebuilds the original Java/skeleton/system prompt and requires an exact
match with saved `prompt.md`. It validates required metadata shapes, no-tools
arguments, each allowed request's prompt hash, contiguous invocation identities,
usage, exit codes and the actual JSONL events. It never reads the source generated
tree, oracle scores or oracle logs to construct a continuation. Only closed model
output and the list of missing whole modules are sent back. Active sources, absent
terminal status/provenance, missing/invalid audits, malformed JSONL, nonzero CLI
exits and tool attempts are rejected rather than silently retried.
Internal user messages must be the audited input or the CLI's known automatic
`Please continue from where you left off.` request; unknown continuation prompts
fail closed and require protocol review.

If CSV used one invocation containing three model calls and emitted ten closed
modules plus a truncated CSVParser, replay keeps those ten modules and requests
CSVParser in full. With `--max-rounds 6`, **at most five new invocations** remain.
Replay makes no model call when every expected module is already closed; an
exhausted total budget also makes no call and leaves missing modules as stubs.

Original files and the original failed `.status.json` are never changed. The new
tag copies validated source audits byte-for-byte, continues global round numbering,
and records audit origin tags, source hashes/revision, current collector code hashes,
source state, usage and `observation_tag` lineage. Hashes establish artifact
consistency, not authentication of potentially forged provenance. A terminal
`generation.json` plus complete valid audits permits recovery even if a later
collector failure prevented final metadata; killed runs still marked active need
operator investigation, not an automatic state override.

Recovery tags are explicitly marked `independent_sample: false`. Comparisons retain
the existing **worst-of-two** policy, disclose linked recovery, and reject comparing
two tags of the same observation as though they were independent samples.

`experiments/baselines/test_continuation.py` exercises the loop offline against a
fake backend and mocked CLI, including multi-message truncation, recovery, total
budgets, source preservation, invalid audits and post-generation scoring. No API,
no real CLI/model invocation, no cost.

## Backends

| Backend | Model matching | Cost reporting |
|---|---|---|
| `copilot` (default) | **exact** — same binary, model and effort as CodeWeaver | premium requests + AIU |
| `copilot-api` | same explicitly selected model; different transport/system-prompt protocol | provider-reported tokens only |
| `foundry` | different stack | prompt/completion tokens |

### API-only Copilot subscription transport

Run a separately authenticated, user-owned instance of
[`ericc-ch/copilot-api`](https://github.com/ericc-ch/copilot-api) on loopback.
This is an unofficial integration: respect subscription policy, model availability
and rate limits. Do not expose the proxy or its token-export endpoint publicly.
The benchmark client accepts only literal loopback addresses (or `localhost`),
does not follow redirects or use environment HTTP proxies, and never reads GitHub
credentials. `COPILOT_API_KEY`, if set, is a **local proxy** bearer key; it is sent
only in the HTTP header and is omitted from all request/audit metadata.

```bash
python -u experiments/baselines/run_one.py \
  --project commons-cli --tag b0-api-sonnet5-med-20260908 \
  --backend copilot-api --api-base-url http://127.0.0.1:4141/v1 \
  --model claude-sonnet-5 --effort medium \
  --max-output-tokens 64000 --api-stream
```

The model ID and output cap must be explicit. Reasoning effort and temperature
are omitted unless requested; CLI context-tier defaults are not applied.
`--context` and CLI `--resume-tag` are rejected for this backend. Check the actual
catalog before choosing parameters: the observed Sonnet 5 catalog advertises a
1M context, 64K streaming output, 16K non-streaming output and medium effort.
Those are observations, not hardcoded promises for other accounts or dates.

One invocation is one HTTP completion request. SSE deltas are assembled within
that one response; a `length` finish reason triggers the existing closed-block,
missing-module continuation. The client sends no tool/function definitions and
rejects returned tool calls, refusals, malformed/multiple choices, missing finish
reasons, model mismatches, and unfinished streams. There are no automatic retries,
model/parameter fallbacks, Copilot CLI invocations or implicit CLI instructions.
Hidden provider-side prompts are not observable, so this arm is not claimed to be
the identical prompt/protocol as the CLI arm.
The client also enforces at least 30 seconds between request starts, independently
of the proxy limiter; benchmark subjects are launched sequentially.

`api-audit/round-*/` preserves the private JSON request, JSON/SSE response, hashes,
HTTP status, timing, requested/returned model, finish reason and token usage.
Raw streams can contain provider reasoning and must remain private. Token counts
are not converted into invented premium-request or AIU costs. Use distinct tags
and do not mix API observations into the CLI worst-of-two selection.

`single_shot.py --backend copilot-api ... --dry-run` validates configuration and
constructs the prompt without an HTTP call. `--api-token-limit-field` explicitly
selects `max_tokens` or `max_completion_tokens`; unsupported parameters fail rather
than being silently removed. The existing offline runner also covers API transport,
SSE continuation, authentication redaction, and CLI-free worker routing.

> A cross-backend comparison measures the *model* as much as the scaffolding. For
> the headline table use `copilot`, so CodeWeaver and B0 differ **only** in
> scaffolding. Use `foundry` for models Copilot does not serve, and label those rows.

Foundry auto-detects endpoint shape: `*.openai.azure.com` → `AzureOpenAI`
(deployment-addressed, needs `api_version`); `*.services.ai.azure.com/models` →
OpenAI-compatible client. It retries once without `temperature`/`max_tokens` for
reasoning models that reject them.

## Adding another baseline

Implement the protocol, write into
`subjects/<p>/pipeline-baseline-<tag>/project/src/main/**`, and drop a
`metadata.json` beside it. Reuse `backends/` for model access. Nothing else needs to
change — scoring, oracle isolation and the tamper manifest already apply to any arm.

## Fairness checklist

- [ ] Same model and effort across arms, or the difference stated in the caption.
- [ ] Same subjects, same denominators; never pool tier A and tier B.
- [ ] Report **cost per project** for every arm (`metadata.json` → `usage`).
      CodeWeaver spends far more than one call; hiding that would be dishonest and
      inviting a reviewer to find it.
- [ ] State oracle access per arm. Single-shot is test-blind; a SWE-agent arm that
      runs the test suite is **not**, and the two are not directly comparable.
