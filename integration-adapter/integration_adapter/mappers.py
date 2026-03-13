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



def _is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _pick_value(raw: dict[str, Any], keys: list[str], *, payload: dict[str, Any] | None = None) -> tuple[str, str]:
    payload_map = payload or {}
    for key in keys:
        if key in raw and _is_present(raw.get(key)):
            return str(raw.get(key)), "sourced"
        if key in payload_map and _is_present(payload_map.get(key)):
            return str(payload_map.get(key)), "sourced"
    return "", "unavailable"


def _source_for_key(raw: dict[str, Any], key: str) -> str:
    if key in raw and _is_present(raw.get(key)):
        return "sourced"
    return "unavailable"


def map_runtime_event(raw: dict[str, Any]) -> NormalizedAuditEvent:
    """Map runtime event payload to normalized event vocabulary.

    Unconfirmed: canonical Onyx retrieval/tool/MCP event feed and field naming are not fully validated in this workspace.
    """

    payload = dict(raw.get("event_payload") or {})
    persona_or_agent_id, persona_source = _pick_value(
        raw,
        ["persona_or_agent_id", "persona_id", "agent_id"],
        payload=payload,
    )
    if not persona_or_agent_id:
        persona_or_agent_id = "unavailable"

    tool_invocation_id, tool_invocation_source = _pick_value(
        raw,
        ["tool_invocation_id", "tool_call_id"],
        payload=payload,
    )
    if not tool_invocation_id:
        tool_invocation_id = "unavailable"

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

    decision_basis, decision_source = _pick_value(
        raw,
        ["decision_basis", "reason"],
        payload=payload,
    )
    if not decision_basis:
        decision_basis = "unavailable"

    resource_scope, resource_scope_source = _pick_value(
        raw,
        ["resource_scope", "source_id", "tool_name", "mcp_server"],
        payload=payload,
    )
    if not resource_scope:
        resource_scope = "unavailable"

    authz_result, authz_source = _pick_value(
        raw,
        ["authz_result", "decision"],
        payload=payload,
    )
    if not authz_result and payload.get("allowed") is True:
        authz_result, authz_source = "allow", "derived"
    elif not authz_result and payload.get("allowed") is False:
        authz_result, authz_source = "deny", "derived"
    elif not authz_result:
        authz_result, authz_source = "unavailable", "unavailable"

    session_id, session_source = _pick_value(
        raw,
        ["session_id", "chat_session_id"],
        payload=payload,
    )
    if not session_id and _is_present(raw.get("trace_id")):
        session_id, session_source = str(raw.get("trace_id")), "derived"
    elif not session_id:
        session_id, session_source = "adapter-session", "derived"

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
            "actor_id": _source_for_key(raw, "actor_id") if raw.get("actor_id") else "derived",
            "tenant_id": _source_for_key(raw, "tenant_id") if raw.get("tenant_id") else "derived",
            "session_id": session_source,
            "persona_or_agent_id": persona_source,
            "tool_invocation_id": tool_invocation_source,
            "delegation_chain": delegation_chain_source,
            "decision_basis": decision_source,
            "resource_scope": resource_scope_source,
            "authz_result": authz_source,
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
