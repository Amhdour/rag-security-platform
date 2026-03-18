from __future__ import annotations

import json
from pathlib import Path

from integration_adapter.adversarial_harness import Scenario, evaluate_scenario


def test_retrieval_poisoning_fixture_docs_exist() -> None:
    base = Path(__file__).parent / "fixtures" / "adversarial" / "retrieval_poisoning"
    required = [
        "doc_malicious_instruction.md",
        "doc_authoritative_misleading.md",
        "doc_hidden_override.md",
        "doc_context_conflict.md",
        "doc_integrity_downgrade.md",
    ]
    for filename in required:
        assert (base / filename).exists(), f"missing fixture doc: {filename}"


def test_retrieval_poisoning_scenarios_score_expected_controls() -> None:
    path = Path(__file__).parent / "fixtures" / "adversarial" / "retrieval_poisoning" / "scenarios.json"
    rows = json.loads(path.read_text(encoding="utf-8"))

    for row in rows:
        scenario = Scenario(
            scenario_id=row["scenario_id"],
            category=row["category"],
            description=row["description"],
            threat=row["threat"],
            expected_control_behavior=row["expected_control_behavior"],
            payload=row["payload"],
        )
        result = evaluate_scenario(scenario)
        assert result["score"] == row["expected_score"]
        assert result["threat"]
        assert result["expected_control_behavior"]
