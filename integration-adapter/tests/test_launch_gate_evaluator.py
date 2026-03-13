from __future__ import annotations

import json

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

    (root / "connectors.inventory.json").write_text(
        json.dumps([
            {"domain": "connectors", "record_id": "con-1", "name": "confluence", "status": "active", "metadata": {"source_type": "wiki", "indexed": True}}
        ]),
        encoding="utf-8",
    )
    (root / "tools.inventory.json").write_text(
        json.dumps([
            {"domain": "tools", "record_id": "tool-1", "name": "search", "status": "enabled", "metadata": {"risk_tier": "low", "enabled": True}}
        ]),
        encoding="utf-8",
    )
    (root / "mcp_servers.inventory.json").write_text(
        json.dumps([
            {"domain": "mcp_servers", "record_id": "mcp-1", "name": "ops", "status": "connected", "metadata": {"endpoint": "https://mcp.local", "usage_count": 1}}
        ]),
        encoding="utf-8",
    )
    (root / "audit.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_type": "request.start"}),
                json.dumps({"event_type": "policy.decision"}),
                json.dumps({"event_type": "request.end"}),
            ]
        ),
        encoding="utf-8",
    )
    (root / "replay" / "trace-1.replay.json").write_text(json.dumps({"trace_id": "trace-1", "events": []}), encoding="utf-8")
    (root / "evals" / "suite.jsonl").write_text(
        json.dumps({"scenario_id": "s1", "outcome": "pass", "severity": "medium"}) + "\n",
        encoding="utf-8",
    )
    (root / "evals" / "suite.summary.json").write_text(
        json.dumps({"suite_name": "suite", "passed": True, "total": 1, "passed_count": 1}),
        encoding="utf-8",
    )


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
    assert payload["control_assessment"]["proven"] is False
    assert payload["control_assessment"]["not_proven"] is True
    assert payload["decision_breakdown"]["blocker_count"] == 0
    assert payload["decision_breakdown"]["warning_count"] == 0
    assert "control_proven: **False**" in md_path.read_text(encoding="utf-8")


def test_launch_gate_evaluator_warn(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    (root / "tools.inventory.json").write_text(
        json.dumps([
            {"domain": "tools", "record_id": "tool-1", "name": "search", "status": "enabled", "metadata": {"risk_tier": "unspecified", "enabled": True}}
        ]),
        encoding="utf-8",
    )

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == CONDITIONAL_GO
    assert result.residual_risks
    assert any("tool_inventory_classified" in item for item in result.residual_risks)

    _, md_path = evaluator.write_outputs(result)
    assert "Residual risks (warn)" in md_path.read_text(encoding="utf-8")


def test_launch_gate_evaluator_fail_on_critical_eval(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    (root / "evals" / "suite.jsonl").write_text(
        json.dumps({"scenario_id": "policy_bypass_attempt", "outcome": "fail", "severity": "critical"}) + "\n",
        encoding="utf-8",
    )
    (root / "evals" / "suite.summary.json").write_text(
        json.dumps({"suite_name": "suite", "passed": False, "total": 1, "passed_count": 0}),
        encoding="utf-8",
    )

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()
    json_path, md_path = evaluator.write_outputs(result)

    assert result.status == NO_GO
    assert result.blockers
    assert json_path.is_file()
    assert md_path.is_file()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["decision_breakdown"]["blocker_count"] >= 1


def test_launch_gate_evaluator_fail_closed_on_schema_malformed(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    _seed_base_artifacts(root)

    (root / "tools.inventory.json").write_text(
        json.dumps([
            {"domain": "tools", "record_id": "tool-1", "name": "search", "status": "enabled", "metadata": "invalid"}
        ]),
        encoding="utf-8",
    )

    evaluator = LaunchGateEvaluator(root)
    result = evaluator.evaluate()

    assert result.status == NO_GO
    assert any("artifact_schema_validity" in item for item in result.blockers)
