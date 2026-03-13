from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from integration_adapter.launch_gate_evaluator import (
    CONDITIONAL_GO,
    GO,
    NO_GO,
    LaunchGateEvaluator,
)


def _seed_base_artifacts(root):
    (root / "replay").mkdir(parents=True, exist_ok=True)
    (root / "evals").mkdir(parents=True, exist_ok=True)
    (root / "launch_gate").mkdir(parents=True, exist_ok=True)
    (root / "adapter_health").mkdir(parents=True, exist_ok=True)

    (root / "artifact_bundle.contract.json").write_text(
        json.dumps(
            {
                "artifact_bundle_schema_version": "1.0",
                "normalized_schema_version": "1.0",
                "source_schema_version": "1.0",
                "launch_gate_schema_version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    (root / "adapter_health" / "adapter_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "success",
                "metrics": {
                    "parse_failures": 0,
                    "partial_extraction_warnings": 0,
                    "fallback_usage_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "connectors.inventory.json").write_text(
        json.dumps(
            [
                {
                    "domain": "connectors",
                    "record_id": "con-1",
                    "name": "confluence",
                    "status": "active",
                    "metadata": {
                        "source_type": "wiki",
                        "indexed": True,
                        "normalized_schema_version": "1.0",
                        "source_mode": "file_backed",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    (root / "tools.inventory.json").write_text(
        json.dumps(
            [
                {
                    "domain": "tools",
                    "record_id": "tool-1",
                    "name": "search",
                    "status": "enabled",
                    "metadata": {
                        "risk_tier": "low",
                        "enabled": True,
                        "normalized_schema_version": "1.0",
                        "source_mode": "file_backed",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    (root / "mcp_servers.inventory.json").write_text(
        json.dumps(
            [
                {
                    "domain": "mcp_servers",
                    "record_id": "mcp-1",
                    "name": "ops",
                    "status": "connected",
                    "metadata": {
                        "endpoint": "https://mcp.local",
                        "usage_count": 1,
                        "source_mode": "file_backed",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    (root / "evals.inventory.json").write_text(
        json.dumps(
            [
                {
                    "domain": "evals",
                    "record_id": "eval-1",
                    "name": "security",
                    "status": "pass",
                    "metadata": {
                        "score": 1.0,
                        "scenario": "prompt_injection_direct",
                        "source_mode": "file_backed",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )



    (root / "artifact_integrity.manifest.json").write_text(
        json.dumps(
            {
                "integrity_manifest_schema_version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "artifact_count": 7,
                "artifacts": [
                    {"path": "artifact_bundle.contract.json", "sha256": "placeholder", "size_bytes": 1},
                    {"path": "audit.jsonl", "sha256": "placeholder", "size_bytes": 1},
                    {"path": "connectors.inventory.json", "sha256": "placeholder", "size_bytes": 1},
                    {"path": "tools.inventory.json", "sha256": "placeholder", "size_bytes": 1},
                    {"path": "mcp_servers.inventory.json", "sha256": "placeholder", "size_bytes": 1},
                    {"path": "evals.inventory.json", "sha256": "placeholder", "size_bytes": 1},
                    {"path": "adapter_health/adapter_run_summary.json", "sha256": "placeholder", "size_bytes": 1},
                ],
            }
        ),
        encoding="utf-8",
    )

    audit_rows = [
        {
            "event_type": "request.start",
            "normalized_schema_version": "1.0",
            "actor_id": "u1",
            "tenant_id": "t1",
            "authz_result": "allow",
            "resource_scope": "chat",
            "decision_basis": "policy",
            "identity_authz_field_sources": {
                "actor_id": "sourced",
                "tenant_id": "sourced",
                "session_id": "sourced",
                "persona_or_agent_id": "sourced",
                "tool_invocation_id": "sourced",
                "delegation_chain": "sourced",
                "decision_basis": "sourced",
                "resource_scope": "sourced",
                "authz_result": "sourced",
            },
        },
        {
            "event_type": "policy.decision",
            "normalized_schema_version": "1.0",
            "actor_id": "policy",
            "tenant_id": "t1",
            "authz_result": "allow",
            "resource_scope": "chat",
            "decision_basis": "policy",
            "identity_authz_field_sources": {
                "actor_id": "sourced",
                "tenant_id": "sourced",
                "session_id": "sourced",
                "persona_or_agent_id": "sourced",
                "tool_invocation_id": "sourced",
                "delegation_chain": "sourced",
                "decision_basis": "sourced",
                "resource_scope": "sourced",
                "authz_result": "sourced",
            },
        },
        {
            "event_type": "request.end",
            "normalized_schema_version": "1.0",
            "actor_id": "orch",
            "tenant_id": "t1",
            "authz_result": "allow",
            "resource_scope": "chat",
            "decision_basis": "policy",
            "identity_authz_field_sources": {
                "actor_id": "sourced",
                "tenant_id": "sourced",
                "session_id": "sourced",
                "persona_or_agent_id": "sourced",
                "tool_invocation_id": "sourced",
                "delegation_chain": "sourced",
                "decision_basis": "sourced",
                "resource_scope": "sourced",
                "authz_result": "sourced",
            },
        },
    ]
    (root / "audit.jsonl").write_text("\n".join(json.dumps(row) for row in audit_rows), encoding="utf-8")
    (root / "replay" / "trace-1.replay.json").write_text(json.dumps({"trace_id": "trace-1", "events": []}), encoding="utf-8")
    (root / "evals" / "suite.jsonl").write_text(
        json.dumps({"scenario_id": "prompt_injection_direct", "outcome": "pass", "severity": "medium", "normalized_schema_version": "1.0"}) + "\n",
        encoding="utf-8",
    )
    (root / "evals" / "suite.summary.json").write_text(
        json.dumps({"suite_name": "suite", "passed": True, "total": 1, "passed_count": 1}),
        encoding="utf-8",
    )

    manifest_path = root / "artifact_integrity.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        target = root / artifact["path"]
        artifact["size_bytes"] = target.stat().st_size
        import hashlib

        digest = hashlib.sha256()
        with target.open("rb") as handle:
            digest.update(handle.read())
        artifact["sha256"] = digest.hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")




def _refresh_integrity_manifest(root) -> None:
    import hashlib

    manifest_path = root / "artifact_integrity.manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in payload.get("artifacts", []):
        rel = artifact.get("path")
        if not isinstance(rel, str):
            continue
        target = root / rel
        if not target.exists():
            continue
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            while True:
                chunk = handle.read(65536)
                if not chunk:
                    break
                digest.update(chunk)
        artifact["sha256"] = digest.hexdigest()
        artifact["size_bytes"] = target.stat().st_size
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def test_launch_gate_evaluator_pass(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()
    json_path, md_path = evaluator.write_outputs(result)

    assert result.status == GO
    assert not result.blockers
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["evidence_status"]["present"] is True
    assert payload["evidence_status"]["incomplete"] is False
    assert payload["decision_breakdown"]["blocker_count"] == 0
    assert payload["decision_breakdown"]["warning_count"] == 0
    assert "control_proven: **False**" in md_path.read_text(encoding="utf-8")


def test_launch_gate_evaluator_warn_for_degraded_source_mode_and_health(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    connectors = json.loads((root / "connectors.inventory.json").read_text(encoding="utf-8"))
    connectors[0]["metadata"]["source_mode"] = "synthetic"
    (root / "connectors.inventory.json").write_text(json.dumps(connectors), encoding="utf-8")

    (root / "adapter_health" / "adapter_run_summary.json").write_text(
        json.dumps({"run_status": "degraded_success", "metrics": {"parse_failures": 1, "partial_extraction_warnings": 2}}),
        encoding="utf-8",
    )
    _refresh_integrity_manifest(root)

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == CONDITIONAL_GO
    assert any("source_mode_quality" in item for item in result.residual_risks)
    assert any("adapter_health_summary" in item for item in result.residual_risks)


def test_launch_gate_evaluator_fail_on_stale_critical_evidence(tmp_path, monkeypatch) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    old = datetime.now(timezone.utc) - timedelta(days=4)
    old_epoch = old.timestamp()
    for path in [root / "artifact_bundle.contract.json", root / "audit.jsonl", root / "evals" / "suite.summary.json"]:
        path.touch()
        os_utime = __import__("os").utime
        os_utime(path, (old_epoch, old_epoch))

    monkeypatch.setenv("INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS", "60")

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("evidence_freshness" in item for item in result.blockers)


def test_launch_gate_evaluator_fail_on_incompatible_contract(tmp_path, monkeypatch) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)
    (root / "artifact_bundle.contract.json").write_text(
        json.dumps(
            {
                "artifact_bundle_schema_version": "2.0",
                "normalized_schema_version": "1.0",
                "source_schema_version": "1.0",
                "launch_gate_schema_version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTEGRATION_ADAPTER_EXPECTED_ARTIFACT_BUNDLE_SCHEMA_VERSION", "1.0")

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("artifact_contract_versions" in item for item in result.blockers)


def test_launch_gate_evaluator_warn_on_mapping_incompleteness(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)
    (root / "evals" / "suite.jsonl").write_text(
        "\n".join([
            json.dumps({"scenario_id": "prompt_injection_direct", "outcome": "pass", "severity": "medium", "normalized_schema_version": "1.0"}),
            json.dumps({"scenario_id": "unknown_scenario", "outcome": "pass", "severity": "medium", "normalized_schema_version": "1.0"}),
        ]) + "\n",
        encoding="utf-8",
    )

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == CONDITIONAL_GO
    assert any("threat_control_mapping_completeness" in item for item in result.residual_risks)


def test_launch_gate_evaluator_fail_on_identity_authz_absence(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)
    (root / "audit.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_type": "request.start", "normalized_schema_version": "1.0", "authz_result": "unavailable", "resource_scope": "unavailable", "decision_basis": "unavailable"}),
                json.dumps({"event_type": "policy.decision", "normalized_schema_version": "1.0", "authz_result": "unavailable", "resource_scope": "unavailable", "decision_basis": "unavailable"}),
                json.dumps({"event_type": "request.end", "normalized_schema_version": "1.0", "authz_result": "unavailable", "resource_scope": "unavailable", "decision_basis": "unavailable"}),
            ]
        ),
        encoding="utf-8",
    )

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("identity_authz_evidence_presence" in item for item in result.blockers)


def test_launch_gate_evaluator_warn_on_partial_authz_provenance(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    rows = [json.loads(line) for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["identity_authz_field_sources"]["decision_basis"] = "unavailable"
    rows[1]["identity_authz_field_sources"]["session_id"] = "derived"
    (root / "audit.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    _refresh_integrity_manifest(root)

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == CONDITIONAL_GO
    assert any("identity_authz_provenance_quality" in item for item in result.residual_risks)


def test_launch_gate_evaluator_warn_on_derived_only_authz_provenance(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    rows = [json.loads(line) for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        row["identity_authz_field_sources"] = {
            "actor_id": "derived",
            "tenant_id": "derived",
            "session_id": "derived",
            "persona_or_agent_id": "derived",
            "tool_invocation_id": "derived",
            "delegation_chain": "derived",
            "decision_basis": "derived",
            "resource_scope": "derived",
            "authz_result": "derived",
        }
    (root / "audit.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    _refresh_integrity_manifest(root)

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == CONDITIONAL_GO
    assert any("identity_authz_provenance_quality" in item for item in result.residual_risks)


def test_launch_gate_evaluator_fail_on_missing_critical_authz_provenance(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    rows = [json.loads(line) for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        row["identity_authz_field_sources"] = {
            "actor_id": "unavailable",
            "tenant_id": "unavailable",
            "session_id": "unavailable",
            "persona_or_agent_id": "unavailable",
            "tool_invocation_id": "unavailable",
            "delegation_chain": "unavailable",
            "decision_basis": "unavailable",
            "resource_scope": "unavailable",
            "authz_result": "unavailable",
        }
    (root / "audit.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    _refresh_integrity_manifest(root)

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("identity_authz_provenance_quality" in item for item in result.blockers)


def test_launch_gate_evaluator_warn_on_missing_mcp_classification(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    mcp = json.loads((root / "mcp_servers.inventory.json").read_text(encoding="utf-8"))
    mcp[0]["status"] = "unknown"
    (root / "mcp_servers.inventory.json").write_text(json.dumps(mcp), encoding="utf-8")
    _refresh_integrity_manifest(root)

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == CONDITIONAL_GO
    assert any("mcp_inventory_classified" in item for item in result.residual_risks)


def test_launch_gate_evaluator_fail_on_partial_exporter_failure_signal(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    (root / "adapter_health" / "adapter_run_summary.json").write_text(
        json.dumps({"run_status": "degraded_success", "metrics": {"parse_failures": 3, "partial_extraction_warnings": 5, "fallback_usage_count": 1}}),
        encoding="utf-8",
    )

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("exporter_degradation" in item for item in result.blockers)


def test_launch_gate_evaluator_fail_on_contract_audit_tampering_signal(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    rows = [json.loads(line) for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["normalized_schema_version"] = "9.9"
    (root / "audit.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("evidence_tampering_signals" in item for item in result.blockers)


def test_launch_gate_evaluator_fail_when_integrity_manifest_missing(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)
    (root / "artifact_integrity.manifest.json").unlink()

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("artifact_integrity_manifest" in item for item in result.blockers)
