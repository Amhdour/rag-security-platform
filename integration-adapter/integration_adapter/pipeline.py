from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from integration_adapter.artifact_output import ArtifactWriter
from integration_adapter.config import AdapterConfig
from integration_adapter.exporters import (
    ConnectorInventoryExporter,
    EvalResultsExporter,
    MCPInventoryExporter,
    RuntimeEventsExporter,
    ToolInventoryExporter,
)
from integration_adapter.launch_gate_evaluator import LaunchGateEvaluator
from integration_adapter.mappers import (
    map_connector_inventory,
    map_eval_inventory,
    map_mcp_inventory,
    map_runtime_event,
    map_tool_inventory,
)


@dataclass
class CollectedPayload:
    mode: str
    connectors: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    mcp_servers: list[dict[str, Any]]
    evals: list[dict[str, Any]]
    runtime_events: list[dict[str, Any]]


@dataclass
class PipelineResult:
    mode: str
    artifacts_root: Path
    audit_path: Path
    replay_paths: list[Path]
    eval_jsonl_path: Path
    eval_summary_path: Path
    launch_gate_path: Path


def collect_from_onyx(*, force_demo: bool = False) -> CollectedPayload:
    """Collect exporter payloads from Onyx-facing sources.

    If no live data is available (or force_demo=True), returns deterministic demo payloads.
    """

    connectors = ConnectorInventoryExporter().export()
    tools = ToolInventoryExporter().export()
    mcp_servers = MCPInventoryExporter().export()
    evals = EvalResultsExporter().export()
    runtime_events = RuntimeEventsExporter().export()

    has_live_data = any([connectors, tools, mcp_servers, evals, runtime_events])
    if force_demo or not has_live_data:
        return CollectedPayload(
            mode="demo",
            connectors=[
                {"id": "con-1", "name": "confluence", "status": "active", "source_type": "wiki", "indexed": True},
                {"id": "con-2", "name": "github", "status": "active", "source_type": "code", "indexed": True},
            ],
            tools=[
                {"id": "tool-1", "name": "search", "status": "enabled", "risk_tier": "low", "enabled": True},
                {"id": "tool-2", "name": "admin_shell", "status": "guarded", "risk_tier": "high", "enabled": False},
            ],
            mcp_servers=[
                {"id": "mcp-1", "name": "ops-mcp", "status": "connected", "endpoint": "https://mcp.local", "usage_count": 3}
            ],
            evals=[
                {"id": "eval-1", "suite": "security_baseline", "passed": True, "score": 0.95, "scenario": "prompt_injection_direct"},
                {"id": "eval-2", "suite": "security_baseline", "passed": False, "score": 0.40, "scenario": "policy_bypass_attempt"},
            ],
            runtime_events=[
                {"request_id": "req-1", "trace_id": "trace-1", "event_type": "request.start", "actor_id": "user-1", "tenant_id": "tenant-a", "event_payload": {"entrypoint": "chat"}},
                {"request_id": "req-1", "trace_id": "trace-1", "event_type": "policy.decision", "actor_id": "policy-engine", "tenant_id": "tenant-a", "event_payload": {"decision": "allow"}},
                {"request_id": "req-1", "trace_id": "trace-1", "event_type": "tool.decision", "actor_id": "tool-router", "tenant_id": "tenant-a", "event_payload": {"tool": "search", "decision": "allow"}},
                {"request_id": "req-1", "trace_id": "trace-1", "event_type": "request.end", "actor_id": "orchestrator", "tenant_id": "tenant-a", "event_payload": {"outcome": "success"}},
            ],
        )

    return CollectedPayload(
        mode="live",
        connectors=connectors,
        tools=tools,
        mcp_servers=mcp_servers,
        evals=evals,
        runtime_events=runtime_events,
    )


def generate_artifacts(*, force_demo: bool = False, config: AdapterConfig | None = None) -> PipelineResult:
    cfg = config or AdapterConfig.from_env(default_root="artifacts/logs")
    writer = ArtifactWriter(cfg)

    payload = collect_from_onyx(force_demo=force_demo)

    writer.write_inventory_snapshot(domain="connectors", rows=map_connector_inventory(payload.connectors))
    writer.write_inventory_snapshot(domain="tools", rows=map_tool_inventory(payload.tools))
    writer.write_inventory_snapshot(domain="mcp_servers", rows=map_mcp_inventory(payload.mcp_servers))
    writer.write_inventory_snapshot(domain="evals", rows=map_eval_inventory(payload.evals))

    events = [map_runtime_event(row) for row in payload.runtime_events]
    audit_path = writer.write_audit_events(events)

    by_trace: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_trace[event.trace_id].append(event.to_dict())

    replay_paths: list[Path] = []
    for trace_id, trace_events in by_trace.items():
        replay_paths.append(
            writer.write_replay(
                replay_id=trace_id,
                payload={
                    "trace_id": trace_id,
                    "request_id": trace_events[0].get("request_id", "unknown-request") if trace_events else "unknown-request",
                    "events": trace_events,
                },
            )
        )

    eval_rows = [
        {
            "scenario_id": str(row.get("scenario", row.get("id", "unknown-scenario"))),
            "outcome": "pass" if bool(row.get("passed", False)) else "fail",
            "severity": "high" if not bool(row.get("passed", False)) else "medium",
            "suite": str(row.get("suite", "unknown-suite")),
        }
        for row in payload.evals
    ]
    eval_jsonl_path, eval_summary_path = writer.write_eval_results(run_id=f"{payload.mode}-security", rows=eval_rows)

    evaluator = LaunchGateEvaluator(cfg.artifacts_root)
    evaluation = evaluator.evaluate()
    launch_gate_path, _ = evaluator.write_outputs(evaluation)

    return PipelineResult(
        mode=payload.mode,
        artifacts_root=cfg.artifacts_root,
        audit_path=audit_path,
        replay_paths=replay_paths,
        eval_jsonl_path=eval_jsonl_path,
        eval_summary_path=eval_summary_path,
        launch_gate_path=launch_gate_path,
    )


def run_launch_gate(*, config: AdapterConfig | None = None) -> Path:
    """Evaluate artifacts and emit machine + human launch-gate summaries."""

    cfg = config or AdapterConfig.from_env(default_root="artifacts/logs")
    cfg.ensure_dirs()

    evaluator = LaunchGateEvaluator(cfg.artifacts_root)
    evaluation = evaluator.evaluate()
    json_path, _ = evaluator.write_outputs(evaluation)
    return json_path
