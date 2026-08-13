from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codeweaver.app import _build_local_tracker


def test_local_tracker_project_creation_is_parallel_safe(tmp_path: Path):
    def create_tracker(_index: int):
        return _build_local_tracker("shared-project", tmp_path)

    with ThreadPoolExecutor(max_workers=8) as pool:
        trackers = list(pool.map(create_tracker, range(24)))

    expected = tmp_path / "shared-project"
    assert expected.is_dir()
    assert {Path(tracker.storage_dir) for tracker in trackers} == {expected}
