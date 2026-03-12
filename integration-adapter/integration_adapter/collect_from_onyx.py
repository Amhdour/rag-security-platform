from __future__ import annotations

import argparse
import json
import sys

from integration_adapter.pipeline import collect_from_onyx


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Onyx-facing inventory/event data")
    parser.add_argument("--demo", action="store_true", help="force demo mode even if live sources exist")
    args = parser.parse_args()

    try:
        payload = collect_from_onyx(force_demo=args.demo)
    except Exception as exc:
        print(f"[integration-adapter] collect failed: {exc}", file=sys.stderr)
        return 1

    summary = {
        "mode": payload.mode,
        "connectors": len(payload.connectors),
        "tools": len(payload.tools),
        "mcp_servers": len(payload.mcp_servers),
        "evals": len(payload.evals),
        "runtime_events": len(payload.runtime_events),
    }
    print("[integration-adapter] collection summary")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
