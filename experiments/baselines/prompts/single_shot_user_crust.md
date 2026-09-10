Translate the C project `{{PROJECT}}` into Rust 2021.

You are given {{N_JAVA}} C source files and a Rust **interface skeleton** of
{{N_MODULES}} modules. Your task is to fill in every skeleton body with a faithful
translation of the corresponding C code.

## The contract — why signatures are not negotiable

The translation is judged by a fixed test suite you will **not** see. Those tests are
compiled against your code as part of the same crate and call it by exact path and
name:

```rust
use crate::<module>::{<Type>, <function>};
```

Therefore:

1. **Keep every module at its given path.** A correct implementation in the wrong
   file scores zero.
2. **Keep every type name, function name, parameter list, field name and signature
   exactly as the skeleton declares them.** Adding, removing or renaming a struct
   field breaks every sibling module that uses it, and the crate will not compile.
3. **Keep the skeleton's `pub` visibility.** A private item is invisible to the tests.
4. **Keep the skeleton's `use` declarations.** The modules must agree with each other:
   the whole crate is compiled together, and one disagreement fails the entire build.

## Faithfulness

The C source is the specification. Where your instinct and the C disagree, follow the
C. Preserve observable behaviour exactly: edge cases, integer width and wrapping,
signedness, iteration order, and error and return conventions.

C and Rust differ in ways that matter here:

- C's implicit integer promotion and wrapping have explicit Rust counterparts. Use
  `wrapping_*`, `saturating_*` or `checked_*` deliberately, and match the C's width.
- A C function returning an error code usually becomes `Result`, but only if the
  skeleton says so. Follow the skeleton.
- Manual allocation and `free` become ownership. Do not translate `malloc`/`free`
  literally; let Rust drop values.
- Raw pointer arithmetic usually becomes slice indexing or iterators.
- A `NULL` return usually becomes `Option::None`, again only if the skeleton says so.

Write safe Rust. Never cast `&T` to `&mut T` — that is undefined behaviour and the
compiler rejects it. Reach for `unsafe` only where the C genuinely requires it.

Use only the standard library and whatever crates the skeleton already imports. Do not
add dependencies.

## Output

Emit **every one of the {{N_MODULES}} modules below**, complete, in file-block format.
Do not omit a module because it is small or unchanged.

{{TARGET_PATHS}}

---

# C source

{{JAVA_FILES}}

---

# Rust interface skeleton (fill these in)

{{SKELETON_FILES}}
