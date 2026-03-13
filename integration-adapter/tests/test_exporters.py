from __future__ import annotations

from contextlib import contextmanager
import json
from types import SimpleNamespace

from integration_adapter.exporters import (
    ConnectorInventoryExporter,
    EvalResultsExporter,
    MCPInventoryExporter,
    RuntimeEventsExporter,
    SOURCE_MODE_DB_BACKED,
    SOURCE_MODE_FILE_BACKED,
    SOURCE_MODE_FIXTURE_BACKED,
    SOURCE_MODE_LIVE,
    SOURCE_MODE_SERVICE_API,
    ToolInventoryExporter,
)


def test_connector_inventory_exporter_reads_json_snapshot(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "connectors.json"
    snapshot.write_text(
        json.dumps(
            [
                {
                    "id": "con-1",
                    "name": "confluence",
                    "status": "active",
                    "source_type": "wiki",
                    "indexed": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", str(snapshot))

    rows = ConnectorInventoryExporter().export()

    assert rows[0]["id"] == "con-1"
    assert rows[0]["source_mode"] == SOURCE_MODE_FILE_BACKED
    assert rows[0]["fallback_used"] is True


def test_tool_inventory_exporter_defaults_missing_fields(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "tools.json"
    snapshot.write_text(json.dumps([{"name": "search"}]), encoding="utf-8")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", str(snapshot))

    rows = ToolInventoryExporter().export()

    assert rows[0]["name"] == "search"
    assert rows[0]["status"] == "unknown"
    assert rows[0]["risk_tier"] == "unspecified"
    assert rows[0]["enabled"] is False
    assert "risk_tier" in rows[0]["derived_fields"]
    assert "enabled" in rows[0]["derived_fields"]


def test_mcp_inventory_exporter_reads_json_snapshot(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "fixtures" / "mcp.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        json.dumps(
            [
                {
                    "id": "mcp-1",
                    "name": "ops-mcp",
                    "status": "connected",
                    "endpoint": "https://mcp.local",
                    "usage_count": 3,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_MCP_JSON", str(snapshot))

    rows = MCPInventoryExporter().export()

    assert rows[0]["id"] == "mcp-1"
    assert rows[0]["endpoint"] == "https://mcp.local"
    assert rows[0]["usage_count"] == 3
    assert rows[0]["source_mode"] == SOURCE_MODE_FIXTURE_BACKED


def test_eval_results_exporter_maps_rows(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "evals.json"
    snapshot.write_text(
        json.dumps(
            [
                {
                    "id": "eval-1",
                    "suite": "security_baseline",
                    "passed": True,
                    "score": 0.98,
                    "scenario": "prompt_injection_direct",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", str(snapshot))

    rows = EvalResultsExporter().export()

    assert rows[0]["id"] == "eval-1"
    assert rows[0]["suite"] == "security_baseline"
    assert rows[0]["source_mode"] == SOURCE_MODE_FILE_BACKED


def test_runtime_events_exporter_filters_invalid_event_types(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "audit.jsonl"
    snapshot.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "request_id": "r1",
                        "trace_id": "t1",
                        "event_type": "request.start",
                        "actor_id": "user-1",
                        "tenant_id": "tenant-a",
                        "event_payload": {"entrypoint": "chat"},
                    }
                ),
                json.dumps(
                    {
                        "request_id": "r2",
                        "trace_id": "t2",
                        "event_type": "malformed",
                        "actor_id": "user-2",
                        "tenant_id": "tenant-a",
                        "event_payload": {},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", str(snapshot))

    exporter = RuntimeEventsExporter()
    rows = exporter.export()

    assert len(rows) == 1
    assert rows[0]["event_type"] == "request.start"
    assert exporter.last_acquisition is not None
    assert any("dropped invalid mapped runtime events" in w for w in exporter.last_acquisition.warnings)


def test_connector_exporter_db_fallback_path(monkeypatch) -> None:
    exporter = ConnectorInventoryExporter()
    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([], [], []))
    monkeypatch.setattr(
        exporter,
        "_read_from_onyx_db",
        lambda: (
            [
                {
                    "id": 1,
                    "name": "drive",
                    "status": "active",
                    "source_type": "google_drive",
                    "indexed": True,
                }
            ],
            [],
            [],
        ),
    )
    rows = exporter.export()
    assert rows[0]["name"] == "drive"
    assert rows[0]["indexed"] is True
    assert rows[0]["source_mode"] in {SOURCE_MODE_DB_BACKED, "live"}
    assert rows[0]["fallback_used"] is True


def test_tool_exporter_db_fallback_path(monkeypatch) -> None:
    exporter = ToolInventoryExporter()
    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([], [], []))
    monkeypatch.setattr(
        exporter,
        "_read_from_onyx_db",
        lambda: ([{"id": 7, "name": "builtin", "status": "enabled", "risk_tier": "low", "enabled": True}], [], []),
    )
    rows = exporter.export()
    assert rows[0]["id"] == "7"
    assert rows[0]["source_mode"] in {SOURCE_MODE_DB_BACKED, "live"}


def test_mcp_exporter_db_fallback_path(monkeypatch) -> None:
    exporter = MCPInventoryExporter()
    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([], [], []))
    monkeypatch.setattr(
        exporter,
        "_read_from_onyx_db",
        lambda: ([{"id": 3, "name": "mcp", "status": "connected", "endpoint": "http://mcp", "usage_count": 11}], [], []),
    )
    rows = exporter.export()
    assert rows[0]["usage_count"] == 11
    assert rows[0]["fallback_used"] is True


def test_runtime_events_exporter_db_fallback_path(monkeypatch) -> None:
    exporter = RuntimeEventsExporter()
    monkeypatch.setattr(exporter, "_read_jsonl_records", lambda _path: ([], [], []))
    monkeypatch.setattr(
        exporter,
        "_read_from_onyx_db",
        lambda: (
            [
                {
                    "request_id": "req-1",
                    "trace_id": "trace-1",
                    "event_type": "tool.execution_attempt",
                    "actor_id": "tool-runtime",
                    "tenant_id": "tenant-a",
                    "event_payload": {"tool_name": "search"},
                }
            ],
            [],
            [],
        ),
    )
    rows = exporter.export()
    assert rows and rows[0]["event_type"] == "tool.execution_attempt"
    assert rows[0]["event_payload"]["source_mode"] in {SOURCE_MODE_DB_BACKED, "live"}


def test_eval_results_exporter_runtime_config_fallback(monkeypatch) -> None:
    exporter = EvalResultsExporter()

    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([], [], []))

    def _runtime_import(module: str, attribute: str):
        if module == "onyx.configs.app_configs" and attribute == "SCHEDULED_EVAL_DATASET_NAMES":
            return ["security-baseline", "policy-stress"]
        if module == "onyx.configs.app_configs" and attribute == "SCHEDULED_EVAL_PROJECT":
            return "onyx"
        raise ImportError(module)

    @contextmanager
    def _noop_backend_path(_onyx_root):
        yield

    monkeypatch.setattr("integration_adapter.exporters._runtime_import", _runtime_import)
    monkeypatch.setattr("integration_adapter.exporters._with_backend_on_path", _noop_backend_path)

    rows = exporter.export()

    assert len(rows) == 2
    assert rows[0]["suite"] == "onyx:security-baseline"
    assert rows[0]["scenario"] == "security-baseline"
    assert rows[0]["passed"] is False
    assert rows[0]["fallback_used"] is True


def test_runtime_events_exporter_db_includes_chat_session_lifecycle(monkeypatch) -> None:
    exporter = RuntimeEventsExporter()
    monkeypatch.setattr(exporter, "_read_jsonl_records", lambda _path: ([], [], []))

    chat_session = SimpleNamespace(id="chat-1", user_id="user-1", time_created="2026-01-01T00:00:00Z", time_updated="2026-01-01T00:00:05Z")
    tool_call = SimpleNamespace(id=5, chat_session_id="chat-1", tool_id=7, tool_call_id="call-7")
    tool = SimpleNamespace(id=7, name="search")

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            return self._rows

    class _FakeSession:
        def query(self, model):
            if model is _ChatSession:
                return _FakeQuery([chat_session])
            if model is _ToolCall:
                return _FakeQuery([tool_call])
            if model is _Tool:
                return _FakeQuery([tool])
            return _FakeQuery([])

    @contextmanager
    def _fake_get_session():
        yield _FakeSession()

    class _SortableField:
        def desc(self):
            return self

    class _ChatSession:
        time_updated = _SortableField()

    class _ToolCall:
        id = _SortableField()

    class _Tool:
        pass

    def _runtime_import(module: str, attribute: str):
        if module == "onyx.db.engine.sql_engine" and attribute == "get_session":
            return _fake_get_session
        if module == "onyx.db.models" and attribute == "ChatSession":
            return _ChatSession
        if module == "onyx.db.models" and attribute == "ToolCall":
            return _ToolCall
        if module == "onyx.db.models" and attribute == "Tool":
            return _Tool
        raise ImportError(module)

    @contextmanager
    def _noop_backend_path(_onyx_root):
        yield

    monkeypatch.setattr("integration_adapter.exporters._runtime_import", _runtime_import)
    monkeypatch.setattr("integration_adapter.exporters._with_backend_on_path", _noop_backend_path)

    rows = exporter.export()

    event_types = {row["event_type"] for row in rows}
    assert "request.start" in event_types
    assert "request.end" in event_types
    assert "tool.execution_attempt" in event_types


def test_exporters_gracefully_handle_missing_files(monkeypatch) -> None:
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", "/tmp/does-not-exist-connectors.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", "/tmp/does-not-exist-tools.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_MCP_JSON", "/tmp/does-not-exist-mcp.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", "/tmp/does-not-exist-evals.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", "/tmp/does-not-exist-audit.jsonl")

    connectors = ConnectorInventoryExporter()
    tools = ToolInventoryExporter()
    mcp = MCPInventoryExporter()
    evals = EvalResultsExporter()
    events = RuntimeEventsExporter()

    assert connectors.export() == []
    assert tools.export() == []
    assert mcp.export() == []
    assert evals.export() == []
    assert events.export() == []

    assert connectors.last_acquisition is not None
    assert any("does not exist" in warning for warning in connectors.last_acquisition.warnings)


def test_tool_risk_tier_heuristics() -> None:
    exporter = ToolInventoryExporter()
    assert exporter._derive_risk_tier(SimpleNamespace(passthrough_auth=True, mcp_server_id=None, openapi_schema=None, in_code_tool_id=None)) == "high"
    assert exporter._derive_risk_tier(SimpleNamespace(passthrough_auth=False, mcp_server_id=9, openapi_schema=None, in_code_tool_id=None)) == "high"
    assert exporter._derive_risk_tier(SimpleNamespace(passthrough_auth=False, mcp_server_id=None, openapi_schema={"type": "object"}, in_code_tool_id=None)) == "medium"
    assert exporter._derive_risk_tier(SimpleNamespace(passthrough_auth=False, mcp_server_id=None, openapi_schema=None, in_code_tool_id="search")) == "low"


def test_connector_exporter_prefers_service_api_over_db_and_file(monkeypatch) -> None:
    exporter = ConnectorInventoryExporter()
    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([{"id": "f1", "name": "file", "status": "active", "source_type": "wiki", "indexed": True}], [], []))
    monkeypatch.setattr(exporter, "_read_from_onyx_db", lambda: ([{"id": "d1", "name": "db", "status": "active", "source_type": "wiki", "indexed": True}], [], []))
    monkeypatch.setattr(exporter, "_read_from_service_api", lambda: ([{"id": "s1", "name": "svc", "status": "active", "source_type": "wiki", "indexed": True}], [], [], "https://onyx/connectors"))

    rows = exporter.export()

    assert rows[0]["id"] == "s1"
    assert rows[0]["source_mode"] == SOURCE_MODE_SERVICE_API
    assert rows[0]["fallback_used"] is True


def test_connector_exporter_prefers_live_when_flag_enabled(monkeypatch) -> None:
    exporter = ConnectorInventoryExporter()
    monkeypatch.setenv("INTEGRATION_ADAPTER_DB_SOURCE_MODE_LIVE", "true")
    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([{"id": "f1", "name": "file", "status": "active", "source_type": "wiki", "indexed": True}], [], []))
    monkeypatch.setattr(exporter, "_read_from_onyx_db", lambda: ([{"id": "l1", "name": "live-db", "status": "active", "source_type": "wiki", "indexed": True}], [], []))
    monkeypatch.setattr(exporter, "_read_from_service_api", lambda: ([{"id": "s1", "name": "svc", "status": "active", "source_type": "wiki", "indexed": True}], [], [], "https://onyx/connectors"))

    rows = exporter.export()

    assert rows[0]["id"] == "l1"
    assert rows[0]["source_mode"] == SOURCE_MODE_LIVE
    assert rows[0]["fallback_used"] is False


def test_runtime_events_exporter_prefers_live_log_source(tmp_path, monkeypatch) -> None:
    live = tmp_path / "live-audit.jsonl"
    live.write_text(json.dumps({"request_id": "r1", "trace_id": "t1", "event_type": "request.start", "actor_id": "u1", "tenant_id": "t", "event_payload": {}}), encoding="utf-8")
    file_snapshot = tmp_path / "file-audit.jsonl"
    file_snapshot.write_text(json.dumps({"request_id": "r2", "trace_id": "t2", "event_type": "request.start", "actor_id": "u2", "tenant_id": "t", "event_payload": {}}), encoding="utf-8")

    exporter = RuntimeEventsExporter()
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_LOG_JSONL", str(live))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", str(file_snapshot))
    monkeypatch.setattr(exporter, "_read_from_onyx_db", lambda: ([], [], []))
    monkeypatch.setattr(exporter, "_read_from_service_api", lambda: ([], [], [], ""))

    rows = exporter.export()

    assert rows
    assert rows[0]["event_payload"]["source_mode"] == SOURCE_MODE_LIVE


def test_eval_exporter_handles_malformed_service_data_and_falls_back(monkeypatch) -> None:
    exporter = EvalResultsExporter()
    monkeypatch.setattr(exporter, "_read_json_records", lambda _path: ([{"id": "f-eval", "suite": "file", "passed": True, "score": 1, "scenario": "ok"}], [], []))
    monkeypatch.setattr(exporter, "_read_from_onyx_runtime_config", lambda: ([], [], []))
    monkeypatch.setattr(exporter, "_read_from_service_api", lambda: ([], [], ["service malformed"], "https://onyx/evals"))

    rows = exporter.export()

    assert rows[0]["id"] == "f-eval"
    assert rows[0]["source_mode"] == SOURCE_MODE_FILE_BACKED
    assert "service malformed" in rows[0]["source_errors"]


def test_runtime_events_exporter_partial_availability_uses_db_when_service_empty(monkeypatch) -> None:
    exporter = RuntimeEventsExporter()
    monkeypatch.setattr(exporter, "_read_from_live_runtime_logs", lambda: ([], ["no live"], [], ""))
    monkeypatch.setattr(exporter, "_read_from_service_api", lambda: ([], ["service empty"], [], "https://onyx/events"))
    monkeypatch.setattr(exporter, "_read_from_onyx_db", lambda: ([{"request_id": "req-1", "trace_id": "trace-1", "event_type": "request.start", "actor_id": "actor", "tenant_id": "tenant", "event_payload": {}}], [], []))
    monkeypatch.setattr(exporter, "_read_jsonl_records", lambda _path: ([], [], []))

    rows = exporter.export()

    assert rows
    assert rows[0]["event_payload"]["source_mode"] in {SOURCE_MODE_DB_BACKED, SOURCE_MODE_LIVE}
    assert rows[0]["event_payload"]["fallback_used"] is True
