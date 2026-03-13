from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from integration_adapter.integrity import verify_integrity_manifest

REQUIRED_PATHS = [
    "artifact_bundle.contract.json",
    "audit.jsonl",
    "connectors.inventory.json",
    "tools.inventory.json",
    "mcp_servers.inventory.json",
    "evals.inventory.json",
    "adapter_health/adapter_run_summary.json",
]


def _latest_launch_gate_payload(artifacts_root: Path) -> dict[str, Any] | None:
    launch_dir = artifacts_root / "launch_gate"
    if not launch_dir.exists():
        return None
    candidates = sorted(launch_dir.glob("security-readiness-*.json"))
    if not candidates:
        return None
    latest = candidates[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    payload["_path"] = str(latest)
    return payload


def _read_retention_outcome(artifacts_root: Path) -> dict[str, Any] | None:
    path = artifacts_root / "adapter_health" / "retention_last_run.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _failure_category(summary: dict[str, Any], integrity_ok: bool, launch_gate_status: str) -> str:
    run_status = str(summary.get("run_status", "unknown"))
    metrics = summary.get("metrics", {}) if isinstance(summary.get("metrics"), dict) else {}
    if run_status == "failed_run":
        if int(metrics.get("artifact_write_failures", 0) or 0) > 0:
            return "artifact_write_failure"
        return "pipeline_failure"
    if not integrity_ok:
        return "integrity_failure"
    if launch_gate_status == "no_go":
        return "launch_gate_no_go"
    if run_status == "degraded_success":
        return "degraded"
    if run_status == "success":
        return "none"
    return "unknown"


def build_health_report(*, artifacts_root: Path, integrity_mode: str = "hash_only", signing_key: str | None = None, signing_key_path: Path | None = None) -> dict[str, Any]:
    summary_path = artifacts_root / "adapter_health" / "adapter_run_summary.json"
    summary: dict[str, Any] = {}
    if summary_path.exists():
        try:
            decoded = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(decoded, dict):
                summary = decoded
        except json.JSONDecodeError:
            summary = {}

    integrity = verify_integrity_manifest(
        artifacts_root=artifacts_root,
        required_paths=REQUIRED_PATHS,
        integrity_mode=integrity_mode,
        signing_key=signing_key,
        signing_key_path=signing_key_path,
    ).to_dict()

    launch_gate_payload = _latest_launch_gate_payload(artifacts_root)
    freshness: dict[str, Any] = {"status": "unavailable", "stale_count": 0, "missing_count": 0}
    launch_gate_failure_reasons: list[str] = []
    launch_gate_status = "unknown"
    if launch_gate_payload:
        launch_gate_status = str(launch_gate_payload.get("status", "unknown"))
        checks = launch_gate_payload.get("checks", []) if isinstance(launch_gate_payload.get("checks"), list) else []
        for check in checks:
            if isinstance(check, dict) and check.get("check_name") == "evidence_freshness":
                evidence = check.get("evidence", {}) if isinstance(check.get("evidence"), dict) else {}
                stale = evidence.get("stale_critical", [])
                missing = evidence.get("missing_critical", [])
                freshness = {
                    "status": str(check.get("status", "unknown")),
                    "stale_count": len(stale) if isinstance(stale, list) else 0,
                    "missing_count": len(missing) if isinstance(missing, list) else 0,
                    "stale_critical": stale if isinstance(stale, list) else [],
                    "missing_critical": missing if isinstance(missing, list) else [],
                }
                break
        launch_gate_failure_reasons = list(launch_gate_payload.get("blockers", [])) if isinstance(launch_gate_payload.get("blockers"), list) else []

    metrics = summary.get("metrics", {}) if isinstance(summary.get("metrics"), dict) else {}
    selected_source_mode = metrics.get("selected_source_mode", {}) if isinstance(metrics.get("selected_source_mode"), dict) else {}

    report = {
        "artifacts_root": str(artifacts_root),
        "run_status": summary.get("run_status", "unknown"),
        "profile": summary.get("profile", "unknown"),
        "mode": summary.get("mode", "unknown"),
        "failure_category": _failure_category(summary, bool(integrity.get("ok")), launch_gate_status),
        "selected_source_mode": selected_source_mode,
        "fallback_usage_count": int(metrics.get("fallback_usage_count", 0) or 0),
        "parse_failures": int(metrics.get("parse_failures", 0) or 0),
        "validation_failures": int(metrics.get("schema_validation_failures", 0) or 0),
        "integrity": integrity,
        "launch_gate": {
            "status": launch_gate_status,
            "failure_reasons": launch_gate_failure_reasons,
            "failure_reasons_count": len(launch_gate_failure_reasons),
            "freshness": freshness,
            "path": launch_gate_payload.get("_path") if launch_gate_payload else "",
        },
        "retention": _read_retention_outcome(artifacts_root) or {"status": "not_run"},
    }
    return report


def _to_metrics_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    status_map = {"success": 0, "degraded_success": 1, "failed_run": 2}
    lines.append(f"integration_adapter_run_status {status_map.get(str(report.get('run_status')), 3)}")
    lines.append(f"integration_adapter_fallback_usage_count {int(report.get('fallback_usage_count', 0))}")
    lines.append(f"integration_adapter_parse_failures {int(report.get('parse_failures', 0))}")
    lines.append(f"integration_adapter_validation_failures {int(report.get('validation_failures', 0))}")
    lines.append(f"integration_adapter_integrity_ok {1 if bool((report.get('integrity') or {}).get('ok')) else 0}")
    lines.append(f"integration_adapter_launch_gate_failure_reasons {int(((report.get('launch_gate') or {}).get('failure_reasons_count', 0)))}")
    freshness = (report.get("launch_gate") or {}).get("freshness", {}) if isinstance(report.get("launch_gate"), dict) else {}
    lines.append(f"integration_adapter_freshness_stale_count {int(freshness.get('stale_count', 0) or 0)}")
    lines.append(f"integration_adapter_freshness_missing_count {int(freshness.get('missing_count', 0) or 0)}")
    retention = report.get("retention", {}) if isinstance(report.get("retention"), dict) else {}
    lines.append(f"integration_adapter_retention_deleted_count {int(retention.get('deleted_count', 0) or 0)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit operator-focused adapter health report")
    parser.add_argument("--artifacts-root", default="artifacts/logs", help="artifact root containing adapter health outputs")
    parser.add_argument("--integrity-mode", default="hash_only", choices=["hash_only", "signed_manifest"], help="integrity verification mode")
    parser.add_argument("--signing-key", default=None, help="signing key value for signed mode integrity checks")
    parser.add_argument("--signing-key-path", default=None, help="signing key file path for signed mode integrity checks")
    parser.add_argument("--format", default="json", choices=["json", "text", "metrics"], help="report output format")
    args = parser.parse_args()

    key_path = Path(args.signing_key_path) if args.signing_key_path else None
    report = build_health_report(
        artifacts_root=Path(args.artifacts_root),
        integrity_mode=args.integrity_mode,
        signing_key=args.signing_key,
        signing_key_path=key_path,
    )

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "metrics":
        print(_to_metrics_text(report))
    else:
        print(f"run_status={report['run_status']}; failure_category={report['failure_category']}; profile={report['profile']}; mode={report['mode']}")
        print(f"selected_source_mode={json.dumps(report['selected_source_mode'], sort_keys=True)}")
        print(f"fallback_usage_count={report['fallback_usage_count']}; parse_failures={report['parse_failures']}; validation_failures={report['validation_failures']}")
        print(f"integrity_ok={report['integrity'].get('ok')}; integrity_mode={report['integrity'].get('integrity_mode')}; signature_verified={report['integrity'].get('signature_verified')}")
        launch = report.get("launch_gate", {})
        print(f"launch_gate_status={launch.get('status')}; launch_gate_failure_reasons_count={launch.get('failure_reasons_count')}")
        freshness = launch.get("freshness", {}) if isinstance(launch, dict) else {}
        print(f"freshness_status={freshness.get('status')}; freshness_stale_count={freshness.get('stale_count')}; freshness_missing_count={freshness.get('missing_count')}")
        retention = report.get("retention", {}) if isinstance(report.get("retention"), dict) else {}
        print(f"retention_status={retention.get('status', 'not_run')}; retention_deleted_count={retention.get('deleted_count', 0)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
