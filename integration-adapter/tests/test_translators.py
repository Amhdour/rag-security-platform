from integration_adapter.translators import (
    translate_eval_outputs,
    translate_mcp_usage,
    translate_retrieval_events,
    translate_tool_decisions,
)


def test_translate_retrieval_events_emits_retrieval_decision() -> None:
    events = translate_retrieval_events([
        {"request_id": "r1", "trace_id": "t1", "tenant_id": "ten", "actor_id": "retriever", "source_id": "con-1", "allowed": True}
    ])
    assert events[0].event_type == "retrieval.decision"
    assert events[0].event_payload["source_id"] == "con-1"
    assert events[0].resource_scope == "con-1"
    assert events[0].authz_result == "allow"


def test_translate_tool_decisions_emits_confirmation_when_required() -> None:
    events = translate_tool_decisions([
        {
            "request_id": "r1",
            "trace_id": "t1",
            "tenant_id": "ten",
            "tool_name": "admin_shell",
            "decision": "require_confirmation",
            "requires_confirmation": True,
        }
    ])
    assert [event.event_type for event in events] == ["tool.decision", "confirmation.required"]
    assert events[0].resource_scope == "admin_shell"
    assert events[0].authz_result == "require_confirmation"


def test_translate_mcp_usage_emits_tool_execution_attempt() -> None:
    events = translate_mcp_usage([
        {"request_id": "r1", "trace_id": "t1", "tenant_id": "ten", "mcp_server": "ops-mcp", "tool_name": "runbook", "decision": "allow"}
    ])
    assert events[0].event_type == "tool.execution_attempt"
    assert events[0].event_payload["mcp_server"] == "ops-mcp"
    assert events[0].resource_scope == "ops-mcp:runbook"


def test_translate_eval_outputs_returns_starterkit_rows() -> None:
    rows = translate_eval_outputs([
        {"run_id": "run-1", "scenario_id": "policy_bypass_attempt", "category": "policy_bypass", "severity": "critical", "passed": False}
    ])
    assert rows[0].outcome == "fail"
    assert rows[0].scenario_id == "policy_bypass_attempt"
