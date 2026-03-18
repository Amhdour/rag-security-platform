from __future__ import annotations

import json
from pathlib import Path

from integration_adapter.adversarial_harness import Scenario, evaluate_scenario


def test_output_leakage_fixture_docs_exist() -> None:
    base = Path(__file__).parent / "fixtures" / "adversarial" / "output_leakage"
    required = [
        "doc_direct_sensitive_disclosure.md",
        "doc_tool_result_leakage.md",
        "doc_policy_conflicting_output.md",
        "doc_unsafe_restricted_summary.md",
        "doc_context_carry_through.md",
    ]
    for filename in required:
        assert (base / filename).exists(), f"missing fixture doc: {filename}"


def test_output_leakage_scenarios_score_expected_controls() -> None:
    path = Path(__file__).parent / "fixtures" / "adversarial" / "output_leakage" / "scenarios.json"
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
