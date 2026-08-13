# CRUST-Bench example — C → safe Rust with CodeWeaver

Run CodeWeaver on a [**CRUST-Bench**](https://github.com/anirudhkhatry/CRUST-bench)
task (arXiv:[2504.15254](https://arxiv.org/abs/2504.15254)): transpile one of the
benchmark's 100 C repositories into **safe, idiomatic Rust** that conforms to a
provided Rust interface and passes provided Rust tests.

Each benchmark project has a different set of functions and tests, so this example
uses CodeWeaver's **auto-milestones** (the scope stage reads the interface + tests
and generates the milestone matrix) plus the **parity loop** (the parity verifier
confirms every interface function / C behavior is implemented before finishing).

> **Which project is "Crust-β"?** The CRUST-Bench paper uses author–year citations
> (no numbered `[36]`), and none of the 100 benchmark folders is named `Crust-β`,
> so that label/citation comes from whatever secondary source you're reading, not
> from CRUST-Bench itself. This example is therefore **retargetable to any of the
> 100 projects** via `setup` — point it at whichever project "Crust-β" actually
> refers to. Good starting points: `bitset` (14 functions, 12 tests, single file —
> a solid, self-contained showcase), `leftpad` (1 function — a trivial smoke test),
> or `lambda-calculus-eval` (a large multi-file interpreter with a type checker and
> β-reduction — much harder, if "β" hints at lambda calculus).

## Prerequisites

1. **Rust** (`cargo` on PATH) — <https://rustup.rs>.
2. **The CRUST-Bench dataset**, extracted so that `<dataset>/CBench` and
   `<dataset>/RBench` exist:
   ```bash
   git clone https://github.com/anirudhkhatry/CRUST-bench.git
   cd CRUST-bench && unzip datasets/CRUST_bench.zip -d datasets
   # -> datasets/CBench/<project>/...   and   datasets/RBench/<project>/...
   ```
3. An authenticated **GitHub Copilot CLI** (`copilot`) for a real run.

## Set up a target project

From this directory (`examples/crust-bench/`):

```powershell
# Windows PowerShell
./setup.ps1 -Project bitset -Dataset C:\path\to\CRUST-bench\datasets
```
```bash
# macOS / Linux
./setup.sh bitset /path/to/CRUST-bench/datasets
```

`setup` (a) copies a clean scaffold of the project's RBench crate (interfaces +
tests + `Cargo.toml`) into `.scaffold/`, and (b) generates `codeweaver.toml` from
`codeweaver.template.toml` with the resolved paths. `-Dataset` defaults to
`~/Desktop/_cw_local/CRUST-bench/datasets`.

## Run

```bash
cd ../..    # CodeWeaver repo root
# Offline smoke test of the orchestrator (no Copilot, no cost):
python -m codeweaver check --config examples/crust-bench/codeweaver.toml
# Real run:
python -m codeweaver run   --config examples/crust-bench/codeweaver.toml --app-id crust-bitset-001
```

The Planner copies `.scaffold/` → `pipeline/crate/` (the working copy the agents
fill in). Build/validate run `cargo build` / `cargo test` against that crate. The
run finishes when the whole test suite passes **and** the parity verifier confirms
every interface function is implemented.

## How it maps to CodeWeaver

| CodeWeaver concept | CRUST-Bench |
|--------------------|-------------|
| `source_dir` | `CBench/<project>` — the C code to transpile (read-only) |
| `reference_dirs` | the Rust `interfaces/` (contract) + `bin/` (tests/oracle), read-only |
| `immutable_input` | `.scaffold/` — a clean copy of the RBench crate; copied, never edited |
| `working_copy` | `pipeline/crate/` — where the agents write `src/<mod>.rs` implementations |
| `build_check` / `unit_test` / `validate` | `cargo build` / `cargo test` in the working copy |
| milestones | auto-generated from the interface + tests (skeleton → function groups → full suite) |
| parity | verifies every interface function / C behavior is implemented |

See `brief.md` for the full transpilation contract handed to every agent.

## Retarget to another project

Just re-run `setup` with a different `-Project`; it regenerates `codeweaver.toml`,
refreshes `.scaffold/`, and clears stale run state. List available projects with
`ls <dataset>/CBench`.

## Notes

- `codeweaver.toml`, `.scaffold/`, and `pipeline/` are **generated/local** and are
  gitignored — only the template, brief, README, and setup scripts are committed.
- CRUST-Bench is hard (in the paper, the best single-shot model solved only 15/100);
  CodeWeaver's milestone × repair × parity loop is designed to push further, but a
  large project may not reach 100% — inspect `pipeline/report.json` and
  `pipeline/parity.json` for where it stopped.
