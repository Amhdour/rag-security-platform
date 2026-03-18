from __future__ import annotations

import argparse
import sys
from pathlib import Path

import os

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import run_launch_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Launch Gate evaluation for generated artifacts")
    parser.add_argument("--artifacts-root", default=None, help="override artifacts root for this run")
    parser.add_argument("--profile", default=None, choices=["demo", "dev", "ci", "prod_like"], help="execution profile override")
    args = parser.parse_args()

    if args.artifacts_root or args.profile:
        base = AdapterConfig.from_env(default_root="artifacts/logs")
        root = Path(args.artifacts_root) if args.artifacts_root else base.artifacts_root
        profile = args.profile or os.environ.get("INTEGRATION_ADAPTER_PROFILE", base.profile)
        config = AdapterConfig(
            artifacts_root=root,
            profile=profile,
            integrity_mode=base.integrity_mode,
            integrity_signing_key=base.integrity_signing_key,
            integrity_signing_key_path=base.integrity_signing_key_path,
            integrity_signing_key_id=base.integrity_signing_key_id,
        )
    else:
        config = None

    try:
        output = run_launch_gate(config=config)
    except Exception as exc:
        print(f"[integration-adapter] launch gate failed: {exc}", file=sys.stderr)
        return 1

    print(f"[integration-adapter] launch gate summary={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
