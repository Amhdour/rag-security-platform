from __future__ import annotations

from integration_adapter.artifact_output import ArtifactWriter
from integration_adapter.config import AdapterConfig
from integration_adapter.mappers import (
    map_connector_inventory,
    map_eval_inventory,
    map_mcp_inventory,
    map_runtime_event,
    map_tool_inventory,
)


def generate_sample_artifacts() -> None:
    config = AdapterConfig.from_env(default_root="artifacts/logs")
    writer = ArtifactWriter(config)

    connectors = map_connector_inventory(
        [
            {"id": "con-1", "name": "confluence", "status": "active", "source_type": "wiki", "indexed": True},
            {"id": "con-2", "name": "github", "status": "active", "source_type": "code", "indexed": True},
        ]
    )
    tools = map_tool_inventory(
        [
            {"id": "tool-1", "name": "search", "status": "enabled", "risk_tier": "low", "enabled": True},
            {"id": "tool-2", "name": "admin_shell", "status": "guarded", "risk_tier": "high", "enabled": False},
        ]
    )
    mcp_servers = map_mcp_inventory(
        [{"id": "mcp-1", "name": "ops-mcp", "status": "connected", "endpoint": "https://mcp.local", "usage_count": 3}]
    )
    evals = map_eval_inventory(
        [
            {"id": "eval-1", "suite": "security_baseline", "passed": True, "score": 0.95, "scenario": "prompt_injection_direct"},
            {"id": "eval-2", "suite": "security_baseline", "passed": False, "score": 0.40, "scenario": "policy_bypass_attempt"},
        ]
    )

    contract_path = writer.write_bundle_contract()
    connectors_path = writer.write_inventory_snapshot(domain="connectors", rows=connectors)
    tools_path = writer.write_inventory_snapshot(domain="tools", rows=tools)
    mcp_path = writer.write_inventory_snapshot(domain="mcp_servers", rows=mcp_servers)
    eval_inventory_path = writer.write_inventory_snapshot(domain="evals", rows=evals)

    raw_events = [
        {"request_id": "req-1", "trace_id": "trace-1", "event_type": "request.start", "actor_id": "user-1", "tenant_id": "tenant-a", "event_payload": {"entrypoint": "chat"}},
        {"request_id": "req-1", "trace_id": "trace-1", "event_type": "policy.decision", "actor_id": "policy-engine", "tenant_id": "tenant-a", "event_payload": {"decision": "allow"}},
        {"request_id": "req-1", "trace_id": "trace-1", "event_type": "retrieval.decision", "actor_id": "retrieval", "tenant_id": "tenant-a", "event_payload": {"source": "confluence"}},
        {"request_id": "req-1", "trace_id": "trace-1", "event_type": "tool.decision", "actor_id": "tool-router", "tenant_id": "tenant-a", "event_payload": {"tool": "search", "decision": "allow"}},
        {"request_id": "req-1", "trace_id": "trace-1", "event_type": "request.end", "actor_id": "orchestrator", "tenant_id": "tenant-a", "event_payload": {"outcome": "success"}},
    ]
    events = [map_runtime_event(row) for row in raw_events]
    audit_path = writer.write_audit_events(events)
    replay_path = writer.write_replay(replay_id="trace-1", payload={"trace_id": "trace-1", "request_id": "req-1", "events": [event.to_dict() for event in events]})
    eval_jsonl_path, eval_summary_path = writer.write_eval_results(
        run_id="sample-security",
        rows=[
            {"scenario_id": "prompt_injection_direct", "outcome": "pass", "severity": "high"},
            {"scenario_id": "policy_bypass_attempt", "outcome": "fail", "severity": "critical"},
        ],
    )
    launch_gate_path = writer.write_launch_gate_summary(statuses=["pass", "pass", "fail"], blockers=["policy_bypass_attempt failed"], residual_risks=["mcp usage model incomplete"])

    writer.write_integrity_manifest(
        file_paths=[
            contract_path,
            connectors_path,
            tools_path,
            mcp_path,
            eval_inventory_path,
            audit_path,
            replay_path,
            eval_jsonl_path,
            eval_summary_path,
            launch_gate_path,
        ]
    )


if __name__ == "__main__":
    generate_sample_artifacts()
