from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integration_adapter.control_matrix import build_control_matrix

GO = "go"
CONDITIONAL_GO = "conditional_go"
NO_GO = "no_go"


def _latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    matches = sorted(directory.glob(pattern))
    return matches[-1] if matches else None


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_eval_rows(artifacts_root: Path) -> tuple[list[dict[str, Any]], Path | None]:
    jsonl_path = _latest_file(artifacts_root / "evals", "*.jsonl")
    if jsonl_path is None:
        return [], None
    rows: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"score": "warn", "rationale": "malformed eval row"})
    return rows, jsonl_path


def _compute_outcomes(rows: list[dict[str, Any]]) -> dict[str, int]:
    outcomes = {"pass": 0, "fail": 0, "warn": 0}
    for row in rows:
        score = str(row.get("score", "warn")).lower()
        outcomes[score] = outcomes.get(score, 0) + 1
    return outcomes


def build_bridge_verdict(artifacts_root: Path) -> dict[str, Any]:
    rows, eval_path = _read_eval_rows(artifacts_root)
    outcomes = _compute_outcomes(rows)

    launch_gate_path = _latest_file(artifacts_root / "launch_gate", "*.json")
    launch_gate = _load_json(launch_gate_path)
    gate_status = str(launch_gate.get("status", "unknown"))
    gate_blockers = launch_gate.get("blockers", []) if isinstance(launch_gate.get("blockers"), list) else []
    gate_residual = launch_gate.get("residual_risks", []) if isinstance(launch_gate.get("residual_risks"), list) else []

    control_rows = build_control_matrix()
    controls = sorted({row.control for row in control_rows})

    blocked_scenarios = [
        {
            "scenario_id": row.get("scenario_id", "unknown"),
            "category": row.get("category", "unknown"),
            "rationale": row.get("rationale", ""),
        }
        for row in rows
        if str(row.get("score", "")).lower() == "pass"
        and any(token in str(row.get("rationale", "")).lower() for token in ["blocked", "denied", "gated"])
    ]

    risky = []
    risky.extend([f"eval_fail:{row.get('scenario_id','unknown')}" for row in rows if str(row.get("score", "")).lower() == "fail"])
    risky.extend([f"eval_warn:{row.get('scenario_id','unknown')}" for row in rows if str(row.get("score", "")).lower() == "warn"])
    risky.extend([f"launch_gate_blocker:{item}" for item in gate_blockers])
    risky.extend([f"launch_gate_residual:{item}" for item in gate_residual])

    core_controls_exist = len(controls) > 0
    adversarial_tests_passed = outcomes.get("fail", 0) == 0 and outcomes.get("pass", 0) > 0
    safer_than_baseline = core_controls_exist and len(blocked_scenarios) > 0 and outcomes.get("fail", 0) == 0

    if not core_controls_exist or outcomes.get("fail", 0) > 0:
        verdict = NO_GO
    elif outcomes.get("warn", 0) > 0 or gate_status in {"conditional_go", "no_go", "unknown"}:
        verdict = CONDITIONAL_GO
    else:
        verdict = GO

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts_root": str(artifacts_root),
        "verdict": verdict,
        "summary": {
            "core_controls_exist": core_controls_exist,
            "adversarial_tests_passed": adversarial_tests_passed,
            "safer_than_unprotected_baseline": safer_than_baseline,
            "basis_statement": (
                "Implemented: verdict derived from current artifact evidence and adversarial eval outputs only; "
                "Unconfirmed: canonical runtime hook not validated in this workspace."
            ),
        },
        "core_controls": controls,
        "adversarial_eval": {
            "latest_eval_jsonl": str(eval_path) if eval_path else "",
            "outcomes": outcomes,
        },
        "notable_blocked_scenarios": blocked_scenarios,
        "remaining_risks": risky,
        "launch_gate_context": {
            "latest_launch_gate_json": str(launch_gate_path) if launch_gate_path else "",
            "status": gate_status,
            "blockers": gate_blockers,
            "residual_risks": gate_residual,
        },
        "limitations": [
            "Verdict is artifact-derived and does not prove production runtime enforcement.",
            "Baseline comparison is relative: presence of blocked adversarial scenarios versus an assumed unprotected path.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload.get("summary", {})
    lines = [
        "# Launch Gate Bridge Verdict",
        "",
        "**Implemented:** This verdict bridges evaluation artifacts into a Launch Gate style summary.",
        "**Unconfirmed:** canonical runtime hook not validated in this workspace.",
        "",
        f"- Verdict: `{payload.get('verdict', 'unknown')}`",
        f"- Core controls exist: `{s.get('core_controls_exist')}`",
        f"- Adversarial tests passed: `{s.get('adversarial_tests_passed')}`",
        f"- Demonstrably safer than unprotected baseline: `{s.get('safer_than_unprotected_baseline')}`",
        f"- Basis: {s.get('basis_statement', '')}",
        "",
        "## Remaining risks",
    ]
    risks = payload.get("remaining_risks", [])
    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("- None identified from current artifact inputs.")

    lines.extend(["", "## Notable blocked scenarios"])
    blocked = payload.get("notable_blocked_scenarios", [])
    if blocked:
        for row in blocked:
            lines.append(f"- `{row.get('scenario_id','unknown')}` ({row.get('category','unknown')}): {row.get('rationale','')}")
    else:
        lines.append("- None observed.")

    lines.extend(["", "## Launch Gate context"])
    context = payload.get("launch_gate_context", {})
    lines.append(f"- Latest Launch Gate artifact: `{context.get('latest_launch_gate_json', '')}`")
    lines.append(f"- Status: `{context.get('status', 'unknown')}`")

    lines.extend(["", "## Limitations"])
    for item in payload.get("limitations", []):
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"


def write_outputs(*, payload: dict[str, Any], output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    output_md.write_text(render_markdown(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge eval results to a Launch Gate style verdict")
    parser.add_argument("--artifacts-root", default="artifacts/logs", help="artifacts root")
    parser.add_argument("--output-json", default="../docs/launch-gate-bridge.example.json", help="output json path")
    parser.add_argument("--output-md", default="../docs/launch-gate-bridge.example.md", help="output markdown path")
    args = parser.parse_args()

    module_root = Path(__file__).resolve().parents[2] / "integration-adapter"
    artifacts_root = (module_root / args.artifacts_root).resolve()
    output_json = (module_root / args.output_json).resolve()
    output_md = (module_root / args.output_md).resolve()

    payload = build_bridge_verdict(artifacts_root)
    write_outputs(payload=payload, output_json=output_json, output_md=output_md)
    print(json.dumps({"verdict": payload.get("verdict"), "output_json": str(output_json), "output_md": str(output_md)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
