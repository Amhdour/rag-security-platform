from __future__ import annotations

import argparse
import sys

from integration_adapter.pipeline import generate_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate starter-kit-compatible artifacts from collected data")
    parser.add_argument("--demo", action="store_true", help="force demo mode")
    args = parser.parse_args()

    try:
        result = generate_artifacts(force_demo=args.demo)
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
