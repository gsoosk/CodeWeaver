# Translation brief — CRUST-bench, C to Rust

Translate a C project into safe, idiomatic Rust 2021, conforming to a provided
interface skeleton and passing a held-out test suite you never see.

## What you are given

- `c-source/` — the original C project, read-only. **Its test directories have been
  removed.** They are the source the held-out Rust tests were generated from.
- `.scaffold/` — the Rust interface skeleton: a crate with `src/lib.rs` declaring
  every module, and one `src/<module>.rs` per module containing the public types and
  function signatures with `unimplemented!()` bodies.
- `pipeline/project/` — your working copy, initialised from the scaffold.

## The contract

The skeleton is the contract between modules and between you and the tests. The
held-out tests are compiled **as part of this crate** and call your code by exact
path and name.

1. Keep every module at its declared path, and keep `src/lib.rs` declaring every
   module the skeleton declares. Removing a module makes the crate compile by
   deleting the code that fails; the tests then fail to link. This is not a repair.
2. Keep every type name, function name, parameter list, field name and signature
   exactly as the skeleton declares them.
3. Keep `pub` visibility. A private item is invisible to the tests.
4. If a caller and a callee disagree, change the caller. Never change a declared
   interface to satisfy a caller.

## Faithfulness

The C source is the specification. Preserve observable behaviour exactly: edge
cases, integer width and wrapping, signedness, iteration order, and error and return
conventions.

Where C and Rust genuinely differ:

- C's implicit promotion and silent wrapping have explicit counterparts. Use
  `wrapping_*`, `saturating_*` or `checked_*` deliberately and match the C's width.
  Rust panics on overflow in debug builds where C wraps.
- Manual allocation and `free` become ownership. Do not translate `malloc`/`free`
  literally; let Rust drop values.
- Raw pointer arithmetic usually becomes slice indexing or iterators.
- An error code or `NULL` return often becomes `Result` or `Option` — but only if
  the skeleton says so. The skeleton wins.

Write safe Rust. Never cast `&T` to `&mut T`: that is undefined behaviour and the
compiler rejects it. Restructure the ownership instead. Reach for `unsafe` only
where the C genuinely requires it, and never to bypass the borrow checker.

Use only the standard library and whatever crates the skeleton already imports. Do
not add dependencies.

## What "done" means

`cargo build` succeeds, your own unit tests pass, and the held-out suite passes.
Because the whole crate compiles together, one cross-module disagreement fails
everything at once — so a module is not finished until the crate still builds with
it in place.
