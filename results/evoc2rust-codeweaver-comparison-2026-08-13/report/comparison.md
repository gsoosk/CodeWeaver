# Leakage-Safe Reproduction of EvoC2Rust with CodeWeaver

## Abstract

We reproduce the publicly executable portion of EvoC2Rust on the paper's disclosed Vivo-Bench repository and compare three independent CodeWeaver gpt-5.6-sol runs. Across repetitions, mean ICompRate is 100.00% +/- 0.00 pp, mean FCompRate is 100.00% +/- 0.00 pp, mean TestRate is 100.00% +/- 0.00 pp, and mean SafeRate is 30.92% +/- 4.72 pp. AccRate-P/R, the six-project C2R-Bench experiment, ablations, and scale experiments cannot be independently rerun because their required artifacts are not public; published values remain reference-only.

## Experimental coverage and artifact availability

| RQ | Surface | Status | Reason |
| --- | --- | --- | --- |
| RQ1 | Vivo-Bench ICompRate | measured | cumulative replacement with C fallback |
| RQ1 | Vivo-Bench AccRate-P/R | unavailable | human-corrected Rust references are unreleased |
| RQ1 | Vivo-Bench SafeRate | measured | candidate production Rust only |
| RQ2 | Vivo-Bench FCompRate/TestRate | measured | 19 modules and 125 active pinned tests |
| RQ1/RQ2 | C2R-Bench | unavailable | C2R-Bench sources, tests, and corrected Rust references are unreleased |
| RQ3 | EvoC2Rust ablations | reference_only | implementation, feature mappings, repairs, and C2R-Bench are unreleased |
| RQ4 | scale and time figures | reference_only | requires unreleased C2R projects and EvoC2Rust runtime traces |

## Table 4 extension: project translation

| Dataset | Model | Method | ICompRate | AccRate-P | AccRate-R | SafeRate |
| --- | --- | --- | --- | --- | --- | --- |
| Vivo-Bench | DeepSeek-V3 | EvoC2Rust | 100.00% | 99.83% | 99.86% | 98.00% |
| Vivo-Bench | Qwen3-32B | EvoC2Rust | 87.65% | 87.92% | 83.45% | 98.22% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver repetition 1 | 100.00% | N/A | N/A | 31.21% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver repetition 2 | 100.00% | N/A | N/A | 35.50% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver repetition 3 | 100.00% | N/A | N/A | 26.07% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver mean | 100.00% | N/A | N/A | 30.92% |

## Table 5 extension: module translation

| Dataset | Model | System/run | FCompRate | TestRate |
| --- | --- | --- | --- | --- |
| Vivo-Bench | DeepSeek-V3 | 19 projects | 99.07% | 98.50% |
| Vivo-Bench | Qwen3-32B | 19 projects | 87.65% | 84.57% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver repetition 1 | 100.00% | 100.00% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver repetition 2 | 100.00% | 100.00% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver repetition 3 | 100.00% | 100.00% |
| Vivo-Bench (pinned revision) | gpt-5.6-sol | CodeWeaver mean | 100.00% | 100.00% |

## Exact CodeWeaver repetitions

| Rep | Terminal | Integrity | IComp | FComp | Tests | TestRate | SafeRate | Elapsed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 15/15 | 15/15 | 19/19 (100.00%) | 19/19 (100.00%) | 125/125 | 100.00% | 31.21% | 11.22 h |
| 2 | 15/15 | 15/15 | 19/19 (100.00%) | 19/19 (100.00%) | 125/125 | 100.00% | 35.50% | 12.03 h |
| 3 | 15/15 | 15/15 | 19/19 (100.00%) | 19/19 (100.00%) | 125/125 | 100.00% | 26.07% | 10.86 h |

## Methodology

The benchmark is pinned at AtomGit commit `c88cef1a1d15079478be14ab361dda8f3b49fee2`. C2Rust 0.22.1 derives only ABI signatures and immutable Rust test contracts; all generated production bodies are stripped before model access. The contracts were calibrated against both the original C and full C2Rust implementations (125/125 active functions), while stripped scaffolds pass 0/125. Each fixed test runs in a separate process. FCompRate credits every module in a group only when the independently restored crate builds. ICompRate follows the paper's incremental strategy: groups are inserted in frozen order into a cumulative project, and failed groups fall back to original C. SafeRate is the line-weighted share of nonblank production Rust lines outside unsafe functions or blocks. Three repetitions use GPT-5.6 Sol at maximum effort, five repair iterations, three parity rounds, and a 5,000-second agent timeout.

## Threats to validity

The paper reports 113 Vivo-Bench test cases, while the pinned public revision enables 125 test functions and disables 2 additional `rb-tree` functions. CodeWeaver therefore uses a 125-test denominator and does not relabel it as the paper's 113-test denominator. Models also differ (GPT-5.6 Sol versus DeepSeek-V3/Qwen3-32B), and the CodeWeaver architecture is not an EvoC2Rust implementation. SafeRate is comparable in intent but the paper does not release its exact analyzer. Published reference values and new measurements are never pooled.

## Reference-only experiments

The complete published Table 4, C2R-Bench portion of Table 5, and Table 6 ablation values are preserved in the companion CSV files. They are not presented as reruns. RQ4's scale and timing figures cannot be regenerated without the six unreleased industrial projects and original execution traces.

## Provenance

- Paper DOI: `10.1145/3786583.3786856`
- Paper version: `2508.04295v4`
- Public benchmark: `https://atomgit.com/vivoblueos2/vivo_blueos_contest2_c2rust` at `c88cef1a1d15079478be14ab361dda8f3b49fee2`
- Protocol: `{"agent_timeout_seconds": 5000, "effort": "max", "evaluated_repetitions": 3, "max_iter": 5, "max_parity_rounds": 3, "model": "gpt-5.6-sol", "repetitions": 3}`
- Evaluation provenance: `{"cargo": {"returncode": 0, "status": "measured", "value": "cargo 1.92.0-nightly (24bb93c38 2025-09-10)"}, "generated_at": "2026-08-13T03:58:59.697593+00:00", "harness_config_sha256": "58a24231d9b512b15783953b2dc11faac6ed6391cd867243980b6c2b872ae0d8", "platform": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39", "python": "3.12.3", "rustc": {"returncode": 0, "status": "measured", "value": "rustc 1.92.0-nightly (52618eb33 2025-09-14)"}}`
