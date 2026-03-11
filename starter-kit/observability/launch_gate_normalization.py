"""Adapter helpers for launch-gate readiness artifacts.

Thin adapter layer to tolerate minor output-shape differences while preserving
read-only behavior and not changing launch-gate enforcement logic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Mapping


def parse_launch_gate_report(path: Path) -> dict[str, object] | None:
    """Parse one launch-gate JSON artifact into a normalized dashboard shape."""

    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    checks_raw = payload.get("checks", [])
    checks = [item for item in checks_raw if isinstance(item, dict)]

    blockers = _as_str_list(payload.get("blockers", []))
    residual = _as_str_list(payload.get("residual_risks", []))

    passed_checks = [item for item in checks if bool(item.get("passed", False))]
    failed_checks = [item for item in checks if not bool(item.get("passed", False))]
    missing_checks = [item for item in checks if str(item.get("status", "")).lower() == "missing"]

    missing_evidence: list[dict[str, str]] = []
    for item in missing_checks:
        missing_evidence.append(
            {
                "check_name": str(item.get("check_name", "")),
                "details": str(item.get("details", "")),
            }
        )

    # Fallback heuristic when explicit missing status is unavailable.
    if not missing_evidence:
        for item in failed_checks:
            details = str(item.get("details", ""))
            if "missing" in details.lower() or "not found" in details.lower():
                missing_evidence.append(
                    {
                        "check_name": str(item.get("check_name", "")),
                        "details": details,
                    }
                )

    return {
        "report_id": path.name,
        "latest_artifact_timestamp": _extract_timestamp(path),
        "status": str(payload.get("status", "unknown")),
        "summary": str(payload.get("summary", "")),
        "blockers": blockers,
        "residual_risks": residual,
        "checks": checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "missing_evidence": missing_evidence,
        "scorecard": [item for item in payload.get("scorecard", []) if isinstance(item, dict)],
        "snapshot": {
            "status": str(payload.get("status", "unknown")),
            "check_total": len(checks),
            "check_passed": len(passed_checks),
            "check_failed": len(failed_checks),
            "blocker_count": len(blockers),
            "residual_risk_count": len(residual),
            "missing_evidence_count": len(missing_evidence),
        },
        "readiness_legend": {
            "readiness": "Launch-gate readiness is a release decision signal over evidence and controls.",
            "runtime_enforcement": "Runtime enforcement remains in policy/retrieval/tool pathways and is not controlled by this dashboard.",
        },
    }


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _extract_timestamp(path: Path) -> str | None:
    name = path.name
    match = re.search(r"(\d{8}T\d{6}Z)", name)
    if match:
        return match.group(1)
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None
