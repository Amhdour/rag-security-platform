from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from integration_adapter.config import AdapterConfig
from integration_adapter.integrity import build_integrity_manifest
from integration_adapter.schemas import InventoryRecord, LaunchGateSummary, NormalizedAuditEvent
from integration_adapter.versioning import (
    ARTIFACT_BUNDLE_SCHEMA_VERSION,
    LAUNCH_GATE_SCHEMA_VERSION,
    NORMALIZED_SCHEMA_VERSION,
    RAW_SOURCE_SCHEMA_VERSION,
)


class ArtifactWriter:
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config
        self.config.ensure_dirs()

    @property
    def root(self) -> Path:
        return self.config.artifacts_root

    def write_bundle_contract(self, *, source_schema_version: str = RAW_SOURCE_SCHEMA_VERSION) -> Path:
        path = self.root / "artifact_bundle.contract.json"
        payload = {
            "artifact_bundle_schema_version": ARTIFACT_BUNDLE_SCHEMA_VERSION,
            "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
            "source_schema_version": source_schema_version,
            "launch_gate_schema_version": LAUNCH_GATE_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_audit_events(self, events: Iterable[NormalizedAuditEvent]) -> Path:
        path = self.root / "audit.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for event in events:
                payload = event.to_dict()
                payload["normalized_schema_version"] = NORMALIZED_SCHEMA_VERSION
                payload["artifact_bundle_schema_version"] = ARTIFACT_BUNDLE_SCHEMA_VERSION
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return path

    def write_replay(self, *, replay_id: str, payload: dict[str, object]) -> Path:
        path = self.root / "replay" / f"{replay_id}.replay.json"
        enriched = {
            **payload,
            "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
            "artifact_bundle_schema_version": ARTIFACT_BUNDLE_SCHEMA_VERSION,
        }
        path.write_text(json.dumps(enriched, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_eval_results(self, *, run_id: str, rows: list[dict[str, object]]) -> tuple[Path, Path]:
        jsonl_path = self.root / "evals" / f"{run_id}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                enriched = {
                    **row,
                    "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
                    "artifact_bundle_schema_version": ARTIFACT_BUNDLE_SCHEMA_VERSION,
                }
                handle.write(json.dumps(enriched, sort_keys=True) + "\n")

        total = len(rows)
        passed = sum(1 for row in rows if row.get("outcome") == "pass")
        summary_path = self.root / "evals" / f"{run_id}.summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "suite_name": run_id,
                    "passed": passed == total if total else False,
                    "total": total,
                    "passed_count": passed,
                    "outcomes": dict(Counter(str(row.get("outcome", "unknown")) for row in rows)),
                    "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
                    "artifact_bundle_schema_version": ARTIFACT_BUNDLE_SCHEMA_VERSION,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return jsonl_path, summary_path

    def write_inventory_snapshot(self, *, domain: str, rows: list[InventoryRecord]) -> Path:
        path = self.root / f"{domain}.inventory.json"
        payload = []
        for row in rows:
            metadata = dict(row.metadata)
            metadata.setdefault("normalized_schema_version", NORMALIZED_SCHEMA_VERSION)
            metadata.setdefault("artifact_bundle_schema_version", ARTIFACT_BUNDLE_SCHEMA_VERSION)
            payload.append(
                {
                    "domain": row.domain,
                    "record_id": row.record_id,
                    "name": row.name,
                    "status": row.status,
                    "metadata": metadata,
                }
            )

        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_integrity_manifest(self, *, file_paths: list[Path]) -> Path:
        return build_integrity_manifest(artifacts_root=self.root, file_paths=file_paths)


    def write_adapter_health_summary(self, payload: dict[str, object]) -> Path:
        path = self.root / "adapter_health" / "adapter_run_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_launch_gate_summary(self, *, statuses: list[str], blockers: list[str], residual_risks: list[str]) -> Path:
        checks_total = len(statuses)
        checks_passed = sum(1 for status in statuses if status == "pass")
        status = "go" if checks_total and checks_passed == checks_total else "no_go"
        report = LaunchGateSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            status=status,
            checks_passed=checks_passed,
            checks_total=checks_total,
            blockers=blockers,
            residual_risks=residual_risks,
        )
        checks = [
            {
                "check_name": f"adapter_check_{idx+1}",
                "status": "pass" if value == "pass" else "fail",
                "passed": value == "pass",
                "details": "generated by integration adapter",
            }
            for idx, value in enumerate(statuses)
        ]
        payload = {
            **report.to_dict(),
            "summary": f"status={status}; checks_passed={checks_passed}/{checks_total}; blockers={len(blockers)}; residual_risks={len(residual_risks)}",
            "checks": checks,
            "scorecard": [
                {
                    "category_name": "integration_adapter",
                    "status": "pass" if status == "go" else "fail",
                }
            ],
            "launch_gate_schema_version": LAUNCH_GATE_SCHEMA_VERSION,
            "artifact_bundle_schema_version": ARTIFACT_BUNDLE_SCHEMA_VERSION,
            "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
        }
        filename = datetime.now(timezone.utc).strftime("security-readiness-%Y%m%dT%H%M%SZ.json")
        path = self.root / "launch_gate" / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path
