from __future__ import annotations

"""Placeholder exporters for Onyx runtime surfaces.

These exporters intentionally avoid importing Onyx internals directly.
They define stable interfaces for the integration adapter and can be
wired to concrete runtime hooks once canonical sources are confirmed.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ConnectorInventoryExporter:
    """Exports connector/indexed-source inventory from runtime state."""

    def export(self) -> list[dict[str, Any]]:
        # TODO(onyx-runtime-hook): confirm canonical Onyx source for connector inventory,
        # including how indexed/document_set status is represented per tenant.
        return []


@dataclass
class ToolInventoryExporter:
    """Exports tool inventory and policy-relevant metadata."""

    def export(self) -> list[dict[str, Any]]:
        # TODO(onyx-runtime-hook): confirm canonical Onyx source for tool inventory,
        # including builtin/custom tool IDs and enabled/visibility flags.
        return []


@dataclass
class MCPInventoryExporter:
    """Exports MCP server inventory and usage-oriented metadata."""

    def export(self) -> list[dict[str, Any]]:
        # TODO(onyx-runtime-hook): confirm canonical Onyx source for MCP server inventory,
        # auth/connection status fields, and usage counters.
        return []


@dataclass
class EvalResultsExporter:
    """Exports eval results for governance normalization."""

    def export(self) -> list[dict[str, Any]]:
        # TODO(onyx-runtime-hook): confirm canonical Onyx eval output format across
        # local/remote providers and how pass/fail aggregates should be derived.
        return []


@dataclass
class RuntimeEventsExporter:
    """Exports security-relevant runtime events for audit normalization."""

    def export(self) -> list[dict[str, Any]]:
        # TODO(onyx-runtime-hook): confirm canonical event feed for request lifecycle,
        # retrieval decisions, tool decisions/execution attempts, and deny/fallback events.
        return []
