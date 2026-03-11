from __future__ import annotations

from typing import Any

from integration_adapter.mappers import (
    map_connector_inventory,
    map_eval_inventory,
    map_mcp_inventory,
    map_runtime_event,
    map_tool_inventory,
)
from integration_adapter.schemas import (
    InventoryRecord,
    NormalizedAuditEvent,
    OnyxEvalResultRecord,
    OnyxMCPUsageRecord,
    OnyxRetrievalRecord,
    OnyxToolDecisionRecord,
    StarterKitEvalRow,
)

def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def translate_connectors(payload: list[dict[str, Any]]) -> list[InventoryRecord]:
    """Translate Onyx connectors/indexed sources into starter-kit inventory rows.

    TODO(onyx-runtime-hook): confirm canonical Onyx connector inventory endpoint/query,
    including tenant-scoped index status and sync state fields.
    """

    return map_connector_inventory(payload)


def translate_retrieval_events(payload: list[dict[str, Any]]) -> list[NormalizedAuditEvent]:
    """Translate retrieval decisions into normalized audit events."""

    events: list[NormalizedAuditEvent] = []
    for row in payload:
        record = OnyxRetrievalRecord(
            request_id=str(row.get("request_id", "unknown-request")),
            trace_id=str(row.get("trace_id", row.get("request_id", "unknown-trace"))),
            tenant_id=str(row.get("tenant_id", "unknown-tenant")),
            actor_id=str(row.get("actor_id", "retrieval")),
            source_id=str(row.get("source_id", row.get("source", "unknown_source"))),
            query=str(row.get("query", "")),
            allowed=_safe_bool(row.get("allowed", True), default=True),
            reason=str(row.get("reason", "")),
            top_k=_safe_int(row.get("top_k", 0), default=0),
        )
        events.append(
            map_runtime_event(
                {
                    "request_id": record.request_id,
                    "trace_id": record.trace_id,
                    "tenant_id": record.tenant_id,
                    "actor_id": record.actor_id,
                    "event_type": "retrieval.decision",
                    "event_payload": {
                        "source_id": record.source_id,
                        "query": record.query,
                        "allow": record.allowed,
                        "reason": record.reason,
                        "top_k": record.top_k,
                    },
                }
            )
        )
    return events


def translate_tool_inventory(payload: list[dict[str, Any]]) -> list[InventoryRecord]:
    """Translate Onyx tools into starter-kit inventory rows."""

    return map_tool_inventory(payload)


def translate_tool_decisions(payload: list[dict[str, Any]]) -> list[NormalizedAuditEvent]:
    """Translate tool decisions into normalized audit events."""

    events: list[NormalizedAuditEvent] = []
    for row in payload:
        record = OnyxToolDecisionRecord(
            request_id=str(row.get("request_id", "unknown-request")),
            trace_id=str(row.get("trace_id", row.get("request_id", "unknown-trace"))),
            tenant_id=str(row.get("tenant_id", "unknown-tenant")),
            actor_id=str(row.get("actor_id", "tool-router")),
            tool_name=str(row.get("tool_name", row.get("tool", "unknown_tool"))),
            decision=str(row.get("decision", "deny")),
            reason=str(row.get("reason", "")),
            requires_confirmation=_safe_bool(row.get("requires_confirmation", False), default=False),
        )

        events.append(
            map_runtime_event(
                {
                    "request_id": record.request_id,
                    "trace_id": record.trace_id,
                    "tenant_id": record.tenant_id,
                    "actor_id": record.actor_id,
                    "event_type": "tool.decision",
                    "event_payload": {
                        "tool_name": record.tool_name,
                        "decision": record.decision,
                        "reason": record.reason,
                    },
                }
            )
        )

        if record.requires_confirmation:
            events.append(
                map_runtime_event(
                    {
                        "request_id": record.request_id,
                        "trace_id": record.trace_id,
                        "tenant_id": record.tenant_id,
                        "actor_id": record.actor_id,
                        "event_type": "confirmation.required",
                        "event_payload": {
                            "tool_name": record.tool_name,
                            "reason": record.reason or "confirmation required",
                        },
                    }
                )
            )
    return events


def translate_mcp_inventory(payload: list[dict[str, Any]]) -> list[InventoryRecord]:
    """Translate MCP server inventory into starter-kit inventory rows.

    TODO(onyx-runtime-hook): confirm canonical Onyx MCP inventory source and field names
    for auth mode, connection state, and server tool discovery metadata.
    """

    return map_mcp_inventory(payload)


def translate_mcp_usage(payload: list[dict[str, Any]]) -> list[NormalizedAuditEvent]:
    """Translate MCP usage into tool execution attempt events.

    TODO(onyx-runtime-hook): confirm canonical Onyx MCP usage feed and the source of
    runtime decision status for allow/deny/fallback semantics.
    """

    events: list[NormalizedAuditEvent] = []
    for row in payload:
        record = OnyxMCPUsageRecord(
            request_id=str(row.get("request_id", "unknown-request")),
            trace_id=str(row.get("trace_id", row.get("request_id", "unknown-trace"))),
            tenant_id=str(row.get("tenant_id", "unknown-tenant")),
            actor_id=str(row.get("actor_id", "mcp-runtime")),
            mcp_server=str(row.get("mcp_server", "unknown_mcp_server")),
            tool_name=str(row.get("tool_name", row.get("tool", "unknown_tool"))),
            decision=str(row.get("decision", "unknown")),
            reason=str(row.get("reason", "")),
        )
        events.append(
            map_runtime_event(
                {
                    "request_id": record.request_id,
                    "trace_id": record.trace_id,
                    "tenant_id": record.tenant_id,
                    "actor_id": record.actor_id,
                    "event_type": "tool.execution_attempt",
                    "event_payload": {
                        "mcp_server": record.mcp_server,
                        "tool_name": record.tool_name,
                        "decision": record.decision,
                        "reason": record.reason,
                    },
                }
            )
        )
    return events


def translate_eval_outputs(payload: list[dict[str, Any]]) -> list[StarterKitEvalRow]:
    """Translate Onyx eval outputs to starter-kit eval JSONL row shape.

    TODO(onyx-runtime-hook): confirm canonical Onyx eval result format across local/remote
    eval providers and mapping for severity/category labels.
    """

    rows: list[StarterKitEvalRow] = []
    for row in payload:
        record = OnyxEvalResultRecord(
            run_id=str(row.get("run_id", "unknown-run")),
            scenario_id=str(row.get("scenario_id", row.get("id", "unknown-scenario"))),
            category=str(row.get("category", "other")),
            severity=str(row.get("severity", "medium")),
            passed=_safe_bool(row.get("passed", row.get("outcome") == "pass"), default=False),
            details=str(row.get("details", "")),
        )
        rows.append(
            StarterKitEvalRow(
                scenario_id=record.scenario_id,
                category=record.category,
                severity=record.severity,
                outcome="pass" if record.passed else "fail",
                passed=record.passed,
                details=record.details,
            )
        )
    return rows


def translate_eval_inventory(payload: list[dict[str, Any]]) -> list[InventoryRecord]:
    """Translate eval run metadata into inventory records."""

    return map_eval_inventory(payload)


def translate_request_lifecycle_events(payload: list[dict[str, Any]]) -> list[NormalizedAuditEvent]:
    """Translate lifecycle/policy/fallback/deny events with pass-through defaults."""

    return [map_runtime_event(row) for row in payload]
