from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integration_adapter.control_matrix import build_control_matrix


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    matches = sorted(directory.glob(pattern))
    return matches[-1] if matches else None


def _read_eval_rows(artifacts_root: Path) -> tuple[list[dict[str, Any]], Path | None, Path | None]:
    evals_dir = artifacts_root / "evals"
    jsonl_path = _latest_file(evals_dir, "*.jsonl")
    summary_path = _latest_file(evals_dir, "*.summary.json")
    if jsonl_path is None:
        return [], None, summary_path

    rows: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"score": "warn", "rationale": "malformed eval row", "raw": line})
    return rows, jsonl_path, summary_path


def _latest_launch_gate(artifacts_root: Path) -> tuple[dict[str, Any], Path | None]:
    path = _latest_file(artifacts_root / "launch_gate", "*.json")
    if path is None:
        return {}, None
    payload = _load_json(path)
    return payload, path


def _build_report_payload(artifacts_root: Path) -> dict[str, Any]:
    rows, eval_jsonl_path, eval_summary_path = _read_eval_rows(artifacts_root)
    eval_summary = _load_json(eval_summary_path) if eval_summary_path else {}
    launch_gate, launch_gate_path = _latest_launch_gate(artifacts_root)

    control_rows = build_control_matrix()
    threats_covered = sorted({row.threat for row in control_rows})
    controls_implemented = sorted({row.control for row in control_rows})

    outcomes = {"pass": 0, "fail": 0, "warn": 0}
    for row in rows:
        score = str(row.get("score", "warn"))
        outcomes[score] = outcomes.get(score, 0) + 1

    blocked = [
        {
            "scenario_id": row.get("scenario_id", "unknown"),
            "category": row.get("category", "unknown"),
            "rationale": row.get("rationale", ""),
        }
        for row in rows
        if str(row.get("score", "")).lower() == "pass"
        and any(word in str(row.get("rationale", "")).lower() for word in ["blocked", "denied", "gated"])
    ]

    limitations: list[str] = []
    if not rows:
        limitations.append("No eval JSONL rows found under artifacts root.")
    if outcomes.get("warn", 0) > 0:
        limitations.append(f"Eval run contains {outcomes['warn']} warning scenarios.")
    if outcomes.get("fail", 0) > 0:
        limitations.append(f"Eval run contains {outcomes['fail']} failing scenarios.")
    gate_status = str(launch_gate.get("status", "unknown"))
    if gate_status != "go":
        limitations.append(f"Launch-gate status is `{gate_status}` in latest artifact.")
    if not limitations:
        limitations.append("No additional limitations detected from current artifact set.")

    appendix_refs = sorted(
        {
            "implementation": sorted({row.implementation for row in control_rows}),
            "tests": sorted({row.tests for row in control_rows}),
            "evidence": sorted({row.evidence for row in control_rows}),
            "source_artifacts": [
                str(eval_jsonl_path) if eval_jsonl_path else "",
                str(eval_summary_path) if eval_summary_path else "",
                str(launch_gate_path) if launch_gate_path else "",
            ],
        }.items()
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts_root": str(artifacts_root),
        "executive_summary": {
            "statement": "Implemented: Evidence report summarizes current workspace artifacts without claiming unverified production enforcement.",
            "eval_rows_analyzed": len(rows),
            "latest_launch_gate_status": gate_status,
            "outcomes": outcomes,
        },
        "threats_covered": threats_covered,
        "controls_implemented": controls_implemented,
        "eval_results": {
            "latest_eval_jsonl": str(eval_jsonl_path) if eval_jsonl_path else "",
            "latest_eval_summary": str(eval_summary_path) if eval_summary_path else "",
            "summary_payload": eval_summary,
            "outcomes": outcomes,
        },
        "notable_blocked_scenarios": blocked,
        "limitations": limitations,
        "reviewer_appendix": {
            key: value for key, value in appendix_refs
        },
    }
    return payload


def _to_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("executive_summary", {})
    lines = [
        "# Evidence Summary Report",
        "",
        "**Implemented:** This report is generated from repository artifacts and control-matrix mappings.",
        "**Unconfirmed:** canonical runtime hook not validated in this workspace.",
        "",
        "## Executive summary",
        f"- Statement: {summary.get('statement', '')}",
        f"- Eval rows analyzed: {summary.get('eval_rows_analyzed', 0)}",
        f"- Latest launch-gate status: `{summary.get('latest_launch_gate_status', 'unknown')}`",
        f"- Outcomes: `{json.dumps(summary.get('outcomes', {}), sort_keys=True)}`",
        "",
        "## Threats covered",
    ]
    for item in payload.get("threats_covered", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Controls implemented")
    for item in payload.get("controls_implemented", []):
        lines.append(f"- {item}")

    eval_results = payload.get("eval_results", {})
    lines.extend(
        [
            "",
            "## Eval results",
            f"- Latest eval JSONL: `{eval_results.get('latest_eval_jsonl', '')}`",
            f"- Latest eval summary: `{eval_results.get('latest_eval_summary', '')}`",
            f"- Outcomes: `{json.dumps(eval_results.get('outcomes', {}), sort_keys=True)}`",
        ]
    )

    lines.append("")
    lines.append("## Notable blocked scenarios")
    blocked = payload.get("notable_blocked_scenarios", [])
    if blocked:
        for row in blocked:
            lines.append(
                f"- `{row.get('scenario_id', 'unknown')}` ({row.get('category', 'unknown')}): {row.get('rationale', '')}"
            )
    else:
        lines.append("- None observed in latest eval artifact.")

    lines.append("")
    lines.append("## Limitations")
    for item in payload.get("limitations", []):
        lines.append(f"- {item}")

    appendix = payload.get("reviewer_appendix", {})
    lines.extend(["", "## Reviewer appendix (file references)"])
    lines.append("- Implementation modules:")
    for path in appendix.get("implementation", []):
        lines.append(f"  - `{path}`")
    lines.append("- Test coverage:")
    for path in appendix.get("tests", []):
        lines.append(f"  - `{path}`")
    lines.append("- Evidence artifact patterns:")
    for path in appendix.get("evidence", []):
        lines.append(f"  - `{path}`")
    lines.append("- Source artifacts used for this report:")
    for path in appendix.get("source_artifacts", []):
        if path:
            lines.append(f"  - `{path}`")

    return "\n".join(lines) + "\n"


def _to_html(payload: dict[str, Any]) -> str:
    md = _to_markdown(payload)
    escaped = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<html><head><meta charset='utf-8'><title>Evidence Summary Report</title>"
        "<style>body{font-family:Arial,Helvetica,sans-serif;max-width:980px;margin:20px auto;line-height:1.4;}pre{white-space:pre-wrap;}</style>"
        "</head><body><pre>" + escaped + "</pre></body></html>"
    )


def generate_evidence_report(*, artifacts_root: Path, output_md: Path, output_json: Path, output_html: Path | None = None) -> dict[str, Any]:
    payload = _build_report_payload(artifacts_root)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(_to_markdown(payload), encoding="utf-8")
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if output_html is not None:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(_to_html(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate conservative evidence summary report from repository artifacts")
    parser.add_argument("--artifacts-root", default="artifacts/logs", help="artifacts root to analyze")
    parser.add_argument("--output-md", default="../docs/evidence-summary.md", help="markdown output path")
    parser.add_argument("--output-json", default="artifacts/logs/evidence-summary.json", help="json output path")
    parser.add_argument("--output-html", default="", help="optional html output path")
    args = parser.parse_args()

    module_root = Path(__file__).resolve().parents[2] / "integration-adapter"
    artifacts_root = (module_root / args.artifacts_root).resolve()
    output_md = (module_root / args.output_md).resolve()
    output_json = (module_root / args.output_json).resolve()
    output_html = (module_root / args.output_html).resolve() if args.output_html else None

    payload = generate_evidence_report(
        artifacts_root=artifacts_root,
        output_md=output_md,
        output_json=output_json,
        output_html=output_html,
    )
    print(
        json.dumps(
            {
                "output_md": str(output_md),
                "output_json": str(output_json),
                "output_html": str(output_html) if output_html else "",
                "eval_rows_analyzed": payload.get("executive_summary", {}).get("eval_rows_analyzed", 0),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
