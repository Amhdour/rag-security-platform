"""Trace normalization helpers for dashboard explanations.

This module converts audit/replay evidence into UI-agnostic, read-only trace models.
It is intentionally independent from frontend rendering.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from app.secrets import redact_mapping


EVENT_STAGES = {
    "lifecycle",
    "policy",
    "retrieval",
    "model",
    "tools",
    "deny",
    "fallback",
    "error",
}


def read_audit_jsonl(path: Path) -> tuple[list[dict[str, object]], int]:
    """Read audit JSONL safely.

    Assumptions:
    - Each valid line is a JSON object representing one audit event.
    - Malformed lines are ignored instead of failing the entire parse.
    """

    if not path.is_file():
        return [], 0

    events: list[dict[str, object]] = []
    malformed_lines = 0
    for line in path.read_text().splitlines():
        row = line.strip()
        if not row:
            continue
        try:
            parsed = json.loads(row)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if not isinstance(parsed, dict):
            malformed_lines += 1
            continue
        events.append(parsed)
    return events, malformed_lines


def load_replay_links(repo_root: Path, *, artifacts_root: Path | None = None) -> dict[str, dict[str, object]]:
    """Build replay lookup keyed by trace_id and request_id where available."""

    index: dict[str, dict[str, object]] = {}
    replay_dir = (artifacts_root or (repo_root / "artifacts" / "logs")) / "replay"
    for path in sorted(replay_dir.glob("*.replay.json"), reverse=True):
        payload = _read_replay_payload(path)
        if payload is None:
            continue
        trace_id = str(payload.get("trace_id", ""))
        request_id = str(payload.get("request_id", ""))
        entry = {
            "replay_id": path.name,
            "replay_path": _display_path(path, repo_root=repo_root),
            "replay_timestamp": _file_timestamp(path),
            "trace_id": trace_id,
            "request_id": request_id,
            "coverage": payload.get("coverage", {}),
            "event_type_counts": payload.get("event_type_counts", {}),
            "decision_summary": payload.get("decision_summary", {}),
        }
        if trace_id:
            index[f"trace:{trace_id}"] = entry
        if request_id:
            index[f"request:{request_id}"] = entry
    return index


def build_trace_explanations(
    events: Sequence[Mapping[str, object]],
    *,
    replay_links: Mapping[str, Mapping[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Build compact explanation objects grouped by trace_id/request_id."""

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for raw in events:
        event = _normalize_event(raw)
        key = _group_key(event)
        grouped[key].append(event)

    explanations = [
        _build_explanation_for_group(group_events, replay_links=replay_links or {})
        for group_events in grouped.values()
        if group_events
    ]
    return sorted(
        explanations,
        key=lambda item: str(item.get("started_at") or item.get("updated_at") or ""),
        reverse=True,
    )


def _group_key(event: Mapping[str, object]) -> str:
    trace_id = str(event.get("trace_id", "")).strip()
    if trace_id:
        return f"trace:{trace_id}"
    request_id = str(event.get("request_id", "")).strip()
    if request_id:
        return f"request:{request_id}"
    event_id = str(event.get("event_id", "")).strip()
    return f"orphan:{event_id or 'unknown'}"


def _normalize_event(raw: Mapping[str, object]) -> dict[str, object]:
    payload = raw.get("event_payload", {})
    payload_map = payload if isinstance(payload, Mapping) else {}
    event_type = str(raw.get("event_type", ""))
    stage = classify_stage(event_type=event_type, payload=payload_map)

    return {
        "event_id": str(raw.get("event_id", "")),
        "trace_id": str(raw.get("trace_id", "")),
        "request_id": str(raw.get("request_id", "")),
        "actor_id": str(raw.get("actor_id", "")),
        "tenant_id": str(raw.get("tenant_id", "")),
        "event_type": event_type,
        "event_category": stage,
        "created_at": str(raw.get("created_at", "")),
        "stage": stage,
        "decision_outcome": _decision_outcome(event_type=event_type, payload=payload_map),
        "reason": _extract_reason_from_payload(event_type=event_type, payload=payload_map),
        "payload": redact_mapping(payload_map),
    }


def classify_stage(*, event_type: str, payload: Mapping[str, object]) -> str:
    """Map event type to canonical trace stage."""

    if event_type in {"request.start", "request.end"}:
        return "lifecycle"
    if event_type == "policy.decision":
        action = str(payload.get("action", ""))
        if action == "model.generate":
            return "model"
        return "policy"
    if event_type == "retrieval.decision":
        return "retrieval"
    if event_type in {"tool.decision", "tool.execution_attempt", "confirmation.required"}:
        return "tools"
    if event_type == "deny.event":
        return "deny"
    if event_type == "fallback.event":
        return "fallback"
    if event_type == "error.event":
        return "error"
    return "lifecycle"


def _decision_outcome(*, event_type: str, payload: Mapping[str, object]) -> str:
    if event_type == "policy.decision":
        allow = payload.get("allow")
        if allow is True:
            return "allowed"
        if allow is False:
            return "denied"
        return "evaluated"
    if event_type == "request.end":
        status = str(payload.get("status", "")).lower()
        return status or "completed"
    if event_type == "retrieval.decision":
        return "evaluated"
    if event_type == "tool.decision":
        decisions = payload.get("decisions", [])
        if isinstance(decisions, list):
            normalized = {str(item).lower() for item in decisions}
            if normalized == {"allow"}:
                return "allowed"
            if normalized and normalized.issubset({"deny"}):
                return "denied"
            if "require_confirmation" in normalized:
                return "confirmation_required"
            if normalized:
                return "mixed"
        return "evaluated"
    if event_type == "confirmation.required":
        return "confirmation_required"
    if event_type == "deny.event":
        return "denied"
    if event_type == "fallback.event":
        return "fallback"
    if event_type == "error.event":
        return "error"
    if event_type == "request.start":
        return "started"
    return "observed"


def _extract_reason_from_payload(*, event_type: str, payload: Mapping[str, object]) -> str:
    for key in ("reason", "message", "details"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if event_type == "request.end":
        status = payload.get("status")
        if isinstance(status, str) and status.strip():
            return f"request status={status.strip()}"
    return ""




def _display_path(path: Path, *, repo_root: Path) -> str:
    """Return a stable, human-readable path for artifacts across roots."""

    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _build_explanation_for_group(
    events: Sequence[Mapping[str, object]], *, replay_links: Mapping[str, Mapping[str, object]]
) -> dict[str, object]:
    ordered = sorted(events, key=lambda item: str(item.get("created_at", "")))
    first = ordered[0]
    trace_id = str(first.get("trace_id", ""))
    request_id = str(first.get("request_id", ""))

    stage_summary: dict[str, dict[str, object]] = {}
    checks: list[dict[str, object]] = []
    decision_reasons: list[dict[str, object]] = []
    evidence_used: list[dict[str, object]] = []
    stage_groups: dict[str, list[dict[str, object]]] = {stage: [] for stage in EVENT_STAGES}

    for event in ordered:
        stage = str(event.get("stage", "lifecycle"))
        if stage not in EVENT_STAGES:
            stage = "lifecycle"
        entry = stage_summary.setdefault(stage, {"count": 0, "last_event_type": "", "last_reason": ""})
        entry["count"] = int(entry["count"]) + 1
        entry["last_event_type"] = str(event.get("event_type", ""))
        reason = str(event.get("reason", "")).strip()
        if reason:
            entry["last_reason"] = reason

        if stage in {"policy", "model", "retrieval", "tools", "deny", "fallback", "error"}:
            check_row = {
                "event_type": str(event.get("event_type", "")),
                "stage": stage,
                "decision_outcome": str(event.get("decision_outcome", "")),
                "reason": reason,
                "created_at": str(event.get("created_at", "")),
            }
            checks.append(check_row)
            stage_groups.setdefault(stage, []).append(check_row)
            if reason:
                decision_reasons.append(
                    {
                        "stage": stage,
                        "event_type": str(event.get("event_type", "")),
                        "reason": reason,
                        "decision_outcome": str(event.get("decision_outcome", "")),
                        "created_at": str(event.get("created_at", "")),
                    }
                )

            payload = event.get("payload", {})
            payload_map = payload if isinstance(payload, Mapping) else {}
            evidence_used.extend(_extract_evidence(event=event, payload=payload_map))

    started_at = next((str(item.get("created_at", "")) for item in ordered if item.get("event_type") == "request.start"), None)
    ended_at = next((str(item.get("created_at", "")) for item in reversed(ordered) if item.get("event_type") == "request.end"), None)

    replay = replay_links.get(f"trace:{trace_id}") or replay_links.get(f"request:{request_id}")
    outcome = _final_outcome(ordered)
    final_summary = _final_disposition_summary(
        final_outcome=outcome,
        partial_trace=ended_at is None,
        checks=checks,
    )

    return {
        "ids": {
            "trace_id": trace_id,
            "request_id": request_id,
            "event_count": len(ordered),
        },
        "actor": {
            "actor_id": str(first.get("actor_id", "")),
            "tenant_id": str(first.get("tenant_id", "")),
        },
        "started_at": started_at,
        "ended_at": ended_at,
        "updated_at": str(ordered[-1].get("created_at", "")),
        "partial_trace": ended_at is None,
        "final_outcome": outcome,
        "final_disposition": outcome,
        "final_disposition_summary": final_summary,
        "stage_summary": stage_summary,
        "stage_groups": {key: value for key, value in stage_groups.items() if value},
        "checks": checks,
        "decision_reasons": _dedupe_reason_entries(decision_reasons),
        "evidence_used": _dedupe_evidence_entries(evidence_used),
        "replay": dict(replay) if replay else None,
        "raw_event_inspector": [
            {
                "index": index + 1,
                "event_id": str(event.get("event_id", "")),
                "created_at": str(event.get("created_at", "")),
                "event_type": str(event.get("event_type", "")),
                "stage": str(event.get("stage", "")),
                "decision_outcome": str(event.get("decision_outcome", "")),
                "payload": event.get("payload", {}),
            }
            for index, event in enumerate(ordered)
        ],
        "timeline": list(ordered),
    }


def _final_disposition_summary(*, final_outcome: str, partial_trace: bool, checks: Sequence[Mapping[str, object]]) -> str:
    if final_outcome == "denied":
        deny_reasons = [str(item.get("reason", "")).strip() for item in checks if str(item.get("decision_outcome", "")) == "denied"]
        reason = next((item for item in deny_reasons if item), "policy control denied at runtime")
        return f"Request denied: {reason}."
    if final_outcome == "fallback":
        reason = next((str(item.get("reason", "")).strip() for item in checks if str(item.get("stage", "")) == "fallback" and str(item.get("reason", "")).strip()), "fallback guard triggered")
        return f"Request completed in fallback mode: {reason}."
    if final_outcome == "error":
        reason = next((str(item.get("reason", "")).strip() for item in checks if str(item.get("stage", "")) == "error" and str(item.get("reason", "")).strip()), "runtime error captured and request failed closed")
        return f"Request failed closed due to error: {reason}."
    if final_outcome == "completed":
        return "Request completed after policy, retrieval, model, and tool routing checks."
    if partial_trace:
        return "Trace is incomplete: no terminal request.end event was observed."
    return f"Request disposition: {final_outcome or 'unknown'}."


def _extract_evidence(*, event: Mapping[str, object], payload: Mapping[str, object]) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    stage = str(event.get("stage", ""))
    event_type = str(event.get("event_type", ""))
    created_at = str(event.get("created_at", ""))

    if event_type == "retrieval.decision":
        evidence.append(
            {
                "kind": "retrieval",
                "label": "retrieval result envelope",
                "stage": stage,
                "created_at": created_at,
                "details": {
                    "document_count": payload.get("document_count"),
                    "top_k": payload.get("top_k"),
                    "allowed_source_ids": payload.get("allowed_source_ids"),
                },
            }
        )
    if event_type == "policy.decision":
        evidence.append(
            {
                "kind": "policy",
                "label": "policy evaluation result",
                "stage": stage,
                "created_at": created_at,
                "details": {
                    "action": payload.get("action"),
                    "allow": payload.get("allow"),
                    "risk_tier": payload.get("risk_tier"),
                },
            }
        )
    if event_type in {"tool.decision", "tool.execution_attempt", "confirmation.required"}:
        details: dict[str, object] = {}
        for key in ("decisions", "attempted_tools", "attempt_count", "tool_name"):
            if key in payload:
                details[key] = payload.get(key)
        evidence.append(
            {
                "kind": "tools",
                "label": "tool mediation evidence",
                "stage": stage,
                "created_at": created_at,
                "details": details,
            }
        )
    if event_type in {"deny.event", "fallback.event", "error.event"}:
        evidence.append(
            {
                "kind": stage,
                "label": f"{stage} signal",
                "stage": stage,
                "created_at": created_at,
                "details": dict(payload),
            }
        )
    return evidence


def _dedupe_reason_entries(entries: Sequence[Mapping[str, object]]) -> tuple[dict[str, object], ...]:
    ordered_unique: dict[str, dict[str, object]] = {}
    for entry in entries:
        key = "|".join(
            (
                str(entry.get("stage", "")),
                str(entry.get("event_type", "")),
                str(entry.get("reason", "")),
                str(entry.get("created_at", "")),
            )
        )
        if key not in ordered_unique:
            ordered_unique[key] = dict(entry)
    return tuple(ordered_unique.values())


def _dedupe_evidence_entries(entries: Sequence[Mapping[str, object]]) -> tuple[dict[str, object], ...]:
    ordered_unique: dict[str, dict[str, object]] = {}
    for entry in entries:
        details = entry.get("details", {})
        details_blob = json.dumps(details, sort_keys=True) if isinstance(details, Mapping) else str(details)
        key = "|".join(
            (
                str(entry.get("kind", "")),
                str(entry.get("label", "")),
                str(entry.get("stage", "")),
                str(entry.get("created_at", "")),
                details_blob,
            )
        )
        if key not in ordered_unique:
            ordered_unique[key] = dict(entry)
    return tuple(ordered_unique.values())


def _final_outcome(events: Sequence[Mapping[str, object]]) -> str:
    event_types = [str(item.get("event_type", "")) for item in events]
    if "error.event" in event_types:
        return "error"
    if "deny.event" in event_types:
        return "denied"
    if "fallback.event" in event_types:
        return "fallback"
    for item in reversed(events):
        if str(item.get("event_type", "")) == "request.end":
            payload = item.get("payload", {})
            status = str(payload.get("status", "")).lower() if isinstance(payload, Mapping) else ""
            if status in {"ok", "completed", "success"}:
                return "completed"
            if status in {"blocked", "denied"}:
                return "denied"
            if status:
                return status
    if "request.end" in event_types:
        return "completed"
    return "in_progress"


def _read_replay_payload(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _file_timestamp(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
    except OSError:
        return None
