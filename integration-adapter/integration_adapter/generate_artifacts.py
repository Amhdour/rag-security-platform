from __future__ import annotations

import argparse
import sys
from pathlib import Path

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import generate_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate starter-kit-compatible artifacts from collected data")
    parser.add_argument("--demo", action="store_true", help="force demo mode")
    parser.add_argument("--artifacts-root", default=None, help="override artifacts root for this run")
    args = parser.parse_args()

    config = AdapterConfig(artifacts_root=Path(args.artifacts_root)) if args.artifacts_root else None

    try:
        result = generate_artifacts(force_demo=args.demo, config=config)
    except Exception as exc:
        print(f"[integration-adapter] artifact generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"[integration-adapter] mode={result.mode}")
    print(f"[integration-adapter] artifacts_root={result.artifacts_root}")
    print(f"[integration-adapter] audit={result.audit_path}")
    print(f"[integration-adapter] replay_files={len(result.replay_paths)}")
    print(f"[integration-adapter] eval_jsonl={result.eval_jsonl_path}")
    print(f"[integration-adapter] eval_summary={result.eval_summary_path}")
    print(f"[integration-adapter] launch_gate={result.launch_gate_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
