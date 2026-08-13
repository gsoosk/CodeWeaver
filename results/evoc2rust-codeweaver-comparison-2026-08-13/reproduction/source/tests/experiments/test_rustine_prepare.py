from __future__ import annotations

import copy
import json
from pathlib import Path

from codeweaver.config import load as load_codeweaver_config
from experiments.rustine.config import load_subject_config
from experiments.rustine.evaluator import materialize_evaluation_copy
from experiments.rustine.prepare import prepare_subject


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _synthetic_qsort_artifact(root: Path) -> None:
    subject = root / "artifacts" / "qsort"
    _write(subject / "preprocess" / "qsort.c", "int qsort_like(void) { return 0; }\n")
    _write(
        subject / "skeleton" / "Cargo.toml",
        '[package]\nname = "qsortrs"\nversion = "0.1.0"\nedition = "2021"\n'
        "\n[dependencies]\n",
    )
    _write(subject / "skeleton" / "src" / "lib.rs", "pub mod qsort;\npub use qsort::*;\n")
    _write(subject / "skeleton" / "src" / "qsort.rs", "pub fn quick_sort() {}\n")
    _write(
        subject / "translate" / "Cargo.toml",
        '[package]\nname = "translate_without_break_down"\nversion = "0.1.0"\nedition = "2021"\n'
        '\n[dependencies]\n\n[[bin]]\nname = "test"\npath = "src/test_main.rs"\n',
    )
    _write(
        subject / "translate" / "src" / "lib.rs",
        "pub mod qsort;\npub use qsort::*;\npub mod test;\npub use test::*;\n",
    )
    _write(
        subject / "translate" / "src" / "test.rs",
        "use translate::*;\npub fn fixed_test() { quick_sort(); }\n",
    )
    _write(
        subject / "translate" / "src" / "test_main.rs",
        "use translate::*;\nfn main() { fixed_test(); }\n",
    )
    _write(
        subject / "translate" / "src" / "secret_solution.rs",
        "pub fn leaked_solution() {}\n",
    )
    _write(subject / "translate" / "translation.json", '{"solution": true}\n')


def test_prepare_copies_only_fixed_contract_and_loadable_codeweaver_config(tmp_path):
    artifact = tmp_path / "artifact"
    workspace_root = tmp_path / "workspaces"
    _synthetic_qsort_artifact(artifact)
    config = load_subject_config()
    subject = copy.deepcopy(config["subjects"][0])
    subject["contract"]["executions"] = [
        {"target": "test", "args": ["--version"], "stdin": None}
    ]

    marker = prepare_subject(
        subject,
        artifact_root=artifact,
        workspace_root=workspace_root,
        protocol=config["protocol"],
    )
    workspace = workspace_root / "1"
    assert marker["ground_truth_excluded"] is True
    assert not (workspace / "scaffold" / "translation.json").exists()
    assert not (workspace / "scaffold" / "src" / "secret_solution.rs").exists()
    assert set(
        path.relative_to(workspace / "oracle").as_posix()
        for path in (workspace / "oracle").rglob("*")
        if path.is_file()
    ) == {"src/test.rs", "src/test_main.rs", "contract.json"}
    assert "use qsortrs::*;" in (
        workspace / "scaffold" / "src" / "test.rs"
    ).read_text(encoding="utf-8")
    assert "pub mod test;" in (
        workspace / "scaffold" / "src" / "lib.rs"
    ).read_text(encoding="utf-8")
    contract = json.loads(
        (workspace / "oracle" / "contract.json").read_text(encoding="utf-8")
    )
    assert contract["executions"] == subject["contract"]["executions"]

    cargo = (workspace / "scaffold" / "Cargo.toml").read_text(encoding="utf-8")
    assert 'name = "qsortrs"' in cargo
    assert 'name = "test"' in cargo
    loaded = load_codeweaver_config(workspace / "codeweaver.toml")
    assert loaded.source_dir == "source"
    assert loaded.reference_dirs == ["oracle"]
    assert loaded.immutable_input == "scaffold"
    assert loaded.working_copy == "pipeline/target"
    assert "immutable_evaluator.py --stage test" in loaded.unit_test_cmd


def test_evaluator_restores_contract_cargo_and_module_wiring(tmp_path):
    artifact = tmp_path / "artifact"
    workspace_root = tmp_path / "workspaces"
    _synthetic_qsort_artifact(artifact)
    config = load_subject_config()
    prepare_subject(
        config["subjects"][0],
        artifact_root=artifact,
        workspace_root=workspace_root,
        protocol=config["protocol"],
    )
    workspace = workspace_root / "1"
    target = workspace / "pipeline" / "target"
    target.mkdir(parents=True)
    _write(
        target / "Cargo.toml",
        '[package]\nname = "weakened"\nversion = "9"\nedition = "2018"\n'
        'build = "evil.rs"\n\n[lib]\npath = "src/fake.rs"\n'
        "\n[dependencies]\n\n[workspace]\nmembers = []\n",
    )
    _write(target / ".cargo" / "config.toml", '[build]\nrustflags = ["--cfg", "bypass"]\n')
    _write(target / "rust-toolchain.toml", '[toolchain]\nchannel = "stable"\n')
    _write(target / "evil.rs", "fn main() {}\n")
    _write(
        target / "src" / "lib.rs",
        '#[path = "fake.rs"]\npub mod test;\npub mod qsort;\n',
    )
    _write(target / "src" / "qsort.rs", "pub fn quick_sort() {}\n")
    _write(target / "src" / "fake.rs", "pub fn fixed_test() {}\n")
    _write(target / "src" / "test.rs", "pub fn fixed_test() {}\n")

    scratch, project, lock = materialize_evaluation_copy(target, workspace / "oracle")
    try:
        assert lock["targets"] == ["test"]
        assert "quick_sort();" in (project / "src" / "test.rs").read_text(encoding="utf-8")
        lib = (project / "src" / "lib.rs").read_text(encoding="utf-8")
        assert "pub mod test;" in lib
        assert '#[path = "fake.rs"]' not in lib
        cargo = (project / "Cargo.toml").read_text(encoding="utf-8")
        assert 'name = "qsortrs"' in cargo
        assert '[lib]\nname = "qsortrs"\npath = "src/lib.rs"' in cargo
        assert 'name = "test"' in cargo
        assert 'path = "src/test_main.rs"' in cargo
        assert "[workspace]" not in cargo
        assert 'build = "evil.rs"' not in cargo
        assert not (project / ".cargo").exists()
        assert not (project / "rust-toolchain.toml").exists()
        assert scratch.parent != target.parent
    finally:
        import shutil

        shutil.rmtree(scratch)
