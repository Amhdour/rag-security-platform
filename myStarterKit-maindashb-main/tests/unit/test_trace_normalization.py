"""Tests for trace normalization into compact dashboard explanation models."""

from __future__ import annotations

import json
from pathlib import Path

from observability.trace_normalization import build_trace_explanations, load_replay_links, read_audit_jsonl


def test_read_audit_jsonl_skips_malformed_lines(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    audit_path.write_text(
        "\n".join(
            [
                json.dumps({"event_id": "evt-1", "trace_id": "trace-1", "event_type": "request.start"}),
                "{not-valid-json}",
                json.dumps(["not", "an", "object"]),
            ]
        )
    )

    events, malformed = read_audit_jsonl(audit_path)

    assert len(events) == 1
    assert malformed == 2


def test_build_trace_explanations_reconstructs_end_to_end_flow(tmp_path: Path) -> None:
    events = [
        {
            "event_id": "evt-1",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "request.start",
            "event_payload": {"channel": "web"},
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "event_id": "evt-2",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "policy.decision",
            "event_payload": {"action": "retrieval.search", "allow": True, "reason": "allowed by policy"},
            "created_at": "2026-01-01T00:00:02Z",
        },
        {
            "event_id": "evt-3",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "retrieval.decision",
            "event_payload": {"document_count": 2},
            "created_at": "2026-01-01T00:00:03Z",
        },
        {
            "event_id": "evt-4",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "policy.decision",
            "event_payload": {"action": "model.generate", "allow": True, "reason": "model allowed"},
            "created_at": "2026-01-01T00:00:04Z",
        },
        {
            "event_id": "evt-5",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "tool.decision",
            "event_payload": {"decisions": ["deny"], "reason": "confirmation missing", "token": "secret"},
            "created_at": "2026-01-01T00:00:05Z",
        },
        {
            "event_id": "evt-6",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "deny.event",
            "event_payload": {"stage": "tools.route", "reason": "forbidden"},
            "created_at": "2026-01-01T00:00:06Z",
        },
        {
            "event_id": "evt-7",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "request.end",
            "event_payload": {"status": "blocked"},
            "created_at": "2026-01-01T00:00:07Z",
        },
    ]

    replay_dir = tmp_path / "artifacts/logs/replay"
    replay_dir.mkdir(parents=True)
    replay_path = replay_dir / "trace-1.replay.json"
    replay_path.write_text(
        json.dumps(
            {
                "trace_id": "trace-1",
                "request_id": "req-1",
                "coverage": {"request_lifecycle_complete": True},
                "event_type_counts": {"request.start": 1, "deny.event": 1},
                "decision_summary": {"deny_events": [{"reason": "forbidden"}]},
            }
        )
    )

    explanations = build_trace_explanations(events, replay_links=load_replay_links(tmp_path))

    assert len(explanations) == 1
    item = explanations[0]
    assert item["ids"]["trace_id"] == "trace-1"
    assert item["ids"]["request_id"] == "req-1"
    assert item["actor"]["actor_id"] == "actor-1"
    assert item["actor"]["tenant_id"] == "tenant-a"
    assert item["final_outcome"] == "denied"
    assert item["final_disposition"] == "denied"
    assert item["partial_trace"] is False
    assert item["timeline"][0]["event_type"] == "request.start"
    assert item["timeline"][1]["event_category"] == "policy"
    assert item["timeline"][1]["decision_outcome"] == "allowed"
    assert item["timeline"][3]["stage"] == "model"
    assert item["timeline"][4]["decision_outcome"] == "denied"
    assert item["timeline"][5]["reason"] == "forbidden"
    assert any(check["event_type"] == "deny.event" for check in item["checks"])
    assert any(reason["reason"] == "forbidden" for reason in item["decision_reasons"])

    # Ensure secret-like token is still redacted in normalized payload output.
    tool_event = [evt for evt in item["timeline"] if evt["event_type"] == "tool.decision"][0]
    assert tool_event["payload"]["token"] == "[redacted]"

    assert item["replay"]["replay_path"].endswith("trace-1.replay.json")
    assert item["replay"]["coverage"]["request_lifecycle_complete"] is True


def test_partial_and_request_grouping_when_trace_id_missing() -> None:
    events = [
        {
            "event_id": "evt-a",
            "trace_id": "",
            "request_id": "req-only",
            "actor_id": "actor-a",
            "tenant_id": "tenant-a",
            "event_type": "request.start",
            "event_payload": {},
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "event_id": "evt-b",
            "trace_id": "",
            "request_id": "req-only",
            "actor_id": "actor-a",
            "tenant_id": "tenant-a",
            "event_type": "fallback.event",
            "event_payload": {"reason": "tools disabled"},
            "created_at": "2026-01-01T00:00:02Z",
        },
    ]

    explanations = build_trace_explanations(events)

    assert len(explanations) == 1
    item = explanations[0]
    assert item["ids"]["request_id"] == "req-only"
    assert item["ids"]["trace_id"] == ""
    assert item["final_outcome"] == "fallback"
    assert item["partial_trace"] is True


def test_incomplete_trace_without_terminal_events_is_safe() -> None:
    events = [
        {
            "event_id": "evt-z",
            "trace_id": "trace-z",
            "request_id": "req-z",
            "actor_id": "actor-z",
            "tenant_id": "tenant-z",
            "event_type": "policy.decision",
            "event_payload": {"action": "retrieval.search", "allow": False, "reason": "not allowed"},
            "created_at": "2026-01-01T00:00:10Z",
        }
    ]

    explanations = build_trace_explanations(events)

    assert len(explanations) == 1
    item = explanations[0]
    assert item["final_disposition"] == "in_progress"
    assert item["partial_trace"] is True
    assert item["timeline"][0]["decision_outcome"] == "denied"


def test_trace_explanations_include_stage_groups_and_disposition_summary() -> None:
    events = [
        {
            "event_id": "evt-1",
            "trace_id": "trace-success",
            "request_id": "req-success",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "request.start",
            "event_payload": {},
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "event_id": "evt-2",
            "trace_id": "trace-success",
            "request_id": "req-success",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "policy.decision",
            "event_payload": {"action": "retrieval.search", "allow": True, "reason": "tenant source allowlist matched"},
            "created_at": "2026-01-01T00:00:02Z",
        },
        {
            "event_id": "evt-3",
            "trace_id": "trace-success",
            "request_id": "req-success",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "retrieval.decision",
            "event_payload": {"document_count": 3, "top_k": 3, "allowed_source_ids": ["kb-a"]},
            "created_at": "2026-01-01T00:00:03Z",
        },
        {
            "event_id": "evt-4",
            "trace_id": "trace-success",
            "request_id": "req-success",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "request.end",
            "event_payload": {"status": "ok"},
            "created_at": "2026-01-01T00:00:04Z",
        },
    ]

    item = build_trace_explanations(events)[0]
    assert item["final_disposition"] == "completed"
    assert item["final_disposition_summary"].startswith("Request completed")
    assert "policy" in item["stage_groups"]
    assert "retrieval" in item["stage_groups"]
    assert item["evidence_used"]
    assert item["raw_event_inspector"][0]["event_type"] == "request.start"


def test_trace_explanations_include_error_and_fallback_summaries() -> None:
    fallback = [
        {
            "event_id": "evt-f1",
            "trace_id": "trace-f",
            "request_id": "req-f",
            "actor_id": "actor-f",
            "tenant_id": "tenant-f",
            "event_type": "request.start",
            "event_payload": {},
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "event_id": "evt-f2",
            "trace_id": "trace-f",
            "request_id": "req-f",
            "actor_id": "actor-f",
            "tenant_id": "tenant-f",
            "event_type": "fallback.event",
            "event_payload": {"mode": "rag_only", "reason": "policy allowed_tools is empty"},
            "created_at": "2026-01-01T00:00:02Z",
        },
        {
            "event_id": "evt-f3",
            "trace_id": "trace-f",
            "request_id": "req-f",
            "actor_id": "actor-f",
            "tenant_id": "tenant-f",
            "event_type": "request.end",
            "event_payload": {"status": "ok"},
            "created_at": "2026-01-01T00:00:03Z",
        },
    ]
    error = [
        {
            "event_id": "evt-e1",
            "trace_id": "trace-e",
            "request_id": "req-e",
            "actor_id": "actor-e",
            "tenant_id": "tenant-e",
            "event_type": "request.start",
            "event_payload": {},
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "event_id": "evt-e2",
            "trace_id": "trace-e",
            "request_id": "req-e",
            "actor_id": "actor-e",
            "tenant_id": "tenant-e",
            "event_type": "error.event",
            "event_payload": {"message": "network failed"},
            "created_at": "2026-01-01T00:00:02Z",
        },
    ]

    fallback_item = build_trace_explanations(fallback)[0]
    error_item = build_trace_explanations(error)[0]

    assert fallback_item["final_disposition"] == "fallback"
    assert "fallback mode" in fallback_item["final_disposition_summary"]
    assert error_item["final_disposition"] == "error"
    assert "failed closed" in error_item["final_disposition_summary"]
