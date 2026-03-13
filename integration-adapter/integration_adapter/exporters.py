from __future__ import annotations

"""Exporters for Onyx-facing runtime surfaces.

Status labels used in this module:
- Implemented: file-backed JSON/JSONL extraction and mapper-based normalization.
- Partially Implemented: optional direct Onyx DB reads when runtime imports/session are available.
- Unconfirmed: canonical production hook parity across all deployments is not asserted here.

Design:
- raw extraction is read-only and best-effort;
- normalization is delegated to mapper functions;
- Implemented: fallback usage and malformed-source handling are explicit via acquisition diagnostics.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import importlib
import os
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

SOURCE_MODE_LIVE = "live"
SOURCE_MODE_DB_BACKED = "db_backed"
SOURCE_MODE_FILE_BACKED = "file_backed"
SOURCE_MODE_FIXTURE_BACKED = "fixture_backed"
SOURCE_MODE_SYNTHETIC = "synthetic"


def _to_rows(records: list[Any]) -> list[dict[str, Any]]:
    return [record for record in records if isinstance(record, dict)]


def _safe_validate_inventory_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    validated: list[dict[str, Any]] = []
    dropped_non_dict = 0
    for row in rows:
        if not isinstance(row, dict):
            dropped_non_dict += 1
            continue
        name = str(row.get("name", "unknown"))
        validated.append(
            {
                "id": str(row.get("id", row.get("record_id", name))),
                "name": name,
                "status": str(row.get("status", "unknown")),
                **row,
            }
        )
    return validated, dropped_non_dict


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


def _classify_path_source_mode(path: Path) -> str:
    lowered = str(path).lower()
    if any(marker in lowered for marker in ("fixture", "fixtures", "sample", "demo")):
        return SOURCE_MODE_FIXTURE_BACKED
    return SOURCE_MODE_FILE_BACKED


def _db_source_mode() -> str:
    if os.getenv("INTEGRATION_ADAPTER_DB_SOURCE_MODE_LIVE", "").strip().lower() in {"1", "true", "yes"}:
        return SOURCE_MODE_LIVE
    return SOURCE_MODE_DB_BACKED


@dataclass(frozen=True)
class AcquisitionResult:
    rows: list[dict[str, Any]]
    source_mode: str
    source_path: str
    used_fallback: bool
    warnings: list[str]
    errors: list[str]


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
    last_acquisition: AcquisitionResult | None = field(default=None, init=False)

    def _source_path(self, env_name: str, default_key: str) -> Path:
        discovered = discover_default_paths(self.onyx_root)
        return env_path(env_name) or discovered[default_key]

    def _read_json_records(self, path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        if not path.exists():
            return [], [f"source file does not exist: {path}"], []
        try:
            rows = load_json_records(path)
            return rows, [], []
        except SourceReadError as exc:
            return [], [], [f"malformed json source at {path}: {exc}"]

    def _read_jsonl_records(self, path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        if not path.exists():
            return [], [f"source file does not exist: {path}"], []
        try:
            rows = load_jsonl_records(path)
            return rows, [], []
        except (OSError, SourceReadError) as exc:
            return [], [], [f"malformed jsonl source at {path}: {exc}"]

    def _record_acquisition(self, result: AcquisitionResult) -> None:
        self.last_acquisition = result

    def _attach_source_metadata(
        self,
        rows: list[dict[str, Any]],
        *,
        source_mode: str,
        source_path: str,
        used_fallback: bool,
        warnings: list[str],
        errors: list[str],
        required_fields: list[str],
    ) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for row in rows:
            derived_fields = sorted([key for key in required_fields if key not in row or row.get(key) in (None, "")])
            enriched.append(
                {
                    **row,
                    "source_mode": source_mode,
                    "source_path": source_path,
                    "fallback_used": used_fallback,
                    "source_warnings": list(warnings),
                    "source_errors": list(errors),
                    "derived_fields": derived_fields,
                }
            )
        return enriched


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

    def _read_from_onyx_db(self) -> tuple[list[dict[str, Any]], list[str], list[str]]:
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
                    return rows, [], []
        except Exception as exc:
            return [], [], [f"db extraction failed for connectors: {exc}"]

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", "connectors")
        file_rows, file_warnings, file_errors = self._read_json_records(path)
        source_mode = _classify_path_source_mode(path)
        used_fallback = False

        rows = file_rows
        warnings = list(file_warnings)
        errors = list(file_errors)
        source_path = str(path)

        if not rows:
            db_rows, db_warnings, db_errors = self._read_from_onyx_db()
            warnings.extend(db_warnings)
            errors.extend(db_errors)
            if db_rows:
                rows = db_rows
                source_mode = _db_source_mode()
                source_path = "onyx.db.connector.fetch_connectors"
                used_fallback = True

        valid_rows, dropped = _safe_validate_inventory_rows(_to_rows(rows))
        if dropped:
            warnings.append(f"dropped non-dict connector rows: {dropped}")

        enriched = self._attach_source_metadata(
            valid_rows,
            source_mode=source_mode if valid_rows else SOURCE_MODE_SYNTHETIC,
            source_path=source_path,
            used_fallback=used_fallback,
            warnings=warnings,
            errors=errors,
            required_fields=["id", "name", "status", "source_type", "indexed"],
        )
        self._record_acquisition(
            AcquisitionResult(
                rows=enriched,
                source_mode=source_mode if enriched else SOURCE_MODE_SYNTHETIC,
                source_path=source_path,
                used_fallback=used_fallback,
                warnings=warnings,
                errors=errors,
            )
        )

        normalized = map_connector_inventory(enriched)
        return [
            {
                "id": row.record_id,
                "name": row.name,
                "status": row.status,
                "source_type": row.metadata.get("source_type", "unknown"),
                "indexed": bool(row.metadata.get("indexed", False)),
                "source_mode": row.metadata.get("source_mode", SOURCE_MODE_SYNTHETIC),
                "fallback_used": bool(row.metadata.get("fallback_used", False)),
                "source_warnings": row.metadata.get("source_warnings", []),
                "source_errors": row.metadata.get("source_errors", []),
                "derived_fields": row.metadata.get("derived_fields", []),
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

    def _read_from_onyx_db(self) -> tuple[list[dict[str, Any]], list[str], list[str]]:
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
                                "name": getattr(tool, "display_name", None) or getattr(tool, "name", "unknown_tool"),
                                "status": "enabled" if enabled else "disabled",
                                "risk_tier": self._derive_risk_tier(tool),
                                "enabled": enabled,
                            }
                        )
                    return rows, [], []
        except Exception as exc:
            return [], [], [f"db extraction failed for tools: {exc}"]

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", "tools")
        file_rows, file_warnings, file_errors = self._read_json_records(path)
        rows = file_rows
        warnings = list(file_warnings)
        errors = list(file_errors)
        source_mode = _classify_path_source_mode(path)
        source_path = str(path)
        used_fallback = False

        if not rows:
            db_rows, db_warnings, db_errors = self._read_from_onyx_db()
            warnings.extend(db_warnings)
            errors.extend(db_errors)
            if db_rows:
                rows = db_rows
                source_mode = _db_source_mode()
                source_path = "onyx.db.tools.get_tools"
                used_fallback = True

        valid_rows, dropped = _safe_validate_inventory_rows(_to_rows(rows))
        if dropped:
            warnings.append(f"dropped non-dict tool rows: {dropped}")
        enriched = self._attach_source_metadata(
            valid_rows,
            source_mode=source_mode if valid_rows else SOURCE_MODE_SYNTHETIC,
            source_path=source_path,
            used_fallback=used_fallback,
            warnings=warnings,
            errors=errors,
            required_fields=["id", "name", "status", "risk_tier", "enabled"],
        )
        self._record_acquisition(
            AcquisitionResult(
                rows=enriched,
                source_mode=source_mode if enriched else SOURCE_MODE_SYNTHETIC,
                source_path=source_path,
                used_fallback=used_fallback,
                warnings=warnings,
                errors=errors,
            )
        )

        normalized = map_tool_inventory(enriched)
        return [
            {
                "id": row.record_id,
                "name": row.name,
                "status": row.status,
                "risk_tier": row.metadata.get("risk_tier", "unspecified"),
                "enabled": bool(row.metadata.get("enabled", False)),
                "source_mode": row.metadata.get("source_mode", SOURCE_MODE_SYNTHETIC),
                "fallback_used": bool(row.metadata.get("fallback_used", False)),
                "source_warnings": row.metadata.get("source_warnings", []),
                "source_errors": row.metadata.get("source_errors", []),
                "derived_fields": row.metadata.get("derived_fields", []),
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

    def _read_from_onyx_db(self) -> tuple[list[dict[str, Any]], list[str], list[str]]:
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
                    return rows, [], []
        except Exception as exc:
            return [], [], [f"db extraction failed for mcp: {exc}"]

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_MCP_JSON", "mcp_servers")
        file_rows, file_warnings, file_errors = self._read_json_records(path)
        rows = file_rows
        warnings = list(file_warnings)
        errors = list(file_errors)
        source_mode = _classify_path_source_mode(path)
        source_path = str(path)
        used_fallback = False

        if not rows:
            db_rows, db_warnings, db_errors = self._read_from_onyx_db()
            warnings.extend(db_warnings)
            errors.extend(db_errors)
            if db_rows:
                rows = db_rows
                source_mode = _db_source_mode()
                source_path = "onyx.db.mcp.get_all_mcp_servers"
                used_fallback = True

        valid_rows, dropped = _safe_validate_inventory_rows(_to_rows(rows))
        if dropped:
            warnings.append(f"dropped non-dict mcp rows: {dropped}")
        enriched = self._attach_source_metadata(
            valid_rows,
            source_mode=source_mode if valid_rows else SOURCE_MODE_SYNTHETIC,
            source_path=source_path,
            used_fallback=used_fallback,
            warnings=warnings,
            errors=errors,
            required_fields=["id", "name", "status", "endpoint", "usage_count"],
        )
        self._record_acquisition(
            AcquisitionResult(
                rows=enriched,
                source_mode=source_mode if enriched else SOURCE_MODE_SYNTHETIC,
                source_path=source_path,
                used_fallback=used_fallback,
                warnings=warnings,
                errors=errors,
            )
        )

        normalized = map_mcp_inventory(enriched)
        return [
            {
                "id": row.record_id,
                "name": row.name,
                "status": row.status,
                "endpoint": row.metadata.get("endpoint", ""),
                "usage_count": int(row.metadata.get("usage_count", 0)),
                "source_mode": row.metadata.get("source_mode", SOURCE_MODE_SYNTHETIC),
                "fallback_used": bool(row.metadata.get("fallback_used", False)),
                "source_warnings": row.metadata.get("source_warnings", []),
                "source_errors": row.metadata.get("source_errors", []),
                "derived_fields": row.metadata.get("derived_fields", []),
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

    def _read_from_onyx_runtime_config(self) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        """Best-effort read of eval metadata from Onyx runtime config.

        Unconfirmed: canonical runtime hook not validated in this workspace.
        Next-step verification: inspect live Onyx eval run persistence for this deployment.
        """

        try:
            with _with_backend_on_path(self.onyx_root):
                dataset_names = _runtime_import("onyx.configs.app_configs", "SCHEDULED_EVAL_DATASET_NAMES")
                project_name = _runtime_import("onyx.configs.app_configs", "SCHEDULED_EVAL_PROJECT")
        except Exception as exc:
            return [], [], [f"runtime config extraction failed for evals: {exc}"]

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
        return rows, [], []

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", "evals")
        file_rows, file_warnings, file_errors = self._read_json_records(path)
        rows = file_rows
        warnings = list(file_warnings)
        errors = list(file_errors)
        source_mode = _classify_path_source_mode(path)
        source_path = str(path)
        used_fallback = False

        if not rows:
            cfg_rows, cfg_warnings, cfg_errors = self._read_from_onyx_runtime_config()
            warnings.extend(cfg_warnings)
            errors.extend(cfg_errors)
            if cfg_rows:
                rows = cfg_rows
                source_mode = SOURCE_MODE_DB_BACKED
                source_path = "onyx.configs.app_configs"
                used_fallback = True

        valid_rows, dropped = _safe_validate_inventory_rows(_to_rows(rows))
        if dropped:
            warnings.append(f"dropped non-dict eval rows: {dropped}")

        enriched = self._attach_source_metadata(
            valid_rows,
            source_mode=source_mode if valid_rows else SOURCE_MODE_SYNTHETIC,
            source_path=source_path,
            used_fallback=used_fallback,
            warnings=warnings,
            errors=errors,
            required_fields=["id", "suite", "passed", "score", "scenario"],
        )
        self._record_acquisition(
            AcquisitionResult(
                rows=enriched,
                source_mode=source_mode if enriched else SOURCE_MODE_SYNTHETIC,
                source_path=source_path,
                used_fallback=used_fallback,
                warnings=warnings,
                errors=errors,
            )
        )

        normalized = map_eval_inventory(enriched)
        return [
            {
                "id": row.record_id,
                "suite": row.name,
                "passed": row.status == "pass",
                "score": row.metadata.get("score", 0),
                "scenario": row.metadata.get("scenario", "unspecified"),
                "source_mode": row.metadata.get("source_mode", SOURCE_MODE_SYNTHETIC),
                "fallback_used": bool(row.metadata.get("fallback_used", False)),
                "source_warnings": row.metadata.get("source_warnings", []),
                "source_errors": row.metadata.get("source_errors", []),
                "derived_fields": row.metadata.get("derived_fields", []),
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

    def _read_from_onyx_db(self) -> tuple[list[dict[str, Any]], list[str], list[str]]:
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
                return rows, [], []
        except Exception as exc:
            return [], [], [f"db extraction failed for runtime events: {exc}"]

    def export(self) -> list[dict[str, Any]]:
        path = self._source_path("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", "runtime_events")
        file_rows, file_warnings, file_errors = self._read_jsonl_records(path)
        rows = file_rows
        warnings = list(file_warnings)
        errors = list(file_errors)
        source_mode = _classify_path_source_mode(path)
        source_path = str(path)
        used_fallback = False

        if not rows:
            db_rows, db_warnings, db_errors = self._read_from_onyx_db()
            warnings.extend(db_warnings)
            errors.extend(db_errors)
            if db_rows:
                rows = db_rows
                source_mode = _db_source_mode()
                source_path = "onyx.db.models.ChatSession/ToolCall"
                used_fallback = True

        valid_dict_rows = _to_rows(rows)
        dropped = len(rows) - len(valid_dict_rows)
        if dropped:
            warnings.append(f"dropped non-dict runtime event rows: {dropped}")

        events = []
        invalid_events = 0
        for raw_row in valid_dict_rows:
            payload = dict(raw_row)
            event_payload = dict(payload.get("event_payload") or {})
            event_payload["source_mode"] = source_mode if valid_dict_rows else SOURCE_MODE_SYNTHETIC
            event_payload["source_path"] = source_path
            event_payload["fallback_used"] = used_fallback
            event_payload["source_warnings"] = list(warnings)
            event_payload["source_errors"] = list(errors)
            payload["event_payload"] = event_payload
            events.append(map_runtime_event(payload))

        valid: list[dict[str, Any]] = []
        for event in events:
            try:
                payload = event.to_dict()
            except ValueError:
                invalid_events += 1
                continue
            valid.append(payload)

        if invalid_events:
            warnings.append(f"dropped invalid mapped runtime events: {invalid_events}")

        self._record_acquisition(
            AcquisitionResult(
                rows=valid,
                source_mode=source_mode if valid else SOURCE_MODE_SYNTHETIC,
                source_path=source_path,
                used_fallback=used_fallback,
                warnings=warnings,
                errors=errors,
            )
        )
        return valid
