"""
Implemented: one-command evidence pipeline orchestration for collection, artifact generation, and launch-gate execution.
Partially Implemented: live runtime extraction depends on environment/runtime hooks used by collection/exporters.
Demo-only: `--demo` mode uses adapter demo data paths when live runtime data is unavailable.
Unconfirmed: production runtime hook parity across all deployment topologies is not validated by this CLI alone.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import collect_from_onyx, generate_artifacts, run_launch_gate


def _verify_expected_outputs(root: Path) -> list[str]:
    expected = [
        root / "artifact_bundle.contract.json",
        root / "artifact_integrity.manifest.json",
        root / "adapter_health" / "adapter_run_summary.json",
        root / "audit.jsonl",
        root / "connectors.inventory.json",
        root / "tools.inventory.json",
        root / "mcp_servers.inventory.json",
        root / "evals",
        root / "replay",
        root / "launch_gate",
    ]
    missing = [str(path) for path in expected if not path.exists()]

    replay_files = list((root / "replay").glob("*.replay.json")) if (root / "replay").exists() else []
    if not replay_files:
        missing.append(str(root / "replay/*.replay.json"))

    launch_gate_json = list((root / "launch_gate").glob("*.json")) if (root / "launch_gate").exists() else []
    if not launch_gate_json:
        missing.append(str(root / "launch_gate/*.json"))

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run collection -> artifact generation -> launch-gate evaluation in one command"
    )
    parser.add_argument("--demo", action="store_true", help="force demo mode")
    parser.add_argument("--profile", default=None, choices=["demo", "dev", "ci", "prod_like"], help="execution profile override")
    args = parser.parse_args()

    try:
        payload = collect_from_onyx(force_demo=args.demo)
        print("[integration-adapter] collect_from_onyx complete")
        print(
            json.dumps(
                {
                    "mode": payload.mode,
                    "raw_source_schema_version": payload.raw_source_schema_version,
                    "connectors": len(payload.connectors),
                    "tools": len(payload.tools),
                    "mcp_servers": len(payload.mcp_servers),
                    "evals": len(payload.evals),
                    "runtime_events": len(payload.runtime_events),
                },
                indent=2,
                sort_keys=True,
            )
        )

        profile = args.profile or os.environ.get("INTEGRATION_ADAPTER_PROFILE", "dev")
        base = AdapterConfig.from_env()
        pipeline_config = AdapterConfig(
            artifacts_root=base.artifacts_root,
            profile=profile,
            integrity_mode=base.integrity_mode,
            integrity_signing_key=base.integrity_signing_key,
            integrity_signing_key_path=base.integrity_signing_key_path,
            integrity_signing_key_id=base.integrity_signing_key_id,
        )
        artifacts = generate_artifacts(force_demo=args.demo, config=pipeline_config)
        print("[integration-adapter] generate_artifacts complete")
        print(f"[integration-adapter] profile={artifacts.profile}")
        print(f"[integration-adapter] artifacts_root={artifacts.artifacts_root}")
        print(f"[integration-adapter] contract={artifacts.artifact_contract_path}")
        print(f"[integration-adapter] audit={artifacts.audit_path}")
        print(f"[integration-adapter] eval_jsonl={artifacts.eval_jsonl_path}")
        print(f"[integration-adapter] eval_summary={artifacts.eval_summary_path}")
        print(f"[integration-adapter] launch_gate={artifacts.launch_gate_path}")
        print(f"[integration-adapter] integrity_manifest={artifacts.integrity_manifest_path}")
        print(f"[integration-adapter] adapter_health={artifacts.adapter_health_path}")
        warn_only = [d for d in artifacts.compatibility_decisions if d.status == "warn_only"]
        if warn_only:
            print("[integration-adapter] compatibility warnings")
            for decision in warn_only:
                print(f"- {decision.contract_name}: expected={decision.expected_version}, actual={decision.actual_version}, reason={decision.reason}")

        # Implemented: run launch-gate against the same artifacts root used in this pipeline execution.
        launch_gate_path = run_launch_gate(config=AdapterConfig(artifacts_root=artifacts.artifacts_root, profile=profile))
        print(f"[integration-adapter] run_launch_gate complete: {launch_gate_path}")

        missing = _verify_expected_outputs(artifacts.artifacts_root)
        if missing:
            print("[integration-adapter] fatal: required evidence outputs missing", file=sys.stderr)
            print(json.dumps({"missing": missing}, indent=2, sort_keys=True), file=sys.stderr)
            return 1

        print("[integration-adapter] evidence pipeline succeeded")
        return 0
    except Exception as exc:
        print(f"[integration-adapter] evidence pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
