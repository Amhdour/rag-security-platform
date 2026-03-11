from __future__ import annotations

import json
from pathlib import Path

from observability.service import DashboardService


def _seed(base: Path) -> None:
    (base / "artifacts/logs/evals").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/replay").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/launch_gate").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/verification").mkdir(parents=True, exist_ok=True)

    audit_rows = [
        {"event_id": "e1", "trace_id": "trace-1", "request_id": "req-1", "event_type": "request.start", "event_payload": {}, "created_at": "2026-01-01T00:00:01Z"},
        {"event_id": "e2", "trace_id": "trace-1", "request_id": "req-1", "event_type": "policy.decision", "event_payload": {"allow": True}, "created_at": "2026-01-01T00:00:02Z"},
        {"event_id": "e3", "trace_id": "trace-1", "request_id": "req-1", "event_type": "request.end", "event_payload": {"status": "ok"}, "created_at": "2026-01-01T00:00:03Z"},
        {"event_id": "e4", "trace_id": "trace-2", "request_id": "req-2", "event_type": "request.start", "event_payload": {}, "created_at": "2026-01-01T00:01:01Z"},
        {"event_id": "e5", "trace_id": "trace-3", "request_id": "req-3", "event_type": "request.start", "event_payload": {}, "created_at": "2026-01-01T00:02:01Z"},
        {"event_id": "e6", "trace_id": "trace-3", "request_id": "req-3", "event_type": "policy.decision", "event_payload": {"allow": True}, "created_at": "2026-01-01T00:02:02Z"},
        {"event_id": "e7", "trace_id": "trace-3", "request_id": "req-3", "event_type": "retrieval.decision", "event_payload": {"document_count": 1}, "created_at": "2026-01-01T00:02:03Z"},
        {"event_id": "e8", "trace_id": "trace-3", "request_id": "req-3", "event_type": "tool.decision", "event_payload": {"decisions": ["allow"]}, "created_at": "2026-01-01T00:02:04Z"},
        {"event_id": "e9", "trace_id": "trace-3", "request_id": "req-3", "event_type": "request.end", "event_payload": {"status": "ok"}, "created_at": "2026-01-01T00:02:05Z"},
    ]
    (base / "artifacts/logs/audit.jsonl").write_text("\n".join(json.dumps(r) for r in audit_rows))

    (base / "artifacts/logs/replay/trace-1.replay.json").write_text(json.dumps({"trace_id": "trace-1", "request_id": "req-1", "timeline": []}))

    run_id = "security-redteam-20260101T000000Z"
    (base / f"artifacts/logs/evals/{run_id}.summary.json").write_text(json.dumps({"suite_name": "security-redteam", "passed": True, "total": 2, "passed_count": 2}))
    rows = [
        {
            "scenario_id": "exact-for-trace-1",
            "title": "exact link",
            "severity": "low",
            "passed": True,
            "evidence": {"trace_id": "trace-1", "request_id": "req-1", "event_types": ["request.start", "policy.decision", "request.end"]},
        },
        {
            "scenario_id": "inferred-for-trace-3",
            "title": "inferred link",
            "severity": "medium",
            "passed": True,
            "evidence": {"event_types": ["request.start", "policy.decision", "retrieval.decision", "tool.decision", "request.end"]},
        },
    ]
    (base / f"artifacts/logs/evals/{run_id}.jsonl").write_text("\n".join(json.dumps(r) for r in rows))

    (base / "artifacts/logs/verification/security.summary.json").write_text(json.dumps({"status": "pass", "summary": "verified"}))
    (base / "artifacts/logs/launch_gate/security-readiness-20260101T000000Z.json").write_text(
        json.dumps(
            {
                "status": "conditional_go",
                "summary": "status=conditional_go",
                "checks": [{"check_name": "policy_artifact", "passed": True}],
                "scorecard": [{"category_name": "policy_artifacts", "status": "pass"}],
            }
        )
    )


def test_cross_links_exact_and_none_and_inferred(tmp_path: Path) -> None:
    _seed(tmp_path)
    service = DashboardService(tmp_path)

    trace1 = service.get_trace("trace-1")
    assert trace1 is not None
    assert trace1["cross_links"]["replay"]["correlation"] == "exact"
    assert trace1["cross_links"]["eval"]["correlation"] == "exact"

    trace2 = service.get_trace("trace-2")
    assert trace2 is not None
    assert trace2["cross_links"]["replay"]["correlation"] == "none"
    assert trace2["cross_links"]["eval"]["correlation"] in {"none", "inferred"}

    trace3 = service.get_trace("trace-3")
    assert trace3 is not None
    assert trace3["cross_links"]["eval"]["correlation"] == "inferred"
    assert trace3["cross_links"]["eval"]["inferred"] is True


def test_launch_gate_related_links_and_overview_connected_summary(tmp_path: Path) -> None:
    _seed(tmp_path)
    service = DashboardService(tmp_path)

    launch = service.get_latest_launch_gate()
    assert launch is not None
    assert launch["related_links"]["correlation"] == "exact"
    assert "policy_artifact" in launch["related_links"]["control_areas"]
    assert "policy_artifacts" in launch["related_links"]["eval_categories"]

    overview = service.get_overview()
    connected = overview.get("connected_evidence_summary", {})
    assert connected.get("traces_with_replay_exact", 0) >= 1
    assert connected.get("traces_with_eval_exact", 0) >= 1
    assert connected.get("traces_with_eval_inferred", 0) >= 1
