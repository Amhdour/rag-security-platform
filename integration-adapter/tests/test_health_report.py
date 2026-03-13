from __future__ import annotations

import json

from integration_adapter.config import AdapterConfig
from integration_adapter.health_report import build_health_report
from integration_adapter.pipeline import generate_artifacts


def test_health_report_healthy_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INTEGRATION_ADAPTER_DB_SOURCE_MODE_LIVE", "")
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    generate_artifacts(force_demo=True, config=config)

    report = build_health_report(artifacts_root=config.artifacts_root)

    assert report["run_status"] in {"success", "degraded_success"}
    assert "selected_source_mode" in report
    assert "integrity" in report
    assert report["integrity"]["ok"] is True


def test_health_report_degraded_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS", "0")
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    generate_artifacts(force_demo=True, config=config)

    report = build_health_report(artifacts_root=config.artifacts_root)

    assert report["run_status"] == "degraded_success"
    assert report["launch_gate"]["freshness"]["stale_count"] >= 0


def test_health_report_failed_run(tmp_path, monkeypatch) -> None:
    import integration_adapter.pipeline as pipeline

    original = pipeline.ArtifactWriter.write_eval_results

    def _boom(self, run_id, rows):  # noqa: ANN001
        raise RuntimeError("forced write failure")

    monkeypatch.setattr(pipeline.ArtifactWriter, "write_eval_results", _boom)

    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    try:
        generate_artifacts(force_demo=True, config=config)
    except RuntimeError:
        pass

    report = build_health_report(artifacts_root=config.artifacts_root)

    assert report["run_status"] == "failed_run"
    assert report["failure_category"] in {"artifact_write_failure", "pipeline_failure", "integrity_failure"}

    monkeypatch.setattr(pipeline.ArtifactWriter, "write_eval_results", original)


def test_health_report_fallback_heavy_run(tmp_path, monkeypatch) -> None:
    import integration_adapter.pipeline as pipeline
    from integration_adapter.pipeline import CollectedPayload

    monkeypatch.setattr(
        pipeline,
        "collect_from_onyx",
        lambda force_demo: CollectedPayload(
            mode="live",
            raw_source_schema_version="1.0",
            exporter_diagnostics={
                "connectors": {"source_mode": "file_backed", "fallback_used": True, "warnings": ["fallback"], "errors": [], "rows_count": 1},
                "tools": {"source_mode": "file_backed", "fallback_used": True, "warnings": ["fallback"], "errors": [], "rows_count": 1},
                "mcp_servers": {"source_mode": "file_backed", "fallback_used": True, "warnings": ["fallback"], "errors": [], "rows_count": 1},
                "evals": {"source_mode": "file_backed", "fallback_used": True, "warnings": ["fallback"], "errors": [], "rows_count": 1},
                "runtime_events": {"source_mode": "file_backed", "fallback_used": True, "warnings": ["fallback"], "errors": [], "rows_count": 3},
            },
            connectors=[{"id": "c1", "name": "con", "status": "active", "source_type": "wiki", "indexed": True}],
            tools=[{"id": "t1", "name": "tool", "status": "enabled", "risk_tier": "low", "enabled": True}],
            mcp_servers=[{"id": "m1", "name": "mcp", "status": "connected", "endpoint": "http://mcp", "usage_count": 1}],
            evals=[{"id": "e1", "suite": "suite", "passed": True, "score": 1, "scenario": "ok"}],
            runtime_events=[
                {"request_id": "r1", "trace_id": "t1", "event_type": "request.start", "actor_id": "u", "tenant_id": "t", "event_payload": {}},
                {"request_id": "r1", "trace_id": "t1", "event_type": "policy.decision", "actor_id": "u", "tenant_id": "t", "event_payload": {}},
                {"request_id": "r1", "trace_id": "t1", "event_type": "request.end", "actor_id": "u", "tenant_id": "t", "event_payload": {}},
            ],
        ),
    )

    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    generate_artifacts(force_demo=False, config=config)

    report = build_health_report(artifacts_root=config.artifacts_root)

    assert report["fallback_usage_count"] >= 5
    assert report["run_status"] == "degraded_success"


def test_retention_writes_health_outcome(tmp_path) -> None:
    from integration_adapter.artifact_retention import apply_retention_policy, write_retention_outcome

    root = tmp_path / "artifacts" / "logs"
    result = apply_retention_policy(artifacts_root=root, profile="ci", dry_run=True)
    path = write_retention_outcome(artifacts_root=root, payload=result.to_dict())
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["profile"] == "ci"
