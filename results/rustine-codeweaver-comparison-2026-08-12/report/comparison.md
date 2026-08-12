# CodeWeaver on Rustine's 23-repository C-to-Rust benchmark

## Abstract

We evaluate CodeWeaver with GPT-5.6 Sol on the same 23 C-to-Rust subjects used by Rustine. To prevent target leakage, CodeWeaver receives only disclosed C inputs, Rust skeletons, and immutable test contracts; Rustine production translations remain excluded. Independent evaluation finds 21/23 compiling CodeWeaver translations and 10/21 fixed-contract passes. Rustine's published reference reports 23/23 compilation and 19/21 complete test-suite passes. Exact measured, inferred, unavailable, and not-applicable states remain distinct throughout the artifact.

## Aggregate summary

| Metric | Rustine paper | CodeWeaver measured |
| --- | --- | --- |
| Subjects/runs | 23 | 23 |
| CodeWeaver pipeline terminal success | not applicable | 9/23 |
| Immutable-contract integrity | paper reference | 23/23 |
| Compilation successes | 23/23 (100.0%) | 21/23 (91.3%; 95% Wilson CI 73.2-97.6%) |
| Fixed-contract passes | 19/21 testable | 10/21 (47.6%); 95% Wilson CI 28.3-67.6%; 21 measured |
| Paired exact McNemar p (compilation/fixed contract) | reference | 0.5/0.003906 |
| Translation function coverage (unweighted subject mean) | 68.4% | 78.2% (10 measured) |
| Translation line coverage (unweighted subject mean) | 64.8% | 76.6% (10 measured) |
| Benchmark test-suite coverage (function/line) | 74.7%/72.2% (paper Table 1) | reference characteristic, not a system outcome |
| CodeWeaver count-weighted coverage (function/line) | not derivable from published Rustine counts | 70.1%/66.3% (10 measured) |
| Assertions E/P/F | 1221192/1063099/158093 | 7596/7595/1 (measured or explicitly inferred credits only) |
| Assertion pass rate | 87.05% | 99.99% (10 credited runs) |
| Output tokens | not reported | 6,499,312 (23 measured runs) |
| AI credits / premium requests | not reported | 56669.5 / 0 (23 measured runs) |
| Cumulative/median elapsed time | not reported | 34.10 h / 61.1 min (23 measured runs) |

## Validation: Rustine paper Table 2 extended with CodeWeaver

| ID | Subject | CW pipeline | Rustine compile | CW compile | Rustine func | CW func | Rustine line | CW line | Rustine assertions E/P/F | CW assertions E/P/F | Fixed contract |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | qsort | completed | 100% | pass | 100% | 80.0% | 92% | 95.2% | 21/21/0 | 21*/21*/0* | pass |
| 2 | bst | completed | 100% | pass | 92% | 87.5% | 95% | 90.1% | 6/6/0 | 6*/6*/0* | pass |
| 3 | rgba | completed | 100% | pass | 99% | 92.0% | 93% | 85.7% | 20/20/0 | 20*/20*/0* | pass |
| 4 | quadtree | failed | 100% | pass | 91% | error | 83% | error | 34/34/0 | unavailable/unavailable/unavailable | fail |
| 5 | buffer | failed | 100% | pass | 91% | error | 88% | error | 54/54/0 | unavailable/unavailable/unavailable | fail |
| 6 | grabc | failed | 100% | pass | 11% | error | 10% | error | 4/4/0 | unavailable/unavailable/unavailable | fail |
| 7 | urlparser | completed | 100% | pass | 75% | 85.7% | 74% | 84.6% | 46/46/0 | 46*/46*/0* | pass |
| 8 | xzoom | completed | 100% | pass | N/A | not_applicable | N/A | not_applicable | N/A | not_applicable/not_applicable/not_applicable | not_applicable |
| 9 | genann | failed | 100% | pass | 84% | error | 79% | error | 521556/521556/0 | unavailable/unavailable/unavailable | fail |
| 10 | ht | failed | 100% | pass | 61% | error | 67% | error | 1/1/0 | unavailable/unavailable/unavailable | fail |
| 11 | robotfindskitten | failed | 100% | pass | 63% | error | 61% | error | 47/47/0 | unavailable/unavailable/unavailable | fail |
| 12 | libcsv | completed | 100% | pass | 45% | 63.0% | 52% | 66.4% | 7406/7406/0 | 7406*/7406*/0* | pass |
| 13 | avl-tree | completed | 100% | pass | 29% | 75.5% | 31% | 70.1% | 12/12/0 | 12*/12*/0* | pass |
| 14 | libopenaptx | completed | 100% | pass | 95% | 94.5% | 81% | 86.1% | 9/9/0 | 9*/9*/0* | pass |
| 15 | libtree | failed | 100% | pass | 82% | error | 75% | error | 121/121/0 | unavailable/unavailable/unavailable | fail |
| 16 | opl | completed | 100% | pass | 45% | 61.6% | 44% | 57.1% | 14/14/0 | 14*/14*/0* | pass |
| 17 | libzahl | failed | 100% | pass | 87% | error | 60% | error | 1570/1570/0 | unavailable/unavailable/unavailable | fail |
| 18 | zopfli | failed | 100% | pass | 92% | 86.0% | 84% | 77.2% | 40/40/0 | 40*/40*/0* | pass |
| 19 | snudown | failed | 100% | pass | N/A | not_applicable | N/A | not_applicable | N/A | not_applicable/not_applicable/not_applicable | not_applicable |
| 20 | lodepng | failed | 100% | fail | 61% | error | 60% | error | 683994/526159/157835 | unavailable/unavailable/unavailable | fail |
| 21 | bzip2 | failed | 100% | pass | 13% | 56.4% | 12% | 53.3% | 36/36/0 | unavailable/unavailable/unavailable | pass |
| 22 | binn | failed | 100% | fail | 55% | error | 60% | error | 1949/1949/0 | unavailable/unavailable/unavailable | fail |
| 23 | tulpindicator | failed | 100% | pass | 65% | error | 60% | error | 4252/3994/258 | 22/21/1 | fail |

## Safety aggregate

| Safety metric | Rustine paper total | CodeWeaver measured total |
| --- | --- | --- |
| Pointer arithmetic | 253 | 0 (19/23 measured) |
| Raw pointer declarations | 198 | 99 (19/23 measured) |
| Raw pointer dereferences | 126 | 3 (19/23 measured) |
| Unsafe lines | 3430 | 476 (19/23 measured) |
| Unsafe type casts | 357 | 4 (19/23 measured) |
| Unsafe calls | 1825 | 125 (19/23 measured) |

## Safety: Rustine paper Table 3 extended with CodeWeaver

| ID | Subject | Rustine Ptr arith | CW Ptr arith | Rustine Raw decl | CW Raw decl | Rustine Raw deref | CW Raw deref | Rustine Unsafe lines | CW Unsafe lines | Rustine Unsafe casts | CW Unsafe casts | Rustine Unsafe calls | CW Unsafe calls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | qsort | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | bst | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | rgba | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | quadtree | 0 | 0 | 4 | 0 | 2 | 0 | 26 | 0 | 0 | 0 | 8 | 0 |
| 5 | buffer | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 6 | grabc | 0 | 0 | 15 | 2 | 7 | 0 | 112 | 4 | 15 | 0 | 51 | 0 |
| 7 | urlparser | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 2 | 0 | 3 | 0 |
| 8 | xzoom | 21 | 0 | 21 | 11 | 17 | 0 | 453 | 426 | 57 | 3 | 274 | 88 |
| 9 | genann | 0 | 0 | 1 | 0 | 4 | 0 | 43 | 0 | 8 | 0 | 21 | 0 |
| 10 | ht | 1 | 0 | 1 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 9 | 0 |
| 11 | robotfindskitten | 0 | unavailable | 1 | error | 0 | error | 20 | error | 1 | error | 8 | error |
| 12 | libcsv | 4 | 0 | 6 | 0 | 8 | 0 | 113 | 9 | 2 | 0 | 41 | 7 |
| 13 | avl-tree | 0 | unavailable | 15 | error | 12 | error | 93 | error | 5 | error | 45 | error |
| 14 | libopenaptx | 7 | 0 | 1 | 0 | 0 | 0 | 5 | 0 | 2 | 0 | 2 | 0 |
| 15 | libtree | 22 | 0 | 8 | 0 | 4 | 0 | 162 | 0 | 25 | 0 | 131 | 0 |
| 16 | opl | 12 | unavailable | 0 | error | 0 | error | 5 | error | 0 | error | 5 | error |
| 17 | libzahl | 12 | 0 | 6 | 85 | 1 | 0 | 1731 | 0 | 8 | 0 | 658 | 0 |
| 18 | zopfli | 3 | 0 | 1 | 0 | 0 | 0 | 8 | 0 | 1 | 0 | 5 | 0 |
| 19 | snudown | 2 | 0 | 8 | 0 | 0 | 0 | 52 | 0 | 17 | 0 | 38 | 0 |
| 20 | lodepng | 90 | unavailable | 27 | error | 17 | error | 117 | error | 11 | error | 39 | error |
| 21 | bzip2 | 7 | 0 | 19 | 1 | 20 | 3 | 114 | 37 | 47 | 1 | 130 | 30 |
| 22 | binn | 56 | 0 | 57 | 0 | 20 | 0 | 331 | 0 | 140 | 0 | 335 | 0 |
| 23 | tulpindicator | 15 | 0 | 7 | 0 | 14 | 0 | 34 | 0 | 16 | 0 | 22 | 0 |

## Methodology

Compilation uses `cargo build --all-targets`. Fixed contract binaries are restored into a temporary target copy before execution. Paper-comparable coverage is measured with cargo-llvm-cov over the production library graph plus immutable Rust contract files; production-only values remain in the raw evaluation. Rustine's reported 74.7% function and 72.2% line values characterize the benchmark test suites in paper Table 1, not Rustine's translated outputs; they are preserved exactly but never used as a system outcome. Comparable system coverage uses unweighted means of the per-subject Table 2 values. CodeWeaver's count-weighted llvm-cov aggregate is shown only as a separate diagnostic. Rustine cargo-newmetrics runs with nightly-2025-05-13; contract and generated tests are excluded through its built-in library-only check. Pointer arithmetic uses only its rustc-HIR result; a source-pattern count is retained solely as a raw diagnostic. Assertion values marked `*` are inferred from the paper denominator only after every disclosed fixed check passes; they are not runtime counts. Missing capabilities remain explicitly unavailable rather than becoming zero or success. Token and AI-credit totals include only values exposed by Copilot usage checkpoints; absent fields remain unavailable.

## Comparability caveats

This report pairs CodeWeaver only with the same 23 Rustine subjects. The older 118-project ReCodeAgent matrix uses different subjects and is not directly comparable. Rustine is a paper-reference single run; CodeWeaver repetitions are reported separately. xzoom and snudown have no test contract and remain N/A. The artifact withholds bzip2's augmented 36-assertion module, so the measured bzip2 status is a deterministic CLI round trip and exact assertion credit is unavailable. The disclosed grabc driver cannot execute its four X11 assertions headlessly, so its derived check invokes the candidate production `grabc -v` binary rather than the self-contained test driver. The HT artifact exposes samples rather than its one-assertion oracle; both use labeled derived checks with unavailable exact assertion credit. Tulip Indicators fixtures are restored from its pinned upstream commit with SHA-256 verification. Calibration reproduced qsort's published 100% function and 92% line translation coverage, but several larger official translations no longer compile under current dependencies/compiler behavior. Rustine values therefore remain the published paper reference rather than a selectively repaired modern rerun. Paper-reference and newly measured values are never blended.

## Interpretation

CodeWeaver trails the Rustine paper reference by 8.7 percentage points in compilation and trails the Rustine paper reference by 42.9 percentage points in complete fixed-contract pass rate. Across 10 translations with measured coverage, CodeWeaver's unweighted mean is 78.2% function and 76.6% line. Coverage is conditioned on measurable builds and is therefore reported with its row count rather than imputed for failures. Assertion credits marked with an asterisk use the paper denominator only after all disclosed checks pass; surrogate checks with unavailable exact oracles are never promoted to measured assertion totals. These results compare complete systems under different model/tool designs and do not isolate any single architectural cause.

## Provenance and source

- Paper: [Translating Large-Scale C Repositories to Idiomatic Rust](https://arxiv.org/abs/2511.20617) (2511.20617v1)
- Official artifact: [https://github.com/Intelligent-CAT-Lab/Rustine](https://github.com/Intelligent-CAT-Lab/Rustine) at `774ff51e48d4d3a6a73e4864689a042fc1028fc0`
- Protocol: `{"agent_timeout_seconds": 5000, "cargo_llvm_cov_version": "0.8.7", "cargo_newmetrics_sha256": "235e5515186bcbe1a455339c524a9e33f8223fffa5fec2f8293cee11c1afc2bb", "effort": "max", "evaluated_repetitions": 1, "max_iter": 5, "max_parity_rounds": 3, "model": "gpt-5.6-sol", "repetitions": 1, "rust_toolchain": "nightly-2025-05-13"}`
- Preparation provenance: `{"artifact_git_commit": "774ff51e48d4d3a6a73e4864689a042fc1028fc0", "generated_at": "2026-08-11T23:03:43.266923+00:00", "harness_config_sha256": "cd52b1dfae899829b5a773364de985dab134015cc8a6347b0e95b42a9fe74389", "platform": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39", "python": "3.12.3"}`
- Evaluation provenance: `{"generated_at": "2026-08-12T08:09:49.239714+00:00", "harness_config_sha256": "cd52b1dfae899829b5a773364de985dab134015cc8a6347b0e95b42a9fe74389", "platform": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39", "python": "3.12.3", "tools": {"backend": "native", "cargo": {"returncode": 0, "status": "measured", "value": ["cargo 1.92.0-nightly (24bb93c38 2025-09-10)"]}, "cargo_llvm_cov": {"returncode": 0, "status": "measured", "value": ["cargo-llvm-cov 0.8.7"]}, "cargo_newmetrics_sha256": {"returncode": 0, "status": "measured", "value": ["235e5515186bcbe1a455339c524a9e33f8223fffa5fec2f8293cee11c1afc2bb  /opt/codeweaver-rustine-tools/bin/cargo-newmetrics"]}, "rustc_nightly": {"returncode": 0, "status": "measured", "value": ["rustc 1.89.0-nightly (8405332bd 2025-05-12)"]}}}`
