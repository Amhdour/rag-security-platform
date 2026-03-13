from __future__ import annotations

"""Pipeline orchestration for adapter evidence flows.

Status labels used in this module:
- Implemented: artifact generation and launch-gate orchestration from normalized payloads.
- Partially Implemented: live collection depends on optional runtime hooks in exporters.
- Demo-only: deterministic fallback payloads when live runtime data is unavailable.
- Unconfirmed: production runtime hook parity is not asserted by this module.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from integration_adapter.artifact_output import ArtifactWriter
from integration_adapter.config import AdapterConfig
from integration_adapter.env_profiles import get_profile_policy, validate_profile_safeguards
from integration_adapter.exporters import (
    ConnectorInventoryExporter,
    EvalResultsExporter,
    MCPInventoryExporter,
    RuntimeEventsExporter,
    ToolInventoryExporter,
)
from integration_adapter.launch_gate_evaluator import LaunchGateEvaluation, LaunchGateEvaluator
from integration_adapter.mappers import (
    map_connector_inventory,
    map_eval_inventory,
    map_mcp_inventory,
    map_runtime_event,
    map_tool_inventory,
)
from integration_adapter.versioning import (
    ARTIFACT_BUNDLE_SCHEMA_VERSION,
    NORMALIZED_SCHEMA_VERSION,
    RAW_SOURCE_SCHEMA_VERSION,
    CompatibilityDecision,
    evaluate_compatibility,
    expected_versions_from_env,
)


@dataclass
class CollectedPayload:
    mode: str
    raw_source_schema_version: str
    exporter_diagnostics: dict[str, dict[str, Any]]
    connectors: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    mcp_servers: list[dict[str, Any]]
    evals: list[dict[str, Any]]
    runtime_events: list[dict[str, Any]]


@dataclass
class PipelineResult:
    mode: str
    profile: str
    artifacts_root: Path
    artifact_contract_path: Path
    adapter_health_path: Path
    audit_path: Path
    replay_paths: list[Path]
    eval_jsonl_path: Path
    eval_summary_path: Path
    launch_gate_path: Path
    integrity_manifest_path: Path
    compatibility_decisions: list[CompatibilityDecision]
INTEGRITY_REQUIRED_RELATIVE_PATHS = [
    "artifact_bundle.contract.json",
    "audit.jsonl",
    "connectors.inventory.json",
    "tools.inventory.json",
    "mcp_servers.inventory.json",
    "evals.inventory.json",
    "adapter_health/adapter_run_summary.json",
]



def _evaluate_contracts(*, source_schema_version: str) -> list[CompatibilityDecision]:
    expected = expected_versions_from_env()
    return [
        evaluate_compatibility(
            contract_name="source_schema",
            expected_version=expected["source_schema"],
            actual_version=source_schema_version,
        ),
        evaluate_compatibility(
            contract_name="normalized_schema",
            expected_version=expected["normalized_schema"],
            actual_version=NORMALIZED_SCHEMA_VERSION,
        ),
        evaluate_compatibility(
            contract_name="artifact_bundle_schema",
            expected_version=expected["artifact_bundle_schema"],
            actual_version=ARTIFACT_BUNDLE_SCHEMA_VERSION,
        ),
    ]


def _raise_on_blocked_compatibility(decisions: list[CompatibilityDecision]) -> None:
    blocked = [d for d in decisions if d.status == "blocked"]
    if blocked:
        details = "; ".join(
            f"{d.contract_name}: expected={d.expected_version}, actual={d.actual_version}, reason={d.reason}"
            for d in blocked
        )
        raise ValueError(f"schema compatibility blocked: {details}")


def _diag_from_exporter(name: str, exporter: Any) -> dict[str, Any]:
    acquisition = getattr(exporter, "last_acquisition", None)
    if acquisition is None:
        return {
            "exporter": name,
            "source_mode": "synthetic",
            "source_path": "",
            "fallback_used": False,
            "rows_count": 0,
            "warnings": ["exporter did not emit acquisition diagnostics"],
            "errors": [],
        }
    return {
        "exporter": name,
        "source_mode": acquisition.source_mode,
        "source_path": acquisition.source_path,
        "fallback_used": acquisition.used_fallback,
        "rows_count": len(acquisition.rows),
        "warnings": list(acquisition.warnings),
        "errors": list(acquisition.errors),
    }


def collect_from_onyx(*, force_demo: bool = False) -> CollectedPayload:
    """Collect exporter payloads from Onyx-facing sources.

    Partially Implemented: uses exporter live reads when available.
    Demo-only: if no live data is available (or force_demo=True), returns deterministic demo payloads.
    Unconfirmed: canonical production runtime hook parity is not validated in this workspace.
    """

    connectors_exporter = ConnectorInventoryExporter()
    tools_exporter = ToolInventoryExporter()
    mcp_exporter = MCPInventoryExporter()
    eval_exporter = EvalResultsExporter()
    events_exporter = RuntimeEventsExporter()

    connectors = connectors_exporter.export()
    tools = tools_exporter.export()
    mcp_servers = mcp_exporter.export()
    evals = eval_exporter.export()
    runtime_events = events_exporter.export()

    exporter_diagnostics = {
        "connectors": _diag_from_exporter("connectors", connectors_exporter),
        "tools": _diag_from_exporter("tools", tools_exporter),
        "mcp_servers": _diag_from_exporter("mcp_servers", mcp_exporter),
        "evals": _diag_from_exporter("evals", eval_exporter),
        "runtime_events": _diag_from_exporter("runtime_events", events_exporter),
    }

    has_live_data = any([connectors, tools, mcp_servers, evals, runtime_events])
    if force_demo or not has_live_data:
        mode = "demo"
        return CollectedPayload(
            mode=mode,
            raw_source_schema_version=RAW_SOURCE_SCHEMA_VERSION,
            exporter_diagnostics={
                key: {
                    **value,
                    "source_mode": "synthetic",
                    "source_path": "demo_payload",
                    "fallback_used": True,
                    "warnings": list(value.get("warnings", [])) + ["demo fallback payload used"],
                }
                for key, value in exporter_diagnostics.items()
            },
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
        raw_source_schema_version=RAW_SOURCE_SCHEMA_VERSION,
        exporter_diagnostics=exporter_diagnostics,
        connectors=connectors,
        tools=tools,
        mcp_servers=mcp_servers,
        evals=evals,
        runtime_events=runtime_events,
    )


def _build_health_summary(
    *,
    profile: str,
    payload: CollectedPayload,
    compatibility_decisions: list[CompatibilityDecision],
    artifact_write_failures: int,
    launch_gate_status: str | None,
    launch_gate_blockers: list[str],
    stale_evidence_detections: int,
) -> dict[str, Any]:
    source_mode_counts: dict[str, int] = defaultdict(int)
    fallback_usage_count = 0
    parse_failures = 0
    partial_extraction_warnings = 0
    for diag in payload.exporter_diagnostics.values():
        source_mode = str(diag.get("source_mode", "synthetic"))
        source_mode_counts[source_mode] += 1
        fallback_usage_count += 1 if bool(diag.get("fallback_used", False)) else 0
        parse_failures += sum(1 for item in diag.get("errors", []) if "malformed" in str(item) or "failed" in str(item))
        partial_extraction_warnings += len(diag.get("warnings", []))

    schema_validation_failures = 0
    if launch_gate_blockers:
        schema_validation_failures = sum(1 for reason in launch_gate_blockers if "schema" in reason)

    has_blocked = any(decision.status == "blocked" for decision in compatibility_decisions)
    has_warn = any(decision.status == "warn_only" for decision in compatibility_decisions)
    has_degradation = has_warn or fallback_usage_count > 0 or parse_failures > 0 or partial_extraction_warnings > 0 or stale_evidence_detections > 0

    if has_blocked or artifact_write_failures > 0:
        run_status = "failed_run"
    elif has_degradation or (launch_gate_status is not None and launch_gate_status != "go"):
        run_status = "degraded_success"
    else:
        run_status = "success"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": payload.mode,
        "profile": profile,
        "run_status": run_status,
        "metrics": {
            "selected_source_mode": {key: value.get("source_mode", "synthetic") for key, value in payload.exporter_diagnostics.items()},
            "source_mode_counts": dict(source_mode_counts),
            "fallback_usage_count": fallback_usage_count,
            "parse_failures": parse_failures,
            "schema_validation_failures": schema_validation_failures,
            "artifact_write_failures": artifact_write_failures,
            "launch_gate_failure_reasons": list(launch_gate_blockers),
            "launch_gate_failure_reasons_count": len(launch_gate_blockers),
            "stale_evidence_detections": stale_evidence_detections,
            "partial_extraction_warnings": partial_extraction_warnings,
        },
        "compatibility": [
            {
                "contract_name": item.contract_name,
                "status": item.status,
                "expected_version": item.expected_version,
                "actual_version": item.actual_version,
                "reason": item.reason,
            }
            for item in compatibility_decisions
        ],
        "exporters": payload.exporter_diagnostics,
        "launch_gate": {
            "status": launch_gate_status or "not_run",
            "blockers": launch_gate_blockers,
        },
    }


def _apply_profile_freshness_env(profile: str) -> None:
    policy = get_profile_policy(profile)
    os.environ.setdefault("INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS", str(policy.critical_freshness_seconds))
    os.environ.setdefault("INTEGRATION_ADAPTER_MAX_WARNING_EVIDENCE_AGE_SECONDS", str(policy.warning_freshness_seconds))


def _freshness_check_evidence(evaluation: LaunchGateEvaluation) -> dict[str, Any] | None:
    for check in evaluation.checks:
        if check.check_name == "evidence_freshness":
            return check.evidence
    return None


def generate_artifacts(*, force_demo: bool = False, config: AdapterConfig | None = None) -> PipelineResult:
    cfg = config or AdapterConfig.from_env(default_root="artifacts/logs")
    profile = cfg.profile.strip().lower()
    _apply_profile_freshness_env(profile)
    writer = ArtifactWriter(cfg)

    payload = collect_from_onyx(force_demo=force_demo)
    compatibility_decisions = _evaluate_contracts(source_schema_version=payload.raw_source_schema_version)
    _raise_on_blocked_compatibility(compatibility_decisions)

    artifact_write_failures = 0

    try:
        artifact_contract_path = writer.write_bundle_contract(source_schema_version=payload.raw_source_schema_version)
        connectors_path = writer.write_inventory_snapshot(domain="connectors", rows=map_connector_inventory(payload.connectors))
        tools_path = writer.write_inventory_snapshot(domain="tools", rows=map_tool_inventory(payload.tools))
        mcp_path = writer.write_inventory_snapshot(domain="mcp_servers", rows=map_mcp_inventory(payload.mcp_servers))
        eval_inventory_path = writer.write_inventory_snapshot(domain="evals", rows=map_eval_inventory(payload.evals))

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
    except Exception:
        artifact_write_failures += 1
        failed_summary = _build_health_summary(
            profile=profile,
            payload=payload,
            compatibility_decisions=compatibility_decisions,
            artifact_write_failures=artifact_write_failures,
            launch_gate_status="not_run",
            launch_gate_blockers=["artifact_write_failure"],
            stale_evidence_detections=0,
        )
        writer.write_adapter_health_summary(failed_summary)
        raise

    prelaunch_summary = _build_health_summary(
        profile=profile,
        payload=payload,
        compatibility_decisions=compatibility_decisions,
        artifact_write_failures=artifact_write_failures,
        launch_gate_status="not_run",
        launch_gate_blockers=[],
        stale_evidence_detections=0,
    )
    adapter_health_path = writer.write_adapter_health_summary(prelaunch_summary)

    evaluator = LaunchGateEvaluator(cfg.artifacts_root)
    evaluation = evaluator.evaluate()
    launch_gate_path, _ = evaluator.write_outputs(evaluation)

    freshness_evidence = _freshness_check_evidence(evaluation)
    profile_validation = validate_profile_safeguards(
        profile=profile,
        force_demo=force_demo,
        exporter_diagnostics=payload.exporter_diagnostics,
        launch_gate_freshness_evidence=freshness_evidence,
    )
    if profile_validation.blocked_reasons:
        raise ValueError("profile safeguards blocked run: " + "; ".join(profile_validation.blocked_reasons))

    stale_detections = 0
    for check in evaluation.checks:
        if check.check_name == "evidence_freshness":
            stale_detections = int((check.evidence or {}).get("stale_count", 0))

    final_summary = _build_health_summary(
        profile=profile,
        payload=payload,
        compatibility_decisions=compatibility_decisions,
        artifact_write_failures=artifact_write_failures,
        launch_gate_status=evaluation.status,
        launch_gate_blockers=evaluation.blockers,
        stale_evidence_detections=stale_detections,
    )
    adapter_health_path = writer.write_adapter_health_summary(final_summary)

    integrity_files: list[Path] = [
        artifact_contract_path,
        audit_path,
        connectors_path,
        tools_path,
        mcp_path,
        eval_inventory_path,
        eval_jsonl_path,
        eval_summary_path,
        adapter_health_path,
        launch_gate_path,
        *replay_paths,
    ]
    integrity_manifest_path = writer.write_integrity_manifest(file_paths=integrity_files)

    return PipelineResult(
        mode=payload.mode,
        profile=profile,
        artifacts_root=cfg.artifacts_root,
        artifact_contract_path=artifact_contract_path,
        adapter_health_path=adapter_health_path,
        audit_path=audit_path,
        replay_paths=replay_paths,
        eval_jsonl_path=eval_jsonl_path,
        eval_summary_path=eval_summary_path,
        launch_gate_path=launch_gate_path,
        integrity_manifest_path=integrity_manifest_path,
        compatibility_decisions=compatibility_decisions,
    )


def run_launch_gate(*, config: AdapterConfig | None = None) -> Path:
    """Evaluate artifacts and emit machine + human launch-gate summaries."""

    cfg = config or AdapterConfig.from_env(default_root="artifacts/logs")
    _apply_profile_freshness_env(cfg.profile)
    cfg.ensure_dirs()

    evaluator = LaunchGateEvaluator(cfg.artifacts_root)
    evaluation = evaluator.evaluate()
    json_path, _ = evaluator.write_outputs(evaluation)
    return json_path
