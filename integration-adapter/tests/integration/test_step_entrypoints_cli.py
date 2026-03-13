from __future__ import annotations

from pathlib import Path
import subprocess


def test_step_entrypoints_support_artifacts_root_override(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    adapter_root = repo_root / "integration-adapter"
    artifacts_root = tmp_path / "custom-artifacts" / "logs"

    collect = subprocess.run(
        ["python", "-m", "integration_adapter.collect_from_onyx", "--demo"],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert collect.returncode == 0, collect.stderr

    generate = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.generate_artifacts",
            "--demo",
            "--artifacts-root",
            str(artifacts_root),
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert generate.returncode == 0, generate.stderr

    gate = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.run_launch_gate",
            "--artifacts-root",
            str(artifacts_root),
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert gate.returncode == 0, gate.stderr

    assert (artifacts_root / "audit.jsonl").is_file()
    assert list((artifacts_root / "replay").glob("*.replay.json"))
    assert list((artifacts_root / "evals").glob("*.summary.json"))
    assert list((artifacts_root / "launch_gate").glob("*.json"))

