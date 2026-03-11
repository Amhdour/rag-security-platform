"""Normalization helpers for security eval artifacts used by the dashboard.

The parser is intentionally tolerant of historical artifact variants:
- summary files may or may not include "outcomes"
- scenario JSONL rows may or may not include "outcome"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

CATEGORY_EXPLANATIONS: Mapping[str, str] = {
    "prompt_injection": "Prompt-injection resilience checks verify policy-aware runtime behavior under direct and indirect jailbreak attempts.",
    "retrieval_boundary": "Retrieval-boundary checks validate tenant/source/trust/provenance controls and resistance to malicious retrieval content.",
    "unsafe_disclosure": "Unsafe-disclosure checks verify that sensitive disclosures are refused and response safety constraints are preserved.",
    "tool_misuse": "Tool-misuse checks validate allowlist/deny/confirmation/rate-limit mediation for forbidden or unauthorized tool usage.",
    "policy_bypass": "Policy-bypass checks confirm runtime decisions remain policy-governed and reject bypass arguments/spoofing attempts.",
    "fallback": "Fallback checks verify fallback-to-RAG behavior when tooling is disabled or denied by policy/risk tier.",
    "auditability": "Auditability checks validate that request lifecycle and critical decision events are present for incident review and replay.",
    "other": "Other security eval scenarios from the repository suite.",
}

BASELINE_CATEGORY_MATCHERS: Mapping[str, tuple[str, ...]] = {
    "prompt injection": ("prompt_injection",),
    "malicious retrieval content": ("retrieval_poisoning", "indirect_prompt_injection_retrieved"),
    "cross-tenant retrieval attempt": ("cross_tenant_retrieval_attempt", "tenant_spoofing"),
    "unsafe disclosure attempt": ("unsafe_disclosure_attempt", "secret_leakage"),
    "forbidden/unauthorized tool usage": ("forbidden_tool_argument_attempt", "unauthorized_tool_use_attempt"),
    "policy bypass attempt": ("policy_bypass_attempt", "policy_bypass", "policy_drift"),
    "fallback-to-RAG verification": ("fallback_to_rag_verification",),
    "auditability verification": ("auditability_verification",),
}


def parse_eval_summary(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    summary = dict(payload)
    outcomes = summary.get("outcomes")
    if not isinstance(outcomes, dict):
        total = int(summary.get("total", 0)) if isinstance(summary.get("total"), int) else 0
        passed_count = int(summary.get("passed_count", 0)) if isinstance(summary.get("passed_count"), int) else 0
        fail_count = max(total - passed_count, 0)
        summary["outcomes"] = {
            "pass": passed_count,
            "fail": fail_count,
            "expected_fail": 0,
            "blocked": 0,
            "inconclusive": 0,
        }
    return summary


def parse_eval_jsonl(path: Path) -> tuple[list[dict[str, object]], int]:
    if not path.is_file():
        return [], 0
    rows: list[dict[str, object]] = []
    malformed = 0
    for line in path.read_text().splitlines():
        row = line.strip()
        if not row:
            continue
        try:
            parsed = json.loads(row)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(parsed, dict):
            malformed += 1
            continue
        rows.append(_normalize_scenario_row(parsed))
    return rows, malformed


def parse_eval_scenario_catalog(path: Path) -> list[dict[str, object]]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    scenarios = payload.get("scenarios", []) if isinstance(payload, dict) else []
    if not isinstance(scenarios, list):
        return []
    out: list[dict[str, object]] = []
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        scenario_id = str(item.get("id", ""))
        title = str(item.get("title", ""))
        category = _category_for_scenario(scenario_id=scenario_id, title=title)
        out.append(
            {
                "scenario_id": scenario_id,
                "title": title,
                "severity": str(item.get("severity", "unknown")),
                "category": category,
                "category_explanation": CATEGORY_EXPLANATIONS.get(category, CATEGORY_EXPLANATIONS["other"]),
                "control_boundary_links": _boundary_links_for_category(category),
            }
        )
    return out


def summarize_baseline_coverage(
    *,
    catalog_rows: Sequence[Mapping[str, object]],
    result_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    by_id = {str(row.get("scenario_id", "")): row for row in result_rows}
    catalog = [dict(item) for item in catalog_rows]

    summary: list[dict[str, object]] = []
    for label, tokens in BASELINE_CATEGORY_MATCHERS.items():
        repo_scenarios = [
            item
            for item in catalog
            if any(token in f"{item.get('scenario_id', '')} {item.get('title', '')}".lower() for token in tokens)
        ]
        scenario_ids = [str(item.get("scenario_id", "")) for item in repo_scenarios]
        run_rows = [dict(by_id[sid]) for sid in scenario_ids if sid in by_id]
        high_critical_failed = [
            item for item in run_rows if (not bool(item.get("passed", False))) and str(item.get("severity", "")).lower() in {"high", "critical"}
        ]
        summary.append(
            {
                "baseline_category": label,
                "repository_scenarios": repo_scenarios,
                "run_results": run_rows,
                "present_in_repository": len(repo_scenarios) > 0,
                "observed_in_run": len(run_rows),
                "high_or_critical_failures": high_critical_failed,
            }
        )
    return summary


def _normalize_scenario_row(row: Mapping[str, object]) -> dict[str, object]:
    scenario_id = str(row.get("scenario_id", ""))
    severity = str(row.get("severity", "unknown"))
    passed = bool(row.get("passed", False))
    outcome = row.get("outcome")
    outcome_value = str(outcome) if isinstance(outcome, str) else ("pass" if passed else "fail")

    category = _category_for_scenario(scenario_id=scenario_id, title=str(row.get("title", "")))
    boundary_links = _boundary_links_for_category(category)

    return {
        "scenario_id": scenario_id,
        "title": str(row.get("title", "")),
        "severity": severity,
        "passed": passed,
        "outcome": outcome_value,
        "details": str(row.get("details", "")),
        "category": category,
        "category_explanation": CATEGORY_EXPLANATIONS.get(category, CATEGORY_EXPLANATIONS["other"]),
        "control_boundary_links": boundary_links,
        "evidence": row.get("evidence", {}),
    }


def _category_for_scenario(*, scenario_id: str, title: str) -> str:
    label = f"{scenario_id} {title}".lower()
    if "prompt_injection" in label:
        return "prompt_injection"
    if any(token in label for token in ("cross_tenant", "retrieval", "poison")):
        return "retrieval_boundary"
    if any(token in label for token in ("unsafe_disclosure", "secret_leakage", "disclosure")):
        return "unsafe_disclosure"
    if any(token in label for token in ("tool", "capability_token", "confirmation_required")):
        return "tool_misuse"
    if "policy_bypass" in label or "policy_drift" in label or "tenant_spoof" in label:
        return "policy_bypass"
    if "fallback" in label:
        return "fallback"
    if "auditability" in label:
        return "auditability"
    return "other"


def _boundary_links_for_category(category: str) -> list[dict[str, str]]:
    links: dict[str, list[dict[str, str]]] = {
        "prompt_injection": [{"control": "policy_governs_runtime_behavior", "boundary": "policies -> app orchestration"}],
        "retrieval_boundary": [{"control": "retrieval_enforces_boundaries", "boundary": "retrieval -> source/document"}],
        "unsafe_disclosure": [{"control": "policy_governs_runtime_behavior", "boundary": "app/model response safety"}],
        "tool_misuse": [{"control": "tool_router_cannot_be_bypassed", "boundary": "app -> tools router"}],
        "policy_bypass": [{"control": "policy_governs_runtime_behavior", "boundary": "request -> policy decision points"}],
        "fallback": [{"control": "fallback_readiness", "boundary": "policy/tools -> RAG fallback"}],
        "auditability": [{"control": "telemetry_supports_replay", "boundary": "runtime -> telemetry/audit"}],
    }
    return links.get(category, [])


def summarize_eval_categories(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    by_category: dict[str, dict[str, object]] = {}
    for row in rows:
        category = str(row.get("category", "other"))
        summary = by_category.setdefault(
            category,
            {
                "category": category,
                "description": CATEGORY_EXPLANATIONS.get(category, CATEGORY_EXPLANATIONS["other"]),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "high_or_critical_failures": 0,
            },
        )
        summary["total"] = int(summary["total"]) + 1
        if bool(row.get("passed", False)):
            summary["passed"] = int(summary["passed"]) + 1
        else:
            summary["failed"] = int(summary["failed"]) + 1
            if str(row.get("severity", "")).lower() in {"high", "critical"}:
                summary["high_or_critical_failures"] = int(summary["high_or_critical_failures"]) + 1
    return sorted(by_category.values(), key=lambda item: str(item.get("category")))


def high_critical_failures(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return [
        dict(item)
        for item in rows
        if (not bool(item.get("passed", False))) and str(item.get("severity", "")).lower() in {"high", "critical"}
    ]
