from __future__ import annotations

import sys

from integration_adapter.pipeline import run_launch_gate


def main() -> int:
    try:
        output = run_launch_gate()
    except Exception as exc:
        print(f"[integration-adapter] launch gate failed: {exc}", file=sys.stderr)
        return 1

    print(f"[integration-adapter] launch gate summary={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
