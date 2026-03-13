from __future__ import annotations

import json

from integration_adapter.config import AdapterConfig
from integration_adapter.integrity import INTEGRITY_MANIFEST_FILENAME, verify_integrity_manifest
from integration_adapter.pipeline import generate_artifacts


def test_generate_artifacts_writes_integrity_manifest(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    assert result.integrity_manifest_path.name == INTEGRITY_MANIFEST_FILENAME
    payload = json.loads(result.integrity_manifest_path.read_text(encoding="utf-8"))
    assert payload["integrity_manifest_schema_version"] == "1.0"
    assert payload["artifact_count"] > 0


def test_integrity_verify_detects_hash_mismatch(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    (config.artifacts_root / "audit.jsonl").write_text('{"tampered": true}\n', encoding="utf-8")

    verification = verify_integrity_manifest(
        artifacts_root=config.artifacts_root,
        required_paths=[
            "artifact_bundle.contract.json",
            "audit.jsonl",
            "connectors.inventory.json",
            "tools.inventory.json",
            "mcp_servers.inventory.json",
            "evals.inventory.json",
            "adapter_health/adapter_run_summary.json",
        ],
    )

    assert result.integrity_manifest_path.is_file()
    assert verification.ok is False
    assert "audit.jsonl" in verification.hash_mismatches
