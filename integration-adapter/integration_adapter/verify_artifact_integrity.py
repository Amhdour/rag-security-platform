from __future__ import annotations

import argparse
import json
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
    args = parser.parse_args()

    result = verify_integrity_manifest(
        artifacts_root=Path(args.artifacts_root),
        required_paths=REQUIRED_PATHS,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if not result.ok:
        print("[integration-adapter] artifact integrity verification failed", file=sys.stderr)
        return 1
    print("[integration-adapter] artifact integrity verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
