from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integration_adapter.integrity import INTEGRITY_MANIFEST_FILENAME, verify_integrity_manifest
from integration_adapter.versioning import (
    ARTIFACT_BUNDLE_SCHEMA_VERSION,
    LAUNCH_GATE_SCHEMA_VERSION,
    NORMALIZED_SCHEMA_VERSION,
    evaluate_compatibility,
    expected_versions_from_env,
)


PASS = "pass"
WARN = "warn"
FAIL = "fail"

GO = "go"
CONDITIONAL_GO = "conditional_go"
NO_GO = "no_go"

REQUIRED_AUDIT_EVENT_TYPES = {"request.start", "policy.decision", "request.end"}
REQUIRED_IDENTITY_FIELDS = {"actor_id", "tenant_id", "authz_result", "resource_scope", "decision_basis"}
IDENTITY_AUTHZ_PROVENANCE_FIELDS = {
    "actor_id",
    "tenant_id",
    "session_id",
    "persona_or_agent_id",
    "tool_invocation_id",
    "delegation_chain",
    "decision_basis",
    "resource_scope",
    "authz_result",
}
CRITICAL_AUTHZ_PROVENANCE_FIELDS = {"actor_id", "tenant_id", "session_id", "decision_basis", "resource_scope", "authz_result"}
INTEGRITY_REQUIRED_PATHS = [
    "artifact_bundle.contract.json",
    "audit.jsonl",
    "connectors.inventory.json",
    "tools.inventory.json",
    "mcp_servers.inventory.json",
    "evals.inventory.json",
    "adapter_health/adapter_run_summary.json",
]

THREAT_CONTROL_MAP = {
    "prompt_injection_direct": ["input_sanitization", "prompt_guardrails"],
    "policy_bypass_attempt": ["policy_enforcement", "deny_path"],
}


@dataclass(frozen=True)
class GateCheck:
    check_name: str
    status: str
    details: str
    evidence: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.status == PASS


@dataclass(frozen=True)
class LaunchGateEvaluation:
    status: str
    summary: str
    checks: list[GateCheck]
    blockers: list[str]
    residual_risks: list[str]


class LaunchGateEvaluator:
    """Evaluates adapter artifacts with fail-closed semantics.

    Implemented: evidence quality/completeness checks over generated artifacts.
    Not claimed: proof of production runtime control enforcement.
    """

    def __init__(self, artifacts_root: Path) -> None:
        self.artifacts_root = artifacts_root

    def evaluate(self) -> LaunchGateEvaluation:
        checks: list[GateCheck] = [
            self._check_connector_inventory_present(),
            self._check_tool_inventory_classified(),
            self._check_mcp_inventory_classified(),
            self._check_required_audit_events_present(),
            self._check_eval_results_present(),
            self._check_evidence_freshness(),
            self._check_artifact_contract_versions(),
            self._check_source_mode_quality(),
            self._check_exporter_degradation(),
            self._check_identity_authz_evidence_presence(),
            self._check_identity_authz_provenance_quality(),
            self._check_threat_control_mapping_completeness(),
            self._check_adapter_health_summary(),
            self._check_artifact_completeness(),
            self._check_optional_artifact_degradation(),
            self._check_artifact_schema_validity(),
            self._check_artifact_integrity_manifest(),
            self._check_evidence_tampering_signals(),
            self._check_critical_failures_or_blockers(),
        ]

        blockers = [f"{check.check_name}: {check.details}" for check in checks if check.status == FAIL]
        residual_risks = [f"{check.check_name}: {check.details}" for check in checks if check.status == WARN]

        has_fail = any(check.status == FAIL for check in checks)
        has_warn = any(check.status == WARN for check in checks)
        if has_fail:
            status = NO_GO
        elif has_warn:
            status = CONDITIONAL_GO
        else:
            status = GO

        summary = (
            f"status={status}; pass={sum(c.status == PASS for c in checks)}; "
            f"warn={sum(c.status == WARN for c in checks)}; fail={sum(c.status == FAIL for c in checks)}; "
            f"blockers={len(blockers)}; residual_risks={len(residual_risks)}"
        )
        return LaunchGateEvaluation(
            status=status,
            summary=summary,
            checks=checks,
            blockers=blockers,
            residual_risks=residual_risks,
        )

    def write_outputs(self, evaluation: LaunchGateEvaluation) -> tuple[Path, Path]:
        launch_dir = self.artifacts_root / "launch_gate"
        launch_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        scorecard = [
            {
                "category_name": "integration_inventory",
                "status": self._category_status(
                    evaluation,
                    {
                        "connector_inventory_present",
                        "tool_inventory_classified",
                        "mcp_inventory_classified",
                        "source_mode_quality",
                    },
                ),
                "check_names": [
                    "connector_inventory_present",
                    "tool_inventory_classified",
                    "mcp_inventory_classified",
                    "source_mode_quality",
                ],
                "details": "Inventory quality and source-mode quality checks; does not assert runtime enforcement.",
            },
            {
                "category_name": "runtime_audit_and_eval",
                "status": self._category_status(
                    evaluation,
                    {
                        "required_audit_events_present",
                        "identity_authz_evidence_presence",
                        "identity_authz_provenance_quality",
                        "eval_results_present",
                        "threat_control_mapping_completeness",
                        "critical_failures_or_blockers",
                    },
                ),
                "check_names": [
                    "required_audit_events_present",
                    "identity_authz_evidence_presence",
                    "identity_authz_provenance_quality",
                    "eval_results_present",
                    "threat_control_mapping_completeness",
                    "critical_failures_or_blockers",
                ],
                "details": "Evidence quality and mapping coverage checks; does not prove live enforcement.",
            },
            {
                "category_name": "artifact_integrity_and_operability",
                "status": self._category_status(
                    evaluation,
                    {
                        "evidence_freshness",
                        "artifact_contract_versions",
                        "artifact_schema_validity",
                        "artifact_integrity_manifest",
                        "evidence_tampering_signals",
                        "artifact_completeness",
                        "optional_artifact_degradation",
                        "adapter_health_summary",
                        "exporter_degradation",
                    },
                ),
                "check_names": [
                    "evidence_freshness",
                    "artifact_contract_versions",
                    "artifact_schema_validity",
                    "artifact_integrity_manifest",
                    "evidence_tampering_signals",
                    "artifact_completeness",
                    "optional_artifact_degradation",
                    "adapter_health_summary",
                    "exporter_degradation",
                ],
                "details": "Fail-closed integrity and freshness checks with explicit degradation signaling.",
            },
        ]

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "launch_gate_schema_version": LAUNCH_GATE_SCHEMA_VERSION,
            "artifact_bundle_schema_version": ARTIFACT_BUNDLE_SCHEMA_VERSION,
            "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
            "status": evaluation.status,
            "summary": evaluation.summary,
            "checks_total": len(evaluation.checks),
            "checks_passed": sum(check.status == PASS for check in evaluation.checks),
            "checks_warn": sum(check.status == WARN for check in evaluation.checks),
            "checks_failed": sum(check.status == FAIL for check in evaluation.checks),
            "checks": [
                {
                    "check_name": check.check_name,
                    "status": check.status,
                    "passed": check.passed,
                    "details": check.details,
                    "evidence": check.evidence,
                }
                for check in evaluation.checks
            ],
            "scorecard": scorecard,
            "blockers": evaluation.blockers,
            "residual_risks": evaluation.residual_risks,
            "decision_breakdown": {
                "blocker_count": len(evaluation.blockers),
                "warning_count": len(evaluation.residual_risks),
            },
            "evidence_status": {
                "present": self._evidence_present(evaluation),
                "incomplete": self._evidence_incomplete(evaluation),
            },
            "control_assessment": {
                "enforced": False,
                "proven": False,
                "not_proven": True,
                "details": "Control enforcement is not proven by artifact-only checks in this workspace.",
            },
            "limitations": [
                "This launch-gate evaluates artifact quality/freshness/completeness only.",
                "It does not by itself prove runtime policy/tool enforcement in production.",
            ],
        }

        json_path = launch_dir / f"security-readiness-{stamp}.json"
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

        md_path = launch_dir / f"security-readiness-{stamp}.md"
        md_lines = [
            "# Integration Adapter Launch-Gate Summary",
            "",
            f"- generated_at: {payload['generated_at']}",
            f"- status: **{evaluation.status}**",
            f"- summary: {evaluation.summary}",
            f"- evidence_present: **{payload['evidence_status']['present']}**",
            f"- evidence_incomplete: **{payload['evidence_status']['incomplete']}**",
            f"- control_enforced: **{payload['control_assessment']['enforced']}**",
            f"- control_proven: **{payload['control_assessment']['proven']}**",
            "",
            "## Checks",
            "",
        ]
        for check in evaluation.checks:
            md_lines.append(f"- `{check.check_name}`: **{check.status}** — {check.details}")
        md_lines.extend(
            [
                "",
                "## Blockers (fail)",
                "",
                *([f"- {item}" for item in evaluation.blockers] or ["- none"]),
                "",
                "## Residual risks (warn)",
                "",
                *([f"- {item}" for item in evaluation.residual_risks] or ["- none"]),
                "",
                "## Policy",
                "",
                "- Fail-closed on missing or stale critical evidence families.",
                "- Demo-only or degraded source-quality evidence is explicitly marked as residual risk.",
                "",
                "## Limitations",
                "",
                "- Evidence quality is not equivalent to runtime control enforcement.",
                "- Deployment-specific runtime hook parity remains Unconfirmed.",
            ]
        )
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        return json_path, md_path

    def _check_connector_inventory_present(self) -> GateCheck:
        path = self.artifacts_root / "connectors.inventory.json"
        rows = self._read_json_list(path)
        if rows is None:
            return GateCheck("connector_inventory_present", FAIL, "missing or malformed connectors inventory", {"path": str(path)})
        if not rows:
            return GateCheck("connector_inventory_present", FAIL, "connectors inventory is empty", {"path": str(path)})
        return GateCheck("connector_inventory_present", PASS, f"found {len(rows)} connector records", {"count": len(rows), "path": str(path)})

    def _check_tool_inventory_classified(self) -> GateCheck:
        path = self.artifacts_root / "tools.inventory.json"
        rows = self._read_json_list(path)
        if rows is None:
            return GateCheck("tool_inventory_classified", FAIL, "missing or malformed tools inventory", {"path": str(path)})
        if not rows:
            return GateCheck("tool_inventory_classified", FAIL, "tools inventory is empty", {"path": str(path)})

        unknown = 0
        for row in rows:
            metadata = row.get("metadata") if isinstance(row, dict) else {}
            risk_tier = metadata.get("risk_tier") if isinstance(metadata, dict) else None
            if not risk_tier or str(risk_tier) in {"unspecified", "unknown"}:
                unknown += 1
        if unknown:
            return GateCheck(
                "tool_inventory_classified",
                WARN,
                f"{unknown}/{len(rows)} tools missing concrete risk classification",
                {"unknown_classifications": unknown, "count": len(rows), "path": str(path)},
            )
        return GateCheck("tool_inventory_classified", PASS, f"all {len(rows)} tools have risk classifications", {"count": len(rows), "path": str(path)})

    def _check_mcp_inventory_classified(self) -> GateCheck:
        path = self.artifacts_root / "mcp_servers.inventory.json"
        rows = self._read_json_list(path)
        if rows is None:
            return GateCheck("mcp_inventory_classified", FAIL, "missing or malformed MCP inventory", {"path": str(path)})
        if not rows:
            return GateCheck("mcp_inventory_classified", WARN, "MCP inventory empty (may be valid if MCP unused)", {"path": str(path)})

        unknown = 0
        for row in rows:
            status = str((row or {}).get("status", "unknown"))
            if status in {"unknown", ""}:
                unknown += 1
        if unknown:
            return GateCheck(
                "mcp_inventory_classified",
                WARN,
                f"{unknown}/{len(rows)} MCP servers with unknown status",
                {"unknown_status": unknown, "count": len(rows), "path": str(path)},
            )
        return GateCheck("mcp_inventory_classified", PASS, f"all {len(rows)} MCP servers have explicit status", {"count": len(rows), "path": str(path)})

    def _check_required_audit_events_present(self) -> GateCheck:
        path = self.artifacts_root / "audit.jsonl"
        if not path.exists():
            return GateCheck("required_audit_events_present", FAIL, "audit.jsonl missing", {"path": str(path)})
        event_types: set[str] = set()
        malformed = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(row, dict):
                event_types.add(str(row.get("event_type", "")))
            else:
                malformed += 1
        missing = sorted(REQUIRED_AUDIT_EVENT_TYPES - event_types)
        if malformed > 0:
            return GateCheck(
                "required_audit_events_present",
                FAIL,
                f"audit stream malformed (malformed_lines={malformed})",
                {"path": str(path), "malformed_lines": malformed, "event_types": sorted(event_types)},
            )
        if missing:
            return GateCheck(
                "required_audit_events_present",
                FAIL,
                f"missing required event types: {', '.join(missing)}",
                {"path": str(path), "event_types": sorted(event_types), "missing": missing},
            )
        return GateCheck(
            "required_audit_events_present",
            PASS,
            "required request/policy lifecycle events present",
            {"path": str(path), "event_types": sorted(event_types)},
        )

    def _check_eval_results_present(self) -> GateCheck:
        eval_dir = self.artifacts_root / "evals"
        summary_files = sorted(eval_dir.glob("*.summary.json"))
        jsonl_files = sorted(eval_dir.glob("*.jsonl"))
        if not summary_files or not jsonl_files:
            return GateCheck(
                "eval_results_present",
                FAIL,
                "missing eval JSONL or summary artifacts",
                {
                    "eval_dir": str(eval_dir),
                    "summary_files": [path.name for path in summary_files],
                    "jsonl_files": [path.name for path in jsonl_files],
                },
            )

        malformed = 0
        total_rows = 0
        for path in jsonl_files:
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if isinstance(row, dict):
                    total_rows += 1
                else:
                    malformed += 1
        if malformed > 0 or total_rows == 0:
            return GateCheck(
                "eval_results_present",
                FAIL,
                "eval evidence malformed or empty",
                {"malformed_lines": malformed, "total_rows": total_rows, "eval_dir": str(eval_dir)},
            )
        return GateCheck("eval_results_present", PASS, f"eval evidence present with {total_rows} rows", {"total_rows": total_rows, "eval_dir": str(eval_dir)})

    def _check_evidence_freshness(self) -> GateCheck:
        now = datetime.now(timezone.utc)
        critical_threshold = int(os.getenv("INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS", "86400"))
        warning_threshold = int(os.getenv("INTEGRATION_ADAPTER_MAX_WARNING_EVIDENCE_AGE_SECONDS", "172800"))

        def _age_seconds(path: Path) -> int:
            return int(now.timestamp() - path.stat().st_mtime)

        stale_critical: list[str] = []
        stale_warning: list[str] = []
        missing_critical: list[str] = []

        critical_files = [
            self.artifacts_root / "artifact_bundle.contract.json",
            self.artifacts_root / "audit.jsonl",
        ]
        eval_summaries = sorted((self.artifacts_root / "evals").glob("*.summary.json"))
        if not eval_summaries:
            missing_critical.append("evals/*.summary.json")
        for path in critical_files:
            if not path.exists():
                missing_critical.append(str(path))
            elif _age_seconds(path) > critical_threshold:
                stale_critical.append(f"{path.name} age={_age_seconds(path)}s")
        for path in eval_summaries:
            if _age_seconds(path) > critical_threshold:
                stale_critical.append(f"{path.name} age={_age_seconds(path)}s")

        warning_files = [
            self.artifacts_root / "connectors.inventory.json",
            self.artifacts_root / "tools.inventory.json",
            self.artifacts_root / "mcp_servers.inventory.json",
            self.artifacts_root / "adapter_health" / "adapter_run_summary.json",
        ]
        for path in warning_files:
            if path.exists() and _age_seconds(path) > warning_threshold:
                stale_warning.append(f"{path.name} age={_age_seconds(path)}s")

        if missing_critical or stale_critical:
            return GateCheck(
                "evidence_freshness",
                FAIL,
                "critical evidence missing or stale",
                {
                    "missing_critical": missing_critical,
                    "stale_critical": stale_critical,
                    "stale_count": len(stale_critical),
                    "critical_threshold_seconds": critical_threshold,
                },
            )
        if stale_warning:
            return GateCheck(
                "evidence_freshness",
                WARN,
                "non-critical evidence stale",
                {
                    "stale_warning": stale_warning,
                    "stale_count": len(stale_warning),
                    "warning_threshold_seconds": warning_threshold,
                },
            )
        return GateCheck("evidence_freshness", PASS, "evidence freshness policy satisfied", {"stale_count": 0})

    def _check_source_mode_quality(self) -> GateCheck:
        inventories = [
            self.artifacts_root / "connectors.inventory.json",
            self.artifacts_root / "tools.inventory.json",
            self.artifacts_root / "mcp_servers.inventory.json",
            self.artifacts_root / "evals.inventory.json",
        ]
        source_modes: list[str] = []
        for path in inventories:
            rows = self._read_json_list(path)
            if not rows:
                continue
            for row in rows:
                meta = row.get("metadata") if isinstance(row, dict) else {}
                if isinstance(meta, dict):
                    source_modes.append(str(meta.get("source_mode", "unknown")))

        if not source_modes:
            return GateCheck("source_mode_quality", WARN, "source modes unavailable for inventory quality scoring", {"source_modes": []})

        synthetic_count = sum(1 for mode in source_modes if mode == "synthetic")
        fixture_count = sum(1 for mode in source_modes if mode == "fixture_backed")
        if synthetic_count > 0:
            return GateCheck(
                "source_mode_quality",
                WARN,
                "demo-only/synthetic inventory evidence present",
                {"source_modes": source_modes, "synthetic_count": synthetic_count, "fixture_count": fixture_count},
            )
        if fixture_count > 0:
            return GateCheck(
                "source_mode_quality",
                WARN,
                "fixture-backed inventory evidence present",
                {"source_modes": source_modes, "synthetic_count": synthetic_count, "fixture_count": fixture_count},
            )
        return GateCheck("source_mode_quality", PASS, "inventory evidence sourced from file/db/live modes", {"source_modes": source_modes})

    def _check_exporter_degradation(self) -> GateCheck:
        path = self.artifacts_root / "adapter_health" / "adapter_run_summary.json"
        if not path.exists():
            return GateCheck("exporter_degradation", WARN, "adapter health missing for exporter degradation analysis", {"path": str(path)})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return GateCheck("exporter_degradation", FAIL, "adapter health malformed", {"path": str(path)})

        metrics = payload.get("metrics") if isinstance(payload, dict) else {}
        if not isinstance(metrics, dict):
            return GateCheck("exporter_degradation", FAIL, "adapter health metrics missing", {"path": str(path)})

        parse_failures = int(metrics.get("parse_failures", 0))
        fallback_count = int(metrics.get("fallback_usage_count", 0))
        partial_warnings = int(metrics.get("partial_extraction_warnings", 0))

        if parse_failures >= 3:
            return GateCheck(
                "exporter_degradation",
                FAIL,
                "high exporter parse failure count",
                {"parse_failures": parse_failures, "fallback_usage_count": fallback_count, "partial_extraction_warnings": partial_warnings},
            )
        if parse_failures > 0 or fallback_count > 0 or partial_warnings > 0:
            return GateCheck(
                "exporter_degradation",
                WARN,
                "exporter degradation signals detected",
                {"parse_failures": parse_failures, "fallback_usage_count": fallback_count, "partial_extraction_warnings": partial_warnings},
            )
        return GateCheck("exporter_degradation", PASS, "no exporter degradation signals detected", {"parse_failures": 0})

    def _check_identity_authz_evidence_presence(self) -> GateCheck:
        audit_path = self.artifacts_root / "audit.jsonl"
        if not audit_path.exists():
            return GateCheck("identity_authz_evidence_presence", FAIL, "audit.jsonl missing for identity/authz evidence", {"path": str(audit_path)})

        total = 0
        missing_count = 0
        unavailable_count = 0
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            total += 1
            for field in REQUIRED_IDENTITY_FIELDS:
                value = row.get(field)
                if value in (None, ""):
                    missing_count += 1
                if str(value) == "unavailable":
                    unavailable_count += 1

        if total == 0:
            return GateCheck("identity_authz_evidence_presence", FAIL, "no audit rows available for identity/authz evidence", {})

        fields_total = total * len(REQUIRED_IDENTITY_FIELDS)
        missing_ratio = (missing_count + unavailable_count) / fields_total if fields_total else 1.0
        if missing_ratio > 0.5:
            return GateCheck(
                "identity_authz_evidence_presence",
                FAIL,
                "identity/authz evidence largely unavailable",
                {"missing_ratio": round(missing_ratio, 3), "missing_count": missing_count, "unavailable_count": unavailable_count, "rows": total},
            )
        if missing_ratio > 0.2:
            return GateCheck(
                "identity_authz_evidence_presence",
                WARN,
                "identity/authz evidence partially unavailable",
                {"missing_ratio": round(missing_ratio, 3), "missing_count": missing_count, "unavailable_count": unavailable_count, "rows": total},
            )
        return GateCheck("identity_authz_evidence_presence", PASS, "identity/authz evidence fields present", {"rows": total, "missing_ratio": round(missing_ratio, 3)})


    def _check_identity_authz_provenance_quality(self) -> GateCheck:
        audit_path = self.artifacts_root / "audit.jsonl"
        if not audit_path.exists():
            return GateCheck("identity_authz_provenance_quality", FAIL, "audit.jsonl missing for provenance quality", {"path": str(audit_path)})

        rows: list[dict[str, Any]] = []
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)

        if not rows:
            return GateCheck("identity_authz_provenance_quality", FAIL, "no audit rows available for provenance quality", {})

        total = len(rows) * len(IDENTITY_AUTHZ_PROVENANCE_FIELDS)
        missing_provenance = 0
        unavailable_sources = 0
        critical_unavailable = 0
        derived_critical = 0

        for row in rows:
            sources = row.get("identity_authz_field_sources")
            if not isinstance(sources, dict):
                missing_provenance += len(IDENTITY_AUTHZ_PROVENANCE_FIELDS)
                critical_unavailable += len(CRITICAL_AUTHZ_PROVENANCE_FIELDS)
                continue

            for field in IDENTITY_AUTHZ_PROVENANCE_FIELDS:
                marker = str(sources.get(field, ""))
                if marker not in {"sourced", "derived", "unavailable"}:
                    missing_provenance += 1
                    if field in CRITICAL_AUTHZ_PROVENANCE_FIELDS:
                        critical_unavailable += 1
                    continue
                if marker == "unavailable":
                    unavailable_sources += 1
                    if field in CRITICAL_AUTHZ_PROVENANCE_FIELDS:
                        critical_unavailable += 1
                if marker == "derived" and field in CRITICAL_AUTHZ_PROVENANCE_FIELDS:
                    derived_critical += 1

        missing_ratio = missing_provenance / total if total else 1.0
        critical_total = len(rows) * len(CRITICAL_AUTHZ_PROVENANCE_FIELDS)
        critical_unavailable_ratio = critical_unavailable / critical_total if critical_total else 1.0
        derived_critical_ratio = derived_critical / critical_total if critical_total else 0.0

        evidence = {
            "rows": len(rows),
            "missing_provenance": missing_provenance,
            "unavailable_sources": unavailable_sources,
            "critical_unavailable": critical_unavailable,
            "missing_ratio": round(missing_ratio, 3),
            "critical_unavailable_ratio": round(critical_unavailable_ratio, 3),
            "derived_critical_ratio": round(derived_critical_ratio, 3),
        }

        if critical_unavailable_ratio > 0.2:
            return GateCheck("identity_authz_provenance_quality", FAIL, "critical identity/authz provenance largely unavailable", evidence)
        if missing_ratio > 0.15 or critical_unavailable_ratio > 0 or derived_critical_ratio > 0.7:
            return GateCheck("identity_authz_provenance_quality", WARN, "identity/authz provenance partially inferred or unavailable", evidence)
        return GateCheck("identity_authz_provenance_quality", PASS, "identity/authz provenance meets minimum quality", evidence)

    def _check_threat_control_mapping_completeness(self) -> GateCheck:
        eval_dir = self.artifacts_root / "evals"
        scenarios: list[str] = []
        for path in sorted(eval_dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    scenarios.append(str(row.get("scenario_id", "unknown-scenario")))

        if not scenarios:
            return GateCheck("threat_control_mapping_completeness", FAIL, "no eval scenarios available for threat-control mapping", {})

        mapped = [scenario for scenario in scenarios if scenario in THREAT_CONTROL_MAP]
        unmapped = sorted({scenario for scenario in scenarios if scenario not in THREAT_CONTROL_MAP})
        if not mapped:
            return GateCheck(
                "threat_control_mapping_completeness",
                FAIL,
                "threat-control mapping absent for all eval scenarios",
                {"unmapped_scenarios": unmapped, "scenario_count": len(scenarios)},
            )
        if unmapped:
            return GateCheck(
                "threat_control_mapping_completeness",
                WARN,
                "threat-control mapping incomplete",
                {"mapped_count": len(mapped), "scenario_count": len(scenarios), "unmapped_scenarios": unmapped},
            )
        return GateCheck(
            "threat_control_mapping_completeness",
            PASS,
            "threat-control mapping complete for eval scenarios",
            {"mapped_count": len(mapped), "scenario_count": len(scenarios)},
        )

    def _check_adapter_health_summary(self) -> GateCheck:
        path = self.artifacts_root / "adapter_health" / "adapter_run_summary.json"
        if not path.exists():
            return GateCheck("adapter_health_summary", WARN, "adapter health summary missing", {"path": str(path)})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return GateCheck("adapter_health_summary", FAIL, "adapter health summary malformed", {"path": str(path)})
        if not isinstance(payload, dict):
            return GateCheck("adapter_health_summary", FAIL, "adapter health summary must be object", {"path": str(path)})

        run_status = str(payload.get("run_status", "unknown"))
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
        parse_failures = int(metrics.get("parse_failures", 0)) if metrics else 0
        partial_warnings = int(metrics.get("partial_extraction_warnings", 0)) if metrics else 0
        if run_status == "failed_run":
            return GateCheck("adapter_health_summary", FAIL, "adapter health indicates failed run", {"path": str(path), "run_status": run_status})
        if run_status == "degraded_success" or parse_failures > 0 or partial_warnings > 0:
            return GateCheck(
                "adapter_health_summary",
                WARN,
                "adapter health indicates degraded run",
                {"path": str(path), "run_status": run_status, "parse_failures": parse_failures, "partial_warnings": partial_warnings},
            )
        return GateCheck("adapter_health_summary", PASS, "adapter health summary indicates success", {"path": str(path), "run_status": run_status})

    def _check_artifact_completeness(self) -> GateCheck:
        critical_required = [
            self.artifacts_root / "artifact_bundle.contract.json",
            self.artifacts_root / "audit.jsonl",
            self.artifacts_root / "connectors.inventory.json",
            self.artifacts_root / "tools.inventory.json",
            self.artifacts_root / "evals",
            self.artifacts_root / "launch_gate",
        ]
        missing_critical: list[str] = []
        for path in critical_required:
            if path.suffix:
                if not path.is_file():
                    missing_critical.append(str(path))
            else:
                if not path.is_dir():
                    missing_critical.append(str(path))

        if missing_critical:
            return GateCheck(
                "artifact_completeness",
                FAIL,
                "critical artifact absence detected",
                {"missing_critical": missing_critical},
            )
        return GateCheck("artifact_completeness", PASS, "critical artifact files and directories present", {})

    def _check_optional_artifact_degradation(self) -> GateCheck:
        optional_missing: list[str] = []
        optional_paths = [
            self.artifacts_root / "mcp_servers.inventory.json",
            self.artifacts_root / "replay",
            self.artifacts_root / "adapter_health" / "adapter_run_summary.json",
        ]
        for path in optional_paths:
            if path.suffix:
                if not path.exists():
                    optional_missing.append(str(path))
            else:
                if not path.exists():
                    optional_missing.append(str(path))

        replay_files = sorted((self.artifacts_root / "replay").glob("*.replay.json")) if (self.artifacts_root / "replay").exists() else []
        if not replay_files:
            optional_missing.append(str(self.artifacts_root / "replay/*.replay.json"))

        if optional_missing:
            return GateCheck(
                "optional_artifact_degradation",
                WARN,
                "optional artifact degradation detected",
                {"missing_optional": optional_missing},
            )
        return GateCheck("optional_artifact_degradation", PASS, "optional artifact families present", {"replay_files": len(replay_files)})

    def _check_artifact_contract_versions(self) -> GateCheck:
        path = self.artifacts_root / "artifact_bundle.contract.json"
        if not path.exists():
            return GateCheck("artifact_contract_versions", FAIL, "artifact bundle contract file missing", {"path": str(path)})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return GateCheck("artifact_contract_versions", FAIL, "artifact bundle contract malformed", {"path": str(path)})
        if not isinstance(payload, dict):
            return GateCheck("artifact_contract_versions", FAIL, "artifact bundle contract must be an object", {"path": str(path)})

        expected = expected_versions_from_env()
        required = {
            "source_schema_version": ("source_schema", expected["source_schema"]),
            "normalized_schema_version": ("normalized_schema", expected["normalized_schema"]),
            "artifact_bundle_schema_version": ("artifact_bundle_schema", expected["artifact_bundle_schema"]),
            "launch_gate_schema_version": ("launch_gate_schema", expected["launch_gate_schema"]),
        }
        blocked: list[dict[str, str]] = []
        warn_only: list[dict[str, str]] = []
        for key, (contract_name, expected_version) in required.items():
            actual = payload.get(key)
            if not isinstance(actual, str):
                blocked.append({"contract_name": contract_name, "reason": f"{key} missing or not string"})
                continue
            decision = evaluate_compatibility(
                contract_name=contract_name,
                expected_version=expected_version,
                actual_version=actual,
            )
            evidence = {
                "contract_name": contract_name,
                "expected_version": expected_version,
                "actual_version": actual,
                "reason": decision.reason,
            }
            if decision.status == "blocked":
                blocked.append(evidence)
            elif decision.status == "warn_only":
                warn_only.append(evidence)

        if blocked:
            return GateCheck(
                "artifact_contract_versions",
                FAIL,
                "artifact contract version compatibility blocked",
                {"path": str(path), "blocked": blocked, "warn_only": warn_only},
            )
        if warn_only:
            return GateCheck(
                "artifact_contract_versions",
                WARN,
                "artifact contract version compatibility has forward minor drift",
                {"path": str(path), "warn_only": warn_only},
            )
        return GateCheck(
            "artifact_contract_versions",
            PASS,
            "artifact contract versions compatible",
            {"path": str(path)},
        )

    def _check_artifact_schema_validity(self) -> GateCheck:
        schema_issues: list[str] = []

        connectors = self._read_json_list(self.artifacts_root / "connectors.inventory.json")
        if connectors is None:
            schema_issues.append("connectors.inventory.json malformed")
        else:
            for idx, row in enumerate(connectors):
                if not all(field in row for field in ("record_id", "name", "status", "metadata")):
                    schema_issues.append(f"connectors.inventory.json row[{idx}] missing required fields")
                metadata = row.get("metadata") if isinstance(row, dict) else None
                if isinstance(metadata, dict) and "normalized_schema_version" not in metadata:
                    schema_issues.append(f"connectors.inventory.json row[{idx}] missing metadata.normalized_schema_version")

        tools = self._read_json_list(self.artifacts_root / "tools.inventory.json")
        if tools is None:
            schema_issues.append("tools.inventory.json malformed")
        else:
            for idx, row in enumerate(tools):
                metadata = row.get("metadata") if isinstance(row, dict) else None
                if not isinstance(metadata, dict):
                    schema_issues.append(f"tools.inventory.json row[{idx}] missing metadata object")
                    continue
                if "risk_tier" not in metadata:
                    schema_issues.append(f"tools.inventory.json row[{idx}] missing metadata.risk_tier")
                if "normalized_schema_version" not in metadata:
                    schema_issues.append(f"tools.inventory.json row[{idx}] missing metadata.normalized_schema_version")

        mcp = self._read_json_list(self.artifacts_root / "mcp_servers.inventory.json")
        if mcp is None and (self.artifacts_root / "mcp_servers.inventory.json").exists():
            schema_issues.append("mcp_servers.inventory.json malformed")

        audit_path = self.artifacts_root / "audit.jsonl"
        if audit_path.exists():
            for idx, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines()):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    schema_issues.append(f"audit.jsonl line {idx+1} malformed json")
                    continue
                if not isinstance(row, dict) or "event_type" not in row:
                    schema_issues.append(f"audit.jsonl line {idx+1} missing event_type")
                    continue
                if "normalized_schema_version" not in row:
                    schema_issues.append(f"audit.jsonl line {idx+1} missing normalized_schema_version")

        eval_jsonls = sorted((self.artifacts_root / "evals").glob("*.jsonl"))
        for path in eval_jsonls:
            for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    schema_issues.append(f"{path.name} line {idx+1} malformed json")
                    continue
                if not isinstance(row, dict) or "outcome" not in row or "severity" not in row:
                    schema_issues.append(f"{path.name} line {idx+1} missing outcome/severity")
                    continue
                if "normalized_schema_version" not in row:
                    schema_issues.append(f"{path.name} line {idx+1} missing normalized_schema_version")

        if schema_issues:
            return GateCheck(
                "artifact_schema_validity",
                FAIL,
                "artifact schema validation failed",
                {"schema_issues": schema_issues},
            )
        return GateCheck(
            "artifact_schema_validity",
            PASS,
            "artifact schema validation passed",
            {},
        )



    def _check_artifact_integrity_manifest(self) -> GateCheck:
        result = verify_integrity_manifest(
            artifacts_root=self.artifacts_root,
            required_paths=INTEGRITY_REQUIRED_PATHS,
        )
        if not result.ok:
            return GateCheck(
                "artifact_integrity_manifest",
                FAIL,
                "artifact integrity manifest verification failed",
                result.to_dict() | {"manifest": INTEGRITY_MANIFEST_FILENAME},
            )
        return GateCheck(
            "artifact_integrity_manifest",
            PASS,
            "artifact integrity manifest verified",
            {"manifest": INTEGRITY_MANIFEST_FILENAME},
        )

    def _check_evidence_tampering_signals(self) -> GateCheck:
        contract_path = self.artifacts_root / "artifact_bundle.contract.json"
        audit_path = self.artifacts_root / "audit.jsonl"

        if not contract_path.exists() or not audit_path.exists():
            return GateCheck(
                "evidence_tampering_signals",
                FAIL,
                "required artifacts missing for tampering checks",
                {"contract_exists": contract_path.exists(), "audit_exists": audit_path.exists()},
            )

        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return GateCheck("evidence_tampering_signals", FAIL, "artifact contract malformed", {"path": str(contract_path)})

        expected_norm = str(contract.get("normalized_schema_version", ""))
        mismatched_rows = 0
        total_rows = 0
        malformed_rows = 0

        for line in audit_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                malformed_rows += 1
                continue
            if not isinstance(row, dict):
                malformed_rows += 1
                continue
            total_rows += 1
            actual_norm = str(row.get("normalized_schema_version", ""))
            if expected_norm and actual_norm and actual_norm != expected_norm:
                mismatched_rows += 1

        if malformed_rows > 0:
            return GateCheck(
                "evidence_tampering_signals",
                FAIL,
                "audit evidence malformed during tampering consistency check",
                {"malformed_rows": malformed_rows, "total_rows": total_rows},
            )
        if mismatched_rows > 0:
            return GateCheck(
                "evidence_tampering_signals",
                FAIL,
                "contract/audit schema version mismatch detected",
                {
                    "expected_normalized_schema_version": expected_norm,
                    "mismatched_rows": mismatched_rows,
                    "total_rows": total_rows,
                },
            )
        return GateCheck("evidence_tampering_signals", PASS, "no contract/audit tampering signals detected", {"total_rows": total_rows})

    def _check_critical_failures_or_blockers(self) -> GateCheck:
        eval_dir = self.artifacts_root / "evals"
        critical_failures: list[str] = []
        for path in sorted(eval_dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    return GateCheck(
                        "critical_failures_or_blockers",
                        FAIL,
                        f"malformed eval row in {path.name}",
                        {"path": str(path)},
                    )
                if not isinstance(row, dict):
                    return GateCheck(
                        "critical_failures_or_blockers",
                        FAIL,
                        f"non-object eval row in {path.name}",
                        {"path": str(path)},
                    )
                outcome = str(row.get("outcome", "unknown"))
                severity = str(row.get("severity", "unknown"))
                if outcome == "fail" and severity in {"critical", "high"}:
                    scenario = str(row.get("scenario_id", "unknown-scenario"))
                    critical_failures.append(f"{scenario} ({severity})")
        if critical_failures:
            return GateCheck(
                "critical_failures_or_blockers",
                FAIL,
                "critical/high eval failures detected",
                {"critical_failures": critical_failures},
            )
        return GateCheck("critical_failures_or_blockers", PASS, "no critical/high eval failures detected", {})

    def _read_json_list(self, path: Path) -> list[dict[str, Any]] | None:
        if not path.exists() or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, list):
            return None
        rows: list[dict[str, Any]] = []
        for row in payload:
            if not isinstance(row, dict):
                return None
            rows.append(row)
        return rows

    def _category_status(self, evaluation: LaunchGateEvaluation, check_names: set[str]) -> str:
        checks = [check for check in evaluation.checks if check.check_name in check_names]
        if any(check.status == FAIL for check in checks):
            return FAIL
        if any(check.status == WARN for check in checks):
            return WARN
        return PASS

    def _evidence_present(self, evaluation: LaunchGateEvaluation) -> bool:
        required = {
            "connector_inventory_present",
            "tool_inventory_classified",
            "required_audit_events_present",
            "identity_authz_evidence_presence",
            "eval_results_present",
            "threat_control_mapping_completeness",
            "artifact_completeness",
            "artifact_schema_validity",
            "artifact_contract_versions",
            "evidence_freshness",
        }
        check_by_name = {check.check_name: check for check in evaluation.checks}
        return all(check_by_name.get(name) and check_by_name[name].status != FAIL for name in required)

    def _evidence_incomplete(self, evaluation: LaunchGateEvaluation) -> bool:
        return any(check.status in {WARN, FAIL} for check in evaluation.checks)
