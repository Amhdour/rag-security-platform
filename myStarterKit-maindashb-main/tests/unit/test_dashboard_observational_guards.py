"""Guard tests ensuring dashboard remains observational and non-enforcement."""

from __future__ import annotations

import json
import hashlib
import threading
import urllib.error
import urllib.request
from pathlib import Path

from evals.runner import SecurityEvalRunner
from evals.runtime import build_runtime_fixture, make_invocation, make_request
from launch_gate.engine import SecurityLaunchGate
from observability.api import create_server
from observability.service import DashboardService


def _seed_minimal_dashboard_artifacts(base: Path) -> None:
    (base / "artifacts/logs/evals").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/replay").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/launch_gate").mkdir(parents=True, exist_ok=True)
    (base / "observability/web/static").mkdir(parents=True, exist_ok=True)

    audit_rows = [
        {
            "event_id": "evt-1",
            "trace_id": "trace-ok",
            "request_id": "req-ok",
            "actor_id": "actor-a",
            "tenant_id": "tenant-a",
            "event_type": "request.start",
            "event_payload": {},
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "event_id": "evt-2",
            "trace_id": "trace-ok",
            "request_id": "req-ok",
            "actor_id": "actor-a",
            "tenant_id": "tenant-a",
            "event_type": "request.end",
            "event_payload": {"status": "ok"},
            "created_at": "2026-01-01T00:00:02Z",
        },
        {
            "event_id": "evt-3",
            "trace_id": "trace-deny",
            "request_id": "req-deny",
            "actor_id": "actor-b",
            "tenant_id": "tenant-b",
            "event_type": "deny.event",
            "event_payload": {"stage": "retrieval", "reason": "tenant mismatch"},
            "created_at": "2026-01-01T00:00:03Z",
        },
        {
            "event_id": "evt-4",
            "trace_id": "trace-fallback",
            "request_id": "req-fallback",
            "actor_id": "actor-c",
            "tenant_id": "tenant-a",
            "event_type": "fallback.event",
            "event_payload": {"mode": "rag_only", "reason": "tools disabled"},
            "created_at": "2026-01-01T00:00:04Z",
        },
        {
            "event_id": "evt-5",
            "trace_id": "trace-error",
            "request_id": "req-error",
            "actor_id": "actor-d",
            "tenant_id": "tenant-a",
            "event_type": "error.event",
            "event_payload": {"reason": "unexpected"},
            "created_at": "2026-01-01T00:00:05Z",
        },
        {
            "event_id": "evt-6",
            "trace_id": "",
            "request_id": "req-partial",
            "actor_id": "actor-e",
            "tenant_id": "tenant-a",
            "event_type": "request.start",
            "event_payload": {},
            "created_at": "2026-01-01T00:00:06Z",
        },
    ]
    (base / "artifacts/logs/audit.jsonl").write_text("\n".join(json.dumps(item) for item in audit_rows))

    (base / "artifacts/logs/replay/demo.replay.json").write_text(
        json.dumps({"trace_id": "trace-ok", "request_id": "req-ok", "timeline": []})
    )
    run_id = "security-redteam-20260101T000000Z"
    (base / f"artifacts/logs/evals/{run_id}.summary.json").write_text(
        json.dumps({"suite_name": "security-redteam", "passed": True, "total": 1, "passed_count": 1})
    )
    (base / f"artifacts/logs/evals/{run_id}.jsonl").write_text(
        json.dumps(
            {
                "scenario_id": "prompt_injection_direct",
                "title": "Direct prompt injection attempt",
                "severity": "high",
                "passed": True,
                "details": "ok",
            }
        )
    )
    (base / "artifacts/logs/launch_gate/security-readiness-20260101T000000Z.json").write_text(
        json.dumps(
            {
                "status": "conditional_go",
                "summary": "status=conditional_go",
                "blockers": [],
                "residual_risks": ["demo only"],
                "checks": [{"check_name": "policy_artifact", "status": "pass", "passed": True, "details": "ok"}],
            }
        )
    )

    (base / "observability/web/index.html").write_text("<html><body>dashboard</body></html>")
    (base / "observability/web/static/app.js").write_text("console.log('ok')")
    (base / "observability/web/static/styles.css").write_text("body{}")


def test_dashboard_endpoints_are_read_only_and_non_execution_path(tmp_path: Path, monkeypatch) -> None:
    _seed_minimal_dashboard_artifacts(tmp_path)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("dashboard must not execute tool or policy runtime paths")

    # If dashboard accidentally enters enforcement path, this test fails immediately.
    monkeypatch.setattr("tools.registry.InMemoryToolRegistry.execute", _forbidden)
    monkeypatch.setattr("policies.engine.RuntimePolicyEngine.evaluate", _forbidden)

    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for path in (
            "/api/traces",
            "/api/traces/trace-ok",
            "/api/replay",
            "/api/evals",
            "/api/evals/security-redteam-20260101T000000Z",
            "/api/launch-gate/latest",
            "/api/system-map",
        ):
            with urllib.request.urlopen(f"http://{host}:{port}{path}") as response:  # noqa: S310
                assert response.status == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_dashboard_handles_malformed_and_partial_data_safely(tmp_path: Path) -> None:
    _seed_minimal_dashboard_artifacts(tmp_path)
    # Corrupt eval summary and launch-gate to ensure fail-safe parsing.
    (tmp_path / "artifacts/logs/evals/security-redteam-20260101T000000Z.summary.json").write_text("{bad-json")
    (tmp_path / "artifacts/logs/launch_gate/security-readiness-20260101T000000Z.json").write_text("{bad-json")

    service = DashboardService(tmp_path)

    traces = service.list_traces()
    assert any(item["final_outcome"] == "denied" for item in traces)
    assert any(item["final_outcome"] == "fallback" for item in traces)
    assert any(item["final_outcome"] == "error" for item in traces)
    # partial request-id grouped trace should not crash
    assert any(item["request_id"] == "req-partial" for item in traces)

    assert service.list_eval_runs() == []
    assert service.get_latest_launch_gate() is None


def test_runtime_controls_and_evidence_pipelines_still_work_with_dashboard_imports(tmp_path: Path) -> None:
    # Orchestrator + retrieval + policy + tools + telemetry behavior still operational.
    fixture = build_runtime_fixture()
    response = fixture.orchestrator.run(
        make_request(request_id="obs-guard-ok", tenant_id="tenant-a", user_text="help with password reset")
    )
    assert response.status in {"ok", "blocked"}
    assert fixture.audit_sink.events

    # Tool-router enforcement still applies.
    deny_decision = fixture.tool_router.route(
        make_invocation(
            request_id="obs-guard-tool",
            tenant_id="tenant-a",
            tool_name="admin_shell",
            action="exec",
            arguments={"command": "whoami"},
        )
    )
    assert deny_decision.status == "deny"

    # Eval and launch-gate still produce/consume artifacts as before.
    eval_result = SecurityEvalRunner(suite_name="obs-guard").run(
        "evals/scenarios/security_baseline.json",
        output_dir=tmp_path / "evals",
        stamp="20260101T000000Z",
    )
    assert eval_result.scenario_results

    report = SecurityLaunchGate(repo_root=Path(".")).evaluate()
    assert report.checks


def test_dashboard_mutating_endpoints_remain_blocked(tmp_path: Path) -> None:
    _seed_minimal_dashboard_artifacts(tmp_path)
    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            request = urllib.request.Request(f"http://{host}:{port}/api/traces", method=method)
            try:
                urllib.request.urlopen(request)  # noqa: S310
                assert False, f"expected HTTP 405 for {method}"
            except urllib.error.HTTPError as exc:
                assert exc.code == 405
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_dashboard_reads_do_not_modify_policy_artifact() -> None:
    policy_path = Path("policies/bundles/default/policy.json")
    before = hashlib.sha256(policy_path.read_bytes()).hexdigest()

    service = DashboardService(Path("."))
    _ = service.get_overview()
    _ = service.list_traces()
    _ = service.list_eval_runs()
    _ = service.get_latest_launch_gate()

    after = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    assert before == after


def test_dashboard_trace_detail_preserves_redaction_and_terminal_flows(tmp_path: Path) -> None:
    _seed_minimal_dashboard_artifacts(tmp_path)
    # add secret-like field to verify redaction preservation
    with (tmp_path / "artifacts/logs/audit.jsonl").open("a") as handle:
        handle.write("\n" + json.dumps({
            "event_id": "evt-7",
            "trace_id": "trace-ok",
            "request_id": "req-ok",
            "actor_id": "actor-a",
            "tenant_id": "tenant-a",
            "event_type": "tool.decision",
            "event_payload": {"token": "raw-secret"},
            "created_at": "2026-01-01T00:00:02.500Z",
        }))

    service = DashboardService(tmp_path)

    trace_ok = service.get_trace("trace-ok")
    assert trace_ok is not None
    token_events = [item for item in trace_ok["timeline"] if item.get("event_type") == "tool.decision"]
    assert token_events
    assert token_events[0]["payload"].get("token") == "[redacted]"

    deny_trace = service.get_trace("trace-deny")
    fallback_trace = service.get_trace("trace-fallback")
    error_trace = service.get_trace("trace-error")
    assert deny_trace is not None and deny_trace["explanation"]["final_disposition"] == "denied"
    assert fallback_trace is not None and fallback_trace["explanation"]["final_disposition"] == "fallback"
    assert error_trace is not None and error_trace["explanation"]["final_disposition"] == "error"


def test_dashboard_observability_calls_do_not_invoke_tool_execution(monkeypatch, tmp_path: Path) -> None:
    _seed_minimal_dashboard_artifacts(tmp_path)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("tool execution must not run in dashboard read paths")

    monkeypatch.setattr("tools.registry.InMemoryToolRegistry.execute", _forbidden)

    service = DashboardService(tmp_path)
    _ = service.get_overview()
    _ = service.list_traces()
    _ = service.list_replay_artifacts()
    _ = service.list_eval_runs()



def test_dashboard_reads_do_not_modify_runtime_artifacts(tmp_path: Path) -> None:
    _seed_minimal_dashboard_artifacts(tmp_path)
    service = DashboardService(tmp_path)

    tracked = [
        tmp_path / "artifacts/logs/audit.jsonl",
        tmp_path / "artifacts/logs/replay/demo.replay.json",
        tmp_path / "artifacts/logs/evals/security-redteam-20260101T000000Z.summary.json",
        tmp_path / "artifacts/logs/evals/security-redteam-20260101T000000Z.jsonl",
        tmp_path / "artifacts/logs/launch_gate/security-readiness-20260101T000000Z.json",
    ]
    before = {str(path): path.read_bytes() for path in tracked}

    _ = service.get_overview()
    _ = service.list_traces()
    _ = service.get_trace("trace-ok")
    _ = service.list_replay_artifacts()
    _ = service.get_replay_artifact("trace-ok")
    _ = service.list_eval_runs()
    _ = service.get_eval_run("security-redteam-20260101T000000Z")
    _ = service.get_latest_launch_gate()

    after = {str(path): path.read_bytes() for path in tracked}
    assert before == after
