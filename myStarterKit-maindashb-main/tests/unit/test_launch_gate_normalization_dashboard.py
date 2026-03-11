"""Tests for launch-gate dashboard normalization adapter."""

from __future__ import annotations

import json
from pathlib import Path

from observability.launch_gate_normalization import parse_launch_gate_report


def test_parse_launch_gate_report_builds_snapshot_and_missing_evidence(tmp_path: Path) -> None:
    path = tmp_path / "security-readiness-1.json"
    payload = {
        "status": "conditional_go",
        "summary": "status=conditional_go",
        "blockers": ["blocker-a"],
        "residual_risks": ["risk-a"],
        "checks": [
            {"check_name": "policy_artifact", "status": "pass", "passed": True, "details": "ok"},
            {"check_name": "replay_evidence", "status": "missing", "passed": False, "details": "replay missing"},
        ],
    }
    path.write_text(json.dumps(payload))

    parsed = parse_launch_gate_report(path)

    assert parsed is not None
    assert parsed["status"] == "conditional_go"
    assert parsed["snapshot"]["check_total"] == 2
    assert parsed["snapshot"]["check_passed"] == 1
    assert parsed["snapshot"]["missing_evidence_count"] == 1
    assert parsed["missing_evidence"][0]["check_name"] == "replay_evidence"
    assert "runtime enforcement" in parsed["readiness_legend"]["runtime_enforcement"].lower()
    assert parsed["latest_artifact_timestamp"]


def test_parse_launch_gate_report_heuristic_missing_evidence(tmp_path: Path) -> None:
    path = tmp_path / "security-readiness-2.json"
    payload = {
        "status": "no_go",
        "summary": "status=no_go",
        "checks": [
            {"check_name": "audit_evidence", "status": "fail", "passed": False, "details": "required file missing"}
        ],
    }
    path.write_text(json.dumps(payload))

    parsed = parse_launch_gate_report(path)

    assert parsed is not None
    assert parsed["missing_evidence"]
    assert parsed["missing_evidence"][0]["check_name"] == "audit_evidence"
