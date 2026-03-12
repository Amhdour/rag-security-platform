from __future__ import annotations

from pathlib import Path
import subprocess


def test_demo_pipeline_cli_smoke(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    adapter_root = repo_root / "integration-adapter"
    env = dict(__import__("os").environ)
    env["INTEGRATION_ADAPTER_ARTIFACTS_ROOT"] = str(tmp_path / "artifacts" / "logs")

    result = subprocess.run(
        ["python", "-m", "integration_adapter.demo_scenario"],
        cwd=adapter_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    root = tmp_path / "artifacts" / "logs"
    assert (root / "audit.jsonl").is_file()
    assert list((root / "replay").glob("*.replay.json"))
    assert list((root / "evals").glob("*.jsonl"))
    assert list((root / "launch_gate").glob("*.json"))
    assert list((root / "launch_gate").glob("*.md"))
