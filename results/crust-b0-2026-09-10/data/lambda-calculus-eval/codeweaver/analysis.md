# Analysis: `lambda-calculus-eval` C → Rust port

## 1. Source project research

### Overview
A toy typed lambda-calculus interpreter (CLI `lc`). It reads a `.lambda` source
file (or an interactive/CLI-produced temp file), tokenizes and parses it into an
`AstNode` tree, resolves `def`/`import`/`type` declarations into a hash table,
type-checks the parsed expression, then beta/eta-reduces it (applicative or
normal order) and prints the resulting AST as a string. Behavior can be driven by
a `config` file (`file=`, `step_by_step_reduction=`, `reduction_order=`) or by an
interactive CLI in `bin/main.c` (`bin/` is **not** mirrored by the scaffold, so the
interactive/CLI entry point is out of scope for the port — only `src/*` and
`hash-table/*` have `.scaffold` counterparts).

### Directory structure and responsibilities
- `src/common.h`/`common.c` — shared `AstNode` tagged-union type (`LAMBDA_EXPR`,
  `APPLICATION`, `VAR`, `DEFINITION`), the `HANDLE_NULL` fatal-null macro, verbose
  logging (`set_verbose`/`print_verbose`/`print_ast_verbose`), fatal `error()`,
  a printf-style `format()` allocator, and a growable-buffer AST stringifier
  (`append_to_buffer`, `append_ast_to_buffer`, `ast_to_string`).
- `src/config.h`/`config.c` — `Options` (file handle, step-by-step flag,
  reduction order), `trim()`, `get_config_type()` (maps a config key string to
  `option_type_t`), `parse_config()` (splits a `key=value` line), and
  `get_config_from_file()` which reads `CONFIG_PATH` (`"config"`) line by line via
  `getline` and builds `Options`, opening the referenced lambda file with
  `io::get_file`.
- `src/io.h`/`io.c` — thin `FILE*` wrappers: `create_file`, `get_file`,
  `write_to_file`, `delete_file`, `close_file`, and `next()` (a `fgetc` wrapper
  returning the byte cast to `char`, including the cast of `EOF`(-1)).
- `src/parser.h`/`parser.c` — hand-written recursive-descent parser and
  lexer: `parse_token` (char → `tokens_t`), `is_variable`, `peek`/`peek_print`
  (lookahead via `fgetc`+`ungetc`), `consume`/`expect` (fatal on mismatch),
  AST constructors (`create_variable/_application/_lambda`), `alpha_convert`
  (appends a fresh `_N` suffix using a `static int n` counter to disambiguate
  shadowed binders), `is_used`/`table_exists`-backed lookups, and the grammar
  functions `parse_lambda`, `parse_expression`, `parse_import`,
  `parse_definition`, `parse_type_definition`, `parse_type`, `parse_variable`,
  plus `free_ast` for manual deallocation.
- `src/reducer.h`/`reducer.c` — reduction engine: `set_reduction_order`/
  `print_reduction_order`, `reduce()` (expand defs → reduce → verbose trace),
  `expand_definitions()` (in-place replacement of `DEFINITION` nodes with the
  looked-up AST, mutating the node's union fields directly), `replace()`
  (renames a bound variable through a subtree, used after `alpha_convert`),
  `reduce_ast()` (recursive beta-reduction honoring `reduction_order_t`:
  applicative reduces arguments eagerly, normal reduces lazily),
  `substitute()` (capture-avoiding-ish substitution — no real capture avoidance
  besides parser-time alpha-conversion), and `deepcopy*` helpers used by
  substitution to avoid aliasing subtrees.
- `src/typechecker.h`/`typechecker.c` — simple structural type checker:
  `Type`/`TypeEnv` (linked list env), `typecheck()` (VAR/APPLICATION/
  LAMBDA_EXPR cases; application asserts `type_equal` of function and argument
  types then returns the function's type — a known TODO in the source, it does
  not currently return a proper arrow-type's codomain), `type_equal`,
  `get_type_from_expr`, `create_type`/`parse_function_type`,
  `expr_type_equal`, `add_to_env`/`lookup_type`, and the fatal `assert_()`.
- `hash-table/hash_table.h`/`hash_table.c` — separate-chaining hash table keyed
  by `char*`, values are `AstNode*` (nullable): `hash` (djb2, mod
  `HASH_TABLE_SIZE`=2000), `insert`, `table_exists` (true iff bucket non-empty —
  **not** key-exact, a source quirk to preserve), `search` (key-exact, returns
  `NULL` if absent or if stored value is `NULL`), `delete_c`,
  `createHashTable`/`destroyHashTable`.
- `bin/main.c` — CLI entry point (interactive prompts or `config`-driven),
  wires config → parse → typecheck → reduce → print. **Out of scope**: no
  `.scaffold` module exists for it, no `bin`/`main` target is declared, so it
  must not be ported.
- `examples/*.lambda`, `src/config` — sample programs and a sample config file
  demonstrating `type`, `def`, `import "path"`, and typed lambda syntax.
- `vim-lambda/` — editor syntax highlighting, irrelevant to the port.
- `Makefile` — builds `lc` from `src/*.c` + `hash-table/hash_table.c`, and (when
  present) compiles/links a `tests/` directory via `make test`. **The `tests/`
  directory has been removed** from this checkout (per the brief) — there are no
  source unit tests to inspect directly. The Makefile's shape (one test binary
  per `tests/%.c`, all linked against every non-main object file) tells us the
  original tests exercised each module's public C API directly against real
  `HashTable`/`FILE*`/`AstNode` values — i.e., no mocking framework, just plain
  state fixtures (in-memory hash tables, small hand-built ASTs, `tmpfile()`-style
  file fixtures for `io`/`config`). The Rust unit-test strategy below is designed
  to reproduce that same style of direct, fixture-based testing per module.

### Key data model / observable output contract
- `AstNode` (tagged union) is the single value threaded through parsing,
  reduction and typechecking; its only externally observable serialization is
  `ast_to_string` / `print_ast`, which renders parenthesized lambda syntax, e.g.
  `(@x : Bool.(VAR x)) ` — this exact textual shape (parens, spacing, `@x : T.`)
  is the contract any port must reproduce byte-for-byte, since the CLI's final
  output is `ast_to_string(reduced)`.
- `Options` (config.h) is the parsed run configuration; `HashTable`
  (hash_table.h) is the shared definition/type/lambda-scope table used by both
  the parser (defs, types, bound-variable membership) and reducer (definition
  expansion).
- `Type`/`TypeEnv` (typechecker.h) model the (currently simplistic, non-arrow)
  type-checking contract: equal string type names, no arrow-type inference
  beyond the source's existing TODOs — the port must **not** "fix" this, only
  reproduce it.

### Error handling
Two fatal styles, both terminate the process (no recoverable error path in the
core library):
1. `HANDLE_NULL(ptr)` — logs to stderr and calls `abort()`.
2. `error(msg, file, line, func)` — logs to stderr and calls `exit(EXIT_FAILURE)`.
`parser.c`'s `expect()` prints directly and calls `exit(EXIT_FAILURE)`. There is
no `errno`/return-code convention; syntax and configuration errors are always
fatal, matching a toy interpreter design.

### Dependencies
Only the C standard library: `stdio.h`, `stdlib.h`, `string.h`, `stdbool.h`,
`stdarg.h`, `ctype.h`, `math.h` (only `log10`/`abs` in `alpha_convert`, to size a
decimal counter string). No third-party C libraries, no threading, no networking.

### Source unit tests
As noted, `c-source/`'s `tests/` directory has been stripped for this exercise
(the CRUST-bench harness generated the held-out Rust tests from those C tests
and hides them). There is nothing to read directly; the Makefile's `test` target
confirms tests were plain per-module C executables (no mocks/stubs — direct
calls against real hash tables/files/ASTs), which is the pattern the Rust
unit-test strategy in §3 reproduces.

## 2. Third-party library analysis

The C source has **zero** third-party dependencies — only libc. Consequently
there is nothing to map to an external crate, and the brief forbids adding
dependencies anyway. Concretely:

| C need | Provided by | Target approach |
|---|---|---|
| `malloc`/`free`, manual `AstNode*` graphs | libc | Rust ownership: `Box<AstNode>` / `Option<Box<AstNode>>` (already baked into the scaffold's `LambdaExpression.body`, `Application.function/argument` fields) — **do not** call `Box::leak` or replicate `malloc`/`free` calls; let Rust drop values. |
| `FILE*` I/O (`fopen`, `fgetc`, `ungetc`, `fputs`, `remove`, `fclose`) | libc `stdio.h` | `std::fs::File` + `std::io::{Read, Write, Seek, SeekFrom, BufRead}`, exactly as already imported by `.scaffold/src/io.rs` and `.scaffold/src/config.rs` (`BufRead` for a `getline`-equivalent line reader). This need is **already met by the scaffold's imports** — no new crate required. `ungetc`-style single-byte pushback must be reimplemented with `Seek::seek(SeekFrom::Current(-1))` since `File` has no pushback buffer. |
| djb2 hash table (`hash_table.c`) | hand-rolled | The scaffold's `hash_table.rs` already replaces the C singly-linked-list buckets with `std::collections::HashMap<String, common::AstNode>` — **use it as declared**; do not reintroduce manual chaining/bucket arithmetic. Only `hash()` itself (djb2 mod `HASH_TABLE_SIZE`) needs a faithful arithmetic port (as `u32`, wrapping to match C's `unsigned long` truncation into `% HASH_TABLE_SIZE`), even though the scaffold's `HashMap` no longer strictly needs a custom hash function — keep `hash()` as a pure function for behavioral parity/testability since the skeleton still declares it. |
| `vsnprintf`-based `format()` | libc `stdarg.h` | Rust's `std::fmt`/`format!` machinery. The scaffold's `common::format(fmt: &str, args: fmt::Arguments) -> String` and `print_verbose(format: &str, args: fmt::Arguments)` already commit to `std::fmt::Arguments` as the va_list equivalent — already met by scaffold, no `printf`-clone crate needed. |
| `log10`/`abs` (`alpha_convert` counter width) | libc `math.h` | Not actually needed in Rust: `to_string()`/`format!("_{}", n)` sizes itself automatically; no digit-counting or manual buffer sizing is required. |
| fatal `exit()`/`abort()` | libc `stdlib.h` | `std::process::exit(1)` for `error()`-style fatal paths (matches `exit(EXIT_FAILURE)`); a genuine Rust `panic!()`/`unreachable!()` only where the C used `abort()` via `HANDLE_NULL` on a truly-impossible-null invariant. Already met by std — no crate needed. |

No new crates are recommended or permitted; everything above is satisfied by
`std` and by the scaffold's existing `use` statements.

## 3. Target project design

### Overview & translation requirements
Functional equivalence is measured by the held-out `cargo test` oracle compiled
against the exact signatures in `.scaffold/src/*.rs`. Every module, type, and
function in the scaffold must be filled in with a body that reproduces the
observable behavior of the corresponding C code — most importantly the exact
textual shape of `ast_to_string`/`print_ast`, the exact reduction results for
applicative vs. normal order, the exact type-check pass/fail behavior
(including its known limitations), and the exact hash-table lookup semantics
(`table_exists` = bucket non-empty, not key-exact).

### Source → target structural mapping
One Rust module per C translation unit, same names, same public surface:

| C file | Rust module (scaffold) | Notes |
|---|---|---|
| `src/common.h/.c` | `common.rs` | `AstNode`/`AstNodeType`/`AstNodeUnion`/`LambdaExpression`/`Application`/`Variable`/`tokens_t` all already declared. **Key idiom shift**: C's `char* type` (nullable) becomes `String` (non-`Option`) in the scaffold — model "no type" as `String::new()` (empty string), exactly mirroring how C's parser only supplies a type for constants/typed binders and leaves others `NULL`. Any equality/printing logic must treat `""` as "absent" the same way C code treats `NULL` (`if (type != NULL)` ⇒ `if !type_.is_empty()`). |
| `src/config.h/.c` | `config.rs` | `Options.file: File` (not `Result`) — `get_config_from_file()` must resolve any file-open failure internally (fatal, e.g. `.expect(...)`/`panic!`), matching C's fatal `error()` inside `get_config_from_file`/`get_file`. |
| `src/io.h/.c` | `io.rs` | Signatures return `io::Result<_>` — unlike C's abort-on-failure, the *io* boundary is explicitly fallible in the skeleton; propagate `Result` (`?`) rather than panicking inside `io.rs` itself. Callers (`config.rs`) that need C's fatal behavior convert `Err` → panic/exit at their boundary. |
| `src/parser.h/.c` | `parser.rs` | `peek`/`consume`/`expect`/grammar functions unchanged in name and shape. `peek(in_: &mut File) -> char` (not `Result`) forces an internal EOF-sentinel convention (see below) since Rust has no `EOF` macro. |
| `src/reducer.h/.c` | `reducer.rs` | Signatures take `&AstNode`/`&mut AstNode` distinctly per function — this is a deliberate ownership split from the C, which mutates through raw pointers everywhere. `expand_definitions`/`replace` take `&mut AstNode` (in-place mutation, matching C). `reduce`, `reduce_ast`, `substitute`, `deepcopy*` take `&AstNode` and **return an owned `AstNode`** — these must be implemented as tree-**reconstruction** (build new owned nodes / clone subtrees as needed), not in-place pointer surgery, since the borrow checker forbids mutating through a shared reference. This is a required, not optional, structural deviation from the C. |
| `src/typechecker.h/.c` | `typechecker.rs` | `TypeEnv` becomes an owned singly-linked list via `Option<Box<TypeEnv>>` (already declared) instead of C's raw `TypeEnv*`; `add_to_env(env: &mut Option<Box<TypeEnv>>, ...)` mirrors C's `add_to_env(TypeEnv **env, ...)` (double-pointer ⇒ `&mut Option<Box<_>>`). `typecheck`'s TODO limitation (application returns the function's own type, not a computed codomain) must be preserved exactly, not "fixed". |
| `hash-table/hash_table.h/.c` | `hash_table.rs` | Backing store swaps `HashNode` chains for `std::collections::HashMap<String, common::AstNode>`, per the scaffold. Because the map's value type is `common::AstNode` (not `Option<AstNode>`), the C behavior of inserting a `NULL` value (used only to mark "this identifier is bound/used", not "this identifier has a definition") must be modeled via the sentinel produced by `impl Default for AstNode` (also declared `unimplemented!()` in the scaffold — the Translator must define it, e.g. an empty `VAR` node with empty name/type). `insert(table, key, common::AstNode::default())` reproduces `insert(table, key, NULL)`; `search()` must return `None` when the stored value is this default sentinel, reproducing C's `search` returning `NULL` for NULL-valued entries. `table_exists` must remain the C's *bucket-based* semantics is not reproducible with a `HashMap` (there are no buckets) — with a `HashMap` backing store, `table_exists` becomes equivalent to key-presence (`contains_key`), which is the natural/expected simplification the scaffold's replacement of chaining buckets with a `HashMap` implies; this is a case where the scaffold's chosen data structure legitimately changes the micro-behavior of a rarely-hit corner case (hash collisions triggering `table_exists` false positives in C) — acceptable because the skeleton, not the C internals, is the contract. |

### Module structure (target)
Mirrors the scaffold exactly (already the working copy layout):
```
src/lib.rs          -- declares: common, config, io, parser, hash_table, reducer, typechecker
src/common.rs
src/config.rs
src/io.rs
src/parser.rs
src/hash_table.rs
src/reducer.rs
src/typechecker.rs
```
No `main.rs`/`bin/` — the CLI entry point (`bin/main.c`) has no scaffold module
and must not be added (would not match any declared module; also brief forbids
inventing modules/binaries not in the skeleton).

### Output/contract mapping per milestone
- **common**: `ast_to_string`/`append_ast_to_buffer`/`print_ast_verbose` must
  reproduce the exact C string format per node type: LAMBDA_EXPR ⇒
  `"(@" + param + " : " + type + " ." + <body> + ") "`; APPLICATION ⇒
  `"(" + <function> + <argument> + ") "`; VAR ⇒ `"(" + name + [" : " + type if
  type present] + ") "`; DEFINITION ⇒ `"(" + name + ") "`; unknown ⇒
  `"(UNKNOWN) "`. This is the single most test-sensitive contract in the whole
  project since it's the CLI's final printed artifact.
- **hash_table**: `insert`/`search`/`table_exists`/`delete` must satisfy: insert
  then search returns the inserted value (unless it's the `Default` sentinel, in
  which case search returns `None`); delete then search returns `None`.
- **io**: `create_file`/`get_file`/`write_to_file`/`delete_file`/`close_file`
  round-trip byte-identical content through a real file on disk; `next` reads one
  byte and advances the cursor by one (mirroring `fgetc`).
- **config**: `trim` strips leading/trailing whitespace exactly as C's
  `isspace`-bounded `memmove` version (including the same off-by-one edge
  behavior for all-whitespace / single-char strings); `get_config_type` maps
  `"file"`/`"step_by_step_reduction"`/`"reduction_order"` to the matching enum
  variant and any other key to `CONFIG_ERROR`; `parse_config` splits exactly on
  the first `=` (via `strtok`-equivalent split) and trims both sides;
  `get_config_from_file` must fail the same way C does when `file=` is missing
  or malformed.
- **parser**: `parse_token` char→token mapping must match exactly (including
  that `is_variable` accepts `_` plus ASCII letters, so e.g. `'_'` ⇒ VARIABLE,
  not ERROR); `parse_expression`/`parse_lambda`/`parse_definition`/
  `parse_import`/`parse_type_definition`/`parse_type`/`parse_variable` must
  reproduce the exact grammar and error strings/behavior (fatal on malformed
  input, mirroring `expect()`/`error()`); `alpha_convert` must produce the same
  `"<name>_<n>"` shape with a process-wide monotonically increasing counter
  (module-level mutable state, e.g. via `std::sync::atomic` or a `static mut`-free
  cell type, mirroring C's `static int n`).
- **reducer**: `reduce_ast` must implement applicative order (reduce function
  and argument fully, then beta-reduce, continuing to reduce the *result* only
  when order is normal — note the actual C logic: applicative returns the
  reduced substitution directly without recursing further, normal recurses via
  `reduce_ast` again) and normal order (lazy argument) exactly as coded, not as
  commented; `substitute` must implement the same (limited, non-alpha-safe at
  substitution time — safety comes only from `alpha_convert` during parsing)
  variable replacement; `expand_definitions` must replace `DEFINITION` nodes
  with the looked-up AST from the table (fatal via `HANDLE_NULL` if absent —
  mirror with a panic, since the scaffold's `expand_definitions` returns `()`
  not `Result`).
- **typechecker**: `typecheck` must reproduce the exact three cases (VAR,
  APPLICATION, LAMBDA_EXPR) and the known non-arrow-codomain limitation on
  APPLICATION; `type_equal`/`expr_type_equal` string-equality semantics
  (including the null/`""`-vs-null asymmetry handling) must match exactly.

### Error-handling & boundary strategy
- Fatal, process-terminating C errors (`error()`, `HANDLE_NULL`, `expect()`) ⇒
  `common::error()` prints to stderr and calls `std::process::exit(1)`
  (`EXIT_FAILURE` ≡ 1); truly-impossible-null invariants (`HANDLE_NULL`) ⇒
  `panic!`/`unreachable!` with an equivalent stderr-style message, since neither
  is part of the tested contract's happy path.
- The one place the skeleton deliberately introduces `Result` is `io.rs`
  (`create_file`, `get_file`, `write_to_file`, `delete_file`, `close_file`,
  `next` all return `io::Result<_>`). This is a genuine "skeleton wins"
  divergence from C: implement these as real fallible operations that
  propagate `std::io::Error` via `?`, and let *callers* (e.g. `config.rs`,
  whose `Options.file: File` and whose `get_config_from_file() -> Options`
  return type is not `Result`) decide to `.expect()`/panic on failure,
  reproducing the observable "fatal on bad file" behavior at the boundary
  where the C code called `error()`.
- EOF sentinel: because `parser::peek`/related lexer helpers return plain
  `char` (no `Result`, no `Option`), and Rust has no `EOF` macro, define one
  internal, consistently-used sentinel char (e.g. a private-use scalar such as
  `'\u{FFFF}'`, chosen because it cannot appear in valid ASCII lambda source)
  and use it uniformly everywhere the C compared against `EOF` (`peek(in) !=
  EOF`, `while ((c = peek(f)) != EOF)`, etc.), including in the byte read
  itself: `File` has no `ungetc`; implement `peek` as "read one byte via
  `Read::read`, then `Seek::seek(SeekFrom::Current(-1))` to un-consume it",
  translating a genuine end-of-file `Read` result of `0` bytes into the
  sentinel rather than attempting to seek back past EOF.

### Unit-test strategy (mockable seams)
The source's own `tests/` are removed, but the Makefile's structure (one plain
executable per module, all linked against the real, non-mocked object files)
tells us the original tests used direct fixtures rather than mocks — the boundary
types in this project (`File`, `HashTable`) are cheap, real, and local (no
network/DB/clock), so the idiomatic Rust unit-test strategy is **fixture-based,
not mock-based**:
- **`common`**: unit tests build small `AstNode` trees by hand (e.g. a `VAR`
  with a type, a one-level `LAMBDA_EXPR`, a two-level `APPLICATION`) and assert
  `ast_to_string`/`append_ast_to_buffer` produce the exact expected strings
  (including trailing spaces from the C implementation). Live in
  `src/common.rs` under `#[cfg(test)] mod tests`.
- **`hash_table`**: tests exercise `HashTable::new/insert/search/table_exists/
  delete` directly against small in-memory tables — no I/O, trivially testable
  without mocks. Includes a `Default` round-trip test proving `search` returns
  `None` for a `Default::default()`-valued ("NULL"-equivalent) entry.
  Live in `src/hash_table.rs`.
- **`io`**: the mockable seam is the filesystem itself; tests use
  `tempfile`-style real temp files under `std::env::temp_dir()` (created and
  cleaned up per test, since no `tempfile` crate is permitted) to round-trip
  `create_file`→`write_to_file`→`get_file`→`next`, and assert `delete_file`
  removes them and subsequent `get_file` errors. No mock trait is warranted
  here because the C original never abstracted `FILE*` behind an interface —
  faithfully mirror that by testing against real (temp) files, not mocks.
- **`config`**: tests write a small temp `config`-formatted file/string and
  feed it through `trim`/`get_config_type`/`parse_config` directly (pure
  string functions, no I/O needed for those three); `get_config_from_file`
  itself is exercised against a real temp file at `CONFIG_PATH`-style paths
  (or, if the test needs isolation from the fixed `"config"` path, at minimum
  `parse_config`/`get_config_type`/`trim` are unit-tested purely).
- **`parser`**: the mockable seam is `File` used purely as an in-memory byte
  cursor; tests write a `&str` fixture to a temp file (or use
  `std::io::Cursor`-backed helpers where the signature allows, though the
  scaffold pins parser functions to `&mut File`, so use small real temp files)
  and assert the resulting `AstNode` shape and/or its `ast_to_string`
  rendering — mirroring how `parser.c`'s own likely tests parsed literal
  strings into ASTs and asserted `print_ast`/`ast_to_string` output.
- **`reducer`**: tests build small typed lambda ASTs in-memory (no file I/O
  needed) and assert `reduce_ast`/`substitute`/`deepcopy*` produce the expected
  reduced tree (compared via `ast_to_string`, since `AstNode` has no
  `PartialEq`), for both `APPLICATIVE` and `NORMAL` reduction orders — this
  exercises `set_reduction_order` as the seam controlling which branch runs.
- **`typechecker`**: tests build small ASTs with matching/mismatched types and
  assert `typecheck` succeeds/panics (via `assert_`) appropriately, and that
  `type_equal`/`expr_type_equal`/`lookup_type` behave per the documented
  (limited) semantics.
- All new unit tests are **new**, mirroring the removed C tests' style
  (direct, fixture-based, no mocking framework) rather than translated 1:1,
  since the original test sources are unavailable in this checkout. They live
  inline in each `src/<module>.rs` under `#[cfg(test)]`, consistent with
  Rust convention and with `unit_test.sh`'s expectation of `cargo test`-visible
  unit tests inside the working copy (Layer 1), separate from the held-out
  oracle (Layer 2).

### Milestone mapping
Ordered by the C dependency graph (`#include`s) so each milestone's crate still
builds and its own unit tests can run before the next lands:
1. **common** — `AstNode`/`tokens_t` model, `Default for AstNode`, verbose
   logging, `error`, `format`, buffer/AST-to-string. No internal deps.
2. **hash_table** — depends only on `common::AstNode`. Implements `hash`,
   `insert`/`search`/`table_exists`/`delete`, `createHashTable`/
   `destroyHashTable` (likely a no-op/identity wrapper in Rust, since
   `HashTable::new()` already owns its `HashMap` and drop is automatic).
3. **io** — depends only on `std::fs`/`std::io`; independent of the above two
   but ordered here because `config` and `parser` both need it.
4. **config** — depends on `io` (file opening) and `common::format`/`error`
   (via the fatal-path convention).
5. **parser** — depends on `common`, `hash_table`, and (via `io::next`) `io`.
   Implements the lexer/grammar and `alpha_convert`/`free_ast`.
6. **reducer** — depends on `common`, `hash_table`, `parser` (uses
   `common::AstNode` shapes and, per `reducer.h`'s C includes, `parser.h`),
   and `config::reduction_order_t`. Implements `reduce`/`reduce_ast`/
   `substitute`/`expand_definitions`/`replace`/`deepcopy*`.
7. **typechecker** — depends only on `common::AstNode`. Can be built any time
   after milestone 1, but is sequenced last here since it is the least
   coupled to the rest and easiest to validate independently once `AstNode`
   fixtures already exist from earlier milestones' tests.

Each milestone's "done" bar is: the module's `unimplemented!()` bodies are
replaced, `cargo build` still succeeds for the whole crate (per
`build_check.sh`), and that module's own new unit tests pass (Layer 1) before
moving to the next milestone.

---

**Confirmation**: this document has been written to
`<repo>/examples/crust/subjects/lambda-calculus-eval/pipeline/analysis.md`.
It contains three sections — (1) Source project research (overview, per-file
responsibilities, data model/output contract, error handling, dependencies, and
the state of the now-removed source unit tests), (2) Third-party library
analysis (no third-party C deps; std-only Rust mappings, all already satisfied
by the `.scaffold` imports, with no new crates recommended), and (3) Target
project design (structural module mapping, module layout, per-module output
contract, error/boundary strategy including the `io::Result` vs. fatal-`error()`
divergence and the EOF-sentinel and hash-table-`Default`-sentinel decisions,
fixture-based unit-test strategy per module, and a 7-step dependency-ordered
milestone plan) — with no Rust implementation code included, as required.
