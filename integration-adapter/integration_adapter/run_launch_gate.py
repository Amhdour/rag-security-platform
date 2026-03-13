from __future__ import annotations

import argparse
import sys
from pathlib import Path

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import run_launch_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run launch-gate evaluation for generated artifacts")
    parser.add_argument("--artifacts-root", default=None, help="override artifacts root for this run")
    args = parser.parse_args()

    config = AdapterConfig(artifacts_root=Path(args.artifacts_root)) if args.artifacts_root else None

    try:
        output = run_launch_gate(config=config)
    except Exception as exc:
        print(f"[integration-adapter] launch gate failed: {exc}", file=sys.stderr)
        return 1

    print(f"[integration-adapter] launch gate summary={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
