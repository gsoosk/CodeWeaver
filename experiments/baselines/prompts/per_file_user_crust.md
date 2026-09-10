Translate one C translation unit of the project `{{PROJECT}}` into Rust 2021.

You are given the C source (its header and, where one exists, its implementation
file) and the single Rust **interface skeleton** module that corresponds to it. Fill
in that skeleton with a faithful translation. Every other module of this project is
being translated separately and will exist at its declared path, so translate only
the unit you are given.

## The contract — why signatures are not negotiable

The translation is judged by a fixed test suite you will **not** see. Those tests are
compiled against your code as part of the same crate and call it by exact path and
name:

```rust
use crate::<module>::{<Type>, <function>};
```

Therefore:

1. **Keep the module at its given path.** A correct implementation in the wrong file
   scores zero.
2. **Keep every type name, function name, parameter list, field name and signature
   exactly as the skeleton declares them.** Adding, removing or renaming a struct
   field breaks every sibling module that uses it, and the crate will not compile.
3. **Keep the skeleton's `pub` visibility.** A private item is invisible to the tests.
4. **Keep the skeleton's `use` declarations.** Sibling modules exist at those paths
   and expose exactly the items the skeleton names.
5. If the skeleton declares a type or constant you would rather define differently,
   the skeleton wins. It is the shared contract between modules translated
   independently.

## Faithfulness

The C source is the specification. Where your instinct and the C disagree, follow the
C. Preserve observable behaviour exactly: edge cases, integer width and wrapping,
signedness, iteration order, and error/return conventions.

C and Rust differ in ways that matter here:

- C's implicit integer promotion and wrapping have explicit Rust counterparts. Use
  `wrapping_*`, `saturating_*` or `checked_*` deliberately, and match the C's width.
- A C function returning an error code usually becomes `Result`, but only if the
  skeleton says so. Follow the skeleton.
- Manual allocation and `free` become ownership. Do not translate `malloc`/`free`
  literally; let Rust drop values.
- Raw pointer arithmetic usually becomes slice indexing or iterators.
- A `NULL` return usually becomes `Option::None`, again only if the skeleton says so.

Use only the standard library and whatever crates the skeleton already imports. Do
not add dependencies.

## Output

Emit exactly one file block, complete, for this module and nothing else:

  - {{TARGET_PATH}}

---

# C source

{{JAVA_FILE}}

---

# Rust interface skeleton (fill this in)

{{SKELETON_FILE}}
