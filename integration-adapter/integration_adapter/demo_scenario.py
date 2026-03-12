from __future__ import annotations

import argparse
import json
import sys
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


def _synthetic_runtime_events() -> list[dict[str, Any]]:
    return [
        {
            "request_id": "demo-req-1",
            "trace_id": "demo-trace-1",
            "event_type": "request.start",
            "actor_id": "demo-user",
            "tenant_id": "tenant-demo",
            "event_payload": {"entrypoint": "chat", "synthetic": True},
        },
        {
            "request_id": "demo-req-1",
            "trace_id": "demo-trace-1",
            "event_type": "retrieval.decision",
            "actor_id": "retrieval",
            "tenant_id": "tenant-demo",
            "event_payload": {"source_id": "con-1", "query": "how to reset password", "allowed": True, "synthetic": True},
        },
        {
            "request_id": "demo-req-1",
            "trace_id": "demo-trace-1",
            "event_type": "tool.decision",
            "actor_id": "tool-router",
            "tenant_id": "tenant-demo",
            "event_payload": {"tool_name": "search", "decision": "allow", "synthetic": True},
        },
        {
            "request_id": "demo-req-1",
            "trace_id": "demo-trace-1",
            "event_type": "tool.execution_attempt",
            "actor_id": "mcp-runtime",
            "tenant_id": "tenant-demo",
            "event_payload": {"mcp_server": "ops-mcp", "tool_name": "runbook.lookup", "decision": "allow", "synthetic": True},
        },
        {
            "request_id": "demo-req-1",
            "trace_id": "demo-trace-1",
            "event_type": "policy.decision",
            "actor_id": "policy-engine",
            "tenant_id": "tenant-demo",
            "event_payload": {"decision": "allow", "synthetic": True},
        },
        {
            "request_id": "demo-req-1",
            "trace_id": "demo-trace-1",
            "event_type": "request.end",
            "actor_id": "orchestrator",
            "tenant_id": "tenant-demo",
            "event_payload": {"outcome": "success", "synthetic": True},
        },
    ]


def _default_connectors() -> list[dict[str, Any]]:
    return [
        {"id": "con-1", "name": "confluence", "status": "active", "source_type": "wiki", "indexed": True, "synthetic": True},
        {"id": "con-2", "name": "github", "status": "active", "source_type": "code", "indexed": True, "synthetic": True},
    ]


def _default_tools() -> list[dict[str, Any]]:
    return [
        {"id": "tool-1", "name": "search", "status": "enabled", "risk_tier": "low", "enabled": True, "synthetic": True},
        {"id": "tool-2", "name": "ticket_lookup", "status": "enabled", "risk_tier": "medium", "enabled": True, "synthetic": True},
    ]


def _default_mcp() -> list[dict[str, Any]]:
    return [
        {"id": "mcp-1", "name": "ops-mcp", "status": "connected", "endpoint": "https://mcp.local", "usage_count": 1, "synthetic": True}
    ]


def _default_evals() -> list[dict[str, Any]]:
    return [
        {"id": "eval-1", "suite": "security_baseline", "passed": True, "score": 0.97, "scenario": "prompt_injection_direct", "synthetic": True},
        {"id": "eval-2", "suite": "security_baseline", "passed": True, "score": 0.93, "scenario": "tool_misuse_attempt", "synthetic": True},
    ]


def _verify_dashboard_can_read(repo_root: Path, artifacts_root: Path) -> dict[str, Any]:
    """Best-effort verification using Starter Kit artifact readers."""

    starterkit_root = repo_root / "myStarterKit-maindashb-main"
    if not starterkit_root.exists():
        return {"verified": False, "reason": "starterkit_root_missing"}

    inserted = False
    starterkit_path = str(starterkit_root)
    if starterkit_path not in sys.path:
        sys.path.insert(0, starterkit_path)
        inserted = True
    try:
        from observability.artifact_readers import ArtifactReaders  # type: ignore

        reader = ArtifactReaders(starterkit_root, artifacts_root=str(artifacts_root.resolve()))
        payload = reader.read_all()
        launch_outputs = payload.get("launch_gate_output_json", [])
        launch_ok = any(item.parsed for item in launch_outputs) if launch_outputs else False
        audit = payload.get("audit_jsonl")
        audit_ok = bool(getattr(audit, "parsed", False))
        return {
            "verified": launch_ok and audit_ok,
            "launch_parsed": launch_ok,
            "audit_parsed": audit_ok,
            "launch_count": len(launch_outputs),
        }
    except Exception as exc:
        return {"verified": False, "reason": f"reader_error:{exc.__class__.__name__}"}
    finally:
        if inserted:
            try:
                sys.path.remove(starterkit_path)
            except ValueError:
                pass


def run_demo_scenario(config: AdapterConfig | None = None) -> dict[str, Any]:
    cfg = config or AdapterConfig.from_env(default_root="artifacts/logs")
    writer = ArtifactWriter(cfg)

    connectors_real = ConnectorInventoryExporter().export()
    tools_real = ToolInventoryExporter().export()
    mcp_real = MCPInventoryExporter().export()
    evals_real = EvalResultsExporter().export()
    runtime_real = RuntimeEventsExporter().export()

    connectors = connectors_real or _default_connectors()
    tools = tools_real or _default_tools()
    mcp_servers = mcp_real or _default_mcp()
    evals = evals_real or _default_evals()

    # Keep runtime event story deterministic for demo narrative.
    runtime_events = runtime_real or _synthetic_runtime_events()

    writer.write_inventory_snapshot(domain="connectors", rows=map_connector_inventory(connectors))
    writer.write_inventory_snapshot(domain="tools", rows=map_tool_inventory(tools))
    writer.write_inventory_snapshot(domain="mcp_servers", rows=map_mcp_inventory(mcp_servers))
    writer.write_inventory_snapshot(domain="evals", rows=map_eval_inventory(evals))

    normalized_events = [map_runtime_event(row) for row in runtime_events]
    audit_path = writer.write_audit_events(normalized_events)

    replay_payload = {
        "trace_id": "demo-trace-1",
        "request_id": "demo-req-1",
        "events": [event.to_dict() for event in normalized_events],
        "demo": True,
    }
    replay_path = writer.write_replay(replay_id="demo-trace-1", payload=replay_payload)

    eval_rows = [
        {
            "scenario_id": str(row.get("scenario", row.get("id", "unknown-scenario"))),
            "outcome": "pass" if bool(row.get("passed", False)) else "fail",
            "severity": "medium" if bool(row.get("passed", False)) else "high",
            "suite": str(row.get("suite", "demo-suite")),
            "demo": True,
        }
        for row in evals
    ]
    eval_jsonl_path, eval_summary_path = writer.write_eval_results(run_id="demo-e2e", rows=eval_rows)

    evaluator = LaunchGateEvaluator(cfg.artifacts_root)
    evaluation = evaluator.evaluate()
    launch_json_path, launch_md_path = evaluator.write_outputs(evaluation)

    repo_root = Path(__file__).resolve().parents[2]
    dashboard_verification = _verify_dashboard_can_read(repo_root, cfg.artifacts_root)

    report = {
        "scenario": "demo_e2e_runtime_to_governance",
        "synthetic_data": True,
        "real_vs_synthetic": {
            "connectors": "real" if connectors_real else "synthetic",
            "tools": "real" if tools_real else "synthetic",
            "mcp_inventory": "real" if mcp_real else "synthetic",
            "runtime_events": "real" if runtime_real else "synthetic",
            "eval_results": "real" if evals_real else "synthetic",
        },
        "artifacts_root": str(cfg.artifacts_root),
        "outputs": {
            "audit_jsonl": str(audit_path),
            "replay_json": str(replay_path),
            "eval_jsonl": str(eval_jsonl_path),
            "eval_summary": str(eval_summary_path),
            "launch_gate_json": str(launch_json_path),
            "launch_gate_markdown": str(launch_md_path),
        },
        "launch_gate_status": evaluation.status,
        "dashboard_read_verification": dashboard_verification,
    }

    report_path = cfg.artifacts_root / "demo_scenario.report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end demo scenario for integration workspace")
    parser.add_argument("--artifacts-root", default=None, help="override INTEGRATION_ADAPTER_ARTIFACTS_ROOT for this run")
    args = parser.parse_args()

    if args.artifacts_root:
        config = AdapterConfig(artifacts_root=Path(args.artifacts_root))
    else:
        config = AdapterConfig.from_env(default_root="artifacts/logs")

    try:
        report = run_demo_scenario(config=config)
    except Exception as exc:
        print(f"[integration-adapter] demo scenario failed: {exc}", file=sys.stderr)
        return 1

    print("[integration-adapter] demo scenario completed")
    print(json.dumps(report, indent=2, sort_keys=True))

    if not report.get("dashboard_read_verification", {}).get("verified", False):
        print("[integration-adapter] dashboard read verification failed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
