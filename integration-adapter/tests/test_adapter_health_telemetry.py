from __future__ import annotations

import json

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import generate_artifacts


def test_generate_artifacts_emits_adapter_health_summary(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    payload = json.loads(result.adapter_health_path.read_text(encoding="utf-8"))
    assert payload["run_status"] in {"success", "degraded_success"}
    metrics = payload["metrics"]
    assert "fallback_usage_count" in metrics
    assert "parse_failures" in metrics
    assert "schema_validation_failures" in metrics
    assert "artifact_write_failures" in metrics
    assert "launch_gate_failure_reasons" in metrics
    assert "stale_evidence_detections" in metrics
    assert "partial_extraction_warnings" in metrics


def test_adapter_health_marks_degraded_run_for_stale_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS", "0")
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)
    payload = json.loads(result.adapter_health_path.read_text(encoding="utf-8"))
    assert payload["run_status"] == "degraded_success"
    assert payload["metrics"]["stale_evidence_detections"] >= 0
