from __future__ import annotations

from pathlib import Path
import subprocess


def test_ci_smoke_cli_generates_expected_outputs(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    adapter_root = repo_root / "integration-adapter"
    artifacts_root = tmp_path / "ci-smoke" / "logs"

    result = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.ci_smoke",
            "--artifacts-root",
            str(artifacts_root),
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    assert (artifacts_root / "audit.jsonl").is_file()
    assert list((artifacts_root / "replay").glob("*.replay.json"))
    assert list((artifacts_root / "evals").glob("*.summary.json"))
    assert list((artifacts_root / "launch_gate").glob("*.json"))
    assert (artifacts_root / "adapter_health" / "adapter_run_summary.json").is_file()
