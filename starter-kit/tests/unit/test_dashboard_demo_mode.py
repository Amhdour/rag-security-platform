"""Tests for dashboard local demo-mode artifact generation and schema compatibility."""

from __future__ import annotations

import json
from pathlib import Path

from observability.demo_artifacts import generate_demo_artifacts
from observability.eval_normalization import parse_eval_jsonl, parse_eval_summary
from observability.launch_gate_normalization import parse_launch_gate_report
from observability.service import DashboardService
from observability.trace_normalization import build_trace_explanations, read_audit_jsonl


def test_generate_demo_artifacts_outputs_expected_files(tmp_path: Path) -> None:
    root = generate_demo_artifacts(tmp_path / "artifacts/demo/dashboard_logs")

    assert (root / "DEMO_MODE.json").is_file()
    assert (root / "audit.jsonl").is_file()
    assert list((root / "replay").glob("*.replay.json"))
    assert list((root / "evals").glob("*.summary.json"))
    assert list((root / "evals").glob("*.jsonl"))
    assert list((root / "launch_gate").glob("*.json"))

    marker = json.loads((root / "DEMO_MODE.json").read_text())
    assert marker["mode"] == "demo"


def test_demo_artifacts_are_schema_compatible_with_dashboard_parsers(tmp_path: Path) -> None:
    root = generate_demo_artifacts(tmp_path / "artifacts/demo/dashboard_logs")

    events, malformed = read_audit_jsonl(root / "audit.jsonl")
    assert malformed == 0
    traces = build_trace_explanations(events)
    trace_ids = {item["ids"]["trace_id"] for item in traces}
    assert {"trace-demo-success", "trace-demo-deny-retrieval", "trace-demo-forbidden-tool", "trace-demo-fallback"}.issubset(trace_ids)

    eval_summary_path = sorted((root / "evals").glob("*.summary.json"))[0]
    eval_jsonl_path = sorted((root / "evals").glob("*.jsonl"))[0]
    assert parse_eval_summary(eval_summary_path) is not None
    parsed_rows, malformed_rows = parse_eval_jsonl(eval_jsonl_path)
    assert malformed_rows == 0
    assert parsed_rows

    launch_gate_path = sorted((root / "launch_gate").glob("*.json"))[0]
    launch = parse_launch_gate_report(launch_gate_path)
    assert launch is not None
    assert launch["status"] in {"go", "conditional_go", "no_go"}


def test_dashboard_service_can_run_in_demo_mode(tmp_path: Path) -> None:
    root = generate_demo_artifacts(tmp_path / "artifacts/demo/dashboard_logs")
    service = DashboardService(tmp_path, artifacts_root=root)

    traces = service.list_traces()
    assert len(traces) >= 4
    trace_ids = {item["trace_id"] for item in traces}
    assert "trace-demo-success" in trace_ids
    assert "trace-demo-deny-retrieval" in trace_ids
    assert "trace-demo-forbidden-tool" in trace_ids
    assert "trace-demo-fallback" in trace_ids

    eval_runs = service.list_eval_runs()
    assert len(eval_runs) == 1
    eval_detail = service.get_eval_run(eval_runs[0]["run_id"])
    assert eval_detail is not None

    launch_gate = service.get_latest_launch_gate()
    assert launch_gate is not None
    assert launch_gate["status"] == "conditional_go"

    overview = service.get_overview()
    assert overview["demo_mode"] is True
    assert overview["readiness_card"]["status"] == "conditional_go"

    system_map = service.get_system_map()
    assert system_map["demo_mode"] is True
