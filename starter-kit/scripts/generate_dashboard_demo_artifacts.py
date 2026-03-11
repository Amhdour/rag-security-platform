"""CLI wrapper to generate local demo artifacts for dashboard learning mode."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observability.demo_artifacts import generate_demo_artifacts


def main() -> None:
    path = generate_demo_artifacts()
    print(f"DEMO MODE artifacts written to: {path}")
    print("Use only for local learning. Do not treat as production evidence.")


if __name__ == "__main__":
    main()
