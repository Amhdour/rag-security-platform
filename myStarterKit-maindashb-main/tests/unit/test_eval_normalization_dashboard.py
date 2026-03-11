"""Tests for eval artifact normalization used by dashboard views."""

from __future__ import annotations

import json
from pathlib import Path

from observability.eval_normalization import (
    parse_eval_jsonl,
    parse_eval_scenario_catalog,
    parse_eval_summary,
    summarize_baseline_coverage,
    summarize_eval_categories,
)


def test_parse_eval_summary_supports_missing_outcomes(tmp_path: Path) -> None:
    path = tmp_path / "run.summary.json"
    path.write_text(json.dumps({"suite_name": "security-redteam", "passed": False, "total": 2, "passed_count": 1}))

    parsed = parse_eval_summary(path)

    assert parsed is not None
    assert parsed["outcomes"]["pass"] == 1
    assert parsed["outcomes"]["fail"] == 1


def test_parse_eval_jsonl_normalizes_category_outcome_and_links(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    rows = [
        {
            "scenario_id": "prompt_injection_direct",
            "title": "Direct prompt injection attempt",
            "severity": "high",
            "passed": True,
            "details": "ok",
        },
        {
            "scenario_id": "cross_tenant_retrieval_attempt",
            "title": "Cross-tenant retrieval attempt is blocked",
            "severity": "critical",
            "passed": False,
            "details": "regression",
        },
        "malformed",
    ]
    path.write_text("\n".join(json.dumps(item) if isinstance(item, dict) else item for item in rows))

    parsed, malformed = parse_eval_jsonl(path)

    assert malformed == 1
    assert len(parsed) == 2
    assert parsed[0]["outcome"] == "pass"
    assert parsed[0]["category"] == "prompt_injection"
    assert parsed[1]["outcome"] == "fail"
    assert parsed[1]["category"] == "retrieval_boundary"
    assert parsed[1]["control_boundary_links"]


def test_parse_eval_scenario_catalog_and_baseline_coverage_uses_real_categories(tmp_path: Path) -> None:
    catalog_path = tmp_path / "security_baseline.json"
    catalog_path.write_text(
        json.dumps(
            {
                "scenarios": [
                    {"id": "prompt_injection_direct", "title": "Direct prompt injection request is handled safely", "severity": "high"},
                    {"id": "retrieval_poisoning_attempt", "title": "Retrieved poisoning content remains visible as an expected failure", "severity": "high"},
                    {"id": "cross_tenant_retrieval_attempt", "title": "Cross-tenant retrieval attempt is blocked by policy", "severity": "critical"},
                    {"id": "unsafe_disclosure_attempt", "title": "Unsafe disclosure attempt is refused", "severity": "high"},
                    {"id": "forbidden_tool_argument_attempt", "title": "Forbidden tool argument is denied", "severity": "high"},
                    {"id": "policy_bypass_attempt", "title": "Policy bypass argument attempt is denied", "severity": "high"},
                    {"id": "fallback_to_rag_verification", "title": "Fallback-to-RAG activates", "severity": "medium"},
                    {"id": "auditability_verification", "title": "Audit trail contains evidence", "severity": "medium"},
                ]
            }
        )
    )
    catalog = parse_eval_scenario_catalog(catalog_path)
    by_id = {row["scenario_id"]: row for row in catalog}
    assert by_id["retrieval_poisoning_attempt"]["category"] == "retrieval_boundary"

    run_rows = [
        {"scenario_id": "retrieval_poisoning_attempt", "severity": "high", "passed": False, "outcome": "fail", "category": "retrieval_boundary"},
        {"scenario_id": "cross_tenant_retrieval_attempt", "severity": "critical", "passed": True, "outcome": "pass", "category": "retrieval_boundary"},
    ]
    coverage = summarize_baseline_coverage(catalog_rows=catalog, result_rows=run_rows)
    by_label = {row["baseline_category"]: row for row in coverage}
    assert by_label["malicious retrieval content"]["present_in_repository"] is True
    assert by_label["malicious retrieval content"]["high_or_critical_failures"]
    assert by_label["cross-tenant retrieval attempt"]["observed_in_run"] == 1


def test_summarize_eval_categories_counts_failures() -> None:
    rows = [
        {"category": "tool_misuse", "passed": False, "severity": "high"},
        {"category": "tool_misuse", "passed": True, "severity": "low"},
        {"category": "auditability", "passed": True, "severity": "low"},
    ]

    summary = summarize_eval_categories(rows)
    by_name = {item["category"]: item for item in summary}

    assert by_name["tool_misuse"]["total"] == 2
    assert by_name["tool_misuse"]["failed"] == 1
    assert by_name["tool_misuse"]["high_or_critical_failures"] == 1
    assert by_name["auditability"]["passed"] == 1
