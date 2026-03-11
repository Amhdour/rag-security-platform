from __future__ import annotations

from typing import Any
from uuid import uuid4

from integration_adapter.schemas import InventoryRecord, NormalizedAuditEvent


def map_connector_inventory(rows: list[dict[str, Any]]) -> list[InventoryRecord]:
    return [
        InventoryRecord(
            domain="connectors",
            record_id=str(row.get("id", f"connector-{idx}")),
            name=str(row.get("name", "unknown_connector")),
            status=str(row.get("status", "unknown")),
            metadata={"source_type": row.get("source_type", "unknown"), "indexed": bool(row.get("indexed", False))},
        )
        for idx, row in enumerate(rows)
    ]


def map_tool_inventory(rows: list[dict[str, Any]]) -> list[InventoryRecord]:
    return [
        InventoryRecord(
            domain="tools",
            record_id=str(row.get("id", f"tool-{idx}")),
            name=str(row.get("name", "unknown_tool")),
            status=str(row.get("status", "unknown")),
            metadata={"risk_tier": row.get("risk_tier", "unspecified"), "enabled": bool(row.get("enabled", False))},
        )
        for idx, row in enumerate(rows)
    ]


def map_mcp_inventory(rows: list[dict[str, Any]]) -> list[InventoryRecord]:
    return [
        InventoryRecord(
            domain="mcp_servers",
            record_id=str(row.get("id", f"mcp-{idx}")),
            name=str(row.get("name", "unknown_mcp_server")),
            status=str(row.get("status", "unknown")),
            metadata={"endpoint": row.get("endpoint", ""), "usage_count": int(row.get("usage_count", 0))},
        )
        for idx, row in enumerate(rows)
    ]


def map_eval_inventory(rows: list[dict[str, Any]]) -> list[InventoryRecord]:
    return [
        InventoryRecord(
            domain="evals",
            record_id=str(row.get("id", f"eval-{idx}")),
            name=str(row.get("suite", "unknown_suite")),
            status="pass" if bool(row.get("passed", False)) else "fail",
            metadata={"score": row.get("score", 0), "scenario": row.get("scenario", "unspecified")},
        )
        for idx, row in enumerate(rows)
    ]


def map_runtime_event(raw: dict[str, Any]) -> NormalizedAuditEvent:
    """Map runtime event payload to normalized event vocabulary.

    TODO(onyx-runtime-hook): confirm canonical Onyx retrieval/tool/MCP event feed and field naming.
    """

    event = NormalizedAuditEvent(
        event_id=str(raw.get("event_id") or f"evt-{uuid4()}"),
        trace_id=str(raw.get("trace_id") or raw.get("request_id") or "unknown-trace"),
        request_id=str(raw.get("request_id") or "unknown-request"),
        event_type=str(raw.get("event_type") or "fallback.event"),
        actor_id=str(raw.get("actor_id") or "unknown-actor"),
        tenant_id=str(raw.get("tenant_id") or "unknown-tenant"),
        event_payload=dict(raw.get("event_payload") or {}),
        created_at=str(raw.get("created_at") or ""),
    )
    if not event.created_at:
        event.created_at = NormalizedAuditEvent(
            event_id=event.event_id,
            trace_id=event.trace_id,
            request_id=event.request_id,
            event_type=event.event_type,
            actor_id=event.actor_id,
            tenant_id=event.tenant_id,
            event_payload=event.event_payload,
        ).created_at
    return event
