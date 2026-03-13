import json

from integration_adapter.artifact_output import ArtifactWriter
from integration_adapter.config import AdapterConfig
from integration_adapter.sample_data import generate_sample_artifacts


def test_sample_generator_writes_required_artifacts(tmp_path) -> None:
    import os

    os.environ["INTEGRATION_ADAPTER_ARTIFACTS_ROOT"] = str(tmp_path / "artifacts" / "logs")
    generate_sample_artifacts()

    root = tmp_path / "artifacts" / "logs"
    assert (root / "audit.jsonl").is_file()
    assert (root / "replay").is_dir()
    assert (root / "evals").is_dir()
    assert (root / "launch_gate").is_dir()


def test_writer_emits_eval_summary(tmp_path) -> None:
    writer = ArtifactWriter(AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs"))
    _, summary = writer.write_eval_results(
        run_id="run-a",
        rows=[{"scenario_id": "x", "outcome": "pass"}, {"scenario_id": "y", "outcome": "fail"}],
    )
    payload = json.loads(summary.read_text())
    assert payload["total"] == 2
    assert payload["passed_count"] == 1


def test_sample_generator_writes_versioned_contract_manifest(tmp_path) -> None:
    import os

    os.environ["INTEGRATION_ADAPTER_ARTIFACTS_ROOT"] = str(tmp_path / "artifacts" / "logs")
    generate_sample_artifacts()

    root = tmp_path / "artifacts" / "logs"
    contract = json.loads((root / "artifact_bundle.contract.json").read_text())
    assert contract["artifact_bundle_schema_version"] == "1.0"
    assert contract["normalized_schema_version"] == "1.0"
    assert contract["source_schema_version"] == "1.0"
