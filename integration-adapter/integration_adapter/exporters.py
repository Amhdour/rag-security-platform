from __future__ import annotations

"""Exporters for Onyx-facing runtime surfaces.

Status labels used in this module:
- Implemented: file-backed JSON/JSONL extraction and mapper-based normalization.
- Partially Implemented: optional direct Onyx DB reads when runtime imports/session are available.
- Unconfirmed: canonical production hook parity across all deployments is not asserted here.

Design:
- raw extraction is read-only and best-effort;
- normalization is delegated to mapper functions;
- schema validation is enforced at exporter boundaries.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from integration_adapter.mappers import (
    map_connector_inventory,
    map_eval_inventory,
    map_mcp_inventory,
    map_runtime_event,
    map_tool_inventory,
)
from integration_adapter.raw_sources import (
    SourceReadError,
    discover_default_paths,
    env_path,
    load_json_records,
    load_jsonl_records,
)


def _to_rows(records: list[Any]) -> list[dict[str, Any]]:
    return [record for record in records if isinstance(record, dict)]


def _safe_validate_inventory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("name", "unknown"))
        validated.append(
            {
                "id": str(row.get("id", row.get("record_id", name))),
                "name": name,
                "status": str(row.get("status", "unknown")),
                **row,
            }
        )
    return validated


@dataclass
class _BaseExporter:
    onyx_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "onyx-main")

    def _source_path(self, env_name: str, default_key: str) -> Path:
        discovered = discover_default_paths(self.onyx_root)
        return env_path(env_name) or discovered[default_key]

    def _read_json_records(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            return load_json_records(path)
        except SourceReadError:
            return []

    def _read_jsonl_records(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return load_jsonl_records(path)


@dataclass
class ConnectorInventoryExporter(_BaseExporter):
    """Exports connector/indexed-source inventory from runtime state.

    Implemented: JSON snapshot source (configured or default path).
    Partially Implemented: optional direct Onyx DB extraction when runtime imports/session work.
    Unconfirmed: production-wide canonical connector source semantics across all deployments.
    """

    def _read_from_onyx_db(self) -> list[dict[str, Any]]:
        try:
            import sys

            backend_root = self.onyx_root / "backend"
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))

            from onyx.db.connector import fetch_connectors  # type: ignore
            from onyx.db.engine.sql_engine import get_session  # type: ignore

            with get_session() as db_session:
                connectors = fetch_connectors(db_session)
            rows: list[dict[str, Any]] = []
            for connector in connectors:
                rows.append(
                    {
                        "id": getattr(connector, "id", "unknown"),
                        "name": getattr(connector, "name", "unknown_connector"),
                        "status": "active",
                        "source_type": str(getattr(connector, "source", "unknown")),
                        "indexed": True,
                    }
                )
            return rows
        except Exception:
            # Explicitly fail closed to file-backed extraction when runtime hooks are unavailable.
            return []

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", "connectors")
        rows = self._read_json_records(path)
        if not rows:
            rows = self._read_from_onyx_db()
        normalized = map_connector_inventory(_safe_validate_inventory_rows(_to_rows(rows)))
        return [
            {
                "id": row.record_id,
                "name": row.name,
                "status": row.status,
                "source_type": row.metadata.get("source_type", "unknown"),
                "indexed": bool(row.metadata.get("indexed", False)),
            }
            for row in normalized
        ]


@dataclass
class ToolInventoryExporter(_BaseExporter):
    """Exports tool inventory and policy-relevant metadata.

    Implemented: JSON snapshot source.
    Partially Implemented: optional Onyx DB `get_tools` extraction.
    Unconfirmed: production-wide canonical risk/visibility semantics across deployments.
    """

    def _read_from_onyx_db(self) -> list[dict[str, Any]]:
        try:
            import sys

            backend_root = self.onyx_root / "backend"
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))

            from onyx.db.engine.sql_engine import get_session  # type: ignore
            from onyx.db.tools import get_tools  # type: ignore

            with get_session() as db_session:
                tools = get_tools(db_session)
            rows: list[dict[str, Any]] = []
            for tool in tools:
                rows.append(
                    {
                        "id": getattr(tool, "id", "unknown"),
                        "name": getattr(tool, "display_name", None)
                        or getattr(tool, "name", "unknown_tool"),
                        "status": "enabled" if bool(getattr(tool, "is_visible", True)) else "hidden",
                        "risk_tier": "unspecified",
                        "enabled": bool(getattr(tool, "is_visible", True)),
                    }
                )
            return rows
        except Exception:
            return []

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", "tools")
        rows = self._read_json_records(path)
        if not rows:
            rows = self._read_from_onyx_db()
        normalized = map_tool_inventory(_safe_validate_inventory_rows(_to_rows(rows)))
        return [
            {
                "id": row.record_id,
                "name": row.name,
                "status": row.status,
                "risk_tier": row.metadata.get("risk_tier", "unspecified"),
                "enabled": bool(row.metadata.get("enabled", False)),
            }
            for row in normalized
        ]


@dataclass
class MCPInventoryExporter(_BaseExporter):
    """Exports MCP server inventory and usage-oriented metadata.

    Implemented: JSON snapshot source.
    Partially Implemented: optional Onyx DB `get_all_mcp_servers` extraction.
    Unconfirmed: canonical runtime MCP usage semantics across deployments.
    """

    def _read_from_onyx_db(self) -> list[dict[str, Any]]:
        try:
            import sys

            backend_root = self.onyx_root / "backend"
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))

            from onyx.db.engine.sql_engine import get_session  # type: ignore
            from onyx.db.mcp import get_all_mcp_servers  # type: ignore

            with get_session() as db_session:
                servers = get_all_mcp_servers(db_session)

            rows: list[dict[str, Any]] = []
            for server in servers:
                rows.append(
                    {
                        "id": getattr(server, "id", "unknown"),
                        "name": getattr(server, "name", "unknown_mcp_server"),
                        "status": str(getattr(server, "status", "unknown")).lower(),
                        "endpoint": getattr(server, "server_url", ""),
                        "usage_count": 0,
                    }
                )
            return rows
        except Exception:
            return []

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_MCP_JSON", "mcp_servers")
        rows = self._read_json_records(path)
        if not rows:
            rows = self._read_from_onyx_db()
        normalized = map_mcp_inventory(_safe_validate_inventory_rows(_to_rows(rows)))
        return [
            {
                "id": row.record_id,
                "name": row.name,
                "status": row.status,
                "endpoint": row.metadata.get("endpoint", ""),
                "usage_count": int(row.metadata.get("usage_count", 0)),
            }
            for row in normalized
        ]


@dataclass
class EvalResultsExporter(_BaseExporter):
    """Exports eval results for governance normalization.

    Implemented: JSON snapshot source (array/object) from configured eval path.
    Unconfirmed: canonical multi-provider Onyx eval output compatibility for all fields.
    """

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", "evals")
        rows = self._read_json_records(path)
        normalized = map_eval_inventory(_safe_validate_inventory_rows(_to_rows(rows)))
        return [
            {
                "id": row.record_id,
                "suite": row.name,
                "passed": row.status == "pass",
                "score": row.metadata.get("score", 0),
                "scenario": row.metadata.get("scenario", "unspecified"),
            }
            for row in normalized
        ]


@dataclass
class RuntimeEventsExporter(_BaseExporter):
    """Exports security-relevant runtime events for audit normalization.

    Implemented: JSONL audit-feed extraction and schema filtering.
    Unconfirmed: canonical Onyx lifecycle/retrieval/tool decision stream parity across deployments.
    """

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", "runtime_events")
        rows = self._read_jsonl_records(path)
        events = [map_runtime_event(row) for row in rows if isinstance(row, dict)]
        valid: list[dict[str, Any]] = []
        for event in events:
            try:
                payload = event.to_dict()
            except ValueError:
                continue
            valid.append(payload)
        return valid
