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


def test_verify_integrity_cli_signed_manifest_success_and_failure(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    adapter_root = repo_root / "integration-adapter"
    artifacts_root = tmp_path / "artifacts" / "signed-logs"

    key_path = tmp_path / "signing.key"
    key_path.write_text("ci-signing-secret", encoding="utf-8")

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
        env={
            **__import__("os").environ,
            "INTEGRATION_ADAPTER_INTEGRITY_MODE": "signed_manifest",
            "INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_PATH": str(key_path),
            "INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_ID": "ci-test",
        },
    )
    assert generate.returncode == 0, generate.stderr

    verify_ok = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.verify_artifact_integrity",
            "--artifacts-root",
            str(artifacts_root),
            "--integrity-mode",
            "signed_manifest",
            "--signing-key-path",
            str(key_path),
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_ok.returncode == 0, verify_ok.stderr

    wrong_key_path = tmp_path / "wrong.key"
    wrong_key_path.write_text("wrong-secret", encoding="utf-8")
    verify_fail = subprocess.run(
        [
            "python",
            "-m",
            "integration_adapter.verify_artifact_integrity",
            "--artifacts-root",
            str(artifacts_root),
            "--integrity-mode",
            "signed_manifest",
            "--signing-key-path",
            str(wrong_key_path),
        ],
        cwd=adapter_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_fail.returncode == 1
