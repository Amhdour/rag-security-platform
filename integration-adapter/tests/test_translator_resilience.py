from integration_adapter.translators import (
    translate_eval_outputs,
    translate_retrieval_events,
    translate_tool_decisions,
)


def test_translate_retrieval_events_handles_malformed_top_k_without_crash() -> None:
    events = translate_retrieval_events(
        [
            {
                "request_id": "req-1",
                "trace_id": "trace-1",
                "tenant_id": "tenant-a",
                "top_k": "not-an-int",
                "allowed": "yes",
            }
        ]
    )
    payload = events[0].event_payload
    assert payload["top_k"] == 0
    assert payload["allow"] is True


def test_translate_tool_decisions_tolerates_missing_onyx_fields() -> None:
    events = translate_tool_decisions([{}])
    assert len(events) == 1
    event = events[0]
    assert event.request_id == "unknown-request"
    assert event.tenant_id == "unknown-tenant"
    assert event.event_payload["tool_name"] == "unknown_tool"


def test_translate_eval_outputs_accepts_string_passed_flags() -> None:
    rows = translate_eval_outputs([
        {"scenario_id": "s1", "category": "policy_bypass", "severity": "high", "passed": "true"},
        {"scenario_id": "s2", "category": "policy_bypass", "severity": "high", "passed": "false"},
    ])
    assert rows[0].outcome == "pass"
    assert rows[1].outcome == "fail"
