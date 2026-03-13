from integration_adapter.schemas import NormalizedAuditEvent


def test_schema_validation_accepts_required_vocabulary() -> None:
    event = NormalizedAuditEvent(
        event_id="evt-1",
        trace_id="trace-1",
        request_id="req-1",
        event_type="request.start",
        actor_id="actor-1",
        tenant_id="tenant-a",
        event_payload={"k": "v"},
    )
    payload = event.to_dict()
    assert payload["event_type"] == "request.start"


def test_schema_validation_rejects_unknown_event_type() -> None:
    event = NormalizedAuditEvent(
        event_id="evt-1",
        trace_id="trace-1",
        request_id="req-1",
        event_type="something.else",
        actor_id="actor-1",
        tenant_id="tenant-a",
        event_payload={},
    )
    try:
        event.to_dict()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unsupported event_type" in str(exc)


def test_schema_validation_accepts_error_event_and_audit_context() -> None:
    event = NormalizedAuditEvent(
        event_id="evt-err",
        trace_id="trace-err",
        request_id="req-err",
        event_type="error.event",
        actor_id="actor-err",
        tenant_id="tenant-a",
        event_payload={"message": "boom"},
    )
    payload = event.to_dict()
    assert payload["session_id"] == "adapter-session"
    assert payload["actor_type"] == "assistant_runtime"
    assert payload["persona_or_agent_id"] == "unavailable"
    assert payload["authz_result"] == "unavailable"


def test_schema_validation_rejects_non_list_delegation_chain() -> None:
    event = NormalizedAuditEvent(
        event_id="evt-x",
        trace_id="trace-x",
        request_id="req-x",
        event_type="request.start",
        actor_id="actor-x",
        tenant_id="tenant-x",
        delegation_chain="not-a-list",  # type: ignore[arg-type]
    )
    try:
        event.to_dict()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "delegation_chain" in str(exc)


def test_schema_validation_rejects_invalid_identity_source_value() -> None:
    event = NormalizedAuditEvent(
        event_id="evt-identity",
        trace_id="trace-identity",
        request_id="req-identity",
        event_type="request.start",
        actor_id="actor-identity",
        tenant_id="tenant-identity",
        identity_authz_field_sources={"actor_id": "invalid"},
    )
    try:
        event.to_dict()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "identity_authz_field_sources" in str(exc)
