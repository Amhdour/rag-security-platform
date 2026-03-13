from __future__ import annotations

import json
from pathlib import Path

from integration_adapter.config import AdapterConfig
from integration_adapter.validate_config import validate_configuration


def test_validate_configuration_non_strict_passes_without_source_env(monkeypatch, tmp_path) -> None:
    for name in [
        "INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON",
        "INTEGRATION_ADAPTER_ONYX_TOOLS_JSON",
        "INTEGRATION_ADAPTER_ONYX_MCP_JSON",
        "INTEGRATION_ADAPTER_ONYX_EVALS_JSON",
        "INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL",
    ]:
        monkeypatch.delenv(name, raising=False)

    report = validate_configuration(config=AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"))

    assert report.status == "pass"
    assert any(issue.level == "warning" for issue in report.issues)


def test_validate_configuration_strict_fails_when_source_env_missing(monkeypatch, tmp_path) -> None:
    for name in [
        "INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON",
        "INTEGRATION_ADAPTER_ONYX_TOOLS_JSON",
        "INTEGRATION_ADAPTER_ONYX_MCP_JSON",
        "INTEGRATION_ADAPTER_ONYX_EVALS_JSON",
        "INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL",
    ]:
        monkeypatch.delenv(name, raising=False)

    report = validate_configuration(
        config=AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"),
        strict_sources=True,
    )

    assert report.status == "fail"
    assert any("required in strict source mode" in issue.message for issue in report.issues)


def test_validate_configuration_strict_fails_on_malformed_source_file(monkeypatch, tmp_path) -> None:
    connectors = tmp_path / "connectors.json"
    connectors.write_text("{invalid-json", encoding="utf-8")
    tools = tmp_path / "tools.json"
    tools.write_text("[]", encoding="utf-8")
    mcp = tmp_path / "mcp.json"
    mcp.write_text("[]", encoding="utf-8")
    evals = tmp_path / "evals.json"
    evals.write_text("[]", encoding="utf-8")
    events = tmp_path / "runtime_events.jsonl"
    events.write_text('{"event_id":"1"}\n', encoding="utf-8")

    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON", str(connectors))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_TOOLS_JSON", str(tools))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_MCP_JSON", str(mcp))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_EVALS_JSON", str(evals))
    monkeypatch.setenv("INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL", str(events))

    report = validate_configuration(
        config=AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"),
        strict_sources=True,
    )

    assert report.status == "fail"
    errors = [issue.message for issue in report.issues if issue.level == "error"]
    assert any("failed to parse json" in msg for msg in errors)

    payload = report.to_dict()
    assert json.loads(json.dumps(payload))["status"] == "fail"


def test_validate_configuration_fails_on_unknown_profile(tmp_path) -> None:
    report = validate_configuration(
        config=AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs", profile="unknown-profile"),
        strict_sources=False,
    )

    assert report.status == "fail"
    assert any(issue.field == "INTEGRATION_ADAPTER_PROFILE" for issue in report.issues)


def test_validate_configuration_fails_when_signed_mode_missing_key(tmp_path) -> None:
    report = validate_configuration(
        config=AdapterConfig(
            artifacts_root=tmp_path / "artifacts" / "logs",
            profile="dev",
            integrity_mode="signed_manifest",
            integrity_signing_key=None,
            integrity_signing_key_path=None,
        ),
        strict_sources=False,
    )

    assert report.status == "fail"
    assert any(issue.field == "INTEGRITY_SIGNING_KEY" for issue in report.issues)


def test_validate_configuration_passes_when_signed_mode_has_key_file(tmp_path) -> None:
    key = tmp_path / "signing.key"
    key.write_text("dev-secret", encoding="utf-8")

    report = validate_configuration(
        config=AdapterConfig(
            artifacts_root=tmp_path / "artifacts" / "logs",
            profile="dev",
            integrity_mode="signed_manifest",
            integrity_signing_key_path=key,
        ),
        strict_sources=False,
    )

    assert report.status == "pass"
