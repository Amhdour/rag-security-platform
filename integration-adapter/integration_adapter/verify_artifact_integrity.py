from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from integration_adapter.integrity import verify_integrity_manifest

REQUIRED_PATHS = [
    "artifact_bundle.contract.json",
    "audit.jsonl",
    "connectors.inventory.json",
    "tools.inventory.json",
    "mcp_servers.inventory.json",
    "evals.inventory.json",
    "adapter_health/adapter_run_summary.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify adapter artifact integrity manifest and required outputs")
    parser.add_argument("--artifacts-root", default="artifacts/logs", help="artifact root containing manifest and artifacts")
    parser.add_argument(
        "--integrity-mode",
        default=os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_MODE", "hash_only"),
        choices=["hash_only", "signed_manifest"],
        help="integrity verification mode",
    )
    parser.add_argument(
        "--signing-key",
        default=os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY"),
        help="signing key value for signed_manifest verification",
    )
    parser.add_argument(
        "--signing-key-path",
        default=os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_PATH"),
        help="path to signing key file for signed_manifest verification",
    )
    args = parser.parse_args()

    key_path = Path(args.signing_key_path) if args.signing_key_path else None
    result = verify_integrity_manifest(
        artifacts_root=Path(args.artifacts_root),
        required_paths=REQUIRED_PATHS,
        integrity_mode=args.integrity_mode,
        signing_key=args.signing_key,
        signing_key_path=key_path,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if not result.ok:
        print("[integration-adapter] artifact integrity verification failed", file=sys.stderr)
        return 1
    print("[integration-adapter] artifact integrity verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
