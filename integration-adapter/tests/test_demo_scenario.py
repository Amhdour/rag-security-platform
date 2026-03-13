from __future__ import annotations

import json

from integration_adapter.config import AdapterConfig
from integration_adapter.demo_scenario import run_demo_scenario


def test_demo_scenario_writes_expected_outputs(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    report = run_demo_scenario(config=config)

    outputs = report["outputs"]
    assert (tmp_path / "artifacts" / "logs" / "audit.jsonl").is_file()
    assert (tmp_path / "artifacts" / "logs" / "demo_scenario.report.json").is_file()
    assert outputs["replay_json"].endswith(".replay.json")
    assert outputs["launch_gate_json"].endswith(".json")
    assert outputs["launch_gate_markdown"].endswith(".md")
    assert report["missing_outputs"] == []


def test_demo_scenario_report_contains_real_vs_synthetic_map(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    report = run_demo_scenario(config=config)

    real_vs_synthetic = report["real_vs_synthetic"]
    assert set(real_vs_synthetic.keys()) == {
        "connectors",
        "tools",
        "mcp_inventory",
        "runtime_events",
        "eval_results",
    }
    assert set(real_vs_synthetic.values()).issubset({"real", "synthetic"})

    story_steps = report["story_steps"]
    assert len(story_steps) == 8
    assert story_steps[0]["step"] == "request enters runtime context"
    assert report["remaining_realism_gaps"]

    report_path = tmp_path / "artifacts" / "logs" / "demo_scenario.report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["scenario"] == "demo_e2e_runtime_to_governance"
    assert payload["synthetic_data"] in {True, False}
