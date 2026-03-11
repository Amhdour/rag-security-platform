"""Tests for artifact path adapter used by dashboard read services."""

from pathlib import Path

from observability.artifact_paths import ArtifactPaths


def test_artifact_paths_resolve_default_and_demo_modes(tmp_path: Path) -> None:
    paths_default = ArtifactPaths.from_root(repo_root=tmp_path)
    assert paths_default.audit_jsonl == tmp_path / "artifacts/logs/audit.jsonl"
    assert paths_default.demo_mode is False

    paths_demo = ArtifactPaths.from_root(repo_root=tmp_path, artifacts_root="artifacts/demo/dashboard_logs")
    assert paths_demo.replay_dir == tmp_path / "artifacts/demo/dashboard_logs/replay"
    assert paths_demo.demo_mode is True
