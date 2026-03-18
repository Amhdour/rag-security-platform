from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MatrixRow:
    threat: str
    control: str
    implementation: str
    tests: str
    evidence: str
    scenario_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "scenario_id": self.scenario_id,
            "threat": self.threat,
            "control": self.control,
            "implementation": self.implementation,
            "tests": self.tests,
            "evidence": self.evidence,
        }


def _repo_root_from_module() -> Path:
    return Path(__file__).resolve().parents[2]


def _scenario_sources(repo_root: Path) -> list[tuple[Path, str]]:
    return [
        (
            repo_root / "integration-adapter/tests/fixtures/adversarial/retrieval_poisoning/scenarios.json",
            "integration-adapter/tests/test_retrieval_poisoning_scenarios.py",
        ),
        (
            repo_root / "integration-adapter/tests/fixtures/adversarial/output_leakage/scenarios.json",
            "integration-adapter/tests/test_output_leakage_scenarios.py",
        ),
    ]


def _default_rows() -> list[MatrixRow]:
    impl = "integration-adapter/integration_adapter/adversarial_harness.py"
    test_file = "integration-adapter/tests/test_adversarial_harness.py"
    evidence = "integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}"
    return [
        MatrixRow(
            scenario_id="PI-001",
            threat="Prompt instruction override attempts unsafe behavior.",
            control="Deny malicious override prompts via policy decision gating.",
            implementation=impl,
            tests=test_file,
            evidence=evidence,
        ),
        MatrixRow(
            scenario_id="PB-001",
            threat="Policy bypass language attempts to disable safeguards.",
            control="Reject policy bypass attempts and preserve guardrails.",
            implementation=impl,
            tests=test_file,
            evidence=evidence,
        ),
        MatrixRow(
            scenario_id="UT-001",
            threat="High-risk tool execution attempted without sufficient authorization.",
            control="Require deny/confirm decision for high-risk tools; warn if tools unavailable.",
            implementation=impl,
            tests=test_file,
            evidence=evidence,
        ),
    ]


def build_control_matrix(repo_root: Path | None = None) -> list[MatrixRow]:
    root = repo_root or _repo_root_from_module()
    rows = _default_rows()

    implementation = "integration-adapter/integration_adapter/adversarial_harness.py"
    evidence = "integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}"

    for scenario_path, test_file in _scenario_sources(root):
        if not scenario_path.exists():
            continue
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
        for item in payload if isinstance(payload, list) else []:
            rows.append(
                MatrixRow(
                    scenario_id=str(item.get("scenario_id", "unknown")),
                    threat=str(item.get("threat", "Unconfirmed: scenario threat not specified.")),
                    control=str(item.get("expected_control_behavior", "Unconfirmed: control behavior not specified.")),
                    implementation=implementation,
                    tests=test_file,
                    evidence=evidence,
                )
            )

    rows.sort(key=lambda row: row.scenario_id)
    return rows


def render_markdown(rows: list[MatrixRow]) -> str:
    lines = [
        "# Reviewer Control Matrix",
        "",
        "**Implemented:** This matrix maps threat scenarios to control intent, implementation modules, test coverage, and evidence artifacts.",
        "**Partially Implemented:** Rows generated from maintained fixture packs and default scenarios; completeness depends on fixture coverage.",
        "**Unconfirmed:** canonical runtime hook not validated in this workspace.",
        "",
        f"Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "| Scenario | Threat | Control | Implementation file/module | Test coverage | Evidence artifact |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.scenario_id}` | {row.threat} | {row.control} | `{row.implementation}` | `{row.tests}` | `{row.evidence}` |"
        )
    lines.append("")
    lines.append("Regenerate with:")
    lines.append("```bash")
    lines.append("cd integration-adapter")
    lines.append("python -m integration_adapter.control_matrix --output-doc ../docs/control-matrix.md")
    lines.append("```")
    return "\n".join(lines) + "\n"


def write_outputs(*, rows: list[MatrixRow], output_doc: Path, output_json: Path | None = None) -> None:
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(render_markdown(rows), encoding="utf-8")
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rows": [row.to_dict() for row in rows],
        }
        output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reviewer-friendly control matrix")
    parser.add_argument("--output-doc", default="../docs/control-matrix.md", help="Markdown output path")
    parser.add_argument("--output-json", default="", help="Optional JSON output path")
    args = parser.parse_args()

    repo_root = _repo_root_from_module()
    rows = build_control_matrix(repo_root)

    output_doc = (repo_root / "integration-adapter" / args.output_doc).resolve()
    output_json = (repo_root / "integration-adapter" / args.output_json).resolve() if args.output_json else None
    write_outputs(rows=rows, output_doc=output_doc, output_json=output_json)
    print(json.dumps({"rows": len(rows), "output_doc": str(output_doc), "output_json": str(output_json) if output_json else ""}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
