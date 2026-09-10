# C-ACES → Rust Port: Analyzer Design Document

## 1. Source Project Research

### 1.1 Overview

`c-source` is **C-ACES**, a C11 implementation of ACES (Arithmetic Channel
Encryption Scheme), a fully-homomorphic-encryption (FHE) cryptosystem based on
category theory (Yoneda Lemma), per Tuyéras, arXiv:2401.13255. The scheme
encrypts a message `m ∈ Zp` into a ciphertext `(c1, c2)` in a polynomial ring
`Zq[X]_u` (polynomials over `Zq` modulo a public polynomial `u`), and supports
homomorphic addition (`aces_add`, fully implemented), a placeholder for
homomorphic multiplication (`aces_mul`, a no-op stub in the C source), and a
level-refresh operation (`aces_refresh`).

Top-level tasks/components:
- **Common** — number theory & RNG helpers (gcd/xgcd, coprimality, ranges,
  Box-Muller normal sampling, min/max/clamp).
- **Matrix** — dense row-major 2D matrices (`Matrix2D`) and arrays of them
  (`Matrix3D`), plus randomized invertible-matrix-pair generation used to build
  the secret key tensor `lambda`.
- **Polynomial** — arbitrary-length integer-coefficient polynomials over a
  modulus, with add/sub/mul/lshift/mod/degree/fit/scaler ops.
- **Channel** — the arithmetic channel tuple `(p, q, w)` with an invariant
  check (`p² < q` and `gcd(p,q)=1`).
- **Aces-internal** — key-material generators: `generate_error`,
  `generate_vanisher`, `generate_linear`, `generate_u`, `generate_secret`,
  `generate_f0`, `generate_f1`.
- **Aces** — the public API: `set_aces` (manual arena allocator for a single
  contiguous `mem` buffer), `init_aces`, `aces_encrypt`, `aces_decrypt`,
  `aces_add`, `aces_mul` (stub), `aces_refresh`.

### 1.2 Directory Structure & File Responsibilities

```
c-source/
  CMakeLists.txt        static lib "CAces"; -DNDEBUG in Release; links libm;
                         CACES_TEST/CACES_BENCHMARK/CACES_EXAMPLE add_subdirectory
                         options — the `tests/` subdir is referenced but has been
                         removed from this checkout (held-out oracle source).
  coverage_report.json  per-file line coverage from the original (now-removed)
                         test suite — 13 entries matching the 6 .c/.h pairs plus
                         aggregate; confirms unit tests existed per-module.
  README.md             scheme description + a worked example (encrypt/add/decrypt).
  scripts/run-clang-format.sh
  src/
    include/Common.h    Xgcd, Pair structs; gcd/xgcd/are_coprime/randinverse/
                         randrange/normal_rand; inline max/min/clamp.
    Common.c             implementations; normal_rand uses Box-Muller with libc
                         rand()/RAND_MAX; randrange uses rand() % range.
    include/Matrix.h     Matrix2D{dim, data:*u64}, Matrix3D{data:*Matrix2D, size},
                         Transformer fn-pointer typedef, TRANSFORM_COUNT=3;
                         inline row/get/set accessors.
    Matrix.c             matrix2d_multiply (mod q), swap_transform,
                         linear_mix_transform, scale_transform,
                         matrix2d_eye, fill_random_invertible_pairs (applies a
                         random sequence of the 3 transforms to build an
                         invertible pair (m, invm) with m·invm ≡ I mod q).
    include/Polynomial.h Coeff = int64_t; Polynomial{coeffs:*Coeff, size};
                         PolyArray{polies:*Polynomial, size}; full op set below.
    Polynomial.c         poly_free/get_polynomial/get_polyarray/set_polynomial
                         (malloc-based ctors), set_zero, coef_sum, poly_degree,
                         poly_fit (strips leading zero coeffs + reduces mod q),
                         poly_mul/poly_add/poly_sub/poly_lshift/poly_mod/
                         poly_sub_scaler/poly_add_scaler, poly_equal.
    include/Channel.h    Parameters{dim,N}; Channel{p,q,w}; init_channel.
    Channel.c            init_channel: forces q = (p+1)^2 if p²<q && coprime(p,q)
                         fails (note: condition is inverted/defensive — see §3).
    include/Aces-internal.h / Aces-internal.c
                         generate_error/vanisher/linear (secret-dependent
                         randomized polynomials whose evaluation at ω yields
                         specific values), generate_u (builds the public modulus
                         polynomial u with random zero/nonzero coefficient
                         pattern), generate_secret (builds invertible matrix
                         pair via Matrix.c, derives secret PolyArray x and the
                         3-tensor `lambda` via poly_mul + poly_mod +
                         matrix2d_multiply), generate_f0 (random PolyArray),
                         generate_f1 (f1 = poly_mod(Σ f0_i·x_i, u)).
    include/Aces.h / Aces.c
                         PublicKey{u, lambda}, PrivateKey{x, f0, f1},
                         SharedInfo{channel, param, pk}, Aces{shared_info,
                         private_key}, CipherMessage{c1: PolyArray, c2:
                         Polynomial, level}. set_aces carves one `void*
                         memory` buffer (via manual pointer bumping) into all
                         the buffers needed for u, lambda, x, f0, f1 — this is
                         a hand-rolled arena allocator, purely a C memory-
                         management artifact. init_aces wires channel → u →
                         secret → f0 → f1. aces_encrypt builds (c1,c2) from a
                         message using r_m/e/b. aces_decrypt inverts it via
                         `Σ c1_i·x_i`, subtract from c2, reduce mod p.
                         aces_add adds two ciphertexts component-wise mod u,
                         sums levels. aces_mul is UNIMPLEMENTED (returns 0,
                         touches nothing — "TODO: Implement it"). aces_refresh
                         subtracts `k*p` from c2 and decrements level.
```

### 1.3 Key Data Models / Observable Contract

- `Xgcd{gcd:u64, a:i64, b:i64}`, `Pair{first:u64, second:u64}` (Common).
- `Matrix2D{dim:size_t, data:*u64}` row-major; `Matrix3D{data:*Matrix2D, size}`.
- `Coeff = int64_t`; `Polynomial{coeffs:*Coeff, size}`,
  `PolyArray{polies:*Polynomial, size}` — coefficients are stored **most-
  significant-first** (index 0 is highest degree; `poly_degree` returns
  `size-1-i` for first nonzero `i`; `poly_fit` strips leading (low-index)
  zeros).
- `Parameters{dim:u64, N:u64}`, `Channel{p:u64, q:u64, w:u64}`.
- `PublicKey{u:Polynomial, lambda:Matrix3D}`,
  `PrivateKey{x:PolyArray, f0:PolyArray, f1:Polynomial}`,
  `SharedInfo{channel, param, pk}`, `Aces{shared_info, private_key}`,
  `CipherMessage{c1:PolyArray, c2:Polynomial, level:u64}`.
- Public API return convention: `int`, `0` = success, `-1` = error (buffer too
  small in `set_aces`/`get_polynomial`/`get_polyarray`, size mismatch in
  `poly_add`/`poly_sub`, invalid leading coeff or degree ordering in
  `poly_lshift`, `size>1` in `aces_encrypt`/`aces_decrypt`). Some functions
  ignore/always return an ambiguous fixed value (e.g. `scale_transform` returns
  `1` despite its own doc comment saying it's a typo and "should be 0";
  `matrix2d_multiply`/`swap_transform`/`linear_mix_transform`/`matrix2d_eye`/
  `fill_random_invertible_pairs`/`aces_add`/`aces_refresh` always return 0 and
  never actually fail in practice).

### 1.4 Error Handling

The C code has **no exceptions**; all error signaling is via `int` return
codes (0 success / -1 failure) or via silently-defaulted/garbage behavior on
invalid input (no bounds checks on raw pointer arithmetic; `set_aces` is the
only place that pre-validates buffer size against a computed `required`
byte count before doing any writes).

### 1.5 Dependencies

- **libc**: `stdlib.h` (`malloc`/`free`, `rand`, `RAND_MAX`), `string.h`
  (`memcpy`/`memset`/`memcmp`), `math.h` (`pow`, `sqrt`, `log`), `stdint.h`
  fixed-width integers, `stddef.h` (`size_t`).
- **libm**: linked via CMake (`target_link_libraries(CAces PRIVATE m)`) for
  `pow`/`sqrt`/`log`/`cos` used in `Channel.c` and `Common.c`.
- No other third-party C libraries.

### 1.6 Source Unit Tests

The `tests/` directory referenced by `CMakeLists.txt`
(`if (CACES_TEST) add_subdirectory(tests) endif()`) **has been removed from
this checkout** — it is exactly the held-out oracle basis (per the project
brief: "CRUST generated its Rust tests from those C tests"). `coverage_report.json`
is the only remaining artifact, showing 13 coverage entries (one per .c file
plus aggregates) with per-module line coverage between 54–100%, confirming
each module (`Common`, `Matrix`, `Polynomial`, `Channel`, `Aces-internal`,
`Aces`) had dedicated unit tests exercising most branches, with `aces_mul`
(112 lines, 0% coverage) understood to be entirely untested since it is an
unimplemented stub. No test source, no mocking framework references, or
boundary-mock patterns are recoverable from the current checkout; the design
below infers seams purely from the module boundaries and function
signatures in the headers.

## 2. Third-Party Library Analysis

| C dependency | Used for | Rust counterpart | Status |
|---|---|---|---|
| `stdlib.h` `rand()`/`RAND_MAX` | Uniform random ints for `randrange`, `normal_rand`'s Box-Muller uniforms | `rand` crate (`rand::rng()` / `Rng::random_range`) | **Already provided** — `.scaffold/Cargo.toml` declares `rand = "0.9.0"` and `matrix.rs` already imports `rand::Rng`. Use it directly; do not add a new RNG dependency. |
| `math.h` `sqrt`, `log`, `cos`, `pow` | Box-Muller transform in `normal_rand`; `p²`/`(p+1)²` and coprimality check in `init_channel` | Rust `f64` primitive methods `.sqrt()`, `.ln()`, `.cos()`, `.powi()/.powf()` (std, no crate needed) | **Standard library covers this fully** — no new dependency. |
| `stdlib.h` `malloc`/`free` (Polynomial.c `get_polynomial`/`get_polyarray`/`poly_free`) | Manual heap allocation for polynomial coefficient arrays | `Vec<Coeff>` / `Vec<Polynomial>` with ordinary Rust ownership; drop happens automatically | **Already modeled in scaffold** — `polynomial.rs`'s `Polynomial{coeffs: Vec<Coeff>}` and `PolyArray{polies: Vec<Polynomial>}` replace the malloc/free pair entirely; no `get_polynomial`/`get_polyarray`/`poly_free` equivalents are declared in the skeleton (the C project's manual heap layer is intentionally erased). |
| Hand-rolled arena allocator in `Aces.c`'s `set_aces` (single `void *memory` buffer sliced via pointer bumping into Coeff/Matrix2D/Polynomial sub-regions) | Avoids per-object heap allocation; lets caller supply pre-allocated static/stack memory | Ownership via `Vec`s inside `Aces`/`SharedInfo`/`PrivateKey`, no arena needed | The Rust `set_aces(aces: &mut Aces, dim: usize, mem: &mut [u8]) -> Result<()>` signature retains the `mem: &mut [u8]` parameter for interface parity with the C signature, but since every field (`Polynomial.coeffs`, `PolyArray.polies`, `Matrix3D.data`) is already a `Vec` owned independently, the port should **not** replicate raw pointer slicing into `mem`; it should size-check `mem.len()` against an equivalent "required capacity" computation (for parity with the C bounds check) and then construct the `Vec`-backed fields directly with `vec![0; ...]`/`Vec::with_capacity` at the correct dimensions, mirroring the C function's *effect* (correctly-sized, zero-initialized buffers) rather than its *mechanism* (pointer arithmetic into a shared arena). |
| No JSON/serialization, no threading, no file I/O in the C source | n/a | n/a | Nothing to add. |

**Summary**: no new Rust crates are required beyond what the scaffold already
declares (`rand`, `rand_distr` — the latter is available in `Cargo.toml`
though not yet imported in the skeleton; it may be used for
`normal_rand`/Box–Muller if a Normal distribution sampler is preferred over
hand-rolled Box-Muller, but a literal translation using `rand::Rng` plus
`f64::ln/sqrt/cos` is equally valid and closer to the source). Do not add
`libm`, custom RNG, or allocator crates.

## 3. Target Project Design

### 3.1 Overview & Translation Requirements

Functional equivalence is measured by the held-out `cargo test` suite
compiled into this crate; it will call the exact public paths declared by
the scaffold (`src/lib.rs` + one file per module). The port must preserve:
- **Coefficient ordering** (most-significant-first) and all index-arithmetic
  (`poly_degree`, `poly_fit`, `poly_lshift`/`poly_mod`) exactly as C computes
  them, including on `size == 0`/empty-vector edge cases.
- **Modular arithmetic semantics**: C's `%` on `int64_t`/`uint64_t` follows
  C's truncating/toward-zero rules for signed operands (used pervasively in
  `Polynomial.c`'s subtraction and in `poly_lshift`, where results can be
  negative and are then corrected: `res < 0 ? res + mod : res`). Rust's `%`
  on signed integers also truncates toward zero, matching C's rule for
  same-signedness operands — replicate the exact `if res < 0 { res + mod }`
  correction pattern rather than relying on `rem_euclid` (which changes the
  observable branch for equal results but is safe to use only if it produces
  bit-identical output — verify sign correction lines up before substituting).
- **Integer width and wrapping**: All arithmetic is on `u64`/`i64` exactly as
  C declares (`uint64_t`, `int64_t`, `size_t`→`usize` in the Rust port
  where the skeleton uses `usize` for lengths/indices, e.g. `Matrix2D.dim:
  usize`, `Polynomial` indices). Multiplication in `matrix2d_multiply` and
  `poly_mul` (`u64 * u64`, `i64 * i64`) can overflow for large `q`; the C
  code relies on silent 64-bit wraparound. Because these are cryptographic
  moduli expected to stay well below 2^32 in the reference examples, prefer
  `wrapping_mul`/`wrapping_add`/`wrapping_sub` at the exact spots the C
  performs raw `*`/`+`/`-` on `uint64_t`/`int64_t`, so debug-build panics
  don't diverge from C's release-mode wrapping behavior; do not use
  `checked_*` (that would introduce a behavior — an early return/panic —
  the C code never has).
- **RNG-dependent functions are not required to reproduce the exact same
  sequence as C's `rand()`** (different PRNGs), but must preserve C's
  *bounds and distributional shape*: `randrange(lower, upper)` is inclusive
  `[lower, upper]` (`rand() % (upper - lower + 1) + lower`); this must map
  to `rand::Rng::random_range(lower..=upper)` (inclusive), not
  `lower..upper`.
- **Error/return conventions**: The C `int` 0/-1 convention becomes
  `Result<T, AcesError>` exactly where the skeleton already declares
  `Result<...>` return types (every non-getter function in the skeleton).
  Use `Err(AcesError::GenericError(msg))` for the C `-1` paths (bad buffer
  size in `set_aces`, size mismatch in `poly_add`/`poly_sub`, invalid input
  in `poly_lshift`, `size > 1` in `aces_encrypt`/`aces_decrypt`). Where C
  always returns 0 (no real failure path — e.g. `matrix2d_eye`,
  `swap_transform`, `aces_add`, `aces_refresh`), the Rust function should
  still return `Result<()>` per the skeleton's signature, wrapping in
  `Ok(())`; do not invent new fallible cases beyond what C actually checks.
- Accessor-style C functions that only ever fail on out-of-bounds indices
  (`matrix2d_get`/`matrix2d_set`/`matrix3d_get`/`matrix2d_row`, all
  `static inline` with **no bounds check** in C) map to `Option`-returning
  methods in the skeleton (`Matrix2D::get/set/row/row_mut` return
  `Option`/`Result`) — this is a place the skeleton **adds** safety C never
  had (out-of-bounds C access is UB; Rust must not panic via raw indexing —
  use `.get()`/`.get_mut()` and return `None`/`Err` instead of `[]` indexing).

### 3.2 Source → Target Structural Mapping

| C file/symbol | Rust module/symbol (from `.scaffold`) | Notes |
|---|---|---|
| `include/Common.h`, `Common.c` | `src/common.rs` | `Xgcd`, `Pair` structs preserved verbatim (field names/types); `gcd`, `xgcd`, `are_coprime` (C `int`→Rust `bool`), `randinverse`, `randrange`, `normal_rand`, `max`, `min`, `clamp` all preserved 1:1 by name. `are_coprime`'s C `int` (0/1) becomes idiomatic `bool` per skeleton. |
| `include/Matrix.h`, `Matrix.c` | `src/matrix.rs` | `Matrix2D{dim,data}` (data: `*u64`→`Vec<u64>`), `Matrix3D{data,size}` becomes `Matrix3D{data: Vec<Matrix2D>}` (skeleton drops the redundant `size` field — use `data.len()`). Free functions `matrix2d_multiply`, `swap_transform`, `linear_mix_transform`, `scale_transform`, `matrix2d_eye`, `fill_random_invertible_pairs` preserved as free functions taking `&mut Matrix2D`/`&Matrix2D` per skeleton signatures (not methods) — matches C's free-function style. `matrix2d_row/get/set` and `matrix3d_get` (C static inline, header-only) become `Matrix2D::row/row_mut/get/set` methods and are **removed** as a free `matrix3d_get` — replaced by `Matrix3D::get_mut`, since skeleton has no free `matrix3d_get`; all interior callers (`aces_internal.rs`, `aces.rs`) must call `lambda.get_mut(i)` instead. `Transformer` fn-pointer typedef and `TRANSFORM_COUNT` are C-only plumbing for `fill_random_invertible_pairs`'s dispatch table — no equivalent public type in skeleton; implement the dispatch internally (e.g. a local array of function pointers/closures) without exposing new public items. |
| `include/Polynomial.h`, `Polynomial.c` | `src/polynomial.rs` | `Polynomial{coeffs: Vec<Coeff>}` (drops explicit `size` field — use `coeffs.len()`), `PolyArray{polies: Vec<Polynomial>}` (drops `size` — use `polies.len()`). C's malloc-based `get_polynomial`/`get_polyarray`/`poly_free`/`set_polynomial` collapse into `Polynomial::new(coeffs: Vec<Coeff>)`/`PolyArray::new(polies: Vec<Polynomial>)` (ownership replaces manual alloc/free). `poly_equal`→`derive(PartialEq)` (skeleton already derives `PartialEq, Eq`) instead of a function — callers use `==`. `coef_sum`, `degree` (was `poly_degree`), `set_zero`, `fit` (was `poly_fit`), `add`/`sub`/`mul`/`lshift` (was `poly_lshift`)/`poly_mod`/`sub_scaler`/`add_scaler` become **methods on `Polynomial`** (`self: &Polynomial` or `&mut Polynomial` for in-place ones) per the skeleton's `impl Polynomial` block, rather than free functions taking `(poly1, poly2, result)` triples — the "result" out-parameter pattern becomes a returned `Result<Polynomial>`, and in-place mutators (`poly_fit`, `poly_mod`) take `&mut self`. |
| `include/Channel.h`, `Channel.c` | `src/channel.rs` | `Parameters{dim,N}` preserved (note skeleton keeps the non-idiomatic uppercase field name `N` verbatim — do not rename). `Channel{p,q,w}` preserved. C's single `init_channel(channel, p, q, w) -> int` splits into `Channel::new` (unconditional constructor) and `Channel::init` (skeleton's doc: "Initializes a channel and checks that `p < q`") returning `Result<Self>` — see §3.4 for how the C auto-correction of `q` maps here. |
| `include/Aces-internal.h`, `Aces-internal.c` | `src/aces_internal.rs` | All 7 functions (`generate_error`, `generate_vanisher`, `generate_linear`, `generate_u`, `generate_secret`, `generate_f0`, `generate_f1`) preserved as free functions with identical names and parameter order, all now returning `Result<()>` instead of C's `int`/`uint64_t` (note: C's `generate_vanisher`/`generate_linear` *return* the sampled `k` value in addition to writing through `e`/`b` — the skeleton's Rust signature drops that return value entirely (`Result<()>`), so any caller in `aces.rs`/`aces_internal.rs` that used the C return value of `generate_vanisher`/`generate_linear` must be restructured to not need it, OR the k must be recomputed/stored differently — checked against C call sites: **neither `init_aces` nor any other caller uses the returned `k`**, so this is safe to drop). |
| `include/Aces.h`, `Aces.c` | `src/aces.rs` | `PublicKey`, `PrivateKey`, `SharedInfo`, `Aces`, `CipherMessage` structs preserved field-for-field (types adjusted: raw pointers → `Vec`/owned struct fields, `Matrix3D`/`PolyArray`/`Polynomial` as above). Free functions `set_aces`, `init_aces`, `aces_encrypt`, `aces_decrypt`, `aces_add`, `aces_mul`, `aces_refresh` preserved 1:1 by name/order; `aces_encrypt`'s C `(aces, message:*u64, size, result)` becomes `(aces, message: &[u64], result: &mut CipherMessage)` (skeleton drops the separate `size` parameter — use `message.len()`, and preserve the C guard `size > 1 → -1` as `message.len() > 1 → Err(...)`); same pattern for `aces_decrypt`'s `result: &mut [u64]`. `aces_mul` remains an unimplemented no-op **matching the C stub** — it should return `Ok(())` without modifying `result`, exactly mirroring C's `(void)a;(void)b;(void)info;(void)result; return 0;` (do not implement real homomorphic multiplication; that is out of scope — the C source itself has a TODO and 0% test coverage there). |

### 3.3 Module Structure (target)

Mirrors both the C header layout and the scaffold exactly — no new modules,
no renamed modules, no merged/split files:

```
src/
  lib.rs             // pub mod aces_internal; pub mod aces; pub mod channel;
                      // pub mod common; pub mod error; pub mod matrix;
                      // pub mod polynomial;   (already declared; keep as-is)
  error.rs            AcesError, Result<T> — shared error type (new relative to
                       C, replacing C's raw int/-1 convention; already fully
                       specified, not `unimplemented!()`, treat as fixed API)
  common.rs           Xgcd, Pair, gcd, xgcd, are_coprime, randinverse,
                       randrange, normal_rand, max, min, clamp
  matrix.rs           Matrix2D, Matrix3D, matrix2d_multiply, swap_transform,
                       linear_mix_transform, scale_transform, matrix2d_eye,
                       fill_random_invertible_pairs
  polynomial.rs       Coeff, Polynomial (+ methods), PolyArray
  channel.rs          Parameters, Channel (+ new/init)
  aces_internal.rs     generate_error, generate_vanisher, generate_linear,
                       generate_u, generate_secret, generate_f0, generate_f1
  aces.rs             PublicKey, PrivateKey, SharedInfo, Aces, CipherMessage,
                       set_aces, init_aces, aces_encrypt, aces_decrypt,
                       aces_add, aces_mul, aces_refresh
```

Dependency order (bottom-up, matches C's own header include order:
`Aces-internal.h` includes `Channel.h`+`Matrix.h`+`Polynomial.h`;
`Aces.h` includes the same three): `error` and `common` have no internal
deps; `matrix` depends on `common` (uses `randrange`/`randinverse` inside
transforms, already imported in scaffold); `polynomial` depends only on
`error`; `channel` depends only on `error`; `aces_internal` depends on
`channel`, `matrix`, `polynomial`, `error`; `aces` depends on all of the
above.

### 3.4 Output/Contract Mapping (per milestone)

The held-out oracle almost certainly follows the C module boundaries
(consistent with the removed `tests/` directory paralleling the 6 `.c`
files and the per-file coverage report). Expected observable contracts:

1. **common** — `gcd`/`xgcd` numeric identity `gcd = a*x + b*y`;
   `are_coprime` boolean equivalence to `gcd(x,y)==1`; `randinverse` returns
   `(a, a⁻¹ mod value)` with `1 ≤ a < value`, `a * a⁻¹ ≡ 1 (mod value)`;
   `randrange(lower,upper)` always in `[lower, upper]`; `clamp`/`min`/`max`
   exact boundary behavior including equal-args ties.
2. **matrix** — `Matrix2D::new`/`get`/`set`/`row` bounds-respecting
   accessors (`None` outside range); `matrix2d_multiply` matches naive
   triple-loop mod-q product; `matrix2d_eye` identity matrix; each transform
   (`swap`, `linear_mix`, `scale`) preserves the invariant `m · invm ≡ I (mod
   q)` before/after application (this is the property the C module's own
   tests almost certainly assert, since it's the entire point of
   `fill_random_invertible_pairs`); `fill_random_invertible_pairs` produces
   a valid invertible pair after N iterations.
3. **polynomial** — `degree`, `coef_sum`, `set_zero`, `fit` exact
   index/value semantics vs. C (including the MSB-first convention and the
   "leading zero" stripping direction); `add`/`sub`/`mul` mod-q correctness
   including the size-mismatch zero-padding logic C implements inline;
   `lshift`/`poly_mod` replicate the C's Euclidean-style polynomial
   reduction (leading coeff of divisor must be 1, else `Err`); `sub_scaler`/
   `add_scaler` per-coefficient mod arithmetic.
4. **channel** — `Channel::new` unconditional; `Channel::init` replicates
   C's `init_channel` auto-correction: **the C condition is
   `if (!(pow(p,2) < q && are_coprime(p,q))) channel->q = pow(p+1,2);`** —
   i.e. if `p² < q` AND `coprime(p,q)` both hold, `q` is left as given;
   otherwise `q` is silently replaced with `(p+1)²`. The Rust `init`
   docstring says "checks that `p < q`" (a weaker/rephrased description in
   the skeleton) — implement the **actual C behavior** (the `p²<q &&
   coprime` check with the `(p+1)²` fallback), since faithfulness to the C
   source takes priority over the paraphrased skeleton doc comment; return
   `Ok(Self{p,q_maybe_corrected,w})` in both branches (C never treats this
   as an error, always returns 0) — do not turn the fallback branch into an
   `Err`.
5. **aces_internal** — `generate_error`: resulting `rm` such that
   `coef_sum(rm) mod q == message` (mirrors C's shift-correction on the
   last coefficient). `generate_vanisher`/`generate_linear`: same
   shift-correction pattern producing `coef_sum ≡ p·k` /`≡ k` mod q for
   internally sampled `k` (even though `k` is no longer returned per
   §3.2). `generate_u`: length `dim+1`, first coeff `1`, last coeff makes
   `coef_sum(u) == q` (via `channel.q - coef_sum`), with the same
   random zero/nonzero run-length pattern as C. `generate_secret`: same
   invertible-pair-based derivation of `secret.polies[i]` and `lambda`
   tensor (mirrors `matrix2d_multiply`/`poly_mul`/`poly_mod` composition).
   `generate_f0`: random `PolyArray` sized to `f0.polies[i].size`
   entries in `[0, q-1]`. `generate_f1`: `f1 = (Σ f0_i · x_i) mod u`,
   right-aligned into `f1`'s existing length exactly as C's pointer-shift
   (`f1->coeffs += diff; f1->size -= diff;`) does — in Rust this becomes
   truncating/copying the low-order `f1.coeffs.len()` entries of the
   computed value into `f1`, not a pointer shift.
6. **aces** — `set_aces` produces correctly-shaped zeroed buffers for
   `u` (`dim+1`), `lambda` (`dim` matrices of `dim×dim`), `x`/`f0`
   (`dim` polynomials of size `dim` each), `f1` (size `dim`), returning
   `Err` if `mem.len()` is insufficient for an equivalent required-capacity
   check (mirrors C's upfront `size < required → -1`, but the "capacity"
   is now a proxy check since actual storage is `Vec`-based, not
   `mem`-backed — see §2 table). `init_aces` wires channel→u→secret→f0→f1
   in the same order as C. `aces_encrypt`/`aces_decrypt` round-trip:
   `decrypt(encrypt(m)) == m mod p` for `message.len() <= 1` (else `Err`).
   `aces_add`: per-component polynomial add + mod-u reduction on `c1`
   and `c2`, `level = a.level + b.level`. `aces_mul`: no-op, `Ok(())`,
   `result` untouched (matches C's TODO stub — the oracle test for this,
   if any, most likely only checks it doesn't panic/error, given 0%
   coverage in the C original). `aces_refresh`: `c2 = c2 - k*p mod q`
   (via `sub_scaler`), `level -= k` (note: C uses plain `-=` on `uint64_t`,
   silently wrapping on underflow if `k > level`; replicate with
   `wrapping_sub` on the Rust `u64 level` field to preserve that
   possibility rather than panicking).

### 3.5 Boundary & Error-Handling Strategy

- Every module-boundary function whose C counterpart could return `-1`
  must return `Result<T>` via `AcesError::GenericError(String)` — construct
  descriptive messages (e.g. `"buffer too small: need {required}, got
  {len}"`, `"message size must be <= 1"`, `"polynomial sizes exceed result
  capacity"`, `"divisor leading coefficient must be 1"`) so failures are
  debuggable, but the *set* of failure conditions must exactly match the C
  source's `-1`-returning `if` conditions — do not add new validation the C
  code doesn't perform (e.g. do not reject `mod == 0` in functions where C
  doesn't check it, except `poly_add`/`poly_sub` which explicitly do:
  `if (... || mod == 0) return -1;` — preserve that specific check).
- Raw-pointer/no-bounds-check C accessors (`matrix2d_get/set/row`,
  `matrix3d_get`) become `Option`/`Result`-returning safe methods — this is
  the one place Rust's contract is *stricter* than C's (C has UB on OOB,
  Rust must not panic-via-indexing in library code); use `.get()`
  /`.get_mut()` against the `Vec` rather than `[]`.
- No `unsafe` is required anywhere in this port: there is no raw pointer
  aliasing, no FFI, and no manual memory layout once `Vec`-backed structs
  replace the C arena/malloc patterns. `set_aces`'s `mem: &mut [u8]`
  parameter is retained purely for signature parity with the C API; the
  implementation should read `mem.len()` for the capacity check and then
  ignore its contents, constructing `Vec`s directly rather than transmuting
  bytes.
- Never cast `&T` to `&mut T`; all "modify a field of a struct passed
  elsewhere" patterns (e.g., C's `Matrix2D *arr` reused as scratch inside
  `generate_secret`, or `f1->coeffs += diff` pointer-shifting in
  `generate_f1`) must be restructured as ordinary owned/`&mut` values
  (e.g., build a fresh `Vec`, or truncate/slice-copy into the existing
  `Vec`) — see §3.4 point 5 for the `generate_f1` specifics.

### 3.6 Unit-Test Strategy

Because the C source's own unit tests are removed (the held-out oracle),
and the scaffold declares no external I/O, network, filesystem, or
mockable "infrastructure" boundaries (all state is pure in-memory data
structures; the only "environment" dependency is the RNG, already
abstracted behind `common::randrange`/`common::normal_rand`/`rand::Rng`),
this crate's own translated unit tests do not need trait-based mocks for
external systems. Instead, the mockable/testable seam design is:

- **Determinism seam**: tests that need reproducible RNG output should seed
  a `StdRng`/`SmallRng` (already available via the `rand` crate declared in
  `Cargo.toml`) rather than relying on the thread-local default RNG, but
  since the skeleton's public functions (`randrange`, `normal_rand`,
  `randinverse`) take no RNG parameter (matching C's global `rand()` state,
  which the skeleton does not parametrize), unit tests for randomized
  functions must assert **invariants** (bounds, modular identities, matrix
  invertibility) rather than exact output values — this mirrors how the
  original C tests almost certainly worked, given `randrange`/`normal_rand`
  wrap C's global `rand()` with no seeding hook either.
- **Pure-function seam**: `common.rs`, `polynomial.rs`, `matrix.rs` (except
  the 3 randomized transforms and `fill_random_invertible_pairs`),
  `channel.rs` are fully deterministic given their inputs — translate/write
  direct input→output assertion tests for these (e.g. `gcd(48,18)==6`,
  `xgcd` Bézout identity, `Polynomial::add`/`mul`/`fit` against small
  hand-computed examples derived from the C doc comments and README
  example, `Channel::init`'s two branches with concrgo values chosen to hit
  both the "kept as-is" and "corrected to (p+1)²" paths).
- **Property-based seam for randomized code**: `matrix.rs`'s
  `swap_transform`/`linear_mix_transform`/`scale_transform`/
  `fill_random_invertible_pairs` and `aces_internal.rs`'s generators should
  have unit tests that run them many times and assert the algebraic
  invariant holds every time (`m·invm ≡ I (mod q)` for matrix transforms;
  `coef_sum(rm) mod q == message` for `generate_error`, etc.) — no mocking
  needed, since the invariant holds regardless of which random values were
  drawn.
- **End-to-end seam**: `aces.rs`'s `init_aces`→`aces_encrypt`→`aces_decrypt`
  round trip (as shown in the C `README.md` example: encrypt 4 and 3 under
  `p=2,q=33,dim=D`, `aces_add`, decrypt, expect `(4+3) % 2`) is the natural
  integration test to translate directly from the README into a Rust unit
  test in `aces.rs`'s own `#[cfg(test)] mod tests` — this is likely close
  to (but not identical to) the held-out oracle's own top-level test, so it
  is safe and valuable as an own-crate regression test without leaking the
  oracle.
- **Location**: place unit tests as `#[cfg(test)] mod tests { use super::*;
  ... }` inline at the bottom of each of the 7 module files (idiomatic Rust,
  keeps tests co-located with the seam they exercise, and matches the
  "translated + new tests run standalone" requirement — `cargo test` inside
  `pipeline/project` runs these without any external harness). Do not add a
  `tests/` integration-test directory in the working copy — that path is
  reserved by the CRUST harness for staging the held-out oracle binaries at
  validation time (per `codeweaver.toml`'s note that `.oracle-master` tests
  get staged back at `validate` time), so a agent-authored `tests/` dir
  would risk colliding with that staging step.

### 3.7 Milestone Mapping

Recommended cumulative milestone order (bottom-up by dependency, matching
§3.3's dependency order and the likely oracle gate structure implied by
`gate_template = "{tests_space}"` in `codeweaver.toml`, which suggests
gates keyed by test-target name — most plausibly one target per module):

1. **Milestone 1 — `error`, `common`**: implement `AcesError`/`Result`
   (already fully specified, no work needed) and all of `common.rs`
   (`gcd`, `xgcd`, `are_coprime`, `randinverse`, `randrange`, `normal_rand`,
   `max`, `min`, `clamp`). Corresponds to C's `Common.h`/`Common.c` and its
   removed unit tests (coverage entries for the smallest files, 100%
   coverage per the report).
2. **Milestone 2 — `matrix`**: `Matrix2D`/`Matrix3D` plus
   `matrix2d_multiply`, `swap_transform`, `linear_mix_transform`,
   `scale_transform`, `matrix2d_eye`, `fill_random_invertible_pairs`.
   Depends on Milestone 1 for `randrange`/`randinverse`. Corresponds to
   `Matrix.h`/`Matrix.c`.
3. **Milestone 3 — `polynomial`**: `Polynomial`/`PolyArray` and all methods
   (`degree`, `set_zero`, `coef_sum`, `fit`, `add`, `sub`, `mul`, `lshift`,
   `poly_mod`, `sub_scaler`, `add_scaler`). Depends only on Milestone 1
   (`error`). Corresponds to `Polynomial.h`/`Polynomial.c`.
4. **Milestone 4 — `channel`**: `Channel::new`/`Channel::init`,
   `Parameters`. Depends on Milestone 1. Corresponds to `Channel.h`/
   `Channel.c`.
5. **Milestone 5 — `aces_internal`**: `generate_error`,
   `generate_vanisher`, `generate_linear`, `generate_u`, `generate_secret`,
   `generate_f0`, `generate_f1`. Depends on Milestones 1–4 (uses `common`,
   `matrix`, `polynomial`, `channel`). Corresponds to `Aces-internal.h`/
   `Aces-internal.c`.
6. **Milestone 6 — `aces`**: `PublicKey`/`PrivateKey`/`SharedInfo`/`Aces`/
   `CipherMessage`, `set_aces`, `init_aces`, `aces_encrypt`, `aces_decrypt`,
   `aces_add`, `aces_mul` (stub), `aces_refresh`. Depends on all prior
   milestones. Corresponds to `Aces.h`/`Aces.c` and is the integration
   point exercised by the README's end-to-end example.

Each milestone's "done" bar: `cargo build` succeeds with the module's
`unimplemented!()` bodies replaced, the module's own inline `#[cfg(test)]`
tests pass, and no downstream milestone's compile is broken (later
milestones only ever *add* new module implementations, never change
already-completed ones' public signatures, per the brief's "never change a
declared interface" rule).
