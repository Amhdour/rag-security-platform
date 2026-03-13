from __future__ import annotations

import argparse
import sys
from pathlib import Path

import os

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import generate_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate starter-kit-compatible artifacts from collected data")
    parser.add_argument("--demo", action="store_true", help="force demo mode")
    parser.add_argument("--artifacts-root", default=None, help="override artifacts root for this run")
    parser.add_argument("--profile", default=None, choices=["demo", "dev", "ci", "prod_like"], help="execution profile override")
    args = parser.parse_args()

    if args.artifacts_root or args.profile:
        base = AdapterConfig.from_env(default_root="artifacts/logs")
        root = Path(args.artifacts_root) if args.artifacts_root else base.artifacts_root
        profile = args.profile or os.environ.get("INTEGRATION_ADAPTER_PROFILE", base.profile)
        config = AdapterConfig(artifacts_root=root, profile=profile)
    else:
        config = None

    try:
        result = generate_artifacts(force_demo=args.demo, config=config)
    except Exception as exc:
        print(f"[integration-adapter] artifact generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"[integration-adapter] mode={result.mode}")
    print(f"[integration-adapter] profile={result.profile}")
    print(f"[integration-adapter] artifacts_root={result.artifacts_root}")
    print(f"[integration-adapter] contract={result.artifact_contract_path}")
    print(f"[integration-adapter] audit={result.audit_path}")
    print(f"[integration-adapter] replay_files={len(result.replay_paths)}")
    print(f"[integration-adapter] eval_jsonl={result.eval_jsonl_path}")
    print(f"[integration-adapter] eval_summary={result.eval_summary_path}")
    print(f"[integration-adapter] launch_gate={result.launch_gate_path}")
    print(f"[integration-adapter] integrity_manifest={result.integrity_manifest_path}")
    print(f"[integration-adapter] adapter_health={result.adapter_health_path}")
    warn_only = [d for d in result.compatibility_decisions if d.status == "warn_only"]
    if warn_only:
        print("[integration-adapter] compatibility warnings")
        for decision in warn_only:
            print(f"- {decision.contract_name}: expected={decision.expected_version}, actual={decision.actual_version}, reason={decision.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
