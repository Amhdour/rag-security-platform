from __future__ import annotations

from pathlib import Path
import sys

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import generate_artifacts


def test_starterkit_readers_report_malformed_adapter_artifacts(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    starterkit_root = repo_root / "myStarterKit-maindashb-main"
    sys.path.insert(0, str(starterkit_root))

    config = AdapterConfig(artifacts_root=tmp_path / "artifacts" / "logs")
    generate_artifacts(force_demo=True, config=config)

    malformed_replay = config.artifacts_root / "replay" / "broken.replay.json"
    malformed_replay.write_text("{bad-json", encoding="utf-8")

    from observability.artifact_readers import ArtifactReaders  # type: ignore

    readers = ArtifactReaders(starterkit_root, artifacts_root=str(config.artifacts_root.resolve()))
    payload = readers.read_all()

    replay_rows = payload["replay_json"]
    assert any(not row.parsed for row in replay_rows)
    assert any((row.error or "").startswith("parse_error") for row in replay_rows)
