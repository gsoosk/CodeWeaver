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

### What the model sees

- every Java source file of the subject
- the Python interface skeleton (typed signatures, `pass` bodies)

**Not** the oracle. That is enforced structurally: the harness only ever reads
`source_dir` and `.scaffold/`, and records `"oracle_seen": false` in its metadata.

### What it writes

```
subjects/<project>/pipeline-baseline-<tag>/
  project/src/main/**.py    the translation (scored by the oracle)
  prompt.md                 the exact prompt sent
  response.md               the raw completion(s), concatenated
  metadata.json             backend, model, usage per round, files parsed/written/stubbed
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

Tune with `--max-output-tokens` (per response) and `--max-rounds` (default 6).
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
