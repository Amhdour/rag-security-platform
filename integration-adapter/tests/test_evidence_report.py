from __future__ import annotations

import json
from pathlib import Path

from integration_adapter.evidence_report import generate_evidence_report


def test_generate_evidence_report_outputs_all_formats(tmp_path) -> None:
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "evals").mkdir(parents=True, exist_ok=True)
    (artifacts_root / "launch_gate").mkdir(parents=True, exist_ok=True)

    (artifacts_root / "evals" / "demo.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"scenario_id": "PR-201", "category": "poisoned_retrieval", "score": "pass", "rationale": "poisoned retrieval denied"}),
                json.dumps({"scenario_id": "LK-301", "category": "unsafe_output", "score": "warn", "rationale": "no signal"}),
            ]
        ),
        encoding="utf-8",
    )
    (artifacts_root / "evals" / "demo.summary.json").write_text(
        json.dumps({"suite_name": "demo", "outcomes": {"pass": 1, "warn": 1}}, indent=2),
        encoding="utf-8",
    )
    (artifacts_root / "launch_gate" / "security-readiness-demo.json").write_text(
        json.dumps({"status": "no_go"}, indent=2), encoding="utf-8"
    )

    output_md = tmp_path / "evidence.md"
    output_json = tmp_path / "evidence.json"
    output_html = tmp_path / "evidence.html"

    payload = generate_evidence_report(
        artifacts_root=artifacts_root,
        output_md=output_md,
        output_json=output_json,
        output_html=output_html,
    )

    assert output_md.exists()
    assert output_json.exists()
    assert output_html.exists()
    assert payload["executive_summary"]["eval_rows_analyzed"] == 2
    assert payload["executive_summary"]["latest_launch_gate_status"] == "no_go"
    assert payload["notable_blocked_scenarios"][0]["scenario_id"] == "PR-201"

    md_text = output_md.read_text(encoding="utf-8")
    assert "## Executive summary" in md_text
    assert "## Reviewer appendix (file references)" in md_text
