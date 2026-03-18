from __future__ import annotations

import json
from pathlib import Path

from integration_adapter.launch_gate_bridge import build_bridge_verdict, render_markdown


def test_bridge_verdict_conditional_when_warn_present(tmp_path) -> None:
    artifacts = tmp_path / "artifacts"
    (artifacts / "evals").mkdir(parents=True, exist_ok=True)
    (artifacts / "launch_gate").mkdir(parents=True, exist_ok=True)

    (artifacts / "evals" / "run.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"scenario_id": "PI-001", "category": "prompt_injection", "score": "pass", "rationale": "malicious prompt blocked"}),
                json.dumps({"scenario_id": "UT-001", "category": "unsafe_tool_usage", "score": "warn", "rationale": "no tools discovered"}),
            ]
        ),
        encoding="utf-8",
    )
    (artifacts / "launch_gate" / "security-readiness.json").write_text(json.dumps({"status": "conditional_go"}), encoding="utf-8")

    payload = build_bridge_verdict(artifacts)

    assert payload["summary"]["core_controls_exist"] is True
    assert payload["summary"]["adversarial_tests_passed"] is True
    assert payload["verdict"] == "conditional_go"
    assert payload["summary"]["safer_than_unprotected_baseline"] is True


def test_bridge_markdown_contains_required_lines(tmp_path) -> None:
    artifacts = tmp_path / "artifacts"
    (artifacts / "evals").mkdir(parents=True, exist_ok=True)
    (artifacts / "evals" / "run.jsonl").write_text(
        json.dumps({"scenario_id": "PB-001", "category": "policy_bypass", "score": "fail", "rationale": "allowed"}) + "\n",
        encoding="utf-8",
    )

    payload = build_bridge_verdict(artifacts)
    md = render_markdown(payload)

    assert "Launch Gate Bridge Verdict" in md
    assert "Core controls exist" in md
    assert "Adversarial tests passed" in md
    assert "Remaining risks" in md
