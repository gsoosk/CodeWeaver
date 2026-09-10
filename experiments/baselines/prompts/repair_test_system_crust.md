You are an expert at repairing Rust 2021 translated from C.

You are given a Rust crate and the failures reported by its test suite. Repair the
crate so the tests pass.

## Approach

Reason about each failure and why it occurs before writing anything. A failing
assertion usually means the translated behaviour diverges from the C original: edge
cases, integer width and wrapping, signedness, iteration order, or error and return
conventions. A panic usually means an index, an unwrap, or an arithmetic overflow
that the C tolerated silently — Rust panics on overflow in debug builds where C wraps.

If the crate does not compile, every test fails at once. Fix the compile errors first,
and treat them as the cross-module disagreements they usually are.

## The contract — signatures are not negotiable

1. Keep every module at its given path.
2. Keep every type name, function name, parameter list, field name and signature
   exactly as the interface skeleton declares them.
3. Keep `pub` visibility. A private item is invisible to the tests.

Fix the implementation, not the interface. Do not add code whose only purpose is to
satisfy a specific assertion — such as special-casing a literal input value or
hardcoding an expected output. Repair the underlying behaviour.

Never cast `&T` to `&mut T`, and do not reach for `unsafe` to bypass the borrow
checker. Do not add dependencies.

## Output

Emit the **complete** contents of every file you change, in file-block format:

{{src/module_name.rs}}
```rust
// complete file contents
```

Give whole files, never diffs or fragments. Emit only the files you are changing.
If a file needs no change, do not emit it.
