from __future__ import annotations

import json
from pathlib import Path

from integration_adapter.config import AdapterConfig
from integration_adapter.exporters import (
    ConnectorInventoryExporter,
    EvalResultsExporter,
    MCPInventoryExporter,
    RuntimeEventsExporter,
    SOURCE_MODE_FIXTURE_BACKED,
    ToolInventoryExporter,
)
from integration_adapter.launch_gate_evaluator import CONDITIONAL_GO, NO_GO, LaunchGateEvaluator
from integration_adapter.pipeline import generate_artifacts


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "onyx_contracts"


def _set_fixture_env(monkeypatch, variant: str) -> None:
    base = FIXTURE_ROOT / variant
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", str(base / "connectors.json"))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", str(base / "tools.json"))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_MCP_JSON", str(base / "mcp.json"))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", str(base / "evals.json"))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", str(base / "runtime_events.jsonl"))


def test_fixture_manifest_is_well_formed() -> None:
    payload = json.loads((FIXTURE_ROOT / "fixture_manifest.json").read_text(encoding="utf-8"))
    assert payload["fixture_set_version"]
    assert payload["classification"]["pass"]["data_lineage"] == "real-derived"
    assert payload["classification"]["pass"]["sanitization"] == "sanitized"
    assert payload["classification"]["pass"]["contains_secrets"] is False


def test_exporters_are_compatible_with_real_derived_fixture_shapes(monkeypatch) -> None:
    _set_fixture_env(monkeypatch, "pass")

    connectors = ConnectorInventoryExporter().export()
    tools = ToolInventoryExporter().export()
    mcp = MCPInventoryExporter().export()
    evals = EvalResultsExporter().export()
    events = RuntimeEventsExporter().export()

    assert connectors and connectors[0]["source_mode"] == SOURCE_MODE_FIXTURE_BACKED
    assert tools and tools[0]["source_mode"] == SOURCE_MODE_FIXTURE_BACKED
    assert mcp and mcp[0]["source_mode"] == SOURCE_MODE_FIXTURE_BACKED
    assert evals and evals[0]["source_mode"] == SOURCE_MODE_FIXTURE_BACKED
    assert events and events[0]["event_payload"]["source_mode"] == SOURCE_MODE_FIXTURE_BACKED
    assert events[0]["event_type"]


def test_launch_gate_behavior_from_pass_fixture(monkeypatch, tmp_path) -> None:
    _set_fixture_env(monkeypatch, "pass")
    result = generate_artifacts(force_demo=False, config=AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"))

    evaluator = LaunchGateEvaluator(result.artifacts_root)
    evaluation = evaluator.evaluate()
    assert evaluation.status == CONDITIONAL_GO


def test_launch_gate_behavior_from_fail_fixture(monkeypatch, tmp_path) -> None:
    _set_fixture_env(monkeypatch, "fail")
    result = generate_artifacts(force_demo=False, config=AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"))

    evaluator = LaunchGateEvaluator(result.artifacts_root)
    evaluation = evaluator.evaluate()
    assert evaluation.status == NO_GO
    assert any("critical_failures_or_blockers" in blocker for blocker in evaluation.blockers)
