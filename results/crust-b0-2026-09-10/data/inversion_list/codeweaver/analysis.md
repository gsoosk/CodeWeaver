# Inversion-List: C → Rust Port Analysis

## 1. Source Project Research

### Overview

`inversion-list` (C, at `c-source/`) is a small single-module library implementing a
**memory-efficient sparse set of unsigned integers**, represented as an *inversion list*:
a sorted flat array of `(start, end)` interval boundaries (`couples`) where each pair
`[couples[2k], couples[2k+1])` is a half-open range of members. This lets large runs of
consecutive integers be stored as two numbers instead of one entry per integer, and
supports standard set algebra (membership, union, intersection, difference, symmetric
difference, complement) plus ordering-style comparisons and two kinds of iterators
(over individual values and over `(inf, sup)` couples).

The library is C, built via CMake (`c-source/CMakeLists.txt`, `src/CMakeLists.txt`),
producing a shared/static lib from `src/inversion-list/inversion-list.c` against the
public header `inversion-list.h`. Its own `test/` directory (referenced by
`add_subdirectory(test)` in the top-level `CMakeLists.txt`) has been stripped for this
exercise — it is the held-out oracle's origin and must be treated as read-only/unknown.

### Directory structure and file responsibilities

- `CMakeLists.txt` — top-level build: enables testing, cppcheck/cclint/clang-format/
  flawfinder tooling, adds `src`, `test`, `docs` subdirectories, and CPack packaging.
- `src/CMakeLists.txt` — descends into `src/inversion-list`.
- `src/inversion-list/inversion-list.h` — **the public API contract**: opaque types
  `InversionList`, `InversionListIterator`, `InversionListCoupleIterator`, and every
  `extern` function signature (documented with Doxygen comments). This is the
  authoritative behavioral spec the Rust port must reproduce.
- `src/inversion-list/inversion-list.inc` — private struct layouts included only by the
  `.c` file: `_InversionList { capacity; support; size; unsigned int couples[]; }`
  (flexible array member holding the interval boundaries), `_InversionListIterator`
  (`set` pointer + scalar `index`, plus an unused `n[]` flexible array), and
  `_InversionListCoupleIterator` (`set` pointer + scalar `index`).
- `src/inversion-list/inversion-list.c` — the entire implementation (~500 lines): init/
  finish lifecycle with a global reference counter and an `atexit` invariant check,
  `_get_buffer`/realloc-based scratch buffer reused across calls, construction from raw
  values via `qsort` + de-duplication into intervals, membership via a custom
  `bsearch`-based lower-bound, clone/complement/to-string, relational and equality
  operators, n-ary varargs set-algebra ops (`union`, `intersection`, `difference`,
  `symmetric_difference`), and the two iterator families.
- `src/inversion-list/inversion-list.pc.in`, `InversionListConfig.cmake.in` — packaging
  metadata (irrelevant to porting).
- `docs/`, `Doxyfile`, `README.rst` — documentation; README states the project's intent
  (sparse integer sets via ranges) and build/test/lint instructions using `make test`,
  `make coverage`, `cppcheck`, `flawfinder`, `valgrind`.
- `cmake/` — CMake helper modules for the enabled tooling (FindCppCheck, FindCcLint, etc).

### Key structures / API surface (from `inversion-list.h` + `.inc`)

Opaque handle types (as C structs, only visible via functions):
- `InversionList` = `{ capacity: u32, support: u32, size: usize, couples: [u32] }` where
  `size` is the number of `u32` entries in `couples` (always even; `size/2` intervals).
  `capacity` is the exclusive upper bound of representable values (`0..capacity`).
  `support` is the count of set members (`inversion_list_support`).
- `InversionListIterator` = `{ set: *const InversionList, index: u32 }` — a **value**
  iterator; `index` walks candidate values `0.. couples[size-1]` and
  `inversion_list_iterator_get` recursively advances past non-members.
- `InversionListCoupleIterator` = `{ set: *const InversionList, index: u32 }` — a
  **couple** iterator; `index` is an interval index in `0..size/2`.

Full function surface (grouped):
- Lifecycle: `inversion_list_init`, `inversion_list_finish` — track a global counter
  `_counter` for how many "clients" are active; `finish` frees the shared scratch buffer
  and resets the `to_string` static cache when the counter drops to 0; an `atexit`
  handler asserts the counter returned to 0 (a debug/test-harness invariant, not part of
  the observable API contract itself).
- Construction/destruction: `inversion_list_create(capacity, count, values)` → sorts a
  copy of `values` (via a shared scratch buffer), rejects (`errno = EINVAL`, returns
  `NULL`) if any value `>= capacity`, and coalesces into intervals; `_destroy` frees.
- Accessors: `inversion_list_capacity`, `inversion_list_support`, `inversion_list_member`
  (binary search based).
- `inversion_list_clone`, `inversion_list_complement` (flips whether 0/`capacity` are
  boundary members), `inversion_list_to_string` (builds `"[v1, v2, ...]"` by expanding
  every interval to individual values — **note**: uses a process-global static string
  buffer, reset via `inversion_list_to_string(NULL)`).
- Comparisons: `equal`, `not_equal` (support count + raw `couples` equality),
  `less`/`less_equal`/`greater`/`greater_equal` (⚠ **buggy/non-standard**: `less` returns
  true merely if `set1` has smaller support *and* set2 has at least one member below
  set1's max boundary — this is not true subset-based ordering; the Rust port must
  reproduce this exact behavior, not "fix" it), `disjoint` (⚠ also just aliases
  `not_equal`, not real disjointness — again, faithfully reproduce as specified even
  though it looks like a bug, since it is the observable C behavior).
- Set algebra: `_union`/`_intersection`/`_difference` (static helpers, brute-force scan
  using `inversion_list_member`, output through `inversion_list_create`), exposed as
  n-ary varargs: `inversion_list_union(set, ...)`, `inversion_list_intersection(set,
  ...)`, `inversion_list_difference(set, ...)` (all terminated by a `NULL` sentinel
  argument), and `inversion_list_symmetric_difference(set1, set2)` = `(A∪B) - (A∩B)`.
- Iterators: `inversion_list_iterator_create/destroy/next/rewind/valid/get` (value
  iterator — `valid` compares `index < couples[size-1]`, i.e. index against the
  *last upper bound*, not `capacity`; `get` recurses over `next` until it finds a
  member) and `inversion_list_couple_iterator_create/destroy/next/rewind/
  iterator_couple_valid/get_inf/get_sup` (couple iterator over interval index).

### Data model / observable output contract

- The canonical **string representation** (`inversion_list_to_string`) is
  `"[v1, v2, v3, ...]"` — a comma-and-space separated ascending list of every member
  value (not compressed ranges), wrapped in `[` `]`, `"[]"` for an empty set.
- **Equality** is defined over `(support, size, couples[])`, i.e. structural equality
  of the interval array — this is what `PartialEq`/`Eq` in the scaffold must implement.
- **Membership** semantics: value `v` is a member iff it falls in some half-open
  interval `[couples[2k], couples[2k+1])`.
- Construction validates values against `capacity` (`value < capacity` required);
  violating this is the one explicit error path (`errno = EINVAL` in C).

### Error handling

C uses return-value-is-`NULL` + `errno` (`EINVAL` for out-of-range value at
construction, `ENOMEM` for allocation failure) as its only error-signaling mechanism.
The scaffold already collapses this to a single `Result`-based path:
`InversionListError::ValueOutOfRange(u32, u32)` (mirrors `EINVAL`) and
`InversionListError::Generic(String)` (catch-all, e.g. would stand in for `ENOMEM`,
which cannot occur in Rust's `Vec`-based design — allocation failure aborts rather than
returning `Result` in idiomatic Rust, so `Generic` is effectively unused/defensive).
All other C functions that never fail (accessors, comparisons, iterators) have no
error path in the C header, and the scaffold reflects this by using infallible
(non-`Result`) signatures for them.

### Dependencies

The C source depends only on the C standard library: `<assert.h>`, `<errno.h>`,
`<math.h>` (unused effectively), `<stdarg.h>` (varargs for n-ary set ops), `<stdbool.h>`,
`<stdio.h>` (`snprintf`/`printf` diagnostics), `<stdlib.h>` (`malloc`/`realloc`/`free`/
`qsort`/`bsearch`/`atexit`), `<string.h>` (`memcpy`/`strncpy`/`strlen`). No external
libraries. Build tooling only (CMake, cppcheck, cclint, flawfinder, valgrind, Doxygen)
is unrelated to runtime dependencies.

### Source's own unit tests

The `test/` directory that historically exercised this API (referenced in the top-level
`CMakeLists.txt` via `enable_testing()` / `add_subdirectory(test)`) has been **removed**
from `c-source/` per the brief — it is exactly the origin of the held-out Rust test
suite and must not be reconstructed or guessed at beyond what the header/`.inc`/`.c`
already specify. No mocking infrastructure exists in the source (it is a pure, allocation-
based data structure library with no I/O or external boundaries to mock), so there are no
source-side boundary-mocking patterns to mirror beyond "construct known sets, assert
observable derived values (support, string form, membership, equality, iteration order)".

## 2. Third-Party Library Analysis

| C facility | How the source uses it | Rust counterpart | Status |
|---|---|---|---|
| `malloc`/`realloc`/`free`, shared static scratch buffer (`_get_buffer`) | Manual heap management + buffer reuse across calls to avoid repeated allocation | `Vec<u32>` ownership; no shared/static scratch buffer needed — each function allocates its own `Vec` as needed | **Scaffold already models this**: `InversionList.intervals: Vec<(u32, u32)>` owns its data; no manual buffer required. Do not reintroduce a global buffer. |
| `qsort` + custom comparator (`_compare_unsigned_int`) | Sort raw values before coalescing into intervals | `slice::sort_unstable()` / `Vec::sort()` | Standard library only — no crate needed. |
| Custom `bsearch`-based `_lower_bound`/`_upper_bound` (via `_search` callback state) | Locate the interval boundary containing a query value for `member` | `slice::binary_search_by` / `partition_point`, or a direct scan over `Vec<(u32,u32)>` (support/size are small; correctness over cleverness) | Standard library only. |
| `errno` + `NULL` return | Only error signal (`EINVAL` for out-of-range value, `ENOMEM` for OOM) | `Result<T, InversionListError>` | **Already fully specified by the scaffold's `InversionListError` enum** — do not add a separate error crate (e.g. `thiserror`/`anyhow`); the skeleton's own enum plus manual `Display`/`Debug` (or none, since only `Debug` is derived) is the contract. |
| `<stdarg.h>` varargs (`inversion_list_union(set, ...)` etc., `NULL`-terminated) | N-ary set operations folding over an arbitrary list of sets | Ordinary Rust parameters: the scaffold's `union`/`intersection`/`difference`/
`symmetric_difference` are all **binary** (`&self, other: &Self) -> Self`) | The scaffold has already collapsed the C varargs API down to pairwise binary methods — callers needing n-ary behavior would fold over the binary method; no variadic mechanism (and no crate) is needed. |
| `snprintf`/manual string buffer growth (`_add_string`) | Build the `"[v1, v2, ...]"` string incrementally | `String` + `std::fmt::Write` / `format!` / iterator `+ join` | Standard library only (`to_str`/`Display` in the scaffold). |
| `assert(_counter == 0)` at `atexit`, `_counter` ref-count in `init`/`finish` | Debug-only lifecycle invariant checking, irrelevant to the pure-data-structure API since there is no global/shared state to initialize in idiomatic Rust | N/A — Rust's ownership model means there is no shared global scratch buffer or lifecycle counter to replicate; the scaffold has **no `init`/`finish` functions at all**, confirming this lifecycle plumbing is intentionally dropped from the target contract | Do not port `inversion_list_init`/`finish`; they existed only to manage the global buffer/static string, which the scaffold's per-instance `Vec`/`String` ownership eliminates entirely. |

No new external crates are required or permitted beyond the standard library (`Cargo.toml`
in `.scaffold` declares zero `[dependencies]`, and the brief forbids adding any). All
needs are met either by the standard library or by scaffolding already provided in
`inversion_list.rs`.

## 3. Target Project Design

### Overview & translation requirements

Functional equivalence is measured against a held-out test suite compiled into this
same crate (`pipeline/project`), exercising exactly the public items declared in
`.scaffold/src/inversion_list.rs` / `src/lib.rs`. The single module `inversion_list`
must be filled in behind the existing signatures with **no signature, name, or
visibility changes**. Because the scaffold's error and iterator types already encode
the target idioms (`Result` instead of `NULL`+`errno`; borrowed lifetimes instead of
raw pointers; `Vec<(u32,u32)>` instead of a flexible array member), the translation
work is: (a) construction/validation logic, (b) membership/search logic, (c) clone/
complement/to_str, (d) equality + the ordering-style comparison quirks (faithfully,
bugs included), (e) the three binary set-algebra ops + symmetric difference, (f) the
two iterators as real Rust `Iterator` impls.

### Source → target structural mapping

| C symbol | Rust target (`.scaffold/src/inversion_list.rs`) | Mapping notes |
|---|---|---|
| `struct _InversionList { capacity, support, size, couples[] }` | `struct InversionList { capacity: u32, support: u32, intervals: Vec<(u32,u32)> }` | `couples: [u32]` (flat, `size` entries) becomes `intervals: Vec<(u32,u32)>` (`size/2` entries) — each `(couples[2k], couples[2k+1])` pair becomes one tuple. `size` itself is *not* a field on the Rust struct; recover it as `intervals.len()*2` wherever the C code reads `set->size`. |
| `inversion_list_create(capacity, count, values)` | `InversionList::new(capacity: u32, values: &[u32]) -> Result<Self, InversionListError>` | `count`/`values` pointer collapse to a slice; sort a local copy, validate `value < capacity` else `Err(InversionListError::ValueOutOfRange(value, capacity))`, coalesce into `intervals` exactly as the C coalescing loop does. No shared scratch buffer — allocate locally. |
| `inversion_list_destroy` | *(none — `Drop` is automatic)* | Do not add an explicit destroy; ownership handles it. |
| `inversion_list_capacity` / `_support` | `capacity(&self) -> u32` / `support(&self) -> u32` | Direct field returns. |
| `inversion_list_member` | `contains(&self, value: u32) -> bool` | Reproduce the lower-bound-on-flattened-array semantics: value is a member iff it lies in some `[lo, hi)` interval — can be done directly over `intervals` without reimplementing the raw bsearch machinery. |
| `inversion_list_clone` | `clone_list(&self) -> Self` | Plain field-wise `Clone` (or hand-rolled) — note the scaffold also derives `Clone`, but the header exposes a `clone` operation as a *method* (`clone_list`) distinct from `#[derive(Clone)]`'s `clone()`, so both must exist; `clone_list` can simply call `self.clone()` (derived) or reconstruct fields. |
| `inversion_list_complement` | `complement(&self) -> Self` | Reproduce exactly the C boundary logic: if the set starts at `0` and ends at `capacity`, drop those two boundary entries; if neither, add both; otherwise add/drop only the missing one. `support` becomes `capacity - support`. |
| `inversion_list_to_string` | `to_str(&self) -> String` + `impl Display` | Expand every interval into individual member values, join with `", "`, wrap in `[`/`]`. No process-global static cache — return an owned `String` each call. `Display::fmt` should delegate to the same logic (or call `to_str`). |
| `inversion_list_equal` / `_not_equal` | `equal(&self, other: &Self) -> bool` + `impl PartialEq`/`Eq` | Structural equality over `(support, intervals)` — implement `PartialEq::eq` directly comparing fields (matches C's `support` + raw `couples` compare), and have `equal()` call the same logic (or vice versa). No separate `not_equal` method exists in the scaffold — callers use `!=` / `.ne()` from the derived/`PartialEq` machinery, or negate `.equal()`. |
| `inversion_list_less` | `is_strict_subset_of` conceptually named but **must reproduce the C behavior verbatim**: true iff `self.support < other.support` AND scanning values `0..self.intervals.last().1` finds at least one member of `other` | Faithfully port the odd C logic (support-based ordering + a "first member" probe), not a corrected proper-subset test — the header names it `less`, the scaffold names the method `is_strict_subset_of`; despite the more suggestive Rust name, behavior must match C's `inversion_list_less` exactly, since that is the oracle. |
| `inversion_list_less_equal` | `is_subset_of(&self, other: &Self) -> bool` | `self.equal(other) || self.is_strict_subset_of(other)`, mirroring `less_equal = equal || less`. |
| `inversion_list_greater` / `_greater_equal` | *(no direct scaffold method — greater(A,B) = less(B,A))* | Not present as separate scaffold methods; if a held-out test needs "greater" semantics it will call `is_strict_subset_of`/`is_subset_of` with swapped operands. No action needed beyond correct `is_strict_subset_of`/`is_subset_of`. |
| `inversion_list_disjoint` | `is_disjoint(&self, other: &Self) -> bool` | C's `disjoint` is literally `not_equal` (a quirk/bug) — reproduce faithfully as `!self.equal(other)`, i.e. do **not** implement true set-disjointness, to stay faithful to the observed C contract. |
| `_union`/`inversion_list_union` (varargs) | `union(&self, other: &Self) -> Self` | Collapsed to binary; brute-force scan from `min(self.start, other.start)` to `max(self.end, other.end)` collecting values where either `contains`, then rebuild via interval-coalescing (equivalent to calling the same construction coalescing logic used in `new`, but since support/values are already known, coalesce directly rather than requiring `capacity` re-validation failure paths — capacity is `max(self.capacity, other.capacity)`). |
| `_intersection`/`inversion_list_intersection` | `intersection(&self, other: &Self) -> Self` | Mirror the C two-pointer interval-walk logic (or an equivalent brute-force membership scan restricted to overlapping regions) — must match observable results in edge cases (empty overlap, touching intervals). |
| `_difference`/`inversion_list_difference` | `difference(&self, other: &Self) -> Self` | Mirror the C two-pointer walk collecting values in `self` but not `other`. Note the C `_difference` has a leftover bug (`min = MAX(set1->couples[0], set1->couples[0])` — always `set1`'s first boundary, not `MAX(set1_min, set2_min)`); reproduce it faithfully since it is the specification, unless the held-out oracle indicates otherwise (it cannot be inspected, so default to literal fidelity). |
| `inversion_list_symmetric_difference` | `symmetric_difference(&self, other: &Self) -> Self` | `difference(union(self,other), intersection(self,other))`, exactly as the C composes it. |
| `InversionListIterator` (`set`, `index`) + `_create/_destroy/_next/_rewind/_valid/_get` | `struct InversionListIterator<'a> { list: &'a InversionList, interval_index: usize, current_value: u32 }` implementing `Iterator<Item = u32>` | The scaffold already redesigns the C "manual index + valid + get" pattern into idiomatic Rust `Iterator::next()`. Semantics to preserve: iterate ascending member values in order (equivalent to what `_get`/`_next`/`_valid` produce), terminating once past the last interval — `interval_index`/`current_value` are the natural fields to drive this without needing raw pointer bounds. |
| `InversionListCoupleIterator` (`set`, `index`) + `_create/_destroy/_next/_rewind/_valid/_get_inf/_get_sup` | `struct InversionListCoupleIterator<'a> { list: &'a InversionList, couple_index: usize }` implementing `Iterator<Item = (u32, u32)>` | Yields `intervals[couple_index]` then advances; `couple_index < intervals.len()` is the validity check (mirrors `index < size/2` in C). |
| `inversion_list_init` / `_finish` | *(not present in scaffold — omit)* | These only managed C's global scratch buffer/static string lifetime; Rust's per-value ownership makes them unnecessary. Do not add equivalents. |

### Module structure (target)

Mirrors the source's single-module shape and the scaffold exactly:

```
pipeline/project/
├── Cargo.toml            (no dependencies; unchanged)
└── src/
    ├── lib.rs            pub mod inversion_list;      (unchanged — do not remove)
    └── inversion_list.rs  <- fill in all `unimplemented!()` bodies here
```

No new modules, files, or dependencies are to be introduced. All implementation work
happens inside `inversion_list.rs`, replacing `unimplemented!()` bodies while keeping
every signature, field name, and visibility exactly as declared.

### Output/contract mapping per milestone

1. **Construction & basic accessors** — `InversionList::new`, `capacity`, `support`,
   `contains`. Contract: `new` returns `Err(ValueOutOfRange(v, capacity))` iff any input
   value `>= capacity`; otherwise returns a set whose `capacity()`/`support()`/
   `contains()` match the C semantics (coalesced intervals, de-duplicated support count).
2. **Clone, complement, string form, equality** — `clone_list`, `complement`, `to_str`,
   `Display`, `equal`, `PartialEq`/`Eq`. Contract: `to_str()` produces
   `"[v1, v2, ...]"` in ascending order (empty ⇒ `"[]"`); `complement()` support =
   `capacity - support` with correct boundary-interval add/drop; equality is exact
   `(support, intervals)` structural comparison.
3. **Ordering-style comparisons** — `is_strict_subset_of`, `is_subset_of`,
   `is_disjoint`. Contract: byte-for-byte behavioral parity with the C
   `less`/`less_equal`/`disjoint` functions, quirks included (these are *not* true
   subset/disjoint tests in the C source and must not be "corrected").
4. **Set algebra** — `union`, `intersection`, `difference`, `symmetric_difference`.
   Contract: binary methods producing sets whose `intervals`/`support` match running
   the equivalent brute-force membership scan the C `_union`/`_intersection`/
   `_difference` implement (including the difference bug noted above), with
   `capacity = max(self.capacity, other.capacity)`.
5. **Iterators** — `InversionListIterator`/`InversionListCoupleIterator` as real
   `Iterator` impls. Contract: value iterator yields ascending members exactly once
   each (equivalent output to walking `_next`/`_get` until invalid in C); couple
   iterator yields each `(inf, sup)` pair in interval order.

### Boundary & error-handling strategy

There are no external I/O, filesystem, network, or FFI boundaries in this library —
it is a pure, in-memory data structure. Therefore:
- The **only boundary requiring an explicit Result** is `InversionList::new`'s input
  validation (`value < capacity`), mapped to the scaffold's
  `InversionListError::ValueOutOfRange(u32, u32)`. All other C `NULL`/`errno` paths were
  either allocation failures (not modeled in safe Rust — `Vec` growth failure aborts the
  process rather than returning an error) or the removed `init`/`finish` lifecycle, so no
  further `Result`-returning surface is needed; keep every other scaffold method
  infallible exactly as declared.
- `InversionListError::Generic(String)` exists in the scaffold for forward-compatibility
  (e.g., if any construction path needs a generic failure) — leave it defined and only
  reach for it if a genuinely new failure mode is required by an already-declared
  signature; do not invent new fallible signatures.
- No `unsafe` is required anywhere in this port: all C pointer arithmetic over the
  flexible-array `couples` becomes ordinary `Vec<(u32,u32)>` indexing/iteration.

### Unit-test strategy (mockable seams)

This is a **pure computation library with no external dependencies to mock** (no
network, filesystem, clock, or randomness) — the C source's own removed tests would
have been plain assert-based behavioral tests against known input sets, not
boundary-mocking tests. Consequently:
- No trait-based mock/real boundary split is needed (there is nothing to fake); the
  entire `InversionList` API is deterministic and directly testable by constructing
  known instances and asserting on `support()`, `contains()`, `to_str()`, `equal()`,
  and the iterator sequences they produce.
- New unit tests (written alongside the implementation, e.g. in a `#[cfg(test)] mod
  tests` block at the bottom of `inversion_list.rs`, matching idiomatic Rust
  convention and not conflicting with any held-out external test file) should cover,
  per milestone above: (1) construction success/`ValueOutOfRange` failure and interval
  coalescing (adjacent vs. disjoint values), (2) complement boundary cases (starts at
  0 / ends at capacity / neither / both), to-string of empty and non-empty sets,
  equality of equal/differently-shaped sets, (3) the exact `less`/`less_equal`/
  `disjoint` quirk-behaviors on constructed pairs where the "correct" set-theoretic
  answer would differ from the C algorithm's answer (to lock in fidelity, not
  correctness), (4) union/intersection/difference/symmetric_difference on
  overlapping, disjoint, and touching interval pairs, and (5) iterator exhaustion
  order and count for both iterator types, including on an empty set.
- Because the held-out suite is compiled into this same crate and calls these exact
  paths, these new unit tests are purely additive validation for the Translator/
  Validator agents and must not redeclare or shadow any scaffold item.

### Milestone mapping

| Milestone | Source functionality ported | New unit tests |
|---|---|---|
| M1 — Construction & accessors | `inversion_list_create` (validation + coalescing), `_capacity`, `_support` | Construction success/failure, interval coalescing, capacity/support accessors |
| M2 — Representation & equality | `_clone`, `_complement`, `_to_string`, `_equal`/`_not_equal` | Clone independence, complement boundary cases, `to_str` formatting, equality/inequality |
| M3 — Comparisons | `_less`, `_less_equal`, `_greater`(implicit), `_greater_equal`(implicit), `_disjoint` | Faithful-quirk tests for `is_strict_subset_of`/`is_subset_of`/`is_disjoint` |
| M4 — Set algebra | `_union`/`inversion_list_union`, `_intersection`/`inversion_list_intersection`, `_difference`/`inversion_list_difference`, `inversion_list_symmetric_difference` | union/intersection/difference/symmetric_difference over overlapping, disjoint, touching, and empty inputs |
| M5 — Iterators | `InversionListIterator` + `_create/_next/_rewind/_valid/_get`, `InversionListCoupleIterator` + its analogous functions | Full-traversal order/count for both iterators, empty-set iteration |

---

Confirmed: `<repo>/examples/crust/subjects/inversion_list/pipeline/analysis.md` has been written.
