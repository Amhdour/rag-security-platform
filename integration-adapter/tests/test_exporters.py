from __future__ import annotations

import json

from integration_adapter.exporters import (
    ConnectorInventoryExporter,
    EvalResultsExporter,
    MCPInventoryExporter,
    RuntimeEventsExporter,
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

    assert rows == [
        {
            "id": "con-1",
            "name": "confluence",
            "status": "active",
            "source_type": "wiki",
            "indexed": True,
        }
    ]


def test_tool_inventory_exporter_defaults_missing_fields(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "tools.json"
    snapshot.write_text(json.dumps([{"name": "search"}]), encoding="utf-8")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", str(snapshot))

    rows = ToolInventoryExporter().export()

    assert rows[0]["name"] == "search"
    assert rows[0]["status"] == "unknown"
    assert rows[0]["risk_tier"] == "unspecified"
    assert rows[0]["enabled"] is False


def test_mcp_inventory_exporter_reads_json_snapshot(tmp_path, monkeypatch) -> None:
    snapshot = tmp_path / "mcp.json"
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

    assert rows == [
        {
            "id": "eval-1",
            "suite": "security_baseline",
            "passed": True,
            "score": 0.98,
            "scenario": "prompt_injection_direct",
        }
    ]


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

    rows = RuntimeEventsExporter().export()

    assert len(rows) == 1
    assert rows[0]["event_type"] == "request.start"


def test_exporters_gracefully_handle_missing_files(monkeypatch) -> None:
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", "/tmp/does-not-exist-connectors.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", "/tmp/does-not-exist-tools.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_MCP_JSON", "/tmp/does-not-exist-mcp.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", "/tmp/does-not-exist-evals.json")
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", "/tmp/does-not-exist-audit.jsonl")

    assert ConnectorInventoryExporter().export() == []
    assert ToolInventoryExporter().export() == []
    assert MCPInventoryExporter().export() == []
    assert EvalResultsExporter().export() == []
    assert RuntimeEventsExporter().export() == []
