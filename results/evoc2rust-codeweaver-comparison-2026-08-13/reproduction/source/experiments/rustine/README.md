# Rustine same-subject comparison harness

This package prepares and evaluates a **new, paired 23-subject experiment**
against Rustine, the artifact for *Translating Large-Scale C Repositories to
Idiomatic Rust* ([arXiv:2511.20617v1](https://arxiv.org/abs/2511.20617)).
It does not call Copilot or CodeWeaver itself.

The Rustine implementation is never exposed. Preparation copies only
`preprocess/`, the generated Rust `skeleton/`, and only the explicitly declared
test contract files/assets from the final available Rustine stage
(`manual_debug`, then `automatic_debug`, then `translate`). Production Rust
files from that stage remain excluded. Tulip Indicators' four omitted fixtures
come from its upstream repository at pinned commit
`be18abb13e075ba866898dcc7cb52399603302a6`, with SHA-256 checks and its LGPL
license. `translation.json` and non-contract translation `.rs` files are
rejected. Each fixed contract is checksummed and a workspace-local evaluator
tests an isolated temporary copy after reconstructing Cargo target wiring and
restoring contract/support files.

## Stages

```powershell
# Validate the committed 23-subject reference configuration.
python -m experiments.rustine validate-config

# Prepare pristine templates and manifest.json.
python -m experiments.rustine prepare `
  --artifact-root C:\path\to\rustine-artifact `
  --workspace-root work\rustine

# Optional later execution (not performed by this harness task).
python -m experiments.recodeagent.run `
  --manifest work\rustine\manifest.json `
  --workspace-root work\rustine `
  --runs-root runs\rustine `
  --config experiments\rustine\experiment.toml `
  --variant full --repetitions 1

# Evaluate existing run workspaces, then render all reports.
python -m experiments.rustine evaluate `
  --manifest work\rustine\manifest.json `
  --runs-root runs\rustine --out results\rustine --jobs 4
python -m experiments.rustine report `
  --config experiments\rustine\subjects.json `
  --evaluation results\rustine\evaluation.json `
  --out results\rustine\report

# Build the final checksummed package after every run is terminal.
python -m experiments.rustine package `
  --repository-root . `
  --campaign-root work\rustine-campaign `
  --workspace-root work\rustine `
  --runs-root runs\rustine `
  --evaluation-root results\rustine `
  --report-root results\rustine\report `
  --infrastructure-failures-root runs\rustine-infrastructure-failures `
  --tool-binary C:\path\to\cargo-newmetrics `
  --execution-python C:\path\to\execution-venv\python.exe `
  --out results\rustine-publication `
  --require-complete
```

Protocol defaults are GPT-5.6 Sol, maximum effort, 5,000-second agent timeout,
`max_iter=5`, `max_parity_rounds=3`, and one repetition. Repetitions remain
configurable in the generic matrix runner.

PDF rendering uses the existing report renderer and requires ReportLab. The
package command requires all 23 terminal run states, all 23 integrity-checked
evaluation rows, a valid comparison PDF, and a clean tracked worktree. It
archives translated outputs and logs without Rust build caches or benchmark
source trees, splits large archives below GitHub's per-file limit, preserves
audited infrastructure-only attempts separately, and checksums every packaged
file.

## Measurement notes

- Compilation is `cargo build --all-targets`.
- Fixed-contract tests run the declared Rust binaries. `xzoom` and `snudown`
  are explicitly N/A. Grabc uses a deterministic headless CLI check because its
  four reported X11 assertions are not runnable from the disclosed driver. HT
  uses a deterministic stdin-driven `demo` check because the artifact exposes
  samples/benchmarks rather than its reported one-assertion oracle. Exact
  assertion credit for both derived checks is unavailable.
- Measured workspaces prepared by harness commit `f4c3a0d` omitted the already
  validated Grabc/HT execution arguments from `contract.json`. Independent
  evaluation verifies the original contract hash and overlays runtime metadata
  in a temporary copy, leaving archived run evidence byte-identical. New
  preparations persist the field directly.
- `evaluation_overrides.json` corrects Grabc's derived version check to invoke
  the candidate's production `grabc -v` binary rather than the disclosed
  `test_grabc` X11 driver, which can print the version without executing
  candidate code. The original `subjects.json` remains frozen; evaluation JSON
  records both values and whether the documented override was applied.
- The artifact does not disclose bzip2's augmented 36-assertion module. Its
  measured oracle is therefore a deterministic CLI compression round trip;
  exact assertion credit remains unavailable.
- Paper-comparable coverage uses `cargo llvm-cov` over the production library
  graph plus immutable Rust contract files, matching the Rustine table's scope.
  Production-only coverage is retained separately in raw evaluation JSON;
  agent-generated tests are excluded from both scopes.
- Rustine's 74.7% function and 72.2% line figures describe the benchmark test
  suites in paper Table 1. They are retained as benchmark characteristics, not
  misreported as Rustine translation outcomes. System comparison uses the
  per-subject translation coverage values from paper Table 2.
- Official-output calibration exactly reproduced qsort's published 100%
  function and 92% line translation coverage. Several larger released Rustine
  translations no longer compile with current dependency/compiler behavior,
  so comparison columns preserve the published paper values rather than
  selectively repairing or overwriting the baseline.
- Rust safety fields use the pinned Rustine `cargo-newmetrics` tool with
  `nightly-2025-05-13`; that tool's built-in library-only check avoids bin
  double-counting. Pointer arithmetic is reported only when the tool exposes
  its rustc-HIR result. A source-pattern count is retained only as a separately
  labeled raw diagnostic, never as the paper-comparable value.
- Missing tools/data are emitted as `unavailable`/`missing`, never as zero or
  success.
- When a fixed suite passes but exposes no runtime assertion counter, assertion
  totals are marked `inferred` (shown with `*`) from Rustine's paper denominator,
  not mislabeled as directly measured.
- The older 118-project ReCodeAgent matrix is not a paired comparison. Only
  results produced by this same-subject harness are placed beside Rustine.
