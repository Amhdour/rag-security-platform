import json

from integration_adapter.artifact_output import ArtifactWriter
from integration_adapter.config import AdapterConfig


def test_launch_gate_summary_generation(tmp_path) -> None:
    writer = ArtifactWriter(AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"))
    report_path = writer.write_launch_gate_summary(statuses=["pass", "pass"], blockers=[], residual_risks=[])
    payload = json.loads(report_path.read_text())
    assert payload["status"] == "go"
    assert payload["checks_passed"] == 2
    assert payload["checks_total"] == 2
    assert len(payload["checks"]) == 2
    assert payload["checks"][0]["check_name"].startswith("adapter_check_")
    assert payload["scorecard"][0]["category_name"] == "integration_adapter"
