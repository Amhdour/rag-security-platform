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


def _field_source(raw: dict[str, Any], key: str, value: str) -> str:
    if key in raw:
        raw_value = raw.get(key)
        if raw_value is not None and raw_value != "" and raw_value != [] and raw_value != {}:
            return "sourced"
    if value == "unavailable" or value == "":
        return "unavailable"
    return "derived"


def map_runtime_event(raw: dict[str, Any]) -> NormalizedAuditEvent:
    """Map runtime event payload to normalized event vocabulary.

    Unconfirmed: canonical Onyx retrieval/tool/MCP event feed and field naming are not fully validated in this workspace.
    """

    payload = dict(raw.get("event_payload") or {})
    persona_or_agent_id = str(
        raw.get("persona_or_agent_id")
        or payload.get("persona_or_agent_id")
        or raw.get("persona_id")
        or payload.get("persona_id")
        or raw.get("agent_id")
        or payload.get("agent_id")
        or "unavailable"
    )
    tool_invocation_id = str(
        raw.get("tool_invocation_id")
        or payload.get("tool_invocation_id")
        or raw.get("tool_call_id")
        or payload.get("tool_call_id")
        or "unavailable"
    )

    raw_chain = raw.get("delegation_chain")
    if isinstance(raw_chain, list):
        delegation_chain = [str(item) for item in raw_chain if str(item)]
        delegation_chain_source = "sourced"
    else:
        chain_payload = payload.get("delegation_chain")
        if isinstance(chain_payload, list):
            delegation_chain = [str(item) for item in chain_payload if str(item)]
            delegation_chain_source = "sourced"
        else:
            delegated_by = raw.get("delegated_by") or payload.get("delegated_by")
            delegation_chain = [str(delegated_by)] if delegated_by else []
            delegation_chain_source = "derived" if delegation_chain else "unavailable"

    decision_basis = str(raw.get("decision_basis") or payload.get("decision_basis") or payload.get("reason") or "unavailable")
    resource_scope = str(
        raw.get("resource_scope")
        or payload.get("resource_scope")
        or payload.get("source_id")
        or payload.get("tool_name")
        or "unavailable"
    )
    authz_result = str(
        raw.get("authz_result")
        or payload.get("authz_result")
        or payload.get("decision")
        or ("allow" if payload.get("allowed") is True else "deny" if payload.get("allowed") is False else "unavailable")
    )

    session_id = str(raw.get("session_id") or payload.get("session_id") or raw.get("trace_id") or "adapter-session")

    event = NormalizedAuditEvent(
        event_id=str(raw.get("event_id") or f"evt-{uuid4()}"),
        trace_id=str(raw.get("trace_id") or raw.get("request_id") or "unknown-trace"),
        request_id=str(raw.get("request_id") or "unknown-request"),
        event_type=str(raw.get("event_type") or "fallback.event"),
        actor_id=str(raw.get("actor_id") or "unknown-actor"),
        tenant_id=str(raw.get("tenant_id") or "unknown-tenant"),
        event_payload=payload,
        session_id=session_id,
        persona_or_agent_id=persona_or_agent_id,
        tool_invocation_id=tool_invocation_id,
        delegation_chain=delegation_chain,
        decision_basis=decision_basis,
        resource_scope=resource_scope,
        authz_result=authz_result,
        identity_authz_field_sources={
            "actor_id": _field_source(raw, "actor_id", str(raw.get("actor_id") or "")),
            "tenant_id": _field_source(raw, "tenant_id", str(raw.get("tenant_id") or "")),
            "session_id": _field_source(raw, "session_id", session_id),
            "persona_or_agent_id": _field_source(raw, "persona_or_agent_id", persona_or_agent_id),
            "tool_invocation_id": _field_source(raw, "tool_invocation_id", tool_invocation_id),
            "delegation_chain": delegation_chain_source,
            "decision_basis": _field_source(raw, "decision_basis", decision_basis),
            "resource_scope": _field_source(raw, "resource_scope", resource_scope),
            "authz_result": _field_source(raw, "authz_result", authz_result),
        },
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
            session_id=event.session_id,
            persona_or_agent_id=event.persona_or_agent_id,
            tool_invocation_id=event.tool_invocation_id,
            delegation_chain=event.delegation_chain,
            decision_basis=event.decision_basis,
            resource_scope=event.resource_scope,
            authz_result=event.authz_result,
            identity_authz_field_sources=event.identity_authz_field_sources,
        ).created_at
    return event
