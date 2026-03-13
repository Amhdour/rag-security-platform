from __future__ import annotations

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import collect_from_onyx, generate_artifacts, run_launch_gate


def test_collect_from_onyx_demo_mode_returns_payload() -> None:
    payload = collect_from_onyx(force_demo=True)
    assert payload.mode == "demo"
    assert payload.connectors
    assert payload.runtime_events


def test_generate_artifacts_writes_required_outputs(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    assert result.artifact_contract_path.is_file()
    assert result.adapter_health_path.is_file()
    assert result.audit_path.is_file()
    assert result.eval_jsonl_path.is_file()
    assert result.eval_summary_path.is_file()
    assert result.launch_gate_path.is_file()
    assert result.replay_paths
    assert result.replay_paths[0].is_file()


def test_run_launch_gate_fails_closed_without_eval_summaries(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    launch_path = run_launch_gate(config=config)
    payload = launch_path.read_text(encoding="utf-8")
    assert "missing eval JSONL or summary artifacts" in payload
    assert '"status": "no_go"' in payload


def test_generate_artifacts_blocks_on_incompatible_source_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INTEGRATION_ADAPTER_EXPECTED_SOURCE_SCHEMA_VERSION", "2.0")
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    try:
        generate_artifacts(force_demo=True, config=config)
        assert False, "expected compatibility failure"
    except ValueError as exc:
        assert "schema compatibility blocked" in str(exc)


def test_generate_artifacts_warns_on_forward_minor_version(tmp_path, monkeypatch) -> None:
    from integration_adapter.pipeline import CollectedPayload
    import integration_adapter.pipeline as pipeline

    monkeypatch.setattr(
        pipeline,
        "collect_from_onyx",
        lambda force_demo: CollectedPayload(
            mode="demo",
            raw_source_schema_version="1.1",
            exporter_diagnostics={"connectors": {"source_mode": "file_backed", "fallback_used": False, "warnings": [], "errors": []}},
            connectors=[{"id": "c1", "name": "confluence", "status": "active", "source_type": "wiki", "indexed": True}],
            tools=[{"id": "t1", "name": "search", "status": "enabled", "risk_tier": "low", "enabled": True}],
            mcp_servers=[{"id": "m1", "name": "ops", "status": "connected", "endpoint": "https://mcp.local", "usage_count": 1}],
            evals=[{"id": "e1", "suite": "security_baseline", "passed": True, "score": 1.0, "scenario": "ok"}],
            runtime_events=[
                {"request_id": "req", "trace_id": "trace", "event_type": "request.start", "actor_id": "u", "tenant_id": "t", "event_payload": {}},
                {"request_id": "req", "trace_id": "trace", "event_type": "policy.decision", "actor_id": "p", "tenant_id": "t", "event_payload": {}},
                {"request_id": "req", "trace_id": "trace", "event_type": "request.end", "actor_id": "o", "tenant_id": "t", "event_payload": {}},
            ],
        ),
    )
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=False, config=config)
    assert any(decision.status == "warn_only" and decision.contract_name == "source_schema" for decision in result.compatibility_decisions)


def test_generate_artifacts_blocks_demo_mode_in_prod_like_profile(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs", profile="prod_like")
    try:
        generate_artifacts(force_demo=True, config=config)
        assert False, "expected profile safeguard failure"
    except ValueError as exc:
        assert "profile safeguards blocked run" in str(exc)


def test_generate_artifacts_records_artifact_write_failure(tmp_path, monkeypatch) -> None:
    import json
    import integration_adapter.pipeline as pipeline

    original = pipeline.ArtifactWriter.write_eval_results

    def _boom(self, run_id, rows):
        raise RuntimeError("forced write failure")

    monkeypatch.setattr(pipeline.ArtifactWriter, "write_eval_results", _boom)

    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    try:
        generate_artifacts(force_demo=True, config=config)
        assert False, "expected artifact write failure"
    except RuntimeError as exc:
        assert "forced write failure" in str(exc)

    summary_path = config.artifacts_root / "adapter_health" / "adapter_run_summary.json"
    assert summary_path.is_file()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["run_status"] == "failed_run"
    assert payload["metrics"]["artifact_write_failures"] == 1

    monkeypatch.setattr(pipeline.ArtifactWriter, "write_eval_results", original)
