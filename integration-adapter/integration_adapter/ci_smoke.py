from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import os

from integration_adapter.config import AdapterConfig
from integration_adapter.evidence_pipeline import _verify_expected_outputs
from integration_adapter.pipeline import generate_artifacts, run_launch_gate
from integration_adapter.validate_config import validate_configuration


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CI-friendly adapter smoke check (no external services)")
    parser.add_argument(
        "--artifacts-root",
        default="artifacts/logs-ci-smoke",
        help="artifacts root for smoke outputs (default: artifacts/logs-ci-smoke)",
    )
    parser.add_argument("--profile", default="ci", choices=["demo", "dev", "ci", "prod_like"], help="execution profile for smoke run")
    args = parser.parse_args()

    profile = args.profile or os.environ.get("INTEGRATION_ADAPTER_PROFILE", "ci")
    base = AdapterConfig.from_env(default_root="artifacts/logs-ci-smoke")
    config = AdapterConfig(
        artifacts_root=Path(args.artifacts_root),
        profile=profile,
        integrity_mode=base.integrity_mode,
        integrity_signing_key=base.integrity_signing_key,
        integrity_signing_key_path=base.integrity_signing_key_path,
        integrity_signing_key_id=base.integrity_signing_key_id,
    )
    validation = validate_configuration(config=config, strict_sources=False)
    if validation.status == "fail":
        print(json.dumps(validation.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
        print("[integration-adapter] ci smoke aborted: invalid configuration", file=sys.stderr)
        return 1

    try:
        artifacts = generate_artifacts(force_demo=True, config=config)
        launch_gate_json = run_launch_gate(config=config)
    except Exception as exc:  # noqa: BLE001
        print(f"[integration-adapter] ci smoke failed: {exc}", file=sys.stderr)
        return 1

    missing = _verify_expected_outputs(artifacts.artifacts_root)
    status = "pass" if not missing else "fail"
    summary = {
        "status": status,
        "mode": artifacts.mode,
        "profile": profile,
        "artifacts_root": str(artifacts.artifacts_root),
        "launch_gate_json": str(launch_gate_json),
        "missing_outputs": missing,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if missing:
        print("[integration-adapter] ci smoke failed: missing required outputs", file=sys.stderr)
        return 1
    print("[integration-adapter] ci smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
