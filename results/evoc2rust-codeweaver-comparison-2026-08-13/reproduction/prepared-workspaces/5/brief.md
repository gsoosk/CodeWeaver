# EvoC2Rust Vivo-Bench comparison: bloom-filter

Translate the target C module group (bloom-filter) under `source/target/` into the
ABI-compatible Rust skeleton under `scaffold/src/production/`. This is fixed
test group 5 of 15, covering 1 of the 19
Vivo-Bench modules used by EvoC2Rust (DOI 10.1145/3786583.3786856).

## Required behavior

- Preserve every generated `#[no_mangle] extern "C"` symbol, `repr(C)` layout,
  public field, callback type, argument type, and return type.
- Replace every `unimplemented!()` production body with working Rust behavior.
- Prefer safe internal data structures and thin ABI adapters. Keep unsafe code
  narrowly scoped because the paper reports SafeRate.
- The immutable tests exercise allocation failure, memory release, collection
  behavior, callbacks, ordering, and boundary conditions.
- C support modules linked only by the evaluator: hash-string.

## Scientific integrity constraints

- Never edit or weaken `oracle/`, `scaffold/`, `immutable_evaluator.py`, Cargo
  topology, test names, or module wiring to gain credit.
- Implement production behavior only in `pipeline/target`.
- C2Rust is used only to derive signatures and fixed tests. Its production
  bodies are intentionally absent from this workspace.
- Independent evaluation restores trusted files in a temporary copy and runs
  each of the 6 fixed tests separately.

Paper: https://arxiv.org/abs/2508.04295v4
