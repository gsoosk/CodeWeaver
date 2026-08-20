"""Frozen protocols, benchmark subjects, and paper reference values."""
from __future__ import annotations

from typing import Any

PROTOCOL: dict[str, Any] = {
    "model": "gpt-5.6-sol",
    "effort_default": "max",
    "agent_timeout_seconds": 5000,
    "max_iter": 5,
    "max_parity_rounds": 3,
    "repetitions": 3,
}

UPSTREAM_COMMITS = {
    "crust_bench": "4b4702544b800a3821feea128c5b9e413665dc83",
    "alphatrans": "c1cabf93d41a153de207d6b098e1da7bbd79abab",
    "repotransbench": "f9f89ea27ca886571a5e59a8bb9a25deab5bd1c2",
    "repotransbench_v1": "7c096b0c89699266144953bfbf3770cc7ca2fc61",
    "sactor": "577c3d2b8074d5fed7c47b988c0acd175e498f98",
    "rustrepotrans": "7026a8a9c8d4a524cbb554ff9b8100df4020114c",
}

UPSTREAM_REPOSITORIES = {
    "crust_bench": "https://github.com/anirudhkhatry/CRUST-bench",
    "alphatrans": "https://github.com/Intelligent-CAT-Lab/AlphaTrans",
    "repotransbench": "https://github.com/DeepSoftwareAnalytics/RepoTransBench",
    "sactor": "https://github.com/qsdrqs/sactor",
    "rustrepotrans": "https://github.com/SYSUSELab/RustRepoTrans",
}

REPOTRANSBENCH_SUBJECTS: list[dict[str, Any]] = [
    {
        "id": "repotransbench__parser",
        "name": "gnebehay/parser",
        "source_directory": "gnebehay_parser",
        "source_commit": "1b9f61157d13e72a1e649adbbbca997a4c159b92",
        "source_license": "MIT",
        "target_tree": "GnebehayParserJava",
        "tests": 7,
    },
    {
        "id": "repotransbench__avalanche",
        "name": "fastly/Avalanche",
        "source_directory": "fastly_Avalanche",
        "source_commit": "92a8b44c07c2d40bd5e4efeb8eb3411dc875bc20",
        "source_license": "MIT",
        "target_tree": "FastlyAvalancheJava",
        "tests": 27,
    },
    {
        "id": "repotransbench__distinct-n",
        "name": "neural-dialogue-metrics/Distinct-N",
        "source_directory": "neural-dialogue-metrics_Distinct-N",
        "source_commit": "e94edcb2e1d2230ff9e0f1821387d7f6d7af0c4f",
        "source_license": "MIT",
        "target_tree": "NeuraldialoguemetricsDistinctnJava",
        "tests": 3,
    },
]

RUSTREPOTRANS_SUBJECTS: list[dict[str, Any]] = [
    {
        "id": "rustrepotrans__c__clean",
        "name": "incubator-milagro-crypto:RAND::clean",
        "project": "incubator-milagro-crypto",
        "source_language": "C",
        "pair_directory": "rust__c",
        "task_file": (
            "projects__incubator-milagro-crypto__rust__src__rand__.rs__"
            "function__2.txt"
        ),
        "target_rel_path": "src/rand.rs",
        "target_license": "Apache-2.0",
        "expected_tests": 284,
        "negative_control_failed_tests": 50,
        "build_command": ["cargo", "+nightly-2025-09-15", "check", "--all", "--all-features"],
        "test_command": [
            "cargo",
            "+nightly-2025-09-15",
            "test",
            "--all",
            "--all-features",
            "--release",
        ],
    },
    {
        "id": "rustrepotrans__java__set",
        "name": "incubator-milagro-crypto:big::set",
        "project": "incubator-milagro-crypto",
        "source_language": "Java",
        "pair_directory": "rust__java",
        "task_file": (
            "projects__incubator-milagro-crypto__rust__src__big__.rs__"
            "function__11.txt"
        ),
        "target_rel_path": "src/big.rs",
        "target_license": "Apache-2.0",
        "expected_tests": 284,
        "negative_control_failed_tests": 73,
        "build_command": ["cargo", "+nightly-2025-09-15", "check", "--all", "--all-features"],
        "test_command": [
            "cargo",
            "+nightly-2025-09-15",
            "test",
            "--all",
            "--all-features",
            "--release",
        ],
    },
    {
        "id": "rustrepotrans__python__encoding",
        "name": "charset-normalizer:CharsetMatch::encoding",
        "project": "charset-normalizer",
        "source_language": "Python",
        "pair_directory": "rust__python",
        "task_file": (
            "projects__charset-normalizer__rust__src__entity__.rs__"
            "function__11.txt"
        ),
        "target_rel_path": "src/entity.rs",
        "target_license": "MIT",
        "expected_tests": 64,
        "negative_control_failed_tests": 13,
        "build_command": ["cargo", "check"],
        "test_command": ["cargo", "test"],
    },
]

SACTOR_SUBJECTS = [
    "2dpartint",
    "42-kocaeli-printf",
    "circularbuffer",
    "fasthamming",
    "holdem-odds",
    "linear-algebra-c",
    "nandc",
    "phills_dht",
    "simple-sparsehash",
    "simplexml",
    "aes128-simd",
    "amp",
    "approxidate",
    "avalanche",
    "bhshell",
    "bitset",
    "bostree",
    "btree-map",
    "c-aces",
    "c-string",
    "carrays",
    "cfsm",
    "chtrie",
    "cissy",
    "clog",
    "cset",
    "csyncmers",
    "dict",
    "emlang",
    "expr",
    "file2str",
    "fs_c",
    "geofence",
    "gfc",
    "gorilla-paper-encode",
    "hydra",
    "inversion_list",
    "jccc",
    "leftpad",
    "lib2bit",
    "libbase122",
    "libbeaufort",
    "libwecan",
    "morton",
    "murmurhash_c",
    "razz_simulation",
    "rhbloom",
    "totp",
    "utf8",
    "vec",
]

CRUST_TABLE4 = [
    {"model": "OpenAI o3", "base_build": 35, "base_test": 19, "compiler_build": 68, "compiler_test": 31, "test_build": 63, "test_test": 48},
    {"model": "Claude Opus 4", "base_build": 43, "base_test": 22, "compiler_build": 78, "compiler_test": 29, "test_build": 65, "test_test": 40},
    {"model": "OpenAI o1", "base_build": 32, "base_test": 15, "compiler_build": 69, "compiler_test": 28, "test_build": 54, "test_test": 37},
    {"model": "Claude 3.7", "base_build": 26, "base_test": 13, "compiler_build": 54, "compiler_test": 23, "test_build": 49, "test_test": 32},
    {"model": "Claude 3.5", "base_build": 26, "base_test": 11, "compiler_build": 49, "compiler_test": 21, "test_build": 38, "test_test": 24},
    {"model": "o1-mini", "base_build": 19, "base_test": 9, "compiler_build": 47, "compiler_test": 16, "test_build": 27, "test_test": 21},
    {"model": "GPT-4o", "base_build": 18, "base_test": 7, "compiler_build": 52, "compiler_test": 18, "test_build": 42, "test_test": 22},
    {"model": "Gemini 1.5 Pro", "base_build": 11, "base_test": 3, "compiler_build": 35, "compiler_test": 11, "test_build": 30, "test_test": 14},
    {"model": "Virtuoso (Distilled Deepseek V3)", "base_build": 2, "base_test": 2, "compiler_build": 21, "compiler_test": 6, "test_build": 10, "test_test": 6},
    {"model": "Deepseek-Coder-32B", "base_build": 1, "base_test": 0, "compiler_build": 2, "compiler_test": 0, "test_build": 2, "test_test": 0},
    {"model": "QwQ-32B-Preview", "base_build": 1, "base_test": 0, "compiler_build": 1, "compiler_test": 0, "test_build": 1, "test_test": 0},
    {"model": "Qwen-2.5-Coder-32B", "base_build": 0, "base_test": 0, "compiler_build": 0, "compiler_test": 0, "test_build": 0, "test_test": 0},
    {"model": "Adapted SWE-agent (Claude-3.7)", "base_build": 41, "base_test": 32, "compiler_build": None, "compiler_test": None, "test_build": None, "test_test": None},
]

ALPHATRANS_REFERENCE = {
    "commons-cli": {"paper_subject": "cli", "amf": 273, "syntax_percent": 100.0, "tpr_percent": 10.08},
    "commons-csv": {"paper_subject": "csv", "amf": 235, "syntax_percent": 98.72, "tpr_percent": 0.0},
    "commons-fileupload": {"paper_subject": "fileupload", "amf": 192, "syntax_percent": 100.0, "tpr_percent": 63.44},
    "commons-validator": {"paper_subject": "validator", "amf": 646, "syntax_percent": 99.23, "tpr_percent": 11.70},
}

REPOTRANSBENCH_PYTHON_JAVA = [
    {"model": "Qwen3", "sr": 0.6, "cr": 1.2, "apr": 1.2, "ampr": 1.2},
    {"model": "Qwen3-think", "sr": 1.2, "cr": 1.2, "apr": 1.7, "ampr": 1.2},
    {"model": "DeepSeek", "sr": 1.8, "cr": 2.9, "apr": 2.3, "ampr": 1.8},
    {"model": "DeepSeek-R", "sr": 0.0, "cr": 0.0, "apr": 0.0, "ampr": 0.0},
    {"model": "Claude", "sr": 5.8, "cr": 8.8, "apr": 8.2, "ampr": 8.2},
    {"model": "Gemini", "sr": 0.0, "cr": 0.0, "apr": 0.0, "ampr": 0.0},
    {"model": "GPT-4.1", "sr": 7.0, "cr": 7.0, "apr": 9.0, "ampr": 7.0},
    {"model": "o3-mini", "sr": 1.8, "cr": 1.8, "apr": 1.8, "ampr": 1.8},
]

REPOTRANSBENCH_V1_RESULTS = [
    {"model": "Llama-3.1-8B-Inst", "success_at_1": 0.00, "build_at_1": 0.00, "apr": 0.00},
    {"model": "Llama-3.1-70B-Inst", "success_at_1": 1.33, "build_at_1": 2.67, "apr": 1.30},
    {"model": "Llama-3.1-405B-Inst", "success_at_1": 2.67, "build_at_1": 5.67, "apr": 4.70},
    {"model": "DeepSeek-V2.5", "success_at_1": 3.00, "build_at_1": 12.00, "apr": 6.20},
    {"model": "GPT-3.5-Turbo", "success_at_1": 0.67, "build_at_1": 2.33, "apr": 1.10},
    {"model": "GPT-4", "success_at_1": 2.33, "build_at_1": 4.33, "apr": 2.00},
    {"model": "GPT-4o", "success_at_1": 4.00, "build_at_1": 9.00, "apr": 6.40},
    {"model": "Claude-3.5-Sonnet", "success_at_1": 7.33, "build_at_1": 28.33, "apr": 16.50},
    {"model": "CodeLlama-34B-Inst", "success_at_1": 0.00, "build_at_1": 0.37, "apr": 0.00},
    {"model": "Codestral-22B", "success_at_1": 2.08, "build_at_1": 5.90, "apr": 2.60},
    {"model": "DeepSeek-Coder-V2-Inst", "success_at_1": 4.86, "build_at_1": 16.84, "apr": 8.40},
]

REPOTRANSBENCH_ORACLE_AUDIT = [
    {"subject": "gnebehay/parser", "released_tests": 7, "golden_status": "pass", "oracle_status": "meaningful", "selected": True},
    {"subject": "fastly/Avalanche", "released_tests": 27, "golden_status": "pass", "oracle_status": "meaningful", "selected": True},
    {"subject": "neural-dialogue-metrics/Distinct-N", "released_tests": 3, "golden_status": "pass", "oracle_status": "meaningful", "selected": True},
    {"subject": "susam/mintotp", "released_tests": 8, "golden_status": "fail: 1 failure, 7 errors", "oracle_status": "invalid golden", "selected": False},
    {"subject": "sbyrnes321/numericalunits", "released_tests": 13, "golden_status": "fail: 5 failures", "oracle_status": "environment/golden incompatible", "selected": False},
    {"subject": "dwyl/english-words", "released_tests": 5, "golden_status": "fail: 5 missing-file errors", "oracle_status": "incomplete release", "selected": False},
    {"subject": "Yelp/ephemeral-port-reserve", "released_tests": 4, "golden_status": "pass", "oracle_status": "vacuous: tests do not call translation", "selected": False},
]

SACTOR_REFERENCE = {
    "unidiomatic_function_success": 81.57,
    "unidiomatic_sample_success": 64.0,
    "idiomatic_function_success": 42.93,
    "idiomatic_sample_success_conditional": 25.0,
    "idiomatic_unsafe_free": 100.0,
    "samples": 50,
    "idiomatic_samples": 32,
}

RUSTREPOTRANS_RQ1_REFERENCE = [
    {"model": "DeepSeek-R1", "pass_at_1": 51.5, "dsr_at_1": 62.1},
    {"model": "DeepSeek-V3", "pass_at_1": 50.1, "dsr_at_1": 58.7},
    {"model": "Claude-3.5", "pass_at_1": 43.5, "dsr_at_1": 56.5},
    {"model": "Qwen-2.5-coder-32B", "pass_at_1": 34.4, "dsr_at_1": 38.9},
]


def validate_config() -> None:
    if PROTOCOL != {
        "model": "gpt-5.6-sol",
        "effort_default": "max",
        "agent_timeout_seconds": 5000,
        "max_iter": 5,
        "max_parity_rounds": 3,
        "repetitions": 3,
    }:
        raise ValueError("protocol drifted")
    if len(REPOTRANSBENCH_SUBJECTS) != 3 or sum(
        row["tests"] for row in REPOTRANSBENCH_SUBJECTS
    ) != 37:
        raise ValueError("RepoTransBench subject lock drifted")
    if len(RUSTREPOTRANS_SUBJECTS) != 3:
        raise ValueError("RustRepoTrans subject lock drifted")
    if {row["source_language"] for row in RUSTREPOTRANS_SUBJECTS} != {
        "C",
        "Java",
        "Python",
    }:
        raise ValueError("RustRepoTrans language stratification drifted")
    if len(SACTOR_SUBJECTS) != 50 or len(set(SACTOR_SUBJECTS)) != 50:
        raise ValueError("SACTOR subset drifted")
    if (
        len(CRUST_TABLE4) != 13
        or len(REPOTRANSBENCH_PYTHON_JAVA) != 8
        or len(REPOTRANSBENCH_V1_RESULTS) != 11
    ):
        raise ValueError("paper reference table drifted")
    if set(UPSTREAM_REPOSITORIES) != {
        "crust_bench",
        "alphatrans",
        "repotransbench",
        "sactor",
        "rustrepotrans",
    }:
        raise ValueError("upstream repository lock drifted")


validate_config()
