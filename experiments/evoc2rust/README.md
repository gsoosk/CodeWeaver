# EvoC2Rust Vivo-Bench comparison

This harness recreates the publicly reproducible portion of *EvoC2Rust: A
Skeleton-guided Framework for Project-Level C-to-Rust Translation*
([DOI:10.1145/3786583.3786856](https://doi.org/10.1145/3786583.3786856),
[arXiv:2508.04295v4](https://arxiv.org/abs/2508.04295v4)) for CodeWeaver.

The paper's six-project C2R-Bench, human-corrected Rust references, translated
outputs, feature-mapping library, and implementation are not public. Those
cells are reported as unavailable rather than reconstructed from unrelated
benchmarks. The new measured experiment uses the paper's public Vivo-Bench
input at AtomGit commit `c88cef1a1d15079478be14ab361dda8f3b49fee2`.

## Leakage-safe contract

The pinned C2Rust 0.22.1 transpiler is used only during preparation to derive
ABI-compatible Rust type/signature skeletons and mechanically translated test
contracts from the disclosed C benchmark. Every production function body is
replaced by `unimplemented!()` before model access. The full transpiled
production output is never copied into a prepared or measured workspace.

The immutable evaluator restores trusted Cargo wiring and translated fixed
tests and a frozen Cargo lock in an isolated temporary copy. Each of the 125
test functions enabled by
the pinned upstream test arrays is run in its own process. Two additional
`rb-tree` functions are disabled upstream and are not promoted into the fixed
contract. The original C benchmark is also built and executed before
preparation, and all 17 upstream CTest executables must pass.

Preparation additionally proves that the immutable contracts pass all 125
active tests against both the original C implementation and the full C2Rust
translation, while the stripped scaffolds compile but pass 0/125. Full C2Rust
production bodies exist only inside a temporary preparation directory and are
not retained.

## Metrics

- **ICompRate/FCompRate:** target modules in independently compiling subject
  groups divided by all 19 Vivo-Bench modules. ICompRate uses cumulative
  insertion with original-C fallback after rejected groups; FCompRate evaluates
  each fixed group independently.
- **TestRate:** independently passing fixed test functions divided by 125.
- **SafeRate:** nonblank production Rust lines outside unsafe functions and
  unsafe blocks divided by all nonblank production Rust lines.
- **AccRate-P/R:** unavailable because the paper's manually corrected Rust
  references are not released.

CodeWeaver uses GPT-5.6 Sol at maximum reasoning effort for three repetitions.
Paper numbers remain labeled published references; CodeWeaver values are never
presented as same-model results.

The paper reports 113 Vivo-Bench test cases. The pinned public repository
revision enables 125 test functions; the report keeps that denominator drift
visible and does not force the new measurements onto the paper denominator.

## Commands

```sh
python -m experiments.evoc2rust validate-config

python -m experiments.evoc2rust prepare \
  --artifact-root /opt/codeweaver-evoc2rust/artifact \
  --workspace-root /opt/codeweaver-evoc2rust/workspaces \
  --c2rust-binary /opt/codeweaver-evoc2rust/tools/bin/c2rust

python -m experiments.evoc2rust run \
  --manifest /opt/codeweaver-evoc2rust/workspaces/manifest.json \
  --workspace-root /opt/codeweaver-evoc2rust/workspaces \
  --runs-root /opt/codeweaver-evoc2rust/runs \
  --variant full --repetitions 3 --jobs 4

python -m experiments.evoc2rust evaluate \
  --manifest /opt/codeweaver-evoc2rust/workspaces/manifest.json \
  --workspace-root /opt/codeweaver-evoc2rust/workspaces \
  --runs-root /opt/codeweaver-evoc2rust/runs \
  --out /opt/codeweaver-evoc2rust/evaluation --jobs 4

python -m experiments.evoc2rust report \
  --evaluation /opt/codeweaver-evoc2rust/evaluation/evaluation.json \
  --out /opt/codeweaver-evoc2rust/report

python -m experiments.evoc2rust package \
  --repository-root /mnt/c/Users/t-fhabibi/CodeWeaver \
  --workspace-root /opt/codeweaver-evoc2rust/workspaces \
  --runs-root /opt/codeweaver-evoc2rust/runs \
  --evaluation-root /opt/codeweaver-evoc2rust/evaluation \
  --report-root /opt/codeweaver-evoc2rust/report \
  --campaign-metadata-root /opt/codeweaver-evoc2rust/campaign \
  --infrastructure-failures-root /opt/codeweaver-evoc2rust/infrastructure-failures \
  --c2rust-binary /opt/codeweaver-evoc2rust/tools/bin/c2rust \
  --out /mnt/c/Users/t-fhabibi/CodeWeaver/results/evoc2rust-codeweaver-comparison-2026-08-13 \
  --require-complete
```

The report emits exact CSV/JSON data, Markdown, publication-ready LaTeX, a
human-readable PDF, and two PDF figures. Packaging additionally preserves the
prepared immutable contracts, filtered raw trajectories, campaign metadata,
excluded infrastructure failures, tool provenance, and SHA-256 checksums.
