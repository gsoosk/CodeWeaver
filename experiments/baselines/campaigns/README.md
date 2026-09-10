# Reproducing the published campaigns

Every published result under `results/` was produced by the code in this
repository. This file records the exact configuration behind each one.

`run_campaign.py` consolidates the four near-identical per-campaign controllers
that drove the original runs into one parameterised entry point. It reproduces
those runs; it is **not** a byte-identical copy of any individual controller.

## Prerequisites

- Linux, Python 3.12.3, pytest 9.1.1, and the AlphaTrans test dependencies.
- The AlphaTrans dataset at revision `c1cabf93d41a153de207d6b098e1da7bbd79abab`,
  materialised with `examples/alphatrans/setup.sh --tier-a <dataset-root>`.
- For the **Copilot CLI** arm: an authenticated `copilot` binary (runs used
  1.0.84-1).
- For the **API** arms: a running proxy — see below.

## The API transport

The API arms reach a GitHub Copilot subscription through a **separately
authenticated, user-run** instance of [`ericc-ch/copilot-api`][proxy], pinned at
v0.7.0, commit `0ea08febdd7e3e055b03dd298bf57e669500b5c1`.

[proxy]: https://github.com/ericc-ch/copilot-api

That proxy is **unofficial and reverse-engineered**. It is not affiliated with or
supported by GitHub, and its README warns that heavy automated use can trigger
abuse detection. No proxy code, credentials or raw streams are published here.
Read its warnings and your own subscription terms before using it.

Setup used for the published runs:

1. `npx copilot-api@0.7.0 auth` — GitHub device flow, on the account holding the
   subscription. The token is written to `~/.local/share/copilot-api/github_token`
   with mode 600. Do not copy credentials from any other tool.
2. Start it bound to loopback only, with its own rate limiter:
   `copilot-api start --account-type <individual|business|enterprise> --port 4141
   --rate-limit 30 --wait`
3. Capture the catalog once — the campaign driver validates settings against it and
   refuses to run on capabilities the provider does not advertise:
   `curl -s http://127.0.0.1:4141/v1/models > model-catalog.json`

The published runs additionally required a local bearer key on the proxy, because
the host was shared. The client sends `COPILOT_API_KEY` as an `Authorization`
header and never records it in any artifact. If your proxy needs no local key,
leave the variable unset.

> **Capability note.** On this route every Claude model advertised a **64,000**
> output-token cap, and only **16,000** without streaming — which is why the API
> arms stream. Reasoning tokens are billed inside `completion_tokens`. Do not
> assume these limits hold for another account or date; read `model-catalog.json`.

## Published runs

### B0 via the Copilot CLI — `results/alphatrans-b0-sonnet5-med-2026-09-08`

```bash
python -u experiments/baselines/run_one.py \
  --project <subject> --tag <tag> \
  --backend copilot --model claude-sonnet-5 --effort medium \
  --context long_context --max-rounds 6
```

Whole-repository prompt, block-aware continuation across responses, tools disabled
and audited. `--compare-tag <earlier-tag>` records a worst-of-two selection.

### B0 via the API, per-file — `results/alphatrans-b0-api-2026-09-09`, headline arm

```bash
python -u experiments/baselines/campaigns/run_campaign.py \
  --mode generate --granularity per-file \
  --tag b0-api-perfile-sonnet5-med-20260909v2 \
  --campaign-dir ~/campaigns/perfile \
  --model-catalog ~/model-catalog.json \
  --model claude-sonnet-5 --effort medium --max-output-tokens 64000
```

One independent request per module; 126 requests across the four subjects.

### B0 via the API, whole repository — same package, secondary arm

```bash
python -u experiments/baselines/campaigns/run_campaign.py \
  --mode generate --granularity repo --max-rounds 1 \
  --tag b0-api-1shot-sonnet5-med-20260908 \
  --campaign-dir ~/campaigns/oneshot \
  --model-catalog ~/model-catalog.json \
  --model claude-sonnet-5 --effort medium --max-output-tokens 64000
```

`--max-rounds 1` is the strict single call: whatever one response cannot hold is
left as an unimplemented skeleton stub and scored as such.

### Repair arms — `results/alphatrans-b0-repair-2026-09-09`
```bash
python -u experiments/baselines/campaigns/run_campaign.py \
  --mode repair --arms build test \
  --source-tag b0-api-perfile-sonnet5-med-20260909v2 \
  --tag b0r-<arm>-sonnet5-med-20260909v2 \
  --campaign-dir ~/campaigns/repair \
  --model-catalog ~/model-catalog.json \
  --model claude-sonnet-5 --effort medium --max-output-tokens 64000 --iterations 3
```

`build` is **test-blind** — its only feedback is `build_check` parse/import
diagnostics. `test` reads the oracle's failure output and is **not** test-blind.
The two are not comparable to each other; see that package's `METHOD.md`.

The original controllers used one tag per arm. `run_campaign.py` takes a single
`--tag`, so run the arms separately if you want the published tag names.

## The CRUST-bench suite (C to Rust)

A second example lives at `examples/crust`. Materialize it, which also relocates the
held-out tests outside the subject tree:

```bash
bash examples/crust/setup.sh --all /path/to/CRUST-bench
```

Its arms, published as `results/crust-b0-2026-09-10`:

```bash
# B0 via the Copilot CLI (whole crate, continued across responses, tools disabled)
python -u experiments/baselines/run_one.py --project <subject> --example crust \
  --tag b0-crust-cli-sonnet5-med-20260910 --backend copilot \
  --model claude-sonnet-5 --effort medium --context long_context --max-rounds 6

# B0 via the API, whole crate in one call, and per file
python -u experiments/baselines/campaigns/run_campaign.py --mode generate \
  --example crust --granularity repo --max-rounds 1 ...
python -u experiments/baselines/campaigns/run_campaign.py --mode generate \
  --example crust --granularity per-file ...

# repair arms
python -u experiments/baselines/campaigns/run_campaign.py --mode repair \
  --example crust --arms build ...    # and --arms test

# CodeWeaver
python -m codeweaver run --config examples/crust/subjects/<subject>/codeweaver.toml \
  --app-id <tag>-<subject>
```

After any CodeWeaver run, verify the oracle stayed unread. This is not optional:
CodeWeaver runs its agents with `--allow-all`, and agents did reach the oracle twice
during development before it was moved out of their working tree.

```bash
bash examples/crust/tools/oracle_audit.sh cset c-aces lambda-calculus-eval inversion_list
```

## Offline checks
```bash
python experiments/baselines/test_continuation.py
```

30 checks covering continuation, collector recovery, API transport and SSE
handling, credential redaction, repair-loop guards, and scoring policy. No model
access, no network, no cost.

## Scoring

Scoring is independent of generation. Every published package ships a
`reproduction/score.sh` that re-scores its frozen artifacts using the bundled
oracle runner, and needs no model access at all.

All published numbers use `--no-pipeline-skips`, so repair-budget deferrals cannot
hide failures. The fixed environment-broken exclusions are retained, because they
fail against AlphaTrans's own golden translation on this harness and are deselected
for every arm equally.
