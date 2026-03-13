from __future__ import annotations

from integration_adapter.env_profiles import get_profile_policy, validate_profile_safeguards


def test_get_profile_policy_rejects_unknown_profile() -> None:
    try:
        get_profile_policy("unknown")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unsupported INTEGRATION_ADAPTER_PROFILE" in str(exc)


def test_prod_like_blocks_synthetic_runtime_evidence() -> None:
    result = validate_profile_safeguards(
        profile="prod_like",
        force_demo=False,
        exporter_diagnostics={
            "runtime_events": {"source_mode": "synthetic", "rows_count": 4, "fallback_used": True},
            "connectors": {"source_mode": "file_backed", "rows_count": 1, "fallback_used": False},
        },
        launch_gate_freshness_evidence={"stale_critical": [], "missing_critical": []},
    )
    assert result.blocked_reasons
    assert any("non-synthetic runtime evidence" in reason for reason in result.blocked_reasons)


def test_prod_like_blocks_stale_critical_evidence() -> None:
    result = validate_profile_safeguards(
        profile="prod_like",
        force_demo=False,
        exporter_diagnostics={
            "runtime_events": {"source_mode": "file_backed", "rows_count": 3, "fallback_used": False},
        },
        launch_gate_freshness_evidence={"stale_critical": ["audit.jsonl age=9999s"], "missing_critical": []},
    )
    assert any("stale_critical" in reason for reason in result.blocked_reasons)


def test_demo_allows_synthetic_runtime_evidence() -> None:
    result = validate_profile_safeguards(
        profile="demo",
        force_demo=True,
        exporter_diagnostics={
            "runtime_events": {"source_mode": "synthetic", "rows_count": 3, "fallback_used": True},
        },
        launch_gate_freshness_evidence=None,
    )
    assert result.blocked_reasons == []
