from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from integration_adapter.artifact_retention import apply_retention_policy


def _write_file(path: Path, *, age_seconds: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    old = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    ts = old.timestamp()
    os.utime(path, (ts, ts))


def test_retention_selects_expired_non_protected_files(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _write_file(root / "launch_gate" / "security-readiness-old.json", age_seconds=5 * 24 * 3600)
    _write_file(root / "launch_gate" / "security-readiness-old.md", age_seconds=5 * 24 * 3600)
    _write_file(root / "launch_gate" / "security-readiness-fresh.json", age_seconds=60)

    result = apply_retention_policy(artifacts_root=root, profile="demo", dry_run=True)

    paths = {item.path.name for item in result.candidates}
    assert "security-readiness-old.json" in paths
    assert "security-readiness-old.md" in paths
    assert "security-readiness-fresh.json" not in paths
    assert result.deleted_paths == []


def test_retention_apply_deletes_expired_files(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    target = root / "evals" / "old-suite.summary.json"
    _write_file(target, age_seconds=20 * 24 * 3600)

    result = apply_retention_policy(artifacts_root=root, profile="dev", dry_run=False)

    assert any(item.path == target for item in result.candidates)
    assert target in result.deleted_paths
    assert not target.exists()


def test_retention_preserves_required_and_manifest_referenced_files(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    protected = root / "audit.jsonl"
    _write_file(protected, age_seconds=60 * 24 * 3600)
    referenced = root / "launch_gate" / "security-readiness-referenced.json"
    _write_file(referenced, age_seconds=60 * 24 * 3600)

    manifest = {
        "integrity_manifest_schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": 1,
        "artifacts": [
            {"path": "launch_gate/security-readiness-referenced.json", "sha256": "x", "size_bytes": 2},
        ],
    }
    (root / "artifact_integrity.manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (root / "artifact_integrity.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = apply_retention_policy(artifacts_root=root, profile="demo", dry_run=False)

    candidate_paths = {item.path for item in result.candidates}
    assert protected not in candidate_paths
    assert referenced not in candidate_paths
    assert protected.exists()
    assert referenced.exists()


def test_retention_preserves_latest_successful_launch_gate_run(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    old_json = root / "launch_gate" / "security-readiness-20240101T010101Z.json"
    new_json = root / "launch_gate" / "security-readiness-20240102T010101Z.json"
    _write_file(old_json, age_seconds=60 * 24 * 3600)
    _write_file(new_json, age_seconds=59 * 24 * 3600)

    old_json.write_text(json.dumps({"status": "go", "generated_at": "2024-01-01T01:01:01+00:00"}), encoding="utf-8")
    new_json.write_text(json.dumps({"status": "conditional_go", "generated_at": "2024-01-02T01:01:01+00:00"}), encoding="utf-8")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).timestamp()
    new_ts = (datetime.now(timezone.utc) - timedelta(days=59)).timestamp()
    os.utime(old_json, (old_ts, old_ts))
    os.utime(new_json, (new_ts, new_ts))

    result = apply_retention_policy(
        artifacts_root=root,
        profile="demo",
        dry_run=False,
        keep_latest_successful_runs=1,
    )

    candidate_paths = {item.path for item in result.candidates}
    assert new_json not in candidate_paths
    assert new_json.exists()
    assert old_json in candidate_paths


def test_retention_dry_run_preserves_files(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    target = root / "launch_gate" / "security-readiness-old.json"
    _write_file(target, age_seconds=90 * 24 * 3600)

    result = apply_retention_policy(artifacts_root=root, profile="ci", dry_run=True)

    assert any(item.path == target for item in result.candidates)
    assert result.deleted_paths == []
    assert target.exists()
