from __future__ import annotations

from pathlib import Path
import subprocess


def test_verify_integrity_cli_passes_after_demo_generation(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    adapter_root = repo_root / "integration-adapter"
    artifacts_root = tmp_path / "artifacts" / "logs"

    generate = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.generate_artifacts",
            "--demo",
            "--artifacts-root",
            str(artifacts_root),
            "--profile",
            "demo",
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert generate.returncode == 0, generate.stderr

    verify = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.verify_artifact_integrity",
            "--artifacts-root",
            str(artifacts_root),
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify.returncode == 0, verify.stderr
