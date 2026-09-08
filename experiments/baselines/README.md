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
| **B0 — single-shot** | ✅ implemented | one call, whole repo in one prompt, no feedback |
| **B1 — SWE-agent** | planned | agentic loop, dollar-budgeted |

## B0 — single-shot

Mirrors CRUST-Bench's `pass@1` setting (arXiv:2504.15254), adapted from C→Rust to
Java→Python and to our interface-skeleton contract. It is the **lower bound**: one
generation, no compiler feedback, no test feedback, no iteration.

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
`backend-audit/round-*/` retains the exact invocation, stdout/stderr and parsed
audit for every response. `"oracle_seen": false` alone in older metadata is not
proof of access isolation.

### What it writes

```
subjects/<project>/pipeline-baseline-<tag>/
  project/src/main/**.py    the translation (scored by the oracle)
  prompt.md                 the exact prompt sent
  response.md               the raw completion(s), concatenated
  metadata.json             backend, model, usage per round, files parsed/written/stubbed
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
That makes seam corruption impossible — a resumed response can never splice a broken
file together — and makes the loop idempotent.

**This stays within the single-shot protocol in the sense that matters: the model gets
no feedback.** It never learns whether anything compiled, imported, or passed a test.
It is told only which files it has not yet written — bookkeeping about its own output,
not information about correctness. `metadata.json` records `continuation_rounds` and
per-round usage, so the deviation from a literal one-call protocol is always visible.

Tune with `--max-output-tokens` (Foundry per-response limit) and `--max-rounds`
(default 6). Copilot's output cap is provider-controlled; the metadata's
`max_output_tokens` is not an enforced Copilot limit. Use `--context long_context`
when the input plus accumulated continuation output exceeds the default context.
`--dry-run` predicts how many rounds a subject will need before you spend anything.

`experiments/baselines/test_continuation.py` exercises the loop offline against a
fake backend, including the mid-file truncation case. No API, no cost.

## Backends

| Backend | Model matching | Cost reporting |
|---|---|---|
| `copilot` (default) | **exact** — same binary, model and effort as CodeWeaver | premium requests + AIU |
| `foundry` | different stack | prompt/completion tokens |

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
