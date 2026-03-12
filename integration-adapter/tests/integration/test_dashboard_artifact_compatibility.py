from __future__ import annotations

from pathlib import Path
import sys

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import generate_artifacts


def test_starterkit_artifact_readers_can_parse_adapter_outputs(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    starterkit_root = repo_root / "myStarterKit-maindashb-main"
    sys.path.insert(0, str(starterkit_root))

    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    generate_artifacts(force_demo=True, config=config)

    from observability.artifact_readers import ArtifactReaders  # type: ignore

    readers = ArtifactReaders(starterkit_root, artifacts_root=str(config.artifacts_root.resolve()))
    payload = readers.read_all()

    assert payload["audit_jsonl"].parsed is True
    assert payload["replay_json"]
    assert payload["eval_jsonl"]
    assert payload["launch_gate_output_json"]
    assert payload["launch_gate_output_json"][0].parsed is True
