from pathlib import Path
import json
from datetime import datetime, timezone
from dataclasses import asdict
from typing import Mapping, Sequence

from observability.contracts import EvalRunSummary, ReplaySummary, TraceSummary
from observability.artifact_paths import ArtifactPaths
from observability.eval_normalization import (
    high_critical_failures,
    parse_eval_jsonl,
    parse_eval_scenario_catalog,
    parse_eval_summary,
    summarize_baseline_coverage,
    summarize_eval_categories,
)
from observability.launch_gate_normalization import parse_launch_gate_report
from observability.trace_normalization import build_trace_explanations, load_replay_links, read_audit_jsonl


class DashboardService:
    """Read-only query service over audit, replay, eval, verification, and launch-gate artifacts."""

    def __init__(self, repo_root: Path, *, artifacts_root: str | Path = "artifacts/logs") -> None:
        self.paths = ArtifactPaths.from_root(repo_root=repo_root, artifacts_root=artifacts_root)

    def get_overview(self) -> dict[str, object]:
        traces = self.list_traces()
        replay = self.list_replay_artifacts()
        evals = self.list_eval_runs()
        launch_gate = self.get_latest_launch_gate()
        verification = self.get_latest_verification()
        readiness_card = {
            "status": launch_gate.get("status") if isinstance(launch_gate, dict) else None,
            "passed_checks": (launch_gate.get("snapshot", {}) or {}).get("check_passed") if isinstance(launch_gate, dict) else None,
            "total_checks": (launch_gate.get("snapshot", {}) or {}).get("check_total") if isinstance(launch_gate, dict) else None,
            "blockers": len(launch_gate.get("blockers", [])) if isinstance(launch_gate, dict) else 0,
            "residual_risks": len(launch_gate.get("residual_risks", [])) if isinstance(launch_gate, dict) else 0,
            "missing_evidence": len(launch_gate.get("missing_evidence", [])) if isinstance(launch_gate, dict) else 0,
            "latest_artifact_timestamp": launch_gate.get("latest_artifact_timestamp") if isinstance(launch_gate, dict) else None,
        }
        explanations = self._build_trace_explanations()
        connected = self._summarize_trace_connections(explanations, eval_runs=evals, launch_gate=launch_gate, verification=verification)
        integrity = self._artifact_integrity_overview(replay=replay, evals=evals, launch_gate=launch_gate, verification=verification)
        empty_state = self._build_empty_state(traces=traces, replay=replay, evals=evals, launch_gate=launch_gate)
        return {
            "counts": {
                "traces": len(traces),
                "replay_artifacts": len(replay),
                "eval_runs": len(evals),
            },
            "latest": {
                "launch_gate_status": launch_gate.get("status") if isinstance(launch_gate, dict) else None,
                "verification_status": verification.get("status") if isinstance(verification, dict) else None,
            },
            "readiness_card": readiness_card,
            "connected_evidence_summary": connected,
            "artifact_integrity": integrity,
            "evidence_sources": [
                {
                    "type": "audit_jsonl",
                    "path": self.paths.relative(self.paths.audit_jsonl),
                    "timestamp": _file_timestamp(self.paths.audit_jsonl),
                },
                {
                    "type": "replay_artifact",
                    "path": replay[0].get("path") if replay else None,
                    "timestamp": _first_present(replay, "artifact_timestamp"),
                },
                {
                    "type": "eval_summary_json",
                    "path": evals[0].get("summary_path") if evals else None,
                    "timestamp": _first_present(evals, "summary_timestamp"),
                },
                {
                    "type": "launch_gate_report",
                    "path": launch_gate.get("path") if isinstance(launch_gate, dict) else None,
                    "timestamp": launch_gate.get("latest_artifact_timestamp") if isinstance(launch_gate, dict) else None,
                },
                {
                    "type": "verification_summary",
                    "path": verification.get("path") if isinstance(verification, dict) else None,
                    "timestamp": verification.get("artifact_timestamp") if isinstance(verification, dict) else None,
                },
                {
                    "type": "static_boundary_metadata",
                    "path": "observability/web/static/security_boundaries.json",
                    "timestamp": _file_timestamp(self.paths.repo_root / "observability/web/static/security_boundaries.json"),
                },
            ],
            "read_only": True,
            "demo_mode": self.paths.demo_mode,
            "artifacts_root": self.paths.relative(self.paths.artifacts_root),
            "empty_state": empty_state,
        }

    def list_traces(self, filters: Mapping[str, str] | None = None) -> list[dict[str, object]]:
        explanations = self._build_trace_explanations()
        rows: list[dict[str, object]] = []
        for explanation in explanations:
            ids = explanation.get("ids", {})
            actor = explanation.get("actor", {})
            timeline = explanation.get("timeline", [])
            event_types = sorted({str(item.get("event_type", "")) for item in timeline if isinstance(item, Mapping)})
            summary = TraceSummary(
                trace_id=str(ids.get("trace_id", "")),
                request_id=str(ids.get("request_id", "")),
                actor_id=str(actor.get("actor_id", "")),
                tenant_id=str(actor.get("tenant_id", "")),
                started_at=str(explanation.get("started_at", "")) or None,
                ended_at=str(explanation.get("ended_at", "")) or None,
                event_count=int(ids.get("event_count", 0)),
                event_types=tuple(event_types),
            )
            row = asdict(summary)
            final_outcome = str(explanation.get("final_outcome", ""))
            row["final_outcome"] = final_outcome
            row["partial_trace"] = bool(explanation.get("partial_trace", False))
            row["has_replay"] = bool(explanation.get("replay"))
            row["security_relevant"] = _is_security_relevant(event_types=event_types)
            row["updated_at"] = str(explanation.get("updated_at", "")) or None
            row["decision_class"] = _decision_class(final_outcome)
            if self._summary_matches_filters(row, filters or {}):
                rows.append(row)
        return self._sort_trace_rows(rows, filters or {})

    def get_trace(self, trace_id: str) -> dict[str, object] | None:
        for explanation in self._build_trace_explanations():
            ids = explanation.get("ids", {})
            if str(ids.get("trace_id", "")) == trace_id or str(ids.get("request_id", "")) == trace_id:
                cross_links = self._trace_cross_links(
                    explanation=explanation,
                    eval_runs=self.list_eval_runs(),
                    launch_gate=self.get_latest_launch_gate(),
                    verification=self.get_latest_verification(),
                )
                integrity_detail = self._trace_integrity_detail(explanation=explanation, cross_links=cross_links)
                return {
                    "trace_id": str(ids.get("trace_id", "")),
                    "request_id": str(ids.get("request_id", "")),
                    "actor_id": str(explanation.get("actor", {}).get("actor_id", "")),
                    "tenant_id": str(explanation.get("actor", {}).get("tenant_id", "")),
                    "event_count": int(ids.get("event_count", 0)),
                    "timeline": explanation.get("timeline", []),
                    "cross_links": cross_links,
                    "artifact_integrity": integrity_detail,
                    "explanation": {**explanation, "cross_links": cross_links, "artifact_integrity": integrity_detail},
                }
        return None

    def list_replay_artifacts(self) -> list[dict[str, object]]:
        out = []
        for path in sorted(self.paths.glob("replay/*.replay.json"), reverse=True):
            payload = _read_json(path)
            if payload is None:
                continue
            row = asdict(ReplaySummary(replay_id=path.name, trace_id=str(payload.get("trace_id", "")), request_id=str(payload.get("request_id", "")), path=self.paths.relative(path)))
            row["artifact_timestamp"] = _file_timestamp(path)
            out.append(row)
        return out

    def get_replay_artifact(self, replay_id: str) -> dict[str, object] | None:
        for path in sorted(self.paths.glob("replay/*.replay.json"), reverse=True):
            payload = _read_json(path)
            if payload is None:
                continue
            trace_id = str(payload.get("trace_id", ""))
            if path.name == replay_id or trace_id == replay_id:
                payload["artifact_path"] = self.paths.relative(path)
                return payload
        return None

    def list_eval_runs(self) -> list[dict[str, object]]:
        runs = []
        for path in sorted(self.paths.glob("evals/*.summary.json"), reverse=True):
            payload = parse_eval_summary(path)
            if payload is None:
                continue
            run_id = path.name.removesuffix(".summary.json")
            run = EvalRunSummary(
                run_id=run_id,
                suite_name=str(payload.get("suite_name", "unknown")),
                passed=bool(payload.get("passed", False)),
                total=int(payload.get("total", 0)) if isinstance(payload.get("total"), int) else 0,
                passed_count=int(payload.get("passed_count", 0)) if isinstance(payload.get("passed_count"), int) else 0,
                summary_path=self.paths.relative(path),
            )
            row = asdict(run)
            row["outcomes"] = payload.get("outcomes", {})
            row["summary_timestamp"] = _file_timestamp(path)
            runs.append(row)
        return runs

    def get_eval_run(self, run_id: str) -> dict[str, object] | None:
        summary_path = self.paths.evals_dir / f"{run_id}.summary.json"
        summary_payload = parse_eval_summary(summary_path)
        if summary_payload is None:
            return None
        jsonl_path = self.paths.evals_dir / f"{run_id}.jsonl"
        scenario_results, malformed_lines = parse_eval_jsonl(jsonl_path)
        catalog_path = self.paths.repo_root / "evals/scenarios/security_baseline.json"
        catalog_rows = parse_eval_scenario_catalog(catalog_path)
        baseline_coverage = summarize_baseline_coverage(catalog_rows=catalog_rows, result_rows=scenario_results)
        return {
            "run_id": run_id,
            "summary": summary_payload,
            "scenario_results": scenario_results,
            "category_summaries": summarize_eval_categories(scenario_results),
            "high_or_critical_failures": high_critical_failures(scenario_results),
            "baseline_coverage": baseline_coverage,
            "catalog_path": self.paths.relative(catalog_path) if catalog_path.is_file() else None,
            "summary_path": self.paths.relative(summary_path),
            "summary_timestamp": _file_timestamp(summary_path),
            "scenario_path": self.paths.relative(jsonl_path) if jsonl_path.is_file() else None,
            "scenario_timestamp": _file_timestamp(jsonl_path) if jsonl_path.is_file() else None,
            "scenario_malformed_lines": malformed_lines,
        }

    def get_latest_verification(self) -> dict[str, object] | None:
        for path in sorted(self.paths.glob("verification/*.summary.json"), reverse=True):
            payload = _read_json(path)
            if not isinstance(payload, dict):
                continue
            status = payload.get("status")
            if not isinstance(status, str):
                status = "unknown"
            return {"status": status, "summary": str(payload.get("summary", "")), "path": self.paths.relative(path), "artifact_timestamp": _file_timestamp(path), "report": payload}
        for path in sorted(self.paths.glob("verification/*.summary.md"), reverse=True):
            try:
                content = path.read_text()
            except OSError:
                continue
            return {"status": "unknown", "summary": content.splitlines()[0] if content else "", "path": self.paths.relative(path), "artifact_timestamp": _file_timestamp(path), "report": {"markdown": True}}
        return None

    def get_latest_launch_gate(self) -> dict[str, object] | None:
        for path in sorted(self.paths.glob("launch_gate/*.json"), reverse=True):
            payload = parse_launch_gate_report(path)
            if payload is None:
                continue
            payload["path"] = self.paths.relative(path)
            payload["artifact_timestamp"] = _file_timestamp(path)
            payload["related_links"] = self._launch_gate_related_links(payload)
            return payload
        return None

    def get_system_map(self) -> dict[str, object]:
        return {
            "components": [
                {"name": "app", "role": "orchestrates runtime request flow", "depends_on": ["policies", "retrieval", "tools", "telemetry/audit"]},
                {"name": "policies", "role": "policy models and enforcement interfaces"},
                {"name": "retrieval", "role": "retrieval abstractions and boundary checks"},
                {"name": "tools", "role": "tool contracts, mediation, and registry behavior"},
                {"name": "telemetry/audit", "role": "auditable event contracts, sinks, replay"},
                {"name": "evals", "role": "quality/safety eval harness and outputs", "depends_on": ["app", "policies", "retrieval", "tools", "telemetry/audit"]},
                {"name": "launch_gate", "role": "release readiness checks and criteria", "depends_on": ["evals", "telemetry/audit", "verification"]},
            ],
            "read_only": True,
            "artifacts_root": self.paths.relative(self.paths.artifacts_root),
            "demo_mode": self.paths.demo_mode,
        }


    def _build_empty_state(
        self,
        *,
        traces: Sequence[Mapping[str, object]],
        replay: Sequence[Mapping[str, object]],
        evals: Sequence[Mapping[str, object]],
        launch_gate: Mapping[str, object] | None,
    ) -> dict[str, object]:
        """Describe actionable empty-state guidance for dashboard users."""

        has_any_artifacts = bool(traces) or bool(replay) or bool(evals) or bool(launch_gate)
        if has_any_artifacts:
            return {"present": False, "message": ""}

        artifacts_root = self.paths.relative(self.paths.artifacts_root)
        return {
            "present": True,
            "title": "No runtime artifacts found",
            "message": "Dashboard is read-only and currently has no audit/replay/eval/launch-gate artifacts to display.",
            "artifacts_root": artifacts_root,
            "suggested_commands": [
                "python scripts/generate_dashboard_demo_artifacts.py",
                "DASHBOARD_ARTIFACTS_ROOT=artifacts/demo/dashboard_logs python -m observability.api",
                "cd ../integration-adapter && python -m integration_adapter.demo_scenario",
                "cd ../integration-adapter && INTEGRATION_ADAPTER_ARTIFACTS_ROOT=artifacts/logs python -m integration_adapter.generate_artifacts --demo",
            ],
            "notes": [
                "For integration deployments, point DASHBOARD_ARTIFACTS_ROOT, INTEGRATION_ADAPTER_ARTIFACTS_ROOT, or INTEGRATION_ARTIFACTS_ROOT to generated artifacts.",
                "Demo artifacts are for review workflows only and are not production evidence.",
                "Dashboard remains read-only and does not execute tools or mutate policy/runtime state.",
            ],
        }



    def _trace_cross_links(
        self,
        *,
        explanation: Mapping[str, object],
        eval_runs: Sequence[Mapping[str, object]],
        launch_gate: Mapping[str, object] | None,
        verification: Mapping[str, object] | None,
    ) -> dict[str, object]:
        ids = explanation.get("ids", {}) if isinstance(explanation.get("ids"), Mapping) else {}
        trace_id = str(ids.get("trace_id", ""))
        request_id = str(ids.get("request_id", ""))
        event_types = {
            str(item.get("event_type", ""))
            for item in explanation.get("timeline", [])
            if isinstance(item, Mapping)
        }

        replay = explanation.get("replay") if isinstance(explanation.get("replay"), Mapping) else None
        replay_link = {
            "correlation": "exact" if replay else "none",
            "confirmed": bool(replay),
            "inferred": False,
            "reason": "matched by trace_id/request_id" if replay else "no replay artifact matched trace_id/request_id",
            "artifact": dict(replay) if replay else None,
        }

        eval_matches: list[dict[str, object]] = []
        for run in eval_runs:
            run_id = str(run.get("run_id", ""))
            run_detail = self.get_eval_run(run_id)
            if run_detail is None:
                continue
            for row in run_detail.get("scenario_results", []):
                if not isinstance(row, Mapping):
                    continue
                evidence = row.get("evidence", {})
                evidence_map = evidence if isinstance(evidence, Mapping) else {}
                ev_trace = str(evidence_map.get("trace_id", ""))
                ev_request = str(evidence_map.get("request_id", ""))
                if (trace_id and ev_trace == trace_id) or (request_id and ev_request == request_id):
                    eval_matches.append(
                        {
                            "correlation": "exact",
                            "inferred": False,
                            "confirmed": True,
                            "reason": "scenario evidence includes matching trace_id/request_id",
                            "run_id": run_id,
                            "scenario_id": str(row.get("scenario_id", "")),
                            "category": str(row.get("category", "")),
                            "summary_path": run_detail.get("summary_path"),
                            "scenario_path": run_detail.get("scenario_path"),
                        }
                    )
                    continue
                if trace_id and trace_id in run_id or request_id and request_id in run_id:
                    eval_matches.append(
                        {
                            "correlation": "exact",
                            "inferred": False,
                            "confirmed": True,
                            "reason": "eval run_id includes trace_id/request_id",
                            "run_id": run_id,
                            "scenario_id": str(row.get("scenario_id", "")),
                            "category": str(row.get("category", "")),
                            "summary_path": run_detail.get("summary_path"),
                            "scenario_path": run_detail.get("scenario_path"),
                        }
                    )
                    continue
                ev_types = set(evidence_map.get("event_types", [])) if isinstance(evidence_map.get("event_types"), list) else set()
                overlap = len(event_types.intersection({str(item) for item in ev_types}))
                if overlap >= 3:
                    eval_matches.append(
                        {
                            "correlation": "inferred",
                            "inferred": True,
                            "confirmed": False,
                            "reason": f"inferred from event_type overlap ({overlap} shared)",
                            "run_id": run_id,
                            "scenario_id": str(row.get("scenario_id", "")),
                            "category": str(row.get("category", "")),
                            "summary_path": run_detail.get("summary_path"),
                            "scenario_path": run_detail.get("scenario_path"),
                        }
                    )

        exact_eval = [item for item in eval_matches if item.get("correlation") == "exact"]
        inferred_eval = [item for item in eval_matches if item.get("correlation") == "inferred"]
        selected_eval = exact_eval if exact_eval else inferred_eval[:5]
        eval_link = {
            "correlation": "exact" if exact_eval else ("inferred" if inferred_eval else "none"),
            "confirmed": bool(exact_eval),
            "inferred": bool(inferred_eval) and not bool(exact_eval),
            "reason": "matched using deterministic eval evidence" if exact_eval else (
                "no deterministic match; showing inferred candidates" if inferred_eval else "no related eval scenario could be confirmed"
            ),
            "items": selected_eval,
        }

        verification_link: dict[str, object]
        if isinstance(verification, Mapping):
            verification_link = {
                "correlation": "inferred",
                "confirmed": False,
                "inferred": True,
                "reason": "verification summary is release-level evidence and not trace-scoped",
                "artifact": {
                    "path": verification.get("path"),
                    "status": verification.get("status"),
                    "artifact_timestamp": verification.get("artifact_timestamp"),
                },
            }
        else:
            verification_link = {
                "correlation": "none",
                "confirmed": False,
                "inferred": False,
                "reason": "no verification summary artifact available",
                "artifact": None,
            }

        launch_link: dict[str, object]
        if isinstance(launch_gate, Mapping):
            launch_link = {
                "correlation": "inferred",
                "confirmed": False,
                "inferred": True,
                "reason": "launch-gate evaluates aggregate evidence and is not trace-scoped",
                "artifact": {
                    "path": launch_gate.get("path"),
                    "status": launch_gate.get("status"),
                    "latest_artifact_timestamp": launch_gate.get("latest_artifact_timestamp"),
                },
                "related_links": launch_gate.get("related_links", {}),
            }
        else:
            launch_link = {
                "correlation": "none",
                "confirmed": False,
                "inferred": False,
                "reason": "no launch-gate artifact available",
                "artifact": None,
                "related_links": {},
            }

        return {
            "replay": replay_link,
            "eval": eval_link,
            "verification": verification_link,
            "launch_gate": launch_link,
        }

    def _launch_gate_related_links(self, launch_gate: Mapping[str, object]) -> dict[str, object]:
        checks = launch_gate.get("checks", []) if isinstance(launch_gate.get("checks"), list) else []
        scorecard = launch_gate.get("scorecard", []) if isinstance(launch_gate.get("scorecard"), list) else []
        control_areas = sorted({str(item.get("check_name", "")) for item in checks if isinstance(item, Mapping) and str(item.get("check_name", ""))})
        eval_categories = sorted({str(item.get("category_name", "")) for item in scorecard if isinstance(item, Mapping) and str(item.get("category_name", ""))})
        return {
            "correlation": "exact" if control_areas or eval_categories else "none",
            "confirmed": bool(control_areas or eval_categories),
            "inferred": False,
            "reason": "derived directly from launch-gate checks/scorecard" if control_areas or eval_categories else "no control-area links present",
            "control_areas": control_areas,
            "eval_categories": eval_categories,
        }

    def _summarize_trace_connections(
        self,
        explanations: Sequence[Mapping[str, object]],
        *,
        eval_runs: Sequence[Mapping[str, object]],
        launch_gate: Mapping[str, object] | None,
        verification: Mapping[str, object] | None,
    ) -> dict[str, object]:
        totals = {
            "traces_with_replay_exact": 0,
            "traces_with_eval_exact": 0,
            "traces_with_eval_inferred": 0,
            "traces_with_verification_inferred": 0,
            "traces_with_launch_gate_inferred": 0,
            "traces_with_no_confirmed_links": 0,
        }
        for explanation in explanations:
            links = self._trace_cross_links(
                explanation=explanation,
                eval_runs=eval_runs,
                launch_gate=launch_gate,
                verification=verification,
            )
            replay_exact = links.get("replay", {}).get("correlation") == "exact"
            eval_exact = links.get("eval", {}).get("correlation") == "exact"
            eval_inferred = links.get("eval", {}).get("correlation") == "inferred"
            verification_inferred = links.get("verification", {}).get("correlation") == "inferred"
            launch_inferred = links.get("launch_gate", {}).get("correlation") == "inferred"
            if replay_exact:
                totals["traces_with_replay_exact"] += 1
            if eval_exact:
                totals["traces_with_eval_exact"] += 1
            if eval_inferred:
                totals["traces_with_eval_inferred"] += 1
            if verification_inferred:
                totals["traces_with_verification_inferred"] += 1
            if launch_inferred:
                totals["traces_with_launch_gate_inferred"] += 1
            if not replay_exact and not eval_exact:
                totals["traces_with_no_confirmed_links"] += 1
        return totals

    def _artifact_integrity_overview(
        self,
        *,
        replay: Sequence[Mapping[str, object]],
        evals: Sequence[Mapping[str, object]],
        launch_gate: Mapping[str, object] | None,
        verification: Mapping[str, object] | None,
    ) -> dict[str, object]:
        entries = [
            _integrity_entry(
                artifact_type="audit",
                evidence_state="file-backed evidence" if self.paths.audit_jsonl.is_file() else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if self.get_latest_verification() else "integrity unverified",
                path=self.paths.relative(self.paths.audit_jsonl),
                timestamp=_file_timestamp(self.paths.audit_jsonl),
            ),
            _integrity_entry(
                artifact_type="replay",
                evidence_state="file-backed evidence" if replay else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if replay else "integrity unverified",
                path=str(replay[0].get("path")) if replay else "artifacts/logs/replay/*.replay.json",
                timestamp=_first_present(list(replay), "artifact_timestamp"),
            ),
            _integrity_entry(
                artifact_type="eval",
                evidence_state="file-backed evidence" if evals else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if evals else "integrity unverified",
                path=str(evals[0].get("summary_path")) if evals else "artifacts/logs/evals/*.summary.json",
                timestamp=_first_present(list(evals), "summary_timestamp"),
            ),
            _integrity_entry(
                artifact_type="launch_gate",
                evidence_state="file-backed evidence" if isinstance(launch_gate, Mapping) else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if isinstance(launch_gate, Mapping) else "integrity unverified",
                path=str(launch_gate.get("path")) if isinstance(launch_gate, Mapping) else "artifacts/logs/launch_gate/*.json",
                timestamp=str(launch_gate.get("latest_artifact_timestamp")) if isinstance(launch_gate, Mapping) else None,
            ),
        ]
        return {
            "entries": entries,
            "legend": "Integrity visibility is conservative: file-backed evidence is shown, but cryptographic signing/attestation is not implemented in this repository.",
        }

    def _trace_integrity_detail(self, *, explanation: Mapping[str, object], cross_links: Mapping[str, object]) -> dict[str, object]:
        replay_artifact = cross_links.get("replay", {}).get("artifact") if isinstance(cross_links.get("replay"), Mapping) else None
        eval_items = cross_links.get("eval", {}).get("items", []) if isinstance(cross_links.get("eval"), Mapping) else []
        launch_artifact = cross_links.get("launch_gate", {}).get("artifact") if isinstance(cross_links.get("launch_gate"), Mapping) else None
        verification_artifact = cross_links.get("verification", {}).get("artifact") if isinstance(cross_links.get("verification"), Mapping) else None

        entries = [
            _integrity_entry(
                artifact_type="trace_audit",
                evidence_state="file-backed evidence" if self.paths.audit_jsonl.is_file() else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if explanation.get("timeline") else "integrity unverified",
                path=self.paths.relative(self.paths.audit_jsonl),
                timestamp=str(explanation.get("updated_at", "")) or _file_timestamp(self.paths.audit_jsonl),
            ),
            _integrity_entry(
                artifact_type="trace_replay",
                evidence_state="file-backed evidence" if isinstance(replay_artifact, Mapping) else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if isinstance(replay_artifact, Mapping) else "integrity unverified",
                path=str(replay_artifact.get("replay_path")) if isinstance(replay_artifact, Mapping) else "not linked",
                timestamp=str(replay_artifact.get("replay_timestamp")) if isinstance(replay_artifact, Mapping) else None,
            ),
            _integrity_entry(
                artifact_type="trace_eval",
                evidence_state="file-backed evidence" if eval_items else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if eval_items else "integrity unverified",
                path=str(eval_items[0].get("summary_path")) if eval_items else "not linked",
                timestamp=None,
            ),
            _integrity_entry(
                artifact_type="trace_launch_gate",
                evidence_state="file-backed evidence" if isinstance(launch_artifact, Mapping) else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if isinstance(launch_artifact, Mapping) else "integrity unverified",
                path=str(launch_artifact.get("path")) if isinstance(launch_artifact, Mapping) else "not linked",
                timestamp=str(launch_artifact.get("latest_artifact_timestamp")) if isinstance(launch_artifact, Mapping) else None,
            ),
            _integrity_entry(
                artifact_type="trace_verification",
                evidence_state="file-backed evidence" if isinstance(verification_artifact, Mapping) else "integrity unverified",
                signing_state="signing not implemented",
                verification_state="verification metadata present" if isinstance(verification_artifact, Mapping) else "integrity unverified",
                path=str(verification_artifact.get("path")) if isinstance(verification_artifact, Mapping) else "not linked",
                timestamp=str(verification_artifact.get("artifact_timestamp")) if isinstance(verification_artifact, Mapping) else None,
            ),
        ]
        return {
            "entries": entries,
            "legend": "No cryptographic signing guarantees are implemented; integrity status reflects observable file-backed metadata only.",
        }

    def _build_trace_explanations(self) -> list[dict[str, object]]:
        events, _ = read_audit_jsonl(self.paths.audit_jsonl)
        replay_links = load_replay_links(self.paths.repo_root)
        return build_trace_explanations(events, replay_links=replay_links)

    def _summary_matches_filters(self, row: Mapping[str, object], filters: Mapping[str, str]) -> bool:
        active = {k: v for k, v in filters.items() if v}
        expected = {
            "request_id": str(row.get("request_id", "")),
            "trace_id": str(row.get("trace_id", "")),
            "tenant_id": str(row.get("tenant_id", "")),
            "actor_id": str(row.get("actor_id", "")),
            "status": str(row.get("final_outcome", "")),
            "final_outcome": str(row.get("final_outcome", "")),
            "decision_class": str(row.get("decision_class", "")),
        }
        for key, value in active.items():
            if key == "event_type" and value not in set(row.get("event_types", ())):
                return False
            if key == "replay_only" and _parse_bool_filter(value) and not bool(row.get("has_replay", False)):
                return False
            if key == "partial_only" and _parse_bool_filter(value) and not bool(row.get("partial_trace", False)):
                return False
            if key == "security_only" and _parse_bool_filter(value) and not bool(row.get("security_relevant", False)):
                return False
            if key in {"date_from", "date_to"}:
                started_at = str(row.get("started_at", "") or row.get("updated_at", ""))
                if key == "date_from" and started_at and started_at < value:
                    return False
                if key == "date_to" and started_at and started_at > value:
                    return False
                continue
            if key in expected and expected[key] != value:
                return False
        return True

    def _sort_trace_rows(self, rows: list[dict[str, object]], filters: Mapping[str, str]) -> list[dict[str, object]]:
        sort_by = str(filters.get("sort_by", "started_at") or "started_at")
        sort_order = str(filters.get("sort_order", "desc") or "desc").lower()
        reverse = sort_order != "asc"

        if sort_by == "event_count":
            keyfunc = lambda item: int(item.get("event_count", 0))
        elif sort_by == "final_outcome":
            keyfunc = lambda item: str(item.get("final_outcome", ""))
        elif sort_by == "updated_at":
            keyfunc = lambda item: str(item.get("updated_at") or "")
        else:
            keyfunc = lambda item: str(item.get("started_at") or item.get("updated_at") or "")
        return sorted(rows, key=keyfunc, reverse=reverse)





def _integrity_entry(
    *,
    artifact_type: str,
    evidence_state: str,
    signing_state: str,
    verification_state: str,
    path: str,
    timestamp: str | None,
) -> dict[str, object]:
    return {
        "artifact_type": artifact_type,
        "evidence_state": evidence_state,
        "signing_state": signing_state,
        "verification_state": verification_state,
        "path": path,
        "timestamp": timestamp,
    }

def _decision_class(final_outcome: str) -> str:
    normalized = final_outcome.lower().strip()
    if normalized in {"denied", "blocked"}:
        return "deny"
    if normalized == "fallback":
        return "fallback"
    if normalized == "error":
        return "error"
    return "allow"


def _is_security_relevant(*, event_types: Sequence[str]) -> bool:
    flags = {"policy.decision", "tool.decision", "deny.event", "fallback.event", "error.event", "confirmation.required"}
    return any(event in flags for event in event_types)


def _parse_bool_filter(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}

def _read_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None



def _file_timestamp(path: Path) -> str | None:
    try:
        stat = path.stat()
        return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except OSError:
        return None


def _first_present(rows: list[dict[str, object]], key: str) -> str | None:
    for row in rows:
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None
