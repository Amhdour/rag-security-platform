from __future__ import annotations

from pathlib import Path

import integration_adapter.evidence_pipeline as evidence_pipeline


class _Payload:
    mode = "demo"
    connectors = []
    tools = []
    mcp_servers = []
    evals = []
    runtime_events = []


class _Artifacts:
    def __init__(self, root: Path) -> None:
        self.artifacts_root = root
        self.audit_path = root / "audit.jsonl"
        self.eval_jsonl_path = root / "evals" / "suite.jsonl"
        self.eval_summary_path = root / "evals" / "suite.summary.json"
        self.launch_gate_path = root / "launch_gate" / "security-readiness.json"


def test_verify_expected_outputs_reports_missing_replay_and_launch_gate_json(tmp_path) -> None:
    root = tmp_path / "artifacts" / "logs"
    (root / "replay").mkdir(parents=True, exist_ok=True)
    (root / "launch_gate").mkdir(parents=True, exist_ok=True)
    (root / "evals").mkdir(parents=True, exist_ok=True)
    (root / "audit.jsonl").write_text("", encoding="utf-8")
    (root / "connectors.inventory.json").write_text("[]", encoding="utf-8")
    (root / "tools.inventory.json").write_text("[]", encoding="utf-8")
    (root / "mcp_servers.inventory.json").write_text("[]", encoding="utf-8")

    missing = evidence_pipeline._verify_expected_outputs(root)

    assert str(root / "replay/*.replay.json") in missing
    assert str(root / "launch_gate/*.json") in missing


def test_evidence_pipeline_returns_nonzero_when_required_outputs_missing(tmp_path, monkeypatch) -> None:
    root = tmp_path / "artifacts" / "logs"
    root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(evidence_pipeline, "collect_from_onyx", lambda force_demo: _Payload())
    monkeypatch.setattr(evidence_pipeline, "generate_artifacts", lambda force_demo: _Artifacts(root))
    seen = {}

    def _run_launch_gate(*, config):
        seen["root"] = config.artifacts_root
        return root / "launch_gate" / "security-readiness.json"

    monkeypatch.setattr(evidence_pipeline, "run_launch_gate", _run_launch_gate)
    monkeypatch.setattr("sys.argv", ["integration_adapter.evidence_pipeline", "--demo"])

    code = evidence_pipeline.main()

    assert code == 1
    assert seen["root"] == root


def test_evidence_pipeline_returns_nonzero_on_unhandled_exception(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(evidence_pipeline, "collect_from_onyx", _boom)
    monkeypatch.setattr("sys.argv", ["integration_adapter.evidence_pipeline", "--demo"])

    code = evidence_pipeline.main()

    assert code == 1
