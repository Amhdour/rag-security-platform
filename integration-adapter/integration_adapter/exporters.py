from __future__ import annotations

"""Exporters for Onyx-facing runtime surfaces.

Status labels used in this module:
- Implemented: file-backed JSON/JSONL extraction and mapper-based normalization.
- Partially Implemented: optional direct Onyx DB reads when runtime imports/session are available.
- Unconfirmed: canonical production hook parity across all deployments is not asserted here.

Design:
- raw extraction is read-only and best-effort;
- normalization is delegated to mapper functions;
- Implemented: schema validation is enforced at exporter boundaries.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import importlib
from pathlib import Path
import sys
from typing import Any, Iterator

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


def _stringify_enumish(value: Any, *, lowercase: bool = False) -> str:
    raw = getattr(value, "value", value)
    text = str(raw)
    return text.lower() if lowercase else text


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _iso_timestamp(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return None


@contextmanager
def _with_backend_on_path(onyx_root: Path) -> Iterator[None]:
    backend_root = onyx_root / "backend"
    inserted = False
    backend_str = str(backend_root)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
        inserted = True
    try:
        yield
    finally:
        if inserted:
            try:
                sys.path.remove(backend_str)
            except ValueError:
                pass


def _runtime_import(module: str, attribute: str) -> Any:
    loaded = importlib.import_module(module)
    return getattr(loaded, attribute)


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
        try:
            return load_jsonl_records(path)
        except OSError:
            return []


@dataclass
class ConnectorInventoryExporter(_BaseExporter):
    """Exports connector/indexed-source inventory from runtime state.

    Implemented: JSON snapshot source (configured or default path).
    Partially Implemented: optional direct Onyx DB extraction when runtime imports/session work.
    Unconfirmed: production-wide canonical connector source semantics across all deployments.
    """

    def _derive_connector_status(self, credential_statuses: list[str]) -> str:
        lowered = {status.lower() for status in credential_statuses if status}
        if not lowered:
            return "unknown"
        if lowered & {"active", "scheduled", "initial_indexing"}:
            return "active"
        if "paused" in lowered:
            return "paused"
        if "deleting" in lowered:
            return "deleting"
        if "invalid" in lowered:
            return "invalid"
        return sorted(lowered)[0]

    def _read_from_onyx_db(self) -> list[dict[str, Any]]:
        try:
            with _with_backend_on_path(self.onyx_root):
                fetch_connectors = _runtime_import("onyx.db.connector", "fetch_connectors")
                get_session = _runtime_import("onyx.db.engine.sql_engine", "get_session")

                with get_session() as db_session:
                    connectors = fetch_connectors(db_session)
                    rows: list[dict[str, Any]] = []
                    for connector in connectors:
                        credential_rows = list(getattr(connector, "credentials", []) or [])
                        statuses = [_stringify_enumish(getattr(item, "status", ""), lowercase=True) for item in credential_rows]
                        indexed = any(_safe_int(getattr(item, "total_docs_indexed", 0), 0) > 0 for item in credential_rows) or any(
                            getattr(item, "last_successful_index_time", None) is not None for item in credential_rows
                        )
                        rows.append(
                            {
                                "id": getattr(connector, "id", "unknown"),
                                "name": getattr(connector, "name", "unknown_connector"),
                                "status": self._derive_connector_status(statuses),
                                "source_type": _stringify_enumish(getattr(connector, "source", "unknown"), lowercase=True),
                                "indexed": indexed,
                            }
                        )
                    return rows
        except Exception:
            # UNCONFIRMED: canonical runtime hook not validated in this workspace.
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

    def _derive_risk_tier(self, tool: Any) -> str:
        if bool(getattr(tool, "passthrough_auth", False)):
            return "high"
        if getattr(tool, "mcp_server_id", None) is not None:
            return "high"
        if getattr(tool, "openapi_schema", None):
            return "medium"
        if getattr(tool, "in_code_tool_id", None):
            return "low"
        return "unspecified"

    def _read_from_onyx_db(self) -> list[dict[str, Any]]:
        try:
            with _with_backend_on_path(self.onyx_root):
                get_session = _runtime_import("onyx.db.engine.sql_engine", "get_session")
                get_tools = _runtime_import("onyx.db.tools", "get_tools")

                with get_session() as db_session:
                    tools = get_tools(db_session)
                    rows: list[dict[str, Any]] = []
                    for tool in tools:
                        enabled = bool(getattr(tool, "enabled", False))
                        rows.append(
                            {
                                "id": getattr(tool, "id", "unknown"),
                                "name": getattr(tool, "display_name", None)
                                or getattr(tool, "name", "unknown_tool"),
                                "status": "enabled" if enabled else "disabled",
                                "risk_tier": self._derive_risk_tier(tool),
                                "enabled": enabled,
                            }
                        )
                    return rows
        except Exception:
            # UNCONFIRMED: canonical runtime hook not validated in this workspace.
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
            with _with_backend_on_path(self.onyx_root):
                get_session = _runtime_import("onyx.db.engine.sql_engine", "get_session")
                get_all_mcp_servers = _runtime_import("onyx.db.mcp", "get_all_mcp_servers")
                func = _runtime_import("sqlalchemy", "func")
                ToolCall = _runtime_import("onyx.db.models", "ToolCall")
                Tool = _runtime_import("onyx.db.models", "Tool")

                with get_session() as db_session:
                    servers = get_all_mcp_servers(db_session)
                    rows: list[dict[str, Any]] = []
                    for server in servers:
                        usage_count = (
                            db_session.query(func.count(ToolCall.id))
                            .join(Tool, ToolCall.tool_id == Tool.id)
                            .filter(Tool.mcp_server_id == getattr(server, "id", -1))
                            .scalar()
                        )
                        rows.append(
                            {
                                "id": getattr(server, "id", "unknown"),
                                "name": getattr(server, "name", "unknown_mcp_server"),
                                "status": _stringify_enumish(getattr(server, "status", "unknown"), lowercase=True),
                                "endpoint": getattr(server, "server_url", ""),
                                "usage_count": _safe_int(usage_count, 0),
                            }
                        )
                    return rows
        except Exception:
            # UNCONFIRMED: canonical runtime hook not validated in this workspace.
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
    Partially Implemented: static/config-backed Onyx eval inventory fallback when runtime modules are available.
    Unconfirmed: canonical multi-provider Onyx eval output compatibility for all fields.
    """

    def _read_from_onyx_runtime_config(self) -> list[dict[str, Any]]:
        """Best-effort read of eval metadata from Onyx runtime config.

        Unconfirmed: canonical runtime hook not validated in this workspace.
        Next-step verification: inspect live Onyx eval run persistence for this deployment.
        """

        try:
            with _with_backend_on_path(self.onyx_root):
                dataset_names = _runtime_import("onyx.configs.app_configs", "SCHEDULED_EVAL_DATASET_NAMES")
                project_name = _runtime_import("onyx.configs.app_configs", "SCHEDULED_EVAL_PROJECT")
        except Exception:
            return []

        rows: list[dict[str, Any]] = []
        for index, dataset in enumerate(dataset_names or [], start=1):
            if not dataset:
                continue
            scenario = str(dataset)
            suite = f"{project_name}:{scenario}" if project_name else scenario
            rows.append(
                {
                    "id": f"scheduled-eval-{index}",
                    "suite": suite,
                    "passed": False,
                    "scenario": scenario,
                    "score": 0,
                }
            )
        return rows

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", "evals")
        rows = self._read_json_records(path)
        if not rows:
            rows = self._read_from_onyx_runtime_config()
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
    Partially Implemented: optional ChatSession/ToolCall-derived events from Onyx DB.
    Unconfirmed: canonical Onyx lifecycle/retrieval/tool decision stream parity across deployments.
    """

    def _read_from_onyx_db(self) -> list[dict[str, Any]]:
        try:
            with _with_backend_on_path(self.onyx_root):
                get_session = _runtime_import("onyx.db.engine.sql_engine", "get_session")
                ChatSession = _runtime_import("onyx.db.models", "ChatSession")
                ToolCall = _runtime_import("onyx.db.models", "ToolCall")
                Tool = _runtime_import("onyx.db.models", "Tool")

                with get_session() as db_session:
                    sessions = db_session.query(ChatSession).order_by(ChatSession.time_updated.desc()).limit(100).all()
                    tool_calls = db_session.query(ToolCall).order_by(ToolCall.id.desc()).limit(200).all()
                    tool_name_by_id = {
                        getattr(tool, "id", -1): str(getattr(tool, "name", "unknown_tool"))
                        for tool in db_session.query(Tool).all()
                    }

                rows: list[dict[str, Any]] = []
                for session in sessions:
                    session_id = str(getattr(session, "id", "unknown-trace"))
                    actor_id = str(getattr(session, "user_id", "unknown-user"))
                    created_at = _iso_timestamp(getattr(session, "time_created", None))
                    updated_at = _iso_timestamp(getattr(session, "time_updated", None))

                    start_event: dict[str, Any] = {
                        "event_id": f"chat-session-start-{session_id}",
                        "trace_id": session_id,
                        "request_id": session_id,
                        "event_type": "request.start",
                        "actor_id": actor_id,
                        "tenant_id": "unknown-tenant",
                        "event_payload": {"source": "chat_session"},
                    }
                    if created_at:
                        start_event["created_at"] = created_at
                    rows.append(start_event)

                    end_event: dict[str, Any] = {
                        "event_id": f"chat-session-end-{session_id}",
                        "trace_id": session_id,
                        "request_id": session_id,
                        "event_type": "request.end",
                        "actor_id": actor_id,
                        "tenant_id": "unknown-tenant",
                        "event_payload": {"source": "chat_session"},
                    }
                    if updated_at:
                        end_event["created_at"] = updated_at
                    rows.append(end_event)

                for call in tool_calls:
                    chat_session_id = str(getattr(call, "chat_session_id", "unknown-trace"))
                    tool_id = getattr(call, "tool_id", -1)
                    rows.append(
                        {
                            "event_id": f"tool-call-{getattr(call, 'id', 'unknown')}",
                            "trace_id": chat_session_id,
                            "request_id": chat_session_id,
                            "event_type": "tool.execution_attempt",
                            "actor_id": "tool-runtime",
                            "tenant_id": "unknown-tenant",
                            "event_payload": {
                                "tool_id": tool_id,
                                "tool_name": tool_name_by_id.get(tool_id, "unknown_tool"),
                                "call_id": str(getattr(call, "tool_call_id", "")),
                            },
                        }
                    )
                return rows
        except Exception:
            # UNCONFIRMED: canonical runtime hook not validated in this workspace.
            return []

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", "runtime_events")
        rows = self._read_jsonl_records(path)
        if not rows:
            rows = self._read_from_onyx_db()
        events = [map_runtime_event(row) for row in rows if isinstance(row, dict)]
        valid: list[dict[str, Any]] = []
        for event in events:
            try:
                payload = event.to_dict()
            except ValueError:
                continue
            valid.append(payload)
        return valid
