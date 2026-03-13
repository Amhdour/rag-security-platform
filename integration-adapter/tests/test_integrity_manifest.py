from __future__ import annotations

import json

from integration_adapter.config import AdapterConfig
from integration_adapter.integrity import (
    INTEGRITY_MANIFEST_FILENAME,
    INTEGRITY_MODE_SIGNED_MANIFEST,
    verify_integrity_manifest,
)
from integration_adapter.pipeline import generate_artifacts


REQUIRED_PATHS = [
    "artifact_bundle.contract.json",
    "audit.jsonl",
    "connectors.inventory.json",
    "tools.inventory.json",
    "mcp_servers.inventory.json",
    "evals.inventory.json",
    "adapter_health/adapter_run_summary.json",
]


def test_generate_artifacts_writes_integrity_manifest(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    assert result.integrity_manifest_path.name == INTEGRITY_MANIFEST_FILENAME
    payload = json.loads(result.integrity_manifest_path.read_text(encoding="utf-8"))
    assert payload["integrity_manifest_schema_version"] == "1.1"
    assert payload["artifact_count"] > 0
    assert payload["integrity_mode"] == "hash_only"


def test_integrity_verify_detects_hash_mismatch(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    (config.artifacts_root / "audit.jsonl").write_text('{"tampered": true}\n', encoding="utf-8")

    verification = verify_integrity_manifest(
        artifacts_root=config.artifacts_root,
        required_paths=REQUIRED_PATHS,
        integrity_mode="hash_only",
    )

    assert result.integrity_manifest_path.is_file()
    assert verification.ok is False
    assert "audit.jsonl" in verification.hash_mismatches


def test_integrity_verify_detects_missing_manifest(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    generate_artifacts(force_demo=True, config=config)

    (config.artifacts_root / INTEGRITY_MANIFEST_FILENAME).unlink()

    verification = verify_integrity_manifest(
        artifacts_root=config.artifacts_root,
        required_paths=REQUIRED_PATHS,
        integrity_mode="hash_only",
    )

    assert verification.ok is False
    assert INTEGRITY_MANIFEST_FILENAME in verification.missing_required


def test_signed_manifest_verification_success(tmp_path) -> None:
    key_path = tmp_path / "signing.key"
    key_path.write_text("dev-only-signing-secret", encoding="utf-8")

    config = AdapterConfig(
        artifacts_root=tmp_path / "artifacts" / "logs",
        integrity_mode=INTEGRITY_MODE_SIGNED_MANIFEST,
        integrity_signing_key_path=key_path,
        integrity_signing_key_id="test-key",
    )
    generate_artifacts(force_demo=True, config=config)

    verification = verify_integrity_manifest(
        artifacts_root=config.artifacts_root,
        required_paths=REQUIRED_PATHS,
        integrity_mode=INTEGRITY_MODE_SIGNED_MANIFEST,
        signing_key_path=key_path,
    )

    assert verification.ok is True
    assert verification.signature_verified is True
    assert verification.signature_errors == []


def test_signed_manifest_verification_failure_with_wrong_key(tmp_path) -> None:
    key_path = tmp_path / "signing.key"
    key_path.write_text("correct-secret", encoding="utf-8")
    wrong_key_path = tmp_path / "wrong.key"
    wrong_key_path.write_text("wrong-secret", encoding="utf-8")

    config = AdapterConfig(
        artifacts_root=tmp_path / "artifacts" / "logs",
        integrity_mode=INTEGRITY_MODE_SIGNED_MANIFEST,
        integrity_signing_key_path=key_path,
        integrity_signing_key_id="test-key",
    )
    generate_artifacts(force_demo=True, config=config)

    verification = verify_integrity_manifest(
        artifacts_root=config.artifacts_root,
        required_paths=REQUIRED_PATHS,
        integrity_mode=INTEGRITY_MODE_SIGNED_MANIFEST,
        signing_key_path=wrong_key_path,
    )

    assert verification.ok is False
    assert verification.signature_verified is False
    assert any("signature verification failed" in item for item in verification.signature_errors)


def test_launch_gate_fails_when_signed_manifest_verification_fails(tmp_path, monkeypatch) -> None:
    from integration_adapter.launch_gate_evaluator import LaunchGateEvaluator

    key_path = tmp_path / "signing.key"
    key_path.write_text("correct-secret", encoding="utf-8")

    config = AdapterConfig(
        artifacts_root=tmp_path / "artifacts" / "logs",
        integrity_mode=INTEGRITY_MODE_SIGNED_MANIFEST,
        integrity_signing_key_path=key_path,
        integrity_signing_key_id="test-key",
    )
    generate_artifacts(force_demo=True, config=config)

    wrong_key = tmp_path / "wrong.key"
    wrong_key.write_text("wrong-secret", encoding="utf-8")
    monkeypatch.setenv("INTEGRATION_ADAPTER_INTEGRITY_MODE", "signed_manifest")
    monkeypatch.setenv("INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_PATH", str(wrong_key))

    evaluation = LaunchGateEvaluator(config.artifacts_root).evaluate()

    assert evaluation.status == "no_go"
    assert any("artifact_integrity_manifest" in blocker for blocker in evaluation.blockers)
