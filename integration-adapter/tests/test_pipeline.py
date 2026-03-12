from __future__ import annotations

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import collect_from_onyx, generate_artifacts, run_launch_gate


def test_collect_from_onyx_demo_mode_returns_payload() -> None:
    payload = collect_from_onyx(force_demo=True)
    assert payload.mode == "demo"
    assert payload.connectors
    assert payload.runtime_events


def test_generate_artifacts_writes_required_outputs(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    result = generate_artifacts(force_demo=True, config=config)

    assert result.audit_path.is_file()
    assert result.eval_jsonl_path.is_file()
    assert result.eval_summary_path.is_file()
    assert result.launch_gate_path.is_file()
    assert result.replay_paths
    assert result.replay_paths[0].is_file()


def test_run_launch_gate_fails_closed_without_eval_summaries(tmp_path) -> None:
    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    launch_path = run_launch_gate(config=config)
    payload = launch_path.read_text(encoding="utf-8")
    assert "missing eval JSONL or summary artifacts" in payload
    assert '"status": "no_go"' in payload
