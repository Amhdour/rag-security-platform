"""Tests for read-only observability dashboard API and parsers."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from observability.api import _resolve_dashboard_host, create_server
from observability.service import DashboardService


def _seed_artifacts(base: Path) -> None:
    (base / "artifacts/logs").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/evals").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/replay").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/launch_gate").mkdir(parents=True, exist_ok=True)
    (base / "artifacts/logs/verification").mkdir(parents=True, exist_ok=True)
    (base / "observability/web/static").mkdir(parents=True, exist_ok=True)

    audit_rows = [
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
            "event_type": "tool.decision",
            "event_payload": {"token": "raw-secret-value"},
            "created_at": "2026-01-01T00:00:02Z",
        },
        {
            "event_id": "evt-3",
            "trace_id": "trace-2",
            "request_id": "req-2",
            "actor_id": "actor-2",
            "tenant_id": "tenant-b",
            "event_type": "request.start",
            "event_payload": {"channel": "email"},
            "created_at": "2026-01-01T00:00:03Z",
        },
        {
            "event_id": "evt-4",
            "trace_id": "trace-1",
            "request_id": "req-1",
            "actor_id": "actor-1",
            "tenant_id": "tenant-a",
            "event_type": "request.end",
            "event_payload": {"status": "ok"},
            "created_at": "2026-01-01T00:00:04Z",
        },
        {
            "event_id": "evt-5",
            "trace_id": "trace-2",
            "request_id": "req-2",
            "actor_id": "actor-2",
            "tenant_id": "tenant-b",
            "event_type": "deny.event",
            "event_payload": {"reason": "blocked by policy"},
            "created_at": "2026-01-01T00:00:05Z",
        },
        "malformed",
    ]
    (base / "artifacts/logs/audit.jsonl").write_text(
        "\n".join(json.dumps(row) if isinstance(row, dict) else row for row in audit_rows)
    )

    replay_payload = {
        "trace_id": "trace-1",
        "request_id": "req-1",
        "timeline": [{"event_type": "request.start", "payload": {"token": "[redacted]"}}],
    }
    (base / "artifacts/logs/replay/security-redteam-20260101T000000Z-trace-1.replay.json").write_text(
        json.dumps(replay_payload)
    )
    (base / "artifacts/logs/replay/malformed.replay.json").write_text("not-json")

    eval_summary = {
        "suite_name": "security-redteam",
        "passed": True,
        "total": 2,
        "passed_count": 2,
        "summary": "2/2 scenarios passed",
    }
    run_id = "security-redteam-20260101T000000Z"
    (base / f"artifacts/logs/evals/{run_id}.summary.json").write_text(json.dumps(eval_summary))
    scenario_rows = [
        {"scenario_id": "s1", "title": "ok", "severity": "low", "passed": True, "details": "all good"},
        {"scenario_id": "unauthorized_tool_use_attempt", "title": "Unauthorized tool use is denied", "severity": "high", "passed": False, "details": "tool unexpectedly allowed"},
    ]
    (base / f"artifacts/logs/evals/{run_id}.jsonl").write_text("\n".join(json.dumps(row) for row in scenario_rows))

    launch_gate = {
        "status": "conditional_go",
        "summary": "status=conditional_go",
        "blockers": [],
        "residual_risks": ["missing external attestation"],
        "checks": [{"check_name": "policy_artifact", "passed": True}],
        "scorecard": [{"category_name": "policy_artifacts", "status": "pass"}],
    }
    (base / "artifacts/logs/launch_gate/security-readiness-20260101T000000Z.json").write_text(json.dumps(launch_gate))

    verification = {"status": "pass", "summary": "all guarantees verified"}
    (base / "artifacts/logs/verification/security_guarantees.summary.json").write_text(json.dumps(verification))

    (base / "observability/web/index.html").write_text("<html><body>dashboard</body></html>")
    (base / "observability/web/static/app.js").write_text("console.log('dashboard')")
    (base / "observability/web/static/styles.css").write_text("body{font-family:sans-serif}")


def test_dashboard_host_defaults_to_localhost_unless_remote_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("DASHBOARD_ALLOW_REMOTE", raising=False)
    monkeypatch.delenv("DASHBOARD_HOST", raising=False)
    assert _resolve_dashboard_host(None) == "127.0.0.1"
    assert _resolve_dashboard_host("0.0.0.0") == "127.0.0.1"

    monkeypatch.setenv("DASHBOARD_ALLOW_REMOTE", "true")
    assert _resolve_dashboard_host("0.0.0.0") == "0.0.0.0"


def test_dashboard_api_endpoints_do_not_execute_tool_paths(tmp_path: Path, monkeypatch) -> None:
    _seed_artifacts(tmp_path)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("dashboard endpoint must not execute tool paths")

    monkeypatch.setattr("tools.registry.InMemoryToolRegistry.execute", _forbidden)
    monkeypatch.setattr("tools.router.SecureToolRouter.route", _forbidden)

    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for path in ("/api/overview", "/api/traces", "/api/traces/trace-1", "/api/replay", "/api/launch-gate/latest"):
            with urllib.request.urlopen(f"http://{host}:{port}{path}") as response:  # noqa: S310
                assert response.status == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_replay_payload_redaction_stays_redacted_in_api(tmp_path: Path) -> None:
    _seed_artifacts(tmp_path)
    service = DashboardService(tmp_path)
    replay = service.get_replay_artifact("trace-1")
    assert replay is not None
    timeline = replay.get("timeline", [])
    assert timeline
    assert timeline[0]["payload"]["token"] == "[redacted]"


def test_dashboard_service_filters_missing_files_and_redacts(tmp_path: Path) -> None:
    _seed_artifacts(tmp_path)
    service = DashboardService(tmp_path)

    traces = service.list_traces(filters={"tenant_id": "tenant-a", "event_type": "tool.decision"})
    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace-1"

    no_match = service.list_traces(filters={"actor_id": "actor-2", "event_type": "tool.decision"})
    assert no_match == []

    trace = service.get_trace("trace-1")
    assert trace is not None
    payload = trace["timeline"][1]["payload"]
    assert payload["token"] == "[redacted]"

    overview = service.get_overview()
    assert overview["counts"]["traces"] == 2
    assert overview["latest"]["launch_gate_status"] == "conditional_go"
    assert overview["latest"]["verification_status"] == "pass"
    assert overview["readiness_card"]["status"] == "conditional_go"
    assert overview["readiness_card"]["latest_artifact_timestamp"]
    assert any(source.get("type") == "audit_jsonl" for source in overview.get("evidence_sources", []))
    assert any(source.get("type") == "static_boundary_metadata" for source in overview.get("evidence_sources", []))
    integrity = overview.get("artifact_integrity", {})
    assert integrity.get("entries")
    assert any(item.get("signing_state") == "signing not implemented" for item in integrity.get("entries", []))


def test_dashboard_service_handles_missing_artifacts(tmp_path: Path) -> None:
    service = DashboardService(tmp_path)
    assert service.get_overview()["counts"]["traces"] == 0
    assert service.list_traces() == []
    assert service.get_trace("missing") is None
    assert service.list_replay_artifacts() == []
    assert service.get_replay_artifact("missing") is None
    assert service.list_eval_runs() == []
    assert service.get_eval_run("missing") is None
    assert service.get_latest_verification() is None
    assert service.get_latest_launch_gate() is None
    integrity = service.get_overview().get("artifact_integrity", {})
    assert integrity.get("entries")
    assert all(item.get("evidence_state") == "integrity unverified" for item in integrity.get("entries", []))





def test_dashboard_service_overview_includes_actionable_empty_state(tmp_path: Path) -> None:
    service = DashboardService(tmp_path)
    overview = service.get_overview()

    empty_state = overview.get("empty_state", {})
    assert empty_state.get("present") is True
    assert "No runtime artifacts found" in str(empty_state.get("title", ""))
    commands = empty_state.get("suggested_commands", [])
    assert any("generate_dashboard_demo_artifacts.py" in str(cmd) for cmd in commands)


def test_dashboard_service_overview_hides_empty_state_when_artifacts_exist(tmp_path: Path) -> None:
    _seed_artifacts(tmp_path)
    service = DashboardService(tmp_path)
    overview = service.get_overview()
    empty_state = overview.get("empty_state", {})
    assert empty_state.get("present") is False

def test_dashboard_service_trace_filtering_and_sorting_security_workflows(tmp_path: Path) -> None:
    _seed_artifacts(tmp_path)
    service = DashboardService(tmp_path)

    deny_only = service.list_traces(filters={"decision_class": "deny"})
    assert len(deny_only) == 1
    assert deny_only[0]["trace_id"] == "trace-2"

    outcome_ok = service.list_traces(filters={"final_outcome": "completed"})
    assert len(outcome_ok) == 1
    assert outcome_ok[0]["trace_id"] == "trace-1"

    replay_only = service.list_traces(filters={"replay_only": "true"})
    assert len(replay_only) == 1
    assert replay_only[0]["trace_id"] == "trace-1"

    partial_only = service.list_traces(filters={"partial_only": "true"})
    assert len(partial_only) == 1
    assert partial_only[0]["trace_id"] == "trace-2"

    security_only = service.list_traces(filters={"security_only": "true"})
    assert len(security_only) == 2

    date_filtered = service.list_traces(filters={"date_from": "2026-01-01T00:00:02Z"})
    assert all((row.get("started_at") or "") >= "2026-01-01T00:00:02Z" for row in date_filtered)

    sorted_by_outcome = service.list_traces(filters={"sort_by": "final_outcome", "sort_order": "asc"})
    assert [row["trace_id"] for row in sorted_by_outcome] == ["trace-1", "trace-2"]

def test_dashboard_http_endpoints_and_error_handling(tmp_path: Path) -> None:
    _seed_artifacts(tmp_path)
    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    def _get(path: str) -> tuple[int, dict]:
        with urllib.request.urlopen(f"http://{host}:{port}{path}") as response:  # noqa: S310
            return response.status, json.loads(response.read().decode("utf-8"))

    try:
        status, payload = _get("/api/overview")
        assert status == 200
        assert payload["counts"]["traces"] == 2
        assert payload["readiness_card"]["status"] == "conditional_go"
        assert any(item.get("type") == "launch_gate_report" for item in payload.get("evidence_sources", []))
        assert "artifact_integrity" in payload

        status, payload = _get("/api/traces?tenant_id=tenant-a")
        assert status == 200
        assert len(payload["items"]) == 1

        status, payload = _get("/api/traces?decision_class=deny")
        assert status == 200
        assert len(payload["items"]) == 1
        assert payload["items"][0]["trace_id"] == "trace-2"

        status, payload = _get("/api/traces/trace-1")
        assert status == 200
        assert payload["trace_id"] == "trace-1"
        assert payload.get("artifact_integrity", {}).get("entries")

        status, payload = _get("/api/replay")
        assert status == 200
        assert len(payload["items"]) == 1

        status, payload = _get("/api/replay/trace-1")
        assert status == 200
        assert payload["trace_id"] == "trace-1"

        status, payload = _get("/api/evals")
        assert status == 200
        assert len(payload["items"]) == 1

        status, payload = _get("/api/evals/security-redteam-20260101T000000Z")
        assert status == 200
        assert len(payload["scenario_results"]) == 2
        assert "baseline_coverage" in payload

        status, payload = _get("/api/verification/latest")
        assert status == 200
        assert payload["status"] == "pass"

        status, payload = _get("/api/launch-gate/latest")
        assert status == 200
        assert payload["status"] == "conditional_go"
        assert payload["latest_artifact_timestamp"]

        status, payload = _get("/api/system-map")
        assert status == 200
        assert payload["read_only"] is True

        for method in ("POST", "PUT", "PATCH", "DELETE"):
            request = urllib.request.Request(f"http://{host}:{port}/api/traces", method=method)
            try:
                urllib.request.urlopen(request)  # noqa: S310
                assert False, f"expected HTTP 405 for {method}"
            except urllib.error.HTTPError as exc:
                assert exc.code == 405

        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/traces/missing")  # noqa: S310
            assert False, "expected HTTP 404"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def test_create_server_uses_integration_artifacts_root_env_when_dashboard_env_missing(tmp_path: Path, monkeypatch) -> None:
    integration_root = tmp_path / "integration-artifacts"
    (integration_root / "replay").mkdir(parents=True, exist_ok=True)
    (integration_root / "evals").mkdir(parents=True, exist_ok=True)
    (integration_root / "launch_gate").mkdir(parents=True, exist_ok=True)
    (integration_root / "audit.jsonl").write_text("")
    (tmp_path / "observability/web/static").mkdir(parents=True, exist_ok=True)
    (tmp_path / "observability/web/index.html").write_text("ok")
    (tmp_path / "observability/web/static/app.js").write_text("ok")

    monkeypatch.delenv("DASHBOARD_ARTIFACTS_ROOT", raising=False)
    monkeypatch.setenv("INTEGRATION_ARTIFACTS_ROOT", str(integration_root))

    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    try:
        service = server.RequestHandlerClass.service
        assert service is not None
        assert service.paths.artifacts_root == integration_root
    finally:
        server.server_close()




def test_dashboard_service_overview_reports_artifact_diagnostics(tmp_path: Path) -> None:
    _seed_artifacts(tmp_path)
    service = DashboardService(tmp_path)
    overview = service.get_overview()

    diagnostics = overview.get("artifact_diagnostics", {})
    assert diagnostics.get("malformed_files") == 1
    assert diagnostics.get("malformed_lines") == 1
    parse_errors = diagnostics.get("parse_errors", [])
    assert any("replay/malformed.replay.json" in str(item.get("path", "")) for item in parse_errors)


def test_dashboard_service_empty_state_identifies_malformed_artifacts(tmp_path: Path) -> None:
    logs = tmp_path / "artifacts/logs"
    (logs / "evals").mkdir(parents=True, exist_ok=True)
    (logs / "replay").mkdir(parents=True, exist_ok=True)
    (logs / "launch_gate").mkdir(parents=True, exist_ok=True)
    (logs / "verification").mkdir(parents=True, exist_ok=True)
    (logs / "audit.jsonl").write_text("not-json")
    (logs / "replay/bad.replay.json").write_text("{bad-json")

    service = DashboardService(tmp_path)
    overview = service.get_overview()

    empty_state = overview.get("empty_state", {})
    assert empty_state.get("present") is True
    assert "malformed" in str(empty_state.get("title", "")).lower()
    diagnostics = empty_state.get("diagnostics", {})
    assert diagnostics.get("malformed_files") == 1
    assert diagnostics.get("malformed_lines") == 1


def test_create_server_falls_back_to_sibling_integration_adapter_artifacts(tmp_path: Path, monkeypatch) -> None:
    dashboard_root = tmp_path / "myStarterKit-maindashb-main"
    (dashboard_root / "observability/web/static").mkdir(parents=True, exist_ok=True)
    (dashboard_root / "observability/web/index.html").write_text("ok")
    (dashboard_root / "observability/web/static/app.js").write_text("ok")

    adapter_root = tmp_path / "integration-adapter" / "artifacts" / "logs"
    (adapter_root / "replay").mkdir(parents=True, exist_ok=True)
    (adapter_root / "evals").mkdir(parents=True, exist_ok=True)
    (adapter_root / "launch_gate").mkdir(parents=True, exist_ok=True)
    (adapter_root / "audit.jsonl").write_text("")

    monkeypatch.delenv("DASHBOARD_ARTIFACTS_ROOT", raising=False)
    monkeypatch.delenv("INTEGRATION_ARTIFACTS_ROOT", raising=False)
    monkeypatch.delenv("INTEGRATION_ADAPTER_ARTIFACTS_ROOT", raising=False)

    server = create_server(host="127.0.0.1", port=0, repo_root=dashboard_root)
    try:
        service = server.RequestHandlerClass.service
        assert service is not None
        assert service.paths.artifacts_root == adapter_root.resolve()
    finally:
        server.server_close()

def test_dashboard_api_returns_500_when_service_raises(tmp_path: Path, monkeypatch) -> None:
    _seed_artifacts(tmp_path)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(DashboardService, "list_traces", _boom)

    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/traces")  # noqa: S310
            assert False, "expected HTTP 500"
        except urllib.error.HTTPError as exc:
            assert exc.code == 500
            payload = json.loads(exc.read().decode("utf-8"))
            assert payload["error"] == "internal_error"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_create_server_uses_integration_adapter_artifacts_root_env_when_others_missing(tmp_path: Path, monkeypatch) -> None:
    integration_root = tmp_path / "adapter-artifacts"
    (integration_root / "replay").mkdir(parents=True, exist_ok=True)
    (integration_root / "evals").mkdir(parents=True, exist_ok=True)
    (integration_root / "launch_gate").mkdir(parents=True, exist_ok=True)
    (integration_root / "audit.jsonl").write_text("")
    (tmp_path / "observability/web/static").mkdir(parents=True, exist_ok=True)
    (tmp_path / "observability/web/index.html").write_text("ok")
    (tmp_path / "observability/web/static/app.js").write_text("ok")

    monkeypatch.delenv("DASHBOARD_ARTIFACTS_ROOT", raising=False)
    monkeypatch.delenv("INTEGRATION_ARTIFACTS_ROOT", raising=False)
    monkeypatch.setenv("INTEGRATION_ADAPTER_ARTIFACTS_ROOT", str(integration_root))

    server = create_server(host="127.0.0.1", port=0, repo_root=tmp_path)
    try:
        service = server.RequestHandlerClass.service
        assert service is not None
        assert service.paths.artifacts_root == integration_root
    finally:
        server.server_close()
