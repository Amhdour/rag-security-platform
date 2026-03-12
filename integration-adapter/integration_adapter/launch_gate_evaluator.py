from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PASS = "pass"
WARN = "warn"
FAIL = "fail"

GO = "go"
CONDITIONAL_GO = "conditional_go"
NO_GO = "no_go"

REQUIRED_AUDIT_EVENT_TYPES = {"request.start", "policy.decision", "request.end"}


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

    Implemented: evidence presence/quality checks over generated artifacts.
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
            self._check_artifact_completeness(),
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
                    {"connector_inventory_present", "tool_inventory_classified", "mcp_inventory_classified"},
                ),
                "check_names": ["connector_inventory_present", "tool_inventory_classified", "mcp_inventory_classified"],
                "details": "Evidence-only inventory coverage checks; does not assert runtime enforcement.",
            },
            {
                "category_name": "runtime_audit_and_eval",
                "status": self._category_status(
                    evaluation,
                    {"required_audit_events_present", "eval_results_present", "critical_failures_or_blockers"},
                ),
                "check_names": ["required_audit_events_present", "eval_results_present", "critical_failures_or_blockers"],
                "details": "Artifact presence and outcomes; does not prove live enforcement.",
            },
            {
                "category_name": "artifact_integrity",
                "status": self._category_status(evaluation, {"artifact_completeness"}),
                "check_names": ["artifact_completeness"],
                "details": "Fail-closed completeness checks for required artifact files.",
            },
        ]

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
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
            "limitations": [
                "This launch-gate evaluates evidence artifacts and output quality only.",
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
            "",
            "## Checks",
            "",
        ]
        for check in evaluation.checks:
            md_lines.append(f"- `{check.check_name}`: **{check.status}** — {check.details}")
        md_lines.extend(
            [
                "",
                "## Blockers",
                "",
                *([f"- {item}" for item in evaluation.blockers] or ["- none"]),
                "",
                "## Residual risks",
                "",
                *([f"- {item}" for item in evaluation.residual_risks] or ["- none"]),
                "",
                "## Limitations",
                "",
                "- Evidence presence is not equivalent to control enforcement.",
                "- Missing or malformed evidence fails checks closed.",
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

    def _check_artifact_completeness(self) -> GateCheck:
        required = [
            self.artifacts_root / "audit.jsonl",
            self.artifacts_root / "connectors.inventory.json",
            self.artifacts_root / "tools.inventory.json",
            self.artifacts_root / "mcp_servers.inventory.json",
            self.artifacts_root / "evals",
            self.artifacts_root / "replay",
            self.artifacts_root / "launch_gate",
        ]
        missing: list[str] = []
        for path in required:
            if path.suffix:
                if not path.is_file():
                    missing.append(str(path))
            else:
                if not path.is_dir():
                    missing.append(str(path))
        replay_files = sorted((self.artifacts_root / "replay").glob("*.replay.json")) if (self.artifacts_root / "replay").exists() else []
        if not replay_files:
            missing.append(str(self.artifacts_root / "replay/*.replay.json"))
        if missing:
            return GateCheck("artifact_completeness", FAIL, "required artifact paths missing", {"missing": missing})
        return GateCheck("artifact_completeness", PASS, "required artifact files and directories present", {"replay_files": len(replay_files)})

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
