# Project brief — CRUST-Bench: C → safe, idiomatic Rust

Transpile the C repository at the **source** directory into **safe, idiomatic
Rust** in the working copy, so that it **conforms to the provided Rust interface**
and **passes the provided Rust tests**. This is a CRUST-Bench task
(arXiv:2504.15254): the interface and tests are fixed specifications you must
satisfy — never weaken or edit them.

## The working copy (what you start from and produce)
The working copy is a Cargo crate copied from the benchmark's `RBench` project. It
contains:
- `src/interfaces/<mod>.rs` — the **interface (contract)**: the exact public types
  (structs/enums) and function signatures your implementation must match, with
  `unimplemented!()` bodies. **Read-only. Never modify.**
- `src/bin/tests.rs` (and any other `src/bin/*.rs`) — the **tests (the oracle)**:
  `#[test]` functions that call the interface. **Read-only. Never modify or weaken.**
- `Cargo.toml`, `src/lib.rs` — the crate manifest and root module.

**What you must produce:** for each interface module `<mod>` (a file
`src/interfaces/<mod>.rs`), create `src/<mod>.rs` that implements **exactly** the
public types and function signatures declared in the interface, by faithfully
translating the corresponding C code, and make sure `src/lib.rs` declares
`pub mod <mod>;` for each. The tests import items as `use <crate>::<mod>::<item>`,
so each module must live at the **crate root** (`src/<mod>.rs`), mirroring the
interface's module name. Do NOT put your implementation inside
`src/interfaces/` — that directory is the contract only.

## Correctness contract (the oracle)
`cargo test` (in the working copy) compiles the crate and runs the provided tests.
The transpilation is correct when **the crate builds** and **all provided tests
pass**. There is no separate mock layer for this benchmark — the provided tests
are both the fast gate and the authoritative oracle, so the unit-test and
end-to-end commands are the same `cargo test`.

## Safe, idiomatic Rust (hard requirements)
- **Match the interface signatures exactly** — types, ownership, borrowing,
  mutability (`&`, `&mut`, slices, `Vec`, `Box`, `Option`, `Result`, `usize`, …).
  The annotators chose these to be safe and idiomatic; honor them.
- **Prefer safe Rust.** Translate C idioms to safe constructs:
  - raw pointers → references / slices / `Vec<T>` / `Box<T>`;
  - `malloc`/`free` → owned types with RAII (no manual free);
  - `char*` / C strings → `&str` / `String` / `&[u8]`;
  - out-parameters → return values or `&mut` arguments as the interface dictates;
  - error codes / sentinel returns → `Option` / `Result` where the interface uses them.
  Avoid `unsafe` unless the interface itself requires it; if you must, isolate and
  justify it. Do not add third-party dependencies unless unavoidable.
- Preserve the C program's observable behavior — the tests encode it.

## Milestones (guidance for the scope stage)
- **M0 — skeleton:** create `src/<mod>.rs` for every interface module with the
  exact signatures and `unimplemented!()` bodies, and wire `src/lib.rs`, so
  `cargo build` compiles. (Tests will still fail at M0 — that is expected.)
- **Then**, implement functions in dependency order, grouped by the tests they
  satisfy, replacing `unimplemented!()` with real translations, until `cargo test`
  passes. Each milestone's gate is the subset of test functions it should make green.
- **Final / golden:** the entire provided test suite passes.

## Parity (end-of-run check)
Every function and type declared in the interface — and every C behavior the tests
exercise — must have a faithful Rust implementation. No `unimplemented!()`,
`todo!()`, or stubbed function bodies may remain. The parity verifier compares the
C source against your Rust and schedules any missed piece as a new milestone.

## Hard boundaries
- Create/edit only implementation files under the working copy's `src/` (e.g.
  `src/<mod>.rs`) and `src/lib.rs`.
- **Never modify** `src/interfaces/**` (the contract), `src/bin/**` (the tests),
  or the C source.
- Keep the crate compiling; never leave a syntax error or a missing module file.
