from __future__ import annotations

from integration_adapter.mappers import map_runtime_event


def test_identity_authz_fields_map_from_raw_and_payload() -> None:
    event = map_runtime_event(
        {
            "request_id": "req-1",
            "trace_id": "trace-1",
            "event_type": "tool.decision",
            "actor_id": "user-1",
            "tenant_id": "tenant-a",
            "session_id": "sess-1",
            "persona_or_agent_id": "agent-7",
            "tool_invocation_id": "call-9",
            "delegation_chain": ["manager", "assistant"],
            "decision_basis": "policy_bundle.default",
            "resource_scope": "tool:ticket_lookup",
            "authz_result": "allow",
            "event_payload": {"decision": "allow"},
        }
    )

    payload = event.to_dict()
    assert payload["session_id"] == "sess-1"
    assert payload["persona_or_agent_id"] == "agent-7"
    assert payload["tool_invocation_id"] == "call-9"
    assert payload["delegation_chain"] == ["manager", "assistant"]
    assert payload["decision_basis"] == "policy_bundle.default"
    assert payload["resource_scope"] == "tool:ticket_lookup"
    assert payload["authz_result"] == "allow"
    assert payload["identity_authz_field_sources"]["persona_or_agent_id"] == "sourced"
    assert payload["identity_authz_field_sources"]["tool_invocation_id"] == "sourced"
    assert payload["identity_authz_field_sources"]["decision_basis"] == "sourced"
    assert payload["identity_authz_field_sources"]["resource_scope"] == "sourced"
    assert payload["identity_authz_field_sources"]["authz_result"] == "sourced"


def test_identity_authz_fields_derived_or_unavailable_when_missing() -> None:
    event = map_runtime_event(
        {
            "event_type": "retrieval.decision",
            "request_id": "req-2",
            "trace_id": "trace-2",
            "actor_id": "retrieval",
            "tenant_id": "tenant-b",
            "event_payload": {"source_id": "con-1", "allowed": True},
        }
    )

    payload = event.to_dict()
    assert payload["session_id"] == "trace-2"
    assert payload["persona_or_agent_id"] == "unavailable"
    assert payload["tool_invocation_id"] == "unavailable"
    assert payload["decision_basis"] == "unavailable"
    assert payload["resource_scope"] == "con-1"
    assert payload["authz_result"] == "allow"
    assert payload["identity_authz_field_sources"]["session_id"] == "derived"
    assert payload["identity_authz_field_sources"]["persona_or_agent_id"] == "unavailable"
    assert payload["identity_authz_field_sources"]["tool_invocation_id"] == "unavailable"
    assert payload["identity_authz_field_sources"]["decision_basis"] == "unavailable"
    assert payload["identity_authz_field_sources"]["resource_scope"] == "sourced"
    assert payload["identity_authz_field_sources"]["authz_result"] == "derived"


def test_identity_mapping_uses_onyx_style_keys_when_available() -> None:
    event = map_runtime_event(
        {
            "event_type": "tool.execution_attempt",
            "request_id": "req-3",
            "trace_id": "trace-3",
            "actor_id": "tool-runtime",
            "tenant_id": "tenant-c",
            "chat_session_id": "chat-session-9",
            "persona_id": "persona-2",
            "tool_call_id": "tool-call-44",
            "event_payload": {
                "tool_name": "search",
                "decision": "deny",
                "delegated_by": "agent-router",
            },
        }
    )

    payload = event.to_dict()
    assert payload["session_id"] == "chat-session-9"
    assert payload["persona_or_agent_id"] == "persona-2"
    assert payload["tool_invocation_id"] == "tool-call-44"
    assert payload["delegation_chain"] == ["agent-router"]
    assert payload["resource_scope"] == "search"
    assert payload["authz_result"] == "deny"
    assert payload["identity_authz_field_sources"]["session_id"] == "sourced"
    assert payload["identity_authz_field_sources"]["persona_or_agent_id"] == "sourced"
    assert payload["identity_authz_field_sources"]["tool_invocation_id"] == "sourced"
    assert payload["identity_authz_field_sources"]["delegation_chain"] == "derived"
